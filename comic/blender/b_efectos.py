# MODO EFECTOS: bocadillos, cartelas, onomatopeyas, lineas de accion y demas recursos de comic, en Grease Pencil.
#   blender -b 04_animacion.blend -P b_efectos.py -- --proyecto DIR --salida DIR/04b_efectos.blend
# Todo vive en "Pantalla" (hijo de la camara, 1 unidad = alto del cuadro), anclado a la posicion proyectada del
# actor en el fotograma del efecto: mismo tamano en un plano general y en un primer plano.
# Los efectos que hierven (lineas, confeti, humo, estrellas) se redibujan cada 2 fotogramas con fotogramas GP;
# los que aparecen de golpe (onomatopeyas, iconos) llevan escala con rebote y visibilidad por fotogramas.
import os, sys, json, math, random, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
import gp_base as GB, camara as CAM, personajes as PJ
from gp_base import Lapiz, P, circulo, elipse, rect, rect_redondeado, poligono, estrella, nube, suave, arco
import comic_parametros as CP

R = 0.0032          # tinta en unidades de pantalla (alto del cuadro = 1)
EMO_GRITO = {"emocionado", "enfadado", "sorprendido", "asustado"}

class Pantalla:
    def __init__(self, params, col_):
        self.params = params
        sc = bpy.context.scene; cam = sc.camera; self.cam = cam
        w, h, _ = CP.resolucion(params); self.A = w / h; self.s = min(1.0, self.A)
        e = bpy.data.objects.new("Pantalla", None); e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.2
        col_.objects.link(e); e.parent = cam
        alto_de_mayor = (1 / self.A) if self.A >= 1 else 1.0
        if cam.data.type == 'ORTHO':
            e.location = (0, 0, -2.0)
            fc = e.driver_add("scale")
            for i, d in enumerate(fc):
                drv = d.driver; drv.type = 'SCRIPTED'
                v = drv.variables.new(); v.name = "os"; v.type = 'SINGLE_PROP'
                v.targets[0].id_type = 'CAMERA'; v.targets[0].id = cam.data; v.targets[0].data_path = "ortho_scale"
                drv.expression = f"os*{alto_de_mayor:.6f}"
        else:
            dist = 1.0
            e.location = (0, 0, -dist)
            hv = dist * cam.data.sensor_width / cam.data.lens * alto_de_mayor
            e.scale = (hv, hv, hv)
        self.e = e; self.col = col_

    def objeto(self, nombre):
        ob = GB.nuevo_gp(nombre, self.col)
        ob.parent = self.e; ob.rotation_euler = (-math.pi / 2, 0, 0)
        return ob

    def proyectar(self, punto, f):
        sc = bpy.context.scene; sc.frame_set(f)
        v = world_to_camera_view(sc, self.cam, Vector(punto))
        return Vector(((v.x - 0.5) * self.A, (v.y - 0.5), v.z))

    def dentro(self, x, z, mx, mz):
        lx, lz = self.A / 2 - mx, 0.5 - mz
        return max(-lx, min(lx, x)), max(-lz, min(lz, z))

# ---------------------------------------------------------------- anclas en el mundo
def punto_actor(actor, que="cabeza"):
    rig = bpy.data.objects.get(f"RIG_{actor}")
    if rig and rig.get("comic_tipo") == "rig_personaje":
        pb = rig.pose.bones["cabeza"]
        z = {"cabeza": 1.85, "boca": 1.40, "pies": 0.0, "pecho": 1.05}[que]
        if que == "pies":
            pr = rig.pose.bones["raiz"]; return rig.matrix_world @ (pr.matrix @ pr.bone.matrix_local.inverted() @ Vector((0, 0, 0)))
        return rig.matrix_world @ (pb.matrix @ pb.bone.matrix_local.inverted() @ Vector((0, 0, z)))
    if rig:
        meta = json.loads(rig.get("comic_meta", "{}")); alto = meta.get("alto", 1.0)
        z = {"cabeza": alto, "boca": alto * 0.6, "pies": 0.0, "pecho": alto * 0.5}[que]
        if meta.get("origen_z") == 0: z -= alto / 2
        return rig.matrix_world @ Vector((0, 0, z))
    return None

