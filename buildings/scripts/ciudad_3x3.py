#!/usr/bin/env python3
"""
ciudad_3x3.py
-------------
Genera un barrio completo de 3x3 manzanas LEGO en Blender utilizando
el generador Geometry Nodes "Edificio LEGO" de Edificios_GN_marquesina_v2.blend.

Uso:
    ~/.local/bin/blender -b ~/blender/buildings/Edificios_GN_marquesina_v2.blend -P ~/blender/buildings/scripts/ciudad_3x3.py
"""

import bpy
import json
import math
import os
import random
from mathutils import Vector, Euler

# ---------------------------------------------------------------------------
# Constantes del barrio y la rejilla LEGO
# ---------------------------------------------------------------------------
BU_PER_STUD = 0.8
BLOCK_SIZE_STUDS = 32
BLOCK_SIZE_BU = BLOCK_SIZE_STUDS * BU_PER_STUD       # 25.6 BU
STREET_WIDTH_STUDS = 16
STREET_WIDTH_BU = STREET_WIDTH_STUDS * BU_PER_STUD   # 12.8 BU
TOTAL_AREA_STUDS = 160
TOTAL_AREA_BU = TOTAL_AREA_STUDS * BU_PER_STUD       # 128.0 BU

BLOCK_CENTERS = {
    'A1': (-38.4, -38.4), 'A2': (0.0, -38.4), 'A3': (38.4, -38.4),
    'B1': (-38.4, 0.0),   'B2': (0.0, 0.0),   'B3': (38.4, 0.0),
    'C1': (-38.4, 38.4),  'C2': (0.0, 38.4),  'C3': (38.4, 38.4),
}

DIR_BASE = os.path.expanduser("~/blender/buildings")
OUT_BLEND = os.path.join(DIR_BASE, "Ciudad_3x3.blend")
OUT_JSON = os.path.join(DIR_BASE, "ciudad_3x3_layout.json")
OUT_RENDERS = os.path.join(DIR_BASE, "renders", "ciudad_3x3")

MASTER_SEED = 2026

# ---------------------------------------------------------------------------
# Esquemas de color (Mecabricks / Nitro)
# ---------------------------------------------------------------------------
COLOR_SCHEMES = {
    "Nitro hotel": {
        "Pared": "LEGO 1 White", "Molduras": "LEGO 1 White", "Tejado": "LEGO 26 Black",
        "Azotea": "LEGO 199 Dark Bluish Grey", "Puerta": "LEGO 26 Black"
    },
    "Sandstone": {
        "Pared": "LEGO 5 Tan", "Molduras": "LEGO 138 Dark Tan", "Tejado": "LEGO 138 Dark Tan",
        "Azotea": "LEGO 199 Dark Bluish Grey", "Puerta": "LEGO 192 Reddish Brown"
    },
    "Red brick": {
        "Pared": "LEGO 154 Dark Red", "Molduras": "LEGO 5 Tan", "Tejado": "LEGO 199 Dark Bluish Grey",
        "Azotea": "LEGO 194 Light Bluish Grey", "Puerta": "LEGO 192 Reddish Brown"
    },
    "Brown brick": {
        "Pared": "LEGO 192 Reddish Brown", "Molduras": "LEGO 194 Light Bluish Grey", "Tejado": "LEGO 26 Black",
        "Azotea": "LEGO 194 Light Bluish Grey", "Puerta": "LEGO 154 Dark Red"
    },
    "Sand green": {
        "Pared": "LEGO 151 Sand Green", "Molduras": "LEGO 1 White", "Tejado": "LEGO 199 Dark Bluish Grey",
        "Azotea": "LEGO 194 Light Bluish Grey", "Puerta": "LEGO 154 Dark Red"
    },
    "Sand blue": {
        "Pared": "LEGO 135 Sand Blue", "Molduras": "LEGO 1 White", "Tejado": "LEGO 140 Dark Blue",
        "Azotea": "LEGO 199 Dark Bluish Grey", "Puerta": "LEGO 140 Dark Blue"
    },
    "Nougat": {
        "Pared": "LEGO 283 Light Nougat", "Molduras": "LEGO 312 Medium Nougat", "Tejado": "LEGO 192 Reddish Brown",
        "Azotea": "LEGO 194 Light Bluish Grey", "Puerta": "LEGO 192 Reddish Brown"
    },
    "Olive": {
        "Pared": "LEGO 330 Olive Green", "Molduras": "LEGO 5 Tan", "Tejado": "LEGO 26 Black",
        "Azotea": "LEGO 199 Dark Bluish Grey", "Puerta": "LEGO 28 Dark Green"
    },
    "Grey office": {
        "Pared": "LEGO 194 Light Bluish Grey", "Molduras": "LEGO 199 Dark Bluish Grey", "Tejado": "LEGO 199 Dark Bluish Grey",
        "Azotea": "LEGO 199 Dark Bluish Grey", "Puerta": "LEGO 26 Black"
    },
}

