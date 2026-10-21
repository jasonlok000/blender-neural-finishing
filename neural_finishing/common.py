# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Version-one file protocol; no Blender, GPU or third-party imports."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path

PROTOCOL = 1
STYLES = {"STANDARD": 0, "NATURAL": 1, "CINEMATIC": 2}


class JobAlreadyRunning(RuntimeError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Job file path must stay inside the job directory")
    return path


def validate_job(job):
    if job.get("protocol") != PROTOCOL:
        raise ValueError("Unsupported neural-finishing job protocol")
    frames = job.get("frames")
    if not isinstance(frames, list) or not frames or any(type(f) is not int for f in frames):
        raise ValueError("frames must be a nonempty list of integers")
    if frames != sorted(set(frames)):
        raise ValueError("frames must be unique and chronological")
    if len(frames) > 1 and any(b != a + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("Version one requires consecutive animation frames")
    if job.get("style") not in STYLES:
        raise ValueError("Unknown neural style")
    for key in ("intensity", "structure", "tone"):
        value = job.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Appearance controls must be finite numbers")
        if not 0 <= value <= 2:
            raise ValueError("Appearance controls must be between zero and two")
    for key in ("width", "height"):
        if type(job.get(key)) is not int or job[key] <= 0:
            raise ValueError("Invalid image dimensions")
    for key in ("blender", "snapshot", "scene", "view_layer", "snapshot_sha256"):
        if not isinstance(job.get(key), str) or not job[key]:
            raise ValueError("Missing job field: " + key)
    contained(Path.cwd(), job["snapshot"])
    if job.get("backend") not in ("nvidia", "fixture"):
        raise ValueError("Unknown backend")
    return job


def job_fingerprint(job):
    return hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()


def verified_receipt(root, receipt, fingerprint):
    try:
        data = read_json(receipt)
        if data.get("job_fingerprint") != fingerprint or not data.get("files"):
            return False
        return all(sha256(contained(root, name)) == digest for name, digest in data["files"].items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


@contextlib.contextmanager
def job_lock(root):
    """OS-owned lock releases on crash; no stale-PID deletion or GPU overlap."""
    path = Path(root) / "job.lock"
    with path.open("a+b") as stream:
        stream.seek(0)
        stream.write(b"0")
        stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise JobAlreadyRunning("This job is already running") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def status(root, state, stage, completed=0, total=0, message=""):
    atomic_json(Path(root) / "status.json", dict(
        protocol=PROTOCOL, state=state, stage=stage, completed=completed,
        total=total, message=message, pid=os.getpid(),
    ))


def cancelled(root):
    return (Path(root) / "CANCEL").exists()
