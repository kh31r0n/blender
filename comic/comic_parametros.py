# Tabla unica del agente de comic con Grease Pencil: parametros, paleta, vocabulario del guion, esquema JSON
# para Gemini y validacion. Sin bpy: la importan el agente (Python del sistema) y los scripts de Blender.
import colorsys, copy, json, math, os, re, sys, unicodedata

COMIC = os.path.dirname(os.path.abspath(__file__))
if COMIC not in sys.path: sys.path.insert(0, COMIC)
import iconos_3d as ICO
BIBLIOTECA = os.path.join(COMIC, "biblioteca")
DESCARGAS = os.path.join(COMIC, "descargas")
MATERIALES_BLEND = os.path.join(BIBLIOTECA, "Materiales_GP.blend")
ESCENOGRAFIA_BLEND = os.path.join(BIBLIOTECA, "Escenografia_GP.blend")
FUENTE_TITULOS = os.path.join(DESCARGAS, "fuentes", "Bangers-Regular.ttf")
FUENTE_TEXTO = os.path.join(DESCARGAS, "fuentes", "ComicNeue-Bold.ttf")

# ---------------------------------------------------------------- paleta (sRGB, colores muy vivos)
PALETA = {
    "rojo": "#FF1744", "carmesi": "#E0003C", "naranja": "#FF6D00", "mandarina": "#FF9100",
    "amarillo": "#FFEA00", "oro": "#FFC400", "lima": "#C6FF00", "verde": "#00E676",
    "verde_oscuro": "#00B248", "turquesa": "#1DE9B6", "cian": "#00E5FF", "celeste": "#40C4FF",
    "azul": "#2979FF", "azul_marino": "#2A2F9E", "violeta": "#AA00FF", "morado": "#7C1FFF",
    "magenta": "#F50057", "rosa": "#FF4FA3", "rosa_claro": "#FF9ECF", "marron": "#A0522D",
    "chocolate": "#6D3B1E", "beige": "#FFE3B3", "crema": "#FFF4D6", "blanco": "#FFFFFF",
    "gris_claro": "#CFD8DC", "gris": "#90A4AE", "gris_oscuro": "#455A64", "negro": "#15151F",
    "piel_clara": "#FFD3B0", "piel_media": "#EBA87A", "piel_morena": "#C07A4C", "piel_oscura": "#7E4A2A",
}
TINTA = "#101018"
COLORES = list(PALETA)
COLORES_PIEL = ["piel_clara", "piel_media", "piel_morena", "piel_oscura", "verde", "azul", "lima", "rosa", "gris_claro"]

def hex_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def srgb_a_lineal(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def color_lineal(nombre_o_hex, alfa=1.0, valor=1.0, saturacion=1.0):
    """Color de la paleta (o #hex) en RGBA lineal, opcionalmente oscurecido/aclarado en HSV."""
    h = PALETA.get(nombre_o_hex, nombre_o_hex if str(nombre_o_hex).startswith("#") else PALETA["magenta"])
    r, g, b = hex_rgb(h)
    if valor != 1.0 or saturacion != 1.0:
        hh, s, v = colorsys.rgb_to_hsv(r, g, b)
        r, g, b = colorsys.hsv_to_rgb(hh, min(1, s * saturacion), min(1, v * valor))
    return (srgb_a_lineal(r), srgb_a_lineal(g), srgb_a_lineal(b), alfa)

# ---------------------------------------------------------------- parametros del proyecto (CLI y proyecto.json)
# (clave, tipo, defecto, opciones|rango, descripcion)
PARAMS = [
    ("formato", "MENU", "3d", ["2d", "3d"],
     "2d: todo en planos frente a una camara ortografica, con paralaje por capas. 3d: escenografia con volumen "
     "(cajas de trazos), personajes y vegetacion que miran a camara, camara en perspectiva que puede orbitar."),
    ("orientacion", "MENU", "horizontal", ["horizontal", "vertical"],
     "horizontal 16:9 o vertical 9:16 (redes sociales). Cambia el encuadre de cada plano."),
    ("fps", "INT", 24, (12, 60), "Fotogramas por segundo."),
    ("en_dos", "BOOL", True, None, "Poses de los personajes cada 2 fotogramas (animacion 'en dos', estilo dibujo a mano)."),
    ("calidad", "MENU", "final", ["borrador", "previa", "final"], "Resolucion: 25 %, 50 % o 100 % de 1920x1080."),
    ("duracion", "FLOAT", 30.0, (5.0, 300.0), "Duracion objetivo en segundos (orienta al guionista; manda el audio)."),
    ("idioma", "MENU", "es", ["es", "en", "pt", "fr", "it"], "Idioma de narracion y dialogos."),
    ("voz_narrador", "MENU", "Charon", None, "Voz Gemini TTS del narrador."),
    ("modelo_tts", "MENU", "gemini-2.5-flash-tts", ["gemini-2.5-flash-tts", "gemini-2.5-pro-tts",
                                                     "gemini-3.1-flash-tts-preview"], "Modelo de voz en Vertex AI."),
    ("ritmo_voz", "FLOAT", 2.6, (1.8, 3.6), "Ritmo objetivo de la voz en palabras/s (2.6 = locutor divulgativo, unas 155 por minuto). "
                                            "Las lineas fuera de banda se regeneran y, si no, se ajustan con atempo (mismo tono)."),
    ("grosor_tinta", "FLOAT", 1.0, (0.3, 3.0), "Multiplicador del grosor de las lineas de tinta."),
    ("temblor_linea", "FLOAT", 0.4, (0.0, 2.0), "Temblor de linea (modificador Noise que cambia cada 3 fotogramas)."),
    ("semitono", "BOOL", True, None, "Sombras con trama de puntos (Ben-Day) en caras laterales y suelos."),
    ("papel", "BOOL", True, None, "Textura de papel impreso (ambientCG, multiplicar) delante de camara."),
    ("bocadillos", "BOOL", True, None, "Bocadillos con el texto de los dialogos de los personajes."),
    ("cartelas", "BOOL", True, None, "Cartelas amarillas con el texto del narrador."),
    ("saturacion", "FLOAT", 1.1, (0.5, 1.5), "Multiplicador de saturacion de la paleta."),
    ("brillo_fx", "BOOL", True, None, "Resplandor (Shader FX Glow) en soles, estrellas y onomatopeyas."),
]
PARAMS_POR_CLAVE = {p[0]: p for p in PARAMS}

def params_por_defecto():
    return {p[0]: p[2] for p in PARAMS}

def limitar_params(d):
    out, avisos = params_por_defecto(), []
    for k, v in (d or {}).items():
        if k not in PARAMS_POR_CLAVE: avisos.append(f"parametro desconocido {k}"); continue
        _, tipo, dflt, opc, _ = PARAMS_POR_CLAVE[k]
        try:
            if tipo == "BOOL": v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "si", "sí", "yes")
            elif tipo == "INT": v = int(round(float(v))); v = max(opc[0], min(opc[1], v))
            elif tipo == "FLOAT": v = float(v); v = max(opc[0], min(opc[1], v))
            elif tipo == "MENU" and opc and v not in opc: avisos.append(f"{k}={v} no valido"); v = dflt
        except (TypeError, ValueError):
            avisos.append(f"{k}={v!r} no valido"); v = dflt
        out[k] = v
    return out, avisos

RESOLUCION_BASE = (1920, 1080)
ESCALA_CALIDAD = {"borrador": 25, "previa": 50, "final": 100}

def resolucion(params):
    w, h = RESOLUCION_BASE
    if params.get("orientacion") == "vertical": w, h = h, w
    return w, h, ESCALA_CALIDAD.get(params.get("calidad"), 100)

# ---------------------------------------------------------------- voces Gemini TTS
VOCES = {
    "Charon": "masculina, informativa (narrador)", "Kore": "femenina, firme", "Puck": "masculina, animada",
    "Fenrir": "masculina, excitable", "Aoede": "femenina, ligera", "Leda": "femenina, juvenil",
    "Orus": "masculina, firme", "Zephyr": "femenina, brillante", "Callirrhoe": "femenina, tranquila",
    "Enceladus": "masculina, susurrante", "Iapetus": "masculina, clara", "Algieba": "masculina, suave",
    "Despina": "femenina, suave", "Laomedeia": "femenina, alegre", "Achird": "masculina, amistosa",
    "Sadachbia": "masculina, vivaz", "Gacrux": "femenina, madura", "Zubenelgenubi": "masculina, informal",
}
VOZ_SILENCIO = "silencio"  # sin TTS: duracion estimada por palabras (pruebas sin red)

# ---------------------------------------------------------------- vocabulario del guion
AMBIENTES_CIELO = {
    "dia": "cielo celeste con nubes y trama de puntos blancos", "atardecer": "bandas amarillo-naranja-magenta-violeta",
    "noche": "azul marino y violeta con estrellas amarillas", "espacio": "negro azulado, estrellas y un planeta",
    "interior": "pared de una habitacion con papel pintado a rayas (sin cielo)",
}
AMBIENTES_SUELO = {
    "cesped": "verde con rayas y matojos", "calle": "asfalto con lineas amarillas y acera",
    "arena": "arena amarilla con puntos", "nieve": "blanco azulado", "agua": "azul con olas blancas (muelle)",
    "madera": "suelo de tablas (interiores)", "luna": "suelo gris con crateres",
}
# tipo -> (descripcion, volumen en 3d: caja|plano, ancho, alto)
ELEMENTOS = {
    "edificio": ("rascacielos con ventanas; 'pisos' 3-14", "caja", 3.0, 8.0),
    "casa": ("casa con tejado a dos aguas, puerta y ventanas", "caja", 3.2, 3.6),
    "tienda": ("local con toldo a rayas y letrero ('texto')", "caja", 3.6, 3.4),
    "arbol": ("arbol de copa redonda", "plano", 2.4, 3.6),
    "pino": ("pino de tres pisos", "plano", 1.8, 3.8),
    "palmera": ("palmera", "plano", 2.4, 4.2),
    "arbusto": ("arbusto redondo", "plano", 1.6, 0.9),
    "flores": ("grupo de flores de colores", "plano", 1.2, 0.5),
    "nube": ("nube esponjosa (flota y se desplaza)", "plano", 3.0, 1.4),
    "sol": ("sol con rayos que giran", "plano", 2.4, 2.4),
    "luna": ("luna creciente", "plano", 1.8, 1.8),
    "montana": ("montana de fondo con nieve", "plano", 12.0, 7.0),
    "colina": ("colina suave", "plano", 10.0, 2.5),
    "roca": ("roca", "caja", 1.2, 0.8),
    "farola": ("farola con luz", "plano", 0.6, 3.6),
    "banco": ("banco de parque", "caja", 1.8, 0.9),
    "valla": ("valla de madera (tramo)", "plano", 3.0, 0.9),
    "senal": ("senal con flecha ('texto')", "plano", 0.9, 2.2),
    "coche": ("coche de comic (puede 'conducir')", "caja", 2.8, 1.4),
    "cartel": ("valla publicitaria con 'texto'", "plano", 4.0, 3.2),
    "caja": ("caja de carton", "caja", 0.9, 0.8),
    "cohete": ("cohete (puede 'despegar')", "plano", 1.2, 3.6),
    "planeta": ("planeta con anillo (fondo)", "plano", 4.0, 4.0),
    "mesa": ("mesa (interior)", "caja", 1.8, 0.9),
    "silla": ("silla (interior)", "plano", 0.6, 1.1),
    "ventana": ("ventana en la pared (interior)", "plano", 1.6, 1.6),
    "cuadro": ("cuadro en la pared (interior)", "plano", 1.2, 1.0),
    "planta": ("planta en maceta", "plano", 0.7, 1.3),
    "lampara": ("lampara de pie", "plano", 0.6, 2.0),
}
PROFUNDIDADES = {"delante": -2.5, "personajes": 1.2, "medio": 4.0, "fondo": 9.0, "lejos": 18.0}
ESCALA_2D_PROFUNDIDAD = {"delante": 1.1, "personajes": 1.0, "medio": 0.9, "fondo": 0.75, "lejos": 0.6}
PARALAJE_2D = {"delante": -0.25, "personajes": 0.0, "medio": 0.25, "fondo": 0.5, "lejos": 0.75}

