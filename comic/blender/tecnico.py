# Estilo TECNICO: dibujo de piezas con Grease Pencil en 3D para explicativos de objetos.
# Inspirado en la referencia (referencias/yt_88DXBq8baS4): vista isometrica alta, papel con baldosas, paleta
# apagada, sombreado en bandas por orientacion de cara, tinta fina, sombra proyectada plana azul cobalto y
# rayos X (carcasas y liquidos translucidos).
#
# Cada pieza es un objeto GP con capas "relleno" (caras), "detalle", "tinta" y "resalte" (contorno lima, oculto).
# Las piezas opacas usan profundidad 3D. Las translucidas (cristal, liquidos y la version de rayos X "<id>_rx")
# usan orden 2D y su origen se adelanta hacia la camara: asi se dibujan despues y dejan ver lo de dentro.
import math, json, os, random
import bpy
from mathutils import Vector, Matrix, Euler
import gp_base as GB
from gp_base import Lapiz
import comic_parametros as CP
import iconos_3d as ICO

# direccion hacia la luz que sombrea las caras (no fisica: arriba claro, frente medio, lateral oscuro)
LUZ_CARAS = Vector((0.35, -0.75, 0.85)).normalized()
# direccion en la que viaja la luz de la sombra proyectada (cae hacia delante-izquierda, como en la referencia)
LUZ_SOMBRA = Vector((-0.55, -0.5, -1.0)).normalized()
BANDAS = (1.07, 0.94, 0.81, 0.69)
R_TINTA_BASE = 0.0085
R_TINTA = R_TINTA_BASE
TEMA = dict(CP.TEMAS_TECNICOS["clasico"], nombre="clasico")
CLAROS = ("blanco", "blanco_hueso", "gris_claro", "papel", "azul_claro", "baldosa", "pared")

def aplicar_tema(params):
    """Tema del estilo tecnico (comic_parametros.TEMAS_TECNICOS): colores por nombre, grosor de tinta, lateral, entorno.
    Llamar antes de crear materiales (al principio de cada etapa)."""
    global R_TINTA
    nombre = (params or {}).get("tema") or "clasico"
    t = CP.TEMAS_TECNICOS.get(nombre, CP.TEMAS_TECNICOS["clasico"])
    TEMA.clear(); TEMA.update(t); TEMA["nombre"] = nombre
    CP.PALETA_TECNICA.update(t["paleta"]); CP.PALETA.update(t["paleta"])
    R_TINTA = R_TINTA_BASE * t["tinta"]
    return TEMA
EMPUJE = 3.0                      # adelanto del origen de los objetos translucidos hacia la camara

def dir_camara(params, az=None):
    """Direccion del objeto a la camara: isometrica alta en 3d, frontal en 2d."""
    if params.get("formato") == "2d": return Vector((0, -1, 0.0001)).normalized()
    a = math.radians(35 if az is None else az); e = math.radians(32)
    return Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))).normalized()

# ---------------------------------------------------------------- materiales del estilo
def colt(nombre, valor=1.0, alfa=1.0, sat=1.0):
    return CP.color_lineal(CP.PALETA_TECNICA.get(nombre, CP.PALETA_TECNICA["metal"]), alfa, valor, sat)

def mat(nombre):
    """'T <color> b<k>' banda k | 'T <color> rx' rayos X | 'T <color> liq' liquido | 'T <color> sup' superficie |
    'T tinta' | 'T tinta fina' | 'T resalte' | 'T sombra' | 'T trazo <color>' | 'T plano <color>'."""
    m = bpy.data.materials.get(nombre)
    if m and m.grease_pencil: return m
    m = bpy.data.materials.new(nombre); bpy.data.materials.create_gpencil_data(m); g = m.grease_pencil
    p = nombre.split(" ")
    g.show_stroke, g.show_fill = False, True
    if nombre == "T tinta": g.show_stroke, g.show_fill = True, False; g.color = colt("negro")
    elif nombre == "T tinta fina": g.show_stroke, g.show_fill = True, False; g.color = colt("gris_oscuro", alfa=0.9)
    elif nombre == "T resalte": g.show_stroke, g.show_fill = True, False; g.color = colt("lima")
    elif nombre == "T sombra": g.fill_color = colt("azul_sombra")
    elif p[1] == "trazo": g.show_stroke, g.show_fill = True, False; g.color = colt(p[2], alfa=float(p[3]) if len(p) > 3 else 1.0)
    elif p[1] == "plano": g.fill_color = colt(p[2], alfa=float(p[3]) if len(p) > 3 else 1.0)
    elif p[2] == "rx": g.fill_color = colt(p[1], valor=1.08, alfa=0.22)
    elif p[2] == "liq": g.fill_color = colt(p[1], alfa=0.42)
    elif p[2] == "sup": g.fill_color = colt(p[1], valor=1.18, alfa=0.55, sat=0.8)
    elif p[2].startswith("b"):
        g.fill_color = color_banda(p[1], int(p[2][1]))
        if p[2].endswith("s"): g.show_stroke = True; g.color = g.fill_color     # borde del mismo color: tapa juntas
    return m

def color_banda(c, b):
    """Color de una cara segun su banda de luz. Con 'lateral' (tema iconos) solo hay dos tonos: luz y lateral."""
    lat = TEMA.get("lateral")
    if not lat: return colt(c, valor=BANDAS[b])
    if b <= 1: return colt(c)
    if c == lat: return colt(lat, valor=0.88 if b == 2 else 0.84)
    if c in CLAROS: return colt(lat, valor=1.0 if b == 2 else 0.97)
    return colt(c, valor=0.86 if b == 2 else 0.8)

def banda(normal):
    d = normal.normalized().dot(LUZ_CARAS)
    return 0 if d > 0.72 else 1 if d > 0.38 else 2 if d > 0.0 else 3

class Pincel:
    """Lapiz con materiales del estilo tecnico."""
    def __init__(self, ob, capa, frame=0):
        self.lp = Lapiz(ob, capa, frame=frame); self.ob = ob
    def _m(self, nombre):
        mats = self.ob.data.materials
        for i, m in enumerate(mats):
            if m and m.name == nombre: return nombre
        mats.append(mat(nombre)); return nombre
    def cara(self, pts, nombre, radio=0.0004):
        self._m(nombre); return self.lp.trazo(pts, nombre, radio=radio, cerrado=True, relleno=True)
    def linea(self, pts, nombre="T tinta", radio=None, cerrado=False, afilar=False):
        self._m(nombre); return self.lp.trazo(pts, nombre, radio=R_TINTA if radio is None else radio, cerrado=cerrado, afilar=afilar)

# ---------------------------------------------------------------- geometria de las formas (coordenadas locales)
def anillo_pts(r, z, n, a0=0.0):
    return [Vector((r * math.cos(a0 + 2 * math.pi * i / n), r * math.sin(a0 + 2 * math.pi * i / n), z)) for i in range(n)]