# ---------------------------------------------------------------- dibujo de texto y globos
def envolver(texto, ancho):
    return "\n".join(textwrap.wrap(texto, ancho, break_long_words=False)) or texto

def dibujar_globo(lp, texto, cx, cz, tam, destino=None, grito=False, pensamiento=False, semilla=0):
    """Globo con texto centrado en (cx, cz); cola hacia destino (x, z)."""
    conts, (w, h) = GB.contornos_texto(texto, CP.FUENTE_TEXTO, tam, "CENTER", 0.95)
    rx, rz = w / 2 * 1.18 + tam * 0.9, h / 2 * 1.25 + tam * 0.8
    if destino is not None:
        dx, dz = destino[0] - cx, destino[1] - cz
        n = math.hypot(dx, dz) or 1
        largo = max(tam * 1.2, min(n - rz * 0.9 - tam * 0.8, rz * 1.15))   # se queda cerca de la cabeza
        base_ang = math.atan2(dz, dx); bx, bz = cx + rx * 0.75 * math.cos(base_ang), cz + rz * 0.75 * math.sin(base_ang)
        perp = (-math.sin(base_ang), math.cos(base_ang))
        tip = (bx + math.cos(base_ang) * largo, bz + math.sin(base_ang) * largo)
        cola = poligono([(bx + perp[0] * rx * 0.18, bz + perp[1] * rx * 0.18), tip, (bx - perp[0] * rx * 0.12, bz - perp[1] * rx * 0.12)])
        if pensamiento: cola = None
    else:
        cola = None
    if grito: forma = estrella(cx, cz, max(rx, rz) * 1.25, max(rx, rz) * 1.0, 14, irregular=0.08, semilla=semilla)
    elif pensamiento: forma = nube(cx, cz, rx * 2.3, rz * 2.4, 5, semilla=semilla)
    else: forma = elipse(cx, cz, rx, rz, 48)
    if grito: forma = [(cx + (p[0] - cx) * rx / max(rx, rz), 0, cz + (p[2] - cz) * rz / max(rx, rz)) for p in forma]
    if cola: lp.forma(cola, "Relleno blanco", radio=R)
    lp.forma(forma, "Relleno blanco", radio=R)
    if cola: lp.forma(cola, "Plano blanco", linea=False)
    if pensamiento and destino is not None:
        for k, f in enumerate((0.55, 0.78)):
            px, pz = cx + (destino[0] - cx) * f, cz + (destino[1] - cz) * f
            lp.forma(circulo(px, pz, tam * (0.55 - 0.2 * k), 12), "Relleno blanco", radio=R * 0.8)
    grupos = {}
    for c, gid in conts:
        if gid not in grupos: grupos[gid] = lp._fid()
        lp.trazo([(cx + x, 0, cz + y) for x, y in c], "Plano negro", radio=0.0003, cerrado=True, relleno=True, fid=grupos[gid])
    return rx, rz

def dibujar_texto_comic(lp, texto, cx, cz, tam, color="amarillo", sombra="rojo", fuente=None):
    conts, (w, h) = GB.contornos_texto(texto, fuente or CP.FUENTE_TITULOS, tam, "CENTER")
    off = tam * 0.07
    rad = tam * 0.012                    # contorno proporcional: Bangers es estrecha y un trazo fijo tapa el relleno
    for capa_mat, dx, dz in ((f"Relleno {sombra}", off, -off), (f"Relleno {color}", 0, 0)):
        grupos = {}
        for c, gid in conts:
            if gid not in grupos: grupos[gid] = lp._fid()
            lp.trazo([(cx + x + dx, 0, cz + y + dz) for x, y in c], capa_mat, radio=rad, cerrado=True, relleno=True, fid=grupos[gid])
    return w, h

# ---------------------------------------------------------------- visibilidad y rebote
def visible_entre(cl, ob, fa, fb):
    cl.append((ob, "hide_render", 0, [(1, 1.0), (fa, 0.0), (fb, 1.0)]))
    cl.append((ob, "hide_viewport", 0, [(1, 1.0), (fa, 0.0), (fb, 1.0)]))

def rebote(cl, ob, fa, s=1.0):
    cl.append((ob, "scale", None, [(fa, 0.05 * s), (fa + 3, 1.25 * s), (fa + 6, 0.92 * s), (fa + 9, 1.0 * s)]))