TIPOS_PERSONAJE = {
    "humano": "persona de comic, cabeza grande", "robot": "robot con cabeza cuadrada, antena y ojos LED",
    "gato": "gato antropomorfo con orejas y cola", "perro": "perro antropomorfo con orejas caidas",
    "monstruo": "monstruo simpatico de un ojo con cuernos",
}
PELOS = ["corto", "largo", "coleta", "rizado", "pincho", "calvo", "mono"]
ACCESORIOS = ["ninguno", "gafas", "gorra", "sombrero", "corona", "pajarita", "capa", "mochila"]

# accion -> descripcion. destino_x/hacia segun la accion
ACCIONES_PERSONAJE = {
    "quieto": "de pie, respirando y parpadeando", "hablar": "habla mirando a camara (automatico durante sus lineas)",
    "caminar": "camina de perfil hasta destino_x", "correr": "corre de perfil hasta destino_x (lineas de velocidad)",
    "saltar": "salta en el sitio (anticipacion y aplastado)", "saludar": "saluda con la mano",
    "senalar": "senala hacia 'hacia' (izquierda/derecha o id)", "celebrar": "brazos arriba y saltitos",
    "sorpresa": "respingo con brazos arriba y boca abierta", "pensar": "mano en la barbilla, mira arriba",
    "bailar": "baile de lado a lado", "triste": "cabeza gacha y brazos caidos", "enfadado": "brazos en jarras, temblor",
    "golpear": "punetazo hacia 'hacia' (efecto POW)", "caer": "cae hacia atras y se levanta",
    "mirar": "se gira de perfil hacia 'hacia'", "girar": "da media vuelta", "entrar": "entra caminando desde fuera de cuadro hasta destino_x",
    "salir": "sale caminando de cuadro hacia 'hacia'",
}
ACCIONES_OBJETO = {
    "aparecer": "surge con un rebote (pop)", "desaparecer": "se encoge y desaparece", "rebotar": "rebota como goma",
    "temblar": "tiembla", "girar": "gira sobre si mismo", "moverse": "se desplaza hasta destino_x",
    "conducir": "(coche) avanza hasta destino_x girando ruedas", "despegar": "(cohete) despega hacia arriba con humo",
    "bailar": "se balancea al ritmo", "encender": "(farola/lampara) se enciende",
}
EFECTOS = {
    "onomatopeya": "texto grande ('texto', p. ej. ¡POW!) con estallido detras", "lineas_velocidad": "lineas de accion detras de 'actor'",
    "lineas_foco": "lineas de concentracion manga alrededor del cuadro", "impacto": "estallido de estrellas en 'actor'",
    "corazones": "corazones sobre 'actor'", "sudor": "gotas de sudor de 'actor'", "exclamacion": "signo ! sobre 'actor'",
    "interrogacion": "signo ? sobre 'actor'", "idea": "bombilla sobre 'actor'", "estrellas": "estrellitas girando (mareo)",
    "zzz": "Zzz de sueno", "humo": "nube de polvo/humo en 'actor'", "destello": "brillos alrededor de 'actor'",
    "confeti": "lluvia de confeti en pantalla",
}
PLANOS = {"general": "toda la escena", "conjunto": "varios personajes de cuerpo entero",
          "medio": "de cintura para arriba", "primer_plano": "cabeza y hombros", "detalle": "solo la cara/objeto"}
MOVIMIENTOS = {"fijo": "camara quieta", "paneo": "barrido lateral hacia 'hacia'", "zoom_in": "acercamiento",
               "zoom_out": "alejamiento", "seguir": "sigue al objetivo", "orbita": "gira alrededor (solo 3d)",
               "temblor": "sacudida (impactos)", "grua": "sube o baja"}
ANGULOS = {"frontal": "a la altura de los ojos", "picado": "desde arriba", "contrapicado": "desde abajo (heroico)"}
EMOCIONES = ["neutral", "alegre", "triste", "enfadado", "sorprendido", "asustado", "emocionado", "susurro", "misterioso"]

LIMITE_X = 20.0           # el decorado ocupa x en [-LIMITE_X, LIMITE_X] alrededor del centro de su escenario
SEPARACION_ESCENARIOS = 150.0

# ---------------------------------------------------------------- esquema de respuesta para Gemini (Vertex)
def _enum(vals): return {"type": "STRING", "enum": list(vals)}

def esquema_guion():
    S, N, I, B = {"type": "STRING"}, {"type": "NUMBER"}, {"type": "INTEGER"}, {"type": "BOOLEAN"}
    elemento = {"type": "OBJECT", "properties": {
        "id": S, "tipo": _enum(ELEMENTOS), "x": N, "profundidad": _enum(PROFUNDIDADES), "escala": N,
        "color": _enum(COLORES), "color2": _enum(COLORES), "texto": S, "pisos": I, "espejo": B},
        "required": ["id", "tipo", "x", "profundidad", "color"]}
    escenario = {"type": "OBJECT", "properties": {
        "id": S, "cielo": _enum(AMBIENTES_CIELO), "suelo": _enum(AMBIENTES_SUELO), "color_pared": _enum(COLORES),
        "elementos": {"type": "ARRAY", "items": elemento}}, "required": ["id", "cielo", "suelo", "elementos"]}
    personaje = {"type": "OBJECT", "properties": {
        "id": S, "nombre": S, "tipo": _enum(TIPOS_PERSONAJE), "piel": _enum(COLORES), "ropa": _enum(COLORES),
        "pantalon": _enum(COLORES), "pelo": _enum(PELOS), "color_pelo": _enum(COLORES), "accesorio": _enum(ACCESORIOS),
        "color_accesorio": _enum(COLORES), "altura": N, "voz": _enum(VOCES), "descripcion": S},
        "required": ["id", "nombre", "tipo", "piel", "ropa", "voz"]}
    linea = {"type": "OBJECT", "properties": {"quien": S, "texto": S, "emocion": _enum(EMOCIONES)},
             "required": ["quien", "texto"]}
    accion = {"type": "OBJECT", "properties": {
        "actor": S, "accion": _enum(sorted(set(ACCIONES_PERSONAJE) | set(ACCIONES_OBJETO))), "destino_x": N,
        "hacia": S, "inicio": N, "fin": N}, "required": ["actor", "accion", "inicio", "fin"]}
    efecto = {"type": "OBJECT", "properties": {"tipo": _enum(EFECTOS), "texto": S, "actor": S, "momento": N,
                                               "duracion": N, "color": _enum(COLORES)}, "required": ["tipo", "momento"]}
    camara = {"type": "OBJECT", "properties": {"plano": _enum(PLANOS), "objetivo": S, "movimiento": _enum(MOVIMIENTOS),
                                               "angulo": _enum(ANGULOS), "hacia": S}, "required": ["plano", "objetivo", "movimiento"]}
    posicion = {"type": "OBJECT", "properties": {"actor": S, "x": N, "mirando": _enum(["camara", "izquierda", "derecha"])},
                "required": ["actor", "x"]}
    escena = {"type": "OBJECT", "properties": {
        "id": I, "escenario": S, "descripcion": S, "presentes": {"type": "ARRAY", "items": posicion}, "camara": camara,
        "lineas": {"type": "ARRAY", "items": linea}, "acciones": {"type": "ARRAY", "items": accion},
        "efectos": {"type": "ARRAY", "items": efecto}, "duracion_minima": N},
        "required": ["id", "escenario", "descripcion", "presentes", "camara", "lineas", "acciones", "efectos"]}
    return {"type": "OBJECT", "properties": {
        "titulo": S, "sinopsis": S, "escenarios": {"type": "ARRAY", "items": escenario},
        "personajes": {"type": "ARRAY", "items": personaje}, "escenas": {"type": "ARRAY", "items": escena}},
        "required": ["titulo", "sinopsis", "escenarios", "personajes", "escenas"],
        "propertyOrdering": ["titulo", "sinopsis", "escenarios", "personajes", "escenas"]}

def vocabulario_texto():
    """Resumen del vocabulario para el prompt del guionista."""
    def tabla(d): return "; ".join(f"{k}: {v if isinstance(v, str) else v[0]}" for k, v in d.items())
    return "\n".join([
        f"ELEMENTOS de escenografia (tipo: descripcion): {tabla(ELEMENTOS)}",
        f"PROFUNDIDADES (fila del decorado, de cerca a lejos): {', '.join(PROFUNDIDADES)}",
        f"CIELOS: {tabla(AMBIENTES_CIELO)}", f"SUELOS: {tabla(AMBIENTES_SUELO)}",
        f"TIPOS DE PERSONAJE: {tabla(TIPOS_PERSONAJE)}", f"PELOS: {', '.join(PELOS)}; ACCESORIOS: {', '.join(ACCESORIOS)}",
        f"ACCIONES DE PERSONAJE: {tabla(ACCIONES_PERSONAJE)}", f"ACCIONES DE OBJETO (actor = id de elemento): {tabla(ACCIONES_OBJETO)}",
        f"EFECTOS: {tabla(EFECTOS)}", f"PLANOS: {tabla(PLANOS)}", f"MOVIMIENTOS DE CAMARA: {tabla(MOVIMIENTOS)}",
        f"ANGULOS: {tabla(ANGULOS)}", f"EMOCIONES: {', '.join(EMOCIONES)}",
        f"COLORES (paleta viva): {', '.join(COLORES)}", f"VOCES: {tabla(VOCES)}",
    ])

# ---------------------------------------------------------------- validacion del guion
def slug(texto, n=40):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:n] or "x"

