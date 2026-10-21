# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert native Blender pass channels, never inferred optical flow."""
import numpy as np


def convert_guides(z, x, y, near, far):
    if not 0 < near < far:
        raise ValueError("Invalid camera clipping planes")
    z = np.nan_to_num(z, nan=far, posinf=far, neginf=far)
    depth = np.clip(far * (z - near) / (np.maximum(z, near) * (far - near)), 0, 1)
    motion = np.nan_to_num(np.stack([x, -y], axis=-1), nan=0, posinf=0, neginf=0)
    motion[np.linalg.norm(motion, axis=-1) > z.shape[1] * 4] = 0
    return depth.astype(np.float32), motion.astype(np.float32)


def load_guides(path, metadata):
    import Imath
    import OpenEXR
    image = OpenEXR.InputFile(str(path))
    try:
        header = image.header()
        window = header["dataWindow"]
        shape = (window.max.y - window.min.y + 1, window.max.x - window.min.x + 1)
        names = list(header["channels"])
        channels = []
        for suffix in (".Depth.Z", ".Vector.X", ".Vector.Y"):
            matches = [name for name in names if name.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous guide channel " + suffix)
            channels.append(matches[0])
        planes = image.channels(channels, Imath.PixelType(Imath.PixelType.FLOAT))
        values = [np.frombuffer(plane, np.float32).reshape(shape).copy() for plane in planes]
        return convert_guides(*values, metadata["near"], metadata["far"])
    finally:
        image.close()
