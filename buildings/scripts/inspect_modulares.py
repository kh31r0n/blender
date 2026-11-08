#!/usr/bin/env python3
"""
inspect_modulares.py
--------------------
Inspecciona e importa los 14 modulares oficiales de LDraw OMR,
mide sus dimensiones y renderiza hojas de contacto (4 vistas + planta).
"""

import bpy
import os
import sys
import json
import math
import addon_utils
from mathutils import Vector, Euler

addon_utils.enable("io_scene_importldraw", default_set=True)

OMR_DIR = os.path.expanduser("~/blender/buildings/descargas/omr")
LDRAW_PATH = "/home/kheiron/ldraw"
OUT_DIR = os.path.expanduser("~/blender/buildings/renders/contact_sheets")
os.makedirs(OUT_DIR, exist_ok=True)

MODULARS = [
    ("10182-1", "Cafe_Corner", "10182-1_Cafe_Corner/10182-1.mpd"),
    ("10185-1", "Green_Grocer", "10185-1_Green_Grocer/10185-1.mpd"),
    ("10190-1", "Market_Street", "10190-1_Market_Street/10190-1.mpd"),
    ("10197-1", "Fire_Brigade", "10197-1_Fire_Brigade/10197-1.mpd"),
    ("10218-1", "Pet_Shop", "10218-1_Pet_Shop/10218-1.mpd"),
    ("10224-1", "Town_Hall", "10224-1_Town_Hall/10224-1.mpd"),
    ("10232-1", "Palace_Cinema", "10232-1_Palace_Cinema/10232-1.mpd"),
    ("10243-1", "Parisian_Restaurant", "10243-1_Parisian_Restaurant/10243-1.mpd"),
    ("10246-1", "Detective_s_Office", "10246-1_Detective_s_Office/10246-1.mpd"),
    ("10251-1", "Brick_Bank", "10251-1_Brick_Bank/10251-1.mpd"),
    ("10264-1", "Corner_Garage", "10264-1_Corner_Garage/10264-1.mpd"),
    ("10270-1", "Bookshop", "10270-1_Bookshop/10270-1.mpd"),
    ("10278-1", "Police_Station", "10278-1_Police_Station/10278-1.mpd"),
    ("10297-1", "Boutique_Hotel", "10297-1_Boutique_Hotel/10297-1.mpd"),
]

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    # create default scene collection
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

def setup_lighting_and_camera():
    # World
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.7, 0.75, 0.8, 1.0)
        bg.inputs[1].default_value = 0.8
    
    # Sun
    sun_data = bpy.data.lights.new("Sun", type='SUN')
    sun_data.energy = 3.5
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    sun_obj.rotation_euler = Euler((math.radians(50), math.radians(20), math.radians(-35)), 'XYZ')
    bpy.context.scene.collection.objects.link(sun_obj)
    
    # Camera
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 50
    cam_data.clip_start = 0.1
    cam_data.clip_end = 500
    cam_obj = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Render settings
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 16
    return cam_obj

def point_camera_at(cam, target, cam_pos):
    cam.location = cam_pos
    direction = target - cam_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()

