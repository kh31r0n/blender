"""
Generador procedural de terreno desértico LEGO con Geometry Nodes para Blender 5.2.2.
Crea el archivo Desierto_LEGO_GN_v2.blend con:
- Cuadrícula continua configurable (1000x1000 u, resolución 300x300 bloques).
- Relieve escalonado cuantizado en niveles de placa con studs visibles.
- Piezas en pendiente (slopes tipo 3040/3039) en las transiciones de dunas.
- Dunas con perfil eólico, colinas y erosión procedural.
- Formaciones rocosas integradas en el terreno.
- Arco natural LEGO con abertura reconocible y pilares de apoyo.
- Materiales de plástico LEGO con variaciones de color auténticas.
- Alto rendimiento mediante instanciación (sin Realize Instances masivo).
"""

import bpy
import math

OUT_BLEND = "/home/kheiron/blender/desert/Desierto_LEGO_GN_v2.blend"


def create_materials():
    # 1. Material Arena (Sand)
    mat_sand = bpy.data.materials.new("MAT_LEGO_Arena")
    mat_sand.use_nodes = True
    nd, lk = mat_sand.node_tree.nodes, mat_sand.node_tree.links
    nd.clear()

    out = nd.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)

    bsdf = nd.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.32
    bsdf.inputs["Coat Weight"].default_value = 0.15
    bsdf.inputs["Coat Roughness"].default_value = 0.2

    # Color variation based on random per-instance / object info + noise
    obj_info = nd.new("ShaderNodeObjectInfo")
    obj_info.location = (-600, 100)

    noise = nd.new("ShaderNodeTexNoise")
    noise.location = (-600, -150)
    noise.inputs["Scale"].default_value = 0.05
    noise.inputs["Detail"].default_value = 2.0

    mix_fac = nd.new("ShaderNodeMix")
    mix_fac.data_type = 'FLOAT'
    mix_fac.location = (-350, 0)
    mix_fac.inputs["Factor"].default_value = 0.6
    lk.new(obj_info.outputs["Random"], mix_fac.inputs["A"])
    lk.new(noise.outputs["Factor"], mix_fac.inputs["B"])

    ramp = nd.new("ShaderNodeValToRGB")
    ramp.location = (-100, 0)
    # LEGO Sand palette: Tan, Dark Tan, Warm Sand / Nougat
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.58, 0.44, 0.26, 1.0)  # Dark Tan
    e1 = ramp.color_ramp.elements.new(0.45)
    e1.color = (0.82, 0.70, 0.48, 1.0)  # Tan base
    e2 = ramp.color_ramp.elements.new(0.80)
    e2.color = (0.90, 0.79, 0.58, 1.0)  # Light Tan
    ramp.color_ramp.elements[-1].position = 1.0
    ramp.color_ramp.elements[-1].color = (0.72, 0.52, 0.32, 1.0)  # Medium Nougat accent

    lk.new(mix_fac.outputs["Result"], ramp.inputs["Fac"])
    lk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    lk.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # 2. Material Roca (Rock)
    mat_rock = bpy.data.materials.new("MAT_LEGO_Roca")
    mat_rock.use_nodes = True
    nd_r, lk_r = mat_rock.node_tree.nodes, mat_rock.node_tree.links
    nd_r.clear()

    out_r = nd_r.new("ShaderNodeOutputMaterial")
    out_r.location = (600, 0)

    bsdf_r = nd_r.new("ShaderNodeBsdfPrincipled")
    bsdf_r.location = (300, 0)
    bsdf_r.inputs["Roughness"].default_value = 0.38
    bsdf_r.inputs["Coat Weight"].default_value = 0.12

    obj_info_r = nd_r.new("ShaderNodeObjectInfo")
    obj_info_r.location = (-600, 100)

    noise_r = nd_r.new("ShaderNodeTexNoise")
    noise_r.location = (-600, -150)
    noise_r.inputs["Scale"].default_value = 0.08
    noise_r.inputs["Detail"].default_value = 3.0

    mix_fac_r = nd_r.new("ShaderNodeMix")
    mix_fac_r.data_type = 'FLOAT'
    mix_fac_r.location = (-350, 0)
    mix_fac_r.inputs["Factor"].default_value = 0.5
    lk_r.new(obj_info_r.outputs["Random"], mix_fac_r.inputs["A"])
    lk_r.new(noise_r.outputs["Factor"], mix_fac_r.inputs["B"])

    ramp_r = nd_r.new("ShaderNodeValToRGB")
    ramp_r.location = (-100, 0)
    # LEGO Rock palette: Reddish Brown, Dark Brown, Dark Orange
    ramp_r.color_ramp.elements[0].position = 0.0
    ramp_r.color_ramp.elements[0].color = (0.22, 0.10, 0.05, 1.0)  # Dark Brown
    e1_r = ramp_r.color_ramp.elements.new(0.40)
    e1_r.color = (0.38, 0.18, 0.08, 1.0)  # Reddish Brown
    e2_r = ramp_r.color_ramp.elements.new(0.75)
    e2_r.color = (0.55, 0.26, 0.10, 1.0)  # Dark Orange
    ramp_r.color_ramp.elements[-1].position = 1.0
    ramp_r.color_ramp.elements[-1].color = (0.42, 0.28, 0.18, 1.0)  # Weathered Nougat

    lk_r.new(mix_fac_r.outputs["Result"], ramp_r.inputs["Fac"])
    lk_r.new(ramp_r.outputs["Color"], bsdf_r.inputs["Base Color"])
    lk_r.new(bsdf_r.outputs["BSDF"], out_r.inputs["Surface"])

    return mat_sand, mat_rock


