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
    a = math.radians(35 if az is None else az); e = math.radians(TEMA.get("elevacion", 32))      # arcilla: 35
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

# Adelanto hacia la camara de las lineas de resalte, como el stroke_depth_offset de Line Art
# (escenes/Cyberpunk_fixed.blend). El resalte va justo encima de la tinta y de las caras: a la misma profundidad,
# el test de profundidad elige al azar por pixel y el contorno lima sale a trozos (z-fighting). En camara
# ortografica, mover un trazo a lo largo de la direccion de vista no lo desplaza en pantalla.
EMPUJE_RESALTE = 0.02

class Pincel:
    """Lapiz con materiales del estilo tecnico. empuje: vector (mundo) que se suma a cada punto (adelanto de profundidad)."""
    def __init__(self, ob, capa, frame=0, empuje=None):
        self.lp = Lapiz(ob, capa, frame=frame); self.ob = ob; self.empuje = empuje
    def _m(self, nombre):
        mats = self.ob.data.materials
        for i, m in enumerate(mats):
            if m and m.name == nombre: return nombre
        mats.append(mat(nombre)); return nombre
    def _mover(self, pts):
        return [p + self.empuje for p in pts] if self.empuje is not None else pts
    def cara(self, pts, nombre, radio=0.0004):
        self._m(nombre); return self.lp.trazo(self._mover(pts), nombre, radio=radio, cerrado=True, relleno=True)
    def linea(self, pts, nombre="T tinta", radio=None, cerrado=False, afilar=False):
        self._m(nombre)
        return self.lp.trazo(self._mover(pts), nombre, radio=R_TINTA if radio is None else radio, cerrado=cerrado, afilar=afilar)

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

def _medialuna(cx, cy, R, cx2, cy2, r2, n=16):
    """Contorno de un circulo (centro c, radio R) menos otro que lo corta (c2, r2): una media luna del biohazard."""
    D = math.hypot(cx2 - cx, cy2 - cy); phi = math.atan2(cy2 - cy, cx2 - cx)
    al = math.acos(max(-1.0, min(1.0, (R * R + D * D - r2 * r2) / (2 * R * D))))
    de = math.acos(max(-1.0, min(1.0, (r2 * r2 + D * D - R * R) / (2 * r2 * D)))); ga = phi + math.pi
    out = [(cx + R * math.cos(phi + al + (2 * math.pi - 2 * al) * i / n), cy + R * math.sin(phi + al + (2 * math.pi - 2 * al) * i / n)) for i in range(n + 1)]
    out += [(cx2 + r2 * math.cos(ga + de - 2 * de * i / n), cy2 + r2 * math.sin(ga + de - 2 * de * i / n)) for i in range(1, n)]
    return out

# simbolo de riesgo biologico en el cuadrado unidad (radio 0.5): tres medias lunas abiertas hacia fuera
BIOHAZARD = [_medialuna(0.26 * math.cos(a), 0.26 * math.sin(a), 0.24, 0.39 * math.cos(a), 0.39 * math.sin(a), 0.165)
             for a in (math.radians(90), math.radians(210), math.radians(330))]

def dibujar_biohazard(p, pl, cen, w, color):
    """Biohazard de diametro w sobre el plano pl(cen, x, y, capa) -> punto. Primero todos los contornos (debajo) y luego
    los rellenos, para que la tinta solo asome por fuera; en malla, pl adelanta cada capa (el GP la ignora)."""
    def circ(r, n, k): return [pl(cen, r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), k) for i in range(n + 1)]
    def lunas(k): return [[pl(cen, x * w, y * w, k) for x, y in m] for m in BIOHAZARD]
    for pts in lunas(0): p.linea(pts + pts[:1], "T tinta", R_TINTA * 1.1)
    p.linea(circ(0.15 * w, 24, 0), "T tinta", 0.06 * w + R_TINTA * 0.8)
    for pts in lunas(1): p.cara(pts, f"T plano {color}")
    p.linea(circ(0.15 * w, 24, 2), f"T trazo {color}", 0.06 * w)
    p.cara(circ(0.075 * w, 16, 3)[:-1], "T plano gris_oscuro")
    for rr in (0.115, 0.185): p.linea(circ(rr * w, 24, 3), "T tinta", max(0.0025, 0.012 * w))   # el aro, separado

