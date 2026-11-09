# Objetos-icono prefabricados del estilo tecnico (forma "icono" + "modelo"), al modo de un set de iconos isometricos
# (referencias/iconos/set_iconos_isometricos.png): cuerpos sencillos hechos con las formas primitivas, frente hacia -Y.
# Sin bpy: lo usan comic_parametros (esquema, medidas, avisos) y blender/tecnico.py (dibujo).
#
# Cada parte es una forma primitiva en coordenadas del modelo (unidades libres; se normaliza para que la dimension
# mayor del icono valga 1 y su base quede centrada en x=y=0, z=0). 'rol' decide el color:
#   c = color de la pieza (cuerpo), a = 'acento' de la pieza (lima por defecto), l = azul claro, n = negro, b = blanco.
import math

def P(forma, rol="c", x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0, **d):
    return dict(forma=forma, rol=rol, x=x, y=y, z=z, rot_x=rx, rot_y=ry, rot_z=rz, **d)

def _hacia(d):
    """rot_x, rot_y (grados, Euler XYZ) que llevan el eje Z local a la direccion d."""
    n = math.sqrt(sum(c * c for c in d)); dx, dy, dz = (c / n for c in d)
    return math.degrees(math.asin(-dy)), math.degrees(math.atan2(dx, dz))

def _reloj_arena():
    return [P("caja", ancho=0.62, fondo=0.62, alto=0.08),
            P("cono", "b", z=0.081, radio=0.24, radio2=0.035, alto=0.418),
            P("cono", "b", z=0.501, radio=0.035, radio2=0.24, alto=0.418),
            P("cono", "a", z=0.082, radio=0.25, radio2=0.14, alto=0.228),           # arena abajo (un poco mayor que el cristal)
            P("cono", "a", z=0.502, radio=0.045, radio2=0.13, alto=0.168),          # arena arriba, junto al cuello
            P("caja", z=0.92, ancho=0.62, fondo=0.62, alto=0.08),
            P("varilla", x=-0.25, y=0.25, z=0.081, radio=0.024, alto=0.838),
            P("varilla", x=0.25, y=-0.25, z=0.081, radio=0.024, alto=0.838)]

def _base_datos():
    ps = []
    for k, z in enumerate((0.0, 0.36, 0.72)):
        ps.append(P("cilindro", z=z, radio=0.42, alto=0.28))
        if k < 2: ps.append(P("cilindro", "a", z=z + 0.281, radio=0.395, alto=0.078))
        for ang in (-112, -92):
            a = math.radians(ang); ps.append(P("esfera", "a", x=0.42 * math.cos(a), y=0.42 * math.sin(a), z=z + 0.14 - 0.032, radio=0.032))
    return ps

def _embudo():
    return [P("cilindro", radio=0.08, alto=0.32),
            P("cono", z=0.3, radio=0.09, radio2=0.46, alto=0.53),
            P("cilindro", "l", z=0.81, radio=0.43, alto=0.04),                     # boca: el interior en azul claro
            P("anillo", "a", z=0.80, radio=0.45, grosor=0.032)]

def _campana():
    return [P("esfera", "a", y=-0.05, radio=0.08),                                    # badajo asomando por debajo
            P("anillo", "a", z=0.1, radio=0.4, grosor=0.04),
            P("cono", z=0.12, radio=0.42, radio2=0.31, alto=0.12),                   # vuelo de la boca
            P("cono", z=0.241, radio=0.31, radio2=0.21, alto=0.359),
            P("esfera", z=0.39, radio=0.21),
            P("esfera", "a", z=0.79, radio=0.06)]

def _esfera_reloj(cz, r, y0, prof):
    """Caja de reloj: cilindro tumbado con la esfera hacia -Y (de y0 a y0 - prof)."""
    return P("cilindro", y=y0, z=cz, rx=90, radio=r, alto=prof)

def _marcas(cz, r, yf):
    return [P("caja", "n", x=0, y=yf, z=cz + r * 0.72, ancho=0.03, fondo=0.012, alto=r * 0.17),
            P("caja", "n", x=0, y=yf, z=cz - r * 0.89, ancho=0.03, fondo=0.012, alto=r * 0.17),
            P("caja", "n", x=r * 0.8, y=yf, z=cz - 0.015, ancho=r * 0.17, fondo=0.012, alto=0.03),
            P("caja", "n", x=-r * 0.8, y=yf, z=cz - 0.015, ancho=r * 0.17, fondo=0.012, alto=0.03)]