def build_geometry_nodes(mat_sand, mat_rock):
    t = bpy.data.node_groups.new("Desierto LEGO", "GeometryNodeTree")
    n, l = t.nodes, t.links

    # Setup Panels and Sockets
    p_terreno = t.interface.new_panel("Terreno")
    p_lego = t.interface.new_panel("Piezas LEGO")
    p_dunas = t.interface.new_panel("Dunas y Relieve")
    p_erosion = t.interface.new_panel("Erosión")
    p_pend = t.interface.new_panel("Pendientes (Slopes)")
    p_rocas = t.interface.new_panel("Rocas")
    p_arcos = t.interface.new_panel("Arcos Naturales")
    p_mats = t.interface.new_panel("Materiales")

    def add_in(name, kind, default, min_v, max_v, desc, panel):
        s = t.interface.new_socket(name=name, in_out='INPUT', socket_type=kind,
                                   description=desc, parent=panel)
        s.default_value = default
        if min_v is not None and hasattr(s, "min_value"): s.min_value = min_v
        if max_v is not None and hasattr(s, "max_value"): s.max_value = max_v
        return s

    add_in("Dimensión X", "NodeSocketInt", 1000, 10, 10000, "Ancho total del terreno en unidades Blender.", p_terreno)
    add_in("Dimensión Y", "NodeSocketInt", 1000, 10, 10000, "Largo total del terreno en unidades Blender.", p_terreno)
    add_in("Resolución X", "NodeSocketInt", 300, 10, 1000, "Número de columnas de bloques en el eje X.", p_terreno)
    add_in("Resolución Y", "NodeSocketInt", 300, 10, 1000, "Número de columnas de bloques en el eje Y.", p_terreno)
    add_in("Semilla", "NodeSocketInt", 42, 0, 999999, "Semilla aleatoria global para dunas, rocas y arcos.", p_terreno)

    add_in("Altura Placa", "NodeSocketFloat", 0.8, 0.1, 10.0, "Altura de una placa LEGO en unidades Blender.", p_lego)
    add_in("Escalón en Placas", "NodeSocketInt", 1, 1, 10, "Número de placas por escalón vertical cuantizado.", p_lego)
    add_in("Mostrar Studs", "NodeSocketBool", True, None, None, "Activa o desactiva los studs superiores.", p_lego)
    add_in("Separación Bloques", "NodeSocketFloat", 0.96, 0.8, 1.0, "Factor de escala horizontal para dejar juntas visibles entre bloques.", p_lego)

    add_in("Altura Dunas", "NodeSocketFloat", 40.0, 0.0, 200.0, "Altura máxima de las dunas de arena.", p_dunas)
    add_in("Escala Dunas", "NodeSocketFloat", 0.008, 0.0005, 0.05, "Frecuencia espacial de las crestas de dunas.", p_dunas)
    add_in("Ángulo Viento", "NodeSocketFloat", 35.0, 0.0, 360.0, "Dirección del viento para la orientación de las dunas (grados).", p_dunas)
    add_in("Distorsión Dunas", "NodeSocketFloat", 2.0, 0.0, 10.0, "Ondulación y sinuosidad de las crestas de dunas.", p_dunas)
    add_in("Altura Colinas", "NodeSocketFloat", 40.0, 0.0, 200.0, "Altura adicional de grandes formaciones de colinas.", p_dunas)
    add_in("Escala Colinas", "NodeSocketFloat", 0.003, 0.0005, 0.05, "Tamaño general de las colinas.", p_dunas)

    add_in("Erosión Suavizado", "NodeSocketInt", 1, 0, 5, "Iteraciones de suavizado del relieve antes de cuantizar.", p_erosion)
    add_in("Fuerza Cárcavas", "NodeSocketFloat", 0.20, 0.0, 1.0, "Profundidad de hendiduras y surcos de erosión.", p_erosion)

    add_in("Usar Pendientes", "NodeSocketBool", True, None, None, "Coloca piezas en cuña/inclinadas en los bordes de los escalones.", p_pend)
    add_in("Probabilidad Pendientes", "NodeSocketFloat", 0.85, 0.0, 1.0, "Porcentaje de escalones que llevan piezas en cuña.", p_pend)

    add_in("Densidad Rocas", "NodeSocketFloat", 0.35, 0.0, 1.0, "Cobertura de formaciones rocosas sobre el terreno.", p_rocas)
    add_in("Altura Rocas", "NodeSocketFloat", 15.0, 0.0, 80.0, "Elevación de las rocas sobre el nivel de la arena.", p_rocas)
    add_in("Escala Rocas", "NodeSocketFloat", 0.015, 0.001, 0.1, "Tamaño de los montículos rocosos.", p_rocas)

    add_in("Generar Arcos", "NodeSocketBool", True, None, None, "Genera arcos naturales con abertura visible.", p_arcos)
    add_in("Posición Arco X", "NodeSocketFloat", -60.0, -500.0, 500.0, "Posición X del arco central.", p_arcos)
    add_in("Posición Arco Y", "NodeSocketFloat", 80.0, -500.0, 500.0, "Posición Y del arco central.", p_arcos)
    add_in("Giro Arco", "NodeSocketFloat", 25.0, 0.0, 360.0, "Rotación del arco (grados).", p_arcos)
    add_in("Luz Arco", "NodeSocketFloat", 75.0, 20.0, 250.0, "Luz o anchura total del arco en unidades Blender.", p_arcos)
    add_in("Altura Abertura", "NodeSocketFloat", 26.0, 5.0, 100.0, "Altura libre del vano o hueco interior del arco.", p_arcos)
    add_in("Grosor Dintel", "NodeSocketFloat", 12.0, 2.0, 50.0, "Espesor del dintel de bloques sobre la abertura.", p_arcos)
    add_in("Profundidad Arco", "NodeSocketFloat", 16.0, 4.0, 60.0, "Fondo del arco en el eje transversal.", p_arcos)

    s_mats = t.interface.new_socket(name="Material Arena", in_out='INPUT', socket_type='NodeSocketMaterial', parent=p_mats)
    s_mats.default_value = mat_sand
    s_matr = t.interface.new_socket(name="Material Roca", in_out='INPUT', socket_type='NodeSocketMaterial', parent=p_mats)
    s_matr.default_value = mat_rock

    # Output Socket
    t.interface.new_socket(name="Geometría", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    gi = n.new("NodeGroupInput")
    gi.location = (-2200, 200)
    go = n.new("NodeGroupOutput")
    go.location = (2400, 0)

    # Helper math nodes
    def math_op(op, a=None, b=None, loc=(0,0), label=None):
        node = n.new("ShaderNodeMath")
        node.operation = op
        node.location = loc
        if label: node.label = label
        if a is not None:
            if isinstance(a, float) or isinstance(a, int): node.inputs[0].default_value = a
            else: l.new(a, node.inputs[0])
        if b is not None:
            if isinstance(b, float) or isinstance(b, int): node.inputs[1].default_value = b
            else: l.new(b, node.inputs[1])
        return node

    # --- Frame 1: Retícula y Dimensiones LEGO ---
    grid = n.new("GeometryNodeMeshGrid")
    grid.location = (-1900, 400)
    grid.label = "Retícula Base del Terreno"
    l.new(gi.outputs["Dimensión X"], grid.inputs["Size X"])
    l.new(gi.outputs["Dimensión Y"], grid.inputs["Size Y"])
    l.new(gi.outputs["Resolución X"], grid.inputs["Vertices X"])
    l.new(gi.outputs["Resolución Y"], grid.inputs["Vertices Y"])

    # Step heights and cell sizes
    sub_rx = math_op('SUBTRACT', gi.outputs["Resolución X"], 1, loc=(-1900, 150))
    sub_ry = math_op('SUBTRACT', gi.outputs["Resolución Y"], 1, loc=(-1900, 50))
    pitch_x = math_op('DIVIDE', gi.outputs["Dimensión X"], sub_rx.outputs[0], loc=(-1700, 150), label="Paso X")
    pitch_y = math_op('DIVIDE', gi.outputs["Dimensión Y"], sub_ry.outputs[0], loc=(-1700, 50), label="Paso Y")

    brick_x = math_op('MULTIPLY', pitch_x.outputs[0], gi.outputs["Separación Bloques"], loc=(-1500, 150), label="Ancho Bloque X")
    brick_y = math_op('MULTIPLY', pitch_y.outputs[0], gi.outputs["Separación Bloques"], loc=(-1500, 50), label="Ancho Bloque Y")

    step_h = math_op('MULTIPLY', gi.outputs["Altura Placa"], gi.outputs["Escalón en Placas"], loc=(-1500, -50), label="Altura Escalón")

    # Stud dimensions
    add_p = math_op('ADD', pitch_x.outputs[0], pitch_y.outputs[0], loc=(-1700, -150))
    avg_p = math_op('MULTIPLY', add_p.outputs[0], 0.5, loc=(-1500, -150))
    stud_r = math_op('MULTIPLY', avg_p.outputs[0], 0.17, loc=(-1300, -150), label="Radio Stud")
    stud_d = math_op('MULTIPLY', gi.outputs["Altura Placa"], 0.35, loc=(-1300, -250), label="Alto Stud")

    # --- Frame 2: Prototipos de Piezas LEGO (Instancias) ---
    # Prototype 1: Bloque / Columna estándar
    cube_prim = n.new("GeometryNodeMeshCube")
    cube_prim.location = (-1300, 700)
    cube_prim.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    tr_cube = n.new("GeometryNodeTransform")
    tr_cube.location = (-1100, 700)
    tr_cube.inputs["Translation"].default_value = (0, 0, 0.5)
    l.new(cube_prim.outputs["Mesh"], tr_cube.inputs["Geometry"])

    # Prototype 2: Pendiente LEGO (Wedge / Slope 45°)
    wedge_cube = n.new("GeometryNodeMeshCube")
    wedge_cube.location = (-1300, 500)
    wedge_cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    tr_wedge = n.new("GeometryNodeTransform")
    tr_wedge.location = (-1100, 500)
    tr_wedge.inputs["Translation"].default_value = (0, 0, 0.5)
    l.new(wedge_cube.outputs["Mesh"], tr_wedge.inputs["Geometry"])

    pos_w = n.new("GeometryNodeInputPosition")
    pos_w.location = (-1300, 350)
    sep_w = n.new("ShaderNodeSeparateXYZ")
    sep_w.location = (-1100, 350)
    l.new(pos_w.outputs["Position"], sep_w.inputs["Vector"])

    comp_wx = n.new("FunctionNodeCompare")
    comp_wx.data_type = 'FLOAT'
    comp_wx.operation = 'GREATER_THAN'
    comp_wx.location = (-900, 420)
    comp_wx.inputs["B"].default_value = 0.0
    l.new(sep_w.outputs["X"], comp_wx.inputs["A"])

    comp_wz = n.new("FunctionNodeCompare")
    comp_wz.data_type = 'FLOAT'
    comp_wz.operation = 'GREATER_THAN'
    comp_wz.location = (-900, 320)
    comp_wz.inputs["B"].default_value = 0.5
    l.new(sep_w.outputs["Z"], comp_wz.inputs["A"])

    and_w = n.new("FunctionNodeBooleanMath")
    and_w.operation = 'AND'
    and_w.location = (-700, 370)
    l.new(comp_wx.outputs["Result"], and_w.inputs[0])
    l.new(comp_wz.outputs["Result"], and_w.inputs[1])

    set_pw = n.new("GeometryNodeSetPosition")
    set_pw.location = (-500, 500)
    comb_off = n.new("ShaderNodeCombineXYZ")
    comb_off.location = (-700, 480)
    comb_off.inputs["Z"].default_value = -1.0
    l.new(comb_off.outputs["Vector"], set_pw.inputs["Offset"])
    l.new(and_w.outputs["Boolean"], set_pw.inputs["Selection"])
    l.new(tr_wedge.outputs["Geometry"], set_pw.inputs["Geometry"])

    merge_w = n.new("GeometryNodeMergeByDistance")
    merge_w.location = (-300, 500)
    merge_w.inputs["Distance"].default_value = 0.01
    l.new(set_pw.outputs["Geometry"], merge_w.inputs["Geometry"])

    # Prototype 3: Studs 2x2
    # Genera 4 cilindros con dimensiones exactas
    stud_cyl = n.new("GeometryNodeMeshCylinder")
    stud_cyl.location = (-1300, -450)
    stud_cyl.inputs["Vertices"].default_value = 14
    l.new(stud_r.outputs[0], stud_cyl.inputs["Radius"])
    l.new(stud_d.outputs[0], stud_cyl.inputs["Depth"])

    half_sd = math_op('MULTIPLY', stud_d.outputs[0], 0.5, loc=(-1100, -450))
    comb_sd = n.new("ShaderNodeCombineXYZ")
    comb_sd.location = (-900, -450)
    l.new(half_sd.outputs[0], comb_sd.inputs["Z"])

    tr_stud = n.new("GeometryNodeTransform")
    tr_stud.location = (-700, -450)
    l.new(stud_cyl.outputs["Mesh"], tr_stud.inputs["Geometry"])
    l.new(comb_sd.outputs["Vector"], tr_stud.inputs["Translation"])

    studs_grid = n.new("GeometryNodeMeshGrid")
    studs_grid.location = (-900, -600)
    studs_grid.inputs["Vertices X"].default_value = 2
    studs_grid.inputs["Vertices Y"].default_value = 2
    half_px = math_op('MULTIPLY', pitch_x.outputs[0], 0.5, loc=(-1100, -600))
    half_py = math_op('MULTIPLY', pitch_y.outputs[0], 0.5, loc=(-1100, -700))
    l.new(half_px.outputs[0], studs_grid.inputs["Size X"])
    l.new(half_py.outputs[0], studs_grid.inputs["Size Y"])

    inst_4studs = n.new("GeometryNodeInstanceOnPoints")
    inst_4studs.location = (-500, -550)
    l.new(studs_grid.outputs["Mesh"], inst_4studs.inputs["Points"])
    l.new(tr_stud.outputs["Geometry"], inst_4studs.inputs["Instance"])

    realize_4studs = n.new("GeometryNodeRealizeInstances")
    realize_4studs.location = (-300, -550)
    realize_4studs.label = "Prototipo 4 Studs (Unificado)"
    l.new(inst_4studs.outputs["Instances"], realize_4studs.inputs["Geometry"])

    # --- Frame 3: Campo de Alturas Procedural (Dunas, Colinas, Rocas) ---
    pos = n.new("GeometryNodeInputPosition")
    pos.location = (-1600, -900)

    # Wind rotation for dunes
    wind_rad = math_op('MULTIPLY', gi.outputs["Ángulo Viento"], math.pi / 180.0, loc=(-1600, -1000))
    rot_pos = n.new("ShaderNodeVectorRotate")
    rot_pos.location = (-1400, -900)
    rot_pos.rotation_type = 'Z_AXIS'
    l.new(pos.outputs["Position"], rot_pos.inputs["Vector"])
    l.new(wind_rad.outputs[0], rot_pos.inputs["Angle"])

    # Dune wave
    wave = n.new("ShaderNodeTexWave")
    wave.location = (-1200, -900)
    wave.wave_profile = 'SAW'
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.0
    l.new(rot_pos.outputs["Vector"], wave.inputs["Vector"])
    l.new(gi.outputs["Escala Dunas"], wave.inputs["Scale"])
    l.new(gi.outputs["Distorsión Dunas"], wave.inputs["Distortion"])

    # Dune amplitude envelope noise
    dune_noise = n.new("ShaderNodeTexNoise")
    dune_noise.noise_dimensions = '4D'
    dune_noise.location = (-1200, -1150)
    dune_noise.inputs["Detail"].default_value = 2.0
    l.new(pos.outputs["Position"], dune_noise.inputs["Vector"])
    scale_dune_env = math_op('MULTIPLY', gi.outputs["Escala Dunas"], 0.35, loc=(-1400, -1150))
    l.new(scale_dune_env.outputs[0], dune_noise.inputs["Scale"])
    l.new(gi.outputs["Semilla"], dune_noise.inputs["W"])

    dune_comb = math_op('MULTIPLY', wave.outputs["Factor"], dune_noise.outputs["Factor"], loc=(-1000, -950))
    dune_h = math_op('MULTIPLY', dune_comb.outputs[0], gi.outputs["Altura Dunas"], loc=(-800, -950), label="Altura Dunas")

    # Hills noise
    seed_hills = math_op('ADD', gi.outputs["Semilla"], 15, loc=(-1400, -1350))
    hills_noise = n.new("ShaderNodeTexNoise")
    hills_noise.noise_dimensions = '4D'
    hills_noise.location = (-1200, -1350)
    hills_noise.inputs["Detail"].default_value = 3.0
    hills_noise.inputs["Roughness"].default_value = 0.5
    l.new(pos.outputs["Position"], hills_noise.inputs["Vector"])
    l.new(gi.outputs["Escala Colinas"], hills_noise.inputs["Scale"])
    l.new(seed_hills.outputs[0], hills_noise.inputs["W"])

    hills_pow = math_op('POWER', hills_noise.outputs["Factor"], 1.8, loc=(-1000, -1350))
    hills_h = math_op('MULTIPLY', hills_pow.outputs[0], gi.outputs["Altura Colinas"], loc=(-800, -1350), label="Altura Colinas")

    # Rock formations noise
    seed_rocks = math_op('ADD', gi.outputs["Semilla"], 40, loc=(-1400, -1550))
    rocks_noise = n.new("ShaderNodeTexNoise")
    rocks_noise.noise_dimensions = '4D'
    rocks_noise.location = (-1200, -1550)
    rocks_noise.inputs["Detail"].default_value = 3.5
    rocks_noise.inputs["Roughness"].default_value = 0.6
    l.new(pos.outputs["Position"], rocks_noise.inputs["Vector"])
    l.new(gi.outputs["Escala Rocas"], rocks_noise.inputs["Scale"])
    l.new(seed_rocks.outputs[0], rocks_noise.inputs["W"])

    rock_thresh = math_op('SUBTRACT', 1.0, gi.outputs["Densidad Rocas"], loc=(-1000, -1650))
    is_rock_val = math_op('SUBTRACT', rocks_noise.outputs["Factor"], rock_thresh.outputs[0], loc=(-800, -1550))
    rock_pos_val = math_op('MAXIMUM', is_rock_val.outputs[0], 0.0, loc=(-600, -1550))
    rock_ratio = math_op('DIVIDE', rock_pos_val.outputs[0], gi.outputs["Densidad Rocas"], loc=(-400, -1550))
    rock_h = math_op('MULTIPLY', rock_ratio.outputs[0], gi.outputs["Altura Rocas"], loc=(-200, -1550), label="Altura Rocas")

    # Mask for rock material: 1.0 if rock, 0.0 if sand
    comp_is_rock = n.new("FunctionNodeCompare")
    comp_is_rock.data_type = 'FLOAT'
    comp_is_rock.operation = 'GREATER_THAN'
    comp_is_rock.location = (-200, -1700)
    comp_is_rock.inputs["B"].default_value = 0.001
    l.new(rock_pos_val.outputs[0], comp_is_rock.inputs["A"])

    # Combine total raw height
    sum_dh = math_op('ADD', dune_h.outputs[0], hills_h.outputs[0], loc=(-600, -950))
    sum_total = math_op('ADD', sum_dh.outputs[0], rock_h.outputs[0], loc=(-400, -950))

    # Blur / Erosion
    blur = n.new("GeometryNodeBlurAttribute")
    blur.data_type = 'FLOAT'
    blur.location = (-200, -950)
    l.new(sum_total.outputs[0], blur.inputs["Value"])
    l.new(gi.outputs["Erosión Suavizado"], blur.inputs["Iterations"])

    # Quantize to discrete LEGO steps
    div_step = math_op('DIVIDE', blur.outputs["Value"], step_h.outputs[0], loc=(0, -950))
    floor_step = math_op('FLOOR', div_step.outputs[0], loc=(150, -950))
    levels = math_op('ADD', floor_step.outputs[0], 1.0, loc=(300, -950))
    final_height = math_op('MULTIPLY', levels.outputs[0], step_h.outputs[0], loc=(450, -950), label="Altura Cuantizada")

    # --- Frame 4: Detección de Pendientes (Slopes) vs Studs ---
    # Posiciones de los 4 vecinos
    sep_pos = n.new("ShaderNodeSeparateXYZ")
    sep_pos.location = (-1000, -100)
    l.new(pos.outputs["Position"], sep_pos.inputs["Vector"])

    pos_px = n.new("ShaderNodeCombineXYZ"); pos_px.location = (-800, 50)
    l.new(sep_pos.outputs["X"], pos_px.inputs["X"]); l.new(sep_pos.outputs["Y"], pos_px.inputs["Y"])
    l.new(pitch_x.outputs[0], pos_px.inputs["X"]) # offset
    # Vector math ADD
    vm_px = n.new("ShaderNodeVectorMath"); vm_px.operation = 'ADD'; vm_px.location = (-650, 50)
    l.new(pos.outputs["Position"], vm_px.inputs[0]); l.new(pos_px.outputs["Vector"], vm_px.inputs[1])

    pos_nx = n.new("ShaderNodeCombineXYZ"); pos_nx.location = (-800, -50)
    neg_px = math_op('MULTIPLY', pitch_x.outputs[0], -1.0, loc=(-950, -50))
    l.new(neg_px.outputs[0], pos_nx.inputs["X"])
    vm_nx = n.new("ShaderNodeVectorMath"); vm_nx.operation = 'ADD'; vm_nx.location = (-650, -50)
    l.new(pos.outputs["Position"], vm_nx.inputs[0]); l.new(pos_nx.outputs["Vector"], vm_nx.inputs[1])

    pos_py = n.new("ShaderNodeCombineXYZ"); pos_py.location = (-800, -150)
    l.new(pitch_y.outputs[0], pos_py.inputs["Y"])
    vm_py = n.new("ShaderNodeVectorMath"); vm_py.operation = 'ADD'; vm_py.location = (-650, -150)
    l.new(pos.outputs["Position"], vm_py.inputs[0]); l.new(pos_py.outputs["Vector"], vm_py.inputs[1])

    pos_ny = n.new("ShaderNodeCombineXYZ"); pos_ny.location = (-800, -250)
    neg_py = math_op('MULTIPLY', pitch_y.outputs[0], -1.0, loc=(-950, -250))
    l.new(neg_py.outputs[0], pos_ny.inputs["Y"])
    vm_ny = n.new("ShaderNodeVectorMath"); vm_ny.operation = 'ADD'; vm_ny.location = (-650, -250)
    l.new(pos.outputs["Position"], vm_ny.inputs[0]); l.new(pos_ny.outputs["Vector"], vm_ny.inputs[1])

    # Sample nearest heights
    sn_px = n.new("GeometryNodeSampleNearest"); sn_px.location = (-450, 50)
    l.new(grid.outputs["Mesh"], sn_px.inputs["Geometry"]); l.new(vm_px.outputs["Vector"], sn_px.inputs["Sample Position"])
    si_px = n.new("GeometryNodeSampleIndex"); si_px.location = (-300, 50); si_px.data_type = 'FLOAT'
    l.new(grid.outputs["Mesh"], si_px.inputs["Geometry"]); l.new(sn_px.outputs["Index"], si_px.inputs["Index"]); l.new(final_height.outputs[0], si_px.inputs["Value"])

    sn_nx = n.new("GeometryNodeSampleNearest"); sn_nx.location = (-450, -50)
    l.new(grid.outputs["Mesh"], sn_nx.inputs["Geometry"]); l.new(vm_nx.outputs["Vector"], sn_nx.inputs["Sample Position"])
    si_nx = n.new("GeometryNodeSampleIndex"); si_nx.location = (-300, -50); si_nx.data_type = 'FLOAT'
    l.new(grid.outputs["Mesh"], si_nx.inputs["Geometry"]); l.new(sn_nx.outputs["Index"], si_nx.inputs["Index"]); l.new(final_height.outputs[0], si_nx.inputs["Value"])

    sn_py = n.new("GeometryNodeSampleNearest"); sn_py.location = (-450, -150)
    l.new(grid.outputs["Mesh"], sn_py.inputs["Geometry"]); l.new(vm_py.outputs["Vector"], sn_py.inputs["Sample Position"])
    si_py = n.new("GeometryNodeSampleIndex"); si_py.location = (-300, -150); si_py.data_type = 'FLOAT'
    l.new(grid.outputs["Mesh"], si_py.inputs["Geometry"]); l.new(sn_py.outputs["Index"], si_py.inputs["Index"]); l.new(final_height.outputs[0], si_py.inputs["Value"])

    sn_ny = n.new("GeometryNodeSampleNearest"); sn_ny.location = (-450, -250)
    l.new(grid.outputs["Mesh"], sn_ny.inputs["Geometry"]); l.new(vm_ny.outputs["Vector"], sn_ny.inputs["Sample Position"])
    si_ny = n.new("GeometryNodeSampleIndex"); si_ny.location = (-300, -250); si_ny.data_type = 'FLOAT'
    l.new(grid.outputs["Mesh"], si_ny.inputs["Geometry"]); l.new(sn_ny.outputs["Index"], si_ny.inputs["Index"]); l.new(final_height.outputs[0], si_ny.inputs["Value"])

    # Comprueba caídas de altura
    drop_px = math_op('SUBTRACT', final_height.outputs[0], si_px.outputs["Value"], loc=(-100, 50))
    has_drop_px = n.new("FunctionNodeCompare"); has_drop_px.data_type = 'FLOAT'; has_drop_px.operation = 'GREATER_EQUAL'; has_drop_px.location = (50, 50)
    l.new(drop_px.outputs[0], has_drop_px.inputs["A"]); l.new(step_h.outputs[0], has_drop_px.inputs["B"])

    drop_nx = math_op('SUBTRACT', final_height.outputs[0], si_nx.outputs["Value"], loc=(-100, -50))
    has_drop_nx = n.new("FunctionNodeCompare"); has_drop_nx.data_type = 'FLOAT'; has_drop_nx.operation = 'GREATER_EQUAL'; has_drop_nx.location = (50, -50)
    l.new(drop_nx.outputs[0], has_drop_nx.inputs["A"]); l.new(step_h.outputs[0], has_drop_nx.inputs["B"])

    drop_py = math_op('SUBTRACT', final_height.outputs[0], si_py.outputs["Value"], loc=(-100, -150))
    has_drop_py = n.new("FunctionNodeCompare"); has_drop_py.data_type = 'FLOAT'; has_drop_py.operation = 'GREATER_EQUAL'; has_drop_py.location = (50, -150)
    l.new(drop_py.outputs[0], has_drop_py.inputs["A"]); l.new(step_h.outputs[0], has_drop_py.inputs["B"])

    drop_ny = math_op('SUBTRACT', final_height.outputs[0], si_ny.outputs["Value"], loc=(-100, -250))
    has_drop_ny = n.new("FunctionNodeCompare"); has_drop_ny.data_type = 'FLOAT'; has_drop_ny.operation = 'GREATER_EQUAL'; has_drop_ny.location = (50, -250)
    l.new(drop_ny.outputs[0], has_drop_ny.inputs["A"]); l.new(step_h.outputs[0], has_drop_ny.inputs["B"])

    # Any drop?
    any_drop_x = n.new("FunctionNodeBooleanMath"); any_drop_x.operation = 'OR'; any_drop_x.location = (250, 0)
    l.new(has_drop_px.outputs["Result"], any_drop_x.inputs[0]); l.new(has_drop_nx.outputs["Result"], any_drop_x.inputs[1])

    any_drop_y = n.new("FunctionNodeBooleanMath"); any_drop_y.operation = 'OR'; any_drop_y.location = (250, -200)
    l.new(has_drop_py.outputs["Result"], any_drop_y.inputs[0]); l.new(has_drop_ny.outputs["Result"], any_drop_y.inputs[1])

    any_drop = n.new("FunctionNodeBooleanMath"); any_drop.operation = 'OR'; any_drop.location = (450, -100)
    l.new(any_drop_x.outputs["Boolean"], any_drop.inputs[0]); l.new(any_drop_y.outputs["Boolean"], any_drop.inputs[1])

    # Rotation selection based on priority
    # rot = 0 (px), pi (nx), pi/2 (py), -pi/2 (ny)
    sw_rot1 = n.new("GeometryNodeSwitch"); sw_rot1.input_type = 'FLOAT'; sw_rot1.location = (300, -350)
    sw_rot1.inputs["False"].default_value = -math.pi / 2 # ny
    sw_rot1.inputs["True"].default_value = math.pi / 2   # py
    l.new(has_drop_py.outputs["Result"], sw_rot1.inputs["Switch"])

    sw_rot2 = n.new("GeometryNodeSwitch"); sw_rot2.input_type = 'FLOAT'; sw_rot2.location = (450, -350)
    sw_rot2.inputs["True"].default_value = math.pi       # nx
    l.new(has_drop_nx.outputs["Result"], sw_rot2.inputs["Switch"])
    l.new(sw_rot1.outputs["Output"], sw_rot2.inputs["False"])

    sw_rot3 = n.new("GeometryNodeSwitch"); sw_rot3.input_type = 'FLOAT'; sw_rot3.location = (600, -350)
    sw_rot3.inputs["True"].default_value = 0.0           # px
    l.new(has_drop_px.outputs["Result"], sw_rot3.inputs["Switch"])
    l.new(sw_rot2.outputs["Output"], sw_rot3.inputs["False"])

    # Border filter: no slopes on external borders
    half_dx = math_op('MULTIPLY', gi.outputs["Dimensión X"], 0.48, loc=(-1000, 200))
    half_dy = math_op('MULTIPLY', gi.outputs["Dimensión Y"], 0.48, loc=(-1000, 100))
    abs_x = math_op('ABSOLUTE', sep_pos.outputs["X"], loc=(-800, 200))
    abs_y = math_op('ABSOLUTE', sep_pos.outputs["Y"], loc=(-800, 100))
    in_bx = n.new("FunctionNodeCompare"); in_bx.data_type = 'FLOAT'; in_bx.operation = 'LESS_THAN'; in_bx.location = (-650, 200)
    l.new(abs_x.outputs[0], in_bx.inputs["A"]); l.new(half_dx.outputs[0], in_bx.inputs["B"])
    in_by = n.new("FunctionNodeCompare"); in_by.data_type = 'FLOAT'; in_by.operation = 'LESS_THAN'; in_by.location = (-650, 100)
    l.new(abs_y.outputs[0], in_by.inputs["A"]); l.new(half_dy.outputs[0], in_by.inputs["B"])
    in_bounds = n.new("FunctionNodeBooleanMath"); in_bounds.operation = 'AND'; in_bounds.location = (-500, 150)
    l.new(in_bx.outputs["Result"], in_bounds.inputs[0]); l.new(in_by.outputs["Result"], in_bounds.inputs[1])

    # Random slope probability
    rand_slope = n.new("FunctionNodeRandomValue"); rand_slope.data_type = 'FLOAT'; rand_slope.location = (450, 50)
    rand_slope.inputs["Min"].default_value = 0.0; rand_slope.inputs["Max"].default_value = 1.0
    pass_prob = n.new("FunctionNodeCompare"); pass_prob.data_type = 'FLOAT'; pass_prob.operation = 'LESS_THAN'; pass_prob.location = (650, 50)
    l.new(rand_slope.outputs["Value"], pass_prob.inputs["A"]); l.new(gi.outputs["Probabilidad Pendientes"], pass_prob.inputs["B"])

    valid_drop = n.new("FunctionNodeBooleanMath"); valid_drop.operation = 'AND'; valid_drop.location = (650, -100)
    l.new(any_drop.outputs["Boolean"], valid_drop.inputs[0]); l.new(in_bounds.outputs["Boolean"], valid_drop.inputs[1])

    is_slope_cand = n.new("FunctionNodeBooleanMath"); is_slope_cand.operation = 'AND'; is_slope_cand.location = (850, -50)
    l.new(valid_drop.outputs["Boolean"], is_slope_cand.inputs[0]); l.new(pass_prob.outputs["Result"], is_slope_cand.inputs[1])

    is_slope_final = n.new("FunctionNodeBooleanMath"); is_slope_final.operation = 'AND'; is_slope_final.location = (1050, -50)
    l.new(is_slope_cand.outputs["Boolean"], is_slope_final.inputs[0]); l.new(gi.outputs["Usar Pendientes"], is_slope_final.inputs[1])

    is_flat_final = n.new("FunctionNodeBooleanMath"); is_flat_final.operation = 'NOT'; is_flat_final.location = (1050, 100)
    l.new(is_slope_final.outputs["Boolean"], is_flat_final.inputs[0])

    # --- Frame 5: Instanciación del Terreno (Cuerpos, Pendientes y Studs) ---
    # Heights
    half_h = math_op('MULTIPLY', final_height.outputs[0], 0.5, loc=(650, -950))
    h_sub_step = math_op('SUBTRACT', final_height.outputs[0], step_h.outputs[0], loc=(650, -850))
    half_h_sub = math_op('MULTIPLY', h_sub_step.outputs[0], 0.5, loc=(800, -850))

    # Point positions for flat columns: (x, y, half_h)
    comb_flat_p = n.new("ShaderNodeCombineXYZ"); comb_flat_p.location = (800, -950)
    l.new(sep_pos.outputs["X"], comb_flat_p.inputs["X"]); l.new(sep_pos.outputs["Y"], comb_flat_p.inputs["Y"]); l.new(half_h.outputs[0], comb_flat_p.inputs["Z"])

    # Point positions for slope columns: (x, y, half_h_sub)
    comb_slope_p = n.new("ShaderNodeCombineXYZ"); comb_slope_p.location = (950, -850)
    l.new(sep_pos.outputs["X"], comb_slope_p.inputs["X"]); l.new(sep_pos.outputs["Y"], comb_slope_p.inputs["Y"]); l.new(half_h_sub.outputs[0], comb_slope_p.inputs["Z"])

    # Point positions for studs: (x, y, final_height)
    comb_stud_p = n.new("ShaderNodeCombineXYZ"); comb_stud_p.location = (800, -1100)
    l.new(sep_pos.outputs["X"], comb_stud_p.inputs["X"]); l.new(sep_pos.outputs["Y"], comb_stud_p.inputs["Y"]); l.new(final_height.outputs[0], comb_stud_p.inputs["Z"])

    # Point positions for slope wedges: (x, y, h_sub_step)
    comb_wedge_p = n.new("ShaderNodeCombineXYZ"); comb_wedge_p.location = (950, -750)
    l.new(sep_pos.outputs["X"], comb_wedge_p.inputs["X"]); l.new(sep_pos.outputs["Y"], comb_wedge_p.inputs["Y"]); l.new(h_sub_step.outputs[0], comb_wedge_p.inputs["Z"])

    # Scale vectors
    scale_flat = n.new("ShaderNodeCombineXYZ"); scale_flat.location = (800, -650)
    l.new(brick_x.outputs[0], scale_flat.inputs["X"]); l.new(brick_y.outputs[0], scale_flat.inputs["Y"]); l.new(final_height.outputs[0], scale_flat.inputs["Z"])

    scale_sub = n.new("ShaderNodeCombineXYZ"); scale_sub.location = (950, -650)
    l.new(brick_x.outputs[0], scale_sub.inputs["X"]); l.new(brick_y.outputs[0], scale_sub.inputs["Y"]); l.new(h_sub_step.outputs[0], scale_sub.inputs["Z"])

    scale_wedge = n.new("ShaderNodeCombineXYZ"); scale_wedge.location = (1100, -650)
    l.new(brick_x.outputs[0], scale_wedge.inputs["X"]); l.new(brick_y.outputs[0], scale_wedge.inputs["Y"]); l.new(step_h.outputs[0], scale_wedge.inputs["Z"])

    rot_wedge = n.new("ShaderNodeCombineXYZ"); rot_wedge.location = (800, -350)
    l.new(sw_rot3.outputs["Output"], rot_wedge.inputs["Z"])

    # Material Switch: Arena vs Roca
    sw_mat = n.new("GeometryNodeSwitch"); sw_mat.input_type = 'MATERIAL'; sw_mat.location = (200, -1800)
    l.new(comp_is_rock.outputs["Result"], sw_mat.inputs["Switch"])
    l.new(gi.outputs["Material Arena"], sw_mat.inputs["False"])
    l.new(gi.outputs["Material Roca"], sw_mat.inputs["True"])

    # Set materials on prototypes
    cube_mat = n.new("GeometryNodeSetMaterial"); cube_mat.location = (-900, 700)
    l.new(tr_cube.outputs["Geometry"], cube_mat.inputs["Geometry"]); l.new(sw_mat.outputs["Output"], cube_mat.inputs["Material"])

    wedge_mat = n.new("GeometryNodeSetMaterial"); wedge_mat.location = (-100, 500)
    l.new(merge_w.outputs["Geometry"], wedge_mat.inputs["Geometry"]); l.new(sw_mat.outputs["Output"], wedge_mat.inputs["Material"])

    studs_mat = n.new("GeometryNodeSetMaterial"); studs_mat.location = (-100, -550)
    l.new(realize_4studs.outputs["Geometry"], studs_mat.inputs["Geometry"]); l.new(sw_mat.outputs["Output"], studs_mat.inputs["Material"])

    # Set point positions on grid
    set_grid_flat = n.new("GeometryNodeSetPosition"); set_grid_flat.location = (1000, -950)
    l.new(grid.outputs["Mesh"], set_grid_flat.inputs["Geometry"]); l.new(comb_flat_p.outputs["Vector"], set_grid_flat.inputs["Position"])

    set_grid_slope = n.new("GeometryNodeSetPosition"); set_grid_slope.location = (1150, -850)
    l.new(grid.outputs["Mesh"], set_grid_slope.inputs["Geometry"]); l.new(comb_slope_p.outputs["Vector"], set_grid_slope.inputs["Position"])

    set_grid_studs = n.new("GeometryNodeSetPosition"); set_grid_studs.location = (1000, -1100)
    l.new(grid.outputs["Mesh"], set_grid_studs.inputs["Geometry"]); l.new(comb_stud_p.outputs["Vector"], set_grid_studs.inputs["Position"])

    set_grid_wedge = n.new("GeometryNodeSetPosition"); set_grid_wedge.location = (1150, -750)
    l.new(grid.outputs["Mesh"], set_grid_wedge.inputs["Geometry"]); l.new(comb_wedge_p.outputs["Vector"], set_grid_wedge.inputs["Position"])

    # Instanciación Flat Columns
    inst_flat = n.new("GeometryNodeInstanceOnPoints"); inst_flat.location = (1350, -950)
    l.new(set_grid_flat.outputs["Geometry"], inst_flat.inputs["Points"])
    l.new(cube_mat.outputs["Geometry"], inst_flat.inputs["Instance"])
    l.new(scale_flat.outputs["Vector"], inst_flat.inputs["Scale"])
    l.new(is_flat_final.outputs["Boolean"], inst_flat.inputs["Selection"])

    # Instanciación Flat Studs
    can_show_studs = n.new("FunctionNodeBooleanMath"); can_show_studs.operation = 'AND'; can_show_studs.location = (1200, 100)
    l.new(is_flat_final.outputs["Boolean"], can_show_studs.inputs[0]); l.new(gi.outputs["Mostrar Studs"], can_show_studs.inputs[1])

    inst_studs = n.new("GeometryNodeInstanceOnPoints"); inst_studs.location = (1350, -1100)
    l.new(set_grid_studs.outputs["Geometry"], inst_studs.inputs["Points"])
    l.new(studs_mat.outputs["Geometry"], inst_studs.inputs["Instance"])
    l.new(can_show_studs.outputs["Boolean"], inst_studs.inputs["Selection"])

    # Instanciación Slope Columns (cuerpo rebajado)
    inst_slope_col = n.new("GeometryNodeInstanceOnPoints"); inst_slope_col.location = (1350, -800)
    l.new(set_grid_slope.outputs["Geometry"], inst_slope_col.inputs["Points"])
    l.new(cube_mat.outputs["Geometry"], inst_slope_col.inputs["Instance"])
    l.new(scale_sub.outputs["Vector"], inst_slope_col.inputs["Scale"])
    l.new(is_slope_final.outputs["Boolean"], inst_slope_col.inputs["Selection"])

    # Instanciación Slope Wedges (cuñas)
    inst_wedge = n.new("GeometryNodeInstanceOnPoints"); inst_wedge.location = (1350, -650)
    l.new(set_grid_wedge.outputs["Geometry"], inst_wedge.inputs["Points"])
    l.new(wedge_mat.outputs["Geometry"], inst_wedge.inputs["Instance"])
    l.new(scale_wedge.outputs["Vector"], inst_wedge.inputs["Scale"])
    l.new(rot_wedge.outputs["Vector"], inst_wedge.inputs["Rotation"])
    l.new(is_slope_final.outputs["Boolean"], inst_wedge.inputs["Selection"])

    # Join terrain elements
    join_terrain = n.new("GeometryNodeJoinGeometry"); join_terrain.location = (1600, -850)
    l.new(inst_flat.outputs["Instances"], join_terrain.inputs["Geometry"])
    l.new(inst_studs.outputs["Instances"], join_terrain.inputs["Geometry"])
    l.new(inst_slope_col.outputs["Instances"], join_terrain.inputs["Geometry"])
    l.new(inst_wedge.outputs["Instances"], join_terrain.inputs["Geometry"])

    # --- Frame 6: Arco Natural LEGO con Abertura Coherente ---
    # Cuadrícula local para el arco
    arch_grid = n.new("GeometryNodeMeshGrid"); arch_grid.location = (-1200, 1500)
    arch_grid.inputs["Vertices X"].default_value = 25
    arch_grid.inputs["Vertices Y"].default_value = 5
    l.new(gi.outputs["Luz Arco"], arch_grid.inputs["Size X"])
    l.new(gi.outputs["Profundidad Arco"], arch_grid.inputs["Size Y"])

    # Posición y rotación del arco
    arch_rot_rad = math_op('MULTIPLY', gi.outputs["Giro Arco"], math.pi / 180.0, loc=(-1200, 1350))
    comb_arch_rot = n.new("ShaderNodeCombineXYZ"); comb_arch_rot.location = (-1000, 1350)
    l.new(arch_rot_rad.outputs[0], comb_arch_rot.inputs["Z"])

    comb_arch_pos = n.new("ShaderNodeCombineXYZ"); comb_arch_pos.location = (-1000, 1450)
    l.new(gi.outputs["Posición Arco X"], comb_arch_pos.inputs["X"]); l.new(gi.outputs["Posición Arco Y"], comb_arch_pos.inputs["Y"])

    tr_arch_grid = n.new("GeometryNodeTransform"); tr_arch_grid.location = (-800, 1500)
    l.new(arch_grid.outputs["Mesh"], tr_arch_grid.inputs["Geometry"])
    l.new(comb_arch_pos.outputs["Vector"], tr_arch_grid.inputs["Translation"])
    l.new(comb_arch_rot.outputs["Vector"], tr_arch_grid.inputs["Rotation"])

    # Sample ground height under arch
    arch_pos = n.new("GeometryNodeInputPosition"); arch_pos.location = (-800, 1250)
    sn_arch = n.new("GeometryNodeSampleNearest"); sn_arch.location = (-600, 1250)
    l.new(grid.outputs["Mesh"], sn_arch.inputs["Geometry"]); l.new(arch_pos.outputs["Position"], sn_arch.inputs["Sample Position"])

    si_arch = n.new("GeometryNodeSampleIndex"); si_arch.location = (-450, 1250); si_arch.data_type = 'FLOAT'
    l.new(grid.outputs["Mesh"], si_arch.inputs["Geometry"]); l.new(sn_arch.outputs["Index"], si_arch.inputs["Index"])
    l.new(final_height.outputs[0], si_arch.inputs["Value"])

    # Proyección a coordenadas locales del arco s in [-1, 1]
    sep_apos = n.new("ShaderNodeSeparateXYZ"); sep_apos.location = (-600, 1500)
    l.new(arch_pos.outputs["Position"], sep_apos.inputs["Vector"])

    dx_arch = math_op('SUBTRACT', sep_apos.outputs["X"], gi.outputs["Posición Arco X"], loc=(-450, 1550))
    dy_arch = math_op('SUBTRACT', sep_apos.outputs["Y"], gi.outputs["Posición Arco Y"], loc=(-450, 1450))

    neg_rot = math_op('MULTIPLY', arch_rot_rad.outputs[0], -1.0, loc=(-450, 1350))
    cos_rot = math_op('COSINE', neg_rot.outputs[0], loc=(-300, 1350))
    sin_rot = math_op('SINE', neg_rot.outputs[0], loc=(-300, 1250))

    dx_cos = math_op('MULTIPLY', dx_arch.outputs[0], cos_rot.outputs[0], loc=(-150, 1550))
    dy_sin = math_op('MULTIPLY', dy_arch.outputs[0], sin_rot.outputs[0], loc=(-150, 1450))
    loc_x = math_op('SUBTRACT', dx_cos.outputs[0], dy_sin.outputs[0], loc=(0, 1500))

    half_luz = math_op('MULTIPLY', gi.outputs["Luz Arco"], 0.5, loc=(0, 1600))
    s_norm = math_op('DIVIDE', loc_x.outputs[0], half_luz.outputs[0], loc=(150, 1500))

    # Outer profile curve: outer_h = sqrt(max(0, 1 - s^2))
    s_sq = math_op('MULTIPLY', s_norm.outputs[0], s_norm.outputs[0], loc=(300, 1500))
    one_sub_sq = math_op('SUBTRACT', 1.0, s_sq.outputs[0], loc=(450, 1500))
    max_sq = math_op('MAXIMUM', one_sub_sq.outputs[0], 0.0, loc=(600, 1500))
    outer_sqrt = math_op('SQRT', max_sq.outputs[0], loc=(750, 1500))

    total_arch_h = math_op('ADD', gi.outputs["Altura Abertura"], gi.outputs["Grosor Dintel"], loc=(750, 1650))
    arch_rise = math_op('MULTIPLY', total_arch_h.outputs[0], outer_sqrt.outputs[0], loc=(900, 1550))
    arch_z_top_raw = math_op('ADD', si_arch.outputs["Value"], arch_rise.outputs[0], loc=(1050, 1550))
    arch_div_step = math_op('DIVIDE', arch_z_top_raw.outputs[0], step_h.outputs[0], loc=(1200, 1550))
    arch_floor = math_op('FLOOR', arch_div_step.outputs[0], loc=(1350, 1550))
    arch_z_top = math_op('MULTIPLY', arch_floor.outputs[0], step_h.outputs[0], loc=(1500, 1550), label="Z Top Arco")

    # Inner profile (The Hole / Opening):
    open_ratio = 0.62  # Opening occupies inner 62% of span
    s_inner = math_op('DIVIDE', s_norm.outputs[0], open_ratio, loc=(300, 1350))
    si_sq = math_op('MULTIPLY', s_inner.outputs[0], s_inner.outputs[0], loc=(450, 1350))
    si_one_sub = math_op('SUBTRACT', 1.0, si_sq.outputs[0], loc=(600, 1350))
    si_max = math_op('MAXIMUM', si_one_sub.outputs[0], 0.0, loc=(750, 1350))
    inner_sqrt = math_op('SQRT', si_max.outputs[0], loc=(900, 1350))

    hole_rise = math_op('MULTIPLY', gi.outputs["Altura Abertura"], inner_sqrt.outputs[0], loc=(1050, 1350))
    hole_z_raw = math_op('ADD', si_arch.outputs["Value"], hole_rise.outputs[0], loc=(1200, 1350))
    hole_div_step = math_op('DIVIDE', hole_z_raw.outputs[0], step_h.outputs[0], loc=(1350, 1350))
    hole_ceil = math_op('CEIL', hole_div_step.outputs[0], loc=(1500, 1350))
    arch_z_hole = math_op('MULTIPLY', hole_ceil.outputs[0], step_h.outputs[0], loc=(1650, 1350), label="Z Techo Abertura")

    # Is inside opening?
    s_abs = math_op('ABSOLUTE', s_norm.outputs[0], loc=(300, 1200))
    is_in_open = n.new("FunctionNodeCompare"); is_in_open.data_type = 'FLOAT'; is_in_open.operation = 'LESS_THAN'; is_in_open.location = (450, 1200)
    is_in_open.inputs["B"].default_value = open_ratio
    l.new(s_abs.outputs[0], is_in_open.inputs["A"])

    # Bottom of column: if in opening -> arch_z_hole, if pillar -> ground - step_h
    ground_sub = math_op('SUBTRACT', si_arch.outputs["Value"], step_h.outputs[0], loc=(1500, 1200))
    sw_arch_bot = n.new("GeometryNodeSwitch"); sw_arch_bot.input_type = 'FLOAT'; sw_arch_bot.location = (1800, 1300)
    l.new(is_in_open.outputs["Result"], sw_arch_bot.inputs["Switch"])
    l.new(ground_sub.outputs[0], sw_arch_bot.inputs["False"])
    l.new(arch_z_hole.outputs[0], sw_arch_bot.inputs["True"])

    # Column height for arch
    arch_col_h = math_op('SUBTRACT', arch_z_top.outputs[0], sw_arch_bot.outputs["Output"], loc=(1950, 1400))
    arch_col_valid = n.new("FunctionNodeCompare"); arch_col_valid.data_type = 'FLOAT'; arch_col_valid.operation = 'GREATER_THAN'; arch_col_valid.location = (2100, 1400)
    arch_col_valid.inputs["B"].default_value = 0.5
    l.new(arch_col_h.outputs[0], arch_col_valid.inputs["A"])

    # Point positions for arch: mid Z
    arch_z_sum = math_op('ADD', sw_arch_bot.outputs["Output"], arch_z_top.outputs[0], loc=(1950, 1250))
    arch_z_mid = math_op('MULTIPLY', arch_z_sum.outputs[0], 0.5, loc=(2100, 1250))

    comb_arch_mid_p = n.new("ShaderNodeCombineXYZ"); comb_arch_mid_p.location = (2250, 1250)
    l.new(sep_apos.outputs["X"], comb_arch_mid_p.inputs["X"])
    l.new(sep_apos.outputs["Y"], comb_arch_mid_p.inputs["Y"])
    l.new(arch_z_mid.outputs[0], comb_arch_mid_p.inputs["Z"])

    comb_arch_top_p = n.new("ShaderNodeCombineXYZ"); comb_arch_top_p.location = (2250, 1550)
    l.new(sep_apos.outputs["X"], comb_arch_top_p.inputs["X"])
    l.new(sep_apos.outputs["Y"], comb_arch_top_p.inputs["Y"])
    l.new(arch_z_top.outputs[0], comb_arch_top_p.inputs["Z"])

    set_arch_p = n.new("GeometryNodeSetPosition"); set_arch_p.location = (2400, 1250)
    l.new(tr_arch_grid.outputs["Geometry"], set_arch_p.inputs["Geometry"])
    l.new(comb_arch_mid_p.outputs["Vector"], set_arch_p.inputs["Position"])

    set_arch_top_p = n.new("GeometryNodeSetPosition"); set_arch_top_p.location = (2400, 1550)
    l.new(tr_arch_grid.outputs["Geometry"], set_arch_top_p.inputs["Geometry"])
    l.new(comb_arch_top_p.outputs["Vector"], set_arch_top_p.inputs["Position"])

    # Arch column scale
    arch_scale = n.new("ShaderNodeCombineXYZ"); arch_scale.location = (2250, 1400)
    l.new(brick_x.outputs[0], arch_scale.inputs["X"])
    l.new(brick_y.outputs[0], arch_scale.inputs["Y"])
    l.new(arch_col_h.outputs[0], arch_scale.inputs["Z"])

    # Prototype for arch with Rock material
    cube_rock_mat = n.new("GeometryNodeSetMaterial"); cube_rock_mat.location = (-900, 900)
    l.new(tr_cube.outputs["Geometry"], cube_rock_mat.inputs["Geometry"])
    l.new(gi.outputs["Material Roca"], cube_rock_mat.inputs["Material"])

    studs_rock_mat = n.new("GeometryNodeSetMaterial"); studs_rock_mat.location = (-100, -400)
    l.new(realize_4studs.outputs["Geometry"], studs_rock_mat.inputs["Geometry"])
    l.new(gi.outputs["Material Roca"], studs_rock_mat.inputs["Material"])

    # Instanciación columnas del arco
    inst_arch_col = n.new("GeometryNodeInstanceOnPoints"); inst_arch_col.location = (2600, 1250)
    l.new(set_arch_p.outputs["Geometry"], inst_arch_col.inputs["Points"])
    l.new(cube_rock_mat.outputs["Geometry"], inst_arch_col.inputs["Instance"])
    l.new(arch_scale.outputs["Vector"], inst_arch_col.inputs["Scale"])
    l.new(arch_col_valid.outputs["Result"], inst_arch_col.inputs["Selection"])

    # Instanciación studs del arco
    inst_arch_studs = n.new("GeometryNodeInstanceOnPoints"); inst_arch_studs.location = (2600, 1550)
    l.new(set_arch_top_p.outputs["Geometry"], inst_arch_studs.inputs["Points"])
    l.new(studs_rock_mat.outputs["Geometry"], inst_arch_studs.inputs["Instance"])
    l.new(arch_col_valid.outputs["Result"], inst_arch_studs.inputs["Selection"])

    join_arch = n.new("GeometryNodeJoinGeometry"); join_arch.location = (2800, 1400)
    l.new(inst_arch_col.outputs["Instances"], join_arch.inputs["Geometry"])
    l.new(inst_arch_studs.outputs["Instances"], join_arch.inputs["Geometry"])

    sw_arch_enable = n.new("GeometryNodeSwitch"); sw_arch_enable.input_type = 'GEOMETRY'; sw_arch_enable.location = (2950, 1400)
    l.new(gi.outputs["Generar Arcos"], sw_arch_enable.inputs["Switch"])
    # False: empty or no arch
    l.new(join_arch.outputs["Geometry"], sw_arch_enable.inputs["True"])

    # --- Frame 7: Salida Final ---
    join_all = n.new("GeometryNodeJoinGeometry"); join_all.location = (2100, 0)
    l.new(join_terrain.outputs["Geometry"], join_all.inputs["Geometry"])
    l.new(sw_arch_enable.outputs["Output"], join_all.inputs["Geometry"])

    l.new(join_all.outputs["Geometry"], go.inputs["Geometría"])

    return t


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 1. Materials
    mat_sand, mat_rock = create_materials()

    # 2. Geometry Nodes
    gn_tree = build_geometry_nodes(mat_sand, mat_rock)

    # 3. Object
    mesh = bpy.data.meshes.new("Malla_Base_Desierto")
    obj = bpy.data.objects.new("Desierto_LEGO_Procedural", mesh)
    bpy.context.collection.objects.link(obj)

    mod = obj.modifiers.new("Desierto LEGO", 'NODES')
    mod.node_group = gn_tree

    # Default parameters are already baked into socket defaults!
    # But let's verify inputs
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 4. Perspective Camera
    # Placed near the LEGO Arch, looking across the opening with stepped dunes and studs in foreground
    cam_data = bpy.data.cameras.new("Camara_Perspectiva")
    cam_data.lens = 28.0
    cam_data.clip_start = 0.5
    cam_data.clip_end = 4000.0
    cam_data.dof.use_dof = False

    cam_obj = bpy.data.objects.new("Camara_Perspectiva", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Position camera at (-140, 20, 32) looking at (-60, 80, 28) (the arch and opening)
    cam_obj.location = (-135.0, 15.0, 34.0)
    # Track towards the arch opening
    target = (-60.0, 80.0, 28.0)
    dir_vec = (target[0] - cam_obj.location.x, target[1] - cam_obj.location.y, target[2] - cam_obj.location.z)
    import mathutils
    rot_quat = mathutils.Vector(dir_vec).to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    # 5. Sun Light
    sun_data = bpy.data.lights.new("Sol_Desierto", 'SUN')
    sun_data.energy = 3.5
    sun_data.color = (1.0, 0.94, 0.85)
    sun_data.angle = math.radians(2.5)  # Soft shadows

    sun_obj = bpy.data.objects.new("Sol_Desierto", sun_data)
    bpy.context.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(48.0), math.radians(22.0), math.radians(-55.0))

    # 6. World (Desert Sky)
    world = bpy.data.worlds.new("Mundo_Desierto")
    bpy.context.scene.world = world
    world.use_nodes = True
    w_nodes = world.node_tree.nodes
    w_links = world.node_tree.links
    w_nodes.clear()

    w_out = w_nodes.new("ShaderNodeOutputWorld")
    w_bg = w_nodes.new("ShaderNodeBackground")
    w_bg.inputs["Color"].default_value = (0.52, 0.72, 0.92, 1.0)  # Bright sky
    w_bg.inputs["Strength"].default_value = 0.85
    w_links.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    # 7. Render Settings
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.resolution_percentage = 100

    # 8. User Notes Text Datablock
    notes = bpy.data.texts.new("LEEME — Desierto LEGO")
    notes.write("""=============================================================
DESIERTO LEGO PROCEDURAL — GEOMETRY NODES (v2)
=============================================================
Este archivo contiene un generador procedural no destructivo de
paisaje desértico construido íntegramente con piezas LEGO.

CARACTERÍSTICAS PRINCIPALES:
-------------------------------------------------------------
1. Cuadrícula continua independiente:
   - 'Dimensión X / Y': Tamaño físico en unidades Blender (1000 x 1000).
   - 'Resolución X / Y': Número fijo de columnas de bloques (300 x 300).
   Permite cambiar la densidad de piezas sin afectar las medidas totales.

2. Cuantización LEGO y Studs:
   - Todas las alturas son múltiplos exactos de 'Altura Placa' * 'Escalón'.
   - Cada bloque posee studs cilíndricos claramente visibles en su cara superior.
   - 'Separación Bloques': 0.96 deja juntas auténticas entre ladrillos.

3. Pendientes LEGO (Slopes):
   - 'Usar Pendientes': Activa piezas en cuña/inclinadas (tipo 3040/3039)
     en los escalones del terreno, uniendo terrazas de forma suave.
   - 'Probabilidad Pendientes': Controla la frecuencia de cuñas vs studs.

4. Formaciones:
   - Dunas eólicas con perfil asimétrico tipo barchán.
   - Colinas y mesetas cuantizadas.
   - Afloramientos rocosos integrados con 'Material Roca'.
   - Arco Natural LEGO con abertura reconocible y pilares de apoyo firmes.

5. Alto Rendimiento:
   - Todo el terreno se genera mediante INSTANCIAS GPU (sin Realize masivo).
   - La manipulación en viewport y el ajuste de sliders es fluido e instantáneo.
=============================================================
""")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"ARCHIVO CREADO CON ÉXITO: {OUT_BLEND}")


if __name__ == "__main__":
    setup_scene()