def escribir(cl):
    for ob, ruta, idx, claves in cl:
        if idx is None:
            for i in range(3): GB.curva(ob, ruta, i, [(f, v, "BEZIER" if ruta == "scale" else "CONSTANT") for f, v in claves])
        else:
            GB.curva(ob, ruta, idx, [(f, v, "CONSTANT") for f, v in claves])

# ---------------------------------------------------------------- efectos
class Efectos:
    def __init__(self, pant, params, fps, rnd):
        self.p = pant; self.params = params; self.fps = fps; self.rnd = rnd; self.cl = []; self.n = 0; self.avisos = []
        self.s = pant.s

    def ancla(self, actor, f, que="cabeza"):
        bpy.context.scene.frame_set(f)          # primero el fotograma: la pose del rig es la de f
        w = punto_actor(actor, que) if actor else None
        if w is None: return Vector((0, 0.15, 1))
        return self.p.proyectar(w, f)

    def nuevo(self, nombre):
        self.n += 1; ob = self.p.objeto(f"FX_{self.n:03d}_{nombre}")
        ob.location.z = 0.035 + 0.0005 * self.n      # sin empates de profundidad entre objetos 2D
        return ob

    def hervir(self, nombre, fa, fb, dibujar, paso=2):
        """Objeto con un fotograma GP nuevo cada `paso` fotogramas (dibujo a mano) y uno vacio al final."""
        ob = self.nuevo(nombre)
        for k, f in enumerate(range(fa, fb, paso)):
            lp = Lapiz(ob, "fx", frame=f); dibujar(lp, k, (f - fa) / max(1, fb - fa))
        Lapiz(ob, "fx", frame=fb)        # vacio: desaparece
        Lapiz(ob, "fx", frame=0)         # vacio antes
        return ob

    # --- cada efecto
    def onomatopeya(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "pecho"); s = self.s
        texto = (ef.get("texto") or "¡POW!").upper()
        ob = self.nuevo("onomatopeya"); lp = Lapiz(ob, "fx")
        tam = 0.105 * s
        conts, (w, h) = GB.contornos_texto(texto, CP.FUENTE_TITULOS, tam)
        r1 = max(w * 0.62, h * 1.1)
        lp.forma(estrella(0, 0, r1 * 1.25, r1 * 0.8, 16, irregular=0.15, semilla=self.n), f"Relleno {ef.get('color') or 'magenta'}", radio=R * 1.5)
        lp.forma(estrella(0, 0, r1 * 0.95, r1 * 0.65, 16, irregular=0.12, semilla=self.n + 1), "Relleno blanco", linea=False)
        dibujar_texto_comic(lp, texto, 0, 0, tam)
        lado = 1 if a.x < 0 else -1                      # al lado del actor, hacia el centro del cuadro
        x, z = self.p.dentro(a.x + lado * (r1 * 1.15 + 0.06 * s), a.y + 0.12, r1 * 1.3, r1 * 1.3)
        ob.location = (x, z, 0.04); ob.rotation_euler = (-math.pi / 2, self.rnd.uniform(-0.2, 0.2), 0)
        GB.brillo(ob, (1, 0.85, 0.1), 25)
        visible_entre(self.cl, ob, f, f + dur); rebote(self.cl, ob, f)

    def icono(self, ef, f, dur, tipo):
        a = self.ancla(ef.get("actor"), f, "cabeza"); s = self.s
        ob = self.nuevo(tipo); lp = Lapiz(ob, "fx"); t = 0.06 * s
        if tipo == "exclamacion":
            lp.forma(poligono([(-t * 0.35, t * 1.6), (t * 0.35, t * 1.6), (t * 0.18, -t * 0.2), (-t * 0.18, -t * 0.2)]), "Relleno rojo", radio=R)
            lp.forma(circulo(0, -t * 0.65, t * 0.25, 14), "Relleno rojo", radio=R)
        elif tipo == "interrogacion":
            lp.texto("?", CP.FUENTE_TITULOS, t * 3.2, (0, 0, 0), "Relleno cian", radio=R)
        elif tipo == "idea":
            lp.forma(suave([(-t * 0.6, t * 0.2), (-t * 0.7, t * 0.9), (0, t * 1.5), (t * 0.7, t * 0.9), (t * 0.6, t * 0.2), (t * 0.3, -t * 0.25), (-t * 0.3, -t * 0.25)], 5), "Relleno amarillo", radio=R)
            lp.forma(rect(-t * 0.3, -t * 0.65, t * 0.3, -t * 0.25), "Relleno gris", radio=R)
            for k in range(7):
                ang = math.pi * (0.05 + 0.9 * k / 6)
                lp.linea([P(math.cos(ang) * t * 1.2, t * 0.6 + math.sin(ang) * t * 1.2), P(math.cos(ang) * t * 1.7, t * 0.6 + math.sin(ang) * t * 1.7)], "Trazo naranja", radio=R * 1.3)
            GB.brillo(ob, (1, 0.9, 0.3), 30)
        elif tipo == "zzz":
            for k, (dx, dz, tt) in enumerate(((0, 0, 1.0), (t * 0.9, t * 0.9, 0.8), (t * 1.6, t * 1.7, 0.6))):
                lp.texto("Z", CP.FUENTE_TITULOS, t * 1.8 * tt, (dx, 0, dz), "Relleno celeste", radio=R)
        lado = -1 if a.x < 0 else 1                      # del lado contrario al bocadillo
        x, z = self.p.dentro(a.x + lado * 0.1 * s, a.y + 0.05 * s, 0.1, 0.1)
        ob.location = (x, z, 0.045)
        visible_entre(self.cl, ob, f, f + dur); rebote(self.cl, ob, f)

    def lineas_velocidad(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "pecho"); d = ef.get("_dir", 1); s = self.s
        rnd = random.Random(self.n)
        def dib(lp, k, u):
            for i in range(9):
                z = a.y + rnd.uniform(-0.12, 0.12) * s; x0 = a.x - d * rnd.uniform(0.07, 0.12) * s; L = rnd.uniform(0.08, 0.22) * s
                lp.linea([P(x0, z), P(x0 - d * L * 0.5, z), P(x0 - d * L, z)], "Tinta", radio=R * 1.3, afilar=True)
        # sigue al actor: un dibujo por tramo, re-anclado
        ob = self.nuevo("lineas_velocidad")
        for k, fr in enumerate(range(f, f + dur, 2)):
            a = self.ancla(ef.get("actor"), fr, "pecho"); lp = Lapiz(ob, "fx", frame=fr); dib(lp, k, 0)
        Lapiz(ob, "fx", frame=f + dur); Lapiz(ob, "fx", frame=0)

    def lineas_foco(self, ef, f, dur):
        A = self.p.A; rnd = random.Random(self.n)
        def dib(lp, k, u):
            for i in range(46):
                ang = rnd.uniform(0, 2 * math.pi); r0 = rnd.uniform(0.32, 0.42); r1 = 0.9
                c, s_ = math.cos(ang), math.sin(ang)
                lp.forma(poligono([(c * r1 * A - s_ * 0.012, s_ * r1 + c * 0.012), (c * r0 * A, s_ * r0), (c * r1 * A + s_ * 0.012, s_ * r1 - c * 0.012)]),
                         "Plano negro", linea=False)
        self.hervir("lineas_foco", f, f + dur, dib)

    def confeti(self, ef, f, dur):
        A = self.p.A; rnd = random.Random(self.n)
        piezas = [(rnd.uniform(-A / 2, A / 2), rnd.uniform(0.5, 0.9), rnd.uniform(0.25, 0.5), rnd.uniform(0, 6.28),
                   rnd.choice(["rojo", "amarillo", "cian", "magenta", "lima", "violeta", "naranja"])) for _ in range(70)]
        def dib(lp, k, u):
            t = k * 2 / self.fps
            for x0, z0, v, ph, c in piezas:
                x = x0 + 0.03 * math.sin(ph + t * 4); z = z0 - v * t
                if z < -0.6: continue
                g = ph + t * 6; w, h = 0.012, 0.006 + 0.006 * abs(math.sin(g))
                lp.forma([(x + w * math.cos(g) - h * math.sin(g), 0, z + w * math.sin(g) + h * math.cos(g)),
                          (x - w * math.cos(g) - h * math.sin(g), 0, z - w * math.sin(g) + h * math.cos(g)),
                          (x - w * math.cos(g) + h * math.sin(g), 0, z - w * math.sin(g) - h * math.cos(g)),
                          (x + w * math.cos(g) + h * math.sin(g), 0, z + w * math.sin(g) - h * math.cos(g))], f"Plano {c}", linea=False)
        self.hervir("confeti", f, f + dur, dib)

    def humo(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "pies"); s = self.s; rnd = random.Random(self.n)
        bolas = [(rnd.uniform(-0.08, 0.08) * s, rnd.uniform(0, 0.03) * s, rnd.uniform(0.6, 1.2)) for _ in range(6)]
        def dib(lp, k, u):
            for i, (dx, dz, v) in enumerate(bolas):
                r = (0.02 + 0.05 * u * v) * s
                lp.forma(nube(a.x + dx * (1 + 2 * u), a.y + dz + 0.06 * u * s, r * 2, r * 1.6, 3, semilla=i), "Relleno blanco" if u < 0.7 else "Relleno gris_claro", radio=R * (1 - u * 0.6))
        self.hervir("humo", f, f + dur, dib)

    def estrellas(self, ef, f, dur):
        s = self.s
        def dib(lp, k, u):
            a = self.ancla(ef.get("actor"), f + k * 2, "cabeza")
            for i in range(3):
                ang = k * 0.5 + i * 2.094
                lp.forma(estrella(a.x + math.cos(ang) * 0.06 * s, a.y + 0.02 + math.sin(ang) * 0.02 * s, 0.018 * s, 0.008 * s), "Relleno amarillo", radio=R * 0.8)
        self.hervir("estrellas", f, f + dur, dib)

    def corazones(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "cabeza"); s = self.s; rnd = random.Random(self.n)
        cs = [(rnd.uniform(-0.06, 0.06) * s, rnd.uniform(0, 0.3)) for _ in range(3)]
        def corazon(cx, cz, r):
            return suave([(cx, cz - r), (cx + r * 1.0, cz + r * 0.2), (cx + r * 0.55, cz + r * 0.8), (cx, cz + r * 0.45),
                          (cx - r * 0.55, cz + r * 0.8), (cx - r * 1.0, cz + r * 0.2)], 4)
        def dib(lp, k, u):
            for dx, d0 in cs:
                v = max(0.0, u - d0) / (1 - d0)
                if v <= 0: continue
                lp.forma(corazon(a.x + dx + 0.02 * math.sin(v * 9), a.y + 0.03 + 0.15 * v * s, 0.022 * s), "Relleno rojo", radio=R)
        self.hervir("corazones", f, f + dur, dib)

    def sudor(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "cabeza"); s = self.s
        def dib(lp, k, u):
            for i, dx in enumerate((-0.05, 0.06)):
                z = a.y - 0.02 - 0.06 * ((u * 2 + i * 0.4) % 1) * s
                cx = a.x + dx * s
                lp.forma(suave([(cx, z + 0.03 * s), (cx + 0.012 * s, z), (cx, z - 0.012 * s), (cx - 0.012 * s, z)], 4), "Relleno celeste", radio=R * 0.8)
        self.hervir("sudor", f, f + dur, dib)

    def destello(self, ef, f, dur):
        s = self.s; rnd = random.Random(self.n)
        def dib(lp, k, u):
            a = self.ancla(ef.get("actor"), f + 2 * k, "pecho")
            for i in range(6):
                ang = rnd.uniform(0, 6.28); r = rnd.uniform(0.05, 0.14) * s; t = rnd.uniform(0.008, 0.02) * s
                lp.forma(estrella(a.x + math.cos(ang) * r, a.y + math.sin(ang) * r, t * 2.2, t * 0.5, 4), "Relleno amarillo", radio=R * 0.6)
        ob = self.hervir("destello", f, f + dur, dib); GB.brillo(ob, (1, 1, 0.5), 20)

    def impacto(self, ef, f, dur):
        a = self.ancla(ef.get("actor"), f, "pecho"); s = self.s
        def dib(lp, k, u):
            r = (0.05 + 0.12 * min(1, u * 3)) * s
            lp.forma(estrella(a.x, a.y, r, r * 0.45, 10, irregular=0.25, semilla=k), "Relleno amarillo", radio=R * 1.5)
            lp.forma(estrella(a.x, a.y, r * 0.55, r * 0.25, 10, irregular=0.25, semilla=k + 9), "Relleno rojo", radio=R)
        ob = self.hervir("impacto", f, min(f + dur, f + int(0.6 * self.fps)), dib); GB.brillo(ob, (1, 0.6, 0.1), 25)

    def aplicar(self, ef, f, dur):
        t = ef["tipo"]
        try:
            if t == "onomatopeya": self.onomatopeya(ef, f, dur)
            elif t in ("exclamacion", "interrogacion", "idea", "zzz"): self.icono(ef, f, dur, t)
            elif t == "lineas_velocidad": self.lineas_velocidad(ef, f, dur)
            elif t == "lineas_foco": self.lineas_foco(ef, f, dur)
            elif t == "confeti": self.confeti(ef, f, dur)
            elif t == "humo": self.humo(ef, f, dur)
            elif t == "estrellas": self.estrellas(ef, f, dur)
            elif t == "corazones": self.corazones(ef, f, dur)
            elif t == "sudor": self.sudor(ef, f, dur)
            elif t == "destello": self.destello(ef, f, dur)
            elif t == "impacto": self.impacto(ef, f, dur)
        except Exception as e:
            self.avisos.append(f"efecto {t} en {f}: {e}")

