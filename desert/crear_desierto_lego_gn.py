import bpy

OUT = "/home/kheiron/blender/desert/Desierto_LEGO_Geometry_Nodes.blend"


def inp(tree, name, kind, default, lo, hi, description, parent):
    s = tree.interface.new_socket(name=name, in_out='INPUT', socket_type=kind,
                                  description=description, parent=parent)
    s.default_value = default
    s.min_value = lo
    s.max_value = hi
    return s


def math(nodes, op, b=None, label=None):
    n = nodes.new("ShaderNodeMath")
    n.operation = op
    if b is not None:
        n.inputs[1].default_value = b
    if label:
        n.label = label
    return n


def vector(nodes, x=None, y=None, z=None):
    n = nodes.new("ShaderNodeCombineXYZ")
    if x is not None: n.inputs["X"].default_value = x
    if y is not None: n.inputs["Y"].default_value = y
    if z is not None: n.inputs["Z"].default_value = z
    return n


def material(name, dark, light):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nd, lk = mat.node_tree.nodes, mat.node_tree.links
    nd.clear()
    out = nd.new("ShaderNodeOutputMaterial")
    out.location = (530, 0)
    bsdf = nd.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (290, 0)
    bsdf.inputs["Roughness"].default_value = 0.76
    noise = nd.new("ShaderNodeTexNoise")
    noise.location = (-460, 0)
    noise.inputs["Scale"].default_value = 0.55
    noise.inputs["Detail"].default_value = 3.5
    ramp = nd.new("ShaderNodeValToRGB")
    ramp.location = (-180, 0)
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    lk.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    lk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    lk.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def transform(nodes, geometry, translation, location):
    n = nodes.new("GeometryNodeTransform")
    n.location = location
    nodes.id_data.links.new(geometry, n.inputs["Geometry"])
    nodes.id_data.links.new(translation, n.inputs["Translation"])
    return n