def _num(v, d, lo=None, hi=None):
    try: v = float(v)
    except (TypeError, ValueError): v = d
    if not math.isfinite(v): v = d
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def validar_guion(g, params=None):
    """Normaliza un guion (de Gemini o a mano): ids unicos, enums validos, rangos. Devuelve (guion, avisos)."""
    av = []
    g = copy.deepcopy(g or {})
    out = {"titulo": str(g.get("titulo") or "Sin titulo")[:80], "sinopsis": str(g.get("sinopsis") or "")[:600]}
    # escenarios
    escs, ids_elem = [], set()
    for i, e in enumerate(g.get("escenarios") or []):
        eid = slug(e.get("id") or f"escenario_{i + 1}")
        if any(x["id"] == eid for x in escs): eid = f"{eid}_{i + 1}"
        cielo = e.get("cielo") if e.get("cielo") in AMBIENTES_CIELO else "dia"
        suelo = e.get("suelo") if e.get("suelo") in AMBIENTES_SUELO else ("madera" if cielo == "interior" else "cesped")
        elems = []
        for j, el in enumerate(e.get("elementos") or []):
            tipo = el.get("tipo")
            if tipo not in ELEMENTOS: av.append(f"elemento {el.get('id')}: tipo {tipo!r} desconocido, omitido"); continue
            lid = slug(el.get("id") or f"{tipo}_{j + 1}")
            while lid in ids_elem: lid += "_b"
            ids_elem.add(lid)
            prof = el.get("profundidad") if el.get("profundidad") in PROFUNDIDADES else "medio"
            elems.append(dict(id=lid, tipo=tipo, x=_num(el.get("x"), 0, -LIMITE_X, LIMITE_X), profundidad=prof,
                              escala=_num(el.get("escala"), 1.0, 0.3, 3.0),
                              color=el.get("color") if el.get("color") in PALETA else None,
                              color2=el.get("color2") if el.get("color2") in PALETA else None,
                              texto=str(el.get("texto") or "")[:24], pisos=int(_num(el.get("pisos"), 0, 0, 14)),
                              espejo=bool(el.get("espejo", False))))
        escs.append(dict(id=eid, cielo=cielo, suelo=suelo, elementos=elems,
                         color_pared=e.get("color_pared") if e.get("color_pared") in PALETA else "crema"))
    if not escs:
        escs = [dict(id="exterior", cielo="dia", suelo="cesped", elementos=[], color_pared="crema")]
        av.append("sin escenarios: se crea uno vacio")
    out["escenarios"] = escs
    # personajes
    pers, voces_usadas = [], set()
    for i, p in enumerate(g.get("personajes") or []):
        if {slug(p.get("id") or ""), slug(p.get("nombre") or "")} & {"narrador", "narradora", "narrator", "narrador_p"}:
            av.append("el narrador no es un personaje: se quita (sus lineas son la voz en off)"); continue
        pid = slug(p.get("id") or p.get("nombre") or f"personaje_{i + 1}", 24)
        if pid in ("narrador", "camara", "escena") or pid in ids_elem: pid = f"{pid}_p"
        while any(x["id"] == pid for x in pers): pid += "_b"
        tipo = p.get("tipo") if p.get("tipo") in TIPOS_PERSONAJE else "humano"
        voz = p.get("voz") if p.get("voz") in VOCES else None
        if not voz or voz in voces_usadas:
            libres = [v for v in VOCES if v not in voces_usadas and v != (params or {}).get("voz_narrador", "Charon")]
            voz = voz if voz and voz not in voces_usadas else (libres[0] if libres else "Puck")
        voces_usadas.add(voz)
        def col(k, d): return p.get(k) if p.get(k) in PALETA else d
        pers.append(dict(id=pid, nombre=str(p.get("nombre") or pid)[:30], tipo=tipo,
                         piel=col("piel", {"robot": "gris_claro", "gato": "naranja", "perro": "beige", "monstruo": "verde"}.get(tipo, "piel_clara")),
                         ropa=col("ropa", "rojo"), pantalon=col("pantalon", "azul"),
                         pelo=p.get("pelo") if p.get("pelo") in PELOS else ("calvo" if tipo != "humano" else "corto"),
                         color_pelo=col("color_pelo", "chocolate"),
                         accesorio=p.get("accesorio") if p.get("accesorio") in ACCESORIOS else "ninguno",
                         color_accesorio=col("color_accesorio", "amarillo"),
                         altura=_num(p.get("altura"), 1.0, 0.6, 1.4), voz=voz, descripcion=str(p.get("descripcion") or "")[:200]))
    out["personajes"] = pers
    ids_p = {p["id"] for p in pers}
    nombres = {slug(p["nombre"], 24): p["id"] for p in pers}
    def actor_id(a):
        s = slug(a or "", 24)
        if s in ids_p or s in ids_elem: return s
        return nombres.get(s)
    # escenas
    escenas, ids_esc = [], {e["id"] for e in escs}
    for i, s in enumerate(g.get("escenas") or []):
        esc_id = slug(s.get("escenario") or escs[0]["id"])
        if esc_id not in ids_esc: av.append(f"escena {i + 1}: escenario {esc_id} desconocido"); esc_id = escs[0]["id"]
        pres = []
        for q in s.get("presentes") or []:
            a = actor_id(q.get("actor"))
            if a in ids_p and all(x["actor"] != a for x in pres):
                m = q.get("mirando") if q.get("mirando") in ("camara", "izquierda", "derecha") else "camara"
                pres.append(dict(actor=a, x=_num(q.get("x"), 0, -LIMITE_X, LIMITE_X), mirando=m))
        cam = s.get("camara") or {}
        obj = actor_id(cam.get("objetivo")) or "escena"
        mov = cam.get("movimiento") if cam.get("movimiento") in MOVIMIENTOS else "fijo"
        if mov == "orbita" and (params or {}).get("formato") == "2d": mov = "paneo"
        camara = dict(plano=cam.get("plano") if cam.get("plano") in PLANOS else "general", objetivo=obj, movimiento=mov,
                      angulo=cam.get("angulo") if cam.get("angulo") in ANGULOS else "frontal",
                      hacia=str(cam.get("hacia") or "derecha"))
        lineas = []
        for ln in s.get("lineas") or []:
            t = str(ln.get("texto") or "").strip()
            if not t: continue
            q = actor_id(ln.get("quien")); q = q if q in ids_p else "narrador"
            lineas.append(dict(quien=q, texto=t[:400], emocion=ln.get("emocion") if ln.get("emocion") in EMOCIONES else "neutral"))
        acciones = []
        for ac in s.get("acciones") or []:
            a = actor_id(ac.get("actor")); nom = ac.get("accion")
            if a in ids_p and nom not in ACCIONES_PERSONAJE: av.append(f"escena {i + 1}: accion {nom} no vale para {a}"); continue
            if a in ids_elem and nom not in ACCIONES_OBJETO: av.append(f"escena {i + 1}: accion {nom} no vale para {a}"); continue
            if a is None: av.append(f"escena {i + 1}: actor {ac.get('actor')!r} desconocido"); continue
            ini = _num(ac.get("inicio"), 0, 0, 1); fin = _num(ac.get("fin"), 1, 0, 1)
            if fin <= ini: fin = min(1.0, ini + 0.3)
            d = dict(actor=a, accion=nom, inicio=ini, fin=fin, hacia=str(ac.get("hacia") or ""))
            if ac.get("destino_x") is not None: d["destino_x"] = _num(ac.get("destino_x"), 0, -LIMITE_X - 6, LIMITE_X + 6)
            acciones.append(d)
            if a in ids_p and all(x["actor"] != a for x in pres):   # quien actua esta presente
                pres.append(dict(actor=a, x=d.get("destino_x", 0.0) if nom == "entrar" else 0.0, mirando="camara"))
        for ln in lineas:  # quien habla esta presente
            if ln["quien"] in ids_p and all(x["actor"] != ln["quien"] for x in pres):
                pres.append(dict(actor=ln["quien"], x=0.0, mirando="camara"))
        efectos = []
        for ef in s.get("efectos") or []:
            if ef.get("tipo") not in EFECTOS: continue
            efectos.append(dict(tipo=ef["tipo"], texto=str(ef.get("texto") or "")[:16], actor=actor_id(ef.get("actor")),
                                momento=_num(ef.get("momento"), 0.5, 0, 1), duracion=_num(ef.get("duracion"), 1.0, 0.3, 4.0),
                                color=ef.get("color") if ef.get("color") in PALETA else None))
        escenas.append(dict(id=i + 1, escenario=esc_id, descripcion=str(s.get("descripcion") or "")[:300], presentes=pres,
                            camara=camara, lineas=lineas, acciones=acciones, efectos=efectos,
                            duracion_minima=_num(s.get("duracion_minima"), 2.5, 1.0, 30.0)))
    if not escenas: av.append("el guion no tiene escenas")
    out["escenas"] = escenas
    return out, av

# ---------------------------------------------------------------- guion de ejemplo (sin IA, para pruebas)
def guion_ejemplo():
    return {
        "titulo": "¡Lola salva el parque!", "sinopsis": "Lola y el robot Bip descubren que el sol se ha apagado y lo vuelven a encender con un salto.",
        "escenarios": [{"id": "parque", "cielo": "dia", "suelo": "cesped", "elementos": [
            {"id": "edificio_1", "tipo": "edificio", "x": -11, "profundidad": "fondo", "color": "azul", "pisos": 9},
            {"id": "edificio_2", "tipo": "edificio", "x": -6, "profundidad": "lejos", "color": "violeta", "pisos": 12},
            {"id": "tienda_1", "tipo": "tienda", "x": 9, "profundidad": "fondo", "color": "amarillo", "color2": "rojo", "texto": "PIZZA"},
            {"id": "casa_1", "tipo": "casa", "x": 2, "profundidad": "fondo", "color": "rosa", "color2": "rojo"},
            {"id": "arbol_1", "tipo": "arbol", "x": -5, "profundidad": "medio", "color": "verde"},
            {"id": "pino_1", "tipo": "pino", "x": 6, "profundidad": "medio", "color": "verde_oscuro"},
            {"id": "farola_1", "tipo": "farola", "x": -2.5, "profundidad": "personajes", "color": "gris_oscuro"},
            {"id": "banco_1", "tipo": "banco", "x": 3.5, "profundidad": "personajes", "color": "naranja"},
            {"id": "sol_1", "tipo": "sol", "x": 7, "profundidad": "lejos", "color": "amarillo"},
            {"id": "nube_1", "tipo": "nube", "x": -8, "profundidad": "lejos", "color": "blanco"},
            {"id": "nube_2", "tipo": "nube", "x": 12, "profundidad": "lejos", "color": "blanco", "escala": 0.8},
            {"id": "flores_1", "tipo": "flores", "x": -7, "profundidad": "delante", "color": "magenta"},
            {"id": "arbusto_1", "tipo": "arbusto", "x": 8.5, "profundidad": "delante", "color": "lima"}]}],
        "personajes": [
            {"id": "lola", "nombre": "Lola", "tipo": "humano", "piel": "piel_media", "ropa": "rojo", "pantalon": "azul",
             "pelo": "coleta", "color_pelo": "chocolate", "accesorio": "gafas", "color_accesorio": "magenta", "voz": "Leda"},
            {"id": "bip", "nombre": "Bip", "tipo": "robot", "piel": "cian", "ropa": "naranja", "pantalon": "gris_oscuro",
             "voz": "Puck", "altura": 0.85}],
        "escenas": [
            {"id": 1, "escenario": "parque", "descripcion": "Plano general del parque; Lola entra caminando.",
             "presentes": [{"actor": "lola", "x": -9}, {"actor": "bip", "x": 2.5}],
             "camara": {"plano": "general", "objetivo": "escena", "movimiento": "zoom_in", "angulo": "frontal"},
             "lineas": [{"quien": "narrador", "texto": "Era una mañana brillante en el parque de la ciudad.", "emocion": "alegre"}],
             "acciones": [{"actor": "lola", "accion": "caminar", "destino_x": -1.5, "inicio": 0.1, "fin": 0.85},
                          {"actor": "nube_1", "accion": "moverse", "destino_x": -5, "inicio": 0, "fin": 1}],
             "efectos": []},
            {"id": 2, "escenario": "parque", "descripcion": "Bip saluda; Lola se sorprende.",
             "presentes": [{"actor": "lola", "x": -1.5, "mirando": "derecha"}, {"actor": "bip", "x": 1.2, "mirando": "izquierda"}],
             "camara": {"plano": "conjunto", "objetivo": "escena", "movimiento": "fijo", "angulo": "frontal"},
             "lineas": [{"quien": "bip", "texto": "¡Hola, Lola! ¡El sol se ha quedado sin pilas!", "emocion": "emocionado"},
                        {"quien": "lola", "texto": "¿Qué? ¡Eso no puede ser!", "emocion": "sorprendido"}],
             "acciones": [{"actor": "bip", "accion": "saludar", "inicio": 0.0, "fin": 0.4},
                          {"actor": "lola", "accion": "sorpresa", "inicio": 0.55, "fin": 0.8}],
             "efectos": [{"tipo": "exclamacion", "actor": "lola", "momento": 0.55}]},
            {"id": 3, "escenario": "parque", "descripcion": "Primer plano de Lola pensando.",
             "presentes": [{"actor": "lola", "x": -1.5}, {"actor": "bip", "x": 1.2}],
             "camara": {"plano": "primer_plano", "objetivo": "lola", "movimiento": "zoom_in", "angulo": "contrapicado"},
             "lineas": [{"quien": "lola", "texto": "Tengo una idea. ¡Un súper salto lo arreglará!", "emocion": "emocionado"}],
             "acciones": [{"actor": "lola", "accion": "pensar", "inicio": 0.0, "fin": 0.5}],
             "efectos": [{"tipo": "idea", "actor": "lola", "momento": 0.35}]},
            {"id": 4, "escenario": "parque", "descripcion": "Lola salta y el sol se enciende.",
             "presentes": [{"actor": "lola", "x": -1.5}, {"actor": "bip", "x": 1.2}],
             "camara": {"plano": "general", "objetivo": "escena", "movimiento": "temblor", "angulo": "contrapicado"},
             "lineas": [{"quien": "narrador", "texto": "Y con un salto gigante, el sol volvió a brillar.", "emocion": "emocionado"}],
             "acciones": [{"actor": "lola", "accion": "saltar", "inicio": 0.1, "fin": 0.5},
                          {"actor": "sol_1", "accion": "rebotar", "inicio": 0.45, "fin": 0.9},
                          {"actor": "bip", "accion": "celebrar", "inicio": 0.5, "fin": 1.0}],
             "efectos": [{"tipo": "onomatopeya", "texto": "¡BOING!", "actor": "lola", "momento": 0.25},
                         {"tipo": "destello", "actor": "sol_1", "momento": 0.5}, {"tipo": "confeti", "momento": 0.6}]},
        ]}