_CEREBRO = {}
def caras_cerebro(r, detalle=5, surcos=False):
    """Cerebro procedural en coordenadas locales (base en z=0, largo en X con el frontal hacia -X): dos hemisferios
    (elipsoides con la cara interna aplanada, separados por la cisura). Un ruido de Perlin deformado marca los surcos donde
    cruza el cero: alli la superficie se hunde un poco (en U) y, con surcos=True, se devuelven tambien esas curvas de nivel
    como polilineas [(puntos, normales)] para dibujarlas como lineas gruesas, como en la referencia. Ademas, la cisura de
    Silvio (frontal-temporal). Ni surcos ni lineas en la cara interna ni debajo. Determinista y con cache."""
    clave = (round(r, 5), detalle)
    if clave in _CEREBRO: return _CEREBRO[clave] if surcos else _CEREBRO[clave][0]
    if os.path.exists(CP.MODELO_CEREBRO):
        # modelo descargado (preparar_modelo_forma.py): sus surcos ya son geometria; Line Art los contornea
        datos = json.load(open(CP.MODELO_CEREBRO))["niveles"]["alto" if detalle >= 5 else "bajo"]
        V = [Vector(v) * r for v in datos["v"]]; caras = []
        for f in datos["f"]:
            pts = [V[i] for i in f]; n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            caras.append((pts, n.normalized() if n.length > 1e-12 else Vector((0, 0, 1)), "lado"))
        _CEREBRO[clave] = (caras, [], [])
        return _CEREBRO[clave] if surcos else caras
    import bmesh
    from mathutils import noise
    def suav(a, b, x): t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
    caras, lineas = [], []
    for s in (-1, 1):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=detalle, radius=1.0)
        campo = {}
        for v in bm.verts:
            d = v.co.normalized()
            ax = 1.0 if d.x < 0 else 0.95                                   # frontal redondo, occipital algo mas corto
            ay = 0.71 if d.y * s > 0 else 0.08                              # cara lateral abombada, la interna plana (cisura estrecha)
            az = (0.62 * (1 - 0.14 * max(0.0, d.x))) if d.z > 0 else 0.42   # mas bajo por detras
            q = Vector((d.x * ax, d.y * ay, d.z * az))
            if d.z < 0 and d.x < 0: q.z += 0.16 * (-d.x) * (-d.z)            # el frontal se curva hacia arriba por debajo
            nor = Vector((q.x / ax ** 2, q.y / ay ** 2, q.z / az ** 2)).normalized()
            P = Vector((q.x, q.y + s * 0.09, q.z + 0.44))                   # en radios; base en z ~ 0.02
            fuera = suav(-0.3, 0.1, d.y * s) * suav(-0.6, -0.25, d.z)        # ni en la cara interna ni debajo
            n = 1.0
            if fuera > 0:
                w = Vector((noise.noise(P * 2.4 + Vector((7.1, 0.0, 0.0))), noise.noise(P * 2.4 + Vector((0.0, 3.3, 0.0))),
                            noise.noise(P * 2.4 + Vector((0.0, 0.0, 5.2)))))
                n = noise.noise((P + w * 0.25) * 5.0 + Vector((s * 11.0, 0.0, 0.0)))
                if d.y * s > 0.2:                                           # cisura de Silvio: un surco mas, de delante-abajo a detras-arriba
                    linea = P.z - (0.34 + 0.32 * (P.x + 0.45))
                    if -0.6 < P.x < 0.45 and abs(linea) < abs(n) * 0.5: n = linea * 2.0
            hueco = 0.03 * fuera * (1 - suav(0.0, 0.22, abs(n)))           # surco en U, poco profundo: la linea se ve dentro
            v.co = (P - nor * hueco) * r
            campo[v.index] = (n, fuera)
        bm.normal_update()
        for f in bm.faces: caras.append(([v.co.copy() for v in f.verts], f.normal.copy(), "lado"))
        if True:                  # siempre: la cache guarda caras y lineas juntas
            # curvas de nivel n = 0 (marching triangles): un punto por arista que cambia de signo; cada triangulo une dos
            pt, vec = {}, {}
            def cruce(a, b):
                k = (min(a.index, b.index), max(a.index, b.index))
                if k not in pt:
                    na, nb = campo[a.index][0], campo[b.index][0]; t = na / (na - nb)
                    pt[k] = (a.co.lerp(b.co, t), a.normal.lerp(b.normal, t).normalized())
                return k
            for f in bm.faces:
                vs = list(f.verts)
                if min(campo[v.index][1] for v in vs) < 0.35: continue
                ks = [cruce(a, b) for a, b in ((vs[0], vs[1]), (vs[1], vs[2]), (vs[2], vs[0]))
                      if (campo[a.index][0] > 0) != (campo[b.index][0] > 0)]
                if len(ks) == 2:
                    vec.setdefault(ks[0], []).append(ks[1]); vec.setdefault(ks[1], []).append(ks[0])
            usados = set()
            for k0 in list(vec):
                if k0 in usados: continue
                # extremo de una cadena abierta, si lo hay; si no, es un lazo
                k = k0; previo = None
                while True:
                    sig = [x for x in vec[k] if x != previo]
                    if len(vec[k]) < 2 or not sig or sig[0] == k0: break
                    previo, k = k, sig[0]
                inicio = k; cadena = [inicio]; usados.add(inicio); previo = None
                while True:
                    sig = [x for x in vec[cadena[-1]] if x != previo and x not in usados]
                    if not sig: break
                    previo = cadena[-1]; cadena.append(sig[0]); usados.add(sig[0])
                if len(vec[inicio]) == 2 and inicio in vec[cadena[-1]] and len(cadena) > 2: cadena.append(inicio)
                if len(cadena) >= 4:
                    cerrada = cadena[0] == cadena[-1]
                    ps, ns = [pt[x][0].copy() for x in cadena], [pt[x][1].copy() for x in cadena]
                    for _ in range(2):                                     # Chaikin: sin los picos de la malla
                        ps, ns = _chaikin(ps, cerrada), [n.normalized() for n in _chaikin(ns, cerrada)]
                    # un segundo ruido corta las curvas cerradas en surcos abiertos y ramificados (como la referencia)
                    tramo = []
                    for q_, n_ in zip(ps + [None], ns + [None]):
                        if q_ is not None and noise.noise(q_ / r * 2.2 + Vector((s * 4.0, 1.7, 0.0))) > -0.18:
                            tramo.append((q_, n_)); continue
                        if len(tramo) >= 6: lineas.append(([a for a, b in tramo], [b for a, b in tramo]))
                        tramo = []
        bm.free()
    # brillos: en las curvas largas, un trazo corto paralelo al surco, desplazado hacia el lado de la luz (arriba-izquierda)
    luz = Vector((-0.5, -0.6, 0.8)).normalized(); brillos = []
    for ps, ns in lineas:
        if len(ps) < 14: continue
        i0, i1 = int(len(ps) * 0.3), int(len(ps) * 0.7); trazo = []
        for i in range(i0, i1):
            t = (ps[min(i + 1, len(ps) - 1)] - ps[max(i - 1, 0)]).normalized(); lado = ns[i].cross(t).normalized()
            if lado.dot(luz) < 0: lado = -lado
            if ns[i].dot(luz) < 0.25: trazo = []; continue
            trazo.append((ps[i] + lado * 0.03 * r, ns[i]))
        if len(trazo) >= 4: brillos.append(([a for a, b in trazo], [b for a, b in trazo]))
    _CEREBRO[clave] = (caras, lineas, brillos)
    return (caras, lineas, brillos) if surcos else caras

def _chaikin(pts, cerrada):
    out = [] if cerrada else [pts[0]]; m = len(pts)
    for i in range(m if cerrada else m - 1):
        a, b = pts[i], pts[(i + 1) % m]; out += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
    if not cerrada: out.append(pts[-1])
    return out

