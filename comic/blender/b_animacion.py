# MODO 4 · ANIMACION: anima rigs, escenografia y camara con el guion y los tiempos del audio (modo 3).
#   blender -b 02_rig.blend -P b_animacion.py -- --proyecto DIR --salida DIR/04_animacion.blend
# - Personajes: pose calculada por fotograma (en dos, interpolacion constante): reposo (respira, parpadea, mira),
#   acciones del guion con mezcla de entrada/salida, ciclo de paso por distancia recorrida, vista frente/perfil,
#   direccion (espejo en el hueso raiz) y boca desde la envolvente de su voz.
# - Escenografia: movimiento propio (viento en copas, nubes, rayos del sol) y acciones de objeto.
# - Camara: un tramo por escena con cortes secos; grosor de tinta compensado por plano.
# - Audio: una tira de sonido por linea (o la pista propia) en el secuenciador: el render sale con voz.
import os, sys, json, math, random
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import gp_base as GB, camara as CAM, personajes as PJ
import comic_parametros as CP

D2R = math.pi / 180

def suave(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def campana(u): return math.sin(math.pi * min(1.0, max(0.0, u)))

def rampa(f, fa, fb, ent=4, sal=4):
    """Peso 0..1 de una accion en [fa, fb] con entrada y salida suaves (en fotogramas)."""
    if f < fa - ent or f > fb + sal: return 0.0
    if f < fa: return suave((f - (fa - ent)) / ent)
    if f > fb: return suave(1 - (f - fb) / sal)
    return 1.0

VISTA_ACCION = {"saludar": "F", "celebrar": "F", "sorpresa": "F", "pensar": "F", "bailar": "F", "triste": "F",
                "enfadado": "F", "saltar": None, "hablar": None, "quieto": None,
                "caminar": "P", "correr": "P", "entrar": "P", "salir": "P", "golpear": "P", "caer": "P", "mirar": "P", "girar": "P",
                "senalar": "F"}
MOVIMIENTO = {"caminar": (1.15, 30, 38, 24), "entrar": (1.15, 30, 38, 24), "salir": (1.15, 30, 38, 24), "correr": (1.9, 50, 75, 50)}

# ================================================================ claves
class Claves:
    """Acumula claves {(bloque, tipo, ruta, indice): {frame: (valor, interpolacion)}} y las escribe en bloque."""
    def __init__(self): self.c = defaultdict(dict)
    def put(self, id_, ruta, idx, f, v, interp="CONSTANT"):
        self.c[(id_.name, getattr(id_, "id_type", "OBJECT"), ruta, idx)][int(f)] = (float(v), interp)
    def valores(self, id_, ruta, idx):
        return {f: v for f, (v, _) in self.c.get((id_.name, getattr(id_, "id_type", "OBJECT"), ruta, idx), {}).items()}
    def escribir(self):
        colecciones = {"OBJECT": bpy.data.objects, "GREASEPENCIL": bpy.data.grease_pencils,
                       "GREASEPENCIL_V3": bpy.data.grease_pencils, "CAMERA": bpy.data.cameras}
        n = 0
        for (nombre, tipo, ruta, idx), d in self.c.items():
            id_ = colecciones[tipo].get(nombre)
            claves = sorted((f, v, i) for f, (v, i) in d.items())
            if all(i == "CONSTANT" for _, _, i in claves):
                claves = [(f, v, "CONSTANT") for f, v in GB.simplificar([(f, v) for f, v, _ in claves])]
            GB.curva(id_, ruta, idx, claves)
            n += len(claves)
        return n

# ================================================================ personajes
class Personaje:
    def __init__(self, datos, rig, gp, params, rnd):
        self.p = datos; self.id = datos["id"]; self.rig = rig; self.gp = gp
        self.fps = params["fps"]; self.paso = 2 if params.get("en_dos", True) else 1
        self.rnd = rnd; self.fase = rnd.uniform(0, 6.28)
        self.x = 0.0; self.dir = 1; self.vista = "F"
        self.parpadeos = set()
        self.capas = [L.name for L in gp.data.layers]

    # --- poses (canales: ('r', hueso) grados, ('l', hueso, eje) unidades, especiales 'boca', 'ojos_cerrados')
    def reposo(self, t, vista):
        b = math.sin(2 * math.pi * t / 3.2 + self.fase); h = math.sin(2 * math.pi * t / 5.3 + self.fase * 2)
        if vista == "F":
            return {("r", "brazo_sup.R"): -4 - 1.5 * b, ("r", "brazo_sup.L"): 4 + 1.5 * b, ("r", "brazo_inf.R"): 7,
                    ("r", "brazo_inf.L"): -7, ("l", "cadera", 1): 0.007 * b, ("r", "cabeza"): 2.2 * h}
        return {("r", "p_brazo_sup.del"): 3 + 1.5 * b, ("r", "p_brazo_sup.tras"): -3, ("r", "p_brazo_inf.del"): 12,
                ("r", "p_brazo_inf.tras"): 10, ("l", "cadera", 1): 0.007 * b, ("r", "cabeza"): 1.5 * h}

    def andar(self, recorrido, tipo):
        zancada, A, K, Ab = MOVIMIENTO[tipo]
        ph = 2 * math.pi * recorrido / zancada
        s, c = math.sin(ph), math.cos(ph)
        corre = tipo == "correr"
        return {("r", "p_pierna_sup.del"): A * s, ("r", "p_pierna_sup.tras"): -A * s,
                ("r", "p_pierna_inf.del"): -K * max(0.0, c), ("r", "p_pierna_inf.tras"): -K * max(0.0, -c),
                ("r", "p_brazo_sup.del"): -Ab * s, ("r", "p_brazo_sup.tras"): Ab * s,
                ("r", "p_brazo_inf.del"): 85 if corre else 22, ("r", "p_brazo_inf.tras"): 85 if corre else 18,
                ("l", "cadera", 1): (0.045 if corre else 0.022) * math.cos(2 * ph),
                ("r", "torso"): -12 if corre else -3, ("r", "cabeza"): 8 if corre else 2}

    def accion_pose(self, nombre, u, t, ac):
        """Pose de una accion en su avance u (0..1). Devuelve (canales, extras)."""
        e = suave(min(1.0, u / 0.15)) * suave(min(1.0, (1 - u) / 0.15))
        if nombre == "saludar":
            return {("r", "brazo_sup.R"): -150 * e, ("r", "brazo_inf.R"): (-20 + 28 * math.sin(2 * math.pi * 3 * t)) * e,
                    ("r", "cabeza"): 5 * e}, {}
        if nombre == "senalar":
            d = ac.get("_dir", 1)
            if d < 0: return {("r", "brazo_sup.R"): -88 * e, ("r", "brazo_inf.R"): -4 * e, ("l", "ojos", 0): -0.03 * e}, {}
            return {("r", "brazo_sup.L"): 88 * e, ("r", "brazo_inf.L"): 4 * e, ("l", "ojos", 0): 0.03 * e}, {}
        if nombre == "celebrar":
            w = math.sin(2 * math.pi * 4 * t)
            return {("r", "brazo_sup.R"): -155 * e, ("r", "brazo_sup.L"): 155 * e, ("r", "brazo_inf.R"): -15 * w * e,
                    ("r", "brazo_inf.L"): 15 * w * e, ("l", "raiz", 1): 0.16 * abs(math.sin(2 * math.pi * 2 * t)) * e}, {"boca": 2}
        if nombre == "sorpresa":
            k = campana(u / 0.35) if u < 0.35 else 0.0
            return {("r", "brazo_sup.R"): -115 * e, ("r", "brazo_sup.L"): 115 * e, ("r", "brazo_inf.R"): -35 * e,
                    ("r", "brazo_inf.L"): 35 * e, ("l", "raiz", 1): 0.14 * k, ("r", "cabeza"): -4 * e}, {"boca": 2}
        if nombre == "pensar":
            return {("r", "brazo_sup.R"): 22 * e, ("r", "brazo_inf.R"): 128 * e, ("r", "cabeza"): 9 * e,
                    ("l", "ojos", 0): 0.02 * e, ("l", "ojos", 1): 0.028 * e}, {}
        if nombre == "bailar":
            s = math.sin(2 * math.pi * 2 * t)
            return {("r", "cadera"): 9 * s * e, ("r", "torso"): -11 * s * e, ("r", "cabeza"): 7 * s * e,
                    ("r", "brazo_sup.R"): (-70 - 45 * s) * e, ("r", "brazo_sup.L"): (70 - 45 * s) * e,
                    ("r", "brazo_inf.R"): -30 * e, ("r", "brazo_inf.L"): 30 * e, ("l", "raiz", 1): 0.07 * abs(s) * e}, {"boca": 1}
        if nombre == "triste":
            return {("r", "cabeza"): 13 * e, ("l", "cabeza", 1): -0.03 * e, ("r", "torso"): -3 * e,
                    ("r", "brazo_sup.R"): 2 * e, ("r", "brazo_sup.L"): -2 * e, ("l", "ojos", 1): -0.02 * e}, {"boca": 0}
        if nombre == "enfadado":
            j = (self.rnd.random() - 0.5) * 0.03 * e
            return {("r", "brazo_sup.R"): -42 * e, ("r", "brazo_inf.R"): 118 * e, ("r", "brazo_sup.L"): 42 * e,
                    ("r", "brazo_inf.L"): -118 * e, ("l", "raiz", 0): j, ("r", "cabeza"): -3 * e}, {"boca": 1}
        if nombre == "saltar":
            if u < 0.22: c = campana(u / 0.44); y = 0.0; aire = 0.0
            elif u < 0.75: a = (u - 0.22) / 0.53; c = 0.0; y = 0.85 * math.sin(math.pi * a); aire = math.sin(math.pi * a)
            else: c = campana((u - 0.75) / 0.25 * 0.5 + 0.5) * 0.8; y = 0.0; aire = 0.0
            return {("l", "cadera", 1): -0.1 * c, ("r", "pierna_sup.R"): -14 * c - 18 * aire, ("r", "pierna_inf.R"): 28 * c + 36 * aire,
                    ("r", "pierna_sup.L"): 14 * c + 18 * aire, ("r", "pierna_inf.L"): -28 * c - 36 * aire,
                    ("r", "p_pierna_sup.del"): 30 * c + 35 * aire, ("r", "p_pierna_inf.del"): -50 * c - 60 * aire,
                    ("r", "p_pierna_sup.tras"): 20 * c + 10 * aire, ("r", "p_pierna_inf.tras"): -40 * c - 30 * aire,
                    ("r", "brazo_sup.R"): -150 * aire + 20 * c, ("r", "brazo_sup.L"): 150 * aire - 20 * c,
                    ("r", "p_brazo_sup.del"): 150 * aire - 30 * c, ("l", "raiz", 1): y}, {"boca": 2 if aire > 0.3 else 0}
        if nombre == "golpear":
            if u < 0.35: k = suave(u / 0.35); sup, inf, tor = -45 * k, 95 * k, 4 * k
            elif u < 0.5: k = suave((u - 0.35) / 0.15); sup, inf, tor = -45 + 135 * k, 95 - 95 * k, 4 - 16 * k
            elif u < 0.8: sup, inf, tor = 90, 0, -12
            else: k = suave((u - 0.8) / 0.2); sup, inf, tor = 90 * (1 - k), 0, -12 * (1 - k)
            return {("r", "p_brazo_sup.del"): sup, ("r", "p_brazo_inf.del"): inf, ("r", "torso"): tor,
                    ("r", "p_pierna_sup.del"): 20 * e, ("r", "p_pierna_sup.tras"): -15 * e}, {"boca": 1}
        if nombre == "caer":
            if u < 0.3: r = 82 * suave(u / 0.3) ** 2
            elif u < 0.65: r = 82 + 4 * math.sin((u - 0.3) / 0.35 * math.pi * 2)
            else: r = 82 * (1 - suave((u - 0.65) / 0.35))
            k = r / 82
            return {("r", "raiz"): r, ("r", "p_pierna_sup.del"): 35 * k, ("r", "p_pierna_sup.tras"): 20 * k,
                    ("r", "p_brazo_sup.del"): 70 * k, ("r", "p_brazo_sup.tras"): 50 * k}, {"boca": 2 if 0.2 < u < 0.6 else 0,
                                                                                         "ojos_cerrados": 0.3 < u < 0.6}
        if nombre == "hablar":
            return {}, {"boca_auto": True}
        return {}, {}

    def simular(self, cl, f0, f1, x_ini, mirando, acciones, lineas, otros, x0_esc, ancho_vis, centro_cam):
        fps = self.fps
        self.x = x_ini
        dir_def = {"izquierda": -1, "derecha": 1}.get(mirando, self.dir)
        vista_def = "F" if mirando == "camara" else "P"
        self.dir = dir_def
        # tramos en fotogramas; desplazamientos resueltos
        tramos = []
        x = x_ini
        for ac in sorted(acciones, key=lambda a: a["inicio"]):
            fa = f0 + int(round(ac["inicio"] * (f1 - f0))); fb = f0 + int(round(ac["fin"] * (f1 - f0)))
            fb = max(fb, fa + 2)
            tr = dict(ac, fa=fa, fb=fb)
            nom = ac["accion"]
            if nom in MOVIMIENTO:
                dest = x0_esc + ac["destino_x"] if "destino_x" in ac else None
                hacia = ac.get("hacia")
                if nom == "entrar":
                    dest = dest if dest is not None else x
                    lado = -1 if (hacia == "izquierda" or (hacia not in ("izquierda", "derecha") and dest < centro_cam)) else 1
                    x = centro_cam + lado * (ancho_vis / 2 + 1.5)
                    if fa == f0 or True: tr["x_pre"] = x
                elif nom == "salir":
                    lado = -1 if hacia == "izquierda" else 1 if hacia == "derecha" else (1 if x >= centro_cam else -1)
                    dest = centro_cam + lado * (ancho_vis / 2 + 2.0)
                if dest is None: dest = x
                tr["xa"], tr["xb"] = x, dest; x = dest
            if nom in ("senalar", "golpear", "mirar"):
                h = ac.get("hacia") or ""
                if h in otros: tr["_dir"] = 1 if otros[h] >= x else -1
                else: tr["_dir"] = -1 if h == "izquierda" else 1
            tramos.append(tr)
        # si entra, empieza fuera de cuadro desde el principio de la escena
        for tr in tramos:
            if "x_pre" in tr: self.x = tr["x_pre"]; break
        dir_actual = dir_def
        frames = list(range(f0, f1, self.paso))
        if frames[-1] != f1 - 1: frames.append(f1 - 1)
        for f in frames:
            t = (f - 1) / fps
            vista = vista_def; d = dir_actual; pose = {}; extras = {}
            # posicion
            xf = self.x
            for tr in tramos:
                if "xa" in tr:
                    if f >= tr["fa"]:
                        u = min(1.0, (f - tr["fa"]) / max(1, tr["fb"] - tr["fa"]))
                        uu = suave(u) if tr["accion"] != "correr" else (u if 0.1 < u < 0.9 else suave(u))
                        xf = tr["xa"] + (tr["xb"] - tr["xa"]) * uu
                    if tr["fa"] <= f <= tr["fb"] + int(0.4 * fps) and abs(tr["xb"] - tr["xa"]) > 0.05:
                        vista = "P"; d = 1 if tr["xb"] >= tr["xa"] else -1; dir_actual = d
            # pose base
            pose.update(self.reposo(t, vista))
            pesos_brazos = 0.0
            for tr in tramos:
                nom = tr["accion"]
                w = rampa(f, tr["fa"], tr["fb"])
                if w <= 0: continue
                u = min(1.0, max(0.0, (f - tr["fa"]) / max(1, tr["fb"] - tr["fa"])))
                if nom in MOVIMIENTO:
                    if tr["fa"] <= f <= tr["fb"] and abs(tr["xb"] - tr["xa"]) > 0.05:
                        rec = abs(xf - tr["xa"])
                        for k, v in self.andar(rec, nom).items(): pose[k] = pose.get(k, 0) * (1 - w) + v * w
                    continue
                if nom == "girar":
                    if f >= (tr["fa"] + tr["fb"]) / 2: dir_actual = -dir_def if dir_actual == dir_def else dir_actual
                    vista = "P"; d = dir_actual if f >= (tr["fa"] + tr["fb"]) / 2 else dir_def
                    continue
                if nom in ("golpear", "mirar") and "_dir" in tr:
                    d = tr["_dir"]; dir_actual = d if nom == "mirar" else dir_actual
                v_acc = VISTA_ACCION.get(nom)
                if v_acc and w > 0.5: vista = v_acc
                cn, ex = self.accion_pose(nom, u, t, tr)
                for k, v in cn.items(): pose[k] = pose.get(k, 0) * (1 - w) + v * w
                if w > 0.5: extras.update(ex)
                if any(k[1].startswith("brazo") for k in cn): pesos_brazos = max(pesos_brazos, w)
            # habla: boca por envolvente, cabeceo y gesto si los brazos estan libres
            hablando = None
            for ln in lineas:
                if ln["inicio"] <= f < ln["fin"]: hablando = ln; break
            boca = extras.get("boca")
            if hablando is not None:
                env = hablando["envolvente"]; i = min(len(env) - 1, max(0, f - hablando["inicio"]))
                ev = max(env[max(0, i - 1):i + 2] or [0])
                if boca is None: boca = 0 if ev < 0.18 else (1 if ev < 0.6 else 2)
                g = suave(min(1.0, (f - hablando["inicio"]) / 6)) * suave(min(1.0, (hablando["fin"] - f) / 6))
                pose[("r", "cabeza")] = pose.get(("r", "cabeza"), 0) + 3.5 * math.sin(2 * math.pi * 1.6 * t) * ev
                if pesos_brazos < 0.3:
                    if vista == "F":
                        pose[("r", "brazo_sup.L")] = pose.get(("r", "brazo_sup.L"), 0) * (1 - g) + (28 + 6 * ev) * g
                        pose[("r", "brazo_inf.L")] = pose.get(("r", "brazo_inf.L"), 0) * (1 - g) + (75 + 20 * math.sin(2 * math.pi * 1.3 * t)) * g
                    else:
                        pose[("r", "p_brazo_sup.del")] = pose.get(("r", "p_brazo_sup.del"), 0) * (1 - g) + 25 * g
                        pose[("r", "p_brazo_inf.del")] = pose.get(("r", "p_brazo_inf.del"), 0) * (1 - g) + (70 + 15 * math.sin(2 * math.pi * 1.3 * t)) * g
            elif extras.get("boca_auto"):
                boca = int(abs(math.sin(t * 9.0)) * 2.6) if boca is None else boca
            if boca is None: boca = 0
            # mirada en vista frontal: hacia quien habla o hacia el otro personaje mas cercano
            if vista == "F" and ("l", "ojos", 0) not in pose:
                objetivo = None
                for oid, ox in otros.items():
                    if objetivo is None or abs(ox - xf) < abs(objetivo - xf): objetivo = ox
                if objetivo is not None and hablando is None:
                    pose[("l", "ojos", 0)] = 0.022 * (1 if objetivo > xf else -1) * d
            if ("r", "raiz") in pose: pose[("r", "raiz")] *= d
            cerrados = extras.get("ojos_cerrados", False) or (f in self.parpadeos)
            self.escribir(cl, f, xf, d, vista, pose, boca, cerrados)
        self.x = xf; self.dir = dir_actual

    def escribir(self, cl, f, x, d, vista, pose, boca, cerrados):
        rig = self.rig
        cl.put(rig, "location", 0, f, x)
        cl.put(rig, 'pose.bones["raiz"].scale', 0, f, d)
        for h in PJ.HUESOS:
            n = h[0]
            cl.put(rig, f'pose.bones["{n}"].rotation_euler', 2, f, pose.get(("r", n), 0.0) * D2R)
        for n, eje in (("raiz", 0), ("raiz", 1), ("cadera", 1), ("cabeza", 1), ("ojos", 0), ("ojos", 1)):
            cl.put(rig, f'pose.bones["{n}"].location', eje, f, pose.get(("l", n, eje), 0.0))
        for L in self.capas:
            if L == "sombra": op = 1.0
            elif L[:2] in ("F_", "P_"):
                if L[0] != vista: op = 0.0
                elif L.endswith("boca_0"): op = 1.0 if boca == 0 else 0.0
                elif L.endswith("boca_1"): op = 1.0 if boca == 1 else 0.0
                elif L.endswith("boca_2"): op = 1.0 if boca == 2 else 0.0
                elif L.endswith("ojos_cerrados"): op = 1.0 if cerrados else 0.0
                elif L.endswith("_pupilas"): op = 0.0 if cerrados else 1.0
                elif L.endswith("_ojos"): op = 0.0 if cerrados else 1.0
                else: op = 1.0
            else: op = 1.0
            cl.put(self.gp.data, f'layers["{L}"].hide', 0, f, 0.0 if op > 0.5 else 1.0)

    def planificar_parpadeos(self, f_fin):
        f = int(self.rnd.uniform(1.0, 2.5) * self.fps)
        while f < f_fin:
            for k in range(3): self.parpadeos.add(f + k)
            f += int(self.rnd.uniform(2.2, 4.5) * self.fps)
        if self.paso == 2: self.parpadeos |= {x - 1 for x in self.parpadeos if x % 2 == 0}

# ================================================================ escenografia
def animar_elemento(cl, rig, tipo, meta, f_ini, f_fin, fps, paso, acciones, noche, rnd):
    fase = rnd.uniform(0, 6.28); huesos = {b.name for b in rig.data.bones}
    gp = bpy.data.objects.get(rig.get("comic_id"))
    # movimiento propio
    if "copa" in huesos:
        T = rnd.uniform(2.8, 4.2); A = 2.6 if tipo != "flores" else 5
        for f in range(f_ini, f_fin + 1, paso):
            cl.put(rig, 'pose.bones["copa"].rotation_euler', 2, f, A * D2R * math.sin(2 * math.pi * (f / fps) / T + fase))
    if "rayos" in huesos:
        cl.put(rig, 'pose.bones["rayos"].rotation_euler', 2, f_ini, 0.0, "LINEAR")
        cl.put(rig, 'pose.bones["rayos"].rotation_euler', 2, f_fin, -0.35 * (f_fin - f_ini) / fps, "LINEAR")
    if tipo == "nube":
        x0 = rig.location.x
        cl.put(rig, "location", 0, f_ini, x0, "LINEAR"); cl.put(rig, "location", 0, f_fin, x0 + 0.12 * (f_fin - f_ini) / fps, "LINEAR")
    if gp:
        se_enciende = any(ac["accion"] == "encender" for ac in acciones)   # si el guion la enciende, empieza apagada
        for L in meta.get("luz", []):
            cl.put(gp.data, f'layers["{L}"].hide', 0, f_ini, 0.0 if (noche and not se_enciende) else 1.0)
        for L in meta.get("llama", []):
            cl.put(gp.data, f'layers["{L}"].hide', 0, f_ini, 1.0)
    # acciones del guion
    pos_x = rig.location.x
    for ac in acciones:
        fa, fb = ac["fa"], ac["fb"]; nom = ac["accion"]; n = max(2, fb - fa)
        rng = list(range(fa - 2, fb + 3, paso))
        if nom == "aparecer":
            for f in range(f_ini, fa, paso): cl.put(rig, 'pose.bones["raiz"].scale', 1, f, 0.0); cl.put(rig, 'pose.bones["raiz"].scale', 0, f, 0.0)
            for f in range(fa, fb + 1, paso):
                u = (f - fa) / n; s = 1.0 + 0.25 * math.sin(math.pi * u) if u > 0.4 else suave(u / 0.4) * 1.15
                for i in (0, 1, 2): cl.put(rig, 'pose.bones["raiz"].scale', i, f, s)
            for i in (0, 1, 2): cl.put(rig, 'pose.bones["raiz"].scale', i, fb + paso, 1.0)
        elif nom == "desaparecer":
            for f in range(fa, fb + 1, paso):
                s = 1.0 - suave((f - fa) / n)
                for i in (0, 1, 2): cl.put(rig, 'pose.bones["raiz"].scale', i, f, s)
            for i in (0, 1, 2): cl.put(rig, 'pose.bones["raiz"].scale', i, f_fin, 0.0)
        elif nom in ("rebotar", "bailar"):
            for f in rng:
                u = (f - fa) / n; w = rampa(f, fa, fb, 3, 3); s = math.sin(2 * math.pi * 2.5 * (f - fa) / fps)
                cl.put(rig, 'pose.bones["raiz"].scale', 1, f, 1 + 0.18 * s * w)
                cl.put(rig, 'pose.bones["raiz"].scale', 0, f, 1 - 0.09 * s * w)
                cl.put(rig, 'pose.bones["raiz"].scale', 2, f, 1 - 0.09 * s * w)
                if nom == "bailar": cl.put(rig, 'pose.bones["raiz"].rotation_euler', 2, f, 8 * D2R * s * w)
                else: cl.put(rig, 'pose.bones["raiz"].location', 1, f, 0.25 * abs(s) * w)
        elif nom == "temblar":
            for f in rng:
                w = rampa(f, fa, fb, 2, 2)
                cl.put(rig, 'pose.bones["raiz"].location', 0, f, (rnd.random() - 0.5) * 0.12 * w)
        elif nom == "girar":
            for f in rng: cl.put(rig, 'pose.bones["raiz"].rotation_euler', 2, f, -2 * math.pi * suave((f - fa) / n))
            cl.put(rig, 'pose.bones["raiz"].rotation_euler', 2, fb + 4, 0.0)
        elif nom in ("moverse", "conducir"):
            dest = ac.get("_dest", pos_x)
            cl.put(rig, "location", 0, fa, pos_x, "BEZIER"); cl.put(rig, "location", 0, fb, dest, "BEZIER")
            if nom == "conducir":
                rr = meta.get("radio_rueda", 0.32)
                for rueda in meta.get("ruedas", []):
                    for f in range(fa, fb + 1, paso):
                        u = suave((f - fa) / n); cl.put(rig, f'pose.bones["{rueda}"].rotation_euler', 2, f, -(dest - pos_x) * u / rr)
                if "carroceria" in huesos:
                    for f in range(fa, fb + 1, paso):
                        cl.put(rig, 'pose.bones["carroceria"].location', 1, f, 0.03 * abs(math.sin(f * 0.9)))
            pos_x = dest
        elif nom == "despegar":
            for L in meta.get("llama", []):
                if gp: cl.put(gp.data, f'layers["{L}"].hide', 0, fa, 0.0)
            for f in range(fa, fb + 1, paso):
                u = (f - fa) / n
                cl.put(rig, 'pose.bones["raiz"].location', 1, f, 14 * u ** 2.2)
                cl.put(rig, 'pose.bones["raiz"].location', 0, f, (rnd.random() - 0.5) * 0.06 * (1 - u))
        elif nom == "encender":
            for L in meta.get("luz", []):
                if gp: cl.put(gp.data, f'layers["{L}"].hide', 0, fa, 0.0)

# ================================================================ principal
def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    tiempos = GB.leer_json(os.path.join(dirp, "tiempos.json"))
    sc = bpy.context.scene
    GB.configurar_escena(params, sc)
    fps = params["fps"]; paso = 2 if params.get("en_dos", True) else 1
    sc.frame_start = 1; sc.frame_end = max(2, tiempos["frame_fin"])
    indice = json.loads(sc["comic_indice"])
    m3d = params["formato"] == "3d"
    rnd = random.Random(7)
    cl = Claves()
    avisos = []
    # --- audio en el secuenciador
    se = sc.sequence_editor_create()
    for s in list(se.strips): se.strips.remove(s)
    canales = {}
    if tiempos.get("pista_unica"):
        st = se.strips.new_sound("audio_propio", os.path.join(dirp, tiempos["pista_unica"]), channel=1, frame_start=1)
    else:
        for e in tiempos["escenas"]:
            for ln in e["lineas"]:
                ch = canales.setdefault(ln["quien"], len(canales) + 1)
                st = se.strips.new_sound(f"E{e['id']}_{ln['quien']}", os.path.join(dirp, ln["wav"]), channel=ch, frame_start=ln["inicio"])
    for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
    for esc, te in zip(guion["escenas"], tiempos["escenas"]):
        sc.timeline_markers.new(f"E{esc['id']} {esc['descripcion'][:30]}", frame=te["inicio"])
    # --- personajes
    pers = {}
    for p in guion["personajes"]:
        rig = bpy.data.objects.get(f"RIG_{p['id']}"); gp = bpy.data.objects.get(p["id"])
        if not rig or not gp: avisos.append(f"falta el rig de {p['id']}"); continue
        pj = Personaje(p, rig, gp, params, random.Random(p["id"]))
        pj.planificar_parpadeos(sc.frame_end)
        pers[p["id"]] = pj
    alturas = {p["id"]: p["altura"] for p in guion["personajes"]}
    cam = bpy.data.objects["Camara"]; obj = bpy.data.objects["Camara_objetivo"]
    rigs_el = {o["comic_id"]: o for o in bpy.data.objects if o.get("comic_tipo") == "rig_elemento"}
    grosor = {}
    pos_actual = {}
    for esc, te in zip(guion["escenas"], tiempos["escenas"]):
        f0, f1 = te["inicio"], te["fin"]
        x0 = indice["escenarios"][esc["escenario"]]["x0"]
        pres = {q["actor"]: q for q in esc["presentes"]}
        posiciones = {aid: x0 + q["x"] for aid, q in pres.items()}
        # encuadre base (para entradas/salidas fuera de cuadro)
        xs = list(posiciones.values()) or [x0]
        enc0 = CAM.encuadre(esc["camara"]["plano"], sum(xs) / len(xs), 1.0, max(xs) - min(xs), params)
        ancho_vis = enc0["alto"] * CAM.aspecto(params)
        centro = enc0["obj"].x
        for pid, pj in pers.items():
            if pid not in pres:
                cl.put(pj.gp, "hide_render", 0, f0, 1.0); cl.put(pj.gp, "hide_viewport", 0, f0, 1.0)
                continue
            cl.put(pj.gp, "hide_render", 0, f0, 0.0); cl.put(pj.gp, "hide_viewport", 0, f0, 0.0)
            acc = [ac for ac in esc["acciones"] if ac["actor"] == pid]
            lin = [ln for ln in te["lineas"] if ln["quien"] == pid]
            otros = {o: x for o, x in posiciones.items() if o != pid}
            pj.simular(cl, f0, f1, posiciones[pid], pres[pid]["mirando"], acc, lin, otros, x0, ancho_vis, centro)
            pos_actual[pid] = pj.x
        # --- camara
        def seguir_fn(f, pid=esc["camara"]["objetivo"]):
            rig = bpy.data.objects.get(f"RIG_{pid}")
            if not rig: return centro
            d = cl.valores(rig, "location", 0)
            prev = [fr for fr in d if fr <= f]
            return d[max(prev)] if prev else centro
        elementos = {}
        for eid, info in indice["elementos"].items():
            r_el = rigs_el.get(eid)
            if r_el is not None and info["escenario"] == esc["escenario"]:
                esc_z = r_el.scale.z
                elementos[eid] = (r_el.location.x, info["meta"].get("alto", 1.0) * esc_z,
                                  r_el.location.z - (info["meta"].get("alto", 1.0) * esc_z / 2 if info["meta"].get("origen_z") == 0 else 0))
        claves = CAM.claves_escena(esc, f0, f1, posiciones, alturas, x0, params, rnd, seguir=seguir_fn, elementos=elementos)
        fr = sorted(claves)
        for i, f in enumerate(fr):
            k = claves[f]; ultimo = i == len(fr) - 1
            interp = "CONSTANT" if ultimo else ("CONSTANT" if esc["camara"]["movimiento"] == "temblor" else "BEZIER")
            for j in range(3):
                cl.put(cam, "location", j, f, k["cam"][j], interp); cl.put(obj, "location", j, f, k["obj"][j], interp)
            if k["ortho"]: cl.put(cam.data, "ortho_scale", 0, f, k["ortho"], interp)
        alto = claves[fr[0]]["alto"]
        grosor[f0] = max(0.4, min(1.3, (alto / 9.0) ** 0.55))
    # --- escenografia
    for eid, rig in rigs_el.items():
        info = indice["elementos"].get(eid)
        if not info: continue
        esc_def = next(e for e in guion["escenarios"] if e["id"] == info["escenario"])
        acciones = []
        for esc, te in zip(guion["escenas"], tiempos["escenas"]):
            for ac in esc["acciones"]:
                if ac["actor"] == eid:
                    f0, f1 = te["inicio"], te["fin"]
                    d = dict(ac, fa=f0 + int(ac["inicio"] * (f1 - f0)), fb=f0 + int(ac["fin"] * (f1 - f0)))
                    if "destino_x" in ac: d["_dest"] = indice["escenarios"][info["escenario"]]["x0"] + ac["destino_x"]
                    acciones.append(d)
        animar_elemento(cl, rig, info["tipo"], info["meta"], 1, sc.frame_end, fps, paso, acciones,
                        esc_def["cielo"] in ("noche", "espacio"), random.Random(eid))
    # --- grosor de tinta por plano (modificador Thickness con clave constante por escena)
    for ob in [o for o in bpy.data.objects if o.type == 'GREASEPENCIL']:
        if ob.get("comic_tipo") in ("cielo", "suelo"): continue
        m = ob.modifiers.get("Grosor por plano") or ob.modifiers.new("Grosor por plano", 'GREASE_PENCIL_THICKNESS')
        m.use_uniform_thickness = False
        for f, g in grosor.items():
            cl.put(ob, 'modifiers["Grosor por plano"].thickness_factor', 0, f, g)
    n = cl.escribir()
    sc.frame_set(1)
    sc["comic_tiempos"] = json.dumps({k: tiempos[k] for k in ("fps", "frame_inicio", "frame_fin", "duracion")})
    GB.guardar(a["salida"])
    if a.get("previa"):
        fr = [int(x) for x in str(a.get("frames", "")).split(",") if x] or [int((e["inicio"] + e["fin"]) / 2) for e in tiempos["escenas"]]
        base = a["previa"]
        for f in fr: GB.render_fotograma(base.replace("#", str(f)), f)
    print("INFORME " + json.dumps(dict(claves=n, fotogramas=sc.frame_end, personajes=len(pers), elementos=len(rigs_el),
                                       sonidos=len(se.strips), avisos=avisos), ensure_ascii=False))

if __name__ == "__main__":
    main()
