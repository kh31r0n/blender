# Utilidades comunes de Grease Pencil (Blender 5.2) para el agente de comic.
# - Materiales por receta ("Relleno rojo", "Semitono azul", "Tinta"...), identicos a los de biblioteca/Materiales_GP.blend
# - Lapiz: anade trazos y rellenos a un dibujo (fill_id != 0 para rellenar; mismo fill_id = agujeros)
# - Formas planas en el plano XZ local, cajas 3D, texto -> trazos (fuentes descargadas)
# - Curvas de animacion con la API de acciones por ranuras (channelbags) de Blender 5
import bpy, json, math, os, random, sys, warnings
import mathutils
from mathutils import Vector, Matrix

warnings.filterwarnings("ignore", category=DeprecationWarning)   # show_stroke/show_fill: se quitan en Blender 6
AQUI = os.path.dirname(os.path.abspath(__file__))
COMIC = os.path.dirname(AQUI)
if COMIC not in sys.path: sys.path.insert(0, COMIC)
import comic_parametros as CP

TEXTURAS = os.path.join(CP.BIBLIOTECA, "texturas")
CFG = {"saturacion": 1.1, "grosor_tinta": 1.0, "semitono": True, "papel": True, "brillo_fx": True,
       "temblor_linea": 0.4, "formato": "3d"}
R_TINTA = 0.022        # radio base de la tinta (unidades de mundo); se multiplica por grosor_tinta

def configurar(params):
    CFG.update({k: params[k] for k in CFG if k in params})

# ---------------------------------------------------------------- argumentos de los scripts (-- --clave valor)
def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, k = {}, None
    for a in argv:
        if a.startswith("--"):
            k = a[2:].replace("-", "_"); out[k] = True
        elif k:
            out[k] = a if out[k] is True else (out[k] + [a] if isinstance(out[k], list) else [out[k], a])
    return out

def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f: return json.load(f)

def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f: json.dump(datos, f, indent=2, ensure_ascii=False)

def proyecto(dir_):
    p = leer_json(os.path.join(dir_, "proyecto.json"))
    params, _ = CP.limitar_params(p.get("parametros"))
    configurar(params)
    return p, params

def guardar(ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True, check_existing=False)
    print(f"GUARDADO {ruta}")

# ---------------------------------------------------------------- colores
def col(nombre, alfa=1.0, valor=1.0, sat=1.0):
    return CP.color_lineal(nombre or "magenta", alfa, valor, sat * CFG["saturacion"])

def colt(token, alfa=1.0):
    """Color por nombre con sufijo opcional: 'azul+' (claro), 'azul-' (oscuro), 'azul--' (muy oscuro)."""
    t = token.strip()
    if t.endswith("--"): return col(t[:-2], alfa, valor=0.5, sat=1.1)
    if t.endswith("-"): return col(t[:-1], alfa, valor=0.72, sat=1.08)
    if t.endswith("++"): return col(t[:-2], alfa, valor=1.5, sat=0.45)
    if t.endswith("+"): return col(t[:-1], alfa, valor=1.25, sat=0.72)
    return col(t, alfa)

def oscuro(nombre, f=0.72, alfa=1.0): return col(nombre, alfa, valor=f, sat=1.08)
def claro(nombre, f=1.25, alfa=1.0): return col(nombre, alfa, valor=f, sat=0.75)
TINTA_RGBA = CP.color_lineal(CP.TINTA)

# ---------------------------------------------------------------- imagenes de la biblioteca
def imagen(nombre):
    """Textura de biblioteca/texturas (creada por el modo materiales). Si falta, la genera (semitonos)."""
    if nombre in bpy.data.images: return bpy.data.images[nombre]
    ruta = os.path.join(TEXTURAS, nombre + ".png")
    if not os.path.exists(ruta): ruta = os.path.join(TEXTURAS, nombre + ".jpg")
    if os.path.exists(ruta):
        img = bpy.data.images.load(ruta, check_existing=True); img.name = nombre; return img
    if nombre.startswith("semitono") or nombre.startswith("puntos"):
        return generar_trama(nombre)
    return None