def surcos_cerebro(p, M, pin, radio=None):
    """Lineas gruesas de tinta por los surcos del cerebro, pegadas a la superficie (malla) o como trazos (GP)."""
    detalle = 5 if TEMA.get("mallas") else 3
    _, lineas, brillos = caras_cerebro(p["radio"], detalle, surcos=True)
    R3 = M.to_3x3(); rr = radio or max(0.003, p["radio"] * 0.0125)
    for grupo, mat_, ancho, eps in ((lineas, "T tinta", rr, 0.004), (brillos, "T plano rosa_brillo", rr * 0.9, 0.005)):
        for pts, nors in grupo:
            tr = _Trazo(M @ (v + n * eps) for v, n in zip(pts, nors)); tr.normales = [(R3 @ n).normalized() for n in nors]
            pin.linea(tr, mat_, ancho)

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
    if f == "biohazard":         # en GP: las medias lunas en el plano XZ, mirando a -Y (en malla, cyberpunk mira a camara)
        w = p["alto"]
        return [([Vector((x * w, 0, w / 2 + y * w)) for x, y in m], Vector((0, -1, 0)), "lado") for m in BIOHAZARD], aristas
    if f == "cerebro":           # en GP, menos facetas (cada una es un relleno)
        return caras_cerebro(p["radio"], 5 if TEMA.get("mallas") else 3), aristas
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
    v_nor = [Vector() for _ in V]
    for k, f in enumerate(m["caras"]):
        for i in f: v_nor[i] += normales[k]
    v_nor = [n.normalized() if n.length > 1e-8 else vista for n in v_nor]
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
    # Desplazamiento micrometrico normal + vista: evita Z-fighting entre relleno, tinta y resalte en modo 3D
    V_tin = [V[i] + vista * 0.0022 + v_nor[i] * 0.0015 for i in range(len(V))]
    V_res = [V[i] + vista * 0.0010 + v_nor[i] * 0.0010 for i in range(len(V))]
    for cad in encadenar(list({tuple(sorted(e)) for e in vivas + silu})):
        tin.linea([V_tin[i] for i in cad], fino, R_TINTA * (0.7 if trans else 0.85))
    for cad in encadenar(list({tuple(sorted(e)) for e in silu})):
        res.linea([V_res[i] for i in cad], "T resalte", R_TINTA * 2.1)

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
        for rr in (R + t * 1.004, R - t * 1.004):
            out.append([M @ Vector((rr * math.cos(2 * math.pi * i / 48), rr * math.sin(2 * math.pi * i / 48), t * 1.004)) for i in range(49)])
    return out

def helice(p, M):
    r, h, n = p["radio"], p["alto"], int(p.get("vueltas", 8)); pts = []
    for i in range(n * 24 + 1):
        a = 2 * math.pi * i / 24; pts.append(M @ Vector((r * math.cos(a), r * math.sin(a), h * i / (n * 24))))
    return pts

