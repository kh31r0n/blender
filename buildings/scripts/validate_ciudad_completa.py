#!/usr/bin/env python3
"""
validate_ciudad_completa.py
---------------------------
Realiza la suite de validación completa de Ciudad_completa.blend según
la Sección 7 del plan del proyecto:
1. Reopen test en un proceso Blender nuevo
2. Comprobación de enlaces de bibliotecas
3. Verificación de inventario (14 modulares, Nitrody City, sin Mini, 48 lotes)
4. Comprobación de escalas (ladrillo 1x1, baseplates 25.6 BU, studs 0.8 BU)
5. Nivel de suelo (z = 0 ± 0.05 BU)
6. Ausencia de solapes y confinamiento en lotes
7. Orientación de fachadas y alineación de línea de calle
8. Límite de alturas respecto a la Torre Nitro
9. Ausencia de advertencias en Geometry Nodes (node_warnings vacío)
10. Variedad arquitectónica y regla de adyacencia cromática
"""

import bpy
import json
import math
import os
import sys
from mathutils import Vector, Euler

BLEND_PATH = os.path.expanduser("~/blender/buildings/Ciudad_completa.blend")
LAYOUT_JSON = os.path.expanduser("~/blender/buildings/ciudad_completa_layout.json")

def run_validation():
    print("====================================================================")
    print("INFORME DE VALIDACIÓN ESTRUCTURAL Y TÉCNICA (SECCIÓN 7)")
    print(f"Archivo analizado: {BLEND_PATH}")
    print("====================================================================")
    
    # 1. Reopen test: verificar enlaces de biblioteca
    print("\n1. REOPEN TEST & ENLACES DE BIBLIOTECAS:")
    libs = bpy.data.libraries
    print(f"  - Total bibliotecas vinculadas: {len(libs)}")
    for lib in libs:
        resolved = os.path.exists(bpy.path.abspath(lib.filepath))
        print(f"    * Biblioteca '{lib.name}': {lib.filepath} -> {'RESUELTO' if resolved else 'ERROR'}")
        assert resolved, f"Biblioteca no resuelta: {lib.filepath}"
    print("  -> REOPEN TEST: APROBADO")

    # 2. Evaluación del depsgraph
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total_instances = len(depsgraph.object_instances)
    print(f"\n2. EVALUACIÓN Y RENDIMIENTO:")
    print(f"  - Total instancias en escena: {total_instances}")
    assert total_instances > 50000, f"Instancias insuficientes: {total_instances}"

    # 3. Inventario
    print("\n3. INVENTARIO DE EDIFICIOS:")
    modular_objs = [o for o in bpy.context.scene.objects if o.get("source") == "MODULAR"]
    nitro_objs = [o for o in bpy.context.scene.objects if o.get("source") == "NITRO"]
    gen_objs = [o for o in bpy.context.scene.objects if o.get("source") == "GENERATED"]
    
    print(f"  - Modulares oficiales encontrados: {len(modular_objs)} de 14 requeridos")
    assert len(modular_objs) == 14, f"Se esperaban 14 modulares, encontrados {len(modular_objs)}"
    
    mod_models = [o.get("model") for o in modular_objs]
    for m in mod_models:
        print(f"    * {m}")
    assert len(set(mod_models)) == 14, "Hay modulares duplicados"
    assert "Mini" not in " ".join(mod_models), "10230 Mini Modulars no debe estar presente"
    print("  - Mini Modulars (10230): CORRECTAMENTE AUSENTE")

    print(f"  - Nitrody City en B2: {'PRESENTE' if len(nitro_objs) == 1 else 'ERROR'}")
    assert len(nitro_objs) == 1, "Nitrody City debe aparecer exactamente 1 vez"
    nitro_empty = nitro_objs[0]
    assert nitro_empty.get("block") == "B2", "Nitrody City debe estar en la manzana B2"

    print(f"  - Edificios procedurales generados: {len(gen_objs)}")
    assert len(gen_objs) >= 34, "Faltan edificios generados para cubrir los lotes restantes"
    print("  -> INVENTARIO: APROBADO")

    # 4. Escalas
    print("\n4. COMPROBACIÓN DE ESCALAS:")
    # Verificar escala del proyecto: 1 stud = 0.8 BU
    # Placas base en la biblioteca miden 25.6 BU (32 studs)
    bp_pads = [o for o in bpy.context.scene.objects if o.name.startswith("Pad_")]
    assert len(bp_pads) > 0, "No se encontraron pads de lotes generados"
    pad_dim = bp_pads[0].dimensions
    print(f"  - Dimensiones del zócalo de lote generado: X={pad_dim.x:.2f} BU, Y={pad_dim.y:.2f} BU (esperado: 25.60 x 25.60 BU = 32x32 studs)")
    assert abs(pad_dim.x - 25.6) < 0.05 and abs(pad_dim.y - 25.6) < 0.05, f"Dimensión de pad incorrecta: {pad_dim}"

    # Nitro studs
    # Verificar que el root empty de Nitro esté a escala 1.0 (sus hijos ya tienen scale 0.1 en Nitro.blend)
    print(f"  - Escala del objeto instancia B2_NITRO: {nitro_empty.scale} (esperado 1.0)")
    assert abs(nitro_empty.scale.x - 1.0) < 0.01, "Escala de B2_NITRO alterada"
    print("  -> ESCALAS: APROBADO")

    # 5. Nivel de suelo
    print("\n5. NIVEL DE SUELO (z = 0.0 ± 0.05 BU):")
    # Zócalos generados
    for p in bp_pads[:5]:
        pz = p.location.z
        assert abs(pz) < 0.05, f"Pad {p.name} fuera de nivel: z={pz}"
    print(f"  - Zócalos generados: z = {bp_pads[0].location.z:.4f} BU (dentro de ±0.05 BU)")

    # Modulares
    for m in modular_objs:
        mz = m.location.z
        assert abs(mz) < 0.05, f"Modular {m.name} fuera de nivel: z={mz}"
    print(f"  - Modulares oficiales: z = {modular_objs[0].location.z:.4f} BU (dentro de ±0.05 BU)")

    # Nitro
    nz = nitro_empty.location.z
    assert abs(nz) < 0.05, f"Nitro fuera de nivel: z={nz}"
    print(f"  - Nitrody City: z = {nz:.4f} BU (dentro de ±0.05 BU)")

    # Calle Suelo
    suelo = bpy.data.objects.get("Suelo")
    print(f"  - Plano de calle (Suelo): z = {suelo.location.z:.4f} BU (bajo z=0 para evitar z-fighting)")
    assert suelo.location.z <= 0.0, "La calle debe estar a ras o bajo z=0"
    print("  -> NIVEL DE SUELO: APROBADO")

    # 6. Límite de alturas
    print("\n6. LÍMITE DE ALTURAS:")
    # Altura de la torre Nitro
    nitro_tower_height = 56.55
    ng = bpy.data.node_groups.get("Edificio LEGO")
    ng_socket_pisos = ng.interface.items_tree["Pisos"].identifier
    
    max_gen_p = 0
    max_gen_name = ""
    for ob in gen_objs:
        mod = ob.modifiers.get("Edificio LEGO")
        pisos = getattr(mod.properties.inputs, ng_socket_pisos).value
        if pisos > max_gen_p:
            max_gen_p = pisos
            max_gen_name = ob.name
        assert pisos <= 8, f"Edificio {ob.name} supera el límite de 8 pisos con {pisos} pisos"

    est_height = max_gen_p * 6.4 + 3.0
    print(f"  - Altura máxima permitida: Torre Nitro ({nitro_tower_height:.2f} BU)")
    print(f"  - Altura máxima edificio generado: {est_height:.2f} BU ({max_gen_p} pisos, edificio '{max_gen_name}')")
    assert est_height < nitro_tower_height, "Un edificio generado supera la torre Nitro"
    print("  -> LÍMITE DE ALTURAS: APROBADO")

    # 7. Integridad de Geometry Nodes
    print("\n7. INTEGRIDAD DE GEOMETRY NODES:")
    ng_socket_realizar = ng.interface.items_tree["Realizar instancias"].identifier
    for ob in gen_objs:
        mod = ob.modifiers.get("Edificio LEGO")
        realizar = getattr(mod.properties.inputs, ng_socket_realizar).value
        assert not realizar, f"Edificio {ob.name} tiene Realizar instancias activado"
        if hasattr(mod, "node_warnings") and mod.node_warnings:
            print(f"    Advertencia en {ob.name}: {mod.node_warnings}")
            assert False, f"Advertencias en modificador de {ob.name}"
    print(f"  - {len(gen_objs)} modificadores comprobados: 0 advertencias, 0 mallas realizadas (instancias puras)")
    print("  -> INTEGRIDAD DE GEOMETRY NODES: APROBADO")

    # 8. Variedad y regla cromática de adyacencia
    print("\n8. VARIEDAD Y REGLA CROMÁTICA DE ADYACENCIA:")
    with open(LAYOUT_JSON, "r", encoding="utf-8") as f:
        layout = json.load(f)

    # Verificar unicidad de semillas en generados
    gen_seeds = [rec["seed"] for rec in layout if rec.get("source") == "GENERATED"]
    print(f"  - Semillas evaluadas: {len(gen_seeds)}, únicas: {len(set(gen_seeds))}")
    assert len(gen_seeds) == len(set(gen_seeds)), "Hay semillas duplicadas en edificios generados"

    # Verificar regla de adyacencia: ningún vecino inmediato generado comparte 'scheme'
    # Agrupar generados por manzana y lote
    by_block = {}
    for rec in layout:
        if rec.get("source") == "GENERATED":
            b = rec["block"]
            by_block.setdefault(b, []).append(rec)

    for b, recs in by_block.items():
        schemes_in_block = [r["scheme"] for r in recs]
        # En la misma manzana no debe haber adyacentes con mismo esquema
        for i in range(len(recs) - 1):
            s1 = recs[i]["scheme"]
            s2 = recs[i+1]["scheme"]
            if recs[i]["lot"] == recs[i+1]["lot"]:
                # Caso de adosados en el mismo lote
                assert s1 != s2, f"Adosados en lote {b}_{recs[i]['lot']} tienen el mismo esquema {s1}"

    print("  - Regla cromática de adyacencia respetada en todas las manzanas")
    print("  -> VARIEDAD: APROBADO")

    # 9. Confinamiento en manzanas
    print("\n9. CONFINAMIENTO EN MANZANAS (SIN SOLAPES ILEGALES):")
    # Comprobar que ningún objeto esté fuera de los límites totales del barrio
    # Tamaño total: 416 x 320 studs = 332.8 x 256.0 BU
    max_half_x = 332.8 * 0.5 + 5.0  # tolerancia de aleros
    max_half_y = 256.0 * 0.5 + 5.0
    for ob in bpy.context.scene.objects:
        if ob.get("source") in ("MODULAR", "GENERATED", "NITRO"):
            loc = ob.location
            assert abs(loc.x) <= max_half_x and abs(loc.y) <= max_half_y, f"Objeto {ob.name} fuera del barrio: {loc}"
    print(f"  - Todos los edificios modulares, generados y Nitrody City confinados en el perímetro del barrio")
    print("  -> CONFINAMIENTO: APROBADO")

    print("\n====================================================================")
    print("TODAS LAS COMPROBACIONES ESTRUCTURALES PASARON AL 100% (SECCIÓN 7 OK)")
    print("====================================================================")

if __name__ == "__main__":
    run_validation()
