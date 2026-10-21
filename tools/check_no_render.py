# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender registration/settings checks ONLY. No rendering or native inference."""
import ast
import json
from pathlib import Path
import runpy
import sys
import bpy

root = Path(__file__).resolve().parents[1]
report = {"render_invocations": 0, "gpu_inference_invocations": 0, "checks": []}


def check(value, name):
    if not value:
        raise AssertionError(name)
    report["checks"].append(name)


for filename in ("preview_in_blender.py", "make_demo.py"):
    tree = ast.parse((root / "tools" / filename).read_text())
    forbidden = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == "render"]
    check(not forbidden, filename + " contains no render calls")

namespace = runpy.run_path(str(root / "tools/preview_in_blender.py"))
operator = namespace["operator"]
panel = namespace["panel"]
settings = bpy.context.window_manager.neural_finishing
check(not settings.enabled, "feature disabled by default")
check(not settings.running, "registration does not start work")
check(operator._process is None, "registration creates no subprocess")
check(hasattr(bpy.ops.render, "neural_finishing"), "native operator registered")
check(panel.RENDER_PT_neural_finishing.bl_context == "render", "panel belongs to Render Properties")
check(settings.mode == "STILL", "default mode is current frame")
check(settings.style == "CINEMATIC", "default style is Cinematic")
try:
    settings.enabled = True
    previous = operator._background_render_exists
    operator._background_render_exists = lambda: True
    try:
        operator._preflight(bpy.context, settings)
        raise AssertionError("Concurrent-render guard did not reject")
    except ValueError as error:
        check("Another Blender render" in str(error), "active-render guard rejects before snapshot/render")
finally:
    operator._background_render_exists = previous
    settings.enabled = False
report["other_background_blender_detected"] = operator._background_render_exists()
settings.package_directory = str(root)
result = bpy.ops.render.neural_finishing_probe()
check(result == {"FINISHED"}, "file-only worker probe succeeds without NVIDIA initialization")
check("not tested" in settings.status, "file probe does not claim inference success")
report["blender_version"] = bpy.app.version_string
report["status"] = "PASS - NON-RENDERING CHECKS ONLY"
(root / "validation").mkdir(exist_ok=True)
(root / "validation/blender_no_render.json").write_text(json.dumps(report, indent=2))
operator.unregister()
for cls in reversed(panel.classes):
    bpy.utils.unregister_class(cls)
for cls in reversed(operator.classes):
    bpy.utils.unregister_class(cls)
check(not hasattr(bpy.types.WindowManager, "neural_finishing"), "prototype unregisters cleanly")
(root / "validation/blender_no_render.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
