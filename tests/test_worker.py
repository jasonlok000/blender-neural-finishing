# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-rendering tests using explicitly synthetic pixels and a fixture backend."""
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import Imath
import numpy as np
import OpenEXR
from PIL import Image

from neural_finishing import common, guides, worker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scene.blend").write_bytes(b"TEST FIXTURE - NOT A BLENDER SCENE")
        self.job = dict(protocol=1, blender="never-executed-blender.exe", snapshot="scene.blend",
                        snapshot_sha256=common.sha256(self.root / "scene.blend"),
                        scene="fixture", view_layer="ViewLayer", frames=[1, 2, 3, 4], width=8, height=4,
                        backend="fixture", intensity=0.65, structure=0.65, tone=0.4, style="CINEMATIC")
        common.atomic_json(self.root / "job.json", self.job)
        self.calls = []
        self.fail_at = None
        self.fingerprint = common.job_fingerprint(self.job)
        for frame in self.job["frames"]:
            self.make_capture(frame)
        # Any attempt to launch Blender/GPU code in this test suite is a failure.
        self.popen = mock.patch("subprocess.Popen", side_effect=AssertionError("Tests must not launch a renderer"))
        self.popen.start()
        self.addCleanup(self.popen.stop)

    def make_capture(self, frame):
        files = {}
        for name in ("beauty", "guides", "metadata", "hdr", "capture"):
            (self.root / name).mkdir(exist_ok=True)
        beauty = self.root / "beauty" / ("%07d.png" % frame)
        color = np.full((4, 8, 4), frame * 10, dtype=np.uint8)
        color[..., 3] = 255
        Image.fromarray(color).save(beauty)
        hdr = self.root / "hdr" / ("%07d.exr" % frame)
        hdr.write_bytes(b"unchanged-original-HDR-fixture")
        path = self.root / "guides" / ("%07d.exr" % frame)
        header = OpenEXR.Header(8, 4)
        names = ["ViewLayer.Depth.Z", "ViewLayer.Vector.X", "ViewLayer.Vector.Y"]
        header["channels"] = {name: Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT)) for name in names}
        image = OpenEXR.OutputFile(str(path), header)
        image.writePixels({name: np.full((4, 8), value, np.float32).tobytes()
                           for name, value in zip(names, (5, 2, 3))})
        image.close()
        meta = self.root / "metadata" / ("%07d.json" % frame)
        common.atomic_json(meta, dict(width=8, height=4, near=0.1, far=100,
                                      shot="A" if frame <= 2 else "B"))
        for item in (beauty, hdr, path, meta):
            files[str(item.relative_to(self.root))] = common.sha256(item)
        common.atomic_json(self.root / "capture" / ("%07d.json" % frame),
                           dict(job_fingerprint=self.fingerprint, files=files))

    def backend(self, logs):
        owner = self

        class FixtureBackend:
            def process(self, color, depth, motion, settings, reset):
                frame = int(color[0, 0, 0]) // 10
                owner.calls.append((frame, reset, motion.copy()))
                if frame == owner.fail_at:
                    raise RuntimeError("deliberate fixture native failure")
                result = color.copy()
                result[..., 0] += 1
                return result, 0.001

            def close(self):
                pass
        return FixtureBackend()

    def run_fixture(self):
        return worker.run_job(self.root / "job.json", backend_factory=self.backend,
                              capture_runner=lambda root, job: None)

    def test_camera_cut_resets_and_sources_unchanged(self):
        originals = {p: common.sha256(p) for folder in ("hdr", "beauty") for p in (self.root / folder).iterdir()}
        self.assertEqual(self.run_fixture(), 0)
        self.assertEqual([(f, reset) for f, reset, _ in self.calls], [(1, True), (2, False), (3, True), (4, False)])
        self.assertTrue(np.all(self.calls[0][2] == 0))
        self.assertEqual(self.calls[1][2][0, 0].tolist(), [2, -3])
        self.assertEqual(originals, {p: common.sha256(p) for p in originals})
        self.assertEqual(len(list((self.root / "processed").glob("*.png"))), 4)
        for path in (self.root / "processed").glob("*.png"):
            with Image.open(path) as image:
                self.assertEqual(image.size, (8, 4))

    def test_complete_shots_are_reused(self):
        self.run_fixture()
        self.calls.clear()
        self.run_fixture()
        self.assertEqual(self.calls, [])

    def test_native_failure_and_resume_restart_incomplete_shot(self):
        self.fail_at = 4
        with self.assertRaisesRegex(RuntimeError, "native failure"):
            self.run_fixture()
        self.assertEqual(common.read_json(self.root / "status.json")["state"], "error")
        self.fail_at = None
        self.calls.clear()
        self.run_fixture()
        self.assertEqual([(f, reset) for f, reset, _ in self.calls], [(3, True), (4, False)])

    def test_cancellation_never_starts_capture(self):
        (self.root / "CANCEL").touch()
        self.assertEqual(self.run_fixture(), 75)
        self.assertEqual(self.calls, [])

    def test_cancellation_midshot_is_not_marked_complete(self):
        old_factory = self.backend

        def factory(logs):
            native = old_factory(logs)
            original = native.process

            def process(*args, **kwargs):
                result = original(*args, **kwargs)
                (self.root / "CANCEL").touch()
                return result
            native.process = process
            return native
        self.assertEqual(worker.run_job(self.root / "job.json", backend_factory=factory,
                                       capture_runner=lambda *_: None), 75)
        self.assertFalse((self.root / "shots").exists())

    def test_tampered_capture_rejected_before_backend(self):
        (self.root / "beauty/0000001.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "altered capture"):
            self.run_fixture()
        self.assertEqual(self.calls, [])

    def test_changed_snapshot_rejected(self):
        (self.root / "scene.blend").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            self.run_fixture()

    def test_incomplete_output_receipt_reprocesses_whole_shot(self):
        self.run_fixture()
        (self.root / "processed/0000002.png").unlink()
        self.calls.clear()
        self.run_fixture()
        self.assertEqual([(f, r) for f, r, _ in self.calls], [(1, True), (2, False)])

    def test_fixture_backend_cannot_be_selected_from_public_cli(self):
        with self.assertRaisesRegex(ValueError, "test-only"):
            worker.run_job(self.root / "job.json")

    def test_duplicate_worker_lock(self):
        with common.job_lock(self.root):
            with self.assertRaisesRegex(RuntimeError, "already running"):
                with common.job_lock(self.root):
                    self.fail("Second lock acquired")

    def test_bad_runtime_hash_and_missing_runtime(self):
        with self.assertRaises(FileNotFoundError):
            worker.probe(self.root)
        (self.root / "model.dll").write_bytes(b"test binary fixture")
        common.atomic_json(self.root / "runtime-manifest.json", {"files": {"model.dll": "wrong"}})
        with self.assertRaisesRegex(RuntimeError, "integrity"):
            worker.probe(self.root)

    def test_probe_does_not_initialize_backend(self):
        (self.root / "model.dll").write_bytes(b"test binary fixture")
        common.atomic_json(self.root / "runtime-manifest.json",
                           {"files": {"model.dll": common.sha256(self.root / "model.dll")}})
        with mock.patch("ctypes.CDLL", side_effect=AssertionError("Must not load native code")):
            self.assertFalse(worker.probe(self.root)["gpu_tested"])

    def test_path_escape_and_protocol_rejected(self):
        with self.assertRaises(ValueError):
            common.contained(self.root, "../outside")
        for changes in ({"protocol": 2}, {"frames": [2, 1]}, {"frames": [1, 3]},
                        {"intensity": float("nan")}, {"width": 0}, {"snapshot": "../outside"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                common.validate_job(dict(self.job, **changes))

    def test_depth_endpoints_and_motion_axis(self):
        z = np.array([[0.1, 100, np.inf]], np.float32)
        depth, motion = guides.convert_guides(z, np.ones_like(z), 2 * np.ones_like(z), 0.1, 100)
        np.testing.assert_allclose(depth, [[0, 1, 1]], atol=1e-6)
        np.testing.assert_allclose(motion[..., 0], 1)
        np.testing.assert_allclose(motion[..., 1], -2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