if __name__ == "__main__":
    g, av = validar_guion(guion_ejemplo())
    print(json.dumps(g, ensure_ascii=False, indent=1)[:1500]); print("avisos:", av)
    print("esquema bytes:", len(json.dumps(esquema_guion())))

# =====================================================================================================
# ESTILO TECNICO (explicativos de objetos: isometrico, papel, paleta apagada, sombra azul, rayos X)
# =====================================================================================================
FUENTE_TECNICA = os.path.join(DESCARGAS, "fuentes", "ArchivoBlack-Regular.ttf")
ESTILOS = ["comic", "tecnico"]
PARAMS.insert(0, ("estilo", "MENU", "comic", ESTILOS,
                  "comic: historias con personajes, colores muy vivos, bocadillos. tecnico: explicativo de un objeto "
                  "pieza a pieza en vista isometrica, papel, paleta apagada, sombra azul y rayos X."))
# temas del estilo tecnico: 'paleta' sustituye colores por nombre; 'colores' son los que puede usar el guion (los demas se
# convierten con MAPA_TEMA); 'lateral' pinta las caras en sombra de los cuerpos claros; 'tinta' multiplica el grosor de linea.
TEMAS_TECNICOS = {
    "clasico": dict(desc="papel con baldosas y paredes, paleta apagada, sombreado en bandas, tinta fina con temblor y grano de lapiz",
                    paleta={}, colores=None, mapa={}, lateral=None, tinta=1.0, temblor=1.0, papel=True, paredes=True, juntas=True,
                    bisel=False, fx_reloj="naranja", fx_ondas="azul", pantalla="negro", marco="gris_oscuro", peanas=False, neon=False,
                    iconos=True, manguera=None, carteles="clave", guia="", resalte=2.1),
    "iconos": dict(desc="iconos isometricos vectoriales (referencias/iconos): cuerpos blancos con el lateral en sombra azul claro, "
                        "acentos lima, contorno negro grueso, esquinas redondeadas, fondo liso gris azulado, sin textura ni temblor",
                   paleta={"papel": "#DCE5EB", "baldosa": "#DCE5EB", "pared": "#DCE5EB", "pared_oscura": "#C9D6DF",
                           "lima": "#A6D63E", "mostaza": "#A6D63E", "azul_sombra": "#C4D3DE", "blanco_hueso": "#FFFFFF",
                           "menta_oscuro": "#5C9A2C", "negro": "#1B1C1E"},
                   colores=["blanco", "azul_claro", "lima", "negro", "gris_claro", "rojo", "naranja"],
                   mapa={"menta": "lima", "verde_agua": "lima", "menta_oscuro": "lima", "amarillo": "lima", "mostaza": "lima",
                         "verde": "lima", "azul": "azul_claro", "agua": "azul_claro", "cielo": "azul_claro", "violeta": "azul_claro",
                         "morado": "azul_claro", "azul_sombra": "azul_claro", "azul_base": "azul_claro", "azul_neon": "azul_claro",
                         "cian": "azul_claro", "metal": "gris_claro", "gris": "gris_claro", "gris_oscuro": "negro", "cafe": "negro",
                         "blanco_hueso": "blanco", "papel": "blanco", "baldosa": "blanco", "pared": "blanco",
                         "pared_oscura": "gris_claro", "rosa": "rojo", "marron": "naranja", "madera": "naranja", "cobre": "naranja"},
                   lateral="azul_claro", tinta=1.6, temblor=0.0, papel=False, paredes=False, juntas=False, bisel=True,
                   fx_reloj="lima", fx_ondas="lima", pantalla="azul_claro", marco="blanco", peanas=False, neon=False, iconos=True,
                   manguera=None, carteles="clave", guia="", resalte=1.4),
    "neon": dict(desc="maqueta de infraestructura (referencias/maqueta_neon): cada componente sobre una peana azul con el borde "
                      "luminoso, mangueras azules de neon con conectores, colores vivos por componente y metal plateado con rejillas, "
                      "suelo de baldosas blanco y gris claro, tinta negra limpia",
                 paso_baldosa=0.85, junta=0.0042,
                 paleta={"papel": "#EFF2F6", "baldosa": "#DCE1E9", "pared": "#EFF2F6", "pared_oscura": "#DCE1E9",
                         "azul_sombra": "#CFD7E3", "metal": "#C4CAD3", "gris_claro": "#DDE1E7", "naranja": "#F39A26",
                         "amarillo": "#F6C430", "azul": "#2F6FE4", "cielo": "#8EC2FF", "rojo": "#E2483A", "lima": "#B8E83A",
                         "blanco_hueso": "#FAFBFC", "gris_oscuro": "#3A3F47", "negro": "#1D2026"},
                 colores=["verde", "morado", "rojo", "naranja", "amarillo", "azul", "cielo", "metal", "gris_claro", "gris_oscuro",
                          "negro", "blanco", "lima"],
                 mapa={"menta": "verde", "verde_agua": "verde", "menta_oscuro": "verde", "violeta": "morado", "agua": "azul",
                       "azul_sombra": "azul", "azul_claro": "cielo", "mostaza": "amarillo", "blanco_hueso": "blanco", "papel": "blanco",
                       "baldosa": "gris_claro", "pared": "gris_claro", "pared_oscura": "metal", "gris": "metal", "rosa": "rojo",
                       "marron": "naranja", "madera": "naranja", "cobre": "naranja", "cafe": "gris_oscuro", "azul_base": "azul",
                       "azul_neon": "azul", "cian": "cielo"},
                 lateral=None, tinta=1.3, temblor=0.0, papel=False, paredes=False, juntas=True, bisel=False,
                 fx_reloj="naranja", fx_ondas="azul", pantalla="negro", marco="gris_oscuro", peanas=True, neon=True, iconos=False,
                 manguera="azul_neon", carteles="todos", resalte=1.5,
                 guia="TEMA NEON: cada componente principal se apoya en su PEANA (forma 'peana', alto 0.04, ancho y fondo 0.12-0.25 m "
                      "mayores que el componente, en z=0) y el componente va encima, con su z = 0.04; los componentes pequenos que "
                      "van juntos comparten una peana. Un color vivo distinto por componente (servidor del agente verde, base de "
                      "datos morada, funciones naranja o amarillo, fallos y alertas rojo, nube azul, servidores y cajas de metal). "
                      "Las mangueras (azules de neon) van de borde a borde de los componentes a z=0.06-0.1, pegadas a las peanas, "
                      "no por el centro de las piezas. Las peanas y las mangueras toman solas su color (azul_base y azul_neon): no lo "
                      "cambies. No hay objetos-icono: los componentes se modelan con primitivas."),
}
PARAMS.insert(1, ("tema", "MENU", "clasico", list(TEMAS_TECNICOS),
                  "estilo tecnico: clasico (papel, paleta apagada), iconos (set de iconos isometricos: blanco, azul claro, lima, "
                  "contorno negro) o neon (maqueta de infraestructura sobre peanas luminosas, mangueras de neon, colores vivos)."))
PARAMS_POR_CLAVE = {p[0]: p for p in PARAMS}

def tema_tecnico(params=None):
    return TEMAS_TECNICOS.get((params or {}).get("tema") or "clasico", TEMAS_TECNICOS["clasico"])

def color_tema(c, params=None, defecto="metal"):
    """Color de la paleta tecnica admitido por el tema (los demas se convierten a su equivalente)."""
    t = tema_tecnico(params); c = c if c in PALETA_TECNICA else defecto
    if t["colores"] and c not in t["colores"]: c = t["mapa"].get(c, t["colores"][0])
    return c

PALETA_TECNICA = {
    "papel": "#ECE6D8", "baldosa": "#D3CAB8", "pared": "#DAD7D0", "pared_oscura": "#B9B6B0",
    "menta": "#7FCBA6", "menta_oscuro": "#2F6B57", "verde_agua": "#9ED9C4", "lima": "#D7EE57",
    "azul_sombra": "#2C449C", "agua": "#7EA6E6", "azul": "#4F78C9", "cielo": "#BFD3F0",
    "blanco_hueso": "#F3F0E8", "gris_claro": "#D2D4D6", "metal": "#B8BDC2", "gris": "#8C9196",
    "gris_oscuro": "#45494E", "negro": "#232325", "rojo": "#DD4B3E", "naranja": "#E8873A",
    "mostaza": "#EDB42F", "amarillo": "#F2D45C", "rosa": "#E7A1B0", "marron": "#8A5A3C",
    "cafe": "#5A3A24", "madera": "#C9A06A", "cobre": "#C27A4A", "violeta": "#8E7CC3",
    "blanco": "#FCFDFD", "azul_claro": "#BCD6E6",
    "verde": "#3BBF6A", "morado": "#7C5CD9", "azul_base": "#2361DD", "azul_neon": "#3A8DFF", "cian": "#9BE6FF",
}
PALETA.update({k: v for k, v in PALETA_TECNICA.items() if k not in PALETA})   # colores por nombre en gp_base
COLORES_TECNICOS = list(PALETA_TECNICA)