def generar_trama(nombre, n=512, celda=32, radio=0.36, rgb=(0, 0, 0), alfa=0.33, guardar_en=None):
    """Trama de puntos Ben-Day en una imagen RGBA (puntos de color con alfa, fondo transparente)."""
    import numpy as np
    presets = {"semitono_oscuro": ((0, 0, 0), 0.30, 0.36), "semitono_claro": ((1, 1, 1), 0.55, 0.30),
               "puntos_blancos": ((1, 1, 1), 0.85, 0.22), "semitono_denso": ((0, 0, 0), 0.38, 0.45)}
    if nombre in presets: rgb, alfa, radio = presets[nombre]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    # red al tresbolillo (puntos a 45 grados, como en la imprenta) que encaja sin costuras al repetirse
    def dist(ox):
        cu = ((xx + ox) % celda) - celda / 2; cv = ((yy + ox) % celda) - celda / 2
        return np.sqrt(cu ** 2 + cv ** 2) / celda
    d = np.minimum(dist(0.0), dist(celda / 2))
    a = np.clip((radio - d) * celda * 1.2 + 0.5, 0, 1) * alfa
    px = np.zeros((n, n, 4), np.float32); px[..., 0], px[..., 1], px[..., 2] = rgb; px[..., 3] = a
    tmp = bpy.data.images.new(nombre + "_tmp", n, n, alpha=True)
    tmp.pixels.foreach_set(px.ravel())
    # una imagen generada y empaquetada pierde los pixeles: se guarda en PNG y se carga desde el archivo
    ruta = guardar_en or os.path.join(TEXTURAS, nombre + ".png")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp.filepath_raw = ruta; tmp.file_format = 'PNG'; tmp.save()
    bpy.data.images.remove(tmp)
    img = bpy.data.images.load(ruta, check_existing=True); img.name = nombre
    return img

# ---------------------------------------------------------------- materiales por receta
def _gp_mat(nombre):
    m = bpy.data.materials.get(nombre)
    if m and m.grease_pencil: return m, False
    m = bpy.data.materials.new(nombre); bpy.data.materials.create_gpencil_data(m)
    return m, True

def material(nombre):
    """Recetas: 'Tinta', 'Tinta blanca', 'Relleno <color>', 'Plano <color>', 'Trazo <color>', 'Semitono <color>',
    'Semitono plano <color>', 'Cielo puntos <color>', 'Sombra', 'Brillo', 'Papel', 'Carton', 'Agujero'."""
    m, nuevo = _gp_mat(nombre)
    if not nuevo: return m
    g = m.grease_pencil
    g.show_stroke, g.show_fill = True, False
    g.color = TINTA_RGBA
    partes = nombre.split(" ")
    base, color = partes[0], " ".join(partes[1:])
    if nombre == "Tinta":
        pass
    elif nombre == "Tinta blanca":
        g.color = (1, 1, 1, 1)
    elif base == "Trazo":
        g.color = colt(color)
    elif base == "Relleno":
        g.show_fill = True; g.fill_color = colt(color)
    elif base == "Plano":
        g.show_stroke = False; g.show_fill = True; g.fill_color = colt(color)
    elif base == "Translucido":
        g.show_stroke = False; g.show_fill = True; g.fill_color = colt(color, 0.45)
    elif nombre.startswith("Semitono plano "):
        c = nombre[len("Semitono plano "):]
        g.show_stroke = False; _relleno_trama(g, colt(c), "semitono_oscuro", 9)
    elif base == "Semitono":
        _relleno_trama(g, colt(color), "semitono_oscuro", 9)
    elif nombre.startswith("Cielo puntos "):
        c = nombre[len("Cielo puntos "):]
        g.show_stroke = False; _relleno_trama(g, colt(c), "puntos_blancos", 4)
    elif nombre == "Sombra":
        g.show_stroke = False; g.show_fill = True; g.fill_color = (0.02, 0.0, 0.08, 0.30)
    elif nombre == "Brillo":
        g.show_stroke = False; g.show_fill = True; g.fill_color = (1, 1, 1, 0.75)
    elif nombre == "Papel":
        g.show_stroke = False; img = imagen("papel")
        if img: g.show_fill = True; g.fill_style = 'TEXTURE'; g.fill_image = img; g.texture_scale = (1, 1); g.fill_color = (1, 1, 1, 1)
        else: g.show_fill = True; g.fill_color = col("crema")
    elif nombre == "Carton":
        img = imagen("carton"); g.show_fill = True
        if img: g.fill_style = 'TEXTURE'; g.fill_image = img; g.texture_scale = (1.5, 1.5)
        else: g.fill_color = col("marron", valor=1.2)
    elif nombre == "Agujero":   # recorta lo que hay debajo dentro del mismo objeto
        g.show_stroke = False; g.show_fill = True; g.use_fill_holdout = True; g.fill_color = (0, 0, 0, 1)
    else:
        g.show_fill = True; g.fill_color = col("magenta")
    return m

