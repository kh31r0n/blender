import bpy
from mathutils import Vector

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 400
scene.render.resolution_y = 300
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = '/home/kheiron/blender/desert/desierto_lego_previa.png'
world = bpy.data.worlds.new('Previa_Mundo') if scene.world is None else scene.world
scene.world = world
world.color = (0.025, 0.025, 0.025)

obj = bpy.data.objects['Desierto_LEGO_Procedural']

cam_data = bpy.data.cameras.new('Previa_Camara')
cam = bpy.data.objects.new('Previa_Camara', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = (1100, -1250, 980)
cam.rotation_euler = (Vector((0, 0, 85)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 1450
cam.data.clip_end = 5000

sun_data = bpy.data.lights.new('Previa_Sol', 'SUN')
sun_data.energy = 3.0
sun = bpy.data.objects.new('Previa_Sol', sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (0.45, -0.55, -0.35)

bpy.ops.render.render(write_still=True)