def detalles(p, M, pin, vista):
    """Agujeros (perforado), costillas (nervado), rayas (rayado) o rejilla sobre la superficie."""
    if p["forma"] == "cerebro": surcos_cerebro(p, M, pin); return
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
    if f == "tubo" and trans:
        # Un tubo transparente construido faceta a faceta acumula alfa en cada
        # union de las caras. Eso deja una serie de lineas espurias (muy
        # visibles en tubos tumbados). Dibujamos una sola lamina frontal y
        # solo los dos bordes y las bocas que definen el volumen.
        r, h = q["radio"], q["alto"]
        eje = (Mo.to_3x3() @ Vector((0, 0, 1))).normalized()
        lado = eje.cross(vista - eje * vista.dot(eje))
        if lado.length > 1e-5:
            lado.normalize()
            base, fin = Mo @ Vector(), Mo @ Vector((0, 0, h))
            rel.cara([base - lado * r, fin - lado * r, fin + lado * r, base + lado * r], f"T {c} rx")
            for a, b in ((base - lado * r, fin - lado * r), (base + lado * r, fin + lado * r)):
                tin.linea([a, b], "T tinta fina", RT * 0.7)
                res.linea([a, b], "T resalte", RS)
            # Las dos bocas bastan para leer el tubo; no se dibuja el aro
            # interior ni las aristas de las 40 facetas.
            for z in (0, h):
                aro = [Mo @ p for p in anillo_pts(r, z, 32)]
                tin.linea(aro + aro[:1], "T tinta fina", RT * 0.7)
                res.linea(aro + aro[:1], "T resalte", RS)
            return None
    if f in ("muelle", "manguera", "varilla"):
        if f == "muelle": pts = helice(q, Mo)
        elif f == "manguera": pts = suave3([Mo @ Vector(v) for v in q["camino"]])
        else: pts = [Mo @ Vector((0, 0, 0)), Mo @ Vector((0, 0, q["alto"]))]
        r = q["radio"]; dv = vista * min(0.006, r * 0.5)      # el relleno, un pelo hacia camara: si no, pelea con la tinta
        pts_res = [v - vista * 0.0015 for v in pts]            # resalte un pelo detras de la tinta para no pelear en 3D
        if f == "manguera" and TEMA.get("neon") and not trans:     # tubo de neon: halo en el suelo, cuerpo azul y brillo claro
            res.linea(pts_res, "T resalte", r * 1.0 + 0.02)
            rel.linea([Vector((v.x, v.y, 0.006)) for v in pts], "T trazo azul_neon 0.18", r * 2.6)
            tin.linea(pts, "T tinta", r + RT * 0.6)
            rel.linea([v + dv for v in pts], f"T trazo {c}", r)
            rel.linea([v + dv * 1.5 + Vector((0, 0, r * 0.35)) for v in pts], "T trazo cian 0.95", r * 0.38)
            return pts
        res.linea(pts_res, "T resalte", r * 1.0 + 0.02)
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
    rad_off = 0.0025 if q["forma"] in ("caja", "panel", "peana") else 0.0018
    def _off_trazo(pts_w, dv_cam, dv_rad):
        return [v + vista * dv_cam + ((v - cen).normalized() * dv_rad if (v - cen).length > 1e-6 else Vector()) for v in pts_w]
    for pts, cerrado in aristas:
        w = [Mo @ v for v in pts]
        w_tin = _off_trazo(w, 0.0022, rad_off)
        w_res = _off_trazo(w, 0.0010, rad_off * 0.7)
        tin.linea(w_tin + ([w_tin[0]] if cerrado else []), fino, RT * (0.85 if trans else 1.0))
        res.linea(w_res + ([w_res[0]] if cerrado else []), "T resalte", RS)
    for s in siluetas(q, Mo, vista) + verticales_redondeadas(q, Mo, vista):
        s_tin = _off_trazo(s, 0.0022, rad_off if q["forma"] in ("caja", "peana") else 0.001)
        s_res = _off_trazo(s, 0.0010, (rad_off if q["forma"] in ("caja", "peana") else 0.001) * 0.7)
        tin.linea(s_tin, fino, RT * (0.85 if trans else 1.0)); res.linea(s_res, "T resalte", RS)
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
    rel, det, tin = Pincel(ob, "relleno"), Pincel(ob, "detalle"), Pincel(ob, "tinta")
    res = Pincel(ob, "resalte", empuje=vista * EMPUJE_RESALTE)      # delante de tinta y caras: sin z-fighting
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
    elif f == "cerebro":
        (x0, y0, z0), (x1, y1, z1) = CP.caja_cerebro(); r = p["radio"]
        pts = [M @ Vector((x * r, y * r, z * r)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    elif f == "biohazard":
        w = p["alto"]; pts = [M @ Vector((x, y, z)) for x in (-w / 2, w / 2) for y in (-0.01, 0.01) for z in (0, w)]
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
    # cilindro en vista isometrica: la tapa es una elipse (no un circulo) y las bandas son medias elipses iguales
    "base_datos": [([(0.34 * math.cos(a), 0.3 + 0.16 * math.sin(a)) for a in [2 * math.pi * i / 24 for i in range(24)]], True, False),
                   ([(-0.34, 0.3), (-0.34, -0.28)], False, False), ([(0.34, 0.3), (0.34, -0.28)], False, False),
                   ([(0.34 * math.cos(a), -0.28 + 0.16 * math.sin(a)) for a in [math.pi + math.pi * i / 14 for i in range(15)]], False, False),
                   ([(0.34 * math.cos(a), 0.01 + 0.16 * math.sin(a)) for a in [math.pi + math.pi * i / 14 for i in range(15)]], False, False)],
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
    # grafica que sube: ejes y una linea quebrada ascendente con un punto al final (ventas, ingresos, mejora)
    "grafica": [([(-0.42, 0.4), (-0.42, -0.4), (0.44, -0.4)], False, False),
                ([(-0.32, -0.24), (-0.12, -0.04), (0.06, -0.16), (0.3, 0.2)], False, False),
                (_arco(0.3, 0.2, 0.07, 0, 2 * math.pi, 12), True, True)],
}

def cara_local(p, cara, vista, M):
    """Cara de una pieza en el mundo: (sup(x, y, eps) -> punto, ancho, alto, normal). x, y en metros desde el centro de la cara,
    x hacia la derecha de la pantalla e y hacia arriba (en 'arriba', hacia el fondo); las caras curvas se envuelven."""
    f = p["forma"]; R3 = M.to_3x3()
    if f == "cerebro":           # solo 'arriba' (su cartel): un plano a la altura de la coronilla, algo hundido en ella
        if cara != "arriba": raise KeyError("cerebro: solo admite el cartel de arriba")
        (x0, y0, z0), (x1, y1, z1) = CP.caja_cerebro(); r = p["radio"]
        O = M @ Vector((0, 0, z1 * r * 0.97)); U = (R3 @ Vector((1, 0, 0))).normalized(); V = (R3 @ Vector((0, 1, 0))).normalized()
        N = (R3 @ Vector((0, 0, 1))).normalized()
        return (lambda x, y, eps=0.004: O + U * x + V * y + N * eps), 0.6 * r, 0.6 * r, N
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

def normal_sup(sup, x, y, d=0.002):
    """Normal de la superficie sup(x, y, eps) en (x, y), por diferencias (vale para caras planas, curvas y carteles)."""
    n = (sup(x + d, y, 0.0) - sup(x - d, y, 0.0)).cross(sup(x, y + d, 0.0) - sup(x, y - d, 0.0))
    return n.normalized() if n.length > 1e-12 else None

def trazo_sup(sup, xy, eps, cerrado=False):
    """Puntos de mundo de un trazo sobre una superficie, con la normal en cada punto: en malla la cinta de la linea va
    pegada a la cara (como una calcomania). Si mirara a la camara, en una tapa vista de lado se hundiria a medias en ella
    y saldria dentada."""
    xy = list(xy) + (list(xy[:1]) if cerrado else [])
    out = _Trazo(sup(x, y, eps) for x, y in xy)
    ns = [normal_sup(sup, x, y) for x, y in xy]
    if all(n is not None for n in ns): out.normales = ns
    return out

def dibujar_icono(pin, sup, nombre, cx, cy, s, color, eps, tinta=True, halo=False):
    lw = max(0.003, s * 0.05)
    t_extra = min(R_TINTA * 0.45, s * 0.06)          # la tinta crece con el icono: en uno pequeno no se lo come
    for pts, cerrado, relleno in ICONO_TRAZOS.get(nombre, ICONO_TRAZOS["sobre"]):
        xy = [(cx + x * s, cy + y * s) for x, y in pts]
        w = trazo_sup(sup, xy, eps, cerrado)
        if relleno: pin.cara(w[:-1] if cerrado else w, f"T plano {color}")
        if halo: pin.linea(trazo_sup(sup, xy, eps - 0.003, cerrado), f"T trazo {color} 0.25", lw * 1.7)
        if tinta: pin.linea(w, "T tinta", lw + t_extra)
        pin.linea(trazo_sup(sup, xy, eps + 0.0015, cerrado), f"T trazo {color}", lw)

class _Trazo(list):
    """Puntos de mundo de un trazo sobre una cara curva, con la normal de la superficie en cada punto ('normales'): la
    malla tiende la cinta de la linea pegada a la superficie (si mirara a la camara fija, al girar la camara o en una
    pieza transparente se veria de canto, como un trazo de cera). El GP la ignora."""
    normales = None

def _cerrar(pts):
    out = _Trazo(list(pts) + list(pts[:1]))
    if getattr(pts, "normales", None): out.normales = pts.normales + pts.normales[:1]
    return out

class _Rejilla(_Trazo):
    """Contorno de un relleno sobre una cara curva que ademas lleva 'rejilla' (filas de puntos): la malla rellena con
    cuadrilateros (un poligono no plano que envuelve un cilindro se triangula por dentro de la pieza). El GP usa el contorno."""
    rejilla = None

_TEXTOS = {}
def poligonos_texto(texto):
    """Poligonos 2D (triangulos) de un texto en la fuente de rotulos, centrado y con la altura de las mayusculas = 1."""
    if texto in _TEXTOS: return _TEXTOS[texto]
    cu = bpy.data.curves.new("_rotulo", 'FONT'); cu.body = texto; cu.align_x = 'CENTER'
    if os.path.exists(CP.FUENTE_TECNICA): cu.font = bpy.data.fonts.load(CP.FUENTE_TECNICA, check_existing=True)
    ob = bpy.data.objects.new("_rotulo", cu); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
    V = [v.co.copy() for v in me.vertices]; tris = []
    me.calc_loop_triangles()
    for t in me.loop_triangles: tris.append([V[i] for i in t.vertices])
    # contornos de las letras: aristas con una sola cara, encadenadas en lazos (exterior y huecos)
    usos = {}
    for t in me.loop_triangles:
        for a, b in ((t.vertices[0], t.vertices[1]), (t.vertices[1], t.vertices[2]), (t.vertices[2], t.vertices[0])):
            k = (min(a, b), max(a, b)); usos[k] = usos.get(k, 0) + 1
    vec = {}
    for (a, b), n in usos.items():
        if n == 1: vec.setdefault(a, []).append(b); vec.setdefault(b, []).append(a)
    lazos, vistos = [], set()
    for v0 in vec:
        if v0 in vistos: continue
        lazo = [v0]; vistos.add(v0)
        while True:
            sig = [x for x in vec[lazo[-1]] if x not in vistos]
            if not sig: break
            lazo.append(sig[0]); vistos.add(sig[0])
        if len(lazo) > 2: lazos.append([V[i] for i in lazo])
    ob.evaluated_get(dg).to_mesh_clear(); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    if not V: _TEXTOS[texto] = ([], []); return _TEXTOS[texto]
    x0, x1 = min(v.x for v in V), max(v.x for v in V); y0, y1 = min(v.y for v in V), max(v.y for v in V)
    h = max(1e-6, y1 - y0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    def n2(v): return ((v.x - cx) / h, (v.y - cy) / h)
    _TEXTOS[texto] = ([[n2(v) for v in t] for t in tris], [[n2(v) for v in l] for l in lazos])
    return _TEXTOS[texto]

def ancho_texto(texto):
    """Ancho del texto en la fuente de rotulos, en alturas de mayuscula."""
    pol, _ = poligonos_texto(texto)
    return max((abs(x) for t in pol for x, y in t), default=0.5) * 2

# ---------------------------------------------------------------- workflow visible: datos vivos y pasos del ciclo
H_ETQ, H_VAL, R_PASO, H_PASO = 0.03, 0.058, 0.045, 0.026
COLOR_DATO = {"lima": "lima", "rojo": "rojo", "azul": "cielo", "blanco": "blanco"}     # sobre panel oscuro: el azul, mas claro

def ejes_vista(vista):
    fwd = -vista; dere = fwd.cross(Vector((0, 0, 1))).normalized(); return dere, dere.cross(fwd).normalized()

def medida_dato(etiqueta, valores):
    """Ancho y alto del panel de un dato (el mismo para todos los valores de un contador: no baila)."""
    w = max([ancho_texto(etiqueta) * H_ETQ if etiqueta else 0.0] + [ancho_texto(v) * H_VAL for v in valores if v]) + 0.07
    return w, (H_ETQ + 0.025 if etiqueta else 0.0) + H_VAL + 0.055

def _lado_libre(indice, pid, dere):
    """+1 si el lado libre de la pieza (hacia fuera de la maqueta) es la derecha de la pantalla, -1 si es la izquierda."""
    todos = [Vector(q) for v in indice["piezas"].values() if v["forma"] != "manguera" for q in v["geo"]["puntos"]]
    cm = sum(q.dot(dere) for q in todos) / max(1, len(todos))
    return 1 if Vector(indice["piezas"][pid]["geo"]["centro"]).dot(dere) >= cm else -1

def sitio_dato(indice, pid, vista, w, h, orden=0, n=1):
    """Centro del panel de un dato: junto a la pieza, por su lado libre, a media altura (apilados si hay dos)."""
    dere, arr = ejes_vista(vista); g = indice["piezas"][pid]["geo"]; c = Vector(g["centro"]); lado = _lado_libre(indice, pid, dere)
    ext = max((Vector(q) - c).dot(dere) * lado for q in g["puntos"])
    cen = c + dere * (lado * (ext + 0.05 + w / 2)) + vista * 0.1
    cen.z = c.z + (h + 0.03) * ((n - 1) / 2 - orden)
    return cen

def sitio_paso(indice, pid, vista):
    """Centro de la insignia de un paso del ciclo: por el lado contrario a los datos, en la parte alta de la pieza."""
    dere, arr = ejes_vista(vista); g = indice["piezas"][pid]["geo"]; c = Vector(g["centro"]); lado = -_lado_libre(indice, pid, dere)
    ext = max((Vector(q) - c).dot(dere) * lado for q in g["puntos"])
    cen = c + dere * (lado * (ext + 0.04 + R_PASO)) + vista * 0.1
    cen.z = c.z + (g["z1"] - c.z) * 0.55
    return cen

def puntos_workflow(indice, guion, vista, k):
    """Esquinas (mundo) de las insignias de la escena k, por pieza: la camara las encuadra con su pieza."""
    dere, arr = ejes_vista(vista); out = {}
    esc = guion["escenas"][k]; datos = esc.get("datos") or []
    for pid in {d["pieza"] for d in datos}:
        mios = [d for d in datos if d["pieza"] == pid]
        for i, d in enumerate(mios):
            w, h = medida_dato(d["etiqueta"], [d["valor"], d.get("hasta")]); cen = sitio_dato(indice, pid, vista, w, h, i, len(mios))
            out.setdefault(pid, []).extend(cen + dere * sx * w / 2 + Vector((0, 0, sz * h / 2)) for sx in (-1, 1) for sz in (-1, 1))
    for n_, paso in enumerate(guion.get("ciclo") or [], 1):
        if esc.get("paso") == n_ or esc.get("ciclo_rapido"):
            cen = sitio_paso(indice, paso["pieza"], vista); r = R_PASO + 0.05
            out.setdefault(paso["pieza"], []).extend(cen + dere * sx * r + Vector((0, 0, sz * r)) for sx in (-1, 1) for sz in (-1, 1))
    return out

def dibujar_dato(pin, pl, etiqueta, valor, color, w, h):
    """Panel oscuro de esquinas redondeadas con borde de color, la etiqueta arriba y el valor grande debajo."""
    o = Vector(); col = COLOR_DATO.get(color, "blanco"); rr = 0.022; esq = []
    for cx, cy, a0 in ((w / 2 - rr, -h / 2 + rr, -90), (w / 2 - rr, h / 2 - rr, 0), (-w / 2 + rr, h / 2 - rr, 90), (-w / 2 + rr, -h / 2 + rr, 180)):
        esq += [(cx + rr * math.cos(math.radians(a0 + 90 * i / 4)), cy + rr * math.sin(math.radians(a0 + 90 * i / 4))) for i in range(5)]
    pin.cara([pl(o, x, y, 0) for x, y in esq], "T plano gris_oscuro")
    pin.linea([pl(o, x, y, 1) for x, y in esq + esq[:1]], f"T trazo {col}", 0.0045)
    y_v = -h / 2 + 0.028 + H_VAL / 2
    if etiqueta:
        y_e = h / 2 - 0.022 - H_ETQ / 2
        dibujar_texto(pin, lambda x, y, k=0: pl(o, x, y_e + y, 2 + k), etiqueta.upper(), H_ETQ, w - 0.05, "blanco")
    dibujar_texto(pin, lambda x, y, k=0: pl(o, x, y_v + y, 2 + k), valor, H_VAL, w - 0.05, col)

ESTADOS_PASO = {"apagado": ("gris_oscuro", "gris", "gris"), "activo": ("lima", "blanco", "gris_oscuro"), "hecho": ("gris_oscuro", "cielo", "cielo")}

def dibujar_paso(pin, pl, n, texto, estado):
    """Insignia de un paso: circulo con su numero y la palabra debajo; apagado (gris), activo (lima) o hecho (cian)."""
    o = Vector(); fondo, borde, letra = ESTADOS_PASO[estado]; r = R_PASO * (1.18 if estado == "activo" else 1.0)
    circ = [(r * math.cos(2 * math.pi * i / 28), r * math.sin(2 * math.pi * i / 28)) for i in range(28)]
    pin.cara([pl(o, x, y, 0) for x, y in circ], f"T plano {fondo}")
    pin.linea([pl(o, x, y, 1) for x, y in circ + circ[:1]], f"T trazo {borde}", 0.005)
    dibujar_texto(pin, lambda x, y, k=0: pl(o, x, y, 2 + k), str(n), r * 0.95, r * 1.3, letra)
    if texto:
        yy = -r - 0.016 - H_PASO / 2; w = ancho_texto(texto.upper()) * H_PASO + 0.03
        caja = [(-w / 2, yy - H_PASO * 0.85), (w / 2, yy - H_PASO * 0.85), (w / 2, yy + H_PASO * 0.85), (-w / 2, yy + H_PASO * 0.85)]
        pin.cara([pl(o, x, y, 0) for x, y in caja], "T plano gris_oscuro")
        dibujar_texto(pin, lambda x, y, k=0: pl(o, x, yy + y, 2 + k), texto.upper(), H_PASO, 1.0, "lima" if estado == "activo" else letra if estado == "hecho" else "gris")

def dibujar_texto(pin, plano, texto, alto, ancho_max, color):
    """Texto relleno sobre un plano (plano(x, y, capa) -> punto), centrado, de 'alto' (o menos si no cabe en 'ancho_max'),
    con borde de tinta como los iconos: primero el contorno de cada letra (capa 0) y encima el relleno (capa 1), asi la
    tinta solo asoma por fuera y no adelgaza la letra."""
    pol, lazos = poligonos_texto(texto)
    if not pol: return
    ancho = max(abs(x) for t in pol for x, y in t) * 2
    k = min(alto, ancho_max / max(ancho, 1e-6))
    for l in lazos: pin.linea([plano(x * k, y * k, 0) for x, y in l + l[:1]], "T tinta", R_TINTA * 0.5)
    for t in pol: pin.cara([plano(x * k, y * k, 1) for x, y in t], f"T plano {color}")

def _subdiv_paso(pts, paso, n_min, cerrado=True):
    """Como _subdiv, pero cada lado en tramos de 'paso' como mucho (en una cara curva, x es longitud de arco)."""
    out = []; m = len(pts)
    for i in range(m if cerrado else m - 1):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % m]
        n = max(n_min, int(math.ceil(math.hypot(bx - ax, by - ay) / paso)))
        out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    if not cerrado: out.append(pts[-1])
    return out

def _subdiv(pts, n, cerrado=True):
    out = []; m = len(pts)
    for i in range(m if cerrado else m - 1):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % m]
        out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    if not cerrado: out.append(pts[-1])
    return out