def _despertador():
    cz, r = 0.46, 0.38; yf = -0.128
    return ([_esfera_reloj(cz, r, 0.12, 0.24)] + _marcas(cz, r, yf) +
            [P("caja", "n", y=yf, z=cz, ancho=0.035, fondo=0.012, alto=0.17),                 # horaria
             P("caja", "n", y=yf, z=cz, ry=115, ancho=0.03, fondo=0.012, alto=0.25),          # minutero
             P("cilindro", "n", y=-0.12, z=cz, rx=90, radio=0.035, alto=0.022),
             P("esfera", "a", x=-0.24, z=0.72, radio=0.14), P("esfera", "a", x=0.24, z=0.72, radio=0.14),
             P("varilla", "n", z=0.84, radio=0.02, alto=0.1), P("esfera", "n", z=0.9, radio=0.035),
             P("varilla", "n", x=-0.3, ry=25, radio=0.025, alto=0.2), P("varilla", "n", x=0.3, ry=-25, radio=0.025, alto=0.2)])

def _cronometro():
    cz, r = 0.38, 0.38; yf = -0.088
    return ([_esfera_reloj(cz, r, 0.08, 0.16)] + _marcas(cz, r, yf) +
            [P("caja", "n", y=yf, z=cz, ry=40, ancho=0.03, fondo=0.012, alto=0.27),
             P("cilindro", "n", y=-0.08, z=cz, rx=90, radio=0.035, alto=0.022),
             P("cilindro", z=0.75, radio=0.05, alto=0.08),
             P("cilindro", "a", z=0.82, radio=0.1, alto=0.06)])

def _candado():
    return [P("caja", ancho=0.7, fondo=0.32, alto=0.56),
            P("anillo", "a", y=0.055, z=0.56, rx=90, radio=0.22, grosor=0.055),     # arco (la mitad de abajo, dentro)
            P("cilindro", "n", y=-0.16, z=0.32, rx=90, radio=0.055, alto=0.02),
            P("caja", "n", y=-0.17, z=0.17, ancho=0.035, fondo=0.02, alto=0.13)]

def _engranaje():
    ps = [P("cilindro", radio=0.36, alto=0.2)]
    for k in range(8):
        a = math.radians(k * 45); ps.append(P("caja", x=0.41 * math.cos(a), y=0.41 * math.sin(a), z=0.002, rz=k * 45, ancho=0.12, fondo=0.15, alto=0.196))
    ps += [P("cilindro", "l", z=0.201, radio=0.12, alto=0.012), P("anillo", "a", z=0.201, radio=0.2, grosor=0.018)]
    return ps

def _monitor():
    return [P("caja", ancho=0.42, fondo=0.26, alto=0.05),
            P("caja", y=0.03, z=0.051, ancho=0.1, fondo=0.06, alto=0.278),
            P("caja", z=0.3, ancho=1.0, fondo=0.08, alto=0.64),
            P("caja", "l", y=-0.045, z=0.4, ancho=0.88, fondo=0.012, alto=0.48),
            P("caja", "a", z=0.299, ancho=1.006, fondo=0.088, alto=0.076)]

def _portatil():
    return [P("caja", ancho=0.9, fondo=0.6, alto=0.05),
            P("caja", "l", y=0.0, z=0.051, ancho=0.76, fondo=0.3, alto=0.008),
            P("caja", "l", y=-0.22, z=0.051, ancho=0.24, fondo=0.11, alto=0.008),
            P("panel", y=0.28, z=0.051, rx=-15, ancho=0.9, alto=0.6, grosor=0.04),
            P("panel", "l", y=0.2707, z=0.1043, rx=-15, ancho=0.8, alto=0.48, grosor=0.006)]

def _servidor():
    ps = [P("caja", ancho=0.55, fondo=0.6, alto=1.0)]
    for z0 in (0.1, 0.4, 0.7):
        ps += [P("caja", "l", y=-0.305, z=z0, ancho=0.45, fondo=0.012, alto=0.22),
               P("caja", "n", x=-0.07, y=-0.313, z=z0 + 0.1, ancho=0.24, fondo=0.008, alto=0.025),
               P("esfera", "a", x=0.15, y=-0.31, z=z0 + 0.08, radio=0.03)]
    return ps

