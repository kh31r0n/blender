#!/usr/bin/env python3
"""
importar_modulares.py
---------------------
Importa los 14 edificios modulares oficiales desde LDraw OMR y genera la biblioteca
Modulares_OMR.blend con cada modular en su propia colección normalizada:
- Origen en el centro de su placa base (0, 0)
- Superficie superior de la placa base a z = 0
- Fachada principal orientada hacia -Y (Sur)
- Escala unificada del proyecto (1 BU = 10 mm, 0.8 BU/stud)

Uso:
    ~/.local/bin/blender -b --python ~/blender/buildings/scripts/importar_modulares.py
"""

import bpy
import os
import sys
import math
import addon_utils
from mathutils import Vector, Matrix

# Asegurar add-on ImportLDraw
addon_utils.enable("io_scene_importldraw", default_set=True)

OMR_DIR = os.path.expanduser("~/blender/buildings/descargas/omr")
LDRAW_PATH = "/home/kheiron/ldraw"
OUT_BLEND = os.path.expanduser("~/blender/buildings/Modulares_OMR.blend")

# Definición de los 14 modulares oficiales (se excluye 10230-1 Mini)
# (set_id, nombre, ruta_relativa, rotación_normalizacion_grados, tipo)
MODULARS_INFO = [
    ("10182-1", "Cafe_Corner", "10182-1_Cafe_Corner/10182-1.mpd", 0, "corner"),
    ("10185-1", "Green_Grocer", "10185-1_Green_Grocer/10185-1.mpd", 180, "middle"),
    ("10190-1", "Market_Street", "10190-1_Market_Street/10190-1.mpd", 0, "middle"),
    ("10197-1", "Fire_Brigade", "10197-1_Fire_Brigade/10197-1.mpd", 270, "middle"),
    ("10218-1", "Pet_Shop", "10218-1_Pet_Shop/10218-1.mpd", 270, "middle"),
    ("10224-1", "Town_Hall", "10224-1_Town_Hall/10224-1.mpd", 0, "middle"),
    ("10232-1", "Palace_Cinema", "10232-1_Palace_Cinema/10232-1.mpd", 0, "corner"),
    ("10243-1", "Parisian_Restaurant", "10243-1_Parisian_Restaurant/10243-1.mpd", 180, "middle"),
    ("10246-1", "Detective_s_Office", "10246-1_Detective_s_Office/10246-1.mpd", 180, "middle"),
    ("10251-1", "Brick_Bank", "10251-1_Brick_Bank/10251-1.mpd", 0, "corner"),
    ("10264-1", "Corner_Garage", "10264-1_Corner_Garage/10264-1.mpd", 270, "corner"),
    ("10270-1", "Bookshop", "10270-1_Bookshop/10270-1.mpd", 0, "middle"),
    ("10278-1", "Police_Station", "10278-1_Police_Station/10278-1.mpd", 0, "middle"),
    ("10297-1", "Boutique_Hotel", "10297-1_Boutique_Hotel/10297-1.mpd", 0, "corner"),
]