def perfil_redondeado(p, n=4):
    """Planta de una caja con las esquinas verticales redondeadas (tema con bisel), en sentido antihorario; None si es recta."""
    if p["forma"] == "peana": a, b = p["ancho"] / 2, p["fondo"] / 2; r = min(0.08, 0.5 * min(a, b))
    elif not TEMA.get("bisel") or p["forma"] != "caja": return None
    else: a, b = p["ancho"] / 2, p["fondo"] / 2; r = min(0.06, 0.36 * min(a, b))
    if r < 0.006: return None
    pts = []
    for cx, cy, a0 in ((a - r, -b + r, -90), (a - r, b - r, 0), (-a + r, b - r, 90), (-a + r, -b + r, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts

def caras_forma(p):
    """Lista de (puntos, normal, tipo) y de aristas [(puntos, cerrado)] en coordenadas locales (base en z=0)."""
    f = p["forma"]; caras, aristas = [], []
    perfil = perfil_redondeado(p)
    if perfil:
        h = p["alto"]; m = len(perfil)
        abajo = [Vector((x, y, 0)) for x, y in perfil]; arriba = [Vector((x, y, h)) for x, y in perfil]
        for i in range(m):
            j = (i + 1) % m; d = arriba[j] - arriba[i]
            if d.length < 1e-9: continue
            caras.append(([abajo[i], abajo[j], arriba[j], arriba[i]], Vector((d.y, -d.x, 0)).normalized(), "lado"))
        caras.append((arriba, Vector((0, 0, 1)), "lado")); caras.append((abajo[::-1], Vector((0, 0, -1)), "lado"))
        aristas += [(arriba, True), (abajo, True)]
        return caras, aristas
    if f in ("caja", "panel"):
        if f == "panel": a, b, h = p["ancho"] / 2, p["grosor"] / 2, p["alto"]
        else: a, b, h = p["ancho"] / 2, p["fondo"] / 2, p["alto"]
        v = [Vector(c) for c in [(-a, -b, 0), (a, -b, 0), (a, b, 0), (-a, b, 0), (-a, -b, h), (a, -b, h), (a, b, h), (-a, b, h)]]
        for idx, n in (((0, 1, 5, 4), (0, -1, 0)), ((1, 2, 6, 5), (1, 0, 0)), ((2, 3, 7, 6), (0, 1, 0)), ((3, 0, 4, 7), (-1, 0, 0)),
                       ((4, 5, 6, 7), (0, 0, 1)), ((3, 2, 1, 0), (0, 0, -1))):
            caras.append(([v[i] for i in idx], Vector(n), "lado"))
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            aristas.append(([v[i], v[j]], False))
        return caras, aristas
    n = 40
    if f in ("cilindro", "disco", "varilla", "tubo", "cono"):
        r1 = p["radio"]; r2 = p.get("radio2", r1) if f == "cono" else r1; h = p["alto"]
        abajo, arriba = anillo_pts(r1, 0, n), anillo_pts(r2, h, n)
        for i in range(n):
            j = (i + 1) % n; mid = (abajo[i] + abajo[j]) / 2
            nor = Vector((mid.x, mid.y, (r1 - r2) / max(h, 1e-6) * mid.xy.length)).normalized()
            caras.append(([abajo[i], abajo[j], arriba[j], arriba[i]], nor, "lado"))
        if f == "tubo":
            t = p.get("grosor", 0.03); ri = max(0.005, r1 - t)
            dentro_ab, dentro_ar = anillo_pts(ri, max(0.02, t), n), anillo_pts(ri, h, n)
            for i in range(n):
                j = (i + 1) % n; mid = (dentro_ar[i] + dentro_ar[j]) / 2
                caras.append(([dentro_ab[i], dentro_ab[j], dentro_ar[j], dentro_ar[i]], Vector((-mid.x, -mid.y, 0)).normalized(), "dentro"))
                caras.append(([arriba[i], arriba[j], dentro_ar[j], dentro_ar[i]], Vector((0, 0, 1)), "borde"))
            caras.append((dentro_ab, Vector((0, 0, 1)), "fondo"))
            aristas += [(arriba, True), (dentro_ar, True), (abajo, True)]
        else:
            caras.append((arriba, Vector((0, 0, 1)), "tapa"))
            aristas += [(arriba, True), (abajo, True)]
        return caras, aristas
    if f == "esfera":
        r = p["radio"]; nl, na = (18, 40) if TEMA.get("lateral") else (10, 24)     # dos tonos: el borde de la sombra se ve escalonado
        for a in range(nl):
            t0, t1 = math.pi * a / nl - math.pi / 2, math.pi * (a + 1) / nl - math.pi / 2
            for b in range(na):
                p0, p1 = 2 * math.pi * b / na, 2 * math.pi * (b + 1) / na
                q = [Vector((r * math.cos(t) * math.cos(ph), r * math.cos(t) * math.sin(ph), r + r * math.sin(t))) for t, ph in ((t0, p0), (t0, p1), (t1, p1), (t1, p0))]
                c = sum(q, Vector()) / 4
                caras.append((q, (c - Vector((0, 0, r))).normalized(), "lado"))
        return caras, aristas
    if f == "anillo":
        R, t = p["radio"], p["grosor"]; nu, nv = 36, 10
        for u in range(nu):
            for v in range(nv):
                pts = []
                for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    a, b = 2 * math.pi * (u + du) / nu, 2 * math.pi * (v + dv) / nv
                    pts.append(Vector(((R + t * math.cos(b)) * math.cos(a), (R + t * math.cos(b)) * math.sin(a), t + t * math.sin(b))))
                a, b = 2 * math.pi * (u + 0.5) / nu, 2 * math.pi * (v + 0.5) / nv
                caras.append((pts, Vector((math.cos(b) * math.cos(a), math.cos(b) * math.sin(a), math.sin(b))), "lado"))
        return caras, aristas
    return caras, aristas

def suave3(pts, n=8):
    """Catmull-Rom abierta por puntos 3D (mangueras)."""
    if len(pts) < 3: return pts
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(0, i - 1)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(len(pts) - 1, i + 2)]
        for j in range(n):
            t = j / n; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out

def encadenar(segs):
    """Une segmentos (a, b) que comparten vertice en polilineas (menos trazos y linea continua)."""
    from collections import defaultdict
    ady = defaultdict(list)
    for i, (a, b) in enumerate(segs): ady[a].append((b, i)); ady[b].append((a, i))
    usado = [False] * len(segs); out = []
    for ini in sorted(ady, key=lambda v: len(ady[v]) == 2):
        for nb, i in ady[ini]:
            if usado[i]: continue
            cad = [ini, nb]; usado[i] = True; cur = nb
            while len(ady[cur]) == 2:
                sig = [(n2, j) for n2, j in ady[cur] if not usado[j]]
                if not sig: break
                n2, j = sig[0]; usado[j] = True; cad.append(n2); cur = n2
            out.append(cad)
    return out

def normal_poligono(pts):
    n = Vector()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))

def dibujar_malla(p, rel, tin, res, vista, trans, rx, off):
    """Pieza de un modelo descargado: caras en bandas, tinta en aristas vivas y siluetas (vistas desde la camara)."""
    m = p["_malla"]; V = [Vector(v) - off for v in m["vertices"]]; c = p["color"]
    normales = [normal_poligono([V[i] for i in f]) for f in m["caras"]]
    frente = [n.dot(vista) > 0 for n in normales]
    orden = sorted(range(len(m["caras"])), key=lambda k: sum(V[i].dot(vista) for i in m["caras"][k]) / len(m["caras"][k]))
    for k in orden:
        f = m["caras"][k]
        if len(f) < 3: continue
        pts = [V[i] for i in f]
        if p["material"] == "liquido" and not rx: rel.cara(pts, f"T {c} liq"); continue
        if trans: rel.cara(pts, f"T {c} rx"); continue
        if normales[k].dot(vista) < -0.2: continue              # oculta por la propia pieza
        nombre = f"T {c} b{banda(normales[k])}s"; rel._m(nombre)
        rel.lp.trazo(pts, nombre, radio=0.0018, cerrado=True, relleno=True)     # el borde del mismo color tapa las juntas
    vivas, silu = [], []
    for a, b, f1, f2, viva in m["aristas"]:
        if f2 < 0 or f1 < 0: vivas.append((a, b)); silu.append((a, b)); continue
        if frente[f1] != frente[f2]: silu.append((a, b))
        elif viva and (trans or frente[f1]): vivas.append((a, b))
    fino = "T tinta fina" if trans else "T tinta"
    for cad in encadenar(list({tuple(sorted(e)) for e in vivas + silu})):
        tin.linea([V[i] for i in cad], fino, R_TINTA * (0.7 if trans else 0.85))
    for cad in encadenar(list({tuple(sorted(e)) for e in silu})):
        res.linea([V[i] for i in cad], "T resalte", R_TINTA * 2.1)

def matriz_pieza(p):
    return Matrix.Translation((p["x"], p["y"], p["z"])) @ Euler((math.radians(p["rot_x"]), math.radians(p["rot_y"]), math.radians(p["rot_z"]))).to_matrix().to_4x4()

def siluetas(p, M, vista):
    """Lineas de contorno de cilindros, conos y esferas vistas desde la camara (en mundo)."""
    f = p["forma"]; out = []
    if f in ("cilindro", "disco", "varilla", "tubo", "cono"):
        eje = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
        v = vista - eje * vista.dot(eje)
        if v.length < 1e-4: return out
        v.normalize(); lado = eje.cross(v).normalized()
        r1 = p["radio"]; r2 = p.get("radio2", r1) if f == "cono" else r1
        base = M.translation; h = p["alto"]
        for s in (-1, 1):
            out.append([base + lado * r1 * s * 1.004, base + eje * h + lado * r2 * s * 1.004])
    elif f == "esfera":
        r = p["radio"]; c = M @ Vector((0, 0, r))
        u = vista.cross(Vector((0, 0, 1))); u = u.normalized() if u.length > 1e-4 else Vector((1, 0, 0))
        w = vista.cross(u).normalized()
        out.append([c + (u * math.cos(2 * math.pi * i / 48) + w * math.sin(2 * math.pi * i / 48)) * r * 1.004 for i in range(49)])
    elif f == "anillo":
        R, t = p["radio"], p["grosor"]
        for rr in (R + t, R - t):
            out.append([M @ Vector((rr * math.cos(2 * math.pi * i / 48), rr * math.sin(2 * math.pi * i / 48), t)) for i in range(49)])
    return out

