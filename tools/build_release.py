# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a portable experimental package without rendering or loading a GPU."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
ORIGINAL = WORKSPACE.parent / "DLSS5_Experiment"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    archive_root = WORKSPACE / "downloads"
    archive_root.mkdir(exist_ok=True)
    python_archive = archive_root / "python-3.13.5-embed-amd64.zip"
    if not python_archive.exists():
        urllib.request.urlretrieve("https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip", python_archive)
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(python_archive) as archive:
        archive.extractall(runtime)
    (runtime / "python313._pth").write_text("python313.zip\n.\n..\nLib/site-packages\nimport site\n", encoding="utf-8")
    destination = runtime / "Lib/site-packages"
    destination.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name in ("numpy", "Pillow", "OpenEXR"):
        distribution = importlib.metadata.distribution(name)
        versions[name] = distribution.version
        for relative in distribution.files:
            if ".." in relative.parts or relative.suffix == ".pyc":
                continue
            source = Path(distribution.locate_file(relative))
            if not source.is_file():
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (ROOT / "bin").mkdir(exist_ok=True)
    originals = {
        "bin/blendlss5_nvngx.dll": ORIGINAL / "Tools/BlenDLSS_Release/dlss5_compositor/bin/blendlss5_nvngx.dll",
        "bin/nvngx_dlssnr.dll": ORIGINAL / "Tools/NeuralScreen_Release/native/nvngx_dlssnr.dll",
        "neural_finishing/ampere_probe_hook.py": ORIGINAL / "ampere_probe_hook.py",
    }
    provenance = json.loads((ORIGINAL / "Tool_Provenance.json").read_text())
    expected = {
        "bin/blendlss5_nvngx.dll": "f8a4040779f1323b74e8aaae6f80a47e559b4901b06bdf28e8a0d2ec653a5533",
        "bin/nvngx_dlssnr.dll": "dcc0dc2414aedec4a8e084647070383be068554042587180c20c784d4772d36f",
    }
    for relative, source in originals.items():
        if relative in expected and digest(source) != expected[relative]:
            raise ValueError("Original runtime hash changed: " + relative)
        shutil.copy2(source, ROOT / relative)
    native_preview = ROOT / "native_preview"
    native_preview.mkdir(exist_ok=True)
    for source in (
        WORKSPACE / "blender/scripts/startup/bl_operators/neural_finishing.py",
        WORKSPACE / "blender/scripts/startup/bl_ui/properties_neural_finishing.py",
    ):
        shutil.copy2(source, native_preview / source.name)
    upstream = ORIGINAL / "Tools/BLENDLSS/source/dlss5_compositor"
    bridge_source = ROOT / "third_party/blendlss/native"
    shutil.copytree(upstream / "native", bridge_source, dirs_exist_ok=True)
    shutil.copy2(upstream / "blender_manifest.toml", bridge_source.parent / "upstream_blender_manifest.toml")
    notices = ROOT / "third_party/notices"
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ORIGINAL / "Tools/NeuralScreen/THIRD-PARTY-NOTICES.md", notices / "NeuralScreen-runtime-provenance.md")
    # This notice is retained as evidence of the upstream runtime's provenance;
    # no NeuralScreen application source is incorporated.
    shutil.copy2(ORIGINAL / "SOURCE_AUDIT_REPORT.txt", notices / "RECORDED_SOURCE_AUDIT.txt")
    files = {relative: digest(ROOT / relative) for relative in originals}
    manifest = dict(protocol=1, compatibility="ampere-process-local", files=files,
                    runtime_version="310.8.0.0", upstream_repositories=provenance["repositories"],
                    tested_configuration="Recorded prior tests only: RTX 3090 24GB, driver 580.97",
                    new_prototype_gpu_validation="NOT RUN; user has an active production render",
                    runtime_origin="Leaked non-public NVIDIA runtime, community compatibility build",
                    python="3.13.5", python_archive_sha256=digest(python_archive), dependencies=versions)
    (ROOT / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (ROOT / "requirements-pinned.txt").write_text("\n".join("%s==%s" % item for item in versions.items()) + "\n")
    print(json.dumps(dict(state="prepared", dependencies=versions, binary_files=files)))


if __name__ == "__main__":
    build()
