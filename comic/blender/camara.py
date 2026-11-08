# Camara unica de la animacion ("Camara" con Track To a "Camara_objetivo"). Cada escena es un tramo de claves;
# los cortes entre escenas son claves constantes. 2D: ortografica frontal. 3D: perspectiva con angulo y orbita.
import math, random
import bpy
from mathutils import Vector
import comic_parametros as CP

LENTE = 35.0
ALTO_PLANO = {"general": 10.0, "conjunto": 4.6, "medio": 2.3, "primer_plano": 1.2, "detalle": 0.75}
CENTRO_Z = {"medio": 1.28, "primer_plano": 1.5, "detalle": 1.55}     # por altura del personaje

def aspecto(params):
    w, h, _ = CP.resolucion(params); return w / h

def crear(params, col_):
    m3d = params["formato"] == "3d"
    cd = bpy.data.cameras.new("Camara")
    cd.type = 'PERSP' if m3d else 'ORTHO'
    cd.lens = LENTE; cd.sensor_width = 36; cd.sensor_fit = 'AUTO'
    cd.clip_start = 0.05; cd.clip_end = 600
    cam = bpy.data.objects.new("Camara", cd); col_.objects.link(cam)
    obj = bpy.data.objects.new("Camara_objetivo", None); obj.empty_display_type = 'SPHERE'; obj.empty_display_size = 0.3
    col_.objects.link(obj)
    c = cam.constraints.new('TRACK_TO'); c.target = obj; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    cam.location = (0, -60 if not m3d else -14, 4.0); obj.location = (0, 0, 4.0)
    cd.ortho_scale = 18
    return cam, obj

def mayor_desde_alto(alto, params):
    a = aspecto(params)
    return alto * a if a >= 1 else alto

def alto_desde_mayor(mayor, params):
    a = aspecto(params)
    return mayor / a if a >= 1 else mayor

def encuadre(plano, centro_x, alto_personaje, span, params, angulo="frontal", yaw=0.0, factor_alto=1.0):
    """Devuelve dict(cam=Vector, obj=Vector, ortho=float, alto=float) para un plano."""
    m3d = params["formato"] == "3d"
    a = aspecto(params)
    H = ALTO_PLANO.get(plano, 4.6) * (alto_personaje if plano in CENTRO_Z else 1.0)
    if plano in ("general", "conjunto"):
        ancho_vis = H * a
        margen = 4.5 if plano == "conjunto" else 3.5        # sitio para cuerpos y bocadillos en los bordes
        if span + margen > ancho_vis: H = (span + margen) / a
        if a < 1: H = min(H, 9.5 if plano == "general" else 6.0)   # vertical: mejor recortar los lados que llenar de cielo
    H *= factor_alto
    if plano in CENTRO_Z: cz = CENTRO_Z[plano] * alto_personaje
    else: cz = H * (0.34 if a < 1 else 0.40)
    if angulo == "picado" and plano in ("general", "conjunto"): cz += H * 0.06
    obj = Vector((centro_x, 0.0 if not m3d else 0.6, cz))
    if not m3d:
        return dict(cam=Vector((centro_x, -60.0, cz)), obj=obj, ortho=mayor_desde_alto(H, params), alto=H)
    D = mayor_desde_alto(H, params) * LENTE / 36.0
    elev = {"frontal": 0.10, "picado": 0.55, "contrapicado": -0.28}.get(angulo, 0.1)
    d = Vector((math.sin(yaw), -math.cos(yaw), elev)).normalized()
    cam = obj + d * D
    if cam.z < 0.35: cam.z = 0.35
    return dict(cam=cam, obj=obj, ortho=None, alto=H)