# ---------------------------------------------------------------------------
# Definición de los 27 edificios (3 por manzana)
# ---------------------------------------------------------------------------
BUILDINGS_DATA = [
    # Manzana A1 (Suroeste: fachadas a Sur y Norte)
    {"block": "A1", "lot": "01", "archetype": "Shop", "pisos": 4, "ancho": 14, "fondo": 12, "rot_deg": 0, "u_min": 1, "v_min": 1, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "A1", "lot": "02", "archetype": "Townhouse", "pisos": 3, "ancho": 12, "fondo": 12, "rot_deg": 0, "u_min": 18, "v_min": 1, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Sandstone"},
    {"block": "A1", "lot": "03", "archetype": "Apartment", "pisos": 6, "ancho": 16, "fondo": 12, "rot_deg": 180, "u_min": 1, "v_min": 18, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sand green"},

    # Manzana A2 (Sur centro: fachadas a Sur y Norte)
    {"block": "A2", "lot": "01", "archetype": "Apartment", "pisos": 7, "ancho": 16, "fondo": 12, "rot_deg": 0, "u_min": 1, "v_min": 1, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Brown brick"},
    {"block": "A2", "lot": "02", "archetype": "Shop", "pisos": 5, "ancho": 12, "fondo": 12, "rot_deg": 0, "u_min": 19, "v_min": 1, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Nougat"},
    {"block": "A2", "lot": "03", "archetype": "Townhouse", "pisos": 4, "ancho": 10, "fondo": 12, "rot_deg": 180, "u_min": 6, "v_min": 18, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Olive"},

    # Manzana A3 (Sureste: fachadas a Sur y Norte)
    {"block": "A3", "lot": "01", "archetype": "Shop", "pisos": 3, "ancho": 12, "fondo": 12, "rot_deg": 0, "u_min": 1, "v_min": 1, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Sand blue"},
    {"block": "A3", "lot": "02", "archetype": "Townhouse", "pisos": 2, "ancho": 10, "fondo": 12, "rot_deg": 0, "u_min": 16, "v_min": 1, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Red brick"},
    {"block": "A3", "lot": "03", "archetype": "Apartment", "pisos": 8, "ancho": 16, "fondo": 12, "rot_deg": 180, "u_min": 12, "v_min": 18, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Grey office"},

    # Manzana B1 (Oeste centro: fachadas a Oeste, Este y Norte)
    {"block": "B1", "lot": "01", "archetype": "Office", "pisos": 8, "ancho": 18, "fondo": 12, "rot_deg": 270, "u_min": 1, "v_min": 1, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Grey office"},
    {"block": "B1", "lot": "02", "archetype": "Apartment", "pisos": 6, "ancho": 14, "fondo": 12, "rot_deg": 90, "u_min": 18, "v_min": 1, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},
    {"block": "B1", "lot": "03", "archetype": "Shop", "pisos": 5, "ancho": 12, "fondo": 12, "rot_deg": 180, "u_min": 16, "v_min": 18, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Olive"},

    # Manzana B2 (Centro: HOTEL LANDMARK en fachada Sur, Office y Townhouse en Norte)
    {"block": "B2", "lot": "01", "archetype": "Hotel", "pisos": 15, "ancho": 18, "fondo": 14, "rot_deg": 0, "u_min": 7, "v_min": 1, "pb": "Entrada hotel", "rm": "Alero con pináculos", "scheme": "Nitro hotel"},
    {"block": "B2", "lot": "02", "archetype": "Office", "pisos": 10, "ancho": 16, "fondo": 12, "rot_deg": 180, "u_min": 1, "v_min": 18, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Sand blue"},
    {"block": "B2", "lot": "03", "archetype": "Townhouse", "pisos": 5, "ancho": 10, "fondo": 12, "rot_deg": 180, "u_min": 20, "v_min": 18, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Nougat"},

    # Manzana B3 (Este centro: fachadas a Este, Oeste y Norte)
    {"block": "B3", "lot": "01", "archetype": "Apartment", "pisos": 9, "ancho": 16, "fondo": 12, "rot_deg": 90, "u_min": 18, "v_min": 1, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sand green"},
    {"block": "B3", "lot": "02", "archetype": "Shop", "pisos": 4, "ancho": 14, "fondo": 12, "rot_deg": 270, "u_min": 1, "v_min": 1, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Brown brick"},
    {"block": "B3", "lot": "03", "archetype": "Townhouse", "pisos": 3, "ancho": 10, "fondo": 12, "rot_deg": 180, "u_min": 1, "v_min": 18, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},

    # Manzana C1 (Noroeste: fachadas a Norte y Sur)
    {"block": "C1", "lot": "01", "archetype": "Office", "pisos": 7, "ancho": 16, "fondo": 12, "rot_deg": 180, "u_min": 1, "v_min": 18, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Nitro hotel"},
    {"block": "C1", "lot": "02", "archetype": "Shop", "pisos": 3, "ancho": 12, "fondo": 12, "rot_deg": 180, "u_min": 19, "v_min": 18, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "C1", "lot": "03", "archetype": "Apartment", "pisos": 5, "ancho": 14, "fondo": 12, "rot_deg": 0, "u_min": 1, "v_min": 1, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Nougat"},

    # Manzana C2 (Norte centro: fachadas a Norte y Sur)
    {"block": "C2", "lot": "01", "archetype": "Office", "pisos": 12, "ancho": 18, "fondo": 12, "rot_deg": 180, "u_min": 7, "v_min": 18, "pb": "Escaparates", "rm": "Azotea", "scheme": "Grey office"},
    {"block": "C2", "lot": "02", "archetype": "Apartment", "pisos": 7, "ancho": 14, "fondo": 12, "rot_deg": 0, "u_min": 1, "v_min": 1, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Olive"},
    {"block": "C2", "lot": "03", "archetype": "Townhouse", "pisos": 2, "ancho": 10, "fondo": 12, "rot_deg": 0, "u_min": 20, "v_min": 1, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Sand blue"},

    # Manzana C3 (Noreste: fachadas a Norte y Sur)
    {"block": "C3", "lot": "01", "archetype": "Shop", "pisos": 6, "ancho": 14, "fondo": 12, "rot_deg": 180, "u_min": 1, "v_min": 18, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Nitro hotel"},
    {"block": "C3", "lot": "02", "archetype": "Townhouse", "pisos": 4, "ancho": 10, "fondo": 12, "rot_deg": 180, "u_min": 20, "v_min": 18, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Brown brick"},
    {"block": "C3", "lot": "03", "archetype": "Apartment", "pisos": 8, "ancho": 14, "fondo": 12, "rot_deg": 0, "u_min": 8, "v_min": 1, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sand green"},
]

def setup_ground_and_pads():
    """Configura el plano del suelo y los zócalos de las manzanas."""
    mat_suelo = bpy.data.materials.get("LEGO 199 Dark Bluish Grey")
    mat_zocalo = bpy.data.materials.get("LEGO 194 Light Bluish Grey")
    if not mat_suelo or not mat_zocalo:
        raise RuntimeError("Faltan materiales base para suelo/zócalos")

    # 1. Suelo general (calles a z = -0.01)
    suelo = bpy.data.objects.get("Suelo")
    if not suelo:
        mesh = bpy.data.meshes.new("Mesh_Suelo")
        suelo = bpy.data.objects.new("Suelo", mesh)
        bpy.context.scene.collection.objects.link(suelo)
    
    # Crear geometría plana de 150 x 150 BU centrada en (0, 0, -0.01)
    half_size = 75.0
    verts = [(-half_size, -half_size, -0.01), (half_size, -half_size, -0.01),
             (half_size, half_size, -0.01), (-half_size, half_size, -0.01)]
    faces = [(0, 1, 2, 3)]
    suelo.data.clear_geometry()
    suelo.data.from_pydata(verts, [], faces)
    suelo.data.update()
    suelo.location = (0, 0, 0)
    suelo.data.materials.clear()
    suelo.data.materials.append(mat_suelo)

    # 2. Zócalos de manzana (32 x 32 studs = 25.6 x 25.6 BU, z = 0.0)
    col_suelos = bpy.data.collections.get("Suelo_Manzanas")
    if not col_suelos:
        col_suelos = bpy.data.collections.new("Suelo_Manzanas")
        bpy.context.scene.collection.children.link(col_suelos)

    pad_half = BLOCK_SIZE_BU / 2.0  # 12.8 BU
    for block_name, (cx, cy) in BLOCK_CENTERS.items():
        pad_name = f"Zocalo_{block_name}"
        pad_ob = bpy.data.objects.get(pad_name)
        if not pad_ob:
            pad_mesh = bpy.data.meshes.new(f"Mesh_{pad_name}")
            pad_ob = bpy.data.objects.new(pad_name, pad_mesh)
            col_suelos.objects.link(pad_ob)
        p_verts = [(-pad_half, -pad_half, 0.0), (pad_half, -pad_half, 0.0),
                   (pad_half, pad_half, 0.0), (-pad_half, pad_half, 0.0)]
        pad_ob.data.clear_geometry()
        pad_ob.data.from_pydata(p_verts, [], [(0, 1, 2, 3)])
        pad_ob.data.update()
        pad_ob.location = (cx, cy, 0.0)
        pad_ob.data.materials.clear()
        pad_ob.data.materials.append(mat_zocalo)

def setup_cameras():
    """Crea y posiciona las 6 cámaras especificadas."""
    cams_info = [
        ("Camara", (-85.0, -125.0, 75.0), (0.0, 0.0, 15.0), 35.0, False, 0.0),
        ("Cam_Planta", (0.0, 0.0, 120.0), (0.0, 0.0, 0.0), 50.0, True, 250.0),
        ("Cam_Calle_1", (-58.0, -24.0, 1.8), (58.0, -24.0, 2.5), 24.0, False, 0.0),
        ("Cam_Calle_2", (-24.0, -58.0, 1.8), (-24.0, 58.0, 2.5), 24.0, False, 0.0),
        ("Cam_Calle_3", (-22.0, -22.0, 2.2), (-5.0, -5.0, 12.0), 24.0, False, 0.0),
        ("Cam_Centro", (-28.0, -32.0, 28.0), (0.0, 0.0, 15.0), 30.0, False, 0.0),
    ]

    for name, pos, target, lens, is_ortho, ortho_scale in cams_info:
        cam_ob = bpy.data.objects.get(name)
        if not cam_ob:
            cam_data = bpy.data.cameras.new(name)
            cam_ob = bpy.data.objects.new(name, cam_data)
            bpy.context.scene.collection.objects.link(cam_ob)
        else:
            cam_data = cam_ob.data

        cam_ob.location = pos
        # Orientar hacia target
        v_dir = Vector(target) - Vector(pos)
        cam_ob.rotation_euler = v_dir.to_track_quat('-Z', 'Y').to_euler()

        if is_ortho:
            cam_data.type = 'ORTHO'
            cam_data.ortho_scale = ortho_scale
            # Rotación fija cenital
            cam_ob.rotation_euler = Euler((0, 0, 0), 'XYZ')
        else:
            cam_data.type = 'PERSP'
            cam_data.lens = lens

    # Asegurar que 'Camara' es la cámara activa de la escena
    bpy.context.scene.camera = bpy.data.objects["Camara"]

def build_city():
    """Construye todos los edificios del barrio usando 'Edificio LEGO'."""
    ng = bpy.data.node_groups.get("Edificio LEGO")
    if not ng:
        raise RuntimeError("No se encontró el grupo de Geometry Nodes 'Edificio LEGO'")

    # Obtener mapeo de nombres de sockets a identificadores
    sock_map = {}
    for item in ng.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
            sock_map[item.name] = item.identifier

    # Eliminar edificios de ejemplo anteriores si existen
    for old_name in ("Hotel", "Tienda", "Casa"):
        ob = bpy.data.objects.get(old_name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    # Colección principal Ciudad
    col_ciudad = bpy.data.collections.get("Ciudad")
    if not col_ciudad:
        col_ciudad = bpy.data.collections.new("Ciudad")
        bpy.context.scene.collection.children.link(col_ciudad)

    block_cols = {}
    for b_id in BLOCK_CENTERS.keys():
        col_b = bpy.data.collections.get(f"Manzana_{b_id}")
        if not col_b:
            col_b = bpy.data.collections.new(f"Manzana_{b_id}")
            col_ciudad.children.link(col_b)
        block_cols[b_id] = col_b

    rng = random.Random(MASTER_SEED)
    layout_export = []

    print("\n--- INSTANCIANDO EDIFICIOS ---")
    for idx, b in enumerate(BUILDINGS_DATA):
        b_name = f"{b['block']}_{b['lot']}_{b['archetype']}"
        rot_deg = b['rot_deg'] % 360
        ancho = b['ancho']
        fondo = b['fondo']
        u_min = b['u_min']
        v_min = b['v_min']
        is_hotel = (b['pb'] == "Entrada hotel")
        vuelo_marq = 4 if is_hotel else 0

        # Calcular dimensiones en la rejilla de la manzana
        if rot_deg in (0, 180):
            u_max = u_min + ancho
            v_max = v_min + fondo
        else:
            u_max = u_min + fondo
            v_max = v_min + ancho

        bc_x, bc_y = BLOCK_CENTERS[b['block']]
        block_min_x = bc_x - 16 * BU_PER_STUD
        block_min_y = bc_y - 16 * BU_PER_STUD

        u_center = (u_min + u_max) / 2.0
        v_center = (v_min + v_max) / 2.0

        world_x = block_min_x + u_center * BU_PER_STUD
        world_y = block_min_y + v_center * BU_PER_STUD
        rot_z_rad = math.radians(rot_deg)

        # Variaciones deterministas
        seed_val = MASTER_SEED * 100 + (idx + 1)
        ciegas_val = round(rng.uniform(0.05, 0.25), 3)
        jardineras_val = round(rng.uniform(0.15, 0.45), 3)
        luces_val = 0.0

        # Crear o reutilizar objeto
        ob = bpy.data.objects.get(b_name)
        if not ob:
            mesh = bpy.data.meshes.new(f"Mesh_{b_name}")
            ob = bpy.data.objects.new(b_name, mesh)
            block_cols[b['block']].objects.link(ob)

        ob.location = (world_x, world_y, 0.0)
        ob.rotation_euler = Euler((0, 0, rot_z_rad), 'XYZ')

        # Custom properties
        ob["archetype"] = b['archetype']
        ob["block"] = b['block']
        ob["lot"] = b['lot']
        ob["scheme"] = b['scheme']

        # Configurar modificador Geometry Nodes
        mod = ob.modifiers.get("Edificio LEGO")
        if not mod:
            mod = ob.modifiers.new("Edificio LEGO", 'NODES')
            mod.node_group = ng

        # Parámetros del modificador
        scheme_info = COLOR_SCHEMES[b['scheme']]
        mod_params = {
            "Pisos": b['pisos'],
            "Ancho (studs)": ancho,
            "Fondo (studs)": fondo,
            "Planta baja": b['pb'],
            "Remate": b['rm'],
            "Semilla": seed_val,
            "Ventanas ciegas": ciegas_val,
            "Jardineras": jardineras_val,
            "Luces encendidas": luces_val,
            "Realizar instancias": False,
            "Pared": bpy.data.materials[scheme_info["Pared"]],
            "Molduras": bpy.data.materials[scheme_info["Molduras"]],
            "Tejado": bpy.data.materials[scheme_info["Tejado"]],
            "Azotea": bpy.data.materials[scheme_info["Azotea"]],
            "Puerta": bpy.data.materials[scheme_info["Puerta"]],
        }

        if is_hotel:
            mod_params["Ancho marquesina (studs)"] = min(ancho, 18)
            mod_params["Vuelo marquesina (studs)"] = 4
            mod_params["Altura marquesina (placas)"] = 1
            mod_params["Pináculos superiores"] = 3
            mod_params["Separación pináculos (studs)"] = 0

        for k, v in mod_params.items():
            ident = sock_map.get(k)
            if not ident:
                raise KeyError(f"Socket desconocido en nodo: {k}")
            getattr(mod.properties.inputs, ident).value = v

        ob.update_tag()

        layout_export.append({
            "name": b_name,
            "block": b['block'],
            "lot": b['lot'],
            "archetype": b['archetype'],
            "pisos": b['pisos'],
            "ancho_studs": ancho,
            "fondo_studs": fondo,
            "rot_deg": rot_deg,
            "planta_baja": b['pb'],
            "remate": b['rm'],
            "scheme": b['scheme'],
            "seed": seed_val,
            "ciegas": ciegas_val,
            "jardineras": jardineras_val,
            "location_bu": [round(world_x, 3), round(world_y, 3), 0.0],
        })

    bpy.context.view_layer.update()
    return layout_export

def validate_city(layout_export):
    """Comprueba advertencias, instancias y ausencia de solapamiento en depsgraph."""
    print("\n--- VALIDACIÓN ESTRUCTURAL ---")
    depsgraph = bpy.context.evaluated_depsgraph_get()

    total_instances = 0
    warnings_found = 0
    bboxes = {}

    for item in layout_export:
        b_name = item["name"]
        ob = bpy.data.objects[b_name]
        mod = ob.modifiers.get("Edificio LEGO")
        
        # 1. Comprobación de advertencias
        if hasattr(mod, 'node_warnings') and mod.node_warnings:
            print(f"ADVERTENCIA en {b_name}: {mod.node_warnings}")
            warnings_found += 1

        # 2. Extensión y conteo de instancias
        b_insts = 0
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        for inst in depsgraph.object_instances:
            if inst.is_instance and inst.parent and inst.parent.original == ob:
                b_insts += 1
                inst_mat = inst.matrix_world.copy()
                for pt in inst.object.bound_box:
                    wpt = inst_mat @ Vector(pt)
                    min_x = min(min_x, wpt.x)
                    max_x = max(max_x, wpt.x)
                    min_y = min(min_y, wpt.y)
                    max_y = max(max_y, wpt.y)
                    min_z = min(min_z, wpt.z)
                    max_z = max(max_z, wpt.z)

        total_instances += b_insts
        bboxes[b_name] = (min_x, max_x, min_y, max_y, min_z, max_z)
        print(f"  {b_name:20s}: {b_insts:5d} inst | X:[{min_x:6.2f}, {max_x:6.2f}] Y:[{min_y:6.2f}, {max_y:6.2f}] Z:[{min_z:5.2f}, {max_z:5.2f}]")

    print(f"\nTotal instancias evaluadas: {total_instances}")
    assert total_instances > 0, "No se generaron instancias"
    assert total_instances < 80000, f"Demasiadas instancias: {total_instances} >= 80000"
    assert warnings_found == 0, f"Se encontraron {warnings_found} advertencias en nodos"

    # 3. Comprobación de solapamientos entre pares de edificios
    overlaps = 0
    names = list(bboxes.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n1, n2 = names[i], names[j]
            b1, b2 = bboxes[n1], bboxes[n2]
            # Solapamiento XY (con tolerancia 0.01 BU)
            dx = min(b1[1], b2[1]) - max(b1[0], b2[0])
            dy = min(b1[3], b2[3]) - max(b1[2], b2[2])
            if dx > 0.01 and dy > 0.01:
                print(f"COLISIÓN DETECTADA entre {n1} y {n2}: dx={dx:.3f}, dy={dy:.3f}")
                overlaps += 1

    assert overlaps == 0, f"Se detectaron {overlaps} colisiones entre edificios"
    print("Verificación de colisiones superada: 0 colisiones en los 27 edificios.")
    return total_instances

def render_cameras():
    """Renderiza las 6 vistas de cámara en ~/blender/buildings/renders/ciudad_3x3/."""
    os.makedirs(OUT_RENDERS, exist_ok=True)
    scene = bpy.context.scene

    scene.render.engine = 'BLENDER_EEVEE'
    scene.view_settings.view_transform = 'AgX'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    cams = [
        ("Camara", "render_01_overview.png"),
        ("Cam_Planta", "render_02_planta.png"),
        ("Cam_Calle_1", "render_03_calle_1.png"),
        ("Cam_Calle_2", "render_04_calle_2.png"),
        ("Cam_Calle_3", "render_05_calle_3.png"),
        ("Cam_Centro", "render_06_centro.png"),
    ]

    print("\n--- RENDERIZANDO CÁMARAS ---")
    for cam_name, filename in cams:
        cam_ob = bpy.data.objects.get(cam_name)
        if not cam_ob:
            print(f"Cámara no encontrada: {cam_name}")
            continue
        scene.camera = cam_ob
        filepath = os.path.join(OUT_RENDERS, filename)
        scene.render.filepath = filepath
        print(f"Renderizando {cam_name} -> {filepath}...")
        bpy.ops.render.render(write_still=True)
        print(f"  Guardado {filepath}")

def main():
    print("=== INICIANDO CONSTRUCCIÓN DE LA CIUDAD 3x3 LEGO ===")
    setup_ground_and_pads()
    setup_cameras()
    layout_export = build_city()
    validate_city(layout_export)

    # Exportar layout a JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(layout_export, f, indent=2, ensure_ascii=False)
    print(f"\nLayout exportado a: {OUT_JSON}")

    # Guardar nuevo archivo blend sin tocar el original
    print(f"\nGuardando archivo principal en: {OUT_BLEND}")
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("Archivo .blend guardado correctamente.")

    # Renderizar todas las cámaras
    render_cameras()
    print("\n=== PROCESO COMPLETADO CON ÉXITO ===")

if __name__ == "__main__":
    main()
