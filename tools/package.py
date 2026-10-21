# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export source patches and portable release. Does not start Blender or a GPU."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
workspace = root.parent
base = "6421771fd4d65965a2259e14d222f4913f192d03"
patches = root / "patches"
patches.mkdir(exist_ok=True)
for branch, name in (("codex/neural-finishing-prototype", "0001-native-neural-finishing.patch"),
                     ("codex/vector-pass-explanation", "0001-vector-pass-explanation.patch")):
    result = subprocess.run(["git", "format-patch", "--stdout", base + ".." + branch],
                            cwd=workspace / "blender", capture_output=True, check=True)
    (patches / name).write_bytes(result.stdout)
artifact_dir = workspace / "artifacts"
artifact_dir.mkdir(exist_ok=True)
archive = artifact_dir / "Neural-Finishing-0.1.0-experimental-Windows.zip"
excluded = {".git", "__pycache__", "dist"}
private_tools = {"tools/github_access.py", "tools/publish.py"}
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (not path.is_file() or any(part in excluded for part in relative.parts)
                or relative.as_posix() in private_tools or path.suffix in {".pyc", ".blend1"}
                or ".partial" in path.name or "local" in path.name and relative.parts[0] == "validation"):
            continue
        output.write(path, "Neural-Finishing-0.1.0/" + relative.as_posix())
with archive.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
(artifact_dir / "SHA256SUMS.txt").write_text(digest + "  " + archive.name + "\n")
print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size, sha256=digest)))