def helice(p, M):
    r, h, n = p["radio"], p["alto"], int(p.get("vueltas", 8)); pts = []
    for i in range(n * 24 + 1):
        a = 2 * math.pi * i / 24; pts.append(M @ Vector((r * math.cos(a), r * math.sin(a), h * i / (n * 24))))
    return pts

def detalles(p, M, pin, vista):
    """Agujeros (perforado), costillas (nervado), rayas (rayado) o rejilla sobre la superficie."""
    d = p.get("detalle", "liso"); f = p["forma"]
    if d == "liso" or f not in ("cilindro", "tubo", "cono", "caja", "disco"): return
    if f in ("cilindro", "tubo", "cono"):
        r1 = p["radio"]; r2 = p.get("radio2", r1) if f == "cono" else r1; h = p["alto"]
        def sup(a, zf, sep=1.006):
            r = (r1 + (r2 - r1) * zf) * sep
            return M @ Vector((r * math.cos(a), r * math.sin(a), h * zf))
        if d == "perforado":
            filas, cols = max(3, int(h / 0.07)), max(12, int(2 * math.pi * max(r1, r2) / 0.07))
            for k in range(1, filas):
                for c in range(cols):
                    a = 2 * math.pi * (c + 0.5 * (k % 2)) / cols; zf = k / filas
                    nrm = (M.to_3x3() @ Vector((math.cos(a), math.sin(a), 0))).normalized()
                    if nrm.dot(vista) < 0.05: continue           # solo la mitad que mira a camara
                    cen = sup(a, zf); t = nrm.cross(Vector((0, 0, 1))).normalized(); rr = 0.011
                    pin.cara([cen + (t * math.cos(2 * math.pi * i / 6) + Vector((0, 0, 1)) * math.sin(2 * math.pi * i / 6)) * rr for i in range(6)], "T plano gris_oscuro")
        elif d == "nervado":
            for k in range(1, max(3, int(h / 0.1))):
                zf = k / max(3, int(h / 0.1)); pin.linea([sup(2 * math.pi * i / 48, zf) for i in range(49)], "T tinta fina", R_TINTA * 0.6)
        elif d == "rayado":
            for c in range(12):
                a = 2 * math.pi * c / 12
                if (M.to_3x3() @ Vector((math.cos(a), math.sin(a), 0))).dot(vista) < 0.1: continue
                pin.linea([sup(a, 0.08), sup(a, 0.92)], "T tinta fina", R_TINTA * 0.55)
        elif d == "rejilla":
            for c in range(-3, 4):
                x = c * r2 / 4; y = math.sqrt(max(0, r2 * r2 - x * x)) * 0.92
                pin.linea([M @ Vector((x, -y, h + 0.004)), M @ Vector((x, y, h + 0.004))], "T tinta fina", R_TINTA * 0.6)
    elif f == "caja" and d in ("rejilla", "rayado", "nervado"):
        a, b, h = p["ancho"] / 2, p["fondo"] / 2, p["alto"]
        for k in range(1, 6):
            if d == "rejilla": pin.linea([M @ Vector((-a + 2 * a * k / 6, -b - 0.004, h * 0.2)), M @ Vector((-a + 2 * a * k / 6, -b - 0.004, h * 0.8))], "T tinta fina", R_TINTA * 0.6)
            else: pin.linea([M @ Vector((-a, -b - 0.004, h * k / 6)), M @ Vector((a, -b - 0.004, h * k / 6))], "T tinta fina", R_TINTA * 0.6)

def recortar(poli, fn):
    """Parte del poligono donde fn(punto) >= 0 (fn lineal: el corte es un plano)."""
    out = []; g = [fn(v) for v in poli]
    for i in range(len(poli)):
        j = (i + 1) % len(poli)
        if g[i] >= 0: out.append(poli[i])
        if (g[i] >= 0) != (g[j] >= 0): out.append(poli[i].lerp(poli[j], g[i] / (g[i] - g[j])))
    return out

class _SinTrazo:
    """Pincel que no dibuja (para omitir el resalte de una parte)."""
    def linea(self, *a, **k): return None
    def cara(self, *a, **k): return None
SIN_TRAZO = _SinTrazo()

def verticales_redondeadas(p, M, vista):
    """Aristas verticales de una caja redondeada: contorno (cambia de cara visible a oculta) y cambio de tono."""
    perfil = perfil_redondeado(p)
    if not perfil: return []
    R3 = M.to_3x3(); m = len(perfil); h = p["alto"]; out = []
    nor = []
    for i in range(m):
        j = (i + 1) % m; d = (perfil[j][0] - perfil[i][0], perfil[j][1] - perfil[i][1])
        nor.append((R3 @ Vector((d[1], -d[0], 0))).normalized() if math.hypot(*d) > 1e-9 else None)
    for i in range(m):
        a, b = nor[i - 1], nor[i]
        if a is None or b is None: continue
        silueta = (a.dot(vista) > 0) != (b.dot(vista) > 0)
        tono = (banda(a) <= 1) != (banda(b) <= 1)
        if silueta or tono:
            x, y = perfil[i]; out.append([M @ Vector((x, y, 0)), M @ Vector((x, y, h))])
    return out

def dibujar_forma(q, Mo, rel, tin, res, vista, trans, rx, grosor=1.0, resalte=True):
    """Caras con bandas, tinta y resalte de una forma primitiva q con su matriz Mo (una pieza o una parte de un icono).
    resalte=False: sin contorno lima (partes pequenas de un icono: si no, el icono resaltado se vuelve todo lima)."""
    f = q["forma"]; c = q["color"]; RT = R_TINTA * grosor
    RS = R_TINTA * TEMA.get("resalte", 2.1)
    if not resalte: res = SIN_TRAZO
    if f in ("muelle", "manguera", "varilla"):
        if f == "muelle": pts = helice(q, Mo)
        elif f == "manguera": pts = suave3([Mo @ Vector(v) for v in q["camino"]])
        else: pts = [Mo @ Vector((0, 0, 0)), Mo @ Vector((0, 0, q["alto"]))]
        r = q["radio"]; dv = vista * min(0.006, r * 0.5)      # el relleno, un pelo hacia camara: si no, pelea con la tinta
        if f == "manguera" and TEMA.get("neon") and not trans:     # tubo de neon: halo en el suelo, cuerpo azul y brillo claro
            res.linea(pts, "T resalte", r * 1.0 + 0.02)
            rel.linea([Vector((v.x, v.y, 0.006)) for v in pts], "T trazo azul_neon 0.18", r * 2.6)
            tin.linea(pts, "T tinta", r + RT * 0.6)
            rel.linea([v + dv for v in pts], f"T trazo {c}", r)
            rel.linea([v + dv * 1.5 + Vector((0, 0, r * 0.35)) for v in pts], "T trazo cian 0.95", r * 0.38)
            return pts
        res.linea(pts, "T resalte", r * 1.0 + 0.02)
        tin.linea(pts, "T tinta", r + RT * 0.8)
        rel.linea([v + dv for v in pts], f"T trazo {c} {'0.35' if trans else '1'}", r)
        if f == "manguera" and not trans:
            rel.linea([v + dv * 1.5 + Vector((0, 0, r * 0.45)) for v in pts], f"T trazo blanco_hueso 0.35", r * 0.25)
        return pts
    caras, aristas = caras_forma(q)
    R3 = Mo.to_3x3()
    dos_tonos = bool(TEMA.get("lateral"))
    limpio = dos_tonos or not TEMA["papel"]     # tema sin papel: el borde del mismo color tapa las juntas entre facetas
    orden = sorted(caras, key=lambda cf: sum((Mo @ v).dot(vista) for v in cf[0]) / len(cf[0]))   # de atras a delante
    for pts, nor, tipo in orden:
        w = [Mo @ v for v in pts]; nw = (R3 @ nor).normalized()
        if q["material"] == "liquido" and not rx:
            rel.cara(w, f"T {c} {'sup' if tipo == 'tapa' else 'liq'}")
        elif trans:
            rel.cara(w, f"T {c} rx")
        elif limpio and f == "esfera":
            # el limite entre bandas de una esfera es un corte plano (n.L = umbral): cada faceta se parte por el y queda liso
            Cw = Mo @ Vector((0, 0, q["radio"])); r = q["radio"]
            tramos = [(0.38, 9, 1), (-9, 0.38, 2)] if dos_tonos else [(0.72, 9, 0), (0.38, 0.72, 1), (0.0, 0.38, 2), (-9, 0.0, 3)]
            for lo, hi, b in tramos:
                poli = w
                if lo > -9: poli = recortar(poli, lambda v, lo=lo: (v - Cw).dot(LUZ_CARAS) - lo * r)
                if hi < 9: poli = recortar(poli, lambda v, hi=hi: hi * r - (v - Cw).dot(LUZ_CARAS))
                if len(poli) >= 3: rel.cara(poli, f"T {c} b{b}s", radio=0.0022)
        else:
            b = banda(nw)
            if tipo == "dentro": b = min(3, b + 1)
            cen = sum(w, Vector()) / len(w)
            if limpio: rel.cara([cen + (v - cen) * 1.02 for v in w], f"T {c} b{b}s", radio=0.0022)
            else: rel.cara([cen + (v - cen) * 1.04 for v in w], f"T {c} b{b}")   # solape: sin juntas de antialias entre caras
    fino = "T tinta fina" if trans else "T tinta"
    cen = Mo @ Vector((0, 0, q.get("alto", 0) / 2))
    for pts, cerrado in aristas:
        w = [Mo @ v for v in pts]
        if q["forma"] in ("caja", "panel", "peana"):   # aristas un poco hacia fuera (sin pelear con las caras)
            w = [v + (v - cen).normalized() * 0.003 for v in w]
        tin.linea(w + ([w[0]] if cerrado else []), fino, RT * (0.85 if trans else 1.0))
        res.linea(w + ([w[0]] if cerrado else []), "T resalte", RS)
    for s in siluetas(q, Mo, vista) + verticales_redondeadas(q, Mo, vista):
        if q["forma"] in ("caja", "peana"): s = [v + (v - cen).normalized() * 0.003 for v in s]
        tin.linea(s, fino, RT * (0.85 if trans else 1.0)); res.linea(s, "T resalte", RS)
    return None