def _relleno_trama(g, color, trama, escala):
    g.show_fill = True; g.fill_color = color; g.mix_color = color   # la textura se compone sobre mix_color
    if not CFG.get("semitono", True): return
    img = imagen(trama)
    if img:
        g.fill_style = 'TEXTURE'; g.fill_image = img; g.mix_factor = 0.0; g.texture_scale = (escala, escala)

# ---------------------------------------------------------------- objetos y capas
def coleccion(nombre, padre=None):
    c = bpy.data.collections.get(nombre)
    if not c:
        c = bpy.data.collections.new(nombre)
        (padre or bpy.context.scene.collection).children.link(c)
    return c

def nuevo_gp(nombre, col_=None, profundidad3d=False):
    gp = bpy.data.grease_pencils.new(nombre)
    gp.stroke_depth_order = '3D' if profundidad3d else '2D'
    ob = bpy.data.objects.new(nombre, gp)
    (col_ or bpy.context.scene.collection).objects.link(ob)
    return ob

class Lapiz:
    """Dibuja en una capa (un fotograma) de un objeto Grease Pencil."""
    _fill = {}

    def __init__(self, ob, capa="Tinta", frame=0, grupo=None, nueva=False):
        self.ob = ob; gp = ob.data
        L = gp.layers.get(capa) if not nueva else None
        if L is None:
            grp = None
            if grupo:
                grp = next((g for g in gp.layer_groups if g.name == grupo), None) or gp.layer_groups.new(grupo)
            L = gp.layers.new(capa, set_active=True, layer_group=grp)
            L.use_lights = False
        self.capa = L
        fr = next((f for f in L.frames if f.frame_number == frame), None)
        self.frame = fr or L.frames.new(frame)
        self.d = self.frame.drawing
        self.k = (ob.name, L.name, frame)

    def _mat(self, nombre):
        mats = self.ob.data.materials
        for i, m in enumerate(mats):
            if m and m.name == nombre: return i
        mats.append(material(nombre)); return len(mats) - 1

    def _fid(self):
        Lapiz._fill[self.k] = Lapiz._fill.get(self.k, 0) + 1
        return Lapiz._fill[self.k]

    def trazo(self, pts, mat="Tinta", radio=None, cerrado=False, relleno=False, fid=None, radios=None,
              opacidad=1.0, afilar=False, temblor=0.0, semilla=0, cap_redonda=True):
        pts = [Vector(p) for p in pts]
        if len(pts) < 2: return None
        if temblor > 0:
            rnd = random.Random(semilla)
            pts = [p + Vector((rnd.uniform(-1, 1), 0, rnd.uniform(-1, 1))) * temblor for p in pts]
        n0 = len(self.d.strokes); self.d.add_strokes([len(pts)]); st = self.d.strokes[n0]
        st.cyclic = cerrado; st.material_index = self._mat(mat)
        if relleno: st.fill_id = fid if fid else self._fid()
        r = (R_TINTA if radio is None else radio) * CFG["grosor_tinta"]
        n = len(pts)
        for i, (p, co) in enumerate(zip(st.points, pts)):
            p.position = co; p.opacity = opacidad
            if radios is not None: p.radius = radios[i] * CFG["grosor_tinta"]
            elif afilar and n > 2: p.radius = r * (0.25 + 0.75 * math.sin(math.pi * i / (n - 1)) ** 0.7)
            else: p.radius = r
        return st

    def forma(self, pts, mat, radio=None, linea=True, fid=None, **kw):
        """Forma cerrada rellena: material con relleno y trazo de tinta (si el material lo muestra).
        Las tramas ('Semitono X', 'Cielo puntos X') son transparentes entre puntos: se pone su color debajo.
        ('Semitono plano X' es solo la trama, para superponer a una forma ya dibujada.)"""
        for pre in ("Semitono ", "Cielo puntos "):
            if mat.startswith(pre) and not mat.startswith("Semitono plano ") and CFG.get("semitono", True):
                self.trazo(pts, "Plano " + mat[len(pre):], radio=0.0005, cerrado=True, relleno=True, **kw)
        return self.trazo(pts, mat, radio=radio if linea else 0.0005, cerrado=True, relleno=True, fid=fid, **kw)

    def linea(self, pts, mat="Tinta", radio=None, **kw):
        return self.trazo(pts, mat, radio=radio, cerrado=False, **kw)

    def texto(self, texto, fuente=None, tam=1.0, centro=(0, 0, 0), mat="Relleno amarillo", radio=None,
              alinear="CENTER", plano="XZ", interlineado=1.0):
        """Texto como trazos rellenos (contornos de la fuente, con agujeros). Devuelve (ancho, alto)."""
        conts, (w, h) = contornos_texto(texto, fuente, tam, alinear, interlineado)
        cx, cy, cz = centro
        grupos = {}
        for c, gid in conts:
            if gid not in grupos: grupos[gid] = self._fid()
            if plano == "XZ": pts = [(cx + x, cy, cz + y) for x, y in c]
            else: pts = [(cx + x, cy + y, cz) for x, y in c]
            self.trazo(pts, mat, radio=radio, cerrado=True, relleno=True, fid=grupos[gid])
        return w, h