def claves_escena(esc, f0, f1, posiciones, alturas, x0_esc, params, rnd, seguir=None, elementos=None):
    """Claves (frame -> (cam, obj, ortho, alto)) de la camara para una escena.
    posiciones: {actor: x} al inicio; seguir(frame) -> x del objetivo (para 'seguir');
    elementos: {id: (x, alto, z_base)} para encuadrar un objeto del decorado."""
    c = esc["camara"]; plano, mov, ang = c["plano"], c["movimiento"], c["angulo"]
    pres = [p["actor"] for p in esc["presentes"]]
    xs = [posiciones[a] for a in pres if a in posiciones] or [x0_esc]
    obj_id = c["objetivo"]
    alto_p = alturas.get(obj_id, 1.0) if obj_id in alturas else (max(alturas.values()) if alturas else 1.0)
    el = (elementos or {}).get(obj_id)
    if el and plano != "general":
        # un objeto del decorado: se encuadra con su propia altura (un personaje de referencia mide 1.85)
        ex, ealto, ez = el
        k = {"detalle": 0.45, "primer_plano": 0.7, "medio": 1.0, "conjunto": 1.6}.get(plano, 1.0)
        H = max(0.8, ealto * k * 1.25)
        out = {}
        for f, fa in ((f0, 1.25 if mov == "zoom_in" else 1.0), (f1 - 1, 1.0 if mov != "zoom_out" else 1.4)):
            e = encuadre("conjunto", ex, 1.0, 0.0, params, ang, 0.0, 1.0)
            Hf = H * fa; cz = ez + (ealto * 0.62 if plano in ("detalle", "primer_plano") else ealto * 0.5)
            e["obj"] = Vector((ex, e["obj"].y, cz)); e["alto"] = Hf
            if e["ortho"] is not None:
                e["cam"] = Vector((ex, e["cam"].y, cz)); e["ortho"] = mayor_desde_alto(Hf, params)
            else:
                D = mayor_desde_alto(Hf, params) * LENTE / 36.0
                d = (e["cam"] - encuadre("conjunto", ex, 1.0, 0.0, params, ang, 0.0, 1.0)["obj"]).normalized()
                e["cam"] = e["obj"] + d * D
            out[f] = e
        return out
    if el and plano == "general" and abs(el[0] - x0_esc) < 25: xs = xs + [el[0]]
    if obj_id in posiciones and plano not in ("general", "conjunto"): cx = posiciones[obj_id]
    elif plano == "conjunto": cx = (min(xs) + max(xs)) / 2          # el conjunto encuadra a todos los presentes
    elif obj_id.startswith("@"): cx = float(obj_id[1:])
    else: cx = (min(xs) + max(xs)) / 2 if plano != "general" else (min(xs) + max(xs)) / 2 * 0.6 + x0_esc * 0.4
    span = (max(xs) - min(xs)) if plano in ("general", "conjunto") else 0.0
    m3d = params["formato"] == "3d"
    yaw0 = rnd.choice([-0.18, -0.1, 0.1, 0.18]) if m3d else 0.0
    hacia = 1 if c.get("hacia", "derecha") != "izquierda" else -1
    out = {}
    def en(f, **kw):
        out[f] = encuadre(plano, kw.get("x", cx), alto_p, span, params, ang, kw.get("yaw", yaw0), kw.get("fa", 1.0))
    n = max(1, f1 - f0 - 1)
    if mov == "zoom_in": en(f0, fa=1.45); en(f1 - 1, fa=1.0)
    elif mov == "zoom_out": en(f0, fa=1.0); en(f1 - 1, fa=1.5)
    elif mov == "paneo":
        e = encuadre(plano, cx, alto_p, span, params, ang, yaw0); dx = e["alto"] * aspecto(params) * 0.3
        en(f0, x=cx - hacia * dx); en(f1 - 1, x=cx + hacia * dx)
    elif mov == "orbita" and m3d:
        for k in range(5): en(f0 + round(n * k / 4), yaw=-0.7 + 1.4 * k / 4)
    elif mov == "seguir" and seguir:
        for f in range(f0, f1, 4): en(f, x=seguir(f))
        en(f1 - 1, x=seguir(f1 - 1))
    elif mov == "grua": en(f0, fa=0.85); out[f0]["obj"].z *= 0.6; out[f0]["cam"].z *= 0.6; en(f1 - 1, fa=1.1)
    else: en(f0); en(f1 - 1)
    if mov == "temblor":
        base = out[f0]
        for f in range(f0 + 2, f1 - 1, 2):
            k = max(0.0, 1.0 - (f - f0) / max(1, (f1 - f0) * 0.6))
            amp = base["alto"] * 0.025 * k
            off = Vector((rnd.uniform(-amp, amp), 0, rnd.uniform(-amp, amp)))
            out[f] = dict(base, cam=base["cam"] + off, obj=base["obj"] + off)
        out[f1 - 1] = dict(base)
    return out