def _cartel(sup, xc, yc, w, h, vista, poste=0.0):
    """Pie del poste (top), centro del tablero (P0), lado del tablero (s) y sus ejes de pantalla (el tablero mira a camara)."""
    top = sup(xc, yc, 0.0); s = max(0.12, min(0.3, max(w, h)))
    fwd = -vista; dere = fwd.cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(fwd).normalized()
    return top, top + Vector((0, 0, 0.05 + s * 0.55 + poste)), s, dere, arr

def puntos_cartel(p, ad, vista):
    """Muestras (mundo) del poste y del tablero de un cartel, para comprobar que no atraviesa otras piezas."""
    M = matriz_pieza(p); sup, W, H, N = cara_local(p, ad["cara"], vista, M)
    xc, yc = (ad["u"] - 0.5) * W, (ad["v"] - 0.5) * H
    top, P0, s, dere, arr = _cartel(sup, xc, yc, ad["ancho"] * W, ad["alto"] * H, vista, ad.get("poste", 0.0))
    pie = P0 - Vector((0, 0, s * 0.45))
    return ([top + (pie - top) * (i / 6) for i in range(7)] +
            [P0 + dere * (s * (i / 8 - 0.5)) + arr * (s * (j / 8 - 0.5)) for i in range(9) for j in range(9)])