# ---------------------------------------------------------------- principal
def efectos_automaticos(esc, f0, f1):
    """Efectos que implican las acciones (correr -> lineas de velocidad, golpear -> POW, caer -> estrellas...)."""
    out = []
    for ac in esc["acciones"]:
        a, n = ac["actor"], ac["accion"]
        fa = f0 + int(ac["inicio"] * (f1 - f0)); fb = f0 + int(ac["fin"] * (f1 - f0))
        if n == "correr":
            d = 1 if ac.get("destino_x", 0) >= 0 else -1
            out.append((dict(tipo="lineas_velocidad", actor=a, _dir=d), fa, max(4, fb - fa)))
        elif n == "golpear":
            fi = fa + int(0.42 * (fb - fa))
            out.append((dict(tipo="onomatopeya", texto="¡POW!", actor=ac.get("hacia") or a), fi, 18))
            out.append((dict(tipo="impacto", actor=ac.get("hacia") or a), fi, 12))
        elif n == "caer":
            out.append((dict(tipo="humo", actor=a), fa + int(0.3 * (fb - fa)), 14))
            out.append((dict(tipo="estrellas", actor=a), fa + int(0.35 * (fb - fa)), int(0.4 * (fb - fa))))
        elif n == "despegar":
            out.append((dict(tipo="humo", actor=a), fa, max(12, fb - fa)))
        elif n == "aparecer":
            out.append((dict(tipo="destello", actor=a), fa, 14))
    return out

