# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone worker. Rendering/inference only occur for an explicit --job."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .common import (STYLES, JobAlreadyRunning, atomic_json, cancelled, contained, job_fingerprint,
                     job_lock, read_json, sha256, status, validate_job, verified_receipt)


class Cancelled(Exception):
    pass


def check_cancel(root):
    if cancelled(root):
        raise Cancelled("Cancelled; completed captures and complete shots are retained")


def reject_other_background_render():
    """CLI callers get the same conservative guard as the native button."""
    if os.name != "nt":
        raise RuntimeError("The current runtime requires Windows")
    command = ("@(Get-CimInstance Win32_Process -Filter \"Name='blender.exe'\" | "
               "Where-Object { $_.CommandLine -match '(?:^|\\s)(?:-b|--background)(?:\\s|$)' } | "
               "Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            capture_output=True, text=True, timeout=15,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("Could not verify that background Blender rendering is idle")
    ids = json.loads(result.stdout) if result.stdout.strip() else []
    if ids:
        raise RuntimeError("Another background Blender render is active; no work was started")


def probe(package):
    """File/ABI dependency inventory only: never loads NVIDIA or initializes a GPU."""
    package = Path(package).resolve()
    manifest = read_json(package / "runtime-manifest.json")
    if not manifest.get("files"):
        raise ValueError("Runtime manifest contains no files")
    for name, digest in manifest["files"].items():
        if sha256(contained(package, name)) != digest:
            raise RuntimeError("Runtime integrity check failed: " + name)
    return dict(protocol=1, state="available", gpu_tested=False, message="Runtime files verified; inference not tested", runtime=manifest)


def render_captures(root, job):
    check_cancel(root)
    # A verified capture-only job never enters the render process on resume.
    fingerprint = job_fingerprint(job)
    if all(verified_receipt(root, root / "capture" / ("%07d.json" % frame), fingerprint)
           for frame in job["frames"]):
        return
    command = [job["blender"], "--background", "--disable-autoexec",
               str(contained(root, job["snapshot"])), "--threads", "2",
               "--python-exit-code", "23", "--python",
               str(Path(__file__).with_name("render_capture.py")), "--", str(root / "job.json")]
    with (root / "render.log").open("ab") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            while child.poll() is None:
                check_cancel(root)
                time.sleep(0.25)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        if child.returncode:
            raise RuntimeError("Background capture failed; see render.log (exit %s)" % child.returncode)


def frame_groups(root, job):
    groups = []
    previous = None
    for frame in job["frames"]:
        meta = read_json(root / "metadata" / ("%07d.json" % frame))
        if meta["width"] != job["width"] or meta["height"] != job["height"]:
            raise ValueError("Captured dimensions disagree with the job")
        if meta["shot"] != previous:
            groups.append([])
            previous = meta["shot"]
        groups[-1].append((frame, meta))
    return groups


def process_captures(root, job, backend_factory=None):
    import numpy as np
    from PIL import Image
    from .guides import load_guides
    from .backend import NvidiaBackend
    fingerprint = job_fingerprint(job)
    groups = frame_groups(root, job)
    package = Path(__file__).resolve().parents[1]
    factory = backend_factory or (lambda logs: NvidiaBackend(package, logs))
    completed = 0
    settings = {key: job[key] for key in ("intensity", "structure", "tone")}
    settings["style"] = STYLES[job["style"]]
    for group in groups:
        check_cancel(root)
        name = "%07d_%07d" % (group[0][0], group[-1][0])
        receipt = root / "shots" / (name + ".json")
        if verified_receipt(root, receipt, fingerprint):
            completed += len(group)
            continue
        # Incomplete shots restart at their first frame, including history.
        native = factory(root / "logs" / name)
        rows = []
        files = {}
        try:
            for index, (frame, meta) in enumerate(group):
                check_cancel(root)
                status(root, "running", "neural", completed, len(job["frames"]), "Processing frame %s" % frame)
                color = np.array(Image.open(root / "beauty" / ("%07d.png" % frame)).convert("RGBA"))
                if color.shape != (job["height"], job["width"], 4) or not np.all(color[..., 3] == 255):
                    raise ValueError("Version one requires matching opaque beauty images")
                depth, motion = load_guides(root / "guides" / ("%07d.exr" % frame), meta)
                if index == 0:
                    motion = np.zeros_like(motion)
                result, seconds = native.process(color, depth, motion, settings, reset=index == 0)
                destination = root / "processed" / ("%07d.png" % frame)
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(".partial.png")
                Image.fromarray(result).save(temporary)
                os.replace(temporary, destination)
                files[str(destination.relative_to(root))] = sha256(destination)
                rows.append(dict(frame=frame, reset=index == 0, native_return=0, seconds=seconds))
                completed += 1
        finally:
            native.close()
        atomic_json(receipt, dict(job_fingerprint=fingerprint, files=files, frames=rows,
                                 backend=job["backend"], native_evaluations=len(rows), color="RGBA8 SDR"))
    return len(job["frames"])


def run_job(job_path, *, backend_factory=None, capture_runner=None):
    job_path = Path(job_path).resolve()
    root = job_path.parent
    job = validate_job(read_json(job_path))
    if job["backend"] != "nvidia" and backend_factory is None:
        raise ValueError("Fixture backend is test-only and cannot be selected in the application")
    snapshot = contained(root, job["snapshot"])
    if sha256(snapshot) != job["snapshot_sha256"]:
        raise ValueError("Scene snapshot changed; create a new job")
    for asset in job.get("assets", []):
        if sha256(asset["path"]) != asset["sha256"]:
            raise ValueError("External scene asset changed; create a new job")
    with job_lock(root), ExitStack() as resources:
        try:
            check_cancel(root)
            if backend_factory is None:
                resource_directory = Path(tempfile.gettempdir()) / "blender-neural-finishing-resource"
                resource_directory.mkdir(exist_ok=True)
                resources.enter_context(job_lock(resource_directory))
                reject_other_background_render()
                package = Path(__file__).resolve().parents[1]
                if sha256(package / "runtime-manifest.json") != job.get("runtime_manifest_sha256"):
                    raise ValueError("Runtime package changed; create a new job")
                probe(package)
            status(root, "running", "capture", 0, len(job["frames"]))
            (capture_runner or render_captures)(root, job)
            fingerprint = job_fingerprint(job)
            for frame in job["frames"]:
                if not verified_receipt(root, root / "capture" / ("%07d.json" % frame), fingerprint):
                    raise ValueError("Missing or altered capture for frame %s" % frame)
            count = process_captures(root, job, backend_factory)
            status(root, "complete", "complete", count, count, "Original HDR and separate SDR results are ready")
            return 0
        except Cancelled as error:
            status(root, "cancelled", "cancelled", message=str(error))
            return 75
        except Exception as error:
            status(root, "error", "error", message=str(error))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--probe", action="store_true", help="Verify files only; no GPU initialization")
    action.add_argument("--job", type=Path, help="Explicitly render and process this job")
    args = parser.parse_args()
    try:
        if args.probe:
            print(json.dumps(probe(Path(__file__).resolve().parents[1])))
            return 0
        return run_job(args.job)
    except Exception as error:
        if args.job and args.job.parent.is_dir() and not isinstance(error, JobAlreadyRunning):
            status(args.job.parent, "error", "error", message=str(error))
        print(json.dumps(dict(state="error", message=str(error))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
