# Convierte un modelo 3D prediseñado en "partes" para el estilo tecnico (luego se dibujan con Grease Pencil).
#   blender -b -P b_modelo.py -- --entrada modelo.gltf --salida DIR/modelo/partes.json --hojas DIR/modelo [--caras 6000]
# 1. Importa (glTF/GLB, OBJ, FBX, STL o .blend), aplica transformaciones y modificadores, y lo apoya en el suelo
#    centrado (escala real si mide 0.15-3 m; si no, 1.2 m de alto).
# 2. Partes: un objeto = una parte; si viene en una sola malla, por islas sueltas (o por material). Las diminutas
#    se unen a la parte mas cercana hasta quedar <= --max_partes.
# 3. Simplifica cada parte (Decimate) con un presupuesto total de caras repartido por tamano.
# 4. Guarda vertices, caras, aristas vivas (borde o angulo > 35 grados) y pares de caras (siluetas), y el color medio
#    (textura incluida) llevado a la paleta tecnica.
# 5. Renderiza una vista por parte resaltada (para que Gemini las nombre) y una vista general.
import bpy, bmesh, json, math, os, sys
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp_base as GB
import comic_parametros as CP

EXCLUIR = {"papel", "baldosa", "pared", "pared_oscura", "azul_sombra", "agua", "cielo", "lima"}

def importar(ruta):
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".gltf", ".glb"): bpy.ops.import_scene.gltf(filepath=ruta)
    elif ext == ".obj": bpy.ops.wm.obj_import(filepath=ruta)
    elif ext == ".fbx": bpy.ops.import_scene.fbx(filepath=ruta)
    elif ext == ".stl": bpy.ops.wm.stl_import(filepath=ruta)
    elif ext == ".blend":
        with bpy.data.libraries.load(ruta, link=False) as (src, dst): dst.objects = list(src.objects)
        for o in dst.objects:
            if o: bpy.context.scene.collection.objects.link(o)
    else: raise SystemExit(f"formato no soportado: {ext}")