def brillo_peana(p, M, pin):
    """Peana luminosa: halo azul en el suelo alrededor, linea clara de borde arriba y franja clara en el canto."""
    perfil = perfil_redondeado(p); h = p["alto"]
    def anillo(k, dx, z):        # contorno de la planta agrandado k (y dx metros hacia fuera)
        out = []
        for x, y in perfil:
            n = math.hypot(x, y) or 1.0; out.append(M @ Vector((x * k + x / n * dx, y * k + y / n * dx, z)))
        return out + out[:1]
    pin.linea(anillo(1.0, 0.05, 0.006), "T trazo azul_neon 0.16", 0.05)
    pin.linea(anillo(1.0, 0.02, 0.006), "T trazo azul_neon 0.3", 0.022)
    pin.linea(anillo(1.0, -0.035, h + 0.003), "T trazo cian 0.9", 0.006)
    pin.linea(anillo(1.0, 0.004, h * 0.45), "T trazo cian 0.75", max(0.004, h * 0.18))

def partes_icono(p):
    """Partes de un objeto-icono, ya escaladas y coloreadas por su rol (en coordenadas locales de la pieza)."""
    col = {"c": p["color"], "a": p.get("acento") or "lima", "l": TEMA.get("lateral") or "azul_claro", "n": "negro", "b": "blanco"}
    return [dict(q, color=col[q["rol"]], material=p["material"], detalle="liso") for q in ICO.partes(p["modelo"], p["alto"])]

def tam_parte(q):
    return max([q.get(k, 0) for k in ("ancho", "fondo", "alto")] + [2 * q.get(k, 0) for k in ("radio", "radio2")])

def dibujar_pieza(p, col_, params, rx=False):
    """Objeto GP de una pieza. rx=True: version translucida para rayos X."""
    vista = dir_camara(params)
    trans = rx or p["material"] in ("transparente", "liquido")
    nombre = p["id"] + ("_rx" if rx else "")
    ob = GB.nuevo_gp(nombre, col_, profundidad3d=not trans)
    M = matriz_pieza(p)
    off = vista * EMPUJE if trans else Vector()
    Mo = Matrix.Translation(-off) @ M
    rel, det, tin, res = Pincel(ob, "relleno"), Pincel(ob, "detalle"), Pincel(ob, "tinta"), Pincel(ob, "resalte")
    f = p["forma"]; c = p["color"]; extra = []
    if f == "malla":
        dibujar_malla(p, rel, tin, res, vista, trans, rx, off)
    elif f == "icono":
        for q in partes_icono(p):           # las piezas pequenas (ojos, agujas) con la tinta mas fina y sin resalte
            dibujar_forma(q, Mo @ matriz_pieza(q), rel, tin, res, vista, trans, rx, grosor=max(0.3, min(1.0, tam_parte(q) / 0.15)),
                          resalte=tam_parte(q) >= 0.4 * p["alto"])
    elif f in ("muelle", "manguera", "varilla"):
        dibujar_forma(dict(p, camino=[list(Vector(v) - off) for v in p["camino"]]) if f == "manguera" else p,
                      Matrix.Identity(4) if f == "manguera" else Mo, rel, tin, res, vista, trans, rx)
        if f == "manguera" and not trans and p.get("_adornos"): dibujar_adornos(p, Mo, Pincel(ob, "adornos"), vista, c)
    elif f == "peana":
        dibujar_forma(p, Mo, rel, tin, res, vista, trans, rx)
        if not trans: brillo_peana(p, Mo, det)
    else:
        dibujar_forma(p, Mo, rel, tin, res, vista, trans, rx)
        if not trans and not p.get("_adornos"): detalles(p, Mo, det, vista)      # los adornos sustituyen al detalle generico
        extra = (dibujar_adornos(p, Mo, Pincel(ob, "adornos"), vista, c) or []) if (not trans and p.get("_adornos")) else []
    ob.location = off
    res.lp.capa.hide = True
    ob["comic_tipo"] = "pieza_rx" if rx else "pieza"; ob["comic_id"] = p["id"]
    geo = geometria(p)
    if extra:                        # los carteles cuentan para el encuadre y para colocar efectos encima
        geo["puntos"] += [list(q) for q in extra]; geo["z1"] = max(geo["z1"], max(q.z for q in extra))
    ob["comic_pieza"] = json.dumps(dict(geo, translucida=trans))
    GB.temblor_linea(ob, factor=0.18 * TEMA["temblor"], paso=4, semilla=hash(p["id"]) % 1000)
    return ob

def geometria(p):
    """Centro, radio aproximado y alturas en mundo (para camara, efectos y sombra)."""
    M = matriz_pieza(p); f = p["forma"]
    if f == "malla":
        vs = p["_malla"]["vertices"]; paso = max(1, len(vs) // 300)
        pts = [Vector(v) for v in vs[::paso]]
        (x0, y0, z0), (x1, y1, z1) = p["bbox"]
        pts += [Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        M = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, z0))
    elif f == "manguera":
        pts = [Vector(q) for q in p["camino"]]
    elif f == "icono":
        pts = [M @ Vector(v) for q in ICO.partes(p["modelo"], p["alto"]) for v in ICO.puntos_parte(q)]
    elif f in ("caja", "panel", "peana"):
        a, b = (p["ancho"] / 2, (p["fondo"] if f in ("caja", "peana") else p["grosor"]) / 2)
        pts = [M @ Vector((x, y, z)) for x in (-a, a) for y in (-b, b) for z in (0, p["alto"])]
    elif f == "esfera":
        r = p["radio"]; pts = [M @ Vector((x, y, z)) for x in (-r, r) for y in (-r, r) for z in (0, 2 * r)]
    elif f == "anillo":
        r = p["radio"] + p["grosor"]; pts = [M @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in [i * math.pi / 8 for i in range(16)] for z in (0, 2 * p["grosor"])]
    else:
        r = max(p.get("radio", 0.1), p.get("radio2", 0) if f == "cono" else 0); h = p.get("alto", 0.1)
        pts = [M @ Vector((r * math.cos(a), r * math.sin(a), z)) for a in [i * math.pi / 8 for i in range(16)] for z in (0, h)]
    xs = [q.x for q in pts]; ys = [q.y for q in pts]; zs = [q.z for q in pts]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    out = dict(centro=list(c), radio=max(max(xs) - min(xs), max(ys) - min(ys)) / 2, z0=min(zs), z1=max(zs),
               puntos=[list(q) for q in pts], base=list(M.translation))
    if f == "manguera":          # recorrido suavizado: sombra por tramos (el casco de una L seria un triangulo) y efecto flujo
        out["tramo"] = [list(q) for q in suave3(pts, 4)]; out["grosor"] = p["radio"]
    return out