def recolocar_carteles(piezas, adornos, vista, margen=0.008):
    """Un cartel encima de una pieza no puede atravesar otras (fichas apiladas, bloques que se posan): si choca, busca
    sobre la misma cara el sitio libre mas cercano y, si no hay, alarga el poste; si nada vale, lo quita. Cambia 'adornos'."""
    cajas = {}; puntos = {}
    for q in piezas:
        if q["forma"] in ("manguera",) or (q["forma"] == "malla" and "_malla" not in q): continue
        try: pts = geometria(q)["puntos"]
        except Exception: continue
        puntos[q["id"]] = pts
        cajas[q["id"]] = ([min(v[i] for v in pts) - margen for i in range(3)], [max(v[i] for v in pts) + margen for i in range(3)])
    por_id = {q["id"]: q for q in piezas}
    fwd = -vista; dere = fwd.cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(fwd).normalized()
    def pantalla(v): v = Vector(v); return v.dot(dere), v.dot(arr)
    def encima(pid):
        """Silueta en pantalla (caja 2D) de lo que se posa encima de la pieza: el cartel no debe taparlo."""
        if pid not in cajas: return {}
        (lo_h, hi_h) = cajas[pid]; out = {}
        for qid, (lo, hi) in cajas.items():
            if qid == pid or lo[2] < hi_h[2] - 0.03: continue
            if lo[0] > hi_h[0] or hi[0] < lo_h[0] or lo[1] > hi_h[1] or hi[1] < lo_h[1]: continue
            xy = [pantalla(v) for v in puntos[qid]]
            out[qid] = (min(a for a, b in xy) - 0.01, max(a for a, b in xy) + 0.01, min(b for a, b in xy) - 0.01, max(b for a, b in xy) + 0.01)
        return out
    def choque(p, ad):
        pts = puntos_cartel(p, ad, vista)
        for qid, (lo, hi) in cajas.items():
            if qid == p["id"]: continue
            if any(all(lo[i] <= v[i] <= hi[i] for i in range(3)) for v in pts): return qid
        tablero = [pantalla(v) for v in pts[7:]]
        x0, x1 = min(a for a, b in tablero), max(a for a, b in tablero); y0, y1 = min(b for a, b in tablero), max(b for a, b in tablero)
        for qid, (a0, a1, b0, b1) in sombras.items():
            if x0 < a1 and x1 > a0 and y0 < b1 and y1 > b0: return qid + " (lo tapa)"
        return None
    for pid, lista in adornos.items():
        p = por_id.get(pid)
        if not p: continue
        sombras = encima(pid)
        for ad in list(lista):
            if ad.get("tipo") != "cartel" or ad.get("cara") != "arriba": continue
            qid = choque(p, ad)
            if not qid: continue
            u0, v0 = ad["u"], ad["v"]; mejor = None
            M = matriz_pieza(p); sup, W, H, N = cara_local(p, "arriba", vista, M)
            for poste in (0.0, 0.06, 0.12, 0.18, 0.24, 0.3):
                cands = sorted(((u0 + du, v0 + dv) for du in (0, 0.2, -0.2, 0.3, -0.3, 0.42, -0.42) for dv in (0, 0.2, -0.2, 0.3, -0.3)),
                               key=lambda c: math.hypot(c[0] - u0, c[1] - v0))
                for u, v in cands:
                    x, y = (u - 0.5) * W, (v - 0.5) * H
                    if p["forma"] in ("caja", "panel", "peana"):
                        if abs(x) > W * 0.45 or abs(y) > H * 0.45: continue
                    elif math.hypot(x, y) > p.get("radio", W / 2) * 0.85: continue
                    if not choque(p, dict(ad, u=u, v=v, poste=poste)): mejor = (u, v, poste); break
                if mejor: break
            if mejor:
                ad.update(u=mejor[0], v=mejor[1], poste=mejor[2])
                AVISOS_ADORNOS.append(f"{pid}: el cartel chocaba con {qid}; movido a u={mejor[0]:.2f} v={mejor[1]:.2f}" + (f", poste +{mejor[2]:.2f} m" if mejor[2] else ""))
            else:
                lista.remove(ad); AVISOS_ADORNOS.append(f"{pid}: el cartel chocaba con {qid} y no hay sitio libre; se quita")