def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    tiempos = GB.leer_json(os.path.join(dirp, "tiempos.json"))
    sc = bpy.context.scene; fps = params["fps"]
    col_ = GB.coleccion("Efectos", bpy.data.collections.get("Comic"))
    pant = Pantalla(params, col_)
    fx = Efectos(pant, params, fps, random.Random(11))
    s = pant.s; A = pant.A
    # papel impreso delante de todo (multiplicar)
    if params.get("papel", True) and GB.imagen("papel"):
        ob = pant.objeto("Papel"); lp = Lapiz(ob, "papel")
        lp.forma(rect(-A / 2 * 1.05, -0.53, A / 2 * 1.05, 0.53), "Papel", linea=False)
        lp.capa.blend_mode = 'MULTIPLY'; lp.capa.opacity = 0.35
        ob.location = (0, 0, 0.05)
    # cartelas del narrador (fotogramas GP: dibujo al empezar la linea, vacio al acabar)
    narr = [ln for e in tiempos["escenas"] for ln in e["lineas"] if ln["quien"] == "narrador"]
    if params.get("cartelas", True) and narr:
        ob = pant.objeto("Cartelas")
        ancho = 34 if A >= 1 else 24
        for i, ln in enumerate(narr):
            lp = Lapiz(ob, "cartela", frame=ln["inicio"])
            txt = envolver(ln["texto"], ancho); tam = 0.036 * s
            conts, (w, h) = GB.contornos_texto(txt, CP.FUENTE_TEXTO, tam, "LEFT", 1.0)
            x0, z1 = -A / 2 + 0.03, 0.47
            bw, bh = w + tam * 1.4, h + tam * 1.2
            lp.forma(rect(x0 + 0.006, z1 - bh - 0.006, x0 + bw + 0.006, z1 - 0.006), "Plano negro", linea=False)
            lp.forma(rect(x0, z1 - bh, x0 + bw, z1), "Relleno amarillo", radio=R)
            grupos = {}
            for c, gid in conts:
                if gid not in grupos: grupos[gid] = lp._fid()
                lp.trazo([(x0 + bw / 2 + x, 0, z1 - bh / 2 + y) for x, y in c], "Plano negro", radio=0.0003, cerrado=True, relleno=True, fid=grupos[gid])
            sig = narr[i + 1]["inicio"] if i + 1 < len(narr) else 10 ** 6
            Lapiz(ob, "cartela", frame=min(ln["fin"] + int(0.3 * fps), sig))
        Lapiz(ob, "cartela", frame=0)
        ob.location = (0, 0, 0.02)
    # bocadillos de los personajes (en pantalla, anclados a la cabeza proyectada al empezar la linea)
    dialogos = [ln for e in tiempos["escenas"] for ln in e["lineas"] if ln["quien"] != "narrador"]
    if params.get("bocadillos", True) and dialogos:
        ob = pant.objeto("Bocadillos")
        ancho = 22 if A >= 1 else 16
        for i, ln in enumerate(dialogos):
            f = ln["inicio"]; cab = fx.ancla(ln["quien"], f, "cabeza"); boca = fx.ancla(ln["quien"], f, "boca")
            lp = Lapiz(ob, "globos", frame=f)
            txt = envolver(ln["texto"], ancho); tam = 0.04 * s
            conts, (w, h) = GB.contornos_texto(txt, CP.FUENTE_TEXTO, tam, "CENTER", 0.95)
            rx, rz = w / 2 * 1.18 + tam * 0.9, h / 2 * 1.25 + tam * 0.8
            lado = 1 if cab.x < 0 else -1
            cx, cz = cab.x + lado * rx * 0.55, cab.y + rz + 0.06
            cx, cz = pant.dentro(cx, cz, rx + 0.02, rz + 0.02)
            if abs(cz - boca.y) < rz + 0.04: cz = min(0.5 - rz - 0.02, boca.y + rz + 0.08)
            dibujar_globo(lp, txt, cx, cz, tam, destino=(boca.x, boca.y + 0.02), grito=ln["emocion"] in EMO_GRITO, semilla=i)
            sig = dialogos[i + 1]["inicio"] if i + 1 < len(dialogos) else 10 ** 6
            Lapiz(ob, "globos", frame=min(ln["fin"] + int(0.35 * fps), sig))
        Lapiz(ob, "globos", frame=0)
        ob.location = (0, 0, 0.03)
    # efectos del guion y automaticos
    total = 0
    for esc, te in zip(guion["escenas"], tiempos["escenas"]):
        f0, f1 = te["inicio"], te["fin"]
        lista = [(ef, f0 + int(ef["momento"] * (f1 - f0)), max(6, int(ef.get("duracion", 1.0) * fps))) for ef in esc["efectos"]]
        lista += efectos_automaticos(esc, f0, f1)
        for ef, f, dur in lista:
            f = max(f0, min(f1 - 2, f)); dur = min(dur, f1 - f)
            fx.aplicar(ef, f, max(2, dur)); total += 1
    for ob in col_.all_objects:
        if ob.type == 'GREASEPENCIL': GB.temblor_linea(ob, factor=0.25, paso=3)
    escribir(fx.cl)
    sc.frame_set(1)
    GB.guardar(a["salida"])
    if a.get("previa"):
        fr = [int(x) for x in str(a.get("frames", "")).split(",") if x] or [int((e["inicio"] + e["fin"]) / 2) for e in tiempos["escenas"]]
        for f in fr: GB.render_fotograma(a["previa"].replace("#", str(f)), f)
    print("INFORME " + json.dumps(dict(efectos=total, objetos_fx=fx.n, cartelas=len(narr), bocadillos=len(dialogos),
                                       avisos=fx.avisos), ensure_ascii=False))

if __name__ == "__main__":
    main()