def capa_padre(L, rig, hueso=""):
    L.parent = rig
    if hueso: L.parent_bone = hueso

# ---------------------------------------------------------------- formas (en el plano XZ local, y fijo)
def P(x, z, y=0.0): return (x, y, z)

def circulo(cx, cz, r, n=40, y=0.0, a0=0.0):
    return [P(cx + r * math.cos(a0 + 2 * math.pi * i / n), cz + r * math.sin(a0 + 2 * math.pi * i / n), y) for i in range(n)]

def elipse(cx, cz, rx, rz, n=40, y=0.0, giro=0.0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n; x, z = rx * math.cos(a), rz * math.sin(a)
        out.append(P(cx + x * math.cos(giro) - z * math.sin(giro), cz + x * math.sin(giro) + z * math.cos(giro), y))
    return out

def rect(x0, z0, x1, z1, y=0.0):
    return [P(x0, z0, y), P(x1, z0, y), P(x1, z1, y), P(x0, z1, y)]

def rect_redondeado(x0, z0, x1, z1, r, y=0.0, n=6):
    r = min(r, (x1 - x0) / 2, (z1 - z0) / 2); out = []
    for (cx, cz, a0) in [(x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)]:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); out.append(P(cx + r * math.cos(a), cz + r * math.sin(a), y))
    return out

def poligono(pts2, y=0.0): return [P(x, z, y) for x, z in pts2]

def suave(pts2, n=6, y=0.0, cerrado=True):
    """Curva Catmull-Rom por los puntos (x, z): formas organicas a partir de pocos puntos de control."""
    m = len(pts2); out = []
    rng = range(m) if cerrado else range(m - 1)
    for i in rng:
        p0 = pts2[(i - 1) % m] if cerrado or i > 0 else pts2[0]
        p1 = pts2[i]; p2 = pts2[(i + 1) % m]
        p3 = pts2[(i + 2) % m] if cerrado or i + 2 < m else pts2[-1]
        for j in range(n):
            t = j / n; t2, t3 = t * t, t * t * t
            out.append(P(*(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                           for a, b, c, d in zip(p0, p1, p2, p3)), y))
    if not cerrado: out.append(P(*pts2[-1], y))
    return out

