# ESTILO TECNICO: etapas de Blender del explicativo de objetos (modos 1, 2, 4 y efectos del agente).
#   blender -b -P b_tecnico.py -- --etapa objetos   --proyecto DIR --salida 01_objetos.blend
#   blender -b 01.blend -P b_tecnico.py -- --etapa rig       --proyecto DIR --salida 02_rig.blend
#   blender -b 02.blend -P b_tecnico.py -- --etapa animacion --proyecto DIR --salida 04_animacion.blend
#   blender -b 04.blend -P b_tecnico.py -- --etapa efectos   --proyecto DIR --salida 04b_efectos.blend
# objetos: entorno (suelo de baldosas, paredes, accesorios) + una pieza GP por pieza del guion (+ su version rayos X)
# rig: RIG_objeto con un hueso por pieza (pivote en su base o en su bisagra) y la jerarquia 'padre' del guion
# animacion: montaje pieza a pieza (cae y rebota; las mangueras de neon de los temas con mallas se dibujan), rayos X y resalte lima por escena, movimientos de pieza,
#            sombra azul proyectada que se rehace cuando cambia lo visible, y camara isometrica por plano
# efectos: agua, gotas, charco, burbujas, vapor, flechas, llama y chispas (fotogramas GP cada 2) + papel y grano
import os, re, sys, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Quaternion
import gp_base as GB, personajes as PJ, tecnico as T
import comic_parametros as CP
import cyberpunk as CYB          # tema con mallas (TEMA["mallas"]): piezas toon, Line Art, EEVEE

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
    mallas = bool(T.TEMA.get("mallas"))
    c_ad = GB.coleccion("Adornos y neon", raiz) if mallas else None     # fuera de Piezas: Line Art no los contornea
    c_pn = GB.coleccion("Piezas trazo neon", raiz) if mallas else None   # piezas con contorno de neon (el cerebro)
    indice = {"piezas": {}, "pared_y": 0.0, "estilo": "tecnico", "mallas": mallas}
    partes = mallas_modelo(dirp) if any(p["forma"] == "malla" for p in guion["piezas"]) else {}
    adornos = {} if sin_adornos else adornos_proyecto(dirp); T.AVISOS_ADORNOS.clear()
    T.recolocar_carteles(guion["piezas"], adornos, T.dir_camara(params))       # que no atraviesen otras piezas
    for p in guion["piezas"]:
        if p["forma"] == "malla": p = dict(p, _malla=unir_partes(p["partes"], partes))
        if p["id"] in adornos: p = dict(p, _adornos=adornos[p["id"]])
        if mallas:
            # tema cyberpunk: malla toon + adornos en malla (el GP se pintaria por delante de todo) + casco de resalte
            # el cerebro, en su coleccion: su Line Art propio pinta los surcos en neon (el negro general no lo traza)
            ob = CYB.pieza(p, c_pn if p["forma"] == "cerebro" else c_p, params, col_neon=c_ad)
            extra = CYB.adornos_pieza(p, ob, c_ad, params)
            geo = T.geometria(p)
            if extra: geo["puntos"] += [list(q) for q in extra]; geo["z1"] = max(geo["z1"], max(q.z for q in extra))
            casco = CYB.casco_resalte(ob, p) if CYB.estilo() == "toon" else None
            if casco is None: ob["resalte"] = 0.0      # cristal: el material lee esta propiedad (0-1) y se aviva
            info = dict(objeto=ob.name, rx=None, geo=geo, padre=p["padre"], bisagra=p["bisagra"], material=p["material"],
                        forma=p["forma"], resalte=CYB.RESALTE if casco else None, resalte_prop=None if casco else "resalte")
            if p["material"] in ("solido", "metal"):
                orx = CYB.pieza(p, c_rx, params, rx=True, col_neon=c_rx); orx.hide_render = True; orx.hide_viewport = True
                info["rx"] = orx.name
            indice["piezas"][p["id"]] = info
            continue
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
    if mallas:
        # suelo oscuro con rejilla de neon, luces de datos del toon, contornos Line Art y EEVEE con bloom (sin sombra GP)
        cen = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0.0)); tam = max(x1 - x0, y1 - y0, alto)
        CYB.suelo(c_ent, cen, tam, caja=(x0, y0, x1, y1))     # arcilla: suelo blanco y plataforma gris del diorama
        if CYB.estilo() in ("toon", "arcilla"): CYB.luces(cen + Vector((0, 0, alto / 2)), tam, c_ent)   # el cristal es emisivo
        if not T.TEMA.get("sin_gp"):         # arcilla: todo malla, sin Line Art (las formas se leen por la luz)
            CYB.contornos(c_p, c_ent)
            if c_pn.objects: CYB.contornos(c_pn, c_ent, color=T.TEMA.get("trazo_neon", "cian"), nombre="Contornos neon")
        if T.TEMA.get("rotulos") or T.TEMA.get("tarjetas"): rotulos_y_tarjetas(guion, indice, params, c_ad)
        CYB.render(sc, params)
    else:
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