# ---------------------------------------------------------------- sombra proyectada
def casco(pts):
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    if len(pts) < 3: return pts
    def cruz(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for q in pts:
        while len(lo) >= 2 and cruz(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(hi) >= 2 and cruz(hi[-2], hi[-1], q) <= 0: hi.pop()
        hi.append(q)
    return lo[:-1] + hi[:-1]

def sombra_piezas(pin, geos, params, z=0.004, pared_y=None):
    """Una mancha azul por pieza: proyeccion de sus puntos sobre el suelo (3d) o sobre la pared (2d)."""
    L = LUZ_SOMBRA
    trozos = []
    for g in geos:
        if g.get("tramo"):
            r, t = g.get("grosor", 0.03), g["tramo"]
            trozos += [dict(puntos=[[q[0] + dx, q[1] + dy, q[2] + dz] for q in (t[i], t[i + 1]) for dx in (-r, r) for dy in (-r, r) for dz in (-r, r)])
                       for i in range(len(t) - 1)]
        else: trozos.append(g)
    for g in trozos:
        if params.get("formato") == "2d" and pared_y is not None:
            L2 = Vector((-0.35, 0.8, -0.5)).normalized()
            prj = [Vector(q) + L2 * ((pared_y - q[1]) / L2.y) for q in g["puntos"]]
            h = casco([(q.x, q.z) for q in prj])
            if len(h) >= 3: pin.cara([Vector((x, pared_y - 0.01, zz)) for x, zz in h], "T sombra")
        else:
            prj = [Vector(q) - L * (q[2] / L.z) for q in g["puntos"]]
            h = casco([(q.x, q.y) for q in prj])
            if len(h) >= 3: pin.cara([Vector((x, y, z)) for x, y in h], "T sombra")

# ---------------------------------------------------------------- entorno: suelo, paredes y accesorios
def entorno(col_, params, guion, ancho=7.0):
    m3d = params.get("formato") != "2d"
    ob = GB.nuevo_gp("Entorno", col_, profundidad3d=True)
    sue, jun, par = Pincel(ob, "suelo"), Pincel(ob, "juntas"), Pincel(ob, "pared")
    W = ancho; paso = TEMA.get("paso_baldosa") or {"baldosa": 0.55, "madera": 0.32, "cemento": 1.6}[guion.get("suelo", "baldosa")]
    junta = TEMA.get("junta") or 0.006
    color_suelo = {"baldosa": "papel", "madera": "madera", "cemento": "gris_claro"}[guion.get("suelo", "baldosa")]
    yw = W * 0.42
    if not TEMA["paredes"]:          # tema sin paredes: suelo liso del color del fondo, que se pierde en el horizonte
        color_suelo = "papel"; sue.cara([Vector(v) for v in ((-3 * W, -3 * W, 0), (3 * W, -3 * W, 0), (3 * W, 3 * W, 0), (-3 * W, 3 * W, 0))], "T papel b0")
    else: sue.cara([Vector(v) for v in ((-W, -W, 0), (W, -W, 0), (W, yw, 0), (-W, yw, 0))], f"T {color_suelo} b0")
    Wj, ywj = (W, yw) if TEMA["paredes"] else (2.5 * W, 2.5 * W)       # sin paredes, la cuadricula sigue hasta el horizonte
    n = int(2 * Wj / paso) if TEMA["juntas"] else -1
    for k in range(n + 1):
        x = -Wj + k * paso
        jun.linea([Vector((x, -Wj, 0.002)), Vector((x, ywj, 0.002))], "T trazo baldosa", junta)
        if guion.get("suelo") != "madera":
            y = -Wj + k * paso
            if y <= ywj: jun.linea([Vector((-Wj, y, 0.002)), Vector((Wj, y, 0.002))], "T trazo baldosa", junta)
    # pared del fondo (y la lateral derecha en 3d), con una cuadricula tenue
    if TEMA["paredes"]:
        par.cara([Vector(v) for v in ((-W, yw, 0), (W, yw, 0), (W, yw, 9), (-W, yw, 9))], "T pared b0")
        for k in range(int(2 * W / 0.55) + 1):
            x = -W + k * 0.55; jun.linea([Vector((x, yw - 0.002, 0)), Vector((x, yw - 0.002, 9))], "T trazo pared_oscura 0.35", 0.004)
        for k in range(17):
            jun.linea([Vector((-W, yw - 0.002, k * 0.55)), Vector((W, yw - 0.002, k * 0.55))], "T trazo pared_oscura 0.35", 0.004)
        par.linea([Vector((-W, yw - 0.004, 0.003)), Vector((W, yw - 0.004, 0.003))], "T tinta", R_TINTA * 1.4)
    if m3d and TEMA["paredes"]:
        xw = W * 0.5
        par.cara([Vector(v) for v in ((xw, -W, 0), (xw, yw, 0), (xw, yw, 9), (xw, -W, 9))], "T pared b1")
        par.linea([Vector((xw - 0.004, -W, 0.003)), Vector((xw - 0.004, yw, 0.003))], "T tinta", R_TINTA * 1.4)
        par.linea([Vector((xw - 0.004, yw - 0.004, 0)), Vector((xw - 0.004, yw - 0.004, 9))], "T tinta", R_TINTA * 1.2)
    acc = Pincel(ob, "accesorios"); rnd = random.Random(3)
    for a in guion.get("accesorios", []):
        t, x, y = a["tipo"], a["x"], min(a["y"], yw - 0.4)
        c = a.get("color")
        if t == "alfombra":
            c = c or "mostaza"; w, d = 0.9, 0.55
            acc.cara(rect3(x, y, w, d, 0.006, 0.08), f"T {c} b0"); acc.linea(rect3(x, y, w, d, 0.008, 0.08) + rect3(x, y, w, d, 0.008, 0.08)[:1], "T tinta", R_TINTA)
            acc.linea(rect3(x, y, w - 0.12, d - 0.12, 0.01, 0.05) + rect3(x, y, w - 0.12, d - 0.12, 0.01, 0.05)[:1], f"T trazo {c}", 0.006)
        elif t == "jabon":
            pj = dict(forma="caja", ancho=0.28, fondo=0.16, alto=0.07, x=x, y=y, z=0, rot_x=0, rot_y=0, rot_z=20, color=c or "rosa", material="solido")
            caja_simple(acc, pj, params)
        elif t == "desague":
            acc.cara(circ3(x, y, 0.2, 0.005), "T gris_claro b0"); acc.linea(circ3(x, y, 0.2, 0.007) + circ3(x, y, 0.2, 0.007)[:1], "T tinta", R_TINTA)
            for k in range(-2, 3): acc.linea([Vector((x + k * 0.06, y - 0.15, 0.008)), Vector((x + k * 0.06, y + 0.15, 0.008))], "T tinta fina", 0.006)
        elif t == "enchufe":
            xx = max(-W + 0.5, min(W - 0.5, x)); acc.cara([Vector((xx - 0.12, yw - 0.006, 0.6)), Vector((xx + 0.12, yw - 0.006, 0.6)), Vector((xx + 0.12, yw - 0.006, 0.84)), Vector((xx - 0.12, yw - 0.006, 0.84))], "T blanco_hueso b0")
            for dx in (-0.04, 0.04): acc.cara([Vector((xx + dx, yw - 0.01, 0.72)) + Vector((0.015 * math.cos(i), 0, 0.015 * math.sin(i))) for i in [k * math.pi / 4 for k in range(8)]], "T plano negro")
        elif t == "cubo":
            caja_simple(acc, dict(forma="cono", radio=0.2, radio2=0.26, alto=0.38, x=x, y=y, z=0, rot_x=0, rot_y=0, rot_z=0, color=c or "azul", material="solido"), params)
        elif t == "maceta":
            caja_simple(acc, dict(forma="cono", radio=0.13, radio2=0.18, alto=0.25, x=x, y=y, z=0, rot_x=0, rot_y=0, rot_z=0, color=c or "cobre", material="solido"), params)
            for k in range(6):
                a = k * math.pi / 3; acc.linea([Vector((x, y, 0.25)), Vector((x + 0.25 * math.cos(a), y + 0.25 * math.sin(a), 0.55 + 0.1 * (k % 2)))], "T trazo menta_oscuro", 0.03)
        elif t == "toalla":
            caja_simple(acc, dict(forma="caja", ancho=0.5, fondo=0.35, alto=0.12, x=x, y=y, z=0, rot_x=0, rot_y=0, rot_z=-15, color=c or "verde_agua", material="solido"), params)
        elif t == "hornillo":
            caja_simple(acc, dict(forma="cilindro", radio=0.35, alto=0.08, x=x, y=y, z=0, rot_x=0, rot_y=0, rot_z=0, color=c or "gris_oscuro", material="metal"), params)
    ob["comic_tipo"] = "entorno"
    return ob, yw

def caja_simple(pin, p, params):
    """Dibuja una forma pequena (accesorio) con bandas y tinta dentro de otro objeto."""
    p = dict(dict(detalle="liso"), **p)
    caras, aristas = caras_forma(p); M = matriz_pieza(p); vista = dir_camara(params)
    for pts, nor, tipo in sorted(caras, key=lambda cf: sum((M @ q).dot(vista) for q in cf[0])):
        pin.cara([M @ q for q in pts], f"T {p['color']} b{banda((M.to_3x3() @ nor).normalized())}")
    for pts, cerrado in aristas:
        w = [M @ q for q in pts]; pin.linea(w + ([w[0]] if cerrado else []), "T tinta", R_TINTA * 0.8)
    for s in siluetas(p, M, vista): pin.linea(s, "T tinta", R_TINTA * 0.8)

def rect3(x, y, w, d, z, r):
    pts = []
    for (cx, cy, a0) in ((x + w / 2 - r, y - d / 2 + r, -90), (x + w / 2 - r, y + d / 2 - r, 0), (x - w / 2 + r, y + d / 2 - r, 90), (x - w / 2 + r, y - d / 2 + r, 180)):
        for i in range(5):
            a = math.radians(a0 + 90 * i / 4); pts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z)))
    return pts