def estrella(cx, cz, r1, r2, n=5, y=0.0, a0=math.pi / 2, irregular=0.0, semilla=0):
    rnd = random.Random(semilla); out = []
    for i in range(2 * n):
        r = (r1 if i % 2 == 0 else r2) * (1 + rnd.uniform(-irregular, irregular))
        a = a0 + math.pi * i / n; out.append(P(cx + r * math.cos(a), cz + r * math.sin(a), y))
    return out

def capsula(x0, z0, x1, z1, r0, r1=None, y=0.0, n=8):
    """Contorno de un segmento grueso con extremos redondos (brazos, piernas)."""
    r1 = r0 if r1 is None else r1
    dx, dz = x1 - x0, z1 - z0; L = math.hypot(dx, dz) or 1e-6; ang = math.atan2(dz, dx)
    out = []
    for i in range(n + 1):   # extremo final
        a = ang - math.pi / 2 + math.pi * i / n; out.append(P(x1 + r1 * math.cos(a), z1 + r1 * math.sin(a), y))
    for i in range(n + 1):   # extremo inicial
        a = ang + math.pi / 2 + math.pi * i / n; out.append(P(x0 + r0 * math.cos(a), z0 + r0 * math.sin(a), y))
    return out

def bezier(p0, p1, p2, p3, n=16):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3)))
    return out

def arco(cx, cz, r, a0, a1, n=16, y=0.0):
    return [P(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), y)
            for i in range(n + 1)]

def nube(cx, cz, w, h, bultos=5, y=0.0, semilla=0, n=10):
    """Contorno festoneado de nube/copa: arcos de circulo sobre una elipse."""
    rnd = random.Random(semilla); out = []
    k = bultos * 2 + 2
    angs = [2 * math.pi * i / k for i in range(k)]
    for i in range(k):
        a0, a1 = angs[i], angs[(i + 1) % k] + (2 * math.pi if i == k - 1 else 0)
        am = (a0 + a1) / 2
        rb = (1 + rnd.uniform(-0.12, 0.18))
        bx, bz = cx + w / 2 * math.cos(am) * 0.82, cz + h / 2 * math.sin(am) * 0.78
        ra = (w + h) / 2 * math.pi / k * 0.62 * rb
        for j in range(n):
            t = j / n; a = am - math.pi / 2 - 0.4 + (math.pi + 0.8) * t
            out.append(P(bx + ra * math.cos(a), bz + ra * math.sin(a) * (h / w) ** 0.3, y))
    return out

def transformar(pts, m):
    return [tuple(m @ Vector(p)) for p in pts]

# ---------------------------------------------------------------- 3D: cajas de trazos
def caja(lp, x0, x1, y0, y1, z0, z1, mat_frente, mat_lado=None, mat_techo=None, radio=None, caras="FLTDIA"):
    """Caja con caras rellenas. caras: F frente(-Y) L izq(-X) D der(+X) T techo A atras I (sin suelo)."""
    ml, mt = mat_lado or mat_frente, mat_techo or mat_frente
    defs = {"F": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], mat_frente),
            "A": ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], mat_frente),
            "L": ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], ml),
            "D": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], ml),
            "T": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], mt)}
    for c in caras:
        if c in defs: lp.forma(defs[c][0], defs[c][1], radio=radio)

def cara_rect(lp, cara, u0, v0, u1, v1, caja_, mat, radio=None, sep=0.012, redondeo=0.0):
    """Rectangulo (ventana, puerta) sobre una cara de una caja. u, v en coordenadas absolutas de esa cara."""
    x0, x1, y0, y1, z0, z1 = caja_
    if redondeo > 0: base = rect_redondeado(u0, v0, u1, v1, redondeo)
    else: base = rect(u0, v0, u1, v1)
    if cara == "F": pts = [(x, y0 - sep, z) for x, _, z in base]
    elif cara == "A": pts = [(x, y1 + sep, z) for x, _, z in base]
    elif cara == "L": pts = [(x0 - sep, x, z) for x, _, z in base]
    elif cara == "D": pts = [(x1 + sep, x, z) for x, _, z in base]
    else: pts = [(x, z, z1 + sep) for x, _, z in base]
    lp.forma(pts, mat, radio=radio)

