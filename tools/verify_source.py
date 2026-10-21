# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile all contribution Python files in memory; never execute capture code."""
import ast
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
paths = []
for folder in ("neural_finishing", "tools", "tests", "native_preview"):
    paths.extend((root / folder).glob("*.py"))
for path in paths:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(json.dumps(dict(state="pass", python_files=len(paths), render_invocations=0, gpu_inference_invocations=0)))