def _robot():
    return [P("cilindro", radio=0.3, alto=0.12),
            P("cilindro", "l", z=0.121, radio=0.14, alto=0.118),
            P("caja", z=0.24, ancho=0.72, fondo=0.56, alto=0.52),
            P("caja", "n", y=-0.285, z=0.34, ancho=0.56, fondo=0.012, alto=0.28),
            P("cilindro", "a", x=-0.13, y=-0.291, z=0.5, rx=90, radio=0.06, alto=0.016),
            P("cilindro", "a", x=0.13, y=-0.291, z=0.5, rx=90, radio=0.06, alto=0.016),
            P("caja", "a", y=-0.296, z=0.39, ancho=0.18, fondo=0.012, alto=0.025),
            P("varilla", "n", z=0.761, radio=0.018, alto=0.139),
            P("esfera", "a", z=0.88, radio=0.06),
            P("cilindro", "a", x=0.361, z=0.5, ry=90, radio=0.09, alto=0.06),
            P("cilindro", "a", x=-0.361, z=0.5, ry=-90, radio=0.09, alto=0.06)]

def _orbe():
    return [P("cono", radio=0.3, radio2=0.2, alto=0.22),
            P("esfera", z=0.16, radio=0.38),
            P("anillo", "a", z=0.52, rx=18, radio=0.5, grosor=0.03)]

def _llave():
    return [P("anillo", "a", x=-0.32, radio=0.15, grosor=0.05),
            P("caja", x=0.08, ancho=0.52, fondo=0.075, alto=0.08),
            P("caja", x=0.22, y=-0.07, z=0.001, ancho=0.06, fondo=0.08, alto=0.078),
            P("caja", x=0.31, y=-0.065, z=0.001, ancho=0.06, fondo=0.06, alto=0.078)]

def _caja_herramientas():
    return [P("caja", ancho=0.9, fondo=0.46, alto=0.42),
            P("caja", "a", z=0.421, ancho=0.93, fondo=0.49, alto=0.139),
            P("anillo", y=0.03, z=0.561, rx=90, radio=0.16, grosor=0.03),
            P("caja", y=-0.245, z=0.33, ancho=0.1, fondo=0.02, alto=0.14)]

def _diana():
    rx, ry = _hacia((0.5, -0.65, 0.55)); o = (0.0, -0.066, 0.5)
    d = (0.507, -0.659, 0.557)
    def en(t): return dict(x=o[0] + d[0] * t, y=o[1] + d[1] * t, z=o[2] + d[2] * t)
    return [P("caja", y=0.02, ancho=0.5, fondo=0.26, alto=0.06),
            P("cilindro", y=0.05, z=0.5, rx=90, radio=0.45, alto=0.08),
            P("cilindro", "l", y=-0.03, z=0.5, rx=90, radio=0.32, alto=0.012),
            P("cilindro", y=-0.042, z=0.5, rx=90, radio=0.21, alto=0.012),
            P("cilindro", "a", y=-0.054, z=0.5, rx=90, radio=0.1, alto=0.012),
            P("varilla", "n", rx=rx, ry=ry, radio=0.018, alto=0.55, **en(0.0)),
            P("cono", "a", rx=rx, ry=ry, radio=0.07, radio2=0.006, alto=0.13, **en(0.42))]

def _escudo():
    return [P("caja", z=0.36, ancho=0.62, fondo=0.12, alto=0.46),
            P("caja", x=-0.155, z=0.205, ry=45, ancho=0.438, fondo=0.1, alto=0.438),   # punta: cuadrado girado sobre su centro (0, 0.36)
            P("caja", "a", x=-0.07, y=-0.068, z=0.42, ry=-40, ancho=0.05, fondo=0.012, alto=0.16),
            P("caja", "a", x=-0.07, y=-0.068, z=0.42, ry=35, ancho=0.05, fondo=0.012, alto=0.3)]