def color_material(m):
    """Color base en sRGB 0-1 (media de la textura si la hay)."""
    if m is None: return (0.7, 0.7, 0.7)
    if m.node_tree:
        bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            entrada = bsdf.inputs.get("Base Color")
            fac = list(entrada.default_value)[:3]
            if entrada.is_linked:
                n = entrada.links[0].from_node; visto = 0
                while n is not None and n.type != 'TEX_IMAGE' and visto < 6:
                    ent = [i for i in n.inputs if i.is_linked]; n = ent[0].links[0].from_node if ent else None; visto += 1
                if n is not None and n.type == 'TEX_IMAGE' and n.image and n.image.size[0] > 0:
                    img = n.image; w, h = img.size; px = np.empty(w * h * img.channels, np.float32)
                    img.pixels.foreach_get(px); px = px.reshape(-1, img.channels)[:, :3]
                    if img.colorspace_settings.name.lower().startswith("srgb") or img.is_float is False:
                        c = px[:: max(1, len(px) // 20000)].mean(axis=0)
                    else:
                        c = np.clip(px.mean(axis=0), 0, 1) ** (1 / 2.2)
                    return tuple(float(x) for x in c)
            return tuple(float(min(1, max(0, x))) ** (1 / 2.2) for x in fac)
    c = m.diffuse_color[:3]
    return tuple(float(x) ** (1 / 2.2) for x in c)

_imgs = {}
def imagen_np(m):
    """(array HxWx3 en sRGB, factor) de la textura de color base del material, o None."""
    if m is None or not m.node_tree: return None
    if m.name in _imgs: return _imgs[m.name]
    res = None
    bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf and bsdf.inputs["Base Color"].is_linked:
        n = bsdf.inputs["Base Color"].links[0].from_node; k = 0
        while n is not None and n.type != 'TEX_IMAGE' and k < 6:
            ent = [i for i in n.inputs if i.is_linked]; n = ent[0].links[0].from_node if ent else None; k += 1
        if n is not None and n.type == 'TEX_IMAGE' and n.image and n.image.size[0] > 0:
            img = n.image; w, h = img.size; px = np.empty(w * h * img.channels, np.float32); img.pixels.foreach_get(px)
            arr = px.reshape(h, w, img.channels)[:, :, :3]
            if img.is_float: arr = np.clip(arr, 0, 1) ** (1 / 2.2)
            res = arr
    _imgs[m.name] = res
    return res

def a_paleta(rgb):
    mejor, dmin = "metal", 9
    for nombre, hexa in CP.PALETA_TECNICA.items():
        if nombre in EXCLUIR: continue
        r, g, b = CP.hex_rgb(hexa)
        d = (r - rgb[0]) ** 2 * 0.3 + (g - rgb[1]) ** 2 * 0.59 + (b - rgb[2]) ** 2 * 0.11
        if d < dmin: mejor, dmin = nombre, d
    return mejor

class Parte:
    def __init__(self, nombre, bm, mats):
        self.nombre = nombre; self.bm = bm; self.mats = mats      # mats: material por indice de cara
    def caja(self):
        co = np.array([v.co[:] for v in self.bm.verts]); return co.min(0), co.max(0)
    def caras(self): return len(self.bm.faces)

def islas(bm):
    """Indices de caras agrupados por componentes conexas (union-find por vertices compartidos)."""
    padre = list(range(len(bm.verts)))
    def raiz(i):
        while padre[i] != i: padre[i] = padre[padre[i]]; i = padre[i]
        return i
    for e in bm.edges:
        a, b = raiz(e.verts[0].index), raiz(e.verts[1].index)
        if a != b: padre[a] = b
    grupos = {}
    for f in bm.faces: grupos.setdefault(raiz(f.verts[0].index), []).append(f.index)
    return list(grupos.values())

def sub_bmesh(bm, indices_caras):
    nb = bmesh.new(); mapa = {}; bm.faces.ensure_lookup_table(); mats = []
    for fi in indices_caras:
        f = bm.faces[fi]; vs = []
        for v in f.verts:
            if v.index not in mapa: mapa[v.index] = nb.verts.new(v.co)
            vs.append(mapa[v.index])
        try:
            nf = nb.faces.new(vs); nf.material_index = f.material_index
        except ValueError: pass
    return nb

def fusionar(a, b):
    off = len(a.bm.verts); mapa = {}
    for v in b.bm.verts: mapa[v.index] = a.bm.verts.new(v.co)
    a.bm.verts.ensure_lookup_table()
    base_m = len(a.mats); a.mats = a.mats + b.mats
    for f in b.bm.faces:
        try:
            nf = a.bm.faces.new([mapa[v.index] for v in f.verts]); nf.material_index = f.material_index + base_m
        except ValueError: pass
    a.bm.verts.index_update(); a.bm.faces.index_update()
    a.nombre = a.nombre if a.caras() >= b.caras() else b.nombre

def main():
    a = GB.argumentos()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    importar(a["entrada"])
    dg = bpy.context.evaluated_depsgraph_get()
    partes = []
    mallas = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not mallas: raise SystemExit("el modelo no tiene mallas")
    for o in mallas:
        bm = bmesh.new(); bm.from_object(o, dg); bm.transform(o.matrix_world)
        if len(bm.faces) == 0: bm.free(); continue
        mats = [s.material for s in o.material_slots] or [None]
        partes.append(Parte(o.name, bm, mats))
    # escala y posicion: apoyado en el suelo y centrado
    mn = np.min([p.caja()[0] for p in partes], 0); mx = np.max([p.caja()[1] for p in partes], 0)
    alto = mx[2] - mn[2]; s = 1.0 if 0.15 <= alto <= 3.0 else 1.2 / max(alto, 1e-6)
    if a.get("alto"): s = float(a["alto"]) / max(alto, 1e-6)
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
    for p in partes:
        for v in p.bm.verts: v.co = Vector(((v.co.x - cx) * s, (v.co.y - cy) * s, (v.co.z - mn[2]) * s))
        diag = float(np.linalg.norm(np.array(p.caja()[1]) - np.array(p.caja()[0])))
        bmesh.ops.remove_doubles(p.bm, verts=p.bm.verts, dist=max(1e-6, diag * 2e-4))
        p.bm.verts.index_update(); p.bm.faces.index_update()
    # una sola malla: por islas (y si no, por material)
    if len(partes) < 3:
        nuevas = []
        for p in partes:
            p.bm.verts.ensure_lookup_table(); p.bm.faces.ensure_lookup_table()
            gr = islas(p.bm)
            if len(gr) <= 1 and len(p.mats) > 1:
                gr = {}
                for f in p.bm.faces: gr.setdefault(f.material_index, []).append(f.index)
                gr = list(gr.values())
            if len(gr) <= 1: nuevas.append(p); continue
            for k, g in enumerate(gr): nuevas.append(Parte(f"{p.nombre}.{k:03d}", sub_bmesh(p.bm, g), list(p.mats)))
        partes = nuevas
    # filtrar paredes internas redundantes (doble pared con normales hacia dentro contenida en otra isla)
    if len(partes) > 1:
        filtradas = []
        for i, p in enumerate(partes):
            p.bm.normal_update()
            c0, c1 = p.caja(); cen = Vector((c0 + c1) / 2)
            flujo_normal = sum((f.calc_center_median() - cen).dot(f.normal) * f.calc_area() for f in p.bm.faces)
            es_pared_interna = False
            if flujo_normal < 0:   # normales apuntando hacia dentro: cascara hueca interior de un solidify/cristal
                for j, q in enumerate(partes):
                    if i == j: continue
                    q0, q1 = q.caja()
                    if np.all(c0 >= q0 - 0.005) and np.all(c1 <= q1 + 0.005) and np.linalg.norm(c1 - c0) >= 0.65 * np.linalg.norm(q1 - q0):
                        es_pared_interna = True; break
            if es_pared_interna: p.bm.free()
            else: filtradas.append(p)
        if filtradas: partes = filtradas
    # unir las pequenas a la mas cercana hasta <= max_partes
    max_p = int(a.get("max_partes", 14))
    mn = np.min([p.caja()[0] for p in partes], 0); mx = np.max([p.caja()[1] for p in partes], 0); D = float(np.linalg.norm(mx - mn))
    def tam(p): c0, c1 = p.caja(); return float(np.linalg.norm(c1 - c0))
    def dist(p, q):
        a0, a1 = p.caja(); b0, b1 = q.caja(); gap = np.maximum(0, np.maximum(a0 - b1, b0 - a1)); return float(np.linalg.norm(gap)) + 1e-3 * float(np.linalg.norm((a0 + a1) / 2 - (b0 + b1) / 2))
    while len(partes) > 1:
        partes.sort(key=tam)
        if len(partes) <= max_p and tam(partes[0]) > 0.05 * D: break
        p = partes.pop(0); q = min(partes, key=lambda x: dist(p, x)); fusionar(q, p)
    # simplificar con presupuesto
    presupuesto = int(a.get("caras", 8000)); total = sum(p.caras() for p in partes)
    salida = {"alto": float(np.max([p.caja()[1][2] for p in partes])), "partes": []}
    for i, p in enumerate(partes):
        objetivo = max(60, int(presupuesto * p.caras() / max(1, total)))     # reparto por caras originales
        me = bpy.data.meshes.new(f"p{i}"); p.bm.to_mesh(me); ob = bpy.data.objects.new(f"p{i}", me); bpy.context.scene.collection.objects.link(ob)
        if len(me.polygons) > objetivo:          # primero planar (respeta formas mecanicas), luego colapso si hace falta
            m1 = ob.modifiers.new("plano", 'DECIMATE'); m1.decimate_type = 'DISSOLVE'; m1.angle_limit = math.radians(4)
            n1 = len(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)
            if n1 > objetivo:
                m2 = ob.modifiers.new("dec", 'DECIMATE'); m2.ratio = objetivo / n1; m2.use_collapse_triangulate = False
        dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
        bm = bmesh.new(); bm.from_object(ob, dg)
        bm.verts.index_update(); bm.faces.index_update(); bm.normal_update()
        # color medio ponderado por area: textura muestreada en las UV de cada cara (atlas incluidos)
        acum, area = np.zeros(3), 0.0
        cache = {}; uv = bm.loops.layers.uv.active
        for f in bm.faces:
            mi = min(f.material_index, len(p.mats) - 1); m = p.mats[mi]
            arr = imagen_np(m) if uv is not None else None
            if arr is not None:
                u = sum(l[uv].uv.x for l in f.loops) / len(f.loops); v = sum(l[uv].uv.y for l in f.loops) / len(f.loops)
                h, w = arr.shape[:2]; c = arr[int((v % 1.0) * (h - 1)), int((u % 1.0) * (w - 1))]
            else:
                if mi not in cache: cache[mi] = color_material(m)
                c = np.array(cache[mi])
            acum += np.array(c) * f.calc_area(); area += f.calc_area()
        rgb = tuple(acum / max(area, 1e-9))
        vert = [[round(c, 4) for c in v.co] for v in bm.verts]
        caras = [[v.index for v in f.verts] for f in bm.faces]
        # detectar aristas vivas y filtrar aristas paralelas de micro-biseles (< 2.5 mm) para evitar trazos dobles
        cand_vivas = []
        for idx_e, e in enumerate(bm.edges):
            lf = [f.index for f in e.link_faces]
            ang = (e.calc_face_angle(0) or 0) if len(lf) == 2 else math.pi
            if len(lf) != 2 or ang > math.radians(35):
                v0, v1 = e.verts[0].co, e.verts[1].co
                dv = v1 - v0; L = dv.length
                if L > 1e-6:
                    cand_vivas.append((idx_e, len(lf) != 2, ang, L, (v0 + v1) * 0.5, dv / L))
        cand_vivas.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        vivas_ok, aceptadas = set(), []
        for idx_e, es_borde, ang, L, mid, dir_u in cand_vivas:
            if not es_borde:
                dup = False
                for m2, d2, L2 in aceptadas:
                    if abs(dir_u.dot(d2)) > 0.96:
                        diff = mid - m2
                        proj = abs(diff.dot(d2))
                        if proj < 0.5 * (L + L2) and (diff - d2 * diff.dot(d2)).length < 0.0025:
                            dup = True; break
                if dup: continue
                aceptadas.append((mid, dir_u, L))
            vivas_ok.add(idx_e)
        aristas = []
        for idx_e, e in enumerate(bm.edges):
            lf = [f.index for f in e.link_faces]
            aristas.append([e.verts[0].index, e.verts[1].index, lf[0] if lf else -1, lf[1] if len(lf) > 1 else -1, 1 if idx_e in vivas_ok else 0])
        c0, c1 = np.array(vert).min(0), np.array(vert).max(0)
        nombre_mat = ", ".join(sorted({m.name for m in p.mats if m}))[:60]
        salida["partes"].append(dict(id=f"p{i + 1:02d}", nombre_original=p.nombre[:60], materiales=nombre_mat,
                                     color=a_paleta(rgb), color_original="#%02x%02x%02x" % tuple(int(255 * min(1, max(0, x))) for x in rgb),
                                     bbox=[list(map(float, c0)), list(map(float, c1))], centro=list(map(float, (c0 + c1) / 2)),
                                     vertices=vert, caras=caras, aristas=aristas))
        bm.free()
    salida["caras_totales"] = sum(len(p["caras"]) for p in salida["partes"])
    salida["caras_originales"] = total
    os.makedirs(os.path.dirname(a["salida"]), exist_ok=True)
    with open(a["salida"], "w") as f: json.dump(salida, f, separators=(",", ":"))
    # vistas: una por parte resaltada (naranja) sobre el resto en gris, y una general con colores de paleta
    if a.get("hojas"): vistas(salida, a["hojas"])
    print("INFORME " + json.dumps(dict(partes=len(salida["partes"]), caras=salida["caras_totales"], caras_originales=total,
                                       alto=round(salida["alto"], 3), colores=[p["color"] for p in salida["partes"]]), ensure_ascii=False))

def vistas(datos, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = sc.render.resolution_y = 384; sc.render.resolution_percentage = 100; sc.render.film_transparent = False
    if not sc.world: sc.world = bpy.data.worlds.new("w")
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", 'SUN')); sc.collection.objects.link(sol)
    sol.rotation_euler = (math.radians(40), math.radians(20), math.radians(30)); sol.data.energy = 3.5
    obs = []
    def mat(nombre, rgb):
        m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
        m.diffuse_color = (*rgb, 1); bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf: bsdf.inputs["Base Color"].default_value = (*rgb, 1); bsdf.inputs["Roughness"].default_value = 0.8
        return m
    gris, naranja = mat("gris", (0.55, 0.55, 0.55)), mat("naranja", (1.0, 0.25, 0.0))
    for p in datos["partes"]:
        me = bpy.data.meshes.new(p["id"]); me.from_pydata(p["vertices"], [], p["caras"]); me.update()
        ob = bpy.data.objects.new(p["id"], me); sc.collection.objects.link(ob); me.materials.append(gris); obs.append(ob)
        me.materials.append(mat(f"pal_{p['color']}", CP.color_lineal(CP.PALETA_TECNICA[p["color"]])[:3]))
    alto = datos["alto"]; mxy = max(max(abs(c) for c in p["bbox"][1][:2] + p["bbox"][0][:2]) for p in datos["partes"])
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(alto, 2 * mxy) * 1.5
    d = Vector((-math.sin(math.radians(35)) * math.cos(math.radians(32)), -math.cos(math.radians(35)) * math.cos(math.radians(32)), math.sin(math.radians(32))))
    cen = Vector((0, 0, alto / 2)); cam.location = cen + d * 20
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    for ob in obs:
        for pol in ob.data.polygons: pol.material_index = 1
    GB.render_fotograma(os.path.join(carpeta, "vista_general.png"), 1, sc)
    for i, ob in enumerate(obs):
        for o in obs:
            o.data.materials[0] = naranja if o is ob else gris
            for pol in o.data.polygons: pol.material_index = 0
        GB.render_fotograma(os.path.join(carpeta, f"parte_{datos['partes'][i]['id']}.png"), 1, sc)

if __name__ == "__main__":
    main()
