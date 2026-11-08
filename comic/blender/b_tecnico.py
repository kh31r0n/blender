# ESTILO TECNICO: etapas de Blender del explicativo de objetos (modos 1, 2, 4 y efectos del agente).
#   blender -b -P b_tecnico.py -- --etapa objetos   --proyecto DIR --salida 01_objetos.blend
#   blender -b 01.blend -P b_tecnico.py -- --etapa rig       --proyecto DIR --salida 02_rig.blend
#   blender -b 02.blend -P b_tecnico.py -- --etapa animacion --proyecto DIR --salida 04_animacion.blend
#   blender -b 04.blend -P b_tecnico.py -- --etapa efectos   --proyecto DIR --salida 04b_efectos.blend
# objetos: entorno (suelo de baldosas, paredes, accesorios) + una pieza GP por pieza del guion (+ su version rayos X)
# rig: RIG_objeto con un hueso por pieza (pivote en su base o en su bisagra) y la jerarquia 'padre' del guion
# animacion: montaje pieza a pieza (cae y rebota), rayos X y resalte lima por escena, movimientos de pieza,
#            sombra azul proyectada que se rehace cuando cambia lo visible, y camara isometrica por plano
# efectos: agua, gotas, charco, burbujas, vapor, flechas, llama y chispas (fotogramas GP cada 2) + papel y grano
import os, sys, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Quaternion
import gp_base as GB, personajes as PJ, tecnico as T
import comic_parametros as CP

# ================================================================ objetos
def mallas_modelo(dirp):
    """Partes del modelo descargado (modo 'modelo' del agente), por id."""
    pj = GB.leer_json(os.path.join(dirp, "proyecto.json"))
    rel = pj.get("archivos", {}).get("modelo")
    if not rel: return {}
    return {q["id"]: q for q in GB.leer_json(os.path.join(dirp, rel))["partes"]}

def adornos_proyecto(dirp):
    """Adornos del modo 'detalles' (adornos.json), por id de pieza. Sobreviven a las revisiones del guion: van aparte."""
    pj = GB.leer_json(os.path.join(dirp, "proyecto.json"))
    rel = pj.get("archivos", {}).get("detalles")
    if not rel or not os.path.exists(os.path.join(dirp, rel)): return {}
    out = {}
    for a in GB.leer_json(os.path.join(dirp, rel)).get("adornos", []): out.setdefault(a["pieza"], []).append(a)
    return out

def unir_partes(ids, partes):
    V, F, E = [], [], []
    for i in ids:
        q = partes[i]; ov, of = len(V), len(F)
        V += q["vertices"]; F += [[ov + k for k in f] for f in q["caras"]]
        E += [[a + ov, b + ov, f1 + of if f1 >= 0 else -1, f2 + of if f2 >= 0 else -1, v] for a, b, f1, f2, v in q["aristas"]]
    return dict(vertices=V, caras=F, aristas=E)