FORMAS = {
    "caja": "prisma: ancho (X), fondo (Y), alto (Z)",
    "cilindro": "cilindro macizo vertical: radio, alto",
    "tubo": "cilindro hueco abierto arriba: radio, alto, grosor de pared",
    "cono": "tronco de cono: radio (abajo), radio2 (arriba), alto",
    "esfera": "esfera: radio",
    "anillo": "toro horizontal: radio (al centro del tubo), grosor (radio del tubo)",
    "disco": "disco plano: radio, alto pequeno",
    "muelle": "resorte vertical: radio, alto, vueltas",
    "varilla": "varilla delgada vertical: radio pequeno, alto",
    "manguera": "tubo flexible por los puntos de 'camino' [[x,y,z],...]: radio",
    "panel": "placa delgada vertical: ancho, alto, grosor (hacia Y)",
    "icono": "objeto-icono prefabricado de 'modelo' (ver MODELOS DE ICONO): 'alto' es su TAMANO (su dimension mayor); "
             "'color' es el cuerpo y 'acento' el de los detalles (lima por defecto); el frente mira a -Y",
    "peana": "base luminosa (tema neon): losa de esquinas redondeadas con el borde que brilla: ancho, fondo, alto (0.03-0.05)",
}
MATERIALES_PIEZA = {"solido": "opaco con sombreado en bandas", "metal": "opaco con brillo",
                    "transparente": "cristal o plastico transparente (deja ver el interior)", "liquido": "agua u otro liquido translucido"}
DETALLES_PIEZA = {"liso": "", "perforado": "agujeros en la pared (tambor de lavadora, filtro)", "nervado": "anillos o costillas horizontales",
                  "rayado": "lineas verticales", "rejilla": "rejilla (desague, ventilacion)"}
BISAGRAS = ["ninguna", "atras", "delante", "izquierda", "derecha"]
MOVIMIENTOS_PIEZA = {
    "girar": "gira sobre su eje vertical ('cantidad' = vueltas)", "oscilar": "gira a un lado y a otro ('cantidad' = grados)",
    "vibrar": "tiembla", "subir": "sube ('cantidad' = metros)", "bajar": "baja ('cantidad' = metros)",
    "desplazar_x": "se mueve en X ('cantidad' = metros)", "desplazar_y": "se mueve en Y ('cantidad')",
    "llenar": "liquido que sube desde vacio", "vaciar": "liquido que baja hasta vacio",
    "abrir": "gira sobre su bisagra ('cantidad' = grados, 100 por defecto)", "cerrar": "vuelve a cerrar la bisagra",
    "comprimir": "se aplasta en altura (muelles, amortiguadores)",
    "volver": "vuelve a su sitio de reposo desde donde la dejaron subir/bajar/desplazar (que se acumulan entre si)",
}
EFECTOS_TECNICOS = {
    "gotas": "gotas que caen de 'pieza'", "chorro": "chorro de agua que cae dentro de 'pieza' desde arriba",
    "charco": "charco que crece en el suelo junto a 'pieza'", "salpicadura": "salpicaduras alrededor de 'pieza'",
    "burbujas": "burbujas que suben dentro de 'pieza' (liquido)", "vapor": "vapor que sale por arriba de 'pieza'",
    "flecha_giro": "flecha curva alrededor de 'pieza' (sentido de giro)", "flecha_arriba": "flecha que sube junto a 'pieza'",
    "flecha_abajo": "flecha que baja junto a 'pieza'", "llama": "llama bajo 'pieza' (hornillo)", "chispas": "chispas electricas en 'pieza'",
    "flujo": "sobres (mensajes, peticiones, datos) que recorren la manguera 'pieza' del primer al ultimo punto de su camino",
    "flujo_vuelta": "sobres de respuesta (mostaza) que recorren la manguera 'pieza' del ultimo al primer punto",
    "aprobado": "circulo verde con un visto sobre 'pieza' (permitido, correcto)",
    "rechazo": "circulo rojo con una X sobre 'pieza' (denegado, error, fallo)",
    "ondas": "ondas que salen de lo alto de 'pieza' (senales, telemetria, emision)",
    "reloj": "reloj con la aguja girando sobre 'pieza' (espera, tiempo limite, reintento)",
    "alerta": "triangulo de aviso con exclamacion que late sobre 'pieza' (alerta, incidente, alarma)",
    "rayo": "rayo que destella sobre 'pieza' (rapido, instantaneo: acierto de cache, respuesta reutilizada)",
}
ACCESORIOS_TECNICOS = {"alfombra": "alfombrilla en el suelo", "jabon": "pastilla de jabon", "desague": "rejilla de desague en el suelo",
                       "hornillo": "hornillo de gas (para cafeteras, ollas)", "enchufe": "enchufe en la pared", "maceta": "planta en maceta",
                       "cubo": "cubo de plastico", "toalla": "toalla doblada"}
PLANOS_TECNICOS = {"general": "objeto entero y su entorno", "medio": "el objeto llenando el cuadro", "detalle": "una pieza de cerca"}
MOVIMIENTOS_CAMARA_TECNICA = {"fijo": "quieta", "acercar": "acercamiento lento", "alejar": "alejamiento lento", "rodear": "gira un poco alrededor"}
SUELOS_TECNICOS = {"baldosa": "baldosas claras con juntas", "madera": "tarima", "cemento": "cemento liso"}

def esquema_guion_tecnico():
    S, N, I, B = {"type": "STRING"}, {"type": "NUMBER"}, {"type": "INTEGER"}, {"type": "BOOLEAN"}
    pieza = {"type": "OBJECT", "properties": {
        "id": S, "nombre": S, "forma": _enum(FORMAS), "radio": N, "radio2": N, "alto": N, "ancho": N, "fondo": N, "grosor": N,
        "vueltas": N, "x": N, "y": N, "z": N, "rot_x": N, "rot_y": N, "rot_z": N, "color": _enum(COLORES_TECNICOS),
        "modelo": _enum(["ninguno"] + ICO.LISTA), "acento": _enum(COLORES_TECNICOS),
        "material": _enum(MATERIALES_PIEZA), "detalle": _enum(DETALLES_PIEZA), "padre": S, "bisagra": _enum(BISAGRAS),
        "camino": {"type": "ARRAY", "items": {"type": "ARRAY", "items": N}}},
        # medidas obligatorias para todas (las que la forma no usa se ignoran): sin esto Gemini omite 'alto' y 'camino'
        "required": ["id", "nombre", "forma", "modelo", "x", "y", "z", "ancho", "fondo", "alto", "radio", "camino", "color", "material"],
        "propertyOrdering": ["id", "nombre", "forma", "modelo", "x", "y", "z", "ancho", "fondo", "alto", "radio", "radio2", "grosor", "vueltas",
                             "camino", "rot_x", "rot_y", "rot_z", "color", "acento", "material", "detalle", "padre", "bisagra"]}
    accesorio = {"type": "OBJECT", "properties": {"tipo": _enum(ACCESORIOS_TECNICOS), "x": N, "y": N, "color": _enum(COLORES_TECNICOS)},
                 "required": ["tipo", "x", "y"]}
    linea = {"type": "OBJECT", "properties": {"texto": S, "emocion": _enum(EMOCIONES)}, "required": ["texto"]}
    anim = {"type": "OBJECT", "properties": {"pieza": S, "movimiento": _enum(MOVIMIENTOS_PIEZA), "inicio": N, "fin": N, "cantidad": N},
            "required": ["pieza", "movimiento", "inicio", "fin"], "propertyOrdering": ["pieza", "movimiento", "inicio", "fin", "cantidad"]}
    efecto = {"type": "OBJECT", "properties": {"tipo": _enum(EFECTOS_TECNICOS), "pieza": S, "momento": N, "duracion": N},
              "required": ["tipo", "pieza", "momento"], "propertyOrdering": ["tipo", "pieza", "momento", "duracion"]}
    escena = {"type": "OBJECT", "properties": {
        "id": I, "descripcion": S, "lineas": {"type": "ARRAY", "items": linea},
        "aparecen": {"type": "ARRAY", "items": S}, "desaparecen": {"type": "ARRAY", "items": S},
        "rayos_x": {"type": "ARRAY", "items": S}, "resaltar": {"type": "ARRAY", "items": S},
        "animaciones": {"type": "ARRAY", "items": anim}, "efectos": {"type": "ARRAY", "items": efecto},
        "camara": {"type": "OBJECT", "properties": {"plano": _enum(PLANOS_TECNICOS), "objetivo": S,
                                                     "objetivos": {"type": "ARRAY", "items": S},
                                                     "movimiento": _enum(MOVIMIENTOS_CAMARA_TECNICA)}, "required": ["plano", "objetivo", "movimiento"]},
        "duracion_minima": N},
        "required": ["id", "descripcion", "lineas", "aparecen", "rayos_x", "resaltar", "animaciones", "efectos", "camara"],
        "propertyOrdering": ["id", "descripcion", "lineas", "aparecen", "desaparecen", "rayos_x", "resaltar", "animaciones", "efectos",
                             "camara", "duracion_minima"]}
    return {"type": "OBJECT", "properties": {
        "titulo": S, "sinopsis": S, "objeto": {"type": "OBJECT", "properties": {"nombre": S, "alto": N}, "required": ["nombre", "alto"]},
        "suelo": _enum(SUELOS_TECNICOS), "piezas": {"type": "ARRAY", "items": pieza},
        "accesorios": {"type": "ARRAY", "items": accesorio}, "escenas": {"type": "ARRAY", "items": escena}},
        "required": ["titulo", "sinopsis", "objeto", "suelo", "piezas", "accesorios", "escenas"],
        "propertyOrdering": ["titulo", "sinopsis", "objeto", "suelo", "piezas", "accesorios", "escenas"]}

def vocabulario_tecnico(params=None):
    def tabla(d): return "; ".join(f"{k}: {v}" for k, v in d.items())
    t = tema_tecnico(params)
    colores = (f"COLORES (tema {(params or {}).get('tema')}: {t['desc']}; usa SOLO estos): {', '.join(t['colores'])}" if t["colores"] else
               f"COLORES (paleta apagada): {', '.join(COLORES_TECNICOS)}")
    formas = {k: v for k, v in FORMAS.items() if (k != "icono" or t["iconos"]) and (k != "peana" or t["peanas"])}
    iconos = ([f"MODELOS DE ICONO (forma 'icono'; en las demas formas modelo='ninguno'): {ICO.vocabulario()}"] if t["iconos"]
              else ["(sin objetos-icono en este tema: modelo='ninguno' en todas las piezas)"])
    return "\n".join([f"FORMAS: {tabla(formas)}"] + iconos + ([t["guia"]] if t["guia"] else []) + [f"MATERIALES: {tabla(MATERIALES_PIEZA)}", f"DETALLES: {tabla(DETALLES_PIEZA)}",
                      f"BISAGRAS: {', '.join(BISAGRAS)}", f"MOVIMIENTOS DE PIEZA: {tabla(MOVIMIENTOS_PIEZA)}",
                      f"EFECTOS: {tabla(EFECTOS_TECNICOS)}", f"ACCESORIOS: {tabla(ACCESORIOS_TECNICOS)}",
                      f"PLANOS: {tabla(PLANOS_TECNICOS)} (camara.objetivos opcional: lista de ids para encuadrar una zona o grupo de piezas)", f"MOVIMIENTOS DE CAMARA: {tabla(MOVIMIENTOS_CAMARA_TECNICA)}",
                      f"SUELOS: {tabla(SUELOS_TECNICOS)}", colores,
                      f"EMOCIONES de la voz: {', '.join(EMOCIONES)}"])

