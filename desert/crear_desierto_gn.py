import bpy


OUT = "/home/kheiron/blender/desert/Desierto_Geometry_Nodes.blend"


def socket(tree, name, socket_type, default=None, min_value=None, max_value=None,
           description="", parent=None):
    item = tree.interface.new_socket(name=name, in_out='INPUT', socket_type=socket_type,
                                     description=description, parent=parent)
    if default is not None:
        item.default_value = default
    if min_value is not None:
        item.min_value = min_value
    if max_value is not None:
        item.max_value = max_value
    return item


def new_mat_sand():
    mat = bpy.data.materials.new("MAT_Arena_Procedural")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (560, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (310, 0)
    bsdf.inputs["Roughness"].default_value = 0.78
    bsdf.inputs["Specular IOR Level"].default_value = 0.18
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "desert_slope"
    attr.location = (-500, 20)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-240, 20)
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    e0 = ramp.color_ramp.elements[0]
    e0.position = 0.08
    e0.color = (0.55, 0.19, 0.045, 1)
    e1 = ramp.color_ramp.elements.new(0.28)
    e1.color = (0.24, 0.07, 0.018, 1)
    e2 = ramp.color_ramp.elements.new(0.48)
    e2.color = (0.075, 0.028, 0.012, 1)
    links.new(attr.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def new_mat_rock():
    mat = bpy.data.materials.new("MAT_Roca_Procedural")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (550, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (310, 0)
    bsdf.inputs["Roughness"].default_value = 0.91
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, 0)
    noise.inputs["Scale"].default_value = 1.4
    noise.inputs["Detail"].default_value = 5.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-220, 0)
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.035, 0.012, 0.005, 1)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.24, 0.065, 0.018, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def math_node(nodes, operation, value=None):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    if value is not None:
        node.inputs[1].default_value = value
    return node