def rotulos_y_tarjetas(guion, indice, params, col_):
    """Tema arcilla: en cada peana, su numero ('01.') tumbado en el borde de delante, y una tarjeta de interfaz flotante
    junto a su componente (referencias 1 y 3). El numero es el del paso del ciclo en que se resalta por primera vez (si el
    guion tiene ciclo); sin ciclo, el orden de aparicion. Rotulo y tarjeta son hijos de la peana: aparecen con ella."""
    vista = T.dir_camara(params); r = (-vista).cross(Vector((0, 0, 1))).normalized()
    peanas = [p for p in guion["piezas"] if p["forma"] == "peana" and p["id"] in indice["piezas"]]
    if not peanas: return
    def encima(pe):
        (x0, y0, _), (x1, y1, _) = CP.aabb_pieza(pe)
        return [q for q in guion["piezas"] if q["forma"] not in ("peana", "manguera") and x0 <= q["x"] <= x1 and y0 <= q["y"] <= y1]
    grupos = {pe["id"]: encima(pe) for pe in peanas}
    de_pieza = {q["id"]: pid for pid, qs in grupos.items() for q in qs}; de_pieza.update({pid: pid for pid in grupos})
    num = {}
    if guion.get("ciclo"):
        for e in guion["escenas"]:
            k = e.get("paso")
            if not k or k in num.values(): continue
            for q in list(e.get("resaltar") or []) + [e["camara"].get("objetivo")]:
                pe = de_pieza.get(q)
                if pe and pe not in num: num[pe] = int(k); break
    if not num:
        orden = [q for e in guion["escenas"] for q in e["aparecen"] if q in grupos]
        num = {pe: i + 1 for i, pe in enumerate(dict.fromkeys(orden))}
    todas = [CP.aabb_pieza(q) for q in guion["piezas"] if q["forma"] != "manguera"]
    cx = sum((a[0][0] + a[1][0]) / 2 for a in todas) / len(todas); cy = sum((a[0][1] + a[1][1]) / 2 for a in todas) / len(todas)
    cajas = {pid: [CP.aabb_pieza(q) for q in [next(p for p in peanas if p["id"] == pid)] + qs] for pid, qs in grupos.items()}
    def union(cs): return ([min(c[0][i] for c in cs) for i in range(3)], [max(c[1][i] for c in cs) for i in range(3)])
    tipos = {"turquesa": "grafica", "naranja": "mensaje", "rojo": "estado"}
    for i, pe in enumerate(peanas):
        ob_pe = bpy.data.objects[indice["piezas"][pe["id"]]["objeto"]]
        (x0, y0, _), (x1, y1, _) = CP.aabb_pieza(pe); top = pe["z"] + pe["alto"]
        qs = grupos[pe["id"]]
        if T.TEMA.get("rotulos") and pe["id"] in num:
            y_comp = min([CP.aabb_pieza(q)[0][1] for q in qs] or [y1])
            franja = y_comp - y0; hh = min(0.075, franja * 0.72)
            if hh >= 0.026:
                ob = CYB.rotulo(f"Rotulo {pe['id']}", f"{num[pe['id']]:02d}.", Vector((x0 + 0.035, y0 + (franja - hh) / 2, top + 0.0004)),
                                hh, col_, color="gris_oscuro")
                CYB.hijo(ob, ob_pe)
        if T.TEMA.get("tarjetas") and qs:
            (gx0, gy0, _), (gx1, gy1, gz1) = union(cajas[pe["id"]])
            g = Vector(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 0))
            media = max(abs(Vector((sx, sy, 0)).dot(r)) for sx in (gx0 - g.x, gx1 - g.x) for sy in (gy0 - g.y, gy1 - g.y))
            principal = max(qs, key=lambda q: max(q.get("alto") or 0, q.get("ancho") or 0))
            tipo = tipos.get(principal["color"], ("mensaje", "grafica", "estado")[i % 3])
            w = max(0.15, min(0.22, (gx1 - gx0) * 0.5))
            lado0 = 1.0 if (g - Vector((cx, cy, 0))).dot(r) >= 0 else -1.0
            puesto = None
            for lado in (lado0, -lado0):
                cen = g + r * lado * (media + w * 0.55 + 0.03); cen.z = gz1 * 0.72 + 0.05
                choca = any(o != pe["id"] and c[0][0] - 0.05 < cen.x < c[1][0] + 0.05 and c[0][1] - 0.05 < cen.y < c[1][1] + 0.05
                            for o, cs in cajas.items() for c in [union(cs)])
                if not choca: puesto = cen; break
            if puesto is None: continue
            ob = CYB.tarjeta(f"Tarjeta {pe['id']}", tipo, puesto, vista, w, col_)
            ob["fase"] = i * 1.7
            CYB.hijo(ob, ob_pe)
            h = w * 0.62; geo = indice["piezas"][pe["id"]]["geo"]
            geo["puntos"] += [list(puesto + r * sx * w / 2 + Vector((0, 0, sz * h / 2))) for sx in (-1, 1) for sz in (-1, 1)]

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

def encuadre(params, indice, plano, objetivo, guion, az=None, factor=1.0, objetivos=None, visibles=None, hueco_arriba=0.0, extra=None,
             hueco_izq=0.0, hueco_abajo=0.0):
    """Encuadre ortografico: proyecta los puntos del objetivo (o del grupo 'objetivos') en los ejes de la camara y lo hace caber.
    visibles: piezas que ya estan montadas en la escena; el plano general encuadra solo esas (no la maqueta que aun no existe).
    hueco_arriba: fraccion del alto del cuadro que queda libre arriba (>0) o abajo (<0); hueco_izq: fraccion del ancho libre
    a la izquierda; hueco_abajo: fraccion libre abajo ademas de la de hueco_arriba (subtitulos). El objeto cabe entero en lo
    que queda y se centra en esa parte (paneles, gancho, comparativa, subtitulos)."""
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
    if extra:                        # insignias (datos y pasos) de las piezas del plano: que entren en cuadro
        en_plano = set(grupo) | ({objetivo} if objetivo in indice["piezas"] else set()) if plano != "general" else set(extra)
        pts = pts + [q for pid in en_plano for q in extra.get(pid, [])]
    xs = [q.dot(right) for q in pts]; ys = [q.dot(up) for q in pts]
    W, H = max(xs) - min(xs), max(ys) - min(ys)
    xc, yc = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    if plano == "general": yc -= H * 0.08                       # algo de suelo y de sombra debajo
    # menos margen a los lados en el general: en horizontal por las maquetas anchas; en vertical, porque una maqueta
    # isometrica es mas ancha que alta y con margen 1.75 se quedaba en la mitad del ancho del movil
    mw = min(m, 1.2 if plano == "general" else 1.3) if a >= 1 else (1.3 if plano == "general" else m)
    minimo = 0.45
    if plano != "general":           # sin zooms extremos: un minimo relativo al plano general (contexto de la maqueta)
        minimo = max(minimo, encuadre(params, indice, "general", "objeto", guion, az=az, visibles=visibles)["alto"] * (0.35 if plano == "medio" else 0.25))
    arriba, abajo = max(0.0, hueco_arriba), max(0.0, -hueco_arriba) + max(0.0, hueco_abajo)
    pv, ph = min(0.75, arriba + abajo), min(0.7, max(0.0, hueco_izq))
    # el aire del margen se reparte con los huecos: con panel y subtitulos (vertical) la parte libre es ya un 38 % del alto,
    # y con el margen entero del general la maqueta (y el sobre que viaja por ella) se quedaba diminuta
    if plano == "general" and pv: m = 1 + (m - 1) * (1 - pv)
    alto = max(H * m / (1 - pv), W * mw / (a * (1 - ph)), minimo) * factor
    cen = sum(pts, Vector()) / len(pts)
    c = right * xc + up * yc + fwd * cen.dot(fwd)
    if arriba or abajo: c = c + up * (alto * (arriba - abajo) / 2)   # el centro del objeto baja (o sube) al de la parte libre
    if ph: c = c - right * (alto * a * ph / 2)                    # y se va a la derecha de la columna libre
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
    """Caja en mundo de una pieza: puntos de sus trazos GP, o de su malla/curva (tema con mallas)."""
    pts = []
    M = ob.matrix_world
    if ob.type == 'GREASEPENCIL':
        for L in ob.data.layers:
            for f in L.frames:
                for st in f.drawing.strokes:
                    for p in st.points: pts.append(M @ Vector(p.position))
    elif ob.type == 'MESH':
        pts = [M @ v.co for v in ob.data.vertices]
    else:
        pts = [M @ Vector(c) for c in ob.bound_box]
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

