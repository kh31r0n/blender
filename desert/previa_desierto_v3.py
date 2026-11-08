# Previsualizacion y comprobaciones del desierto LEGO v3 (objeto "Desierto_LEGO" con el modificador "Desierto LEGO").
# Uso: blender -b Desierto_LEGO_GN_v3.blend -P previa_desierto_v3.py -- [opciones]
#   --preset p.json        aplica un preset (claves de desierto_parametros.py) a las entradas del modificador
#   --previa ruta.png      render EEVEE desde Cámara_Previa (perspectiva hacia el primer arco)
#   --general ruta.png     render EEVEE desde Cámara_General (perspectiva de todo el terreno)
#   --res 1600x900  --muestras 32
#   --guardar nuevo.blend  guarda una copia con el preset aplicado (nunca sobrescribe un archivo existente)
#   --comprobar            comprobaciones numericas y tiempos de evaluacion
# Tambien se importa desde crear_desierto_lego_gn_v3.py (colocar_camaras).
import bpy, sys, os, json, time, math
import numpy as np
from mathutils import Vector

DESERT = os.path.expanduser("~/blender/desert")
sys.path.insert(0, DESERT)
import desierto_parametros as DP

NPROTO = 16
NOMBRES = ["cima 1x1", "cima 1x2", "cima 2x2", "cima 2x4", "lateral 1x1", "lateral 1x2", "cuña", "cuña esquina",
           "arco placa", "arco placa sin stud", "arco ladrillo", "arco ladrillo sin stud",
           "roca suelta S", "roca suelta M", "roca suelta L", "tapa"]