# ---------------------------------------------------------------- texto -> contornos
_cache_fuentes = {}
def fuente(ruta):
    if not ruta or not os.path.exists(ruta): return None
    if ruta not in _cache_fuentes: _cache_fuentes[ruta] = bpy.data.fonts.load(ruta, check_existing=True)
    return _cache_fuentes[ruta]

def contornos_texto(texto, ruta_fuente=None, tam=1.0, alinear="CENTER", interlineado=1.0, pasos=5):
    """Contornos 2D (x, y) del texto centrados en (0,0) y agrupados para el relleno con agujeros."""
    tc = bpy.data.curves.new("_tmp_texto", 'FONT'); tc.body = texto; tc.size = tam
    tc.align_x = alinear; tc.align_y = 'CENTER'; tc.space_line = interlineado
    f = fuente(ruta_fuente or CP.FUENTE_TITULOS)
    if f: tc.font = f
    ob = bpy.data.objects.new("_tmp_texto", tc); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    cu = ev.to_curve(dg)
    conts = []
    for sp in cu.splines:
        pts = []
        if sp.type == 'BEZIER':
            bps = sp.bezier_points; n = len(bps)
            for i in range(n):
                a, b = bps[i], bps[(i + 1) % n]
                P4 = [a.co, a.handle_right, b.handle_left, b.co]
                for j in range(pasos):
                    t = j / pasos; u = 1 - t
                    q = u ** 3 * P4[0] + 3 * u * u * t * P4[1] + 3 * u * t * t * P4[2] + t ** 3 * P4[3]
                    pts.append((q.x, q.y))
        else:
            pts = [(p.co.x, p.co.y) for p in sp.points]
        if len(pts) >= 3: conts.append(pts)
    ev.to_curve_clear()
    bpy.data.objects.remove(ob); bpy.data.curves.remove(tc)
    if not conts: return [], (0, 0)
    xs = [x for c in conts for x, _ in c]; ys = [y for c in conts for _, y in c]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    conts = [[(x - mx, y - my) for x, y in c] for c in conts]
    # agrupacion por anidamiento: profundidad par = contorno exterior (nuevo grupo), impar = agujero del padre
    def dentro(pt, poly):
        x, y = pt; c = False
        for i in range(len(poly)):
            (ax, ay), (bx, by) = poly[i], poly[i - 1]
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay + 1e-12) + ax: c = not c
        return c
    prof = [sum(dentro(c[0], o) for j, o in enumerate(conts) if j != i) for i, c in enumerate(conts)]
    grupo = [None] * len(conts); g = 0
    for i in sorted(range(len(conts)), key=lambda i: prof[i]):
        if prof[i] % 2 == 0: grupo[i] = g; g += 1
        else:
            padres = [j for j in range(len(conts)) if prof[j] == prof[i] - 1 and dentro(conts[i][0], conts[j])]
            grupo[i] = grupo[padres[0]] if padres else (g := g + 1)
    return list(zip(conts, grupo)), (max(xs) - min(xs), max(ys) - min(ys))

# ---------------------------------------------------------------- modificadores y efectos
def temblor_linea(ob, factor=None, paso=3, semilla=0):
    f = CFG["temblor_linea"] if factor is None else factor
    if f <= 0: return None
    m = ob.modifiers.new("Temblor de linea", 'GREASE_PENCIL_NOISE')
    m.factor = 0.012 * f; m.factor_strength = 0.0; m.factor_thickness = 0.25 * f; m.factor_uvs = 0.0
    m.noise_scale = 0.35; m.step = paso; m.use_random = True; m.seed = semilla
    return m

