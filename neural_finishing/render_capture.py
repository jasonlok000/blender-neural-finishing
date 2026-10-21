# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit worker-only Blender capture. Never imported during startup/tests."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neural_finishing.common import (atomic_json, cancelled, job_fingerprint, read_json,
                                     sha256, status, validate_job, verified_receipt)


def capture(job_path):
    import bpy
    root = Path(job_path).resolve().parent
    job = validate_job(read_json(job_path))
    fingerprint = job_fingerprint(job)
    scene = bpy.data.scenes[job["scene"]]
    bpy.context.window.scene = scene
    layer = scene.view_layers[job["view_layer"]]
    for item in scene.view_layers:
        item.use = item == layer
    scene.render.engine = "CYCLES"
    # Preserve the user's device; sample demo explicitly opts into CPU.
    scene.render.resolution_x = job["width"]
    scene.render.resolution_y = job["height"]
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = False
    beauty_blur = scene.render.use_motion_blur
    beauty_compositing = scene.render.use_compositing
    samples = scene.cycles.samples
    adaptive = scene.cycles.use_adaptive_sampling
    denoise = scene.cycles.use_denoising
    # A copied compositor must not write File Output nodes into production paths.
    for tree in bpy.data.node_groups:
        if tree.bl_idname == "CompositorNodeTree":
            for node in tree.nodes:
                if node.bl_idname == "CompositorNodeOutputFile":
                    node.mute = True
    legacy_tree = getattr(scene, "node_tree", None)
    if legacy_tree is not None:
        for node in legacy_tree.nodes:
            if node.bl_idname == "CompositorNodeOutputFile":
                node.mute = True
    layer.use_pass_z = True
    layer.use_pass_vector = True
    markers = sorted((m for m in scene.timeline_markers if m.camera), key=lambda m: m.frame)
    default_camera = scene.camera
    if default_camera is None:
        raise ValueError("A perspective camera is required")
    for number, frame in enumerate(job["frames"]):
        if cancelled(root):
            return 75
        receipt = root / "capture" / ("%07d.json" % frame)
        if verified_receipt(root, receipt, fingerprint):
            continue
        scene.frame_set(frame)
        preceding = [m for m in markers if m.frame <= frame]
        marker = preceding[-1] if preceding else None
        camera = marker.camera if marker else default_camera
        scene.camera = camera
        if camera.data.type != "PERSP":
            raise ValueError("Version one supports perspective cameras only")
        files = {}
        for name in ("hdr", "beauty", "guides", "metadata"):
            (root / name).mkdir(parents=True, exist_ok=True)
        scene.render.use_motion_blur = beauty_blur
        scene.render.use_compositing = beauty_compositing
        scene.cycles.samples = samples
        scene.cycles.use_adaptive_sampling = adaptive
        scene.cycles.use_denoising = denoise
        settings = scene.render.image_settings
        settings.file_format = "OPEN_EXR_MULTILAYER"
        settings.color_depth = "32"
        settings.exr_codec = "ZIP"
        scene.render.filepath = str(root / "hdr" / ("%07d.partial.exr" % frame))
        status(root, "running", "beauty", number, len(job["frames"]), "Rendering frame %s" % frame)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        destination = root / "hdr" / ("%07d.exr" % frame)
        os.replace(scene.render.filepath, destination)
        files[str(destination.relative_to(root))] = sha256(destination)
        settings.file_format = "PNG"
        settings.color_mode = "RGBA"
        settings.color_depth = "8"
        temporary = root / "beauty" / ("%07d.partial.png" % frame)
        bpy.data.images["Render Result"].save_render(str(temporary), scene=scene)
        destination = root / "beauty" / ("%07d.png" % frame)
        os.replace(temporary, destination)
        files[str(destination.relative_to(root))] = sha256(destination)
        if cancelled(root):
            return 75
        scene.render.use_motion_blur = False
        scene.render.use_compositing = False
        scene.cycles.samples = 1
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.use_denoising = False
        settings.file_format = "OPEN_EXR_MULTILAYER"
        settings.color_depth = "32"
        temporary = root / "guides" / ("%07d.partial.exr" % frame)
        scene.render.filepath = str(temporary)
        status(root, "running", "guides", number, len(job["frames"]), "Exporting guides for frame %s" % frame)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        destination = root / "guides" / ("%07d.exr" % frame)
        os.replace(temporary, destination)
        files[str(destination.relative_to(root))] = sha256(destination)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        matrix = camera.matrix_world.copy()
        projection = camera.calc_matrix_camera(depsgraph, x=job["width"], y=job["height"],
                                                scale_x=scene.render.pixel_aspect_x, scale_y=scene.render.pixel_aspect_y)
        metadata = dict(frame=frame, width=job["width"], height=job["height"],
                        near=camera.data.clip_start, far=camera.data.clip_end,
                        camera=camera.name, shot="%s:%s" % (camera.name, marker.frame if marker else "initial"),
                        world=[list(row) for row in matrix], projection=[list(row) for row in projection],
                        beauty_motion_blur=beauty_blur, guide_motion_blur=False)
        destination = root / "metadata" / ("%07d.json" % frame)
        atomic_json(destination, metadata)
        files[str(destination.relative_to(root))] = sha256(destination)
        atomic_json(receipt, dict(job_fingerprint=fingerprint, files=files))
    return 0


if __name__ == "__main__":
    code = capture(sys.argv[sys.argv.index("--") + 1])
    if code:
        raise SystemExit(code)