# ---------- entradas del modificador ----------
def modificador(ob):
    mod = ob.modifiers["Desierto LEGO"]
    ids = {it.name: it.identifier for it in mod.node_group.interface.items_tree
           if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    return mod, ids

def leer(ob, nombre):
    mod, ids = modificador(ob)
    return getattr(mod.properties.inputs, ids[nombre]).value

def poner(ob, nombre, valor):
    mod, ids = modificador(ob)
    getattr(mod.properties.inputs, ids[nombre]).value = valor

def aplicar_preset(ob, preset):
    pres, avisos = DP.limitar(preset)
    pal = DP.paleta()
    for k, v in pres.items():
        socket, tipo = DP.POR_CLAVE[k][1], DP.POR_CLAVE[k][2]
        poner(ob, socket, tuple(pal[v]) if tipo == "COLOR" else v)
    ob.update_tag()
    return pres, avisos

def medidas(ob):
    dx, dy = leer(ob, "Dimensión X"), leer(ob, "Dimensión Y")
    cx, cy = dx / leer(ob, "Resolución X"), dy / leer(ob, "Resolución Y")
    placa = 0.4 * min(cx, cy)
    return dict(dx=dx, dy=dy, cx=cx, cy=cy, cmin=min(cx, cy), placa=placa, esc=placa * leer(ob, "Altura de escalón (placas)"))

# ---------- geometria evaluada ----------
def datos(ob):
    """Posiciones (n, 3), prototipo (n), roca (n) y arco (n) de las instancias evaluadas. El indice de referencia no
    sirve para identificar la pieza (Instance on Points compacta las referencias sin usar): se leen los atributos."""
    dg = bpy.context.evaluated_depsgraph_get()
    gs = ob.evaluated_get(dg).evaluated_geometry()
    pc = gs.instances_pointcloud()
    if pc is None or len(pc.points) == 0:
        return np.zeros((0, 3)), np.zeros(0, int), np.zeros(0, int), np.zeros(0)
    n = len(pc.points)
    M = np.empty(n * 16, np.float32); pc.attributes["instance_transform"].data.foreach_get("value", M)
    M = M.reshape(n, 4, 4)
    # la traslacion va en la ultima fila o en la ultima columna segun el orden de foreach_get
    T = M[:, 3, :3] if np.abs(M[:, 3, :3]).sum() > np.abs(M[:, :3, 3]).sum() else M[:, :3, 3]
    def leer_attr(nombre):
        v = np.zeros(n, np.float32)
        if nombre in pc.attributes: pc.attributes[nombre].data.foreach_get("value", v)
        return v
    proto = np.round(leer_attr("proto")).astype(int); roca = np.round(leer_attr("roca")).astype(int)
    global EXTRA
    EXTRA = {k: leer_attr(k) for k in ("nivel", "tam", "giro")}
    pc_ = np.empty(n * 3, np.float32)
    if "pcelda" in pc.attributes: pc.attributes["pcelda"].data.foreach_get("vector", pc_)
    EXTRA["pcelda"] = pc_.reshape(n, 3)
    return T.astype(np.float64), proto, roca, leer_attr("arco")

EXTRA = {}

def mapa_niveles(proto, md):
    """Nivel de cada celda a partir de las piezas de cima: ancla (pcelda), tamaño de la fusion y giro."""
    nx, ny = int(round(md["dx"] / md["cx"])), int(round(md["dy"] / md["cy"]))
    mapa = np.full((nx, ny), np.nan)
    tam = {0: (1, 1), 1: (2, 1), 2: (2, 2), 3: (4, 2)}
    for i in np.where(proto <= 7)[0]:
        if proto[i] in (4, 5): continue
        a, b = tam[int(round(EXTRA["tam"][i]))] if proto[i] <= 3 else (1, 1)
        if abs(math.sin(EXTRA["giro"][i])) > 0.5 and proto[i] <= 3: a, b = b, a
        ci = int(round((EXTRA["pcelda"][i, 0] + md["dx"] / 2) / md["cx"] - 0.5))
        cj = int(round((EXTRA["pcelda"][i, 1] + md["dy"] / 2) / md["cy"] - 0.5))
        mapa[max(ci, 0):ci + a, max(cj, 0):cj + b] = EXTRA["nivel"][i]
    return mapa

def altura_en(T, xy, radio, esc):
    """Cota maxima de las piezas (cima incluida) en un circulo del plano."""
    d = np.hypot(T[:, 0] - xy[0], T[:, 1] - xy[1])
    sel = d < radio
    return float((T[sel, 2] + esc).max()) if sel.any() else 0.0

# ---------- camaras ----------
def mirar(cam, objetivo):
    cam.rotation_euler = (Vector(objetivo) - cam.location).to_track_quat('-Z', 'Y').to_euler()

def colocar_camaras(sc, ob):
    T, proto, roca, arco = datos(ob)
    md = medidas(ob)
    dx, dy, esc = md["dx"], md["dy"], md["esc"]
    gen = sc.objects["Cámara_General"]
    gen.data.lens = 30
    gen.location = (-0.58 * dx, -0.86 * dy, 0.42 * max(dx, dy))
    mirar(gen, (0.03 * dx, 0.02 * dy, 0.0))
    pre = sc.objects["Cámara_Previa"]
    ids = sorted(set(int(a) for a in arco if a > 0))
    if not ids:   # sin arcos: vista baja hacia el centro
        pre.location = (-0.25 * dx, -0.35 * dy, 0.0)
        pre.location.z = altura_en(T, pre.location[:2], 6 * md["cmin"], esc) + 0.08 * max(dx, dy)
        mirar(pre, (0.0, 0.0, 0.0))
        return None
    V = T[arco == ids[0]]
    mn, mx = V.min(0), V.max(0); ext = mx - mn; c = (mn + mx) / 2
    eje = 0 if ext[0] >= ext[1] else 1                  # eje de la luz
    W, H = ext[eje], ext[2]
    objetivo = Vector((c[0], c[1], mn[2] + 0.42 * H))
    d = max(1.9 * H, 1.25 * W)
    mejor = None
    for lado in (1.0, -1.0):                            # el lado con el primer plano mas bajo, girado 30 grados
        perp = np.array([0.0, 0.0]); perp[1 - eje] = lado
        ang = math.radians(30.0)
        dirv = np.array([perp[0] * math.cos(ang) - perp[1] * math.sin(ang), perp[0] * math.sin(ang) + perp[1] * math.cos(ang)])
        xy = np.array(c[:2]) + dirv * d
        xy = np.clip(xy, [-0.48 * dx, -0.48 * dy], [0.48 * dx, 0.48 * dy])
        tramo = [altura_en(T[arco == 0], np.array(c[:2]) + dirv * d * f, 0.12 * d, esc) for f in (0.35, 0.6, 0.85)]
        coste = max(tramo)
        if mejor is None or coste < mejor[0]: mejor = (coste, xy)
    xy = mejor[1]
    suelo = altura_en(T, xy, 0.1 * d, esc)
    z = max(objetivo.z + 0.12 * d, suelo + 0.3 * H)
    pre.location = (float(xy[0]), float(xy[1]), float(z))
    mirar(pre, objetivo)
    return dict(arco=ids[0], centro=c.tolist(), luz=float(W), alto=float(H), distancia=float(d))

# ---------- render ----------
def render(sc, camara, ruta, res=(1600, 900), muestras=32):
    sc.camera = sc.objects[camara]
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = muestras
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = os.path.abspath(ruta)      # una ruta relativa se tomaria respecto al .blend ("//")
    bpy.ops.render.render(write_still=True)
    print("RENDER", ruta)

# ---------- comprobaciones ----------
def evaluar(ob):
    ob.update_tag()
    t0 = time.perf_counter()
    T, proto, roca, arco = datos(ob)
    return time.perf_counter() - t0, T, proto, roca, arco

def comprobar_arcos(T, proto, arco, md):
    res = []
    mapa = mapa_niveles(proto, md) if EXTRA else None
    placa, c = md["placa"], md["cmin"]
    for a in sorted(set(int(x) for x in arco if x > 0)):
        sel = arco == a
        V, R = T[sel], proto[sel]
        mn, mx = V.min(0), V.max(0); ext = mx - mn; cen = (mn + mx) / 2
        eje = 0 if ext[0] >= ext[1] else 1
        u = V[:, eje] - cen[eje]; z = V[:, 2] - mn[2]; H = ext[2]
        hueco = int(((np.abs(u) < 0.2 * ext[eje]) & (z > 0.25 * H) & (z < 0.55 * H)).sum())
        # tamaño del voxel en celdas (m > 1 con resoluciones altas o arcos muy grandes)
        paso_eje = md["cx"] if eje == 0 else md["cy"]
        dif = np.diff(np.unique(np.round(V[:, eje] / paso_eje, 2)))
        m = max(1, int(round(dif[dif > 0.5].min()))) if (dif > 0.5).any() else 1
        # celdas (celda x celda x placa) ocupadas: cada voxel cubre m x m celdas y m placas (3m si es ladrillo)
        celdas, fondo = set(), {}
        for p, r in zip(V, R):
            ci0 = int(round((p[0] + md["dx"] / 2) / md["cx"] - m / 2)); cj0 = int(round((p[1] + md["dy"] / 2) / md["cy"] - m / 2))
            k0 = int(round(p[2] / placa))
            for di in range(m):
                for dj in range(m):
                    fondo[(ci0 + di, cj0 + dj)] = min(fondo.get((ci0 + di, cj0 + dj), 1e9), p[2])
                    for kk in range(3 * m if r in (10, 11) else m): celdas.add((ci0 + di, cj0 + dj, k0 + kk))
        # conectividad (26 vecinos) de pata a pata
        inicio = min(celdas, key=lambda q: q[eje]); fin = max(celdas, key=lambda q: q[eje])
        vistos, pila = {inicio}, [inicio]
        while pila:
            q = pila.pop()
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for dk in (-1, 0, 1):
                        w = (q[0] + di, q[1] + dj, q[2] + dk)
                        if w in celdas and w not in vistos: vistos.add(w); pila.append(w)
        # patas apoyadas: en el contorno de la mitad exterior de cada pata (las columnas interiores no tienen piezas
        # a ras de suelo: solo se instancia la superficie) la pieza mas baja debe tocar el terreno
        flotan = 0; columnas = 0
        if mapa is not None:
            for (ci, cj), zb in fondo.items():
                x = (ci + 0.5) * md["cx"] - md["dx"] / 2 if eje == 0 else (cj + 0.5) * md["cy"] - md["dy"] / 2
                if abs(x - cen[eje]) < 0.4 * ext[eje]: continue          # zona del vano: el arco va por encima
                if all((ci + di, cj + dj) in fondo for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))): continue
                if not (0 <= ci < mapa.shape[0] and 0 <= cj < mapa.shape[1]) or np.isnan(mapa[ci, cj]): continue
                columnas += 1
                if zb > mapa[ci, cj] * md["esc"] + 1e-3: flotan += 1
        res.append(dict(arco=a, voxeles=int(sel.sum()), voxel_celdas=m, luz=round(float(ext[eje]), 1), alto=round(float(H), 1),
                        voxeles_en_abertura=hueco, conectado=fin in vistos, columnas_de_pata=columnas, columnas_flotando=flotan))
    return res