CAIDA_F = 16           # fotogramas de la caida con rebote de una pieza nueva
REVELA_S = 0.6         # segundos que tarda en dibujarse una manguera de neon (temas con mallas), de su origen a su destino
APAGA_F = 5            # fotogramas en que se apaga la chispa de la punta al llegar

def revelado_f(fps): return max(4, round(REVELA_S * fps))

# profundidad de campo (temas con 'dof'): f-stop por plano. La camara es ortografica (Cycles la desenfoca igual).
F_DOF = {"general": 64.0, "medio": 6.0, "detalle": 3.2}
# grano de la textura (temas con 'textura'): su fuerza baja con el zoom. Un encuadre de ALTO_GRANO m o mas lo lleva
# entero; en los planos muy cercanos (0,6 m de alto: los asientos) el grano sale 5 veces mas grande y parecia piedra
ALTO_GRANO = 3.0

def fuerza_grano(alto): return max(0.35, min(1.0, (alto / ALTO_GRANO) ** 0.75))

def tandas(nuevas, f0, f1, fps, indice):
    """Fotograma de entrada de cada pieza nueva de una escena: dos momentos como mucho, no una a una. Hasta 3 piezas
    entran juntas; con mas, se parten en dos tandas por el componente (una peana empieza componente) mas cercano a la mitad,
    y la segunda entra hacia el 40 % de la escena."""
    n = len(nuevas); t1 = min(f1 - 16, f0 + 6)
    if n <= 3: return [t1] * n
    t2 = max(t1 + 12, min(f1 - 16, f0 + max(int(1.5 * fps), int(0.4 * (f1 - f0)))))
    forma = [indice["piezas"].get(q, {}).get("forma") for q in nuevas]
    cortes = ([i for i in range(1, n) if forma[i] == "peana"] or
              [i for i in range(1, n) if forma[i] == "manguera" and forma[i - 1] != "manguera"] or [(n + 1) // 2])
    c = min(cortes, key=lambda i: abs(i - n / 2))
    return [t1 if i < c else t2 for i in range(n)]

def paneles_del_proyecto(dirp, params, guion):
    """(ids de escenas con panel, pieza de cada panel) si los datos van en los paneles de Motion Canvas (parametro
    paneles_mc y etapa 'paneles' hecha); (None, {}) si siguen en 3D."""
    proy = GB.leer_json(os.path.join(dirp, "proyecto.json"))
    if not CP.usa_paneles(proy, params): return None, {}
    ruta = os.path.join(dirp, "paneles.json")
    piezas = {p["escena"]: p["pieza"] for p in (GB.leer_json(ruta).get("paneles") or [] if os.path.exists(ruta) else []) if p.get("pieza")}
    return set(CP.escenas_con_panel(guion, params)), piezas

def hueco_subtitulos(dirp, params):
    """Fraccion del alto que la camara deja libre abajo para los subtitulos de Motion Canvas (0 sin la etapa hecha)."""
    proy = GB.leer_json(os.path.join(dirp, "proyecto.json"))
    return CP.zona_subtitulos(params)["hueco"] if CP.usa_subtitulos(proy, params) else 0.0

def etapa_animacion(dirp, params, guion, tiempos):
    sc = bpy.context.scene; indice = json.loads(sc["comic_indice"])
    con_panel, pieza_panel = paneles_del_proyecto(dirp, params, guion)
    hueco_sub = hueco_subtitulos(dirp, params)
    for esc in guion["escenas"]:     # el componente del que habla el panel se resalta, si la escena no resalta ya otro
        pz = pieza_panel.get(esc["id"])
        if pz and pz in indice["piezas"] and not esc.get("resaltar"): esc["resaltar"] = [pz]
    GB.configurar_escena(params, sc)
    if indice.get("mallas"): CYB.render(sc, params)              # EEVEE, fondo casi negro y bloom del tema
    else:
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
        nuevas = [p for p in esc["aparecen"] if aparece.get(p) == k and p in listadas]
        for pid, f in zip(nuevas, tandas(nuevas, f0, f1, fps, indice)): caida[pid] = f
    # fichas que se guardan dentro de un contenedor transparente (la cola SQS): no caen, llegan en movimiento por la
    # manguera que lo alimenta (la que termina en el contenedor: los caminos van del origen al destino), como los sobres
    def _caja(g): return ([min(v[i] for v in g["puntos"]) for i in range(3)], [max(v[i] for v in g["puntos"]) for i in range(3)])
    def _dentro(c, caja, m=0.0): return all(caja[0][i] - m <= c[i] <= caja[1][i] + m for i in range(3))
    llegada = {}
    contenedores = {q: _caja(v["geo"]) for q, v in indice["piezas"].items()
                    if v["material"] in ("transparente", "liquido") and v["forma"] not in ("manguera",)}
    tramos = {q: [Vector(x) for x in v["geo"]["tramo"]] for q, v in indice["piezas"].items() if v["forma"] == "manguera" and v["geo"].get("tramo")}
    def _cerca(c, caja, m):           # junto al componente (las mangueras acaban en el canto de su peana), hasta su altura
        return all(caja[0][i] - m <= c[i] <= caja[1][i] + m for i in range(2)) and c[2] <= caja[1][2] + 0.02
    for qc, caja in contenedores.items():
        entran = [tr for tr in tramos.values() if _cerca(tr[-1], caja, 0.35) and not _cerca(tr[0], caja, 0.35)]
        fichas = [pid for pid in caida if pid != qc and _dentro(indice["piezas"][pid]["geo"]["centro"], caja)
                  and indice["piezas"][pid]["geo"]["radio"] < indice["piezas"][qc]["geo"]["radio"]]
        # boca: el extremo del eje largo del contenedor mas cercano al final de la manguera (entran por ella, no por la pared)
        eje = max(range(3), key=lambda i: caja[1][i] - caja[0][i]); cen = Vector([(caja[0][i] + caja[1][i]) / 2 for i in range(3)])
        bocas = [cen.copy(), cen.copy()]; bocas[0][eje] = caja[0][eje]; bocas[1][eje] = caja[1][eje]
        for i, pid in enumerate(fichas if entran else []):
            tr = entran[i % len(entran)]; boca = min(bocas, key=lambda b: (b - tr[-1]).length)
            llegada[pid] = tr + [boca, Vector(indice["piezas"][pid]["geo"]["centro"])]
    def visible(pid, f, k):
        if pid in caida and aparece[pid] == k: return f >= caida[pid]
        return aparece[pid] <= k < desaparece[pid]
    eventos = sorted({1} | {te["inicio"] for te in tiempos["escenas"]} | set(caida.values()))
    # mangueras de neon de los temas con mallas: no caen, se dibujan de su origen a su destino con una chispa en la punta
    L_rev = revelado_f(fps)
    revela = {pid for pid, v in indice["piezas"].items() if indice.get("mallas") and v["forma"] == "manguera"
              and bpy.data.objects[v["objeto"]].type == 'CURVE'}
    col_neon = bpy.data.collections.get("Adornos y neon") or sc.collection
    if revela: bpy.context.view_layer.update()       # matrix_world de las curvas (el guardado puede no estar evaluado)
    def revelar(pid, ob, orx, fa):
        """bevel_factor_end 0 -> 1 por la longitud del camino (mapeo SPLINE) en L_rev fotogramas, con la chispa en la punta:
        la misma fraccion de longitud sobre el poligono de la curva. Al llegar, la chispa se encoge y se apaga."""
        for o in (ob, orx):
            if o is None: continue
            o.data.bevel_factor_mapping_end = 'SPLINE'
            for f in range(fa, fa + L_rev + 1): put(o.data, "bevel_factor_end", 0, f, suave((f - fa) / L_rev), "LINEAR")
        for ch in ob.children_recursive:
            if ch.type == 'CURVE':                       # banda de la cinta (arcilla): crece con el canal
                ch.data.bevel_factor_mapping_end = 'SPLINE'
                for f in range(fa, fa + L_rev + 1): put(ch.data, "bevel_factor_end", 0, f, suave((f - fa) / L_rev), "LINEAR")
            elif ch.type != 'ARMATURE':                  # nodos del cristal, patas de la cinta: salen cuando ha llegado
                for prop in ("hide_render", "hide_viewport"): put(ch, prop, 0, fa, 1.0); put(ch, prop, 0, fa + L_rev, 0.0)
        M = ob.matrix_world
        pts = [M @ Vector(p.co[:3]) for p in ob.data.splines[0].points]
        acu = [0.0]
        for a_, b_ in zip(pts, pts[1:]): acu.append(acu[-1] + (b_ - a_).length)
        def en(u):
            dist = u * acu[-1]
            for i in range(len(pts) - 1):
                if dist <= acu[i + 1] or i == len(pts) - 2:
                    return pts[i].lerp(pts[i + 1], min(1.0, max(0.0, (dist - acu[i]) / max(1e-6, acu[i + 1] - acu[i]))))
        if CYB.arcilla(): bs, emi = CYB.chispa(f"Chispa {pid}", 0.022, col_neon, color="turquesa", fuerza=12.0)
        else: bs, emi = CYB.chispa(f"Chispa {pid}", max(0.012, ob.data.bevel_depth * 1.8), col_neon)
        fin = fa + L_rev
        for prop in ("hide_render", "hide_viewport"):
            put(bs, prop, 0, 1, 1.0); put(bs, prop, 0, fa, 0.0); put(bs, prop, 0, fin + APAGA_F + 1, 1.0)
        for f in range(fa, fin + 1):
            q = en(suave((f - fa) / L_rev))
            for i in range(3): put(bs, "location", i, f, q[i], "LINEAR")
        for i in range(3): put(bs, "scale", i, fin, 1.0, "BEZIER"); put(bs, "scale", i, fin + APAGA_F, 0.0, "BEZIER")
        fuerza = emi.inputs["Strength"].default_value
        put(emi.id_data, f'nodes["{emi.name}"].inputs[1].default_value', 0, fin, fuerza, "BEZIER")
        put(emi.id_data, f'nodes["{emi.name}"].inputs[1].default_value', 0, fin + APAGA_F, 0.0, "BEZIER")
    hueso_rest = {pid: rig.data.bones[pid].matrix_local.to_3x3() for pid in indice["piezas"]}
    acum = {}            # desplazamiento acumulado de cada pieza (subir/bajar/desplazar se suman; 'volver' lo deshace)
    def a_local(pid, v): return hueso_rest[pid].inverted() @ Vector(v)
    for k, (esc, te) in enumerate(zip(guion["escenas"], tiempos["escenas"])):
        f0, f1 = te["inicio"], te["fin"]; n = max(1, f1 - f0)
        rx = set(esc["rayos_x"])
        # resalte: cada pieza lo enciende al entrar (su tanda), pero TODAS lo apagan a la vez, con un fin comun por escena
        def entra(pid): return caida[pid] if (pid in caida and aparece[pid] == k) else f0
        resaltadas = [pid for pid in indice["piezas"] if pid in esc["resaltar"] or (pid in caida and aparece[pid] == k)]
        fin_r = min(f1 - 1, max(entra(q) for q in resaltadas) + max(int(1.6 * fps), int(0.55 * n))) if resaltadas else f1 - 1
        sale_r = max(min(entra(q) for q in resaltadas) + 2, fin_r - max(2, int(0.35 * fps))) if resaltadas else fin_r
        for pid, v in indice["piezas"].items():
            ob = bpy.data.objects[v["objeto"]]; orx = bpy.data.objects[v["rx"]] if v["rx"] else None
            usa_rx = orx is not None and pid in rx
            for f in sorted({f0} | ({caida[pid]} if pid in caida and aparece[pid] == k else set())):
                vis = visible(pid, f, k)
                put(ob, "hide_render", 0, f, 0.0 if (vis and not usa_rx) else 1.0); put(ob, "hide_viewport", 0, f, 0.0 if (vis and not usa_rx) else 1.0)
                for ch in ob.children_recursive:        # temas con mallas: adornos, aros de neon y surcos son hijos de la pieza
                    if ch.type != 'ARMATURE':
                        put(ch, "hide_render", 0, f, 0.0 if (vis and not usa_rx) else 1.0); put(ch, "hide_viewport", 0, f, 0.0 if (vis and not usa_rx) else 1.0)
                if orx: put(orx, "hide_render", 0, f, 0.0 if (vis and usa_rx) else 1.0); put(orx, "hide_viewport", 0, f, 0.0 if (vis and usa_rx) else 1.0)
            # Resalte lima: entra y sale con opacidad, no como un corte seco.
            # La capa se mantiene oculta fuera de la transicion para que no
            # interfiera con las piezas que no estan en foco.
            resalta = pid in esc["resaltar"] or (pid in caida and aparece[pid] == k)
            a0 = caida.get(pid, f0) if (pid in caida and aparece[pid] == k) else f0
            if v.get("resalte") or v.get("resalte_prop"):
                # temas con mallas: la propiedad 'resalte' del objeto (0-1) entra y sale con fundido. En cyberpunk
                # ademas se enciende el casco (modificador) solo mientras dura, siempre con opacidad 0 al conmutar.
                ruta_p = '["resalte"]'; ruta_m = f'modifiers["{v["resalte"]}"]' if v.get("resalte") else None
                put(ob, ruta_p, 0, f0, 0.0)
                if ruta_m:
                    for prop in ("show_render", "show_viewport"): put(ob, f"{ruta_m}.{prop}", 0, f0, 0.0)
                if resalta:
                    fin = fin_r; entrada = max(2, min(int(0.35 * fps), (sale_r - a0) // 2 if sale_r > a0 + 3 else 2))
                    put(ob, ruta_p, 0, a0, 0.0, "BEZIER"); put(ob, ruta_p, 0, min(sale_r, a0 + entrada), 1.0, "BEZIER")
                    put(ob, ruta_p, 0, max(a0 + entrada, sale_r), 1.0, "BEZIER"); put(ob, ruta_p, 0, fin, 0.0, "BEZIER")
                    if ruta_m:
                        for prop in ("show_render", "show_viewport"):
                            put(ob, f"{ruta_m}.{prop}", 0, a0, 1.0); put(ob, f"{ruta_m}.{prop}", 0, fin + 1, 0.0)
            for o in (ob, orx) if not (v.get("resalte") or v.get("resalte_prop")) else ():
                if o is None: continue
                put(o.data, 'layers["resalte"].hide', 0, f0, 1.0)
                put(o.data, 'layers["resalte"].opacity', 0, f0, 0.0)
                if resalta:
                    fin = fin_r; fundido = max(2, min(int(0.25 * fps), (sale_r - a0) // 2 if sale_r > a0 + 3 else 2))
                    salida = max(a0 + fundido, sale_r)
                    put(o.data, 'layers["resalte"].hide', 0, a0, 0.0)
                    put(o.data, 'layers["resalte"].opacity', 0, a0, 0.0, "BEZIER")
                    put(o.data, 'layers["resalte"].opacity', 0, min(fin, a0 + fundido), 1.0, "BEZIER")
                    put(o.data, 'layers["resalte"].opacity', 0, salida, 1.0, "BEZIER")
                    put(o.data, 'layers["resalte"].opacity', 0, fin, 0.0, "BEZIER")
                    put(o.data, 'layers["resalte"].hide', 0, fin, 1.0)
            if pid in caida and aparece[pid] == k and pid in llegada:      # llega por la manguera, sin caer
                ruta = llegada[pid]; fin_ = ruta[-1]; acu = [0.0]
                for a_, b_ in zip(ruta, ruta[1:]): acu.append(acu[-1] + (b_ - a_).length)
                Lr = max(0.05, acu[-1]); fa = caida[pid]; Lf = int(max(1.0, min(2.5, Lr / 0.9)) * fps)
                def en(dist):
                    for i in range(len(ruta) - 1):
                        if dist <= acu[i + 1] or i == len(ruta) - 2:
                            return ruta[i].lerp(ruta[i + 1], min(1.0, max(0.0, (dist - acu[i]) / max(1e-6, acu[i + 1] - acu[i]))))
                for f in list(range(fa, fa + Lf, paso)) + [fa + Lf]:
                    loc = a_local(pid, en(Lr * suave(min(1.0, (f - fa) / Lf))) - fin_)
                    for i in range(3): put(rig, f'pose.bones["{pid}"].location', i, f, loc[i])
            elif pid in caida and aparece[pid] == k and pid in revela:    # manguera de neon: se dibuja, no cae
                revelar(pid, ob, orx, caida[pid])
            # caida con rebote
            elif pid in caida and aparece[pid] == k:
                fa = caida[pid]; L = CAIDA_F
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
        c = esc["camara"]; az0 = 35; hueco_i = 0.0
        if con_panel is not None:          # paneles de Motion Canvas: franja arriba (vertical) o columna izquierda (horizontal)
            tam = float(params.get("tam_panel", 0.40)) if esc["id"] in con_panel else 0.0
            vertical = params.get("orientacion") == "vertical"
            hueco, hueco_i = (tam, 0.0) if vertical else (0.0, tam * 0.95)
            ins = None
        else:
            hueco = 0.21 if (k == 0 and guion.get("gancho") and params.get("gancho", "dolor") != "ninguno") else 0.0
            comp = guion.get("comparativa")
            if comp and params.get("comparativa", True) and comp.get("escena") == esc["id"]: hueco = -0.22   # la grafica, abajo
            ins = T.puntos_workflow(indice, guion, T.dir_camara(params), k)
        vis = [pid for pid in indice["piezas"] if aparece[pid] <= k < desaparece[pid]]     # lo que ya esta montado
        # escenas con flujo: la manguera por la que viajan los sobres entra entera en el plano (con sus dos extremos)
        objs = c.get("objetivos")
        flujos = [ef["pieza"] for ef in esc["efectos"] if ef["tipo"] in ("flujo", "flujo_vuelta")
                  and indice["piezas"].get(ef["pieza"], {}).get("forma") == "manguera"]
        if flujos and c["plano"] != "general":
            objs = list(dict.fromkeys([q for q in (objs or [c["objetivo"]]) if q in indice["piezas"]] + flujos))
        fa_ = {"acercar": 1.22, "alejar": 1.0}.get(c["movimiento"], 1.0); fb_ = {"acercar": 1.0, "alejar": 1.25}.get(c["movimiento"], 1.0)
        if c["plano"] == "general" and c["movimiento"] == "alejar": fa_, fb_ = 0.82, 1.0       # alejarse hasta el general, no mas alla
        aza, azb = (az0 - 14, az0 + 14) if c["movimiento"] == "rodear" and params.get("formato") != "2d" else (az0, az0)
        orb = float(T.TEMA.get("orbita") or 0)         # arcilla: los generales fijos giran despacio (+-orb grados)
        gira = c["movimiento"] == "rodear" or (orb and c["plano"] == "general" and c["movimiento"] == "fijo")
        if gira and c["movimiento"] != "rodear" and params.get("formato") != "2d": aza, azb = az0 - orb, az0 + orb
        if T.TEMA.get("dof"):                          # profundidad de campo: enfoca el objetivo; en el general, todo nitido
            cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt
            put(cam.data, "dof.aperture_fstop", 0, f0, F_DOF.get(c["plano"], F_DOF["general"]))
        for f, fac, az, it in ((f0, fa_, aza, "BEZIER"), (f1 - 1, fb_, azb, "CONSTANT")):
            e = encuadre(params, indice, c["plano"], c["objetivo"], guion, az=az, factor=fac, objetivos=objs, visibles=vis, hueco_arriba=hueco, extra=ins, hueco_izq=hueco_i, hueco_abajo=hueco_sub)
            if f == f0 and T.TEMA.get("textura"): put(sc, '["grano"]', 0, f0, fuerza_grano(e["alto"]))
            for i in range(3): put(cam, "location", i, f, e["cam"][i], it); put(tgt, "location", i, f, e["obj"][i], it)
            put(cam.data, "ortho_scale", 0, f, e["ortho"], it)
        if gira and params.get("formato") != "2d":
            for j in range(1, 4):
                f = f0 + int(n * j / 4); e = encuadre(params, indice, c["plano"], c["objetivo"], guion, az=aza + (azb - aza) * j / 4, objetivos=objs, visibles=vis, hueco_arriba=hueco, extra=ins, hueco_izq=hueco_i, hueco_abajo=hueco_sub)
                for i in range(3): put(cam, "location", i, f, e["cam"][i], "BEZIER")
        alto = encuadre(params, indice, c["plano"], c["objetivo"], guion, objetivos=objs, visibles=vis)["alto"]
        g = max(0.35, min(1.5, (alto / 2.6) ** 0.6))
        for o in bpy.data.objects:
            if o.type == 'GREASEPENCIL':
                m = o.modifiers.get("Grosor por plano") or o.modifiers.new("Grosor por plano", 'GREASE_PENCIL_THICKNESS')
                put(o, 'modifiers["Grosor por plano"].thickness_factor', 0, f0, g)
    # sombra: un dibujo por cada cambio de lo visible
    sombra = bpy.data.objects.get("Sombra")          # el tema con mallas no tiene sombra GP
    L = sombra.data.layers["sombra"] if sombra else None
    for fr in (list(L.frames) if L else []): L.frames.remove(fr.frame_number)
    for f in (eventos if sombra else []):
        k = max(i for i, te in enumerate(tiempos["escenas"]) if te["inicio"] <= f)
        geos = [v["geo"] for pid, v in indice["piezas"].items() if v["material"] in ("solido", "metal") and visible(pid, f, k)]
        T.sombra_piezas(T.Pincel(sombra, "sombra", frame=f), geos, params, pared_y=indice["pared_y"])
    n = 0
    for (id_, ruta, idx), d in claves.items():
        ks = sorted((f, v, i) for f, (v, i) in d.items())
        if all(i == "CONSTANT" for _, _, i in ks): ks = [(f, v, "CONSTANT") for f, v in GB.simplificar([(f, v) for f, v, _ in ks])]
        GB.curva(id_, ruta, idx, ks); n += len(ks)
    for o in bpy.data.objects:            # tarjetas flotantes (arcilla): suben y bajan despacio, cada una a su ritmo
        if o.get("comic_tarjeta"):
            fc = GB.curva(o, "location", 2, [(1, o.location.z, "LINEAR")])
            md = fc.modifiers.new('FNGENERATOR'); md.function_type = 'SIN'; md.use_additive = True
            md.amplitude = 0.012; md.phase_multiplier = 2 * math.pi / (2.8 * fps); md.phase_offset = float(o.get("fase", 0.0))
    sc.frame_set(1)
    return dict(claves=n, fotogramas=sc.frame_end, cambios_de_sombra=len(eventos), piezas=len(indice["piezas"]))

# ================================================================ workflow visible
def _numero(s):
    """'+16.800 €' -> ('+', 16800.0, ' €', 0 decimales). None si no hay numero."""
    m = re.search(r"\d[\d.]*(?:,\d+)?", s or "")
    if not m: return None
    txt = m.group(); dec = len(txt.split(",")[1]) if "," in txt else 0
    return s[:m.start()], float(txt.replace(".", "").replace(",", ".")), s[m.end():], dec

def _formato(pre, v, suf, dec):
    t = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{pre}{t}{suf}"

def contador(valor, hasta, pasos):
    """Valores intermedios de un contador, con frenada al final (ease-out), en el formato del valor final."""
    a, b = _numero(valor), _numero(hasta)
    if not a or not b: return [valor, hasta]
    pre, v0, _, _ = a; pre_b, v1, suf, dec = b
    out = []
    for i in range(pasos + 1):
        u = 1 - (1 - i / pasos) ** 3; v = v0 + (v1 - v0) * u
        txt = _formato(pre_b or pre, round(v, dec) if dec else round(v), suf, dec)
        if not out or out[-1] != txt: out.append(txt)
    out[-1] = hasta
    return out

def workflow_visible(params, guion, tiempos, indice, vista, mallas, col_fichas, objeto, off, visible_desde, avisos):
    """Datos vivos (paneles con numeros del caso junto a los componentes, con contadores) y pasos del ciclo (insignias
    numeradas que se encienden). En temas con mallas, un objeto por estado con claves de visibilidad; en GP, un objeto
    con un dibujo por cambio."""
    fps = params["fps"]; dere, arr = T.ejes_vista(vista); n_obj = 0
    escenas = list(zip(guion["escenas"], tiempos["escenas"]))
    def pl_local(c0, x, y, k=0): return c0 + dere * x + arr * y + vista * (0.003 * k)
    def capa(nombre, cen, tramos, dibujar, pop=True):
        """tramos: [(f_ini, f_fin, clave)] sin solapes; dibujar(clave, pin, pl) dibuja el estado 'clave'."""
        nonlocal n_obj
        tramos = sorted(t for t in tramos if t[1] >= t[0])
        if not tramos: return
        f_a, f_z = tramos[0][0], tramos[-1][1]
        if mallas:
            for clave in dict.fromkeys(t[2] for t in tramos):
                pin = CYB.PincelMalla(f"{nombre} {clave}", vista); dibujar(clave, pin, pl_local)
                ob = pin.objeto(col_fichas)
                if ob is None: continue
                ob.location = cen; ob.lineart.usage = 'OCCLUSION_ONLY'; n_obj += 1
                vis = [(0, 1.0)]
                for fi, ff, k in tramos:
                    if k != clave: continue
                    if vis[-1][0] == fi: vis.pop()                 # contiguo al anterior: sigue visible
                    else: vis.append((fi, 0.0))
                    vis.append((ff + 1, 1.0))
                GB.curva(ob, "hide_render", 0, vis); GB.curva(ob, "hide_viewport", 0, vis)
                if pop:                                             # entra con un pequeno salto y sale encogiendose
                    ks = [(f_a, 0.05, "BEZIER"), (f_a + 5, 1.0, "BEZIER"), (max(f_a + 6, f_z - 4), 1.0, "BEZIER"), (f_z, 0.05, "BEZIER")]
                    for i in range(3): GB.curva(ob, "scale", i, ks)
        else:
            ob = objeto(nombre); T.Pincel(ob, "fx", frame=0)
            def pl_gp(c0, x, y, k=0): return cen + c0 + dere * x + arr * y - off
            for j, (fi, ff, clave) in enumerate(tramos):
                dibujar(clave, T.Pincel(ob, "fx", frame=fi), pl_gp)
                if j + 1 == len(tramos) or tramos[j + 1][0] != ff + 1: T.Pincel(ob, "fx", frame=ff + 1)
    def entra(pid, f):          # la insignia no aparece antes que su pieza (ni mientras cae)
        v = visible_desde(indice["piezas"][pid]["objeto"], f)
        return None if v is None else (v + 18 if v > f else v)
    # ---- datos vivos: un panel por (pieza, etiqueta), seguido mientras se repite en escenas consecutivas
    if params.get("datos_vivos", True):
        series = {}
        for k, (esc, te) in enumerate(escenas):
            mios = {}
            for d in esc.get("datos") or []: mios.setdefault(d["pieza"], []).append(d)
            for pid, ds in mios.items():
                for i, d in enumerate(ds): series.setdefault((pid, d["etiqueta"]), []).append((k, te, d, i, len(ds)))
        for (pid, etq), lista in series.items():
            grupos = [[lista[0]]]
            for item in lista[1:]:
                (grupos[-1].append(item) if item[0] == grupos[-1][-1][0] + 1 else grupos.append([item]))
            for g_ in grupos:
                valores = [v for _, _, d, _, _ in g_ for v in (d["valor"], d.get("hasta")) if v]
                w, h = T.medida_dato(etq, valores)
                k0, te0, d0, i0, n0 = g_[0]
                cen = T.sitio_dato(indice, pid, vista, w, h, i0, n0)
                fa = entra(pid, te0["inicio"] + 4)
                if fa is None or fa >= g_[-1][1]["fin"] - 6:
                    avisos.append(f"dato {etq} en {pid}: la pieza no se ve"); continue
                tramos = []
                for k, te, d, _, _ in g_:
                    f0, f1 = max(fa, te["inicio"]), te["fin"] - 1
                    if d.get("hasta"):
                        n = max(1, f1 - f0); ini = f0 + int(0.15 * n); dur = max(12, min(int(2.5 * fps), int(0.6 * n)))
                        vals = contador(d["valor"], d["hasta"], max(2, min(24, dur // 3)))
                        tramos.append((f0, ini - 1, d["valor"]))
                        paso = dur / max(1, len(vals) - 1)
                        for j, v in enumerate(vals[1:], 1):
                            a_ = ini + int((j - 1) * paso); b_ = (ini + int(j * paso) - 1) if j < len(vals) - 1 else f1
                            tramos.append((a_, b_, v))
                    else:
                        tramos.append((f0, f1, d["valor"]))
                tramos = [t for t in tramos if t[1] >= t[0]]
                color = d0["color"]
                capa(f"Dato {pid} {etq}", cen, tramos, lambda v, pin, pl, etq=etq, w=w, h=h, color=color: T.dibujar_dato(pin, pl, etq, v, color, w, h))
    # ---- pasos del ciclo: insignias numeradas (apagado, activo, hecho)
    ciclo = guion.get("ciclo") or []
    if params.get("pasos_ciclo", True) and ciclo:
        ini_ciclo = next((te["inicio"] for esc, te in escenas if esc.get("paso") or esc.get("ciclo_rapido")), None)
        if ini_ciclo is not None:
            fin_video = tiempos["escenas"][-1]["fin"] - 1
            activos = {i: [] for i in range(1, len(ciclo) + 1)}
            for esc, te in escenas:
                if esc.get("ciclo_rapido"):                 # el bucle se repite cada vez mas rapido
                    f = te["inicio"] + int(0.1 * (te["fin"] - te["inicio"])); d = 0.5 * fps; fin = te["fin"] - int(0.1 * (te["fin"] - te["inicio"]))
                    while f < fin:
                        for i in range(1, len(ciclo) + 1):
                            dd = max(3, int(d)); activos[i].append((f, min(fin, f + dd) - 1)); f += dd
                            if f >= fin: break
                        d *= 0.72
                elif esc.get("paso"):
                    activos[esc["paso"]].append((te["inicio"], te["fin"] - 1))
            for i, paso in enumerate(ciclo, 1):
                fa = entra(paso["pieza"], ini_ciclo)
                if fa is None: continue
                cortes = sorted(set([fa, fin_video + 1] + [x for a, b in activos[i] if b >= fa for x in (max(a, fa), b + 1)]))
                primero = min((a for a, b in activos[i] if b >= fa), default=None)
                tramos = []
                for a, b in zip(cortes, cortes[1:]):
                    if any(x <= a and a <= y for x, y in activos[i]): est = "activo"
                    elif primero is not None and a > primero: est = "hecho"
                    else: est = "apagado"
                    if tramos and tramos[-1][2] == est and tramos[-1][1] == a - 1: tramos[-1] = (tramos[-1][0], b - 1, est)
                    else: tramos.append((a, b - 1, est))
                cen = T.sitio_paso(indice, paso["pieza"], vista)
                capa(f"Paso {i}", cen, tramos, lambda est, pin, pl, i=i, txt=paso["texto"]: T.dibujar_paso(pin, pl, i, txt, est))
    return n_obj

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
    sin_gp = bool(T.TEMA.get("sin_gp"))
    if sin_gp: off = vista * 0.02     # mallas casi en su sitio: lejos de la pieza las desenfocaria la profundidad de campo
    def hervir_malla(nombre, fa, fb, dibujar):
        """Tema sin Grease Pencil: cada dibujo del efecto es una malla (PincelMalla) visible hasta el dibujo siguiente."""
        nonlocal n_fx
        n_fx += 1; fr = list(range(fa, fb, 2))
        for k, f in enumerate(fr):
            pin = CYB.PincelMalla(f"FX_{n_fx:03d}_{nombre}_{k:03d}", vista)
            dibujar(pin, k, (f - fa) / max(1, fb - fa), (f - fa) / fps)
            ob = pin.objeto(col_)
            if ob is None: continue
            ob.location = off; ob.visible_shadow = False       # iconos que flotan: sin sombra en la maqueta
            vis = [(0, 1.0), (f, 0.0), (fr[k + 1] if k + 1 < len(fr) else fb, 1.0)]
            GB.curva(ob, "hide_render", 0, vis); GB.curva(ob, "hide_viewport", 0, vis)
        return None
    def hervir(nombre, fa, fb, dibujar):
        if sin_gp: return hervir_malla(nombre, fa, fb, dibujar)
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
    def pl_gp(cen, x, y, k=0): return plano(cen, x, y)
    def pl_malla(cen, x, y, k=0): return cen + dere * x + arr * y + vista * (0.003 * k)     # capas sin z-fighting
    def sobre(p, cen, w, mat_, pl=pl_gp):
        h = w * 0.66; esq = [pl(cen, x * w / 2, y * h / 2, 0) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        p.cara(esq, mat_); esq1 = [pl(cen, x * w / 2, y * h / 2, 1) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        p.linea(esq1 + esq1[:1], "T tinta", T.R_TINTA * 0.8)
        p.linea([pl(cen, -w / 2, h / 2, 1), pl(cen, 0, -h * 0.08, 1), pl(cen, w / 2, h / 2, 1)], "T tinta", T.R_TINTA * 0.7)
    COLORES_ALERTA = ("rojo", "amarillo", "lima", "naranja", "cian", "rosa")
    def biohazard(p, cen, w, color, pl=pl_gp): T.dibujar_biohazard(p, pl, cen, w, color)
    # temas con mallas: las fichas del flujo son mallas animadas (el GP se pinta encima de las piezas aunque pase por
    # detras). Van en la coleccion que lee Line Art, solo como oclusoras: tapan los contornos de lo que queda detras.
    mallas = bool(T.TEMA.get("mallas")); col_fichas = None; mallas_ficha = {}
    if mallas:
        lin = next((o for o in bpy.data.objects if o.type == 'GREASEPENCIL' and o.modifiers.get("Line Art")), None)
        col_fichas = GB.coleccion("Fichas del flujo", lin.modifiers["Line Art"].source_collection if lin else bpy.data.collections.get("Tecnico"))
    def malla_ficha(clave, dibujar):
        if clave[0] == "cubo":                 # arcilla: cubo redondeado que brilla, encima de la cinta
            return CYB.ficha_cubo(clave[2], clave[1])
        if clave not in mallas_ficha:
            pin = CYB.PincelMalla("Ficha " + " ".join(map(str, clave)), vista); dibujar(pin)
            ob = pin.objeto(col_fichas); mallas_ficha[clave] = ob.data; bpy.data.objects.remove(ob)
        return mallas_ficha[clave]
    def fichas_malla(nombre, punto, L, vel, dt, ultimo, fa, fb, empuje, dibujo):
        """Una malla por ficha: visible solo mientras viaja, con la posicion por la ruta en cada fotograma."""
        nonlocal n_fx
        n_fx += 1; j = 0
        while j * dt <= ultimo + 1e-6:
            f_ini = fa + int(math.ceil(j * dt * fps)); f_fin = min(fb, fa + int((j * dt + L / vel) * fps))
            if f_ini < f_fin:
                clave, dib = dibujo(j)
                ob = bpy.data.objects.new(f"FX_{n_fx:03d}_{nombre}_{j:02d}", malla_ficha(clave, dib)); col_fichas.objects.link(ob)
                ob.lineart.usage = 'OCCLUSION_ONLY'
                locs = [(f, punto(min(L, max(0.0, ((f - fa) / fps - j * dt) * vel))) + empuje) for f in range(f_ini, f_fin + 1)]
                for i in range(3): GB.curva(ob, "location", i, [(f, v[i], "LINEAR") for f, v in locs])
                vis = [(0, 1.0), (f_ini, 0.0), (f_fin + 1, 1.0)]
                GB.curva(ob, "hide_render", 0, vis); GB.curva(ob, "hide_viewport", 0, vis)
            j += 1
    def visible_desde(nombre, f):
        """Primer fotograma >= f en que el objeto se ve (claves de hide_render de la animacion); None si no llega a verse."""
        ob = bpy.data.objects.get(nombre)
        if ob is None: return None
        ad = ob.animation_data; fc = None
        if ad and ad.action:
            for cb in [GB.channelbag(ob)]:
                fc = cb.fcurves.find("hide_render")
        if fc is None: return None if ob.hide_render else f
        for g_ in range(int(f), int(f) + 20000):
            if fc.evaluate(g_) < 0.5: return g_
            if g_ > sc.frame_end: return None
        return None
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
                    # nada viaja por una manguera que aun no esta: si aparece dentro de la escena, el flujo espera
                    # (ni por una que esta cayendo o dibujandose: el flujo empieza cuando ya se ha posado o ha llegado)
                    margen = max(CAIDA_F, revelado_f(fps)) + int(0.2 * fps)
                    v0 = visible_desde(indice["piezas"][pid]["objeto"], max(f0, fa - margen)) if g.get("tramo") else fa
                    if v0 is None or v0 >= f1 - 6:
                        avisos.append(f"flujo por {pid}: la manguera no esta visible en la escena {esc['id']}"); continue
                    if v0 > fa - margen: fa = min(f1 - 6, max(fa, v0 + margen)); fb = min(f1, fa + max(6, largo))
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
                    bio = t == "flujo" and params.get("icono_flujo") == "biohazard"
                    def d(p, k, u, s, ruta=ruta, punto=punto, L=L, vel=vel, dt=dt, ultimo=ultimo, ancho=ancho, mat_=mat_, bio=bio, n0=n_fx):
                        j = 0
                        while j * dt <= ultimo + 1e-6:
                            dist = (s - j * dt) * vel
                            if 0 <= dist <= L:
                                if bio: biohazard(p, punto(dist), ancho, COLORES_ALERTA[(j + n0) % len(COLORES_ALERTA)])
                                else: sobre(p, punto(dist), ancho, mat_)
                            j += 1
                    if mallas and CYB.arcilla() and g.get("tramo"):
                        # cinta transportadora: las fichas son cubos que brillan y viajan ENCIMA de la banda
                        ci = T.TEMA.get("cinta") or dict(alto=0.03); lado = 0.042
                        emp = Vector((0, 0, -ci["alto"] / 2 + 0.017 + lado / 2 + 0.001))
                        col_f = "turquesa" if t == "flujo_vuelta" else "naranja"
                        fichas_malla(t, punto, L, vel, dt, ultimo, fa, fb, emp, lambda j, col_f=col_f: (("cubo", col_f, lado), None))
                    elif mallas:
                        # delante de la manguera (su tubo de neon no la corta por la mitad)
                        emp = vista * (g.get("grosor", 0.0) + 0.012) if g.get("tramo") else Vector()
                        def dibujo(j, bio=bio, ancho=ancho, mat_=mat_, n0=n_fx + 1):
                            if bio:
                                col = COLORES_ALERTA[(j + n0) % len(COLORES_ALERTA)]
                                return ("bio", col, round(ancho, 3)), (lambda pin: biohazard(pin, Vector(), ancho, col, pl=pl_malla))
                            return ("sobre", mat_, round(ancho, 3)), (lambda pin: sobre(pin, Vector(), ancho, mat_, pl=pl_malla))
                        fichas_malla(t, punto, L, vel, dt, ultimo, fa, fb, emp, dibujo)
                    else:
                        hervir(t, fa, fb, d)
                elif t in ("aprobado", "rechazo"):
                    # Los carteles ya ocupan la vertical de los componentes.
                    # Elevamos y desplazamos los iconos de estado para que se
                    # lean como una llamada independiente, no como otra capa
                    # atravesando el objeto o su etiqueta.
                    tam = max(0.12, min(0.3, r * 0.5)); cen0 = Vector((c.x, c.y, z1 + tam + 0.14)) - dere * tam * 0.7
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
                    tam = max(0.12, min(0.28, r * 0.5)); cen0 = Vector((c.x, c.y, z1 + tam + 0.14)) - dere * tam * 0.7
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
                    tam = max(0.14, min(0.3, r * 0.55)); cen0 = Vector((c.x, c.y, z1 + tam + 0.14)) - dere * tam * 0.7
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
    if paneles_del_proyecto(dirp, params, guion)[0] is None:     # con paneles de Motion Canvas los datos van arriba, no en 3D
        n_fx += workflow_visible(params, guion, tiempos, indice, vista, mallas, col_fichas, objeto, off, visible_desde, avisos)
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