MODELOS = {
    "reloj_arena": ("reloj de arena: TTL, caducidad, ventana de tiempo, espera", _reloj_arena),
    "base_datos": ("base de datos: tabla (DynamoDB, Postgres), almacen, cache persistente", _base_datos),
    "embudo": ("embudo: agrupar, correlacionar, filtrar, deduplicar", _embudo),
    "campana": ("campana: alerta, notificacion, aviso a un equipo", _campana),
    "despertador": ("despertador: alarma urgente, alerta que suena", _despertador),
    "cronometro": ("cronometro: latencia, medir tiempos, rapidez", _cronometro),
    "candado": ("candado: seguridad, permiso, acceso restringido", _candado),
    "engranaje": ("engranaje (tumbado): proceso, funcion (Lambda), worker", _engranaje),
    "monitor": ("monitor: panel, consola, analista, dashboard", _monitor),
    "portatil": ("portatil: cliente, usuario, desarrollador", _portatil),
    "servidor": ("servidor (rack): backend, worker, API", _servidor),
    "robot": ("robot: el agente de IA", _robot),
    "orbe": ("orbe con anillo sobre pedestal: el modelo de lenguaje (LLM)", _orbe),
    "llave": ("llave (tumbada): clave, hash, credencial", _llave),
    "caja_herramientas": ("caja de herramientas: tools del agente", _caja_herramientas),
    "diana": ("diana con flecha: acierto (cache hit), objetivo", _diana),
    "escudo": ("escudo con visto: seguridad, SOC, proteccion", _escudo),
}
LISTA = list(MODELOS)

# ---------------------------------------------------------------- caja envolvente y normalizacion
def _rot(v, rx, ry, rz):
    x, y, z = v
    for eje, a in (("x", rx), ("y", ry), ("z", rz)):          # Euler XYZ, como Blender
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        if eje == "x": y, z = y * c - z * s, y * s + z * c
        elif eje == "y": x, z = x * c + z * s, -x * s + z * c
        else: x, y = x * c - y * s, x * s + y * c
    return x, y, z

def puntos_parte(q):
    """Puntos de la caja envolvente de una parte (coordenadas del modelo)."""
    f = q["forma"]
    if f in ("caja", "panel"):
        a = q["ancho"] / 2; b = (q["fondo"] if f == "caja" else q["grosor"]) / 2; h = q["alto"]
        loc = [(x, y, z) for x in (-a, a) for y in (-b, b) for z in (0, h)]
    elif f == "esfera": r = q["radio"]; loc = [(x, y, z) for x in (-r, r) for y in (-r, r) for z in (0, 2 * r)]
    elif f == "anillo":
        r = q["radio"] + q["grosor"]; loc = [(r * math.cos(a), r * math.sin(a), z) for a in [i * math.pi / 8 for i in range(16)] for z in (0, 2 * q["grosor"])]
    else:
        r = max(q.get("radio", 0.1), q.get("radio2", 0) if f == "cono" else 0); h = q.get("alto", 0.1)
        loc = [(r * math.cos(a), r * math.sin(a), z) for a in [i * math.pi / 8 for i in range(16)] for z in (0, h)]
    return [tuple(c + o for c, o in zip(_rot(v, q["rot_x"], q["rot_y"], q["rot_z"]), (q["x"], q["y"], q["z"]))) for v in loc]

def _caja(partes):
    pts = [v for q in partes for v in puntos_parte(q)]
    return [min(v[i] for v in pts) for i in range(3)], [max(v[i] for v in pts) for i in range(3)]

MEDIDAS = ("radio", "radio2", "alto", "ancho", "fondo", "grosor")

def partes(modelo, tam=1.0):
    """Partes del modelo escaladas para que su dimension mayor mida 'tam', centradas en XY y con la base en z=0."""
    crudo = MODELOS.get(modelo, MODELOS["servidor"])[1]()
    (x0, y0, z0), (x1, y1, z1) = _caja(crudo)
    s = tam / max(x1 - x0, y1 - y0, z1 - z0, 1e-6); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = []
    for q in crudo:
        q = dict(q, x=(q["x"] - cx) * s, y=(q["y"] - cy) * s, z=(q["z"] - z0) * s)
        for k in MEDIDAS:
            if k in q: q[k] = q[k] * s
        out.append(q)
    return out

def caja_local(modelo, tam=1.0):
    """(min, max) de la caja envolvente del icono ya escalado, en sus coordenadas locales."""
    return _caja(partes(modelo, tam))

def proporciones(modelo):
    (x0, y0, z0), (x1, y1, z1) = caja_local(modelo, 1.0)
    return round(x1 - x0, 2), round(y1 - y0, 2), round(z1 - z0, 2)

def vocabulario():
    return "; ".join(f"{k}: {v[0]} (ancho x fondo x alto = {'x'.join(str(c) for c in proporciones(k))} por 'alto' 1)" for k, v in MODELOS.items())
