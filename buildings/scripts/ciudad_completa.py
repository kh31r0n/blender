#!/usr/bin/env python3
"""
ciudad_completa.py
------------------
Construye el barrio completo de 3x3 manzanas LEGO en Blender combinando:
1. "Edificio LEGO": generador Geometry Nodes (Edificios_GN_marquesina_v2.blend)
2. 14 edificios modulares oficiales en LDraw desde Modulares_OMR.blend (vinculados relativos)
3. Nitrody City en la manzana central B2 desde Nitro.blend (vinculada relativa)

Uso:
    ~/.local/bin/blender -b ~/blender/buildings/Edificios_GN_marquesina_v2.blend -P ~/blender/buildings/scripts/ciudad_completa.py
"""

import bpy
import json
import math
import os
import random
import time
from mathutils import Vector, Euler, Matrix

# ---------------------------------------------------------------------------
# Constantes de la rejilla LEGO y dimensiones del barrio
# ---------------------------------------------------------------------------
BU_PER_STUD = 0.8                   # 1 stud = 0.8 BU (10 mm)
BLOCK_STUDS_X = 96                  # 96 studs = 76.8 BU
BLOCK_STUDS_Y = 64                  # 64 studs = 51.2 BU
BLOCK_BU_X = BLOCK_STUDS_X * BU_PER_STUD   # 76.8 BU
BLOCK_BU_Y = BLOCK_STUDS_Y * BU_PER_STUD   # 51.2 BU
STREET_STUDS = 32                   # Calle estándar = 32 studs (25.6 BU)
STREET_BU = STREET_STUDS * BU_PER_STUD     # 25.6 BU

PITCH_X = BLOCK_BU_X + STREET_BU    # 102.4 BU
PITCH_Y = BLOCK_BU_Y + STREET_BU    # 76.8 BU

BLOCK_CENTERS = {
    'A1': (-PITCH_X, -PITCH_Y), 'A2': (0.0, -PITCH_Y), 'A3': (PITCH_X, -PITCH_Y),
    'B1': (-PITCH_X,      0.0), 'B2': (0.0,      0.0), 'B3': (PITCH_X,      0.0),
    'C1': (-PITCH_X,  PITCH_Y), 'C2': (0.0,  PITCH_Y), 'C3': (PITCH_X,  PITCH_Y),
}

DIR_BASE = os.path.expanduser("~/blender/buildings")
OUT_BLEND = os.path.join(DIR_BASE, "Ciudad_completa.blend")
OUT_JSON = os.path.join(DIR_BASE, "ciudad_completa_layout.json")
OUT_RENDERS = os.path.join(DIR_BASE, "renders", "ciudad_completa")
LIB_MODULARS = "//Modulares_OMR.blend"
LIB_NITRO = "//Nitro.blend"

MASTER_SEED = 2026

# Paletas de color aprobadas (Mecabricks / Nitro)
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
# Estructura de datos completa del layout del barrio
# ---------------------------------------------------------------------------
# Lotes modulares asignados estratégicamente en las calles que rodean B2
# Rotaciones de modulares respecto a su fachada normalizada (-Y):
# - Fachada a Sur (-Y): rot_deg = 0
# - Fachada a Norte (+Y): rot_deg = 180
# - Fachada a Oeste (-X): rot_deg = 270
# - Fachada a Este (+X): rot_deg = 90
MODULAR_ASSIGNMENTS = {
    # Manzana C2 fila Sur (frente a B2, mirando al Sur)
    "C2_S1": {"col": "MOD_10182-1_Cafe_Corner", "rot_deg": 270, "btype": "corner", "desc": "Café Corner"},
    "C2_S2": {"col": "MOD_10224-1_Town_Hall", "rot_deg": 0, "btype": "middle", "desc": "Town Hall"},
    "C2_S3": {"col": "MOD_10232-1_Palace_Cinema", "rot_deg": 0, "btype": "corner", "desc": "Palace Cinema"},
    # Manzana A2 fila Norte (frente a B2, mirando al Norte)
    "A2_N1": {"col": "MOD_10251-1_Brick_Bank", "rot_deg": 180, "btype": "corner", "desc": "Brick Bank"},
    "A2_N2": {"col": "MOD_10197-1_Fire_Brigade", "rot_deg": 180, "btype": "middle", "desc": "Fire Brigade"},
    "A2_N3": {"col": "MOD_10264-1_Corner_Garage", "rot_deg": 90, "btype": "corner", "desc": "Corner Garage"},
    # Manzana B1 (avenida oeste)
    "B1_S3": {"col": "MOD_10297-1_Boutique_Hotel", "rot_deg": 0, "btype": "corner", "desc": "Boutique Hotel"},
    "B1_S2": {"col": "MOD_10270-1_Bookshop", "rot_deg": 0, "btype": "middle", "desc": "Bookshop"},
    "B1_N2": {"col": "MOD_10278-1_Police_Station", "rot_deg": 180, "btype": "middle", "desc": "Police Station"},
    # Manzana B3 (avenida este)
    "B3_S2": {"col": "MOD_10218-1_Pet_Shop", "rot_deg": 0, "btype": "middle", "desc": "Pet Shop"},
    "B3_N2": {"col": "MOD_10190-1_Market_Street", "rot_deg": 180, "btype": "middle", "desc": "Market Street"},
    # Manzana A2 fila Sur (continuación manzana oficial)
    "A2_S2": {"col": "MOD_10185-1_Green_Grocer", "rot_deg": 0, "btype": "middle", "desc": "Green Grocer"},
    "A2_S3": {"col": "MOD_10243-1_Parisian_Restaurant", "rot_deg": 0, "btype": "middle", "desc": "Parisian Restaurant"},
    # Manzana C2 fila Norte (continuación manzana oficial)
    "C2_N2": {"col": "MOD_10246-1_Detective_s_Office", "rot_deg": 180, "btype": "middle", "desc": "Detective's Office"},
}

