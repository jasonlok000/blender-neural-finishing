# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the exact native WIP panel into an isolated stock Blender session."""
import importlib.util
from pathlib import Path
import sys
import bpy

root = Path(__file__).resolve().parents[1]


def load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    for cls in module.classes:
        bpy.utils.register_class(cls)
    if hasattr(module, "register"):
        module.register()
    return module


operator = load("neural_finishing_native_operators", root / "native_preview/neural_finishing.py")
panel = load("neural_finishing_native_panel", root / "native_preview/properties_neural_finishing.py")
settings = bpy.context.window_manager.neural_finishing
settings.package_directory = str(root)
settings.enabled = False
settings.status = "Prototype loaded; rendering and GPU inference have not started"
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == "PROPERTIES":
            area.spaces.active.context = "RENDER"
print("NATIVE_PREVIEW_REGISTERED_WITHOUT_RENDER")
