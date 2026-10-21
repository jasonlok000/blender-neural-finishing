# SPDX-FileCopyrightText: 2026 Jason Lok
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create the reproducible scene only. This script NEVER renders."""
import math
from pathlib import Path
import sys


def create(destination):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "NeuralFinishingDemo"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 48
    scene.render.use_motion_blur = True
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("Studio World")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.12, 0.18, 1)

    def material(name, color, metallic=0, roughness=0.4):
        value = bpy.data.materials.new(name)
        value.use_nodes = True
        node = value.node_tree.nodes.get("Principled BSDF")
        node.inputs["Base Color"].default_value = (*color, 1)
        node.inputs["Metallic"].default_value = metallic
        node.inputs["Roughness"].default_value = roughness
        return value

    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.data.materials.append(material("Ground", (0.12, 0.14, 0.19)))
    bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 1.2))
    hero = bpy.context.object
    hero.data.materials.append(material("Copper", (0.52, 0.17, 0.055), 0.75, 0.26))
    subdivision = hero.modifiers.new("Smooth", "SUBSURF")
    subdivision.levels = 2
    for polygon in hero.data.polygons:
        polygon.use_smooth = True
    for frame, angle in ((1, -0.4), (48, 0.7)):
        hero.rotation_euler.z = angle
        hero.keyframe_insert("rotation_euler", frame=frame)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(2.1, 0.5, 0.8), radius=0.8)
    bpy.context.object.data.materials.append(material("Ceramic", (0.025, 0.16, 0.32), 0, 0.2))
    for index, (location, energy, color, size) in enumerate((
            ((2, -4, 6), 900, (1.0, 0.8, 0.65), 4),
            ((-4, 0, 3), 700, (0.5, 0.7, 1.0), 3))):
        data = bpy.data.lights.new("Area %s" % index, "AREA")
        data.energy, data.color, data.shape, data.size = energy, color, "DISK", size
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
    cameras = []
    for index, location in enumerate(((5, -8, 4), (-5, -6, 2.8))):
        data = bpy.data.cameras.new("Camera %s" % (index + 1))
        data.lens = 48
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (Vector((0.5, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        cameras.append(camera)
    scene.camera = cameras[0]
    for frame, camera in ((1, cameras[0]), (25, cameras[1])):
        marker = scene.timeline_markers.new("Shot %s" % frame, frame=frame)
        marker.camera = camera
    scene.frame_set(12)
    scene["demo_status"] = "Scene prepared only. No render or GPU inference performed."
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    print("DEMO_SAVED_WITHOUT_RENDER", destination)


if __name__ == "__main__":
    create(sys.argv[sys.argv.index("--") + 1])