def build_modular_library():
    print("====================================================================")
    print("Construyendo biblioteca Modulares_OMR.blend...")
    print("====================================================================")
    
    # Iniciar archivo limpio
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_scene_importldraw", default_set=True)
    
    # Crear escena y limpiar colecciones
    scene = bpy.context.scene
    main_col = scene.collection
    
    reports = []
    
    for set_id, name, rel_path, rot_deg, btype in MODULARS_INFO:
        mpd_path = os.path.join(OMR_DIR, rel_path)
        if not os.path.exists(mpd_path):
            raise FileNotFoundError(f"No se encontró el archivo MPD: {mpd_path}")
            
        col_name = f"MOD_{set_id}_{name}"
        print(f"\n---> Importando {set_id} ({name}) a colección {col_name}...")
        
        # Colección dedicada para este modular
        mod_col = bpy.data.collections.new(col_name)
        main_col.children.link(mod_col)
        
        # Registrar objetos antes de importar para saber cuáles son nuevos
        objs_before = set(bpy.data.objects)
        
        # Importar con escala exacta: 1 LDU = 0.04 BU (realScale=100.0)
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
        
        new_objs = list(set(bpy.data.objects) - objs_before)
        
        # Eliminar LegoGroundPlane si se genera
        for o in new_objs:
            if o.name == "LegoGroundPlane":
                new_objs.remove(o)
                bpy.data.objects.remove(o, do_unlink=True)
                
        # Mover los nuevos objetos de Scene Collection a mod_col
        for o in new_objs:
            if o.name in main_col.objects:
                main_col.objects.unlink(o)
            if o.name not in mod_col.objects:
                mod_col.objects.link(o)
                
        # Buscar placas base para medir límites
        bp_objs = [o for o in new_objs if o.type == "MESH" and any(b in o.name for b in ["3811", "3857", "43857"])]
        if not bp_objs:
            # fallback si no tiene placa estándar
            bp_objs = [o for o in new_objs if o.type == "MESH" and o.matrix_world.translation.z < 1.0]
            
        min_x = min(min((o.matrix_world @ Vector(v)).x for v in o.bound_box) for o in bp_objs)
        max_x = max(max((o.matrix_world @ Vector(v)).x for v in o.bound_box) for o in bp_objs)
        min_y = min(min((o.matrix_world @ Vector(v)).y for v in o.bound_box) for o in bp_objs)
        max_y = max(max((o.matrix_world @ Vector(v)).y for v in o.bound_box) for o in bp_objs)
        max_z = max(max((o.matrix_world @ Vector(v)).z for v in o.bound_box) for o in bp_objs)
        
        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5
        z_top = max_z - 0.16  # la superficie plana de la placa está a 0.16 BU bajo la cima de los studs
        
        # Matriz de normalización:
        # 1. Traslada para que (cx, cy, z_top) quede en (0, 0, 0)
        # 2. Rota rot_deg alrededor de Z para que el frente dé a -Y
        angle_rad = math.radians(rot_deg)
        M_norm = Matrix.Rotation(angle_rad, 4, "Z") @ Matrix.Translation((-cx, -cy, -z_top))
        
        # Aplicar a los objetos raíz de la importación (padres None)
        roots = [o for o in new_objs if o.parent is None]
        for r in roots:
            r.matrix_world = M_norm @ r.matrix_world
            
        bpy.context.view_layer.update()
        
        # Medir dimensiones finales del edificio normalizado
        norm_min_x = min(min((o.matrix_world @ Vector(v)).x for v in o.bound_box) for o in bp_objs)
        norm_max_x = max(max((o.matrix_world @ Vector(v)).x for v in o.bound_box) for o in bp_objs)
        norm_min_y = min(min((o.matrix_world @ Vector(v)).y for v in o.bound_box) for o in bp_objs)
        norm_max_y = max(max((o.matrix_world @ Vector(v)).y for v in o.bound_box) for o in bp_objs)
        norm_max_z = max(max((o.matrix_world @ Vector(v)).z for v in o.bound_box) for o in bp_objs)
        norm_z_top = norm_max_z - 0.16
        
        # Altura total del modelo
        mesh_objs = [o for o in new_objs if o.type == "MESH"]
        model_max_z = max(max((o.matrix_world @ Vector(v)).z for v in o.bound_box) for o in mesh_objs)
        model_min_z = min(min((o.matrix_world @ Vector(v)).z for v in o.bound_box) for o in mesh_objs)
        total_height = model_max_z - norm_z_top
        
        rep = {
            "set_id": set_id,
            "name": name,
            "type": btype,
            "col": col_name,
            "parts_count": len(mesh_objs),
            "bp_size_studs": (round((norm_max_x - norm_min_x) / 0.8, 1), round((norm_max_y - norm_min_y) / 0.8, 1)),
            "z_top": round(norm_z_top, 4),
            "height_bu": round(total_height, 2)
        }
        reports.append(rep)
        print(f"  -> OK: {rep['parts_count']} piezas, huella={rep['bp_size_studs']} studs, z_top={rep['z_top']}, altura={rep['height_bu']} BU")

    # Verificación de escala: buscar un ladrillo 1x1 o 2x4
    test_part = [o for o in bpy.data.objects if "3005" in o.name and o.type == "MESH"]
    if test_part:
        dim = test_part[0].dimensions
        print(f"\nVerificación de escala (ladrillo 1x1 3005): X={dim.x:.3f} BU (esperado 0.8 BU)")
        assert abs(dim.x - 0.8) < 0.01, f"Error de escala en ladrillo 1x1: {dim.x}"
    
    # Guardar biblioteca
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"\nBiblioteca guardada exitosamente en: {OUT_BLEND}")
    print(f"Total colecciones creadas: {len(reports)}")
    return reports

if __name__ == "__main__":
    build_modular_library()