def brillo(ob, color=(1, 0.9, 0.2), tam=40, umbral=0.0):
    if not CFG.get("brillo_fx", True): return None
    fx = ob.shader_effects.new("Brillo", 'FX_GLOW')
    fx.mode = 'COLOR'; fx.select_color = (1, 1, 1); fx.threshold = 0.9; fx.glow_color = color[:3]
    fx.size = (tam, tam); fx.samples = 12; fx.use_glow_under = True; fx.opacity = 0.9
    return fx

# ---------------------------------------------------------------- animacion (acciones por ranuras, Blender 5)
from bpy_extras import anim_utils

def channelbag(id_, nombre=None):
    ad = id_.animation_data or id_.animation_data_create()
    if ad.action is None:
        ad.action = bpy.data.actions.new(nombre or f"{id_.name}_accion")
    if ad.action_slot is None:
        slot = ad.action.slots.new(id_type=id_.id_type, name=id_.name); ad.action_slot = slot
    return anim_utils.action_ensure_channelbag_for_slot(ad.action, ad.action_slot)

INTERP = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}

def curva(id_, ruta, indice, claves, interp="CONSTANT", reemplazar=True, grupo=None):
    """claves: [(frame, valor)] o [(frame, valor, interpolacion)]. Crea/reemplaza la F-curve en bloque."""
    if not claves: return None
    cb = channelbag(id_)
    fc = cb.fcurves.find(ruta, index=indice)
    if fc and reemplazar: cb.fcurves.remove(fc); fc = None
    if fc is None:
        fc = cb.fcurves.new(ruta, index=indice)
        if grupo:
            g = cb.groups.get(grupo) or cb.groups.new(grupo); fc.group = g
    norm = {}
    for c in claves:
        norm[float(c[0])] = (float(c[1]), c[2] if len(c) > 2 else interp)
    kp = fc.keyframe_points; n0 = len(kp); kp.add(len(norm))
    for i, (f, (v, it)) in enumerate(sorted(norm.items())):
        k = kp[n0 + i]; k.co = (f, v); k.interpolation = it
        k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
    fc.update()
    return fc

def simplificar(claves, tol=1e-4):
    """Quita claves repetidas consecutivas (para interpolacion constante)."""
    out = []
    for f, v in sorted(claves):
        if out and abs(out[-1][1] - v) < tol: continue
        out.append((f, v))
    return out

# ---------------------------------------------------------------- escena
def configurar_escena(params, sc=None):
    sc = sc or bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
    w, h, pct = CP.resolucion(params)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, pct
    sc.render.fps = int(params.get("fps", 24)); sc.render.fps_base = 1.0
    sc.grease_pencil_settings.antialias_threshold_render = 0.5
    sc.grease_pencil_settings.aa_samples = 8
    sc.eevee.taa_render_samples = 16
    sc.render.film_transparent = False
    if not sc.world:
        sc.world = bpy.data.worlds.new("Comic")
    bg = sc.world.node_tree.nodes.get("Background") if sc.world.node_tree else None
    if bg: bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 1.0
    sc["comic_parametros"] = json.dumps(params)
    return sc

def limpiar_escena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for a in ("Brillo",): pass

def dimension_mayor_visible(cam, distancia=None):
    """Extension visible de la dimension mayor del encuadre (ortografica u horizontal en perspectiva)."""
    if cam.data.type == 'ORTHO': return cam.data.ortho_scale
    return distancia * cam.data.sensor_width / cam.data.lens

def alto_visible_a_param(alto, params, cam_data, distancia=None):
    """Convierte un alto visible deseado en ortho_scale (ORTHO) o en distancia (PERSP)."""
    w, h, _ = CP.resolucion(params)
    mayor = alto if h >= w else alto * w / h
    if cam_data.type == 'ORTHO': return mayor
    return mayor * cam_data.lens / cam_data.sensor_width   # distancia

def render_fotograma(ruta, frame=None, sc=None):
    sc = sc or bpy.context.scene
    if frame is not None: sc.frame_set(int(frame))
    sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = ruta
    bpy.ops.render.render(write_still=True, scene=sc.name)