def inspect_and_render_all():
    results = {}
    for set_id, name, rel_path in MODULARS:
        mpd_path = os.path.join(OMR_DIR, rel_path)
        print(f"\n==========================================")
        print(f"Importing {set_id} {name}...")
        print(f"==========================================")
        
        clear_scene()
        
        # Check first 0 FILE
        first_file = ""
        with open(mpd_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("0 FILE "):
                    first_file = line[7:].strip()
                    break
        
        # Import
        bpy.ops.import_scene.importldraw(
            filepath=mpd_path,
            ldrawPath=LDRAW_PATH,
            realScale=100.0,
            linkParts=True,
            addEnvironment=False,
            importCameras=False,
            positionCamera=False,
            useLogoStuds=False
        )
        
        # Remove ground plane if any
        ground = bpy.data.objects.get("LegoGroundPlane")
        if ground:
            bpy.data.objects.remove(ground, do_unlink=True)
            
        # Compute bounding box of meshes
        min_co = Vector((float("inf"), float("inf"), float("inf")))
        max_co = Vector((float("-inf"), float("-inf"), float("-inf")))
        mesh_count = 0
        baseplates = []
        
        for ob in bpy.context.scene.objects:
            if ob.type == "MESH":
                mesh_count += 1
                mat = ob.matrix_world
                ob_min = Vector((float("inf"), float("inf"), float("inf")))
                ob_max = Vector((float("-inf"), float("-inf"), float("-inf")))
                for v in ob.bound_box:
                    wco = mat @ Vector(v)
                    min_co.x = min(min_co.x, wco.x)
                    min_co.y = min(min_co.y, wco.y)
                    min_co.z = min(min_co.z, wco.z)
                    max_co.x = max(max_co.x, wco.x)
                    max_co.y = max(max_co.y, wco.y)
                    max_co.z = max(max_co.z, wco.z)
                    ob_min.x = min(ob_min.x, wco.x)
                    ob_min.y = min(ob_min.y, wco.y)
                    ob_min.z = min(ob_min.z, wco.z)
                    ob_max.x = max(ob_max.x, wco.x)
                    ob_max.y = max(ob_max.y, wco.y)
                    ob_max.z = max(ob_max.z, wco.z)
                if any(bp in ob.name for bp in ["3811", "3857", "43857", "Baseplate"]):
                    baseplates.append({
                        "name": ob.name,
                        "min": [round(c, 4) for c in ob_min],
                        "max": [round(c, 4) for c in ob_max],
                        "size_bu": [round(ob_max.x - ob_min.x, 2), round(ob_max.y - ob_min.y, 2)],
                        "size_studs": [round((ob_max.x - ob_min.x) / 0.8, 1), round((ob_max.y - ob_min.y) / 0.8, 1)]
                    })
        
        extents_bu = max_co - min_co
        extents_studs = Vector((extents_bu.x / 0.8, extents_bu.y / 0.8, extents_bu.z / 0.8))
        center = (min_co + max_co) * 0.5
        
        # Baseplate overall footprint
        bp_min = Vector((float("inf"), float("inf"), float("inf")))
        bp_max = Vector((float("-inf"), float("-inf"), float("-inf")))
        if baseplates:
            for bp in baseplates:
                bp_min.x = min(bp_min.x, bp["min"][0])
                bp_min.y = min(bp_min.y, bp["min"][1])
                bp_min.z = min(bp_min.z, bp["min"][2])
                bp_max.x = max(bp_max.x, bp["max"][0])
                bp_max.y = max(bp_max.y, bp["max"][1])
                bp_max.z = max(bp_max.z, bp["max"][2])
            bp_center = (bp_min + bp_max) * 0.5
            bp_ext = bp_max - bp_min
            bp_footprint_studs = [round(bp_ext.x / 0.8, 1), round(bp_ext.y / 0.8, 1)]
        else:
            bp_footprint_studs = [round(extents_studs.x, 1), round(extents_studs.y, 1)]
            bp_center = center
        
        data = {
            "set_id": set_id,
            "name": name,
            "first_file": first_file,
            "mesh_count": mesh_count,
            "min_bu": [round(c, 4) for c in min_co],
            "max_bu": [round(c, 4) for c in max_co],
            "extents_bu": [round(c, 4) for c in extents_bu],
            "extents_studs": [round(c, 2) for c in extents_studs],
            "height_bu": round(extents_bu.z, 4),
            "baseplate_footprint_studs": bp_footprint_studs,
            "baseplate_center_bu": [round(c, 4) for c in bp_center],
            "baseplates": baseplates
        }
        results[set_id] = data
        print(f"Result for {set_id}: height={data['height_bu']:.2f} BU, BP={bp_footprint_studs} studs, meshes={mesh_count}")
        
        # Setup render
        cam = setup_lighting_and_camera()
        tgt = Vector((bp_center.x, bp_center.y, extents_bu.z * 0.4))
        dist = max(extents_bu.x, extents_bu.y, extents_bu.z) * 1.5
        
        set_render_dir = os.path.join(OUT_DIR, set_id)
        os.makedirs(set_render_dir, exist_ok=True)
        
        # 1. South view (facing from -Y)
        point_camera_at(cam, tgt, Vector((bp_center.x, bp_center.y - dist, extents_bu.z * 0.45)))
        bpy.context.scene.render.filepath = os.path.join(set_render_dir, "view_south.png")
        bpy.ops.render.render(write_still=True)
        
        # 2. North view (facing from +Y)
        point_camera_at(cam, tgt, Vector((bp_center.x, bp_center.y + dist, extents_bu.z * 0.45)))
        bpy.context.scene.render.filepath = os.path.join(set_render_dir, "view_north.png")
        bpy.ops.render.render(write_still=True)
        
        # 3. West view (facing from -X)
        point_camera_at(cam, tgt, Vector((bp_center.x - dist, bp_center.y, extents_bu.z * 0.45)))
        bpy.context.scene.render.filepath = os.path.join(set_render_dir, "view_west.png")
        bpy.ops.render.render(write_still=True)
        
        # 4. East view (facing from +X)
        point_camera_at(cam, tgt, Vector((bp_center.x + dist, bp_center.y, extents_bu.z * 0.45)))
        bpy.context.scene.render.filepath = os.path.join(set_render_dir, "view_east.png")
        bpy.ops.render.render(write_still=True)
        
        # 5. Top view (facing from +Z)
        point_camera_at(cam, Vector((bp_center.x, bp_center.y, 0)), Vector((bp_center.x, bp_center.y, dist * 1.6)))
        bpy.context.scene.render.filepath = os.path.join(set_render_dir, "view_top.png")
        bpy.ops.render.render(write_still=True)
        
    with open(os.path.join(OUT_DIR, "modulars_inspection.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nAll 14 modulars inspected and rendered successfully!")

if __name__ == "__main__":
    inspect_and_render_all()