DIMS_DEFECTO = {"caja": dict(ancho=0.6, fondo=0.6, alto=0.6), "cilindro": dict(radio=0.3, alto=0.6), "tubo": dict(radio=0.4, alto=0.8, grosor=0.03),
                "cono": dict(radio=0.3, radio2=0.1, alto=0.5), "esfera": dict(radio=0.25), "anillo": dict(radio=0.4, grosor=0.05),
                "disco": dict(radio=0.35, alto=0.04), "muelle": dict(radio=0.08, alto=0.4, vueltas=8), "varilla": dict(radio=0.015, alto=0.6),
                "manguera": dict(radio=0.03), "panel": dict(ancho=0.8, alto=1.0, grosor=0.03), "icono": dict(alto=0.6),
                "peana": dict(ancho=0.8, fondo=0.8, alto=0.04)}

def validar_guion_tecnico(g, params=None):
    av = []; g = copy.deepcopy(g or {})
    out = {"estilo": "tecnico", "titulo": str(g.get("titulo") or "Como funciona")[:80], "sinopsis": str(g.get("sinopsis") or "")[:600]}
    ob = g.get("objeto") or {}
    out["objeto"] = dict(nombre=str(ob.get("nombre") or out["titulo"])[:60], alto=_num(ob.get("alto"), 1.2, 0.2, 6.0))
    out["suelo"] = g.get("suelo") if g.get("suelo") in SUELOS_TECNICOS else "baldosa"
    out["tema"] = (params or {}).get("tema") or "clasico"
    piezas, ids = [], set()
    for i, p in enumerate(g.get("piezas") or []):
        forma = p.get("forma") if p.get("forma") in FORMAS or (p.get("forma") == "malla" and p.get("partes")) else None
        if not forma: av.append(f"pieza {p.get('id')}: forma {p.get('forma')!r} desconocida"); continue
        pid = slug(p.get("id") or f"pieza_{i + 1}", 30)
        while pid in ids: pid += "_b"
        ids.add(pid)
        d = dict(DIMS_DEFECTO.get(forma, {}))
        q = dict(id=pid, nombre=str(p.get("nombre") or pid)[:40], forma=forma,
                 x=_num(p.get("x"), 0, -5, 5), y=_num(p.get("y"), 0, -5, 5), z=_num(p.get("z"), 0, -1, 8),
                 rot_x=_num(p.get("rot_x"), 0, -360, 360), rot_y=_num(p.get("rot_y"), 0, -360, 360), rot_z=_num(p.get("rot_z"), 0, -360, 360),
                 color=color_tema(p.get("color"), params, "blanco" if forma == "icono" else "metal"),
                 material=p.get("material") if p.get("material") in MATERIALES_PIEZA else "solido",
                 detalle=p.get("detalle") if p.get("detalle") in DETALLES_PIEZA else "liso",
                 padre=slug(p.get("padre"), 30) if p.get("padre") else None,
                 bisagra=p.get("bisagra") if p.get("bisagra") in BISAGRAS else "ninguna")
        for k, v in d.items():
            val = p.get(k); val = val if isinstance(val, (int, float)) and val > 0 else None     # 0 = 'no la uso'
            q[k] = _num(val, v, 0.003, 6.0) if k != "vueltas" else _num(val, v, 1, 40)
        if forma == "malla":
            q["partes"] = list(p["partes"]); q["bbox"] = p["bbox"]
        if forma == "icono":
            if p.get("modelo") not in ICO.MODELOS:
                av.append(f"icono {pid}: modelo {p.get('modelo')!r} desconocido: servidor"); q["modelo"] = "servidor"
            else: q["modelo"] = p["modelo"]
            q["acento"] = color_tema(p.get("acento"), params, "lima") if p.get("acento") in PALETA_TECNICA else color_tema("lima", params)
            q["alto"] = _num(q["alto"], 0.6, 0.1, 2.5)
        if forma == "peana": q["color"] = "azul_base"; q["material"] = "solido"
        if forma == "manguera":
            if tema_tecnico(params)["manguera"]: q["color"] = tema_tecnico(params)["manguera"]
            cam = [[_num(c, 0, -6, 8) for c in pt[:3]] for pt in (p.get("camino") or []) if isinstance(pt, list) and len(pt) >= 3]
            if len(cam) < 2: av.append(f"manguera {pid} sin camino: omitida"); ids.discard(pid); continue
            q["camino"] = [[x, y, max(z, q["radio"])] for x, y, z in cam]      # apoyada en el suelo, no medio enterrada
        elif forma != "malla" and q["material"] != "liquido":
            z0 = aabb_pieza(q)[0][2]
            if z0 < -0.01:                        # girada o mal colocada: nada atraviesa el suelo
                q["z"] = round(q["z"] - z0, 4); av.append(f"pieza {pid} bajo el suelo (z0={z0:.2f}): se sube")
        piezas.append(q)
    for q in piezas:   # padres validos y sin ciclos
        if q["padre"] not in ids or q["padre"] == q["id"]: q["padre"] = None
    padres = {q["id"]: q["padre"] for q in piezas}
    for q in piezas:
        vistos, a = set(), q["id"]
        while padres.get(a):
            if a in vistos: av.append(f"ciclo de padres en {q['id']}"); q["padre"] = None; padres[q["id"]] = None; break
            vistos.add(a); a = padres[a]
    if not piezas: av.append("el guion no tiene piezas")
    out["piezas"] = piezas
    out["accesorios"] = [dict(tipo=a["tipo"], x=_num(a.get("x"), 1.5, -6, 6), y=_num(a.get("y"), -1, -6, 6),
                              color=color_tema(a.get("color"), params) if a.get("color") in PALETA_TECNICA else None)
                         for a in g.get("accesorios") or [] if a.get("tipo") in ACCESORIOS_TECNICOS][:8]
    escenas = []
    def ids_validos(lst): return [slug(x, 30) for x in (lst or []) if slug(x, 30) in ids]
    for i, s in enumerate(g.get("escenas") or []):
        cam = s.get("camara") or {}
        obj = slug(cam.get("objetivo") or "objeto", 30)
        lineas = [dict(quien="narrador", texto=str(l.get("texto") or "").strip()[:400],
                       emocion=l.get("emocion") if l.get("emocion") in EMOCIONES else "neutral")
                  for l in s.get("lineas") or [] if str(l.get("texto") or "").strip()]
        anims = []
        for a in s.get("animaciones") or []:
            pid = slug(a.get("pieza"), 30)
            if pid not in ids or a.get("movimiento") not in MOVIMIENTOS_PIEZA: continue
            ini = _num(a.get("inicio"), 0, 0, 0.8); fin = _num(a.get("fin"), 1, 0, 1)    # inicio 1 = cuando la escena ya acaba
            if fin < ini + 0.15: fin = min(1.0, ini + 0.4)
            anims.append(dict(pieza=pid, movimiento=a["movimiento"], inicio=ini, fin=fin, cantidad=a.get("cantidad")))
        efectos = [dict(tipo=e["tipo"], pieza=slug(e.get("pieza"), 30), momento=_num(e.get("momento"), 0.3, 0, 0.75),
                        duracion=_num(e.get("duracion"), 2.0, 0.3, 20))
                   for e in s.get("efectos") or [] if e.get("tipo") in EFECTOS_TECNICOS and slug(e.get("pieza"), 30) in ids]
        escenas.append(dict(id=i + 1, descripcion=str(s.get("descripcion") or "")[:300], lineas=lineas,
                            aparecen=ids_validos(s.get("aparecen")), desaparecen=ids_validos(s.get("desaparecen")),
                            rayos_x=ids_validos(s.get("rayos_x")), resaltar=ids_validos(s.get("resaltar")),
                            animaciones=anims, efectos=efectos, acciones=[], presentes=[],
                            camara=dict(plano=cam.get("plano") if cam.get("plano") in PLANOS_TECNICOS else "general",
                                        objetivo=obj if obj in ids else "objeto", objetivos=ids_validos(cam.get("objetivos"))[:12],
                                        movimiento=cam.get("movimiento") if cam.get("movimiento") in MOVIMIENTOS_CAMARA_TECNICA else "fijo"),
                            duracion_minima=_num(s.get("duracion_minima"), 3.0, 1.0, 30.0)))
    if not escenas: av.append("el guion no tiene escenas")
    out["escenas"] = escenas
    out["personajes"] = []; out["escenarios"] = []
    return out, av

def guion_ejemplo_tecnico():
    return {
        "titulo": "Así funciona la cafetera italiana", "sinopsis": "El vapor empuja el agua a través del café y sube por la chimenea.",
        "objeto": {"nombre": "cafetera italiana", "alto": 1.6}, "suelo": "baldosa",
        "piezas": [
            {"id": "hornillo_base", "nombre": "hornillo", "forma": "cilindro", "radio": 0.55, "alto": 0.12, "x": 0, "y": 0, "z": 0, "color": "gris_oscuro", "material": "metal"},
            {"id": "deposito", "nombre": "depósito de agua", "forma": "tubo", "radio": 0.42, "alto": 0.62, "grosor": 0.03, "x": 0, "y": 0, "z": 0.12, "color": "metal", "material": "metal", "detalle": "rayado"},
            {"id": "agua", "nombre": "agua", "forma": "cilindro", "radio": 0.39, "alto": 0.4, "x": 0, "y": 0, "z": 0.15, "color": "agua", "material": "liquido", "padre": "deposito"},
            {"id": "valvula", "nombre": "válvula de seguridad", "forma": "cilindro", "radio": 0.05, "alto": 0.08, "x": 0.42, "y": 0, "z": 0.5, "rot_y": 90, "color": "cobre", "material": "metal", "padre": "deposito"},
            {"id": "filtro", "nombre": "embudo filtro", "forma": "cono", "radio": 0.06, "radio2": 0.38, "alto": 0.42, "x": 0, "y": 0, "z": 0.32, "color": "metal", "material": "metal", "detalle": "perforado", "padre": "deposito"},
            {"id": "cafe_molido", "nombre": "café molido", "forma": "disco", "radio": 0.36, "alto": 0.06, "x": 0, "y": 0, "z": 0.68, "color": "cafe", "material": "solido", "padre": "filtro"},
            {"id": "superior", "nombre": "jarra superior", "forma": "tubo", "radio": 0.44, "alto": 0.62, "grosor": 0.03, "x": 0, "y": 0, "z": 0.76, "color": "metal", "material": "metal", "detalle": "rayado"},
            {"id": "chimenea", "nombre": "chimenea", "forma": "cilindro", "radio": 0.05, "alto": 0.42, "x": 0, "y": 0, "z": 0.78, "color": "gris", "material": "metal", "padre": "superior"},
            {"id": "cafe_arriba", "nombre": "café", "forma": "cilindro", "radio": 0.41, "alto": 0.24, "x": 0, "y": 0, "z": 0.8, "color": "cafe", "material": "liquido", "padre": "superior"},
            {"id": "asa", "nombre": "asa", "forma": "caja", "ancho": 0.08, "fondo": 0.1, "alto": 0.45, "x": -0.48, "y": 0, "z": 0.86, "color": "negro", "material": "solido", "padre": "superior"},
            {"id": "tapa", "nombre": "tapa", "forma": "disco", "radio": 0.45, "alto": 0.05, "x": 0, "y": 0, "z": 1.38, "color": "metal", "material": "metal", "padre": "superior", "bisagra": "atras"}],
        "accesorios": [{"tipo": "alfombra", "x": 1.4, "y": -0.9, "color": "mostaza"}, {"tipo": "jabon", "x": -1.3, "y": -0.6, "color": "rosa"}],
        "escenas": [
            {"id": 1, "descripcion": "El depósito de abajo con el agua.", "lineas": [{"texto": "Todo empieza abajo: un depósito con agua fría, justo hasta la válvula.", "emocion": "neutral"}],
             "aparecen": ["hornillo_base", "deposito", "agua", "valvula"], "rayos_x": ["deposito"], "resaltar": ["agua"], "animaciones": [{"pieza": "agua", "movimiento": "llenar", "inicio": 0.2, "fin": 0.7}],
             "efectos": [{"tipo": "chorro", "pieza": "deposito", "momento": 0.15, "duracion": 2.5}], "camara": {"plano": "medio", "objetivo": "deposito", "movimiento": "acercar"}},
            {"id": 2, "descripcion": "Entra el filtro con el café.", "lineas": [{"texto": "Encima va el filtro, un embudo lleno de café molido.", "emocion": "neutral"}],
             "aparecen": ["filtro", "cafe_molido"], "rayos_x": ["deposito"], "resaltar": ["filtro"], "animaciones": [], "efectos": [], "camara": {"plano": "medio", "objetivo": "filtro", "movimiento": "fijo"}},
            {"id": 3, "descripcion": "Se enrosca la parte de arriba.", "lineas": [{"texto": "Y arriba, la jarra con su chimenea, que todavía está vacía.", "emocion": "neutral"}],
             "aparecen": ["superior", "chimenea", "cafe_arriba", "asa", "tapa"], "rayos_x": ["deposito", "superior"], "resaltar": ["chimenea"],
             "animaciones": [{"pieza": "cafe_arriba", "movimiento": "vaciar", "inicio": 0.0, "fin": 0.05}], "efectos": [], "camara": {"plano": "general", "objetivo": "objeto", "movimiento": "rodear"}},
            {"id": 4, "descripcion": "El calor hace vapor que empuja el agua.", "lineas": [{"texto": "Con el fuego, el vapor empuja el agua hacia arriba a través del café.", "emocion": "emocionado"}],
             "aparecen": [], "rayos_x": ["deposito", "superior"], "resaltar": [], "animaciones": [{"pieza": "agua", "movimiento": "vaciar", "inicio": 0.2, "fin": 0.95},
             {"pieza": "cafe_arriba", "movimiento": "llenar", "inicio": 0.3, "fin": 1.0}, {"pieza": "deposito", "movimiento": "vibrar", "inicio": 0.1, "fin": 0.9}],
             "efectos": [{"tipo": "llama", "pieza": "hornillo_base", "momento": 0.0, "duracion": 8}, {"tipo": "burbujas", "pieza": "agua", "momento": 0.1, "duracion": 6},
                         {"tipo": "flecha_arriba", "pieza": "chimenea", "momento": 0.3, "duracion": 3}], "camara": {"plano": "general", "objetivo": "objeto", "movimiento": "fijo"}},
            {"id": 5, "descripcion": "Sale el vapor por arriba.", "lineas": [{"texto": "Cuando borbotea, el café ya está listo. ¡A servir!", "emocion": "alegre"}],
             "aparecen": [], "rayos_x": ["superior"], "resaltar": [], "animaciones": [{"pieza": "tapa", "movimiento": "abrir", "inicio": 0.1, "fin": 0.5, "cantidad": 100}],
             "efectos": [{"tipo": "vapor", "pieza": "superior", "momento": 0.3, "duracion": 3}], "camara": {"plano": "medio", "objetivo": "superior", "movimiento": "alejar"}},
        ]}