def comprobar(sc, ob):
    md = medidas(ob)
    t, T, proto, roca, arco = evaluar(ob)
    print(f"\n== Comprobaciones ({len(proto)} instancias, evaluación {t:.2f} s) ==")
    for p in range(NPROTO):
        a, r = int(((proto == p) & (roca == 0)).sum()), int(((proto == p) & (roca == 1)).sum())
        if a or r: print(f"  {p:2d} {NOMBRES[p]:24s} arena {a:7d}  roca {r:7d}")
    ok = True
    def informe(nombre, cond, detalle=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'OK' if cond else 'FALLO'}] {nombre} {detalle}")
    esc, c = md["esc"], md["cmin"]
    lim = np.abs(T[:, :2]) <= np.array([md["dx"] / 2 + c, md["dy"] / 2 + c])
    informe("todas las piezas dentro de Dimensión X/Y", lim.all())
    tops = proto <= 3
    q = T[tops, 2] / esc
    informe("cimas en niveles cuantizados", np.abs(q - np.round(q)).max() < 1e-3 if tops.any() else True,
            f"(niveles {int(np.round(q).min())}..{int(np.round(q).max())})" if tops.any() else "")
    informe("hay pendientes (cuñas)", ((proto == 6) | (proto == 7)).sum() > 0, f"({int(((proto == 6) | (proto == 7)).sum())})")
    informe("hay roca", (roca == 1).sum() > 0)
    sueltas = np.where((proto >= 12) & (proto <= 14))[0]
    superficie = T[proto <= 7]
    flot = 0
    for i in sueltas:
        d = np.hypot(superficie[:, 0] - T[i, 0], superficie[:, 1] - T[i, 1])
        cerca = superficie[d < 2.3 * c]
        if not len(cerca) or np.abs(cerca[:, 2] + esc - T[i, 2]).min() > 1e-3: flot += 1
    if leer(ob, "Densidad de rocas sueltas") > 0: informe("hay rocas sueltas", len(sueltas) > 0, f"({len(sueltas)})")
    informe("ninguna roca suelta flota", flot == 0, f"({len(sueltas)} rocas sueltas, {flot} sin apoyo)")
    arcos = comprobar_arcos(T, proto, arco, md)
    informe("al menos un arco", len(arcos) > 0, f"({len(arcos)})")
    for a in arcos:
        informe(f"arco {a['arco']}: abertura libre y banda continua", a["voxeles_en_abertura"] == 0 and a["conectado"], str(a))
        informe(f"arco {a['arco']}: patas apoyadas en el terreno", a["columnas_flotando"] == 0,
                f"({a['columnas_flotando']} de {a['columnas_de_pata']} columnas de pata sin apoyo)")
    return ok, dict(instancias=int(len(proto)), evaluacion_s=round(t, 3), arcos=arcos)