def circ3(x, y, r, z, n=32):
    return [Vector((x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n), z)) for i in range(n)]

# ---------------------------------------------------------------- textura de lapiz (grano) para la capa de pantalla
def textura_grano(nombre="grano_lapiz", n=512):
    import numpy as np
    ruta = os.path.join(GB.TEXTURAS, nombre + ".png")
    if not os.path.exists(ruta):
        rng = np.random.default_rng(5)
        a = rng.random((n, n)).astype(np.float32)          # grano fino (sin suavizar: suavizado forma manchas)
        a = (a + np.roll(a, 1, 1)) / 2
        trazos = np.zeros((n, n), np.float32)
        for _ in range(2200):              # rayitas diagonales de lapiz
            x, y = rng.integers(0, n, 2); L = rng.integers(6, 18)
            for t in range(L): trazos[(y + t) % n, (x + t) % n] = 1.0
        alfa = np.clip((a - 0.55) * 0.35, 0, 0.09) + trazos * 0.05
        px = np.zeros((n, n, 4), np.float32); px[..., :3] = 0.25; px[..., 3] = alfa
        os.makedirs(GB.TEXTURAS, exist_ok=True)
        tmp = bpy.data.images.new("_grano", n, n, alpha=True); tmp.pixels.foreach_set(px.ravel())
        tmp.filepath_raw = ruta; tmp.file_format = 'PNG'; tmp.save(); bpy.data.images.remove(tmp)
    img = bpy.data.images.load(ruta, check_existing=True); img.name = nombre
    return img

# ---------------------------------------------------------------- adornos (modo 'detalles'): pantallas, leds, rejillas, iconos...
AVISOS_ADORNOS = []

def _arco(cx, cy, r, a0, a1, n=14):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def _nube():
    circ = [(-0.25, -0.08, 0.17), (0.0, 0.05, 0.24), (0.27, -0.06, 0.17)]; top = []
    for i in range(25):
        x = -0.42 + 0.86 * i / 24
        ys = [cy + math.sqrt(max(0.0, r * r - (x - cx) ** 2)) for cx, cy, r in circ if abs(x - cx) <= r]
        top.append((x, max(ys) if ys else -0.22))
    return [(-0.42, -0.22)] + top + [(0.44, -0.22)]

def _rect(x0, y0, x1, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

# trazos en el cuadrado unidad [-0.5, 0.5]: (puntos, cerrado, relleno)
ICONO_TRAZOS = {
    "sobre": [(_rect(-0.45, -0.3, 0.45, 0.3), True, False), ([(-0.45, 0.3), (0, -0.05), (0.45, 0.3)], False, False)],
    "lambda": [([(-0.3, 0.42), (-0.17, 0.42), (0.32, -0.42)], False, False), ([(0.03, 0.06), (-0.3, -0.42)], False, False)],
    "candado": [(_rect(-0.32, -0.42, 0.32, 0.08), True, False), (_arco(0, 0.08, 0.2, 0, math.pi), False, False), ([(0, -0.1), (0, -0.25)], False, False)],
    "engranaje": [(_arco(0, 0, 0.24, 0, 2 * math.pi, 24), True, False), (_arco(0, 0, 0.08, 0, 2 * math.pi, 12), True, False)] +
                 [([(0.24 * math.cos(a), 0.24 * math.sin(a)), (0.42 * math.cos(a), 0.42 * math.sin(a))], False, False) for a in [k * math.pi / 4 for k in range(8)]],
    "nube": [(_nube(), True, False)],
    "base_datos": [(_arco(0, 0.3, 0.32, 0, 2 * math.pi, 24), True, False), ([(-0.32, 0.3), (-0.32, -0.3)], False, False), ([(0.32, 0.3), (0.32, -0.3)], False, False),
                   ([(0.32 * math.cos(a), -0.3 + 0.1 * math.sin(a)) for a in [math.pi + math.pi * i / 14 for i in range(15)]], False, False),
                   ([(0.32 * math.cos(a), 0.1 * math.sin(a)) for a in [math.pi + math.pi * i / 14 for i in range(15)]], False, False)],
    "grafo": [(_arco(-0.3, -0.25, 0.1, 0, 2 * math.pi, 12), True, True), (_arco(0.3, -0.25, 0.1, 0, 2 * math.pi, 12), True, True),
              (_arco(0, 0.28, 0.1, 0, 2 * math.pi, 12), True, True), ([(-0.24, -0.16), (-0.06, 0.2)], False, False),
              ([(0.06, 0.2), (0.24, -0.16)], False, False), ([(-0.19, -0.25), (0.19, -0.25)], False, False)],
    "ojo": [([(x, 0.24 * math.cos(x / 0.45 * math.pi / 2)) for x in [-0.45 + 0.9 * i / 14 for i in range(15)]] +
             [(x, -0.24 * math.cos(x / 0.45 * math.pi / 2)) for x in [0.45 - 0.9 * i / 14 for i in range(15)]], True, False),
            (_arco(0, 0, 0.12, 0, 2 * math.pi, 12), True, True)],
    "rayo": [([(0.08, 0.48), (-0.28, -0.04), (-0.02, -0.04), (-0.1, -0.48), (0.28, 0.06), (0.02, 0.06)], True, True)],
    "llave": [(_arco(-0.27, 0, 0.15, 0, 2 * math.pi, 14), True, False), ([(-0.12, 0), (0.45, 0)], False, False),
              ([(0.28, 0), (0.28, -0.14)], False, False), ([(0.4, 0), (0.4, -0.12)], False, False)],
    "documento": [([(-0.3, -0.45), (0.3, -0.45), (0.3, 0.28), (0.13, 0.45), (-0.3, 0.45)], True, False), ([(0.13, 0.45), (0.13, 0.28), (0.3, 0.28)], False, False)] +
                 [([(-0.18, y), (0.18, y)], False, False) for y in (0.12, -0.02, -0.16, -0.3)],
    "chip": [(_rect(-0.25, -0.25, 0.25, 0.25), True, False), (_rect(-0.11, -0.11, 0.11, 0.11), True, True)] +
            [(seg, False, False) for k in (-0.14, 0, 0.14) for seg in ([(-0.25, k), (-0.42, k)], [(0.25, k), (0.42, k)], [(k, 0.25), (k, 0.42)], [(k, -0.25), (k, -0.42)])],
    "escudo": [([(-0.34, 0.4), (0.34, 0.4), (0.34, 0.05), (0, -0.46), (-0.34, 0.05)], True, False), ([(-0.14, 0.0), (-0.03, -0.12), (0.16, 0.14)], False, False)],
    "check": [([(-0.36, 0), (-0.1, -0.28), (0.38, 0.3)], False, False)],
    "cruz": [([(-0.32, -0.32), (0.32, 0.32)], False, False), ([(-0.32, 0.32), (0.32, -0.32)], False, False)],
    "barras": [([(-0.44, -0.4), (0.44, -0.4)], False, False), (_rect(-0.35, -0.4, -0.15, -0.1), True, True), (_rect(-0.08, -0.4, 0.12, 0.2), True, True),
               (_rect(0.19, -0.4, 0.39, 0.05), True, True)],
    "traza": [([(-0.47, -0.42), (-0.47, 0.45)], False, False), (_rect(-0.42, 0.28, 0.42, 0.4), True, True), (_rect(-0.3, 0.08, 0.05, 0.2), True, True),
              (_rect(-0.05, -0.12, 0.3, 0.0), True, True), (_rect(0.12, -0.32, 0.4, -0.2), True, True)],
    "onda": [(_arco(0, -0.35, r, math.pi / 4, 3 * math.pi / 4, 10), False, False) for r in (0.2, 0.4, 0.6)] + [(_arco(0, -0.35, 0.05, 0, 2 * math.pi, 8), True, True)],
    "persona": [(_arco(0, 0.22, 0.15, 0, 2 * math.pi, 14), True, False), (_arco(0, -0.42, 0.36, 0, math.pi, 14), True, False)],
    "reloj": [(_arco(0, 0, 0.42, 0, 2 * math.pi, 24), True, False), ([(0, 0), (0, 0.28)], False, False), ([(0, 0), (0.2, -0.06)], False, False)],
}

def cara_local(p, cara, vista, M):
    """Cara de una pieza en el mundo: (sup(x, y, eps) -> punto, ancho, alto, normal). x, y en metros desde el centro de la cara,
    x hacia la derecha de la pantalla e y hacia arriba (en 'arriba', hacia el fondo); las caras curvas se envuelven."""
    f = p["forma"]; R3 = M.to_3x3()
    if f in ("caja", "panel"):
        a = p["ancho"] / 2; b = (p["fondo"] if f == "caja" else p["grosor"]) / 2; h = p["alto"]
        o, u, v, n, W, H = {"frente": ((0, -b, h / 2), (1, 0, 0), (0, 0, 1), (0, -1, 0), 2 * a, h),
                            "atras": ((0, b, h / 2), (-1, 0, 0), (0, 0, 1), (0, 1, 0), 2 * a, h),
                            "izquierda": ((-a, 0, h / 2), (0, -1, 0), (0, 0, 1), (-1, 0, 0), 2 * b, h),
                            "derecha": ((a, 0, h / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0), 2 * b, h),
                            "arriba": ((0, 0, h), (1, 0, 0), (0, 1, 0), (0, 0, 1), 2 * a, 2 * b)}[cara]
        O = M @ Vector(o); U = (R3 @ Vector(u)).normalized(); V = (R3 @ Vector(v)).normalized(); N = (R3 @ Vector(n)).normalized()
        return (lambda x, y, eps=0.004: O + U * x + V * y + N * eps), W, H, N
    E = (R3 @ Vector((0, 0, 1))).normalized(); base = M.translation
    n0 = vista - E * vista.dot(E)
    n0 = n0.normalized() if n0.length > 1e-4 else (R3 @ Vector((0, -1, 0))).normalized()
    T_ = E.cross(n0).normalized()
    if f == "esfera":
        r = p["radio"]; c = base + E * r
        return (lambda x, y, eps=0.004: c + (n0 * r + T_ * x + E * y).normalized() * (r + eps)), 1.8 * r, 1.8 * r, n0
    r1 = p["radio"]; r2 = p.get("radio2", r1) if f == "cono" else r1; h = p["alto"]
    if cara == "arriba":
        O = base + E * h
        return (lambda x, y, eps=0.004: O + T_ * x - n0 * y + E * eps), 2 * r2 * 0.95, 2 * r2 * 0.95, E
    def sup(x, y, eps=0.004):
        zf = min(1.0, max(0.0, 0.5 + y / max(h, 1e-6))); r = r1 + (r2 - r1) * zf; ang = x / max(r, 1e-6)
        return base + E * (h * zf) + (n0 * math.cos(ang) + T_ * math.sin(ang)) * (r + eps)
    return sup, 2.4 * min(r1, r2), h, n0

def dibujar_icono(pin, sup, nombre, cx, cy, s, color, eps, tinta=True, halo=False):
    lw = max(0.003, s * 0.05)
    for pts, cerrado, relleno in ICONO_TRAZOS.get(nombre, ICONO_TRAZOS["sobre"]):
        w = [sup(cx + x * s, cy + y * s, eps) for x, y in pts]
        if cerrado: w = w + w[:1]
        if relleno: pin.cara(w[:-1] if cerrado else w, f"T plano {color}")
        if halo: pin.linea([sup(cx + x * s, cy + y * s, eps - 0.0015) for x, y in pts] + ([w[0]] if cerrado else []), f"T trazo {color} 0.25", lw * 1.7)
        if tinta: pin.linea(w, "T tinta", lw + R_TINTA * 0.45)
        wc = [sup(cx + x * s, cy + y * s, eps + 0.0015) for x, y in pts]
        pin.linea(wc + (wc[:1] if cerrado else []), f"T trazo {color}", lw)

def _subdiv(pts, n, cerrado=True):
    out = []; m = len(pts)
    for i in range(m if cerrado else m - 1):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % m]
        out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    if not cerrado: out.append(pts[-1])
    return out