def build(sand, rock):
    t = bpy.data.node_groups.new("GN_Desierto_LEGO_Continuo", "GeometryNodeTree")
    terrain = t.interface.new_panel("Terreno LEGO")
    forms = t.interface.new_panel("Formaciones LEGO")
    inp(t, "Dimensión X", "NodeSocketInt", 1000, 8, 10000,
        "Ancho en unidades Blender enteras.", terrain)
    inp(t, "Dimensión Y", "NodeSocketInt", 1000, 8, 10000,
        "Largo en unidades Blender enteras.", terrain)
    inp(t, "Subdivisiones X", "NodeSocketInt", 125, 2, 512,
        "Número fijo de columnas de bloques LEGO en X.", terrain)
    inp(t, "Subdivisiones Y", "NodeSocketInt", 125, 2, 512,
        "Número fijo de columnas de bloques LEGO en Y.", terrain)
    inp(t, "Semilla", "NodeSocketInt", 14, 0, 100000,
        "Cambia el patrón de dunas, rocas y arcos.", terrain)
    inp(t, "Niveles Máximos", "NodeSocketInt", 12, 1, 100,
        "Altura máxima, medida en placas/bloques discretos.", terrain)
    inp(t, "Altura Placa", "NodeSocketFloat", 2.0, 0.1, 50.0,
        "Altura visual de una placa LEGO; la escala es libre.", terrain)
    inp(t, "Escala Dunas", "NodeSocketFloat", 0.009, 0.0001, 1.0,
        "Tamaño de las dunas: menor valor produce dunas más grandes.", terrain)
    inp(t, "Detalle Dunas", "NodeSocketFloat", 0.34, 0.0, 1.0,
        "Cantidad de detalle fino antes de cuantizar la altura.", terrain)
    inp(t, "Densidad Rocas", "NodeSocketFloat", 0.00008, 0.0, 0.005,
        "Formaciones rocosas LEGO por unidad cuadrada.", forms)
    inp(t, "Densidad Arcos", "NodeSocketFloat", 0.000006, 0.0, 0.0005,
        "Arcos/puentes LEGO por unidad cuadrada.", forms)
    inp(t, "Escala Formaciones", "NodeSocketFloat", 1.0, 0.1, 8.0,
        "Escala global de rocas y arcos.", forms)
    t.interface.new_socket(name="Geometría", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n, l = t.nodes, t.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    gi.location, go.location = (-1600, 40), (1550, 180)

    # Fixed-resolution grid: every vertex becomes a LEGO terrain column.
    grid = n.new("GeometryNodeMeshGrid")
    grid.location = (-1360, 220)
    grid.label = "Retícula continua de columnas LEGO"
    l.new(gi.outputs["Dimensión X"], grid.inputs["Size X"])
    l.new(gi.outputs["Dimensión Y"], grid.inputs["Size Y"])
    l.new(gi.outputs["Subdivisiones X"], grid.inputs["Vertices X"])
    l.new(gi.outputs["Subdivisiones Y"], grid.inputs["Vertices Y"])

    # Compute the free-scale brick pitch from terrain dimensions and fixed cell count.
    sxm1, sym1 = math(n, 'SUBTRACT', 1), math(n, 'SUBTRACT', 1)
    sxm1.location, sym1.location = (-1360, 20), (-1360, -50)
    l.new(gi.outputs["Subdivisiones X"], sxm1.inputs[0])
    l.new(gi.outputs["Subdivisiones Y"], sym1.inputs[0])
    pitch_x, pitch_y = math(n, 'DIVIDE'), math(n, 'DIVIDE')
    pitch_x.location, pitch_y.location = (-1170, 20), (-1170, -50)
    l.new(gi.outputs["Dimensión X"], pitch_x.inputs[0]); l.new(sxm1.outputs[0], pitch_x.inputs[1])
    l.new(gi.outputs["Dimensión Y"], pitch_y.inputs[0]); l.new(sym1.outputs[0], pitch_y.inputs[1])
    brick_x, brick_y = math(n, 'MULTIPLY', .965), math(n, 'MULTIPLY', .965)
    brick_x.location, brick_y.location = (-980, 20), (-980, -50)
    l.new(pitch_x.outputs[0], brick_x.inputs[0]); l.new(pitch_y.outputs[0], brick_y.inputs[0])

    # Height field, explicitly rounded down to discrete LEGO levels.
    pos = n.new("GeometryNodeInputPosition"); pos.location = (-1360, -260)
    dunes = n.new("ShaderNodeTexNoise")
    dunes.location = (-1150, -280); dunes.noise_dimensions = '4D'
    dunes.inputs["Detail"].default_value = 2.0
    dunes.inputs["Roughness"].default_value = .55
    l.new(pos.outputs["Position"], dunes.inputs["Vector"])
    l.new(gi.outputs["Escala Dunas"], dunes.inputs["Scale"])
    l.new(gi.outputs["Semilla"], dunes.inputs["W"])
    fine = n.new("ShaderNodeTexNoise")
    fine.location = (-1150, -460); fine.noise_dimensions = '4D'
    fine.inputs["Scale"].default_value = .045
    fine.inputs["Detail"].default_value = 2.0
    l.new(pos.outputs["Position"], fine.inputs["Vector"])
    l.new(gi.outputs["Semilla"], fine.inputs["W"])
    detail_center = math(n, 'SUBTRACT', .5); detail_center.location = (-960, -460)
    detail_scale = math(n, 'MULTIPLY'); detail_scale.location = (-780, -460)
    l.new(fine.outputs["Fac"], detail_center.inputs[0])
    l.new(detail_center.outputs[0], detail_scale.inputs[0])
    l.new(gi.outputs["Detalle Dunas"], detail_scale.inputs[1])
    add_noise = math(n, 'ADD'); add_noise.location = (-590, -340)
    l.new(dunes.outputs["Fac"], add_noise.inputs[0]); l.new(detail_scale.outputs[0], add_noise.inputs[1])
    clamp = math(n, 'MAXIMUM', 0.0); clamp.location = (-410, -340)
    l.new(add_noise.outputs[0], clamp.inputs[0])
    levels_float = math(n, 'MULTIPLY'); levels_float.location = (-230, -330)
    l.new(clamp.outputs[0], levels_float.inputs[0]); l.new(gi.outputs["Niveles Máximos"], levels_float.inputs[1])
    levels_floor = math(n, 'FLOOR'); levels_floor.location = (-50, -330)
    l.new(levels_float.outputs[0], levels_floor.inputs[0])
    levels = math(n, 'ADD', 1.0); levels.location = (130, -330)
    l.new(levels_floor.outputs[0], levels.inputs[0])
    height = math(n, 'MULTIPLY'); height.location = (310, -330)
    l.new(levels.outputs[0], height.inputs[0]); l.new(gi.outputs["Altura Placa"], height.inputs[1])

    # Body of a brick column. Gaps preserve the visible LEGO grid.
    cube = n.new("GeometryNodeMeshCube"); cube.location = (80, 170)
    sand_cube = n.new("GeometryNodeSetMaterial"); sand_cube.location = (250, 170)
    sand_cube.inputs["Material"].default_value = sand
    l.new(cube.outputs["Mesh"], sand_cube.inputs["Geometry"])
    body_scale = vector(n); body_scale.location = (320, -100)
    l.new(brick_x.outputs[0], body_scale.inputs["X"])
    l.new(brick_y.outputs[0], body_scale.inputs["Y"])
    l.new(height.outputs[0], body_scale.inputs["Z"])
    half_height = math(n, 'MULTIPLY', .5); half_height.location = (490, -330)
    l.new(height.outputs[0], half_height.inputs[0])
    body_move = vector(n); body_move.location = (680, -260)
    l.new(half_height.outputs[0], body_move.inputs["Z"])
    body = n.new("GeometryNodeInstanceOnPoints"); body.location = (710, 180)
    l.new(grid.outputs["Mesh"], body.inputs["Points"])
    l.new(sand_cube.outputs["Geometry"], body.inputs["Instance"])
    l.new(body_scale.outputs["Vector"], body.inputs["Scale"])
    body_translate = n.new("GeometryNodeTranslateInstances"); body_translate.location = (890, 180)
    l.new(body.outputs["Instances"], body_translate.inputs["Instances"])
    l.new(body_move.outputs["Vector"], body_translate.inputs["Translation"])

    # Four visible studs per terrain cell; their positions respond to the free brick pitch.
    stud = n.new("GeometryNodeMeshCylinder"); stud.location = (-80, -700)
    stud.inputs["Vertices"].default_value = 12
    stud.inputs["Radius"].default_value = 1.0
    stud.inputs["Depth"].default_value = 1.0
    stud_mat = n.new("GeometryNodeSetMaterial"); stud_mat.location = (90, -700)
    stud_mat.inputs["Material"].default_value = sand
    l.new(stud.outputs["Mesh"], stud_mat.inputs["Geometry"])
    avg_pitch = math(n, 'ADD'); avg_pitch.location = (-780, -650)
    avg_half = math(n, 'MULTIPLY', .5); avg_half.location = (-610, -650)
    stud_radius = math(n, 'MULTIPLY', .155); stud_radius.location = (-430, -650)
    l.new(pitch_x.outputs[0], avg_pitch.inputs[0]); l.new(pitch_y.outputs[0], avg_pitch.inputs[1])
    l.new(avg_pitch.outputs[0], avg_half.inputs[0]); l.new(avg_half.outputs[0], stud_radius.inputs[0])
    stud_scale = vector(n, z=.32); stud_scale.location = (-230, -610)
    l.new(stud_radius.outputs[0], stud_scale.inputs["X"]); l.new(stud_radius.outputs[0], stud_scale.inputs["Y"])
    scale_stud = n.new("GeometryNodeTransform"); scale_stud.location = (270, -700)
    l.new(stud_mat.outputs["Geometry"], scale_stud.inputs["Geometry"])
    l.new(stud_scale.outputs["Vector"], scale_stud.inputs["Scale"])
    off_x, off_y = math(n, 'MULTIPLY', .25), math(n, 'MULTIPLY', .25)
    off_x.location, off_y.location = (-780, -740), (-780, -800)
    l.new(pitch_x.outputs[0], off_x.inputs[0]); l.new(pitch_y.outputs[0], off_y.inputs[0])
    neg_x, neg_y = math(n, 'MULTIPLY', -1.0), math(n, 'MULTIPLY', -1.0)
    neg_x.location, neg_y.location = (-590, -740), (-590, -800)
    l.new(off_x.outputs[0], neg_x.inputs[0]); l.new(off_y.outputs[0], neg_y.inputs[0])
    translations = []
    for x, y, loc in [(off_x, off_y, (470, -610)), (off_x, neg_y, (470, -710)),
                      (neg_x, off_y, (470, -810)), (neg_x, neg_y, (470, -910))]:
        v = vector(n); v.location = loc
        l.new(x.outputs[0], v.inputs["X"]); l.new(y.outputs[0], v.inputs["Y"])
        translations.append(v)
    studs_join = n.new("GeometryNodeJoinGeometry"); studs_join.location = (690, -720)
    for tr in translations:
        moved = n.new("GeometryNodeTransform"); moved.location = (650, tr.location.y)
        l.new(scale_stud.outputs["Geometry"], moved.inputs["Geometry"])
        l.new(tr.outputs["Vector"], moved.inputs["Translation"])
        l.new(moved.outputs["Geometry"], studs_join.inputs["Geometry"])
    stud_z = math(n, 'ADD', .16); stud_z.location = (850, -390)
    l.new(height.outputs[0], stud_z.inputs[0])
    studs_move = vector(n); studs_move.location = (1030, -390)
    l.new(stud_z.outputs[0], studs_move.inputs["Z"])
    top_studs = n.new("GeometryNodeInstanceOnPoints"); top_studs.location = (1050, -640)
    l.new(grid.outputs["Mesh"], top_studs.inputs["Points"])
    l.new(studs_join.outputs["Geometry"], top_studs.inputs["Instance"])
    studs_translate = n.new("GeometryNodeTranslateInstances"); studs_translate.location = (1210, -640)
    l.new(top_studs.outputs["Instances"], studs_translate.inputs["Instances"])
    l.new(studs_move.outputs["Vector"], studs_translate.inputs["Translation"])

    # Rock outcrops are scaled LEGO blocks. Placement height uses the same rounded field.
    rock_points = n.new("GeometryNodeDistributePointsOnFaces"); rock_points.location = (280, 520)
    rock_points.distribute_method = 'RANDOM'
    l.new(grid.outputs["Mesh"], rock_points.inputs["Mesh"])
    l.new(gi.outputs["Densidad Rocas"], rock_points.inputs["Density"])
    l.new(gi.outputs["Semilla"], rock_points.inputs["Seed"])
    rock_cube = n.new("GeometryNodeMeshCube"); rock_cube.location = (290, 400)
    rock_set = n.new("GeometryNodeSetMaterial"); rock_set.location = (470, 400)
    rock_set.inputs["Material"].default_value = rock
    l.new(rock_cube.outputs["Mesh"], rock_set.inputs["Geometry"])
    rand = n.new("FunctionNodeRandomValue"); rand.location = (490, 570); rand.data_type = 'FLOAT_VECTOR'
    rand.inputs["Min"].default_value = (2.0, 1.5, 2.5)
    rand.inputs["Max"].default_value = (7.0, 5.0, 9.0)
    rock_base = vector(n); rock_base.location = (680, 520)
    l.new(brick_x.outputs[0], rock_base.inputs["X"]); l.new(brick_y.outputs[0], rock_base.inputs["Y"])
    l.new(gi.outputs["Altura Placa"], rock_base.inputs["Z"])
    rock_size = n.new("ShaderNodeVectorMath"); rock_size.operation = 'MULTIPLY'; rock_size.location = (860, 540)
    l.new(rock_base.outputs["Vector"], rock_size.inputs[0]); l.new(rand.outputs["Value"], rock_size.inputs[1])
    rock_global = n.new("ShaderNodeVectorMath"); rock_global.operation = 'SCALE'; rock_global.location = (1040, 540)
    l.new(rock_size.outputs["Vector"], rock_global.inputs[0]); l.new(gi.outputs["Escala Formaciones"], rock_global.inputs["Scale"])
    rock_z = n.new("ShaderNodeSeparateXYZ"); rock_z.location = (1040, 430)
    l.new(rock_global.outputs["Vector"], rock_z.inputs["Vector"])
    rock_half = math(n, 'MULTIPLY', .5); rock_half.location = (1210, 430)
    l.new(rock_z.outputs["Z"], rock_half.inputs[0])
    rock_lift = math(n, 'ADD'); rock_lift.location = (1380, 430)
    l.new(height.outputs[0], rock_lift.inputs[0]); l.new(rock_half.outputs[0], rock_lift.inputs[1])
    rock_move = vector(n); rock_move.location = (1390, 520)
    l.new(rock_lift.outputs[0], rock_move.inputs["Z"])
    rock_inst = n.new("GeometryNodeInstanceOnPoints"); rock_inst.location = (1240, 650)
    l.new(rock_points.outputs["Points"], rock_inst.inputs["Points"])
    l.new(rock_set.outputs["Geometry"], rock_inst.inputs["Instance"])
    l.new(rock_global.outputs["Vector"], rock_inst.inputs["Scale"])
    rock_translate = n.new("GeometryNodeTranslateInstances"); rock_translate.location = (1420, 650)
    l.new(rock_inst.outputs["Instances"], rock_translate.inputs["Instances"])
    l.new(rock_move.outputs["Vector"], rock_translate.inputs["Translation"])

    # A bridge-style desert arch built from three LEGO-scale blocks, not reference meshes.
    pillar_size = vector(n); pillar_size.location = (-20, 800)
    px2, py2, pz8 = math(n, 'MULTIPLY', 2), math(n, 'MULTIPLY', 2), math(n, 'MULTIPLY', 8)
    px2.location, py2.location, pz8.location = (-220, 780), (-220, 830), (-220, 880)
    l.new(brick_x.outputs[0], px2.inputs[0]); l.new(brick_y.outputs[0], py2.inputs[0]); l.new(gi.outputs["Altura Placa"], pz8.inputs[0])
    l.new(px2.outputs[0], pillar_size.inputs["X"]); l.new(py2.outputs[0], pillar_size.inputs["Y"]); l.new(pz8.outputs[0], pillar_size.inputs["Z"])
    pillar = n.new("GeometryNodeMeshCube"); pillar.location = (170, 820)
    l.new(pillar_size.outputs["Vector"], pillar.inputs["Size"])
    arch_dx = math(n, 'MULTIPLY', 3.0); arch_dx.location = (-20, 940); l.new(brick_x.outputs[0], arch_dx.inputs[0])
    arch_dx_neg = math(n, 'MULTIPLY', -1.0); arch_dx_neg.location = (160, 940); l.new(arch_dx.outputs[0], arch_dx_neg.inputs[0])
    pillar_z = math(n, 'MULTIPLY', .5); pillar_z.location = (160, 880); l.new(pz8.outputs[0], pillar_z.inputs[0])
    left_v, right_v = vector(n), vector(n)
    left_v.location, right_v.location = (330, 900), (330, 980)
    l.new(arch_dx_neg.outputs[0], left_v.inputs["X"]); l.new(pillar_z.outputs[0], left_v.inputs["Z"])
    l.new(arch_dx.outputs[0], right_v.inputs["X"]); l.new(pillar_z.outputs[0], right_v.inputs["Z"])
    left, right = n.new("GeometryNodeTransform"), n.new("GeometryNodeTransform")
    left.location, right.location = (510, 900), (510, 980)
    l.new(pillar.outputs["Mesh"], left.inputs["Geometry"]); l.new(left_v.outputs["Vector"], left.inputs["Translation"])
    l.new(pillar.outputs["Mesh"], right.inputs["Geometry"]); l.new(right_v.outputs["Vector"], right.inputs["Translation"])
    beam_size = vector(n); beam_size.location = (170, 1080)
    bx8, bz2 = math(n, 'MULTIPLY', 8), math(n, 'MULTIPLY', 2)
    bx8.location, bz2.location = (-20, 1050), (-20, 1110)
    l.new(brick_x.outputs[0], bx8.inputs[0]); l.new(gi.outputs["Altura Placa"], bz2.inputs[0])
    l.new(bx8.outputs[0], beam_size.inputs["X"]); l.new(py2.outputs[0], beam_size.inputs["Y"]); l.new(bz2.outputs[0], beam_size.inputs["Z"])
    beam = n.new("GeometryNodeMeshCube"); beam.location = (350, 1100); l.new(beam_size.outputs["Vector"], beam.inputs["Size"])
    beam_z = math(n, 'ADD'); beam_z.location = (350, 1180); l.new(pz8.outputs[0], beam_z.inputs[0]); l.new(bz2.outputs[0], beam_z.inputs[1])
    beam_v = vector(n); beam_v.location = (510, 1130); l.new(beam_z.outputs[0], beam_v.inputs["Z"])
    beam_move = n.new("GeometryNodeTransform"); beam_move.location = (690, 1100)
    l.new(beam.outputs["Mesh"], beam_move.inputs["Geometry"]); l.new(beam_v.outputs["Vector"], beam_move.inputs["Translation"])
    arch_proto = n.new("GeometryNodeJoinGeometry"); arch_proto.location = (860, 980)
    l.new(left.outputs["Geometry"], arch_proto.inputs["Geometry"]); l.new(right.outputs["Geometry"], arch_proto.inputs["Geometry"]); l.new(beam_move.outputs["Geometry"], arch_proto.inputs["Geometry"])
    arch_set = n.new("GeometryNodeSetMaterial"); arch_set.location = (1030, 980); arch_set.inputs["Material"].default_value = rock
    l.new(arch_proto.outputs["Geometry"], arch_set.inputs["Geometry"])
    arch_points = n.new("GeometryNodeDistributePointsOnFaces"); arch_points.location = (850, 780); arch_points.distribute_method = 'RANDOM'
    l.new(grid.outputs["Mesh"], arch_points.inputs["Mesh"]); l.new(gi.outputs["Densidad Arcos"], arch_points.inputs["Density"]); l.new(gi.outputs["Semilla"], arch_points.inputs["Seed"])
    rot_rand = n.new("FunctionNodeRandomValue"); rot_rand.location = (1040, 760); rot_rand.data_type = 'FLOAT'; rot_rand.inputs["Max"].default_value = 6.283185
    rot = vector(n); rot.location = (1210, 760); l.new(rot_rand.outputs["Value"], rot.inputs["Z"])
    arch_s = vector(n); arch_s.location = (1210, 870)
    l.new(gi.outputs["Escala Formaciones"], arch_s.inputs["X"]); l.new(gi.outputs["Escala Formaciones"], arch_s.inputs["Y"]); l.new(gi.outputs["Escala Formaciones"], arch_s.inputs["Z"])
    arch_move = vector(n); arch_move.location = (1210, 980); l.new(height.outputs[0], arch_move.inputs["Z"])
    arch_inst = n.new("GeometryNodeInstanceOnPoints"); arch_inst.location = (1380, 980)
    l.new(arch_points.outputs["Points"], arch_inst.inputs["Points"]); l.new(arch_set.outputs["Geometry"], arch_inst.inputs["Instance"])
    l.new(rot.outputs["Vector"], arch_inst.inputs["Rotation"]); l.new(arch_s.outputs["Vector"], arch_inst.inputs["Scale"])
    arch_translate = n.new("GeometryNodeTranslateInstances"); arch_translate.location = (1480, 980)
    l.new(arch_inst.outputs["Instances"], arch_translate.inputs["Instances"])
    l.new(arch_move.outputs["Vector"], arch_translate.inputs["Translation"])

    join = n.new("GeometryNodeJoinGeometry"); join.location = (1380, 220)
    l.new(body_translate.outputs["Instances"], join.inputs["Geometry"])
    l.new(studs_translate.outputs["Instances"], join.inputs["Geometry"])
    l.new(rock_translate.outputs["Instances"], join.inputs["Geometry"])
    l.new(arch_translate.outputs["Instances"], join.inputs["Geometry"])
    # Realizing only at the final output preserves an editable procedural graph while
    # ensuring every brick and stud is visible in viewport, render and export.
    realize = n.new("GeometryNodeRealizeInstances"); realize.location = (1510, 220)
    l.new(join.outputs["Geometry"], realize.inputs["Geometry"])
    l.new(realize.outputs["Geometry"], go.inputs["Geometría"])
    return t


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sand = material("MAT_LEGO_Arena", (0.20, 0.050, 0.008, 1), (0.84, 0.32, 0.045, 1))
    rock = material("MAT_LEGO_Roca", (0.06, 0.012, 0.003, 1), (0.28, 0.045, 0.008, 1))
    group = build(sand, rock)
    obj = bpy.data.objects.new("Desierto_LEGO_Procedural", bpy.data.meshes.new("Base_LEGO"))
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers.new("Desierto LEGO — Geometry Nodes", 'NODES')
    mod.node_group = group
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    text = bpy.data.texts.new("LEEME — Desierto LEGO")
    text.write("El objeto Desierto_LEGO_Procedural es un Geometry Nodes no destructivo.\n"
               "El terreno está formado por columnas de bloques y cuatro studs por celda.\n"
               "La escala es libre: Dimensión X/Y y Altura Placa controlan su tamaño.\n"
               "Las alturas son discretas; rocas y arcos se crean con bloques procedurales.\n")
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("CREATED", OUT)


if __name__ == '__main__':
    main()