# Lotes generados (34 lotes restantes en manzanas A1, A2, A3, B1, B3, C1, C2, C3)
GENERATED_LOTS = [
    # Manzana A1
    {"block": "A1", "lot": "S1", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "A1", "lot": "S2", "archetype": "Shop", "pisos": 4, "ancho": 20, "fondo": 16, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Sandstone"},
    {"block": "A1", "lot": "S3", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Nougat", "offset_x": -6.0},
        {"sub": "B", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sand blue", "offset_x": 6.0}
    ]},
    {"block": "A1", "lot": "N1", "archetype": "Office", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Escaparates", "rm": "Azotea", "scheme": "Grey office"},
    {"block": "A1", "lot": "N2", "archetype": "Apartment", "pisos": 5, "ancho": 22, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Olive"},
    {"block": "A1", "lot": "N3", "archetype": "Shop", "pisos": 4, "ancho": 18, "fondo": 16, "rot_deg": 180, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Brown brick"},

    # Manzana A2 (lote S1 restante)
    {"block": "A2", "lot": "S1", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 4, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sand green", "offset_x": -6.0},
        {"sub": "B", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Sandstone", "offset_x": 6.0}
    ]},

    # Manzana A3
    {"block": "A3", "lot": "S1", "archetype": "Shop", "pisos": 4, "ancho": 22, "fondo": 16, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "A3", "lot": "S2", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Nougat", "offset_x": -6.0},
        {"sub": "B", "pisos": 2, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Brown brick", "offset_x": 6.0}
    ]},
    {"block": "A3", "lot": "S3", "archetype": "Apartment", "pisos": 7, "ancho": 26, "fondo": 20, "rot_deg": 0, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sand blue"},
    {"block": "A3", "lot": "N1", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},
    {"block": "A3", "lot": "N2", "archetype": "Office", "pisos": 8, "ancho": 26, "fondo": 20, "rot_deg": 180, "pb": "Escaparates", "rm": "Azotea", "scheme": "Grey office"},
    {"block": "A3", "lot": "N3", "archetype": "Hotel", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Entrada hotel", "rm": "Alero con pináculos", "scheme": "Nitro hotel"},

    # Manzana B1 (lotes restantes S1, N1, N3)
    {"block": "B1", "lot": "S1", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Olive"},
    {"block": "B1", "lot": "N1", "archetype": "Shop", "pisos": 5, "ancho": 22, "fondo": 16, "rot_deg": 180, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Sand green"},
    {"block": "B1", "lot": "N3", "archetype": "Office", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Escaparates", "rm": "Azotea", "scheme": "Grey office"},

    # Manzana B3 (lotes restantes S1, S3, N1, N3)
    {"block": "B3", "lot": "S1", "archetype": "Shop", "pisos": 5, "ancho": 22, "fondo": 16, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "B3", "lot": "S3", "archetype": "Apartment", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},
    {"block": "B3", "lot": "N1", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 4, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Brown brick", "offset_x": -6.0},
        {"sub": "B", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Nougat", "offset_x": 6.0}
    ]},
    {"block": "B3", "lot": "N3", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sand blue"},

    # Manzana C1
    {"block": "C1", "lot": "S1", "archetype": "Office", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Grey office"},
    {"block": "C1", "lot": "S2", "archetype": "Shop", "pisos": 4, "ancho": 20, "fondo": 16, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Red brick"},
    {"block": "C1", "lot": "S3", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},
    {"block": "C1", "lot": "N1", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sand green"},
    {"block": "C1", "lot": "N2", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Olive", "offset_x": -6.0},
        {"sub": "B", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Brown brick", "offset_x": 6.0}
    ]},
    {"block": "C1", "lot": "N3", "archetype": "Hotel", "pisos": 7, "ancho": 22, "fondo": 18, "rot_deg": 180, "pb": "Entrada hotel", "rm": "Alero con pináculos", "scheme": "Nougat"},

    # Manzana C2 (lotes restantes N1, N3)
    {"block": "C2", "lot": "N1", "archetype": "Shop", "pisos": 5, "ancho": 22, "fondo": 16, "rot_deg": 180, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Sand blue"},
    {"block": "C2", "lot": "N3", "archetype": "Apartment", "pisos": 6, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sandstone"},

    # Manzana C3
    {"block": "C3", "lot": "S1", "archetype": "Hotel", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 0, "pb": "Entrada hotel", "rm": "Alero con pináculos", "scheme": "Red brick"},
    {"block": "C3", "lot": "S2", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 4, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sand green", "offset_x": -6.0},
        {"sub": "B", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 0, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Brown brick", "offset_x": 6.0}
    ]},
    {"block": "C3", "lot": "S3", "archetype": "Office", "pisos": 8, "ancho": 26, "fondo": 20, "rot_deg": 0, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Grey office"},
    {"block": "C3", "lot": "N1", "archetype": "Apartment", "pisos": 7, "ancho": 24, "fondo": 18, "rot_deg": 180, "pb": "Puerta simple", "rm": "Alero con pináculos", "scheme": "Sandstone"},
    {"block": "C3", "lot": "N2", "archetype": "Shop", "pisos": 4, "ancho": 20, "fondo": 16, "rot_deg": 180, "pb": "Escaparates", "rm": "Cornisa plana", "scheme": "Olive"},
    {"block": "C3", "lot": "N3", "archetype": "Townhouse_Pair", "townhouses": [
        {"sub": "A", "pisos": 3, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Azotea", "scheme": "Nougat", "offset_x": -6.0},
        {"sub": "B", "pisos": 2, "ancho": 12, "fondo": 16, "rot_deg": 180, "pb": "Puerta simple", "rm": "Cornisa plana", "scheme": "Sand blue", "offset_x": 6.0}
    ]},
]

# ---------------------------------------------------------------------------
# Funciones auxiliares geométricas
# ---------------------------------------------------------------------------
def get_lot_center_bu(block_id, lot_id):
    """Calcula las coordenadas de mundo del centro de un lote 32x32."""
    bc_x, bc_y = BLOCK_CENTERS[block_id]
    # Lote ID: S1, S2, S3 o N1, N2, N3
    is_south = lot_id.startswith("S")
    col_idx = int(lot_id[1]) - 1  # 0: Oeste (-25.6), 1: Centro (0.0), 2: Este (+25.6)
    
    offset_x = (col_idx - 1) * 32.0 * BU_PER_STUD  # -25.6, 0.0, +25.6
    offset_y = -16.0 * BU_PER_STUD if is_south else 16.0 * BU_PER_STUD  # -12.8 o +12.8
    
    return bc_x + offset_x, bc_y + offset_y

def setup_ground_and_pads(block_cols):
    """Crea la superficie general de calles y los zócalos de cada lote generado."""
    mat_calle = bpy.data.materials.get("LEGO 199 Dark Bluish Grey")
    mat_zocalo = bpy.data.materials.get("LEGO 194 Light Bluish Grey")
    if not mat_calle or not mat_zocalo:
        raise RuntimeError("Faltan materiales base para suelo/zócalos")

    # 1. Calle general a z = -0.02 BU para evitar z-fighting
    suelo = bpy.data.objects.get("Suelo")
    if not suelo:
        mesh = bpy.data.meshes.new("Mesh_Suelo")
        suelo = bpy.data.objects.new("Suelo", mesh)
        bpy.context.scene.collection.objects.link(suelo)
    
    half_x, half_y = 225.0, 180.0
    verts = [(-half_x, -half_y, -0.02), (half_x, -half_y, -0.02), (half_x, half_y, -0.02), (-half_x, half_y, -0.02)]
    faces = [(0, 1, 2, 3)]
    suelo.data.clear_geometry()
    suelo.data.from_pydata(verts, [], faces)
    suelo.data.update()
    suelo.data.materials.clear()
    suelo.data.materials.append(mat_calle)

    # 2. Plaza pad para la manzana B2 (Nitrody City)
    b2_col = block_cols["B2"]
    b2_pad_mesh = bpy.data.meshes.new("Mesh_B2_Plaza_Pad")
    b2_pad_obj = bpy.data.objects.new("B2_Plaza_Pad", b2_pad_mesh)
    b2_col.objects.link(b2_pad_obj)
    
    b2_hx, b2_hy = BLOCK_BU_X * 0.5, BLOCK_BU_Y * 0.5  # 38.4, 25.6
    b2_verts = [(-b2_hx, -b2_hy, 0.0), (b2_hx, -b2_hy, 0.0), (b2_hx, b2_hy, 0.0), (-b2_hx, b2_hy, 0.0)]
    b2_pad_mesh.from_pydata(b2_verts, [], faces)
    b2_pad_mesh.update()
    b2_pad_mesh.materials.append(mat_zocalo)

    # 3. Zócalos 32x32 para cada lote generado
    pad_half = 16.0 * BU_PER_STUD  # 12.8 BU
    pad_verts = [(-pad_half, -pad_half, 0.0), (pad_half, -pad_half, 0.0), (pad_half, pad_half, 0.0), (-pad_half, pad_half, 0.0)]
    
    # Crear malla compartida para los pads de lotes generados
    shared_pad_mesh = bpy.data.meshes.new("Mesh_Pad_32x32")
    shared_pad_mesh.from_pydata(pad_verts, [], faces)
    shared_pad_mesh.update()
    shared_pad_mesh.materials.append(mat_zocalo)

    for item in GENERATED_LOTS:
        b_id = item["block"]
        l_id = item["lot"]
        pad_name = f"Pad_{b_id}_{l_id}"
        pad_obj = bpy.data.objects.new(pad_name, shared_pad_mesh)
        lot_x, lot_y = get_lot_center_bu(b_id, l_id)
        pad_obj.location = Vector((lot_x, lot_y, 0.0))
        block_cols[b_id].objects.link(pad_obj)

def create_credits_datablock():
    """Crea el datablock de texto Creditos en Ciudad_completa.blend."""
    txt = bpy.data.texts.get("Creditos")
    if not txt:
        txt = bpy.data.texts.new("Creditos")
    txt.clear()
    
    creditos_text = """CRÉDITOS DE MODELOS Y ATRIBUCIONES (CIUDAD LEGO COMPLETA)
=========================================================

1. EDIFICIOS MODULARES OFICIALES LEGO (LDraw Official Model Repository - OMR)
Descargados de https://library.ldraw.org/omr bajo licencias Creative Commons:
- 10182-1 Café Corner: Max Martin Richter [MMR1988] (CCAL 2.0)
- 10185-1 Green Grocer: Max Martin Richter [MMR1988] (CCAL 2.0)
- 10190-1 Market Street: Max Martin Richter [MMR1988] (CCAL 2.0)
- 10197-1 Fire Brigade: Max Martin Richter [MMR1988] (CCAL 2.0)
- 10218-1 Pet Shop: Stefan Frenz [smf] (CCAL 2.0)
- 10224-1 Town Hall: Marc Giraudet [Mad_Marc] (CCAL 2.0)
- 10232-1 Palace Cinema: Orion Pobursky [OrionP] (CC BY 4.0)
- 10243-1 Parisian Restaurant: Willy Tschager [Holly Wood] (CCAL 2.0)
- 10246-1 Detective's Office: Willy Tschager [Holly-Wood] (CCAL 2.0)
- 10251-1 Brick Bank: Merlijn Wissink [Legolijntje] (CCAL 2.0)
- 10264-1 Corner Garage: Jaco van der Molen [Jaco van der Molen] (CCAL 2.0)
- 10270-1 Bookshop: Ulrich Röder [UR] (CCAL 2.0)
- 10278-1 Police Station: Philippe Hurbain [Philo] (CCAL 2.0)
- 10297-1 Boutique Hotel: Philippe Hurbain [Philo] (CCAL 2.0)

2. NITRODY CITY (Mecabricks)
- Modelo: Nitrody City! IV
- Autor/Plataforma: Mecabricks (10.463 piezas originales, materiales mb:*)
- Función en el proyecto: Hito central (Landmark) de la manzana B2.

3. GENERADOR PROCEDURAL GEOMETRY NODES "Edificio LEGO"
- Implementación procedural mediante nodos de geometría en Blender 5.2.2.
- Utiliza piezas LDraw y paleta de materiales Mecabricks (82 colores).
"""
    txt.write(creditos_text)
    print("Texto 'Creditos' creado exitosamente.")

def setup_cameras():
    """Configura las 7 cámaras requeridas con parámetros optimizados."""
    cams = {
        # 1. Cámara principal (tres cuartos aérea de todo el barrio)
        "Camara": {
            "type": 'PERSP', "lens": 38,
            "loc": Vector((-175.0, -190.0, 140.0)),
            "target": Vector((0.0, 0.0, 15.0))
        },
        # 2. Planta cenital ortográfica
        "Cam_Planta": {
            "type": 'ORTHO', "ortho_scale": 340.0,
            "loc": Vector((0.0, 0.0, 250.0)),
            "target": Vector((0.0, 0.0, 0.0))
        },
        # 3. Vista central (Nitrody City y el distrito modular que la rodea)
        "Cam_Centro": {
            "type": 'PERSP', "lens": 45,
            "loc": Vector((0.0, -90.0, 52.0)),
            "target": Vector((0.0, 5.0, 22.0))
        },
        # 4. Vista de calle 1 (a lo largo de la calle entre B2 y C2: Café Corner, Town Hall, Palace Cinema)
        "Cam_Calle_1": {
            "type": 'PERSP', "lens": 24,
            "loc": Vector((-65.0, 38.4, 1.8)),
            "target": Vector((65.0, 38.4, 14.0))
        },
        # 5. Vista de calle 2 (a lo largo de la calle entre A2 y B2: Brick Bank, Fire Brigade, Corner Garage)
        "Cam_Calle_2": {
            "type": 'PERSP', "lens": 24,
            "loc": Vector((65.0, -38.4, 1.8)),
            "target": Vector((-65.0, -38.4, 14.0))
        },
        # 6. Vista de calle 3 (avenida longitudinal entre B1 y B2 a nivel de suelo)
        "Cam_Calle_3": {
            "type": 'PERSP', "lens": 24,
            "loc": Vector((-51.2, -80.0, 1.8)),
            "target": Vector((-51.2, 80.0, 18.0))
        },
        # 7. Vista de contraste/mezcla (modular + generado + Nitrody City)
        "Cam_Mezcla": {
            "type": 'PERSP', "lens": 32,
            "loc": Vector((-42.0, 12.0, 6.0)),
            "target": Vector((-12.0, 20.0, 15.0))
        },
    }

    cam_objs = {}
    for name, cfg in cams.items():
        ob = bpy.data.objects.get(name)
        if not ob:
            c_data = bpy.data.cameras.new(name)
            ob = bpy.data.objects.new(name, c_data)
            bpy.context.scene.collection.objects.link(ob)
        c_data = ob.data
        c_data.type = cfg["type"]
        if cfg["type"] == 'PERSP':
            c_data.lens = cfg["lens"]
        else:
            c_data.ortho_scale = cfg["ortho_scale"]
        c_data.clip_start = 0.2
        c_data.clip_end = 1000.0
        
        ob.location = cfg["loc"]
        direction = cfg["target"] - cfg["loc"]
        rot_quat = direction.to_track_quat('-Z', 'Y')
        ob.rotation_euler = rot_quat.to_euler()
        cam_objs[name] = ob

    bpy.context.scene.camera = cam_objs["Camara"]
    print(f"7 cámaras configuradas correctamente. Cámara activa: {bpy.context.scene.camera.name}")
    return cam_objs

# ---------------------------------------------------------------------------
# Construcción del barrio
# ---------------------------------------------------------------------------
def build_complete_city():
    print("====================================================================")
    print("Iniciando montaje de Ciudad_completa.blend...")
    print("====================================================================")
    
    # 1. Limpiar objetos de ejemplo del archivo generador
    for old_name in ("Hotel", "Tienda", "Casa"):
        ob = bpy.data.objects.get(old_name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
            
    # Colecciones de la escena
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

    # 2. Configurar calles y pads
    setup_ground_and_pads(block_cols)

    # 3. Vincular colecciones de bibliotecas externas
    # A) Modulares oficiales
    with bpy.data.libraries.load(LIB_MODULARS, link=True, relative=True) as (data_from, data_to):
        data_to.collections = [c for c in data_from.collections if c.startswith("MOD_")]
    print(f"Colecciones modulares vinculadas: {len(data_to.collections)}")

    # B) Nitrody City
    with bpy.data.libraries.load(LIB_NITRO, link=True, relative=True) as (data_from, data_to):
        data_to.collections = ["Nitrody City! IV"]
    print("Colección Nitrody City vinculada exitosamente.")

    # 4. Colocar Nitrody City en Manzana B2
    nitro_col = bpy.data.collections.get("Nitrody City! IV")
    if not nitro_col:
        raise RuntimeError("No se encontró la colección 'Nitrody City! IV'")
        
    nitro_empty = bpy.data.objects.get("B2_NITRO")
    if not nitro_empty:
        nitro_empty = bpy.data.objects.new("B2_NITRO", None)
        nitro_empty.instance_type = 'COLLECTION'
        nitro_empty.instance_collection = nitro_col
        block_cols["B2"].objects.link(nitro_empty)
        
    # Offset calculado para centrar Nitrody City (69x53 studs) en B2 (96x64 studs)
    # y rotación de +90° para que su entrada "HOTEL" dé a la calle Sur
    nitro_empty.location = Vector((18.0, -6.0, 0.0))
    nitro_empty.rotation_euler = Euler((0.0, 0.0, math.radians(90)), 'XYZ')
    nitro_empty["block"] = "B2"
    nitro_empty["lot"] = "CENTRO"
    nitro_empty["source"] = "NITRO"
    nitro_empty["name"] = "Nitrody City"

    layout_record = []
    layout_record.append({
        "object": "B2_NITRO",
        "block": "B2",
        "lot": "CENTRO",
        "source": "NITRO",
        "model": "Nitrody City! IV",
        "location_bu": [18.0, -6.0, 0.0],
        "rotation_deg": 90,
        "landmark": True
    })

    # 5. Colocar los 14 Edificios Modulares oficiales
    print("\n--- INSTANCIANDO LOS 14 MODULARES OFICIALES ---")
    for lot_key, minfo in MODULAR_ASSIGNMENTS.items():
        b_id, l_id = lot_key.split("_")
        col_name = minfo["col"]
        m_col = bpy.data.collections.get(col_name)
        if not m_col:
            raise KeyError(f"Colección modular no encontrada: {col_name}")
            
        obj_name = f"{b_id}_{l_id}_{col_name}"
        ob = bpy.data.objects.get(obj_name)
        if not ob:
            ob = bpy.data.objects.new(obj_name, None)
            ob.instance_type = 'COLLECTION'
            ob.instance_collection = m_col
            block_cols[b_id].objects.link(ob)
            
        lot_x, lot_y = get_lot_center_bu(b_id, l_id)
        rot_deg = minfo["rot_deg"]
        ob.location = Vector((lot_x, lot_y, 0.0))
        ob.rotation_euler = Euler((0.0, 0.0, math.radians(rot_deg)), 'XYZ')
        
        # Propiedades personalizadas
        ob["block"] = b_id
        ob["lot"] = l_id
        ob["source"] = "MODULAR"
        ob["model"] = minfo["desc"]
        ob["type"] = minfo["btype"]

        layout_record.append({
            "object": obj_name,
            "block": b_id,
            "lot": l_id,
            "source": "MODULAR",
            "model": minfo["desc"],
            "type": minfo["btype"],
            "location_bu": [round(lot_x, 3), round(lot_y, 3), 0.0],
            "rotation_deg": rot_deg
        })
        print(f"  Modular {minfo['desc']:22} en {b_id}_{l_id} (rot={rot_deg}°)")

    # 6. Colocar los Edificios Generados con Geometry Nodes
    ng = bpy.data.node_groups.get("Edificio LEGO")
    if not ng:
        raise RuntimeError("No se encontró el grupo de nodos 'Edificio LEGO'")
    sock_map = {item.name: item.identifier for item in ng.interface.items_tree if item.item_type == 'SOCKET' and item.in_out == 'INPUT'}

    rng = random.Random(MASTER_SEED)
    print("\n--- INSTANCIANDO EDIFICIOS PROCEDURALES (GEOMETRY NODES) ---")
    gen_idx = 0

    for item in GENERATED_LOTS:
        b_id = item["block"]
        l_id = item["lot"]
        lot_x, lot_y = get_lot_center_bu(b_id, l_id)
        is_south = l_id.startswith("S")
        lot_rot_deg = 0 if is_south else 180

        # Caso de pareja de adosados (dos por lote)
        if item["archetype"] == "Townhouse_Pair":
            for th in item["townhouses"]:
                gen_idx += 1
                b_name = f"{b_id}_{l_id}_GEN_Townhouse_{th['sub']}"
                ancho = th["ancho"]
                fondo = th["fondo"]
                pisos = th["pisos"]
                scheme_name = th["scheme"]
                
                # Alineación de fachada: setback de 8 studs respecto al borde de calle
                # Lote mide 32 studs de fondo. Borde de calle a -16 studs del centro del lote.
                # Línea de fachada a -8 studs del centro del lote.
                # Con fondo F, el centro del edificio se sitúa en -8 + F/2 studs del centro del lote.
                y_local_studs = -8.0 + (fondo / 2.0)
                if not is_south:
                    y_local_studs = -y_local_studs
                
                # Desplazamiento lateral dentro del lote
                x_local_studs = th["offset_x"]
                if not is_south:
                    x_local_studs = -x_local_studs
                    
                world_x = lot_x + x_local_studs * BU_PER_STUD
                world_y = lot_y + y_local_studs * BU_PER_STUD
                
                ob = bpy.data.objects.get(b_name)
                if not ob:
                    mesh = bpy.data.meshes.new(f"Mesh_{b_name}")
                    ob = bpy.data.objects.new(b_name, mesh)
                    block_cols[b_id].objects.link(ob)
                    
                ob.location = Vector((world_x, world_y, 0.0))
                ob.rotation_euler = Euler((0.0, 0.0, math.radians(lot_rot_deg)), 'XYZ')
                
                ob["block"] = b_id
                ob["lot"] = l_id
                ob["source"] = "GENERATED"
                ob["archetype"] = "Townhouse"
                ob["scheme"] = scheme_name
                
                mod = ob.modifiers.get("Edificio LEGO")
                if not mod:
                    mod = ob.modifiers.new("Edificio LEGO", 'NODES')
                    mod.node_group = ng

                scheme_info = COLOR_SCHEMES[scheme_name]
                seed_val = MASTER_SEED * 100 + gen_idx
                mod_params = {
                    "Pisos": pisos,
                    "Ancho (studs)": ancho,
                    "Fondo (studs)": fondo,
                    "Planta baja": th["pb"],
                    "Remate": th["rm"],
                    "Semilla": seed_val,
                    "Ventanas ciegas": round(rng.uniform(0.05, 0.20), 3),
                    "Jardineras": round(rng.uniform(0.15, 0.40), 3),
                    "Luces encendidas": 0.0,
                    "Realizar instancias": False,
                    "Pared": bpy.data.materials[scheme_info["Pared"]],
                    "Molduras": bpy.data.materials[scheme_info["Molduras"]],
                    "Tejado": bpy.data.materials[scheme_info["Tejado"]],
                    "Azotea": bpy.data.materials[scheme_info["Azotea"]],
                    "Puerta": bpy.data.materials[scheme_info["Puerta"]],
                }
                for k, v in mod_params.items():
                    getattr(mod.properties.inputs, sock_map[k]).value = v
                ob.update_tag()

                layout_record.append({
                    "object": b_name,
                    "block": b_id,
                    "lot": l_id,
                    "source": "GENERATED",
                    "archetype": "Townhouse",
                    "pisos": pisos,
                    "ancho_studs": ancho,
                    "fondo_studs": fondo,
                    "location_bu": [round(world_x, 3), round(world_y, 3), 0.0],
                    "rotation_deg": lot_rot_deg,
                    "scheme": scheme_name,
                    "seed": seed_val
                })
        else:
            # Edificio único por lote
            gen_idx += 1
            arch = item["archetype"]
            b_name = f"{b_id}_{l_id}_GEN_{arch}"
            ancho = item["ancho"]
            fondo = item["fondo"]
            pisos = item["pisos"]
            scheme_name = item["scheme"]
            is_hotel = (item["pb"] == "Entrada hotel")
            
            y_local_studs = -8.0 + (fondo / 2.0)
            if not is_south:
                y_local_studs = -y_local_studs
                
            world_x = lot_x
            world_y = lot_y + y_local_studs * BU_PER_STUD
            
            ob = bpy.data.objects.get(b_name)
            if not ob:
                mesh = bpy.data.meshes.new(f"Mesh_{b_name}")
                ob = bpy.data.objects.new(b_name, mesh)
                block_cols[b_id].objects.link(ob)
                
            ob.location = Vector((world_x, world_y, 0.0))
            ob.rotation_euler = Euler((0.0, 0.0, math.radians(lot_rot_deg)), 'XYZ')
            
            ob["block"] = b_id
            ob["lot"] = l_id
            ob["source"] = "GENERATED"
            ob["archetype"] = arch
            ob["scheme"] = scheme_name
            
            mod = ob.modifiers.get("Edificio LEGO")
            if not mod:
                mod = ob.modifiers.new("Edificio LEGO", 'NODES')
                mod.node_group = ng

            scheme_info = COLOR_SCHEMES[scheme_name]
            seed_val = MASTER_SEED * 100 + gen_idx
            mod_params = {
                "Pisos": pisos,
                "Ancho (studs)": ancho,
                "Fondo (studs)": fondo,
                "Planta baja": item["pb"],
                "Remate": item["rm"],
                "Semilla": seed_val,
                "Ventanas ciegas": round(rng.uniform(0.05, 0.20), 3),
                "Jardineras": round(rng.uniform(0.15, 0.40), 3),
                "Luces encendidas": 0.0,
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
                getattr(mod.properties.inputs, sock_map[k]).value = v
            ob.update_tag()

            layout_record.append({
                "object": b_name,
                "block": b_id,
                "lot": l_id,
                "source": "GENERATED",
                "archetype": arch,
                "pisos": pisos,
                "ancho_studs": ancho,
                "fondo_studs": fondo,
                "location_bu": [round(world_x, 3), round(world_y, 3), 0.0],
                "rotation_deg": lot_rot_deg,
                "scheme": scheme_name,
                "seed": seed_val
            })
            print(f"  Generado {arch:14} en {b_id}_{l_id} ({ancho}x{fondo} studs, {pisos} pisos, {scheme_name})")

    # 7. Actualizar vista y crear créditos y cámaras
    bpy.context.view_layer.update()
    create_credits_datablock()
    setup_cameras()

    # 8. Exportar JSON de layout
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(layout_record, f, indent=2)
    print(f"\nLayout exportado a: {OUT_JSON} ({len(layout_record)} registros)")

    # 9. Guardar archivo .blend final
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"Archivo de ciudad guardado exitosamente: {OUT_BLEND}")
    return layout_record

# ---------------------------------------------------------------------------
# Validación completa y Renderizado
# ---------------------------------------------------------------------------
def validate_and_render():
    print("\n====================================================================")
    print("INICIANDO VALIDACIÓN Y RENDERS DE LA CIUDAD COMPLETA")
    print("====================================================================")
    
    t0 = time.time()
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    t_eval = time.time() - t0
    
    # 1. Conteo de instancias y objetos
    total_inst = len(depsgraph.object_instances)
    print(f"Tiempo de evaluación del depsgraph: {t_eval:.3f} s")
    print(f"Total de instancias evaluadas en la escena: {total_inst}")

    # 2. Validación de inventario de modulares
    found_mods = set()
    found_nitro = False
    max_gen_height = 0.0
    gen_count = 0

    for ob in bpy.context.scene.objects:
        if ob.get("source") == "MODULAR":
            found_mods.add(ob.get("model"))
        elif ob.get("source") == "NITRO":
            found_nitro = True
        elif ob.get("source") == "GENERATED":
            gen_count += 1

    print(f"\nVerificación de Inventario:")
    print(f"  - Modulares encontrados: {len(found_mods)} de 14")
    assert len(found_mods) == 14, f"Faltan modulares: {found_mods}"
    print(f"  - Nitrody City en B2: {'PRESENTE' if found_nitro else 'AUSENTE'}")
    assert found_nitro, "Nitrody City no fue encontrada"
    print(f"  - Mini Modulars (10230): {'CORRECTAMENTE EXCLUIDO' if 'Mini' not in found_mods else 'ERROR'}")
    assert 'Mini' not in found_mods, "Mini Modulars no debe estar en la ciudad"
    print(f"  - Edificios generados totales: {gen_count}")

    # 3. Validación de alturas
    # La torre hotel de Nitro mide 56.55 BU
    nitro_tower_height = 56.55
    print(f"\nVerificación de Alturas:")
    for ob in bpy.context.scene.objects:
        if ob.get("source") == "GENERATED":
            pisos = getattr(ob.modifiers["Edificio LEGO"].properties.inputs, ng_socket_pisos).value
            # Altura aprox = pisos * 6.4 + remate (~3 BU)
            est_height = pisos * 6.4 + 3.0
            max_gen_height = max(max_gen_height, est_height)
            assert pisos <= 8, f"Edificio {ob.name} supera el límite de 8 pisos ({pisos} pisos)"
    print(f"  - Altura máxima generada: {max_gen_height:.1f} BU < Torre Nitro ({nitro_tower_height:.1f} BU)")

    # 4. Comprobación de modificadores y advertencias
    ng = bpy.data.node_groups.get("Edificio LEGO")
    for ob in bpy.context.scene.objects:
        if ob.get("source") == "GENERATED":
            mod = ob.modifiers.get("Edificio LEGO")
            assert mod, f"Objeto {ob.name} sin modificador"
            # Verificar que no tenga Realizar instancias activado
            realizar = getattr(mod.properties.inputs, ng_socket_realizar).value
            assert not realizar, f"Objeto {ob.name} tiene 'Realizar instancias' activado"

    print("  - Todos los modificadores Geometry Nodes verificados y sin realizar instancias.")

    # 5. Renderizar las 7 cámaras
    os.makedirs(OUT_RENDERS, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.view_settings.view_transform = 'AgX'

    cam_names = ["Camara", "Cam_Planta", "Cam_Centro", "Cam_Calle_1", "Cam_Calle_2", "Cam_Calle_3", "Cam_Mezcla"]
    render_times = {}

    print("\n--- RENDERIZANDO LAS 7 CÁMARAS (1920x1080, EEVEE, AgX) ---")
    for cname in cam_names:
        cam_ob = bpy.data.objects.get(cname)
        if not cam_ob:
            raise KeyError(f"Cámara no encontrada: {cname}")
        scene.camera = cam_ob
        out_img = os.path.join(OUT_RENDERS, f"{cname}.png")
        scene.render.filepath = out_img
        
        t_start = time.time()
        bpy.ops.render.render(write_still=True)
        t_dur = time.time() - t_start
        render_times[cname] = t_dur
        print(f"  Cámara '{cname:12}' renderizada en {t_dur:.2f} s -> {out_img}")

    print("\n====================================================================")
    print("RESUMEN DE RENDIMIENTO Y VALIDACIÓN:")
    print(f"  - Archivo guardado: {OUT_BLEND}")
    print(f"  - Tiempo medio de render por fotograma: {sum(render_times.values())/len(render_times):.2f} s")
    print(f"  - Total instancias en escena: {total_inst}")
    print("====================================================================")

if __name__ == "__main__":
    # Obtener identificadores de sockets de referencia
    ng = bpy.data.node_groups.get("Edificio LEGO")
    items = ng.interface.items_tree
    ng_socket_pisos = items["Pisos"].identifier
    ng_socket_realizar = items["Realizar instancias"].identifier
    
    build_complete_city()
    validate_and_render()