# ---------------------------------------------------------------- comprobaciones de geometria (sin bpy)
MEDIDAS_FORMA = {"caja": ("ancho", "fondo", "alto"), "panel": ("ancho", "alto", "grosor"), "cilindro": ("radio", "alto"),
                 "tubo": ("radio", "alto"), "cono": ("radio", "radio2", "alto"), "esfera": ("radio",), "anillo": ("radio", "grosor"),
                 "disco": ("radio", "alto"), "muelle": ("radio", "alto"), "varilla": ("radio", "alto"), "manguera": ("radio",),
                 "icono": ("alto",), "peana": ("ancho", "fondo", "alto")}

def medidas_faltantes(bruto):
    """Piezas del guion SIN validar a las que les falta alguna medida de su forma (el validador pondria las de defecto)."""
    av = []
    for p in (bruto or {}).get("piezas") or []:
        falta = [k for k in MEDIDAS_FORMA.get(p.get("forma"), ()) if not (isinstance(p.get(k), (int, float)) and p.get(k) > 0)]
        if p.get("forma") == "manguera" and len(p.get("camino") or []) < 2: falta.append("camino")
        if falta:
            d = DIMS_DEFECTO.get(p.get("forma"), {})
            av.append(f"'{p.get('id')}' ({p.get('forma')}) sin {', '.join(falta)}: se usaria " + ", ".join(f"{k}={d.get(k)}" for k in falta))
    return av

def _rot(v, rx, ry, rz):
    x, y, z = v
    for eje, a in (("x", rx), ("y", ry), ("z", rz)):          # Euler XYZ, como Blender
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        if eje == "x": y, z = y * c - z * s, y * s + z * c
        elif eje == "y": x, z = x * c + z * s, -x * s + z * c
        else: x, y = x * c - y * s, x * s + y * c
    return x, y, z

def aabb_pieza(p):
    f = p["forma"]
    if f == "malla": return list(p["bbox"][0]), list(p["bbox"][1])
    if f == "manguera":
        pts = p["camino"]; r = p["radio"]
        return [min(q[i] for q in pts) - r for i in range(3)], [max(q[i] for q in pts) + r for i in range(3)]
    if f == "icono":
        c0, c1 = ICO.caja_local(p["modelo"], p["alto"])
        loc = [(x, y, z) for x in (c0[0], c1[0]) for y in (c0[1], c1[1]) for z in (c0[2], c1[2])]
    elif f in ("caja", "panel", "peana"):
        a = p["ancho"] / 2; b = (p["fondo"] if f in ("caja", "peana") else p["grosor"]) / 2; h = p["alto"]
        loc = [(x, y, z) for x in (-a, a) for y in (-b, b) for z in (0, h)]
    elif f == "esfera": r = p["radio"]; loc = [(x, y, z) for x in (-r, r) for y in (-r, r) for z in (0, 2 * r)]
    elif f == "anillo": r = p["radio"] + p["grosor"]; loc = [(x, y, z) for x in (-r, r) for y in (-r, r) for z in (0, 2 * p["grosor"])]
    else:
        r = max(p.get("radio", 0.1), p.get("radio2", 0) if f == "cono" else 0); h = p.get("alto", 0.1)
        loc = [(x, y, z) for x in (-r, r) for y in (-r, r) for z in (0, h)]
    w = [_rot(v, p["rot_x"], p["rot_y"], p["rot_z"]) for v in loc]
    w = [(x + p["x"], y + p["y"], z + p["z"]) for x, y, z in w]
    return [min(q[i] for q in w) for i in range(3)], [max(q[i] for q in w) for i in range(3)]

def revisar_geometria(g, tol=0.04):
    """Avisos numericos para el guion tecnico: piezas que flotan sin apoyo y palancas o brazos de pie."""
    av = []; cajas = {p["id"]: aabb_pieza(p) for p in g["piezas"]}
    for p in g["piezas"]:
        (x0, y0, z0), (x1, y1, z1) = cajas[p["id"]]
        if p["material"] == "liquido" or z0 <= tol or p["forma"] == "malla": continue
        apoyo = False
        for q in g["piezas"]:
            if q["id"] == p["id"]: continue
            (a0, b0, c0), (a1, b1, c1) = cajas[q["id"]]
            toca = (x0 - tol < a1 and a0 < x1 + tol and y0 - tol < b1 and b0 < y1 + tol and z0 - tol < c1 and c0 < z1 + tol)
            if toca: apoyo = True; break                 # apoyada, metida dentro o sujeta por un lado
        if not apoyo: av.append(f"'{p['id']}' flota: no toca ninguna otra pieza (base a z={z0:.2f})")
    for p in g["piezas"]:
        n = (p["id"] + " " + p["nombre"]).lower()
        if any(k in n for k in ("palanca", "brazo", "barra", "eje horizontal")) and p["forma"] in ("cilindro", "varilla", "caja") \
                and abs(p["rot_x"]) < 30 and abs(p["rot_y"]) < 30:
            (x0, y0, z0), (x1, y1, z1) = cajas[p["id"]]
            if z1 - z0 > 2 * max(x1 - x0, y1 - y0): av.append(f"'{p['id']}' esta de pie (alto {z1 - z0:.2f}); una palanca o brazo suele ir tumbado (rot_y=90 o rot_x=90)")
    # mangueras: que no atraviesen otras piezas y que sus extremos lleguen a alguna
    solidas = [q for q in g["piezas"] if q["forma"] != "manguera" and q["material"] != "liquido"]
    def dentro(pt, caja, m=0.02):      # pegada al suelo por debajo de una pieza tambien cuenta como atravesarla
        return all(caja[0][i] + m < pt[i] < caja[1][i] - m for i in range(2)) and caja[0][2] - 0.03 < pt[2] < caja[1][2] - m
    def dist(pt, caja): return math.sqrt(sum(max(caja[0][i] - pt[i], 0, pt[i] - caja[1][i]) ** 2 for i in range(3)))
    for p in g["piezas"]:
        if p["forma"] != "manguera" or len(p.get("camino") or []) < 2: continue
        cam = p["camino"]; pts = []
        for a_, b_ in zip(cam, cam[1:]): pts += [[a_[i] + (b_[i] - a_[i]) * k / 12 for i in range(3)] for k in range(13)]
        L = len(pts); medio = pts[int(L * 0.15):int(L * 0.85) + 1]
        familia = {p["id"], p.get("padre")} | {q["id"] for q in solidas if min(dist(cam[0], cajas[q["id"]]), dist(cam[-1], cajas[q["id"]])) < 0.08}
        for q in solidas:
            if q["id"] in familia or q.get("padre") == p["id"]: continue
            if any(dentro(pt, cajas[q["id"]]) for pt in medio):
                av.append(f"la manguera '{p['id']}' atraviesa '{q['id']}': rodeala con mas puntos en 'camino'")
        for nombre, pt in (("primer", cam[0]), ("ultimo", cam[-1])):
            empalme = any(math.dist(pt, e) < 0.04 for o in g["piezas"] if o["forma"] == "manguera" and o["id"] != p["id"]
                          for e in ((o.get("camino") or [[9, 9, 9]])[0], (o.get("camino") or [[9, 9, 9]])[-1]))
            if empalme: continue                              # dos mangueras que se unen (p. ej. bajo un arco)
            d = min([dist(pt, cajas[q["id"]]) for q in solidas] or [0])
            if d > 0.08: av.append(f"el {nombre} punto de la manguera '{p['id']}' queda suelto, a {d:.2f} m de la pieza mas cercana")
    xs = [c for b in cajas.values() for c in (b[0][0], b[1][0])]
    if xs and max(xs) - min(xs) > 5.5: av.append(f"el objeto mide {max(xs) - min(xs):.1f} m de ancho: piezas demasiado separadas")
    if TEMAS_TECNICOS.get(g.get("tema") or "clasico", {}).get("peanas"):
        peanas = [q for q in g["piezas"] if q["forma"] == "peana"]
        for p in g["piezas"]:
            if p["forma"] in ("peana", "manguera") or p.get("padre") or p["material"] == "liquido": continue
            (x0, y0, z0), (x1, y1, z1) = cajas[p["id"]]
            if z0 > 0.03 or max(x1 - x0, y1 - y0) < 0.12: continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if not any(cajas[q["id"]][0][0] < cx < cajas[q["id"]][1][0] and cajas[q["id"]][0][1] < cy < cajas[q["id"]][1][1] for q in peanas):
                av.append(f"'{p['id']}' esta en el suelo sin peana: ponle una peana debajo (z de la pieza = alto de la peana)")
    return av + revisar_movimientos(g, cajas)

