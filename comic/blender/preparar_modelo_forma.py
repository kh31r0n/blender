"""Prepara un modelo descargado como malla de una forma del estilo tecnico (p. ej. 'cerebro'): lo importa, suelda
vertices, lo reduce a varios niveles de detalle y lo normaliza (media longitud en X = 1, centrado en X/Y, base en z=0).
Guarda un JSON con vertices y caras por nivel, la caja normalizada, la fuente y la licencia.

  blender -b --factory-startup -P preparar_modelo_forma.py -- entrada.glb salida.json "fuente" "licencia" [alto=40000] [bajo=3000]

El modelo ya debe venir con Z arriba y el frente hacia -X (si no, girarlo antes). No ejecuta nada del archivo: solo importa malla.
"""
import sys, json, bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
entrada, salida, fuente, licencia = args[:4]
niveles = {"alto": 40000, "bajo": 3000}
for a in args[4:]:
    k, v = a.split("="); niveles[k] = int(v)

bpy.ops.wm.read_factory_settings(use_empty=True)
ext = entrada.lower().rsplit(".", 1)[-1]
if ext in ("glb", "gltf"): bpy.ops.import_scene.gltf(filepath=entrada)
elif ext == "stl": bpy.ops.wm.stl_import(filepath=entrada)
elif ext == "obj": bpy.ops.wm.obj_import(filepath=entrada)
else: raise SystemExit(f"formato no soportado: {ext}")
mallas = [o for o in bpy.data.objects if o.type == 'MESH']
for o in bpy.data.objects: o.select_set(o in mallas)
bpy.context.view_layer.objects.active = mallas[0]
if len(mallas) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-4 * max(ob.dimensions)); bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
# normalizar: media longitud en X = 1, centrado en X/Y, base en z = 0
vs = [v.co for v in ob.data.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
esc = 2.0 / (hi.x - lo.x); c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
for v in ob.data.vertices: v.co = (v.co - c) * esc
print("PREPARAR original", len(ob.data.vertices), "vertices", len(ob.data.polygons), "caras")
out = dict(fuente=fuente, licencia=licencia, archivo=entrada.rsplit("/", 1)[-1],
           bbox=[[round((lo[i] - c[i]) * esc, 5) for i in range(3)], [round((hi[i] - c[i]) * esc, 5) for i in range(3)]], niveles={})
for nombre, n_caras in sorted(niveles.items(), key=lambda kv: -kv[1]):
    cp = ob.copy(); cp.data = ob.data.copy(); bpy.context.collection.objects.link(cp)
    m = cp.modifiers.new("Reducir", 'DECIMATE'); m.decimate_type = 'COLLAPSE'
    m.ratio = min(1.0, n_caras / max(1, len(ob.data.polygons))); m.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get(); me = cp.evaluated_get(dg).to_mesh()
    out["niveles"][nombre] = dict(v=[[round(x, 5) for x in v.co] for v in me.vertices], f=[list(p.vertices) for p in me.polygons])
    print("PREPARAR", nombre, len(me.vertices), "vertices", len(me.polygons), "caras")
json.dump(out, open(salida, "w"), separators=(",", ":"))
print("PREPARAR ->", salida, out["bbox"])
