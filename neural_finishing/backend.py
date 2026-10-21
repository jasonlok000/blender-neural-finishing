# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict adapter for the upstream BlenDLSS ABI 3, isolated from Blender."""
import ctypes
import os
import time
from pathlib import Path

from .common import read_json, sha256


class Frame(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int32) for name in ("width", "height")] + [
        ("color", ctypes.POINTER(ctypes.c_uint8)),
        ("depth", ctypes.POINTER(ctypes.c_float)),
        ("motion", ctypes.POINTER(ctypes.c_float)),
    ] + [(name, ctypes.c_int32) for name in ("reset", "stream", "passes", "hide_indicator")]


class Settings(ctypes.Structure):
    _fields_ = [(name, ctypes.c_float) for name in ("intensity", "structure", "tone", "skin")] + [
        (name, ctypes.c_int32) for name in ("style", "auto_mask", "preset")]


class NvidiaBackend:
    def __init__(self, package, log_directory):
        if os.name != "nt":
            raise RuntimeError("The current NVIDIA backend requires Windows")
        package = Path(package).resolve()
        provenance = read_json(package / "runtime-manifest.json")
        for name, expected in provenance["files"].items():
            candidate = (package / name).resolve()
            if not candidate.is_relative_to(package) or sha256(candidate) != expected:
                raise RuntimeError("Runtime integrity check failed: " + name)
        self.hook = None
        self.lib = None
        self.evaluations = 0
        try:
            if provenance["compatibility"] == "ampere-process-local":
                from .ampere_probe_hook import ProbeHook
                self.hook = ProbeHook()
            elif provenance["compatibility"] != "none":
                raise RuntimeError("Unknown compatibility profile")
            self.lib = lib = ctypes.CDLL(str(package / "bin/blendlss5_nvngx.dll"))
            lib.dlss5b_abi_version.restype = ctypes.c_int32
            if lib.dlss5b_abi_version() != 3:
                raise RuntimeError("Expected BlenDLSS bridge ABI 3")
            lib.dlss5b_last_error.restype = ctypes.c_char_p
            lib.dlss5b_adapter_name.restype = ctypes.c_char_p
            lib.dlss5b_init.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
            lib.dlss5b_init.restype = ctypes.c_int32
            lib.dlss5b_process.argtypes = [ctypes.POINTER(Frame), ctypes.POINTER(Settings), ctypes.POINTER(ctypes.c_uint8)]
            lib.dlss5b_process.restype = ctypes.c_int32
            lib.dlss5b_release_stream.argtypes = [ctypes.c_int32]
            lib.dlss5b_shutdown.argtypes = []
            Path(log_directory).mkdir(parents=True, exist_ok=True)
            if lib.dlss5b_init(str(package / "bin/nvngx_dlssnr.dll"), str(log_directory)):
                raise RuntimeError(self.error())
            self.adapter = lib.dlss5b_adapter_name().decode(errors="replace")
        except Exception:
            self.close()
            raise

    def error(self):
        return (self.lib.dlss5b_last_error() or b"Native NVIDIA error").decode(errors="replace")

    def process(self, color, depth, motion, settings, reset):
        import numpy as np
        color = np.ascontiguousarray(color[::-1], dtype=np.uint8)
        depth = np.ascontiguousarray(depth[::-1], dtype=np.float32)
        motion = np.ascontiguousarray(motion[::-1], dtype=np.float32)
        h, w = color.shape[:2]
        if color.shape != (h, w, 4) or depth.shape != (h, w) or motion.shape != (h, w, 2):
            raise ValueError("Color, depth and motion dimensions do not match")
        output = np.empty_like(color)
        pointer = lambda array, kind: array.ctypes.data_as(ctypes.POINTER(kind))
        frame = Frame(w, h, pointer(color, ctypes.c_uint8), pointer(depth, ctypes.c_float),
                      pointer(motion, ctypes.c_float), int(reset), 0, 1, 1)
        options = Settings(settings["intensity"], settings["structure"], settings["tone"],
                           -1, settings["style"], 1, 1)
        start = time.perf_counter()
        code = self.lib.dlss5b_process(ctypes.byref(frame), ctypes.byref(options), pointer(output, ctypes.c_uint8))
        if code:
            raise RuntimeError("Native evaluation failed (%s): %s" % (code, self.error()))
        self.evaluations += 1
        output[..., 3] = 255
        return np.ascontiguousarray(output[::-1]), time.perf_counter() - start

    def close(self):
        try:
            if self.lib is not None:
                self.lib.dlss5b_shutdown()
        finally:
            self.lib = None
            if self.hook is not None:
                self.hook.close()
                self.hook = None