def _solapan(a, b, m=0.02):
    return all(a[0][i] + m < b[1][i] and b[0][i] + m < a[1][i] for i in range(3))

def revisar_movimientos(g, cajas=None):
    """Piezas que al desplazarse (desplazar_x/y, subir, bajar) atraviesan otra pieza por el camino."""
    cajas = cajas or {p["id"]: aabb_pieza(p) for p in g["piezas"]}
    piezas = {p["id"]: p for p in g["piezas"]}; acum = {}; av = []
    hijos = {}
    for p in g["piezas"]:
        if p.get("padre"): hijos.setdefault(p["padre"], set()).add(p["id"])
    def caja(pid, d): c0, c1 = cajas[pid]; return [[c0[i] + d[i] for i in range(3)], [c1[i] + d[i] for i in range(3)]]
    for e in g["escenas"]:
        moviles = {a["pieza"] for a in e["animaciones"] if a["movimiento"] in ("desplazar_x", "desplazar_y", "subir", "bajar", "volver")}
        for a in sorted(e["animaciones"], key=lambda a: a["inicio"]):
            pid, mov = a["pieza"], a["movimiento"]
            if pid not in cajas or mov not in ("desplazar_x", "desplazar_y", "subir", "bajar", "volver"): continue
            d0 = acum.get(pid, [0.0, 0.0, 0.0]); c = float(a.get("cantidad") if a.get("cantidad") is not None else 0.3)
            v = {"desplazar_x": [c, 0, 0], "desplazar_y": [0, c, 0], "subir": [0, 0, c], "bajar": [0, 0, -c], "volver": [-x for x in d0]}[mov]
            d1 = [d0[i] + v[i] for i in range(3)]; acum[pid] = d1
            if piezas[pid]["forma"] == "manguera": continue
            inicio = caja(pid, d0)
            for q in g["piezas"]:
                qid = q["id"]
                if qid == pid or qid in moviles or q["forma"] == "manguera" or q["material"] == "liquido": continue
                if qid in hijos.get(pid, ()) or piezas[pid].get("padre") == qid: continue
                if _solapan(inicio, cajas[qid]): continue            # ya estaba dentro o encima: es su sitio
                if _solapan(caja(pid, d1), cajas[qid]): continue       # acaba dentro: entra en ella a proposito (un mensaje al LLM)
                if any(_solapan(caja(pid, [d0[i] + v[i] * k / 8 for i in range(3)]), cajas[qid]) for k in range(1, 8)):
                    av.append(f"escena {e['id']}: '{pid}' al hacer {mov} {c:g} atraviesa '{qid}': cambia el destino o el camino "
                              f"(origen y destino uno al lado del otro, sin piezas en medio)")
                    break
    return av


# ---------------------------------------------------------------- guion tecnico sobre un modelo descargado
def esquema_guion_modelo(ids_partes):
    e = esquema_guion_tecnico()
    S = {"type": "STRING"}
    e["properties"]["piezas"] = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "id": S, "nombre": S, "partes": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(ids_partes)}},
        "material": _enum(MATERIALES_PIEZA), "color": _enum(COLORES_TECNICOS), "padre": S, "bisagra": _enum(BISAGRAS)},
        "required": ["id", "nombre", "partes", "material", "color"]}}
    return e

def validar_guion_modelo(g, modelo, params=None):
    """Piezas = grupos de partes del modelo (forma 'malla'). Cada parte en una sola pieza; lo no asignado va a 'resto'."""
    g = copy.deepcopy(g or {}); av = []
    partes = {q["id"]: q for q in modelo["partes"]}; asignadas = set(); piezas = []
    def caja(ids):
        c0 = [min(partes[i]["bbox"][0][k] for i in ids) for k in range(3)]; c1 = [max(partes[i]["bbox"][1][k] for i in ids) for k in range(3)]
        return [c0, c1]
    for p in g.get("piezas") or []:
        ids = [i for i in p.get("partes") or [] if i in partes and i not in asignadas]
        if not ids: av.append(f"pieza {p.get('id')} sin partes validas: omitida"); continue
        asignadas |= set(ids); b = caja(ids)
        mayor = max(ids, key=lambda i: len(partes[i]["caras"]))
        piezas.append(dict(id=p.get("id"), nombre=p.get("nombre") or p.get("id"), forma="malla", partes=ids, bbox=b,
                           x=(b[0][0] + b[1][0]) / 2, y=(b[0][1] + b[1][1]) / 2, z=b[0][2],
                           color=p.get("color") if p.get("color") in PALETA_TECNICA else partes[mayor]["color"],
                           material=p.get("material") if p.get("material") in MATERIALES_PIEZA else "solido",
                           padre=p.get("padre"), bisagra=p.get("bisagra") or "ninguna"))
    resto = [i for i in partes if i not in asignadas]
    if resto:
        b = caja(resto); av.append(f"{len(resto)} partes sin pieza: van en 'resto'")
        piezas.append(dict(id="resto", nombre="resto del objeto", forma="malla", partes=resto, bbox=b, x=(b[0][0] + b[1][0]) / 2,
                           y=(b[0][1] + b[1][1]) / 2, z=b[0][2], color=partes[resto[0]]["color"], material="solido"))
    g["piezas"] = piezas
    out, av2 = validar_guion_tecnico(g, params)
    out["modelo"] = True
    return out, av + av2


# ---------------------------------------------------------------- adornos (modo 'detalles' del estilo tecnico)
ADORNOS = {
    "pantalla": "pantalla encendida: marco oscuro, fondo negro y contenido brillante del 'color' (el 'icono' o lineas de texto) con halo",
    "leds": "fila de 'cantidad' luces encendidas con halo",
    "rejilla": "rejilla de ventilacion de lamas",
    "ranuras": "'cantidad' bahias apiladas de rack, cada una con su luz del 'color'",
    "tirador": "asa o tirador metalico en relieve (vertical si alto > ancho)",
    "tornillos": "un tornillo en cada esquina de la zona",
    "franja": "banda de color que cruza la zona",
    "placa": "tapa de acceso atornillada de otro tono",
    "boton": "boton redondo",
    "teclado": "teclado de teclas pequenas (portatiles, consolas)",
    "icono": "'icono' pintado sobre la cara en 'color'",
    "cartel": "cartel encima de la pieza (cara 'arriba') que mira a camara, con un 'icono' en 'color'",
    "conector": "brida metalica en los extremos de una manguera (se anade sola)",
}
ICONOS = ["sobre", "lambda", "candado", "engranaje", "nube", "base_datos", "grafo", "ojo", "rayo", "llave", "documento",
          "chip", "escudo", "check", "cruz", "barras", "traza", "onda", "persona", "reloj", "ninguno"]   # ninguno: pantalla vacia
CARAS_FORMA = {"caja": ["frente", "izquierda", "arriba", "derecha", "atras"], "panel": ["frente", "izquierda", "arriba", "derecha", "atras"],
               "cilindro": ["lado", "arriba"], "tubo": ["lado"], "cono": ["lado", "arriba"], "disco": ["lado", "arriba"],
               "esfera": ["lado"], "varilla": [], "muelle": [], "anillo": [], "manguera": [], "malla": [], "peana": []}
CARAS_ADORNO = ["frente", "izquierda", "derecha", "atras", "arriba", "lado"]
COLOR_ADORNO = {"pantalla": "lima", "leds": "lima", "ranuras": "lima", "tirador": "metal", "tornillos": "metal", "franja": "mostaza",
                "placa": None, "boton": "rojo", "teclado": "gris_oscuro", "icono": "blanco_hueso", "cartel": "naranja", "rejilla": None}
DENSIDADES = {"baja": "1-3 adornos por componente principal", "media": "3-6 adornos por componente principal",
              "alta": "5-9 adornos por componente principal, muy detallado"}

def esquema_adornos():
    S, N, I = {"type": "STRING"}, {"type": "NUMBER"}, {"type": "INTEGER"}
    item = {"type": "OBJECT", "properties": {
        "pieza": S, "tipo": _enum([k for k in ADORNOS if k != "conector"]), "cara": _enum(CARAS_ADORNO), "u": N, "v": N,
        "ancho": N, "alto": N, "color": _enum(COLORES_TECNICOS), "icono": _enum(ICONOS), "cantidad": I},
        "required": ["pieza", "tipo", "cara", "u", "v", "ancho", "alto", "color"],
        "propertyOrdering": ["pieza", "tipo", "cara", "u", "v", "ancho", "alto", "color", "icono", "cantidad"]}
    return {"type": "OBJECT", "properties": {"adornos": {"type": "ARRAY", "items": item}}, "required": ["adornos"]}

def vocabulario_adornos(params=None):
    t = tema_tecnico(params)
    return "\n".join([f"ADORNOS: " + "; ".join(f"{k}: {v}" for k, v in ADORNOS.items() if k != "conector"),
                      f"ICONOS: {', '.join(ICONOS)}",
                      "CARAS por forma: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in CARAS_FORMA.items() if v),
                      f"COLORES (paleta): {', '.join(t['colores'] or COLORES_TECNICOS)}"])

def validar_adornos(bruto, guion, max_pieza=10, params=None):
    """Adornos de Gemini -> lista limpia (pieza, tipo, cara valida para su forma, zona dentro de la cara) + conectores de mangueras."""
    av = []; piezas = {p["id"]: p for p in guion["piezas"]}; out = []; por_pieza = {}
    for a in (bruto or {}).get("adornos") or []:
        pid = slug(a.get("pieza"), 30); t = a.get("tipo")
        if pid not in piezas: av.append(f"adorno en pieza desconocida {a.get('pieza')!r}"); continue
        if t not in ADORNOS or t == "conector": continue
        p = piezas[pid]; caras = CARAS_FORMA.get(p["forma"], [])
        if not caras: av.append(f"{pid}: la forma {p['forma']} no admite adornos"); continue
        if p["material"] in ("liquido",): continue
        cara = a.get("cara") if a.get("cara") in caras else caras[0]
        if t == "cartel": cara = "arriba" if "arriba" in caras else caras[0]
        if por_pieza.get(pid, 0) >= max_pieza: continue
        por_pieza[pid] = por_pieza.get(pid, 0) + 1
        an, al = _num(a.get("ancho"), 0.3, 0.04, 1.0), _num(a.get("alto"), 0.2, 0.04, 1.0)
        u = _num(a.get("u"), 0.5, an / 2, 1 - an / 2) if an < 1 else 0.5
        v = _num(a.get("v"), 0.5, al / 2, 1 - al / 2) if al < 1 else 0.5
        col = color_tema(a.get("color") if a.get("color") in PALETA_TECNICA else (COLOR_ADORNO.get(t) or p["color"]), params)
        ico = a.get("icono") if a.get("icono") in ICONOS else ("sobre" if t in ("icono", "cartel") else None)
        out.append(dict(pieza=pid, tipo=t, cara=cara, u=round(u, 3), v=round(v, 3), ancho=round(an, 3), alto=round(al, 3),
                        color=col, icono=ico, cantidad=int(_num(a.get("cantidad"), 3, 1, 12))))
    for p in guion["piezas"]:         # bridas en los extremos de todas las mangueras opacas
        if p["forma"] == "manguera" and p["material"] in ("solido", "metal"):
            out.append(dict(pieza=p["id"], tipo="conector", cara="extremos", u=0.5, v=0.5, ancho=1, alto=1, color="metal", icono=None, cantidad=2))
    return out, av