def build_group(sand, rock):
    tree = bpy.data.node_groups.new("GN_Desierto_Continuo", "GeometryNodeTree")
    interface = tree.interface
    terrain = interface.new_panel("Terreno")
    elements = interface.new_panel("Formaciones", default_closed=False)
    socket(tree, "Dimensión X", "NodeSocketInt", 1000, 1, 10000,
           "Ancho del desierto en unidades Blender enteras.", terrain)
    socket(tree, "Dimensión Y", "NodeSocketInt", 1000, 1, 10000,
           "Largo del desierto en unidades Blender enteras.", terrain)
    socket(tree, "Subdivisiones X", "NodeSocketInt", 256, 2, 2048,
           "Número fijo de vértices en X; no cambia automáticamente con el tamaño.", terrain)
    socket(tree, "Subdivisiones Y", "NodeSocketInt", 256, 2, 2048,
           "Número fijo de vértices en Y; no cambia automáticamente con el tamaño.", terrain)
    socket(tree, "Semilla", "NodeSocketInt", 7, 0, 100000,
           "Varía el patrón completo de forma determinista.", terrain)
    socket(tree, "Altura Dunas", "NodeSocketFloat", 38.0, 0.0, 500.0,
           "Altura dominante de las dunas.", terrain)
    socket(tree, "Escala Dunas", "NodeSocketFloat", 0.009, 0.0001, 2.0,
           "Frecuencia de las dunas: menor valor produce formaciones más grandes.", terrain)
    socket(tree, "Altura Colinas", "NodeSocketFloat", 80.0, 0.0, 1000.0,
           "Relieve macro de colinas y mesetas.", terrain)
    socket(tree, "Detalle Arena", "NodeSocketFloat", 4.0, 0.0, 100.0,
           "Microrelieve superficial de la arena.", terrain)
    socket(tree, "Erosión", "NodeSocketFloat", 16.0, 0.0, 300.0,
           "Intensidad de cortes y variación erosiva.", terrain)
    socket(tree, "Densidad Rocas", "NodeSocketFloat", 0.00028, 0.0, 0.02,
           "Rocas por unidad cuadrada; 0 las desactiva.", elements)
    socket(tree, "Densidad Arcos", "NodeSocketFloat", 0.000012, 0.0, 0.001,
           "Arcos por unidad cuadrada; 0 los desactiva.", elements)
    socket(tree, "Escala Rocas", "NodeSocketFloat", 1.0, 0.0, 20.0,
           "Multiplicador global del tamaño de rocas y arcos.", elements)
    interface.new_socket(name="Geometría", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1550, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1440, 120)

    grid = nodes.new("GeometryNodeMeshGrid")
    grid.label = "Malla continua de resolución fija"
    grid.location = (-1290, 170)
    links.new(group_in.outputs["Dimensión X"], grid.inputs["Size X"])
    links.new(group_in.outputs["Dimensión Y"], grid.inputs["Size Y"])
    links.new(group_in.outputs["Subdivisiones X"], grid.inputs["Vertices X"])
    links.new(group_in.outputs["Subdivisiones Y"], grid.inputs["Vertices Y"])

    pos = nodes.new("GeometryNodeInputPosition")
    pos.location = (-1280, -230)
    dune = nodes.new("ShaderNodeTexNoise")
    dune.label = "Dunas"
    dune.location = (-1050, -250)
    dune.noise_dimensions = '4D'
    dune.inputs["Detail"].default_value = 3.0
    dune.inputs["Roughness"].default_value = 0.52
    links.new(pos.outputs["Position"], dune.inputs["Vector"])
    links.new(group_in.outputs["Escala Dunas"], dune.inputs["Scale"])
    links.new(group_in.outputs["Semilla"], dune.inputs["W"])
    dune_sub = math_node(nodes, 'SUBTRACT', 0.5)
    dune_sub.location = (-850, -240)
    dune_mul = math_node(nodes, 'MULTIPLY')
    dune_mul.location = (-670, -240)
    links.new(dune.outputs["Fac"], dune_sub.inputs[0])
    links.new(dune_sub.outputs[0], dune_mul.inputs[0])
    links.new(group_in.outputs["Altura Dunas"], dune_mul.inputs[1])

    hill = nodes.new("ShaderNodeTexNoise")
    hill.label = "Colinas macro"
    hill.location = (-1050, -450)
    hill.noise_dimensions = '4D'
    hill.inputs["Scale"].default_value = 0.0022
    hill.inputs["Detail"].default_value = 2.0
    hill.inputs["Roughness"].default_value = 0.7
    links.new(pos.outputs["Position"], hill.inputs["Vector"])
    links.new(group_in.outputs["Semilla"], hill.inputs["W"])
    hill_sub = math_node(nodes, 'SUBTRACT', 0.42)
    hill_sub.location = (-850, -440)
    hill_mul = math_node(nodes, 'MULTIPLY')
    hill_mul.location = (-670, -440)
    links.new(hill.outputs["Fac"], hill_sub.inputs[0])
    links.new(hill_sub.outputs[0], hill_mul.inputs[0])
    links.new(group_in.outputs["Altura Colinas"], hill_mul.inputs[1])

    fine = nodes.new("ShaderNodeTexNoise")
    fine.label = "Grano de arena"
    fine.location = (-1050, -650)
    fine.noise_dimensions = '4D'
    fine.inputs["Scale"].default_value = 0.16
    fine.inputs["Detail"].default_value = 2.0
    links.new(pos.outputs["Position"], fine.inputs["Vector"])
    links.new(group_in.outputs["Semilla"], fine.inputs["W"])
    fine_sub = math_node(nodes, 'SUBTRACT', 0.5)
    fine_sub.location = (-850, -640)
    fine_mul = math_node(nodes, 'MULTIPLY')
    fine_mul.location = (-670, -640)
    links.new(fine.outputs["Fac"], fine_sub.inputs[0])
    links.new(fine_sub.outputs[0], fine_mul.inputs[0])
    links.new(group_in.outputs["Detalle Arena"], fine_mul.inputs[1])

    erosion = nodes.new("ShaderNodeTexVoronoi")
    erosion.label = "Erosión"
    erosion.location = (-1050, -840)
    erosion.voronoi_dimensions = '4D'
    erosion.feature = 'DISTANCE_TO_EDGE'
    erosion.distance = 'EUCLIDEAN'
    erosion.inputs["Scale"].default_value = 0.022
    links.new(pos.outputs["Position"], erosion.inputs["Vector"])
    links.new(group_in.outputs["Semilla"], erosion.inputs["W"])
    erosion_mul = math_node(nodes, 'MULTIPLY')
    erosion_mul.location = (-670, -830)
    links.new(erosion.outputs["Distance"], erosion_mul.inputs[0])
    links.new(group_in.outputs["Erosión"], erosion_mul.inputs[1])

    add_1 = math_node(nodes, 'ADD')
    add_1.location = (-440, -320)
    add_2 = math_node(nodes, 'ADD')
    add_2.location = (-260, -360)
    add_3 = math_node(nodes, 'ADD')
    add_3.location = (-80, -410)
    links.new(dune_mul.outputs[0], add_1.inputs[0])
    links.new(hill_mul.outputs[0], add_1.inputs[1])
    links.new(add_1.outputs[0], add_2.inputs[0])
    links.new(fine_mul.outputs[0], add_2.inputs[1])
    links.new(add_2.outputs[0], add_3.inputs[0])
    links.new(erosion_mul.outputs[0], add_3.inputs[1])
    offset = nodes.new("ShaderNodeCombineXYZ")
    offset.location = (120, -360)
    links.new(add_3.outputs[0], offset.inputs["Z"])
    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (140, 170)
    links.new(grid.outputs["Mesh"], set_pos.inputs["Geometry"])
    links.new(offset.outputs["Vector"], set_pos.inputs["Offset"])

    store_height = nodes.new("GeometryNodeStoreNamedAttribute")
    store_height.data_type = 'FLOAT'
    store_height.domain = 'POINT'
    store_height.label = "Atributo de altura para material"
    store_height.location = (390, 180)
    store_height.inputs["Name"].default_value = "desert_height"
    links.new(set_pos.outputs["Geometry"], store_height.inputs["Geometry"])
    links.new(add_3.outputs[0], store_height.inputs["Value"])
    normal = nodes.new("GeometryNodeInputNormal")
    normal.location = (360, -30)
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.location = (530, -30)
    slope = math_node(nodes, 'SUBTRACT', 1.0)
    slope.location = (700, -30)
    links.new(normal.outputs["Normal"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], slope.inputs[0])
    store_slope = nodes.new("GeometryNodeStoreNamedAttribute")
    store_slope.data_type = 'FLOAT'
    store_slope.domain = 'POINT'
    store_slope.label = "Atributo de pendiente para material"
    store_slope.location = (650, 180)
    store_slope.inputs["Name"].default_value = "desert_slope"
    links.new(store_height.outputs["Geometry"], store_slope.inputs["Geometry"])
    links.new(slope.outputs[0], store_slope.inputs["Value"])
    set_sand = nodes.new("GeometryNodeSetMaterial")
    set_sand.location = (900, 250)
    set_sand.inputs["Material"].default_value = sand
    links.new(store_slope.outputs["Geometry"], set_sand.inputs["Geometry"])

    # Rocks are instanced on the continuous terrain, so they inherit its varying height.
    rock_points = nodes.new("GeometryNodeDistributePointsOnFaces")
    rock_points.distribute_method = 'RANDOM'
    rock_points.location = (800, -220)
    links.new(store_slope.outputs["Geometry"], rock_points.inputs["Mesh"])
    links.new(group_in.outputs["Densidad Rocas"], rock_points.inputs["Density"])
    links.new(group_in.outputs["Semilla"], rock_points.inputs["Seed"])
    ico = nodes.new("GeometryNodeMeshIcoSphere")
    ico.location = (800, -430)
    ico.inputs["Radius"].default_value = 1.0
    ico.inputs["Subdivisions"].default_value = 2
    rock_mat = nodes.new("GeometryNodeSetMaterial")
    rock_mat.location = (990, -430)
    rock_mat.inputs["Material"].default_value = rock
    links.new(ico.outputs["Mesh"], rock_mat.inputs["Geometry"])
    rock_random = nodes.new("FunctionNodeRandomValue")
    rock_random.data_type = 'FLOAT_VECTOR'
    rock_random.location = (990, -590)
    rock_random.inputs["Min"].default_value = (1.5, 1.0, 0.7)
    rock_random.inputs["Max"].default_value = (6.0, 4.0, 3.2)
    rock_scale = nodes.new("ShaderNodeVectorMath")
    rock_scale.operation = 'SCALE'
    rock_scale.location = (1180, -570)
    links.new(rock_random.outputs["Value"], rock_scale.inputs[0])
    links.new(group_in.outputs["Escala Rocas"], rock_scale.inputs["Scale"])
    rock_instances = nodes.new("GeometryNodeInstanceOnPoints")
    rock_instances.location = (1190, -280)
    links.new(rock_points.outputs["Points"], rock_instances.inputs["Points"])
    links.new(rock_mat.outputs["Geometry"], rock_instances.inputs["Instance"])
    links.new(rock_scale.outputs["Vector"], rock_instances.inputs["Scale"])

    # An arch is modeled from three boxes, then instanced; it is fully new procedural geometry.
    pillar = nodes.new("GeometryNodeMeshCube")
    pillar.location = (760, -870)
    pillar.inputs["Size"].default_value = (3.8, 5.0, 18.0)
    left = nodes.new("GeometryNodeTransform")
    left.location = (940, -820)
    left.inputs["Translation"].default_value = (-8.0, 0.0, 9.0)
    right = nodes.new("GeometryNodeTransform")
    right.location = (940, -940)
    right.inputs["Translation"].default_value = (8.0, 0.0, 9.0)
    links.new(pillar.outputs["Mesh"], left.inputs["Geometry"])
    links.new(pillar.outputs["Mesh"], right.inputs["Geometry"])
    lintel = nodes.new("GeometryNodeMeshCube")
    lintel.location = (940, -1060)
    lintel.inputs["Size"].default_value = (20.0, 5.0, 5.0)
    lintel_move = nodes.new("GeometryNodeTransform")
    lintel_move.location = (1120, -1060)
    lintel_move.inputs["Translation"].default_value = (0.0, 0.0, 18.0)
    links.new(lintel.outputs["Mesh"], lintel_move.inputs["Geometry"])
    arch_join = nodes.new("GeometryNodeJoinGeometry")
    arch_join.location = (1210, -900)
    links.new(left.outputs["Geometry"], arch_join.inputs["Geometry"])
    links.new(right.outputs["Geometry"], arch_join.inputs["Geometry"])
    links.new(lintel_move.outputs["Geometry"], arch_join.inputs["Geometry"])
    arch_mat = nodes.new("GeometryNodeSetMaterial")
    arch_mat.location = (1390, -900)
    arch_mat.inputs["Material"].default_value = rock
    links.new(arch_join.outputs["Geometry"], arch_mat.inputs["Geometry"])
    arch_points = nodes.new("GeometryNodeDistributePointsOnFaces")
    arch_points.distribute_method = 'RANDOM'
    arch_points.location = (1180, -60)
    links.new(store_slope.outputs["Geometry"], arch_points.inputs["Mesh"])
    links.new(group_in.outputs["Densidad Arcos"], arch_points.inputs["Density"])
    links.new(group_in.outputs["Semilla"], arch_points.inputs["Seed"])
    arch_rot_val = nodes.new("FunctionNodeRandomValue")
    arch_rot_val.data_type = 'FLOAT'
    arch_rot_val.location = (1370, -200)
    arch_rot_val.inputs["Min"].default_value = 0.0
    arch_rot_val.inputs["Max"].default_value = 6.283185
    arch_rot = nodes.new("ShaderNodeCombineXYZ")
    arch_rot.location = (1540, -200)
    links.new(arch_rot_val.outputs["Value"], arch_rot.inputs["Z"])
    arch_instances = nodes.new("GeometryNodeInstanceOnPoints")
    arch_instances.location = (1590, -80)
    links.new(arch_points.outputs["Points"], arch_instances.inputs["Points"])
    links.new(arch_mat.outputs["Geometry"], arch_instances.inputs["Instance"])
    links.new(arch_rot.outputs["Vector"], arch_instances.inputs["Rotation"])
    # A uniform global scale keeps the arch shape intact.
    arch_scale = nodes.new("ShaderNodeCombineXYZ")
    arch_scale.location = (1570, -320)
    links.new(group_in.outputs["Escala Rocas"], arch_scale.inputs["X"])
    links.new(group_in.outputs["Escala Rocas"], arch_scale.inputs["Y"])
    links.new(group_in.outputs["Escala Rocas"], arch_scale.inputs["Z"])
    links.new(arch_scale.outputs["Vector"], arch_instances.inputs["Scale"])

    join = nodes.new("GeometryNodeJoinGeometry")
    join.location = (1190, 330)
    links.new(set_sand.outputs["Geometry"], join.inputs["Geometry"])
    links.new(rock_instances.outputs["Instances"], join.inputs["Geometry"])
    links.new(arch_instances.outputs["Instances"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], group_out.inputs["Geometría"])

    # Keep the graph readable in a wide, left-to-right layout.
    for n in nodes:
        n.select = False
    return tree


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sand = new_mat_sand()
    rock = new_mat_rock()
    tree = build_group(sand, rock)
    mesh = bpy.data.meshes.new("Desierto_Base")
    obj = bpy.data.objects.new("Desierto_Procedural", mesh)
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers.new("Desierto — Geometry Nodes", 'NODES')
    mod.node_group = tree
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    note = bpy.data.texts.new("LEEME — Desierto procedural")
    note.write(
        "DESIERTO PROCEDURAL\n\n"
        "Modifica los controles del modificador 'Desierto — Geometry Nodes'.\n"
        "Dimensión X/Y son enteros en unidades Blender. Subdivisiones X/Y son\n"
        "fijas: al aumentar las dimensiones no aumentan por sí solas.\n\n"
        "El objeto usa Geometry Nodes no destructivo. Las rocas y arcos son\n"
        "geometría nueva creada en el grafo; no se usan mallas de referencia.\n"
    )
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("CREATED", OUT)


if __name__ == "__main__":
    main()