def dibujar_adornos(p, M, pin, vista, color_pieza):
    """Dibuja los adornos de la pieza; devuelve puntos extra (mundo) que sobresalen de ella (carteles) para encuadre y efectos."""
    f = p["forma"]; extra = []
    if f == "cerebro": surcos_cerebro(p, M, pin)
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
        curva = n_sub > 1
        def _nor(x, y, d=0.002):
            n = (sup(x + d, y, 0.0) - sup(x - d, y, 0.0)).cross(sup(x, y + d, 0.0) - sup(x, y - d, 0.0))
            return n.normalized() if n.length > 1e-9 else Vector(N)
        def _trazo(xy, eps):              # con la normal de la cara (planas y curvas): la cinta va pegada a la superficie
            out = _Trazo(sup(x, y, eps) for x, y in xy)
            out.normales = [_nor(x, y) for x, y in xy]
            return out
        def P(pts, eps, cerrado=True): return _trazo(_subdiv_paso(pts, 0.02, n_sub, cerrado) if curva else pts, eps)
        def R(a0, b0, a1, b1, eps):
            pts = P(_rect(a0, b0, a1, b1), eps)
            if curva:                  # cara curva: rejilla de cuadrilateros para la malla (tramos de 2 cm como mucho)
                nx = max(1, int(math.ceil(abs(a1 - a0) / 0.02))); ny = max(1, int(math.ceil(abs(b1 - b0) / 0.03)))
                r_ = _Rejilla(pts); r_.normales = pts.normales
                r_.rejilla = [[sup(a0 + (a1 - a0) * i / nx, b0 + (b1 - b0) * j / ny, eps) for i in range(nx + 1)] for j in range(ny + 1)]
                pts = r_
            return pts
        def borde(pts, eps, nombre="T tinta", rad=R_TINTA * 0.7): pin.linea(_cerrar(pts), nombre, rad)
        def circ(cx, cy, rr, eps, n=14): return _trazo([(cx + rr * math.cos(2 * math.pi * i / n), cy + rr * math.sin(2 * math.pi * i / n)) for i in range(n)], eps)
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
                # el halo translucido imita el brillo en GP; en malla queda como un borde borroso: icono nitido
                dibujar_icono(pin, sup, ad["icono"], (sx0 + sx1) / 2, (sy0 + sy1) / 2, min(sw, sh) * 0.8, c, e3, tinta=not oscura,
                              halo=oscura and not TEMA.get("mallas"))
            else:
                for i, L in enumerate((0.8, 0.5, 0.65, 0.35)[:max(2, min(4, int(sh / max(sw, 1e-6) * 6) + 2))]):
                    y = sy1 - sh * (0.2 + 0.22 * i)
                    if y < sy0 + sh * 0.1: break
                    seg = [(sx0 + sw * 0.1, y), (sx0 + sw * (0.1 + L), y)]
                    if oscura and not TEMA.get("mallas"): pin.linea(P(seg, e3 - 0.0015, False), f"T trazo {c} 0.3", lw * 2.4)
                    else: pin.linea(P(seg, e3 - 0.0015, False), "T tinta", lw * 1.6)
                    pin.linea(P(seg, e3, False), f"T trazo {c}", lw)
        elif t in ("leds", "ranuras"):
            n = max(1, ad.get("cantidad") or 3)
            if t == "leds":
                hor = w >= h; rr = min(h * 0.32, w / n * 0.3) if hor else min(w * 0.32, h / n * 0.3)
                for i in range(n):
                    cx = x0 + w * (i + 0.5) / n if hor else xc; cy = yc if hor else y0 + h * (i + 0.5) / n
                    if not TEMA.get("mallas"): pin.cara(circ(cx, cy, rr * 2.0, e0), f"T plano {c} 0.3")   # brillo (GP)
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
                    if not TEMA.get("mallas"): pin.cara(circ(cx, cy, rr * 2.0, e1), f"T plano {c} 0.3")
                    pin.cara(circ(cx, cy, rr, e2), f"T plano {c}")
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
            if t == "placa":                  # panel de servicio: placa, ranuras de ventilacion y tornillos que se vean
                pl = R(x0, y0, x1, y1, e0); pin.cara(pl, f"T {c} b1"); borde(pl, e1)
                for i in (-1, 0, 1):
                    yy = yc + i * h * 0.16
                    pin.linea(P([(x0 + w * 0.26, yy), (x1 - w * 0.26, yy)], e1, False), "T tinta", max(R_TINTA * 0.6, lw * 0.9))
            rr = max(0.007, min(0.022, min(w, h) * (0.09 if t == "placa" else 0.07))); k = rr * 1.8
            for cx, cy in ((x0 + k, y0 + k), (x1 - k, y0 + k), (x1 - k, y1 - k), (x0 + k, y1 - k)):
                tor = circ(cx, cy, rr, e2, 10); pin.cara(tor, "T metal b1"); borde(tor, e2, "T tinta fina", R_TINTA * 0.45)
                pin.linea([sup(cx - rr * 0.6, cy - rr * 0.6, e3), sup(cx + rr * 0.6, cy + rr * 0.6, e3)], "T tinta fina", R_TINTA * 0.4)
        elif t == "barras":                   # indicador LED: barras de color plano, con un borde fino (no se las come la tinta)
            nb = max(1, min(6, int(ad.get("cantidad", 3)))); paso = h / (nb * 3 + 1)
            for i in range(nb):
                b0 = y0 + paso + i * 3 * paso
                barra = R(x0, b0, x1, b0 + 2 * paso, e1); pin.cara(barra, f"T plano {c}"); borde(barra, e1, "T tinta fina", R_TINTA * 0.3)
        elif t == "franja":
            if curva and f in ("tubo", "cilindro") and p["material"] in ("transparente", "liquido") and ad["ancho"] >= 0.95:
                x0, x1 = -math.pi * p["radio"], math.pi * p["radio"]       # se ve por detras: la franja da la vuelta entera
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
            top, P0, s, dere, arr = _cartel(sup, xc, yc, w, h, vista, ad.get("poste", 0.0))
            pin.linea([top, P0 - Vector((0, 0, s * 0.45))], "T tinta", 0.008 + R_TINTA * 0.5)
            pin.linea([q + vista * 0.0012 for q in (top, P0 - Vector((0, 0, s * 0.45)))], "T trazo gris", 0.008)   # encima de su tinta
            def bill(x, y, eps=0.0): return P0 + dere * x + arr * y + vista * eps
            rr = s * 0.12; esq = []
            for (cx, cy, a0) in ((s / 2 - rr, -s / 2 + rr, -90), (s / 2 - rr, s / 2 - rr, 0), (-s / 2 + rr, s / 2 - rr, 90), (-s / 2 + rr, -s / 2 + rr, 180)):
                esq += [bill(cx + rr * math.cos(math.radians(a0 + 90 * i / 4)), cy + rr * math.sin(math.radians(a0 + 90 * i / 4))) for i in range(5)]
            pin.cara(esq, "T blanco_hueso b0"); pin.linea(esq + esq[:1], "T tinta", R_TINTA * 0.9); extra += esq[::5]
            if ad.get("texto"):                      # sigla (LLM, API...) en lugar del icono
                dibujar_texto(pin, lambda x, y, k=0: bill(x, y, 0.004 + 0.003 * k), ad["texto"], s * 0.36, s * 0.8, c)
            else:
                dibujar_icono(pin, bill, ad.get("icono") or "lambda", 0, 0, s * 0.7, c, 0.004)
    return extra