def dibujar_adornos(p, M, pin, vista, color_pieza):
    """Dibuja los adornos de la pieza; devuelve puntos extra (mundo) que sobresalen de ella (carteles) para encuadre y efectos."""
    f = p["forma"]; extra = []
    if f == "manguera":
        ruta = suave3([Vector(q) for q in p["camino"]]); r = p["radio"]
        if len(ruta) < 2: return
        for E0, E1 in ((ruta[0], ruta[1]), (ruta[-1], ruta[-2])):
            t = (E1 - E0).normalized(); a = t.cross(Vector((0, 0, 1)))
            a = a.normalized() if a.length > 1e-3 else t.cross(Vector((1, 0, 0))).normalized()
            b = t.cross(a).normalized(); rr = r * 1.9
            for k, d in enumerate((r * 1.3, r * 0.15)):          # collarin: primero el disco de detras
                c = E0 + t * d; anillo = [c + (a * math.cos(2 * math.pi * i / 20) + b * math.sin(2 * math.pi * i / 20)) * rr for i in range(20)]
                pin.cara(anillo, f"T metal b{banda(t if t.dot(vista) > 0 else -t)}")
                pin.linea(anillo + anillo[:1], "T tinta", R_TINTA * 0.7)
        return
    for ad in p["_adornos"]:
        cara = ad["cara"]
        try:
            sup, W, H, N = cara_local(p, cara, vista, M)
        except KeyError:
            continue
        if f in ("caja", "panel") and N.dot(vista) < 0.05:          # cara que no se ve: la mas visible
            mejor = max(["frente", "izquierda", "arriba"], key=lambda c_: cara_local(p, c_, vista, M)[3].dot(vista))
            AVISOS_ADORNOS.append(f"{p['id']}: {ad['tipo']} en '{cara}' no se ve; va en '{mejor}'")
            cara = mejor; sup, W, H, N = cara_local(p, cara, vista, M)
        n_sub = 6 if f not in ("caja", "panel") else 1
        c = ad["color"]; t = ad["tipo"]
        xc, yc = (ad["u"] - 0.5) * W, (ad["v"] - 0.5) * H; w, h = ad["ancho"] * W, ad["alto"] * H
        x0, y0, x1, y1 = xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2
        lw = max(0.003, min(0.012, min(w, h) * 0.05)); e0, e1, e2, e3 = 0.007, 0.010, 0.013, 0.016   # por encima de 'detalles' (0.004)
        def P(pts, eps, cerrado=True): return [sup(x, y, eps) for x, y in (_subdiv(pts, n_sub, cerrado) if n_sub > 1 else pts)]
        def R(a0, b0, a1, b1, eps): return P(_rect(a0, b0, a1, b1), eps)
        def borde(pts, eps, nombre="T tinta", rad=R_TINTA * 0.7): pin.linea(pts + pts[:1], nombre, rad)
        def circ(cx, cy, rr, eps, n=14): return [sup(cx + rr * math.cos(2 * math.pi * i / n), cy + rr * math.sin(2 * math.pi * i / n), eps) for i in range(n)]
        if t == "pantalla":
            m = min(w, h) * 0.12
            if TEMA["pantalla"] == "negro": pin.cara(R(x0 - m, y0 - m, x1 + m, y1 + m, e0), f"T plano {c} 0.3")
            marco = R(x0, y0, x1, y1, e1); pin.cara(marco, f"T plano {TEMA['marco']}"); borde(marco, e1)
            k = min(w, h) * 0.1; sx0, sy0, sx1, sy1 = x0 + k, y0 + k, x1 - k, y1 - k; sw, sh = sx1 - sx0, sy1 - sy0
            oscura = TEMA["pantalla"] == "negro"            # pantalla oscura con brillo; clara (tema iconos) con tinta
            pin.cara(R(sx0, sy0, sx1, sy1, e2), f"T plano {TEMA['pantalla']}")
            if not oscura: borde(R(sx0, sy0, sx1, sy1, e2), e2, "T tinta", R_TINTA * 0.5)
            if ad.get("icono") == "ninguno": pass                   # vacia: lo que se ve es lo que hay delante (barras, piezas)
            elif ad.get("icono"):
                dibujar_icono(pin, sup, ad["icono"], (sx0 + sx1) / 2, (sy0 + sy1) / 2, min(sw, sh) * 0.8, c, e3, tinta=not oscura, halo=oscura)
            else:
                for i, L in enumerate((0.8, 0.5, 0.65, 0.35)[:max(2, min(4, int(sh / max(sw, 1e-6) * 6) + 2))]):
                    y = sy1 - sh * (0.2 + 0.22 * i)
                    if y < sy0 + sh * 0.1: break
                    seg = [(sx0 + sw * 0.1, y), (sx0 + sw * (0.1 + L), y)]
                    if oscura: pin.linea(P(seg, e3 - 0.0015, False), f"T trazo {c} 0.3", lw * 2.4)
                    else: pin.linea(P(seg, e3 - 0.0015, False), "T tinta", lw * 1.6)
                    pin.linea(P(seg, e3, False), f"T trazo {c}", lw)
        elif t in ("leds", "ranuras"):
            n = max(1, ad.get("cantidad") or 3)
            if t == "leds":
                hor = w >= h; rr = min(h * 0.32, w / n * 0.3) if hor else min(w * 0.32, h / n * 0.3)
                for i in range(n):
                    cx = x0 + w * (i + 0.5) / n if hor else xc; cy = yc if hor else y0 + h * (i + 0.5) / n
                    pin.cara(circ(cx, cy, rr * 2.0, e0), f"T plano {c} 0.3")
                    led = circ(cx, cy, rr, e1); pin.cara(led, f"T plano {c}"); borde(led, e1, "T tinta fina", R_TINTA * 0.45)
                    pin.cara(circ(cx - rr * 0.3, cy + rr * 0.3, rr * 0.3, e2, 8), "T plano blanco_hueso 0.7")
            else:
                g = h * 0.05; bh = (h - g * (n + 1)) / n
                for i in range(n):
                    b0 = y0 + g + i * (bh + g); bahia = R(x0, b0, x1, b0 + bh, e0)
                    pin.cara(bahia, f"T {color_pieza} b2"); borde(bahia, e1, "T tinta fina", R_TINTA * 0.6)
                    pin.linea(P([(x0 + w * 0.18, b0 + bh / 2), (x1 - w * 0.22, b0 + bh / 2)], e1, False), "T tinta fina", R_TINTA * 0.45)
                    pin.linea(P([(x0 + w * 0.06, b0 + bh * 0.25), (x0 + w * 0.06, b0 + bh * 0.75)], e1, False), "T trazo metal", max(0.003, bh * 0.08))
                    rr = min(bh * 0.18, w * 0.035); cx = x1 - w * 0.09; cy = b0 + bh / 2
                    pin.cara(circ(cx, cy, rr * 2.0, e1), f"T plano {c} 0.3"); pin.cara(circ(cx, cy, rr, e2), f"T plano {c}")
        elif t == "rejilla":
            fondo = R(x0, y0, x1, y1, e0); pin.cara(fondo, f"T {color_pieza} b3"); borde(fondo, e1)
            n = max(3, min(14, int(h / max(lw * 5, 0.012))))
            for i in range(1, n):
                y = y0 + h * i / n
                pin.linea(P([(x0 + w * 0.06, y), (x1 - w * 0.06, y)], e1, False), "T tinta fina", lw * 0.7)
                pin.linea(P([(x0 + w * 0.06, y - lw * 1.2), (x1 - w * 0.06, y - lw * 1.2)], e1, False), f"T trazo {color_pieza} 0.9", lw * 0.6)
        elif t == "tirador":
            th = max(0.006, min(0.025, min(w, h) * 0.35)); seg = [(xc, y0), (xc, y1)] if h > w else [(x0, yc), (x1, yc)]
            for (sx, sy) in seg: pin.cara(circ(sx, sy, th * 1.4, e0, 10), "T plano gris_oscuro")
            pin.linea(P(seg, e1, False), "T tinta", th + R_TINTA * 0.6); pin.linea(P(seg, e2, False), "T trazo metal", th)
            pin.linea(P(seg, e3, False), "T trazo blanco_hueso 0.5", th * 0.3)
        elif t in ("tornillos", "placa"):
            if t == "placa":
                pl = R(x0, y0, x1, y1, e0); pin.cara(pl, f"T {c} b1"); borde(pl, e1)
            rr = max(0.005, min(0.02, min(w, h) * 0.07)); k = rr * 1.8
            for cx, cy in ((x0 + k, y0 + k), (x1 - k, y0 + k), (x1 - k, y1 - k), (x0 + k, y1 - k)):
                tor = circ(cx, cy, rr, e2, 10); pin.cara(tor, "T metal b1"); borde(tor, e2, "T tinta fina", R_TINTA * 0.45)
                pin.linea([sup(cx - rr * 0.6, cy - rr * 0.6, e3), sup(cx + rr * 0.6, cy + rr * 0.6, e3)], "T tinta fina", R_TINTA * 0.4)
        elif t == "franja":
            fr = R(x0, y0, x1, y1, e0); pin.cara(fr, f"T {c} b1")
            for y in (y0, y1): pin.linea(P([(x0, y), (x1, y)], e1, False), "T tinta", R_TINTA * 0.6)
        elif t == "boton":
            rr = min(w, h) / 2; pin.cara(circ(xc, yc, rr, e0), "T plano gris_oscuro")
            bt = circ(xc, yc, rr * 0.72, e1); pin.cara(bt, f"T plano {c}"); borde(bt, e1, "T tinta fina", R_TINTA * 0.5)
            pin.cara(circ(xc - rr * 0.22, yc + rr * 0.22, rr * 0.22, e2, 8), "T plano blanco_hueso 0.6")
        elif t == "teclado":
            fondo = R(x0, y0, x1, y1, e0); pin.cara(fondo, "T plano gris_oscuro"); borde(fondo, e0)
            filas = 4; cols = max(6, min(16, round(w / max(h, 1e-6) * filas))); kw, kh = w / cols, h / filas
            for i in range(filas):
                for j in range(cols):
                    if i == 0 and 2 <= j < cols - 2:
                        if j == 2: pin.cara(R(x0 + kw * 2 + kw * 0.12, y0 + kh * 0.15, x0 + kw * (cols - 2) - kw * 0.12, y0 + kh * 0.85, e1), f"T plano {c if c != 'gris_oscuro' else 'gris'}")
                        continue
                    pin.cara(R(x0 + kw * j + kw * 0.12, y0 + kh * i + kh * 0.15, x0 + kw * (j + 1) - kw * 0.12, y0 + kh * (i + 1) - kh * 0.15, e1),
                             f"T plano {c if c != 'gris_oscuro' else 'gris'}")
        elif t == "icono":
            dibujar_icono(pin, sup, ad.get("icono") or "sobre", xc, yc, min(w, h) * 0.9, c, e1)
        elif t == "cartel":
            top = sup(xc, yc, 0.0); s = max(0.12, min(0.3, max(w, h)))
            fwd = -vista; dere = fwd.cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(fwd).normalized()
            P0 = top + Vector((0, 0, 0.05 + s * 0.55))
            pin.linea([top, P0 - Vector((0, 0, s * 0.45))], "T tinta", 0.008 + R_TINTA * 0.5); pin.linea([top, P0 - Vector((0, 0, s * 0.45))], "T trazo gris", 0.008)
            def bill(x, y, eps=0.0): return P0 + dere * x + arr * y + vista * eps
            rr = s * 0.12; esq = []
            for (cx, cy, a0) in ((s / 2 - rr, -s / 2 + rr, -90), (s / 2 - rr, s / 2 - rr, 0), (-s / 2 + rr, s / 2 - rr, 90), (-s / 2 + rr, -s / 2 + rr, 180)):
                esq += [bill(cx + rr * math.cos(math.radians(a0 + 90 * i / 4)), cy + rr * math.sin(math.radians(a0 + 90 * i / 4))) for i in range(5)]
            pin.cara(esq, "T blanco_hueso b0"); pin.linea(esq + esq[:1], "T tinta", R_TINTA * 0.9); extra += esq[::5]
            dibujar_icono(pin, bill, ad.get("icono") or "lambda", 0, 0, s * 0.7, c, 0.004)
    return extra