def etapa_objetos(dirp, params, guion, sin_adornos=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    GB.configurar(params); sc = GB.configurar_escena(params); sc.name = "Tecnico"
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[0].default_value = T.colt("papel")
    raiz = GB.coleccion("Tecnico"); c_ent = GB.coleccion("Entorno", raiz); c_p = GB.coleccion("Piezas", raiz)
    c_rx = GB.coleccion("Rayos X", raiz); c_cam = GB.coleccion("Camara", raiz)
    indice = {"piezas": {}, "pared_y": 0.0, "estilo": "tecnico"}
    partes = mallas_modelo(dirp) if any(p["forma"] == "malla" for p in guion["piezas"]) else {}
    adornos = {} if sin_adornos else adornos_proyecto(dirp); T.AVISOS_ADORNOS.clear()
    for p in guion["piezas"]:
        if p["forma"] == "malla": p = dict(p, _malla=unir_partes(p["partes"], partes))
        if p["id"] in adornos: p = dict(p, _adornos=adornos[p["id"]])
        ob = T.dibujar_pieza(p, c_p, params)
        info = dict(objeto=ob.name, rx=None, geo=json.loads(ob["comic_pieza"]), padre=p["padre"], bisagra=p["bisagra"],
                    material=p["material"], forma=p["forma"])
        if p["material"] in ("solido", "metal"):
            orx = T.dibujar_pieza(p, c_rx, params, rx=True); orx.hide_render = True; orx.hide_viewport = True
            info["rx"] = orx.name
        indice["piezas"][p["id"]] = info
    # el entorno despues de las piezas: los accesorios se apartan del objeto y nunca quedan delante de el
    pts = [q for v in indice["piezas"].values() for q in v["geo"]["puntos"]] or [[0, 0, 0]]
    x0, x1 = min(q[0] for q in pts), max(q[0] for q in pts); y0, y1 = min(q[1] for q in pts), max(q[1] for q in pts)
    alto = max(q[2] for q in pts); escala = max(0.45, min(1.3, alto / 1.4))
    acc = []
    for k, a in enumerate(guion.get("accesorios", [])):
        x, y = a["x"] * escala, a["y"] * escala
        if x0 - 0.35 < x < x1 + 0.35 and y < y1 + 0.2:          # delante o encima del objeto: a un lado
            x = (x1 + 0.45 + 0.35 * k) if (k % 2 == 0) else (x0 - 0.45 - 0.35 * k)
        acc.append(dict(a, x=x, y=y))
    guion = dict(guion, accesorios=acc)
    ancho = max(3.0, 7.0 * escala, (max(abs(x0), abs(x1)) + 0.8) / 0.5, (y1 + 0.8) / 0.42)   # paredes detras de toda la maqueta
    ent, yw = T.entorno(c_ent, params, guion, ancho=ancho)
    indice["pared_y"] = yw
    sombra = GB.nuevo_gp("Sombra", c_ent, profundidad3d=True)
    T.sombra_piezas(T.Pincel(sombra, "sombra"), [v["geo"] for v in indice["piezas"].values() if v["material"] in ("solido", "metal")],
                    params, pared_y=yw)
    cam = camara(params, c_cam)
    enc = encuadre(params, indice, "general", "objeto", guion)
    colocar(cam, enc, params)
    sc["comic_indice"] = json.dumps(indice)
    return indice

def camara(params, col_):
    cd = bpy.data.cameras.new("Camara"); cd.type = 'ORTHO'; cd.clip_start = 0.05; cd.clip_end = 300; cd.sensor_fit = 'AUTO'
    cam = bpy.data.objects.new("Camara", cd); col_.objects.link(cam)
    obj = bpy.data.objects.new("Camara_objetivo", None); col_.objects.link(obj)
    c = cam.constraints.new('TRACK_TO'); c.target = obj; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam

def caja_total(indice, ids=None):
    pts = [Vector(q) for pid, v in indice["piezas"].items() if ids is None or pid in ids for q in v["geo"]["puntos"]]
    if not pts: return Vector((0, 0, 0.5)), 1.0
    mn = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
    mx = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
    return (mn + mx) / 2, (mx - mn).length / 2

def encuadre(params, indice, plano, objetivo, guion, az=None, factor=1.0, objetivos=None, visibles=None):
    """Encuadre ortografico: proyecta los puntos del objetivo (o del grupo 'objetivos') en los ejes de la camara y lo hace caber.
    visibles: piezas que ya estan montadas en la escena; el plano general encuadra solo esas (no la maqueta que aun no existe)."""
    d = T.dir_camara(params, az); fwd = -d
    right = fwd.cross(Vector((0, 0, 1))); right = right.normalized() if right.length > 1e-4 else Vector((1, 0, 0))
    up = right.cross(fwd).normalized()
    grupo = [i for i in (objetivos or []) if i in indice["piezas"]]
    w, h, _ = CP.resolucion(params); a = w / h
    if plano != "general" and len(grupo) > 1:
        pts = [Vector(q) for i in grupo for q in indice["piezas"][i]["geo"]["puntos"]]; m = 1.3 if plano == "medio" else 1.6
    elif plano != "general" and (objetivo in indice["piezas"] or grupo):
        objetivo = objetivo if objetivo in indice["piezas"] else grupo[0]
        pts = [Vector(q) for q in indice["piezas"][objetivo]["geo"]["puntos"]]; m = 1.35 if plano == "medio" else 1.9
    else:
        hay = [pid for pid in (visibles or []) if pid in indice["piezas"]] or list(indice["piezas"])
        pts = [Vector(q) for pid in hay for q in indice["piezas"][pid]["geo"]["puntos"]] or [Vector((0, 0, 0)), Vector((0, 0, 1))]
        m = 1.25 if plano == "medio" else (1.3 if a >= 1 else 1.75)        # en horizontal el general no necesita tanto aire
    xs = [q.dot(right) for q in pts]; ys = [q.dot(up) for q in pts]
    W, H = max(xs) - min(xs), max(ys) - min(ys)
    xc, yc = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    if plano == "general": yc -= H * 0.08                       # algo de suelo y de sombra debajo
    mw = min(m, 1.2 if plano == "general" else 1.3) if a >= 1 else m      # en horizontal, menos margen a los lados (maquetas anchas)
    minimo = 0.45
    if plano != "general":           # sin zooms extremos: un minimo relativo al plano general (contexto de la maqueta)
        minimo = max(minimo, encuadre(params, indice, "general", "objeto", guion, az=az, visibles=visibles)["alto"] * (0.35 if plano == "medio" else 0.25))
    alto = max(H * m, W * mw / a, minimo) * factor
    cen = sum(pts, Vector()) / len(pts)
    c = right * xc + up * yc + fwd * cen.dot(fwd)
    mayor = alto * a if a >= 1 else alto
    return dict(cam=c + d * 30.0, obj=c, ortho=mayor, alto=alto)

def colocar(cam, enc, params):
    cam.location = enc["cam"]; bpy.data.objects["Camara_objetivo"].location = enc["obj"]; cam.data.ortho_scale = enc["ortho"]

# ================================================================ rig
def pivote(info):
    g = info["geo"]; pts = [Vector(q) for q in g["puntos"]]
    c = Vector(g["centro"]); z0 = g["z0"]
    b = info.get("bisagra", "ninguna")
    if b == "atras": return Vector((c.x, max(q.y for q in pts), z0))
    if b == "delante": return Vector((c.x, min(q.y for q in pts), z0))
    if b == "izquierda": return Vector((min(q.x for q in pts), c.y, z0))
    if b == "derecha": return Vector((max(q.x for q in pts), c.y, z0))
    base = Vector(g["base"]) if info["forma"] != "manguera" else Vector((c.x, c.y, z0))
    return base

def bbox_mundo(ob):
    pts = []
    M = ob.matrix_world
    for L in ob.data.layers:
        for f in L.frames:
            for st in f.drawing.strokes:
                for p in st.points: pts.append(M @ Vector(p.position))
    if not pts: return None
    return [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]

def etapa_rig(dirp, params, guion):
    sc = bpy.context.scene; indice = json.loads(sc["comic_indice"])
    bpy.context.view_layer.update()      # el matrix_world guardado en el .blend puede no estar evaluado
    col_ = GB.coleccion("Rig", bpy.data.collections.get("Tecnico"))
    antes = {}
    for pid, v in indice["piezas"].items():
        for n in (v["objeto"], v["rx"]):
            if n: antes[n] = bbox_mundo(bpy.data.objects[n])
    huesos = [("raiz", (0, 0), (0, 0.3), None)]
    arm = bpy.data.armatures.new("RIG_objeto"); arm.display_type = 'STICK'
    rig = bpy.data.objects.new("RIG_objeto", arm); col_.objects.link(rig); rig.show_in_front = True
    vl = bpy.context.view_layer; vl.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    r = arm.edit_bones.new("raiz"); r.head = (0, 0, 0); r.tail = (0, 0, 0.3)
    ebs = {"raiz": r}
    for pid, v in indice["piezas"].items():
        eb = arm.edit_bones.new(pid); h = pivote(v); alto = max(0.08, (v["geo"]["z1"] - v["geo"]["z0"]) * 0.5)
        eb.head = h; eb.tail = h + Vector((0, 0, alto)); eb.roll = 0.0; ebs[pid] = eb
    for pid, v in indice["piezas"].items():
        ebs[pid].parent = ebs.get(v["padre"]) or ebs["raiz"]
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
    bpy.context.view_layer.update()
    for pid, v in indice["piezas"].items():
        b = rig.data.bones[pid]
        inv = (rig.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
        for n in (v["objeto"], v["rx"]):
            if not n: continue
            ob = bpy.data.objects[n]; mw = ob.matrix_basis.copy()     # sin padre todavia: basis = mundo
            ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = pid; ob.matrix_parent_inverse = inv
            ob.matrix_basis = mw
    bpy.context.view_layer.update()
    desvio = 0.0
    for n, bb0 in antes.items():
        bb1 = bbox_mundo(bpy.data.objects[n])
        if bb0 and bb1: desvio = max(desvio, max(abs(x - y) for x, y in zip(bb0, bb1)))
    rig["comic_tipo"] = "rig_objeto"
    return dict(huesos=len(rig.data.bones), piezas=len(indice["piezas"]), desvio_max=round(desvio, 6))

# ================================================================ animacion
def suave(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

def rebote(u):
    """Caida con rebote: 1 -> 0 con un pequeno bote al final."""
    if u < 0.6: return 1 - (u / 0.6) ** 2
    v = (u - 0.6) / 0.4; return 0.12 * math.sin(math.pi * v) * (1 - v)

def etapa_animacion(dirp, params, guion, tiempos):
    sc = bpy.context.scene; indice = json.loads(sc["comic_indice"])
    GB.configurar_escena(params, sc)
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[0].default_value = T.colt("papel")
    fps = params["fps"]; paso = 2 if params.get("en_dos", True) else 1
    sc.frame_start, sc.frame_end = 1, max(2, tiempos["frame_fin"])
    rig = bpy.data.objects["RIG_objeto"]; cam = bpy.data.objects["Camara"]; tgt = bpy.data.objects["Camara_objetivo"]
    claves = {}
    def put(id_, ruta, idx, f, v, it="CONSTANT"): claves.setdefault((id_, ruta, idx), {})[int(f)] = (float(v), it)
    # audio y marcadores
    se = sc.sequence_editor_create()
    for s in list(se.strips): se.strips.remove(s)
    if tiempos.get("pista_unica"): se.strips.new_sound("audio_propio", os.path.join(dirp, tiempos["pista_unica"]), channel=1, frame_start=1)
    else:
        for e in tiempos["escenas"]:
            for ln in e["lineas"]: se.strips.new_sound(f"E{e['id']}", os.path.join(dirp, ln["wav"]), channel=1, frame_start=ln["inicio"])
    for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
    for esc, te in zip(guion["escenas"], tiempos["escenas"]): sc.timeline_markers.new(f"E{esc['id']} {esc['descripcion'][:30]}", frame=te["inicio"])
    # cuando aparece y desaparece cada pieza
    aparece = {pid: 0 for pid in indice["piezas"]}; desaparece = {pid: 10 ** 6 for pid in indice["piezas"]}
    vista_en = {}
    for k, esc in enumerate(guion["escenas"]):
        for pid in esc["aparecen"]:
            if pid in aparece and aparece[pid] == 0 and not any(pid in e["aparecen"] for e in guion["escenas"][:k]): aparece[pid] = k
        for pid in esc["desaparecen"]: desaparece[pid] = min(desaparece[pid], k)
    listadas = {pid for e in guion["escenas"] for pid in e["aparecen"]}
    # inicio de cada caida (escalonadas) y visibilidad por fotograma de cambio
    caida = {}
    for k, (esc, te) in enumerate(zip(guion["escenas"], tiempos["escenas"])):
        f0, f1 = te["inicio"], te["fin"]
        for i, pid in enumerate([p for p in esc["aparecen"] if aparece.get(p) == k and p in listadas]):
            caida[pid] = min(f1 - 16, f0 + 6 + i * 10)
    def visible(pid, f, k):
        if pid in caida and aparece[pid] == k: return f >= caida[pid]
        return aparece[pid] <= k < desaparece[pid]
    eventos = sorted({1} | {te["inicio"] for te in tiempos["escenas"]} | set(caida.values()))
    hueso_rest = {pid: rig.data.bones[pid].matrix_local.to_3x3() for pid in indice["piezas"]}
    acum = {}            # desplazamiento acumulado de cada pieza (subir/bajar/desplazar se suman; 'volver' lo deshace)
    def a_local(pid, v): return hueso_rest[pid].inverted() @ Vector(v)
    for k, (esc, te) in enumerate(zip(guion["escenas"], tiempos["escenas"])):
        f0, f1 = te["inicio"], te["fin"]; n = max(1, f1 - f0)
        rx = set(esc["rayos_x"])
        for pid, v in indice["piezas"].items():
            ob = bpy.data.objects[v["objeto"]]; orx = bpy.data.objects[v["rx"]] if v["rx"] else None
            usa_rx = orx is not None and pid in rx
            for f in sorted({f0} | ({caida[pid]} if pid in caida and aparece[pid] == k else set())):
                vis = visible(pid, f, k)
                put(ob, "hide_render", 0, f, 0.0 if (vis and not usa_rx) else 1.0); put(ob, "hide_viewport", 0, f, 0.0 if (vis and not usa_rx) else 1.0)
                if orx: put(orx, "hide_render", 0, f, 0.0 if (vis and usa_rx) else 1.0); put(orx, "hide_viewport", 0, f, 0.0 if (vis and usa_rx) else 1.0)
            # resalte lima: las que se piden y las que acaban de entrar
            resalta = pid in esc["resaltar"] or (pid in caida and aparece[pid] == k)
            a0 = caida.get(pid, f0) if (pid in caida and aparece[pid] == k) else f0
            for o in (ob, orx):
                if o is None: continue
                put(o.data, 'layers["resalte"].hide', 0, f0, 1.0)
                if resalta:
                    put(o.data, 'layers["resalte"].hide', 0, a0, 0.0)
                    put(o.data, 'layers["resalte"].hide', 0, min(f1 - 1, a0 + max(int(1.6 * fps), int(0.55 * n))), 1.0)
            # caida con rebote
            if pid in caida and aparece[pid] == k:
                fa = caida[pid]; L = 16
                for f in range(fa, fa + L + 1, paso):
                    z = 0.9 * rebote((f - fa) / L); loc = a_local(pid, (0, 0, z))
                    for i in range(3): put(rig, f'pose.bones["{pid}"].location', i, f, loc[i])
        # movimientos de pieza
        for an in sorted(esc["animaciones"], key=lambda a: a["inicio"]):
            pid = an["pieza"]; mov = an["movimiento"]; fa = f0 + int(an["inicio"] * n); fb = max(fa + 2, f0 + int(an["fin"] * n))
            cant = an.get("cantidad"); ruta_q = f'pose.bones["{pid}"].rotation_quaternion'
            ruta_l = f'pose.bones["{pid}"].location'; ruta_s = f'pose.bones["{pid}"].scale'
            def quat(eje_mundo, ang):
                q = Quaternion(a_local(pid, eje_mundo).normalized(), ang); return q
            if mov in ("girar", "oscilar"):
                for f in range(fa, fb + 1, paso):
                    u = (f - fa) / max(1, fb - fa)
                    ang = 2 * math.pi * float(cant or 3) * u if mov == "girar" else math.radians(float(cant or 25)) * math.sin(2 * math.pi * 1.5 * (f - fa) / fps) * math.sin(math.pi * u)
                    q = quat((0, 0, 1), ang)
                    for i in range(4): put(rig, ruta_q, i, f, q[i], "LINEAR")
                for i in range(4): put(rig, ruta_q, i, fb + 1, (1, 0, 0, 0)[i] if mov == "oscilar" else quat((0, 0, 1), 2 * math.pi * float(cant or 3))[i])
            elif mov == "vibrar":
                rnd = random.Random(pid + str(fa)); v0 = acum.get(pid, Vector())
                for f in range(fa, fb + 1, paso):
                    v_ = a_local(pid, v0 + Vector((rnd.uniform(-1, 1) * 0.012, rnd.uniform(-1, 1) * 0.006, rnd.uniform(-1, 1) * 0.008)))
                    for i in range(3): put(rig, ruta_l, i, f, v_[i])
                v_ = a_local(pid, v0)
                for i in range(3): put(rig, ruta_l, i, fb + paso, v_[i])
            elif mov in ("subir", "bajar", "desplazar_x", "desplazar_y", "volver"):
                v0 = acum.get(pid, Vector())
                if mov == "volver": vec = -v0
                else:
                    d = float(cant if cant is not None else 0.3)
                    vec = Vector({"subir": (0, 0, d), "bajar": (0, 0, -d), "desplazar_x": (d, 0, 0), "desplazar_y": (0, d, 0)}[mov])
                for f in range(fa, fb + 1, paso):
                    v_ = a_local(pid, v0 + vec * suave((f - fa) / max(1, fb - fa)))
                    for i in range(3): put(rig, ruta_l, i, f, v_[i])
                acum[pid] = v0 + vec
            elif mov in ("llenar", "vaciar", "comprimir"):
                eje = a_local(pid, (0, 0, 1)); i_eje = max(range(3), key=lambda i: abs(eje[i]))
                for f in range(fa, fb + 1, paso):
                    u = suave((f - fa) / max(1, fb - fa))
                    s = (0.02 + 0.98 * u) if mov == "llenar" else (1 - 0.98 * u) if mov == "vaciar" else 1 - 0.35 * math.sin(math.pi * u)
                    put(rig, ruta_s, i_eje, f, s)
                if mov == "llenar":                    # vacio desde el principio de la escena
                    for f in range(f0, fa, paso): put(rig, ruta_s, i_eje, f, 0.02)
            elif mov in ("abrir", "cerrar"):
                b = indice["piezas"][pid].get("bisagra", "atras")
                eje, signo = {"atras": ((1, 0, 0), -1), "delante": ((1, 0, 0), 1), "izquierda": ((0, 0, 1), -1),
                              "derecha": ((0, 0, 1), 1), "ninguna": ((1, 0, 0), -1)}[b]
                ang = math.radians(float(cant or 100)) * signo
                for f in range(fa, fb + 1, paso):
                    u = suave((f - fa) / max(1, fb - fa)); q = quat(eje, ang * (u if mov == "abrir" else 1 - u))
                    for i in range(4): put(rig, ruta_q, i, f, q[i])
        # camara
        c = esc["camara"]; az0 = 35
        vis = [pid for pid in indice["piezas"] if aparece[pid] <= k < desaparece[pid]]     # lo que ya esta montado
        fa_ = {"acercar": 1.22, "alejar": 1.0}.get(c["movimiento"], 1.0); fb_ = {"acercar": 1.0, "alejar": 1.25}.get(c["movimiento"], 1.0)
        if c["plano"] == "general" and c["movimiento"] == "alejar": fa_, fb_ = 0.82, 1.0       # alejarse hasta el general, no mas alla
        aza, azb = (az0 - 14, az0 + 14) if c["movimiento"] == "rodear" and params.get("formato") != "2d" else (az0, az0)
        for f, fac, az, it in ((f0, fa_, aza, "BEZIER"), (f1 - 1, fb_, azb, "CONSTANT")):
            e = encuadre(params, indice, c["plano"], c["objetivo"], guion, az=az, factor=fac, objetivos=c.get("objetivos"), visibles=vis)
            for i in range(3): put(cam, "location", i, f, e["cam"][i], it); put(tgt, "location", i, f, e["obj"][i], it)
            put(cam.data, "ortho_scale", 0, f, e["ortho"], it)
        if c["movimiento"] == "rodear" and params.get("formato") != "2d":
            for j in range(1, 4):
                f = f0 + int(n * j / 4); e = encuadre(params, indice, c["plano"], c["objetivo"], guion, az=aza + (azb - aza) * j / 4, objetivos=c.get("objetivos"), visibles=vis)
                for i in range(3): put(cam, "location", i, f, e["cam"][i], "BEZIER")
        alto = encuadre(params, indice, c["plano"], c["objetivo"], guion, objetivos=c.get("objetivos"), visibles=vis)["alto"]
        g = max(0.35, min(1.5, (alto / 2.6) ** 0.6))
        for o in bpy.data.objects:
            if o.type == 'GREASEPENCIL':
                m = o.modifiers.get("Grosor por plano") or o.modifiers.new("Grosor por plano", 'GREASE_PENCIL_THICKNESS')
                put(o, 'modifiers["Grosor por plano"].thickness_factor', 0, f0, g)
    # sombra: un dibujo por cada cambio de lo visible
    sombra = bpy.data.objects["Sombra"]; L = sombra.data.layers["sombra"]
    for fr in list(L.frames): L.frames.remove(fr.frame_number)
    for f in eventos:
        k = max(i for i, te in enumerate(tiempos["escenas"]) if te["inicio"] <= f)
        geos = [v["geo"] for pid, v in indice["piezas"].items() if v["material"] in ("solido", "metal") and visible(pid, f, k)]
        T.sombra_piezas(T.Pincel(sombra, "sombra", frame=f), geos, params, pared_y=indice["pared_y"])
    n = 0
    for (id_, ruta, idx), d in claves.items():
        ks = sorted((f, v, i) for f, (v, i) in d.items())
        if all(i == "CONSTANT" for _, _, i in ks): ks = [(f, v, "CONSTANT") for f, v in GB.simplificar([(f, v) for f, v, _ in ks])]
        GB.curva(id_, ruta, idx, ks); n += len(ks)
    sc.frame_set(1)
    return dict(claves=n, fotogramas=sc.frame_end, cambios_de_sombra=len(eventos), piezas=len(indice["piezas"]))

# ================================================================ efectos
def etapa_efectos(dirp, params, guion, tiempos):
    import b_efectos as BE
    sc = bpy.context.scene; indice = json.loads(sc["comic_indice"]); fps = params["fps"]
    col_ = GB.coleccion("Efectos", bpy.data.collections.get("Tecnico"))
    vista = T.dir_camara(params); off = vista * T.EMPUJE * 1.3
    n_fx = 0; avisos = []
    def geo(pid): return indice["piezas"][pid]["geo"]
    def objeto(nombre):
        nonlocal n_fx
        n_fx += 1; ob = GB.nuevo_gp(f"FX_{n_fx:03d}_{nombre}", col_, profundidad3d=False); ob.location = off; return ob
    def hervir(nombre, fa, fb, dibujar):
        ob = objeto(nombre)
        for k, f in enumerate(range(fa, fb, 2)):
            dibujar(T.Pincel(ob, "fx", frame=f), k, (f - fa) / max(1, fb - fa), (f - fa) / fps)
        T.Pincel(ob, "fx", frame=fb); T.Pincel(ob, "fx", frame=0)
        return ob
    def W(v): return Vector(v) - off
    rnd = random.Random(4)
    # ejes de pantalla para iconos y sobres que miran a camara
    fwd = -vista; dere = fwd.cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(fwd).normalized()
    def plano(cen, x, y): return W(cen + dere * x + arr * y)
    def circulo(cen, r, n=32, a0=0.0, a1=2 * math.pi): return [plano(cen, r * math.cos(a0 + (a1 - a0) * i / n), r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    def emerge(s):       # escala de aparicion con un pequeno rebote
        k = min(1.0, s / 0.3); return k * 1.2 if k < 0.85 else 1.02 - (k - 0.85) * 0.13
    def sobre(p, cen, w, mat_):
        h = w * 0.66; esq = [plano(cen, x * w / 2, y * h / 2) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        p.cara(esq, mat_); p.linea(esq + esq[:1], "T tinta", T.R_TINTA * 0.8)
        p.linea([plano(cen, -w / 2, h / 2), plano(cen, 0, -h * 0.08), plano(cen, w / 2, h / 2)], "T tinta", T.R_TINTA * 0.7)
    def recorrido(pid, g):
        """Puntos (mundo) por los que viaja un flujo: el camino suavizado de una manguera o, si no, por encima de la pieza."""
        if g.get("tramo"): return [Vector(q) for q in g["tramo"]]
        c = Vector(g["centro"]); r = max(0.1, g["radio"]); z = g["z1"] + 0.1
        return [Vector((c.x, c.y, z)) - dere * r * 1.2, Vector((c.x, c.y, z)) + dere * r * 1.2]
    for esc, te in zip(guion["escenas"], tiempos["escenas"]):
        f0, f1 = te["inicio"], te["fin"]
        for ef in esc["efectos"]:
            t, pid = ef["tipo"], ef["pieza"]; g = geo(pid)
            c = Vector(g["centro"]); r = max(0.05, g["radio"]); z0, z1 = g["z0"], g["z1"]
            fa = f0 + int(ef["momento"] * (f1 - f0))
            # duracion en segundos; <= 1 suele ser una fraccion de la escena (Gemini la confunde con 'momento')
            largo = int(ef["duracion"] * fps) if ef["duracion"] > 1.0 else max(int(1.5 * fps), int(ef["duracion"] * (f1 - f0)))
            fb = min(f1, fa + max(6, largo))
            try:
                if t == "chorro":
                    def d(p, k, u, s):
                        top = z1 + 0.7; pts = [W((c.x + 0.012 * math.sin(s * 30 + j), c.y, top - (top - z0 - 0.1) * j / 12)) for j in range(13)]
                        p.linea(pts, "T trazo agua 0.85", 0.03); p.linea([q + Vector((0.01, 0, 0)) for q in pts], "T trazo blanco_hueso 0.6", 0.007)
                        for j in range(4):
                            a = rnd.uniform(0, 6.28); zz = z0 + 0.12 + rnd.uniform(0, 0.1)
                            p.cara([W(q + Vector((0, 0, zz))) for q in T.circ3(c.x + 0.12 * math.cos(a), c.y + 0.12 * math.sin(a), 0.012, 0, 8)], "T plano agua 0.9")
                    hervir("chorro", fa, fb, d)
                elif t == "gotas":
                    semillas = [(rnd.uniform(-r, r) * 0.7, rnd.uniform(0, 1)) for _ in range(6)]
                    def d(p, k, u, s):
                        for dx, ph in semillas:
                            v = (s * 1.4 + ph) % 1.0; zz = z0 - (z0) * v
                            q = W((c.x + dx, c.y - r * 0.5, max(0.01, zz)))
                            p.cara([q + Vector((0.018 * math.cos(a), 0, 0.026 * math.sin(a) + (0.012 if math.sin(a) > 0 else 0))) for a in [i * math.pi / 5 for i in range(10)]], "T plano agua 0.9")
                    hervir("gotas", fa, fb, d)
                elif t == "charco":
                    def d(p, k, u, s):
                        rr = (0.15 + 0.7 * u) * max(0.6, r)
                        pts = [W((c.x - r * 0.4 + rr * 1.3 * math.cos(a) * (1 + 0.15 * math.sin(3 * a + k * 0.3)), c.y - r * 0.6 + rr * math.sin(a) * (1 + 0.12 * math.cos(4 * a)), 0.006))
                               for a in [i * 2 * math.pi / 36 for i in range(36)]]
                        p.cara(pts, "T plano agua 0.55"); p.linea(pts + pts[:1], "T trazo azul 0.6", 0.006)
                    hervir("charco", fa, fb, d)
                elif t == "salpicadura":
                    gotas = [(rnd.uniform(0, 6.28), rnd.uniform(0.6, 1.4)) for _ in range(12)]
                    def d(p, k, u, s):
                        for a, v in gotas:
                            dd = r * (0.6 + 1.2 * u * v); zz = z1 * 0.6 + 0.5 * math.sin(math.pi * min(1, u * v))
                            q = W((c.x + dd * math.cos(a), c.y + dd * math.sin(a), max(0.01, zz)))
                            p.cara([q + Vector((0.016 * math.cos(b), 0, 0.016 * math.sin(b))) for b in [i * math.pi / 4 for i in range(8)]], "T plano agua 0.85")
                    hervir("salpicadura", fa, fb, d)
                elif t == "burbujas":
                    bs = [(rnd.uniform(0, 6.28), rnd.uniform(0, r * 0.8), rnd.uniform(0, 1), rnd.uniform(0.01, 0.025)) for _ in range(16)]
                    def d(p, k, u, s):
                        for a, rr, ph, tam in bs:
                            v = (s * 0.7 + ph) % 1.0
                            q = W((c.x + rr * math.cos(a) + 0.01 * math.sin(s * 8 + ph * 9), c.y + rr * math.sin(a), z0 + 0.03 + (z1 - z0 - 0.05) * v))
                            p.linea([q + Vector((tam * math.cos(b), 0, tam * math.sin(b))) for b in [i * math.pi / 6 for i in range(13)]], "T trazo blanco_hueso 0.9", 0.004)
                    hervir("burbujas", fa, fb, d)
                elif t == "vapor":
                    hilos = [(rnd.uniform(-r, r) * 0.5, rnd.uniform(0, 1)) for _ in range(4)]
                    def d(p, k, u, s):
                        for dx, ph in hilos:
                            v = (s * 0.5 + ph) % 1.0
                            pts = [W((c.x + dx + 0.06 * math.sin(j * 0.9 + s * 3 + ph * 7), c.y, z1 + 0.05 + v * 0.3 + j * 0.06)) for j in range(9)]
                            p.linea(pts, "T trazo gris_claro 0.75", 0.022 * (1 - v * 0.6), afilar=True)
                    hervir("vapor", fa, fb, d)
                elif t == "flecha_giro":
                    def d(p, k, u, s):
                        zz = (z0 + z1) / 2 + 0.02; rr = r * 1.25; a1 = 1.6 * math.pi * min(1, u * 3)
                        pts = [W((c.x + rr * math.cos(-0.6 + a), c.y + rr * math.sin(-0.6 + a), zz)) for a in [a1 * i / 24 for i in range(25)]]
                        if len(pts) > 2:
                            p.linea(pts, "T trazo azul", 0.022); fin = pts[-1]; tg = (pts[-1] - pts[-2]).normalized(); nr = tg.cross(Vector((0, 0, 1))).normalized()
                            p.cara([fin + tg * 0.09, fin + nr * 0.05, fin - nr * 0.05], "T plano azul")
                    hervir("flecha_giro", fa, fb, d)
                elif t in ("flecha_arriba", "flecha_abajo"):
                    sgn = 1 if t == "flecha_arriba" else -1
                    def d(p, k, u, s):
                        lado = Vector(vista.cross(Vector((0, 0, 1)))).normalized() * (r + 0.12)
                        base = Vector((c.x, c.y, (z0 + z1) / 2)) - lado
                        a = base - Vector((0, 0, 0.25 * sgn)); b = base + Vector((0, 0, (0.25 + 0.05 * math.sin(s * 6)) * sgn))
                        p.linea([W(a), W(b)], "T trazo azul", 0.024)
                        nr = lado.normalized() * 0.06
                        p.cara([W(b + Vector((0, 0, 0.1 * sgn))), W(b + nr), W(b - nr)], "T plano azul")
                    hervir(t, fa, fb, d)
                elif t == "llama":
                    def d(p, k, u, s):
                        for j in range(10):
                            a = 2 * math.pi * j / 10; q = Vector((c.x + r * 0.7 * math.cos(a), c.y + r * 0.7 * math.sin(a), z1))
                            h = 0.12 + 0.05 * math.sin(s * 14 + j)
                            for col, esc_ in (("azul", 1.0), ("amarillo", 0.55)):
                                p.cara([W(q + Vector((-0.035 * esc_, 0, 0))), W(q + Vector((0, 0, h * esc_))), W(q + Vector((0.035 * esc_, 0, 0)))], f"T plano {col} 0.9")
                    hervir("llama", fa, fb, d)
                elif t == "chispas":
                    def d(p, k, u, s):
                        for j in range(4):
                            a = rnd.uniform(0, 6.28); q = Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), rnd.uniform(z0, z1)))
                            pts = [W(q + Vector((0.03 * i * math.cos(a), 0.03 * i * math.sin(a), 0.02 * (-1) ** i))) for i in range(5)]
                            p.linea(pts, "T trazo amarillo", 0.01)
                    hervir("chispas", fa, fb, d)
                elif t in ("flujo", "flujo_vuelta"):
                    ruta = recorrido(pid, g)
                    if t == "flujo_vuelta": ruta = ruta[::-1]
                    acum_ = [0.0]
                    for a_, b_ in zip(ruta, ruta[1:]): acum_.append(acum_[-1] + (b_ - a_).length)
                    L = max(0.05, acum_[-1]); dur = (fb - fa) / fps
                    vel = max(0.7, L / max(0.5, dur * 0.7))           # el primer sobre llega antes del 70 % del efecto
                    dt = max(0.3, min(0.9, L / 3)) / vel; ultimo = max(0.0, dur - L / vel)
                    ancho = max(0.17, min(0.26, L / 6)); mat_ = "T plano mostaza" if t == "flujo_vuelta" else "T plano blanco_hueso"
                    def punto(dist):
                        for i in range(len(ruta) - 1):
                            if dist <= acum_[i + 1] or i == len(ruta) - 2:
                                u = (dist - acum_[i]) / max(1e-6, acum_[i + 1] - acum_[i]); return ruta[i].lerp(ruta[i + 1], min(1.0, max(0.0, u)))
                    def d(p, k, u, s, ruta=ruta, punto=punto, L=L, vel=vel, dt=dt, ultimo=ultimo, ancho=ancho, mat_=mat_):
                        j = 0
                        while j * dt <= ultimo + 1e-6:
                            dist = (s - j * dt) * vel
                            if 0 <= dist <= L: sobre(p, punto(dist), ancho, mat_)
                            j += 1
                    hervir(t, fa, fb, d)
                elif t in ("aprobado", "rechazo"):
                    tam = max(0.12, min(0.3, r * 0.5)); cen0 = Vector((c.x, c.y, z1 + tam + 0.12))
                    def d(p, k, u, s, tam=tam, cen0=cen0, t=t):
                        e = emerge(s) * tam; cen = cen0 + (dere * 0.035 * math.sin(s * 45) * max(0.0, 1 - s / 0.6) if t == "rechazo" else Vector())
                        if e <= 0.005: return
                        p.cara(circulo(cen, e)[:-1], "T plano " + ("menta_oscuro" if t == "aprobado" else "rojo"))
                        p.linea(circulo(cen, e), "T tinta", T.R_TINTA * 1.1)
                        trazos = [[(-0.45, 0.0), (-0.12, -0.34), (0.48, 0.36)]] if t == "aprobado" else [[(-0.36, -0.36), (0.36, 0.36)], [(-0.36, 0.36), (0.36, -0.36)]]
                        for tr in trazos: p.linea([plano(cen, x * e, y * e) for x, y in tr], "T trazo blanco_hueso", e * 0.13)
                    hervir(t, fa, fb, d)
                elif t == "ondas":
                    cen0 = Vector((c.x, c.y, z1 + 0.04)); tam = max(0.25, min(0.6, r * 1.4))
                    def d(p, k, u, s, cen0=cen0, tam=tam):
                        p.cara(circulo(cen0, 0.025, 12)[:-1], f"T plano {T.TEMA['fx_ondas']}")
                        for j in range(3):
                            v = (s * 0.9 + j / 3) % 1.0; rr = 0.06 + v * tam
                            if T.TEMA["lateral"]: p.linea(circulo(cen0, rr, 12, math.radians(45), math.radians(135)), "T tinta", 0.014 * (1 - 0.7 * v) + 0.006)
                            p.linea(circulo(cen0, rr, 12, math.radians(45), math.radians(135)), f"T trazo {T.TEMA['fx_ondas']}", 0.014 * (1 - 0.7 * v))
                    hervir("ondas", fa, fb, d)
                elif t == "reloj":
                    tam = max(0.12, min(0.28, r * 0.5)); cen0 = Vector((c.x, c.y, z1 + tam + 0.12))
                    def d(p, k, u, s, tam=tam, cen0=cen0):
                        e = emerge(s) * tam
                        if e <= 0.005: return
                        p.cara(circulo(cen0, e)[:-1], "T plano blanco_hueso"); p.linea(circulo(cen0, e), "T tinta", T.R_TINTA * 1.2)
                        for h in range(12):
                            a = 2 * math.pi * h / 12; p.linea([plano(cen0, 0.78 * e * math.cos(a), 0.78 * e * math.sin(a)), plano(cen0, 0.9 * e * math.cos(a), 0.9 * e * math.sin(a))], "T tinta", T.R_TINTA * 0.6)
                        a = math.pi / 2 - 2 * math.pi * min(1.0, u)                # una vuelta en lo que dura: el tiempo que se agota
                        if u > 0.02: p.cara(circulo(cen0, e * 0.7, 24, math.pi / 2, a) + [plano(cen0, 0, 0)], f"T plano {T.TEMA['fx_reloj']} 0.45")
                        p.linea([plano(cen0, 0, 0), plano(cen0, 0.72 * e * math.cos(a), 0.72 * e * math.sin(a))], "T tinta", T.R_TINTA * 1.1)
                        p.linea([plano(cen0, 0, 0), plano(cen0, 0, 0.45 * e)], "T tinta", T.R_TINTA * 1.3)
                    hervir("reloj", fa, fb, d)
                elif t == "alerta":
                    tam = max(0.14, min(0.3, r * 0.55)); cen0 = Vector((c.x, c.y, z1 + tam + 0.12))
                    def d(p, k, u, s, tam=tam, cen0=cen0):
                        e = emerge(s) * tam * (1 + 0.08 * math.sin(s * 9))           # late
                        if e <= 0.005: return
                        tri = [plano(cen0, e * math.cos(math.radians(90 + 120 * i)), e * math.sin(math.radians(90 + 120 * i)) - e * 0.1) for i in range(3)]
                        if int(s * 4) % 2 == 0:
                            p.linea(tri + tri[:1], "T trazo rojo 0.3", e * 0.3)
                        p.cara(tri, "T plano rojo"); p.linea(tri + tri[:1], "T tinta", T.R_TINTA * 1.2)
                        p.linea([plano(cen0, 0, e * 0.38), plano(cen0, 0, -e * 0.1)], "T trazo blanco_hueso", e * 0.09)
                        p.cara(circulo(cen0 + arr * (-e * 0.32), e * 0.07, 10)[:-1], "T plano blanco_hueso")
                    hervir("alerta", fa, fb, d)
                elif t == "rayo":
                    tam = max(0.14, min(0.3, r * 0.55)); cen0 = Vector((c.x, c.y, z1 + tam + 0.1))
                    forma = [(0.08, 0.48), (-0.28, -0.04), (-0.02, -0.04), (-0.1, -0.48), (0.28, 0.06), (0.02, 0.06)]
                    def d(p, k, u, s, tam=tam, cen0=cen0, forma=forma):
                        e = emerge(s) * tam * 2
                        if e <= 0.01: return
                        pts = [plano(cen0, x * e, y * e) for x, y in forma]
                        if int(s * 6) % 3 != 2:                                          # destello
                            for j in range(8):
                                a = 2 * math.pi * j / 8; p.linea([plano(cen0, 0.42 * e * math.cos(a), 0.42 * e * math.sin(a)),
                                                                  plano(cen0, 0.58 * e * math.cos(a), 0.58 * e * math.sin(a))], "T tinta", T.R_TINTA * 0.8)
                        p.cara(pts, "T plano lima"); p.linea(pts + pts[:1], "T tinta", T.R_TINTA * 1.2)
                    hervir("rayo", fa, fb, d)
            except Exception as e:
                avisos.append(f"{t} en {pid}: {e}")
    # capa de pantalla: papel y grano de lapiz (multiplicar)
    pant = BE.Pantalla(params, col_); A = pant.A
    if not T.TEMA["papel"]:                      # tema vectorial: sin papel ni grano
        sc.frame_set(1); return dict(efectos=n_fx, avisos=avisos)
    if GB.imagen("papel"):
        ob = pant.objeto("Papel"); lp = GB.Lapiz(ob, "papel")
        lp.forma(GB.rect(-A / 2 * 1.05, -0.53, A / 2 * 1.05, 0.53), "Papel", linea=False)
        lp.capa.blend_mode = 'MULTIPLY'; lp.capa.opacity = 0.16; ob.location = (0, 0, 0.05)
    img = T.textura_grano()
    m = bpy.data.materials.new("Grano lapiz"); bpy.data.materials.create_gpencil_data(m); g = m.grease_pencil
    g.show_stroke = False; g.show_fill = True; g.fill_style = 'TEXTURE'; g.fill_image = img; g.texture_scale = (6, 6); g.mix_color = (1, 1, 1, 0)
    ob = pant.objeto("Grano"); ob.data.materials.append(m); lp = GB.Lapiz(ob, "grano")
    lp.trazo(GB.rect(-A / 2 * 1.05, -0.53, A / 2 * 1.05, 0.53), "Grano lapiz", radio=0.0004, cerrado=True, relleno=True)
    lp.capa.blend_mode = 'MULTIPLY'; ob.location = (0, 0, 0.06)
    sc.frame_set(1)
    return dict(efectos=n_fx, avisos=avisos)

# ================================================================ principal
def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    T.aplicar_tema(params)
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    etapa = a["etapa"]
    if etapa == "objetos":
        inf = etapa_objetos(dirp, params, guion, sin_adornos=bool(a.get("sin_adornos")))
        inf = dict(piezas=len(inf["piezas"]), rayos_x=sum(1 for v in inf["piezas"].values() if v["rx"]),
                   adornos=sum(len(v) for v in ({} if a.get("sin_adornos") else adornos_proyecto(dirp)).values()), avisos_adornos=T.AVISOS_ADORNOS[:12])
    elif etapa == "rig": inf = etapa_rig(dirp, params, guion)
    elif etapa == "animacion": inf = etapa_animacion(dirp, params, guion, GB.leer_json(os.path.join(dirp, "tiempos.json")))
    elif etapa == "efectos": inf = etapa_efectos(dirp, params, guion, GB.leer_json(os.path.join(dirp, "tiempos.json")))
    else: raise SystemExit(f"etapa desconocida {etapa}")
    GB.guardar(a["salida"])
    if a.get("previa"):
        fr = [int(x) for x in str(a.get("frames", "1")).split(",") if x]
        for f in fr: GB.render_fotograma(a["previa"].replace("#", str(f)), f)
    print("INFORME " + json.dumps(inf, ensure_ascii=False))

if __name__ == "__main__":
    main()