VARIANTES = [
    ("por defecto", {}),
    ("semilla 123", {"semilla": 123}),
    ("resolución 100x100", {"resolucion_x": 100, "resolucion_y": 100}),
    ("resolución 500x500", {"resolucion_x": 500, "resolucion_y": 500}),
    ("dimensiones 500x800", {"dimension_x": 500, "dimension_y": 800}),
    ("sin arcos", {"max_arcos": 0}),
    ("tres arcos grandes", {"densidad_arcos": 5.0, "max_arcos": 3, "luz_arco": 170.0, "altura_arco": 120.0}),
    ("sin rocas", {"densidad_rocas": 0.0, "densidad_sueltas": 0.0}),
    ("muchas rocas", {"densidad_rocas": 0.5}),
    ("barjanes", {"tipo_duna": "Barjanes"}),
    ("estrella", {"tipo_duna": "Estrella"}),
    ("escalón de placa", {"escalon_placas": 1}),
    ("sin erosión ni pendientes", {"iteraciones_erosion": 0, "pendientes": False}),
    ("sin studs", {"mostrar_studs": False}),
    ("submuestreo 2 (visor)", {"submuestreo_visor": 2}),
    ("1024x1024", {"resolucion_x": 1024, "resolucion_y": 1024}),
    ("máximo 2048x2048 (8000x8000 u)", {"resolucion_x": 2048, "resolucion_y": 2048, "dimension_x": 8000, "dimension_y": 8000, "max_arcos": 12}),
]

