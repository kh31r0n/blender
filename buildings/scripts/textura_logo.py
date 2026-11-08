# Genera el mapa de alturas del logo LEGO de los studs (descargas/cc0/logo_stud_altura.png) a partir de la geometria
# oficial de LDraw (stud-logo4): se importa una placa 1x1 con logo y se renderiza desde arriba, en ortografica, con un
# material de emision igual a la altura sobre la cara superior del stud. La imagen cubre una celda de 1 stud (0.8 BU)
# con el stud centrado. Uso: blender -b -P ~/blender/buildings/scripts/textura_logo.py
import bpy, addon_utils, os

OUT = os.path.expanduser("~/blender/buildings/descargas/cc0/logo_stud_altura.png")
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_scene_importldraw")
bpy.ops.import_scene.importldraw(filepath="/home/kheiron/ldraw/parts/3024.dat", ldrawPath="/home/kheiron/ldraw", realScale=100.0,
                                 useLogoStuds=True, bevelEdges=False, addEnvironment=False, importCameras=False,
                                 positionCamera=False, positionOnGround=False)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'      # el importador deja Cycles
ob = next(o for o in sc.objects if o.type == 'MESH')
dg = bpy.context.evaluated_depsgraph_get()
zs = [(ob.matrix_world @ v.co).z for v in ob.evaluated_get(dg).data.vertices]
cx, cy = ob.matrix_world.translation.x, ob.matrix_world.translation.y
z_max = max(zs)
z_cara = z_max - 0.0078              # stud-logo4: cara del stud a 3.8 LDU y logo hasta 4 LDU (0.2 LDU de relieve)
print("Z", min(zs), z_max, z_cara)

m = bpy.data.materials.new("altura"); nt = m.node_tree; nt.nodes.clear()
geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mr = nt.nodes.new('ShaderNodeMapRange'); mr.clamp = True
mr.inputs["From Min"].default_value = z_cara; mr.inputs["From Max"].default_value = z_max
em = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(geo.outputs["Position"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
nt.links.new(mr.outputs["Result"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
ob.data.materials.clear(); ob.data.materials.append(m)
for p in ob.data.polygons: p.material_index = 0

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.8; cam.location = (cx, cy, z_max + 1); cam.rotation_euler = (0, 0, 0)
sc.world = bpy.data.worlds.new("negro"); sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
sc.render.resolution_x = sc.render.resolution_y = 512
sc.view_settings.view_transform = 'Standard'; sc.render.filter_size = 0.5
sc.render.image_settings.color_depth = '16'; sc.render.image_settings.color_mode = 'BW'
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
print("guardado", OUT)