def tiempos(ob):
    base = DP.por_defecto()
    print("\n== Tiempos de evaluación ==")
    filas = []
    for nombre, cambios in VARIANTES:
        aplicar_preset(ob, dict(base, **cambios))
        t, T, proto, roca, arco = evaluar(ob)
        narc = len(set(int(a) for a in arco if a > 0))
        print(f"  {nombre:28s} {t:6.2f} s  {len(proto):8d} instancias  {narc} arcos")
        filas.append(dict(variante=nombre, segundos=round(t, 3), instancias=int(len(proto)), arcos=narc))
    aplicar_preset(ob, base)
    return filas

# ---------- linea de comandos ----------
def argumentos():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    op = {"res": "1600x900", "muestras": "32"}
    i = 0
    while i < len(a):
        if a[i] == "--comprobar": op["comprobar"] = True; i += 1
        else: op[a[i].lstrip("-")] = a[i + 1]; i += 2
    return op

if __name__ == "__main__":
    op = argumentos()
    sc = bpy.context.scene; ob = bpy.data.objects["Desierto_LEGO"]
    informe = {}
    if "preset" in op:
        pres, avisos = aplicar_preset(ob, json.load(open(op["preset"])))
        informe["preset"] = pres; informe["avisos"] = avisos
        for av in avisos: print("AVISO", av)
    informe["camara"] = colocar_camaras(sc, ob)
    if op.get("comprobar"):
        ok, r = comprobar(sc, ob); informe["comprobaciones"] = r; informe["comprobaciones_ok"] = ok
        informe["tiempos"] = tiempos(ob)
        colocar_camaras(sc, ob)
    res = tuple(int(v) for v in op["res"].split("x"))
    if "previa" in op: render(sc, "Cámara_Previa", op["previa"], res, int(op["muestras"]))
    if "general" in op: render(sc, "Cámara_General", op["general"], res, int(op["muestras"]))
    if "guardar" in op:
        ruta = os.path.abspath(op["guardar"])
        if os.path.exists(ruta): print("NO SE GUARDA: ya existe", ruta)
        else: bpy.ops.wm.save_as_mainfile(filepath=ruta, copy=True); print("GUARDADO", ruta)
    if "informe" in op: json.dump(informe, open(op["informe"], "w"), indent=2, ensure_ascii=False)
    print("INFORME", json.dumps(informe, ensure_ascii=False)[:2000])
