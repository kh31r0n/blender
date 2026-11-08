# Tabla de parametros del grupo de Geometry Nodes "Desierto LEGO" (v3).
# Clave ASCII (presets JSON y agente) -> socket del modificador. Fuente unica para:
#   crear_desierto_lego_gn_v3.py (crea la interfaz), previa_desierto_v3.py (aplica presets)
#   y agente_desierto_gemini.py (esquema que se envia al modelo). Sin bpy: se importa tambien fuera de Blender.
import json, os

PALETA_JSON = os.path.expanduser("~/blender/buildings/scripts/paleta_mecabricks.json")

# Colores LEGO permitidos en presets (id LEGO -> nombre). Los valores RGBA salen de la paleta de Mecabricks.
COLORES_LEGO = {
    5: "Tan", 138: "Dark Tan", 312: "Medium Nougat", 18: "Nougat", 283: "Light Nougat",
    192: "Reddish Brown", 38: "Dark Orange", 106: "Orange", 217: "Brown", 25: "Earth Orange",
    194: "Light Bluish Gray", 199: "Dark Bluish Gray", 330: "Olive Green", 24: "Yellow",
}

PANELES = ["Terreno", "Dunas", "Erosión", "Rocas", "Arcos", "Materiales"]
TIPOS_DUNA = ["Transversales", "Barjanes", "Estrella"]

# (clave, socket, tipo, defecto, minimo, maximo, panel, descripcion)
# tipo: INT, FLOAT, FACTOR (float 0..1 con deslizador), BOOL, MENU, COLOR (defecto = id LEGO), MATERIAL
PARAMS = [
    ("dimension_x", "Dimensión X", "INT", 1000, 10, 10000, "Terreno",
     "Ancho total del terreno en unidades de Blender (eje X)."),
    ("dimension_y", "Dimensión Y", "INT", 1000, 10, 10000, "Terreno",
     "Largo total del terreno en unidades de Blender (eje Y)."),
    ("resolucion_x", "Resolución X", "INT", 250, 8, 2048, "Terreno",
     "Celdas (studs) a lo largo de X. Fija la cantidad de bloques; el tamaño de pieza es Dimensión X / Resolución X."),
    ("resolucion_y", "Resolución Y", "INT", 250, 8, 2048, "Terreno",
     "Celdas (studs) a lo largo de Y. Fija la cantidad de bloques; el tamaño de pieza es Dimensión Y / Resolución Y."),
    ("semilla", "Semilla", "INT", 7, 0, 99999, "Terreno",
     "Semilla global: cambia dunas, rocas, arcos y colores sin tocar el resto de parámetros."),
    ("escalon_placas", "Altura de escalón (placas)", "INT", 3, 1, 6, "Terreno",
     "Altura de cada nivel del relieve en placas LEGO (3 = un ladrillo, 1 = una placa: escalones más finos)."),
    ("grosor_base", "Grosor de la base (escalones)", "INT", 2, 1, 12, "Terreno",
     "Escalones de zócalo por debajo de la cota 0 en el borde del terreno."),
    ("holgura", "Holgura entre piezas", "FACTOR", 0.02, 0.0, 0.15, "Terreno",
     "Ancho de la junta entre piezas (bisel de las aristas superiores) como fracción del stud. Las piezas siguen "
     "ocupando su celda entera: no se abren ranuras."),
    ("mostrar_studs", "Mostrar studs", "BOOL", True, None, None, "Terreno",
     "Studs en la cara superior de las piezas visibles."),
    ("submuestreo_visor", "Submuestreo en el visor", "INT", 1, 1, 8, "Terreno",
     "Solo en la vista 3D: divide la resolución por este factor para editar con fluidez. El render usa la resolución completa."),

    ("tipo_duna", "Tipo de duna", "MENU", "Transversales", None, None, "Dunas",
     "Transversales: crestas paralelas perpendiculares al viento. Barjanes: medias lunas sueltas con los cuernos a sotavento. "
     "Estrella: picos con brazos en tres direcciones."),
    ("altura_dunas", "Altura de dunas", "FLOAT", 75.0, 0.0, 400.0, "Dunas",
     "Altura máxima de las dunas en unidades de Blender."),
    ("escala_dunas", "Escala de dunas", "FLOAT", 240.0, 20.0, 2000.0, "Dunas",
     "Distancia entre crestas (longitud de onda) en unidades de Blender."),
    ("direccion_viento", "Dirección del viento (°)", "FLOAT", 30.0, 0.0, 360.0, "Dunas",
     "Hacia dónde sopla el viento, en grados desde +X. Las caras de avalancha miran a sotavento."),
    ("asimetria", "Asimetría", "FACTOR", 0.6, 0.0, 1.0, "Dunas",
     "0: dunas simétricas. 1: ladera de barlovento larga y cara de avalancha corta y abrupta."),
    ("agudeza_cresta", "Agudeza de cresta", "FACTOR", 0.5, 0.0, 1.0, "Dunas",
     "0: crestas redondeadas. 1: crestas afiladas con valles anchos y llanos."),
    ("sinuosidad", "Sinuosidad", "FLOAT", 0.6, 0.0, 2.0, "Dunas",
     "Cuánto serpentean las crestas (deformación del dominio con ruido)."),
    ("altura_colinas", "Altura de colinas", "FLOAT", 35.0, 0.0, 400.0, "Dunas",
     "Relieve de fondo de baja frecuencia sobre el que se apoyan las dunas."),
    ("escala_colinas", "Escala de colinas", "FLOAT", 450.0, 50.0, 5000.0, "Dunas",
     "Tamaño de las colinas en unidades de Blender."),
    ("pendientes", "Pendientes en bordes", "BOOL", True, None, None, "Dunas",
     "Pone piezas en cuña (slope) en los escalones de un nivel para suavizar las dunas."),
    ("prob_pendientes", "Probabilidad de pendientes", "FACTOR", 0.85, 0.0, 1.0, "Dunas",
     "Proporción de escalones de un nivel que reciben cuña (en roca se usa la mitad)."),

    ("iteraciones_erosion", "Iteraciones de erosión", "INT", 6, 0, 40, "Erosión",
     "Pasadas de erosión térmica: la arena se desliza donde el desnivel supera el talud."),
    ("talud", "Talud máximo (escalones)", "FLOAT", 1.0, 0.2, 5.0, "Erosión",
     "Desnivel estable entre celdas vecinas, en escalones. Menos = relieve más suave."),
    ("carcavas", "Cárcavas", "FACTOR", 0.35, 0.0, 1.0, "Erosión",
     "Profundidad de los surcos de erosión en rocas y colinas."),
    ("escala_carcavas", "Escala de cárcavas", "FLOAT", 90.0, 10.0, 1000.0, "Erosión",
     "Separación entre surcos en unidades de Blender."),
    ("limpiar_picos", "Limpiar picos sueltos", "BOOL", True, None, None, "Erosión",
     "Elimina columnas de una celda más altas o más bajas que todas sus vecinas."),

    ("densidad_rocas", "Densidad de rocas", "FACTOR", 0.3, 0.0, 1.0, "Rocas",
     "Proporción de celdas de roca que levantan una meseta."),
    ("tamano_rocas", "Tamaño de rocas", "FLOAT", 170.0, 10.0, 1000.0, "Rocas",
     "Separación media entre mesetas en unidades de Blender (su diámetro es aproximadamente la mitad)."),
    ("altura_rocas", "Altura de rocas", "FLOAT", 55.0, 0.0, 300.0, "Rocas",
     "Altura de las mesetas sobre las colinas."),
    ("gradas_mesetas", "Gradas de las mesetas", "INT", 3, 1, 8, "Rocas",
     "Número de terrazas en los costados de cada meseta."),
    ("grosor_estrato", "Grosor de estrato (escalones)", "INT", 1, 1, 10, "Rocas",
     "Grosor de las bandas de color de la roca, en escalones."),
    ("densidad_sueltas", "Densidad de rocas sueltas", "FLOAT", 0.01, 0.0, 0.3, "Rocas",
     "Probabilidad de que una pieza de cima lleve encima una roca suelta."),
    ("tamano_sueltas", "Tamaño de rocas sueltas", "FACTOR", 0.5, 0.0, 1.0, "Rocas",
     "Proporción de rocas sueltas grandes frente a pequeñas."),

    ("densidad_arcos", "Densidad de arcos", "FLOAT", 2.0, 0.0, 20.0, "Arcos",
     "Arcos por cada 1000 × 1000 unidades de terreno (limitado por Máximo de arcos y por el espacio)."),
    ("max_arcos", "Máximo de arcos", "INT", 6, 0, 12, "Arcos",
     "Tope de arcos. 0 desactiva los arcos."),
    ("luz_arco", "Luz del arco", "FLOAT", 120.0, 10.0, 600.0, "Arcos",
     "Distancia entre los ejes de las dos patas, en unidades de Blender."),
    ("altura_arco", "Altura del arco", "FLOAT", 85.0, 10.0, 500.0, "Arcos",
     "Altura de la parte superior del arco sobre su base."),
    ("grosor_arco", "Grosor del arco", "FLOAT", 18.0, 2.0, 150.0, "Arcos",
     "Grosor de la banda del arco (se limita a 0.3 × la menor de luz y altura para que la abertura no se cierre)."),
    ("profundidad_arco", "Profundidad del arco", "FLOAT", 20.0, 2.0, 200.0, "Arcos",
     "Fondo de la banda, perpendicular a la luz."),
    ("redondez_arco", "Redondez del arco", "FLOAT", 2.2, 1.2, 5.0, "Arcos",
     "Exponente de la superelipse: 2 = semielipse, menos = apuntado, más = cuadrado."),
    ("abocinado", "Abocinado de patas", "FLOAT", 0.6, 0.0, 1.5, "Arcos",
     "Cuánto se ensanchan las patas al llegar al suelo."),
    ("erosion_arco", "Erosión del arco", "FACTOR", 0.35, 0.0, 1.0, "Arcos",
     "Mordiscos de erosión en la cara exterior (la abertura y la continuidad de la banda se conservan)."),
    ("variacion_arcos", "Variación de tamaño", "FLOAT", 0.2, 0.0, 0.6, "Arcos",
     "Variación aleatoria de tamaño entre arcos (± fracción)."),
    ("radio_pedestal", "Radio del pedestal", "FLOAT", 28.0, 0.0, 300.0, "Arcos",
     "Radio del montículo de roca que envuelve cada pata. 0 lo desactiva."),

    ("material_arena", "Material arena", "MATERIAL", "Arena LEGO", None, None, "Materiales",
     "Material de las piezas de arena. Lee el color de cada pieza del atributo de instancia color_lego."),
    ("material_roca", "Material roca", "MATERIAL", "Roca LEGO", None, None, "Materiales",
     "Material de las piezas de roca, arcos y rocas sueltas. Lee color_lego."),
    ("color_arena_1", "Color arena principal", "COLOR", 5, None, None, "Materiales", "Color dominante de la arena."),
    ("color_arena_2", "Color arena oscura", "COLOR", 138, None, None, "Materiales",
     "Manchas, zócalo y variaciones de la arena."),
    ("color_arena_3", "Color arena cálida", "COLOR", 312, None, None, "Materiales", "Acentos ocasionales en la arena."),
    ("color_roca_1", "Color roca principal", "COLOR", 312, None, None, "Materiales", "Estrato dominante de la roca."),
    ("color_roca_2", "Color roca clara", "COLOR", 18, None, None, "Materiales", "Estratos claros de la roca."),
    ("color_roca_3", "Color roca oscura", "COLOR", 192, None, None, "Materiales", "Estratos oscuros de la roca."),
    ("color_roca_4", "Color roca acento", "COLOR", 38, None, None, "Materiales", "Piezas sueltas de acento en la roca."),
    ("variacion_color", "Variación de color", "FACTOR", 0.35, 0.0, 1.0, "Materiales",
     "Cantidad de piezas que cambian de color al azar."),
]

POR_CLAVE = {p[0]: p for p in PARAMS}
POR_SOCKET = {p[1]: p for p in PARAMS}


def paleta():
    return {int(k): v for k, v in json.load(open(PALETA_JSON)).items()}


def por_defecto():
    """Preset con los valores por defecto (colores como id LEGO, sin materiales)."""
    return {c: d for c, s, t, d, lo, hi, pan, desc in PARAMS if t != "MATERIAL"}


def limitar(preset):
    """Devuelve una copia del preset con claves conocidas, tipos correctos y valores dentro de rango."""
    out, avisos = {}, []
    for k, v in preset.items():
        if k not in POR_CLAVE:
            avisos.append(f"clave desconocida ignorada: {k}"); continue
        c, s, t, d, lo, hi, pan, desc = POR_CLAVE[k]
        try:
            if t == "MATERIAL":
                avisos.append(f"{k}: los materiales no se cambian desde presets"); continue
            if t == "BOOL":
                v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "si", "sí", "yes")
            elif t == "MENU":
                if v not in TIPOS_DUNA:
                    avisos.append(f"{k}: '{v}' no es un tipo válido, se usa {d}"); v = d
            elif t == "COLOR":
                v = int(v)
                if v not in COLORES_LEGO:
                    avisos.append(f"{k}: color {v} fuera de la paleta permitida, se usa {d}"); v = d
            else:
                v = int(round(float(v))) if t == "INT" else float(v)
                if lo is not None and v < lo: avisos.append(f"{k}: {v} < {lo}"); v = lo
                if hi is not None and v > hi: avisos.append(f"{k}: {v} > {hi}"); v = hi
        except (TypeError, ValueError):
            avisos.append(f"{k}: valor no válido {v!r}, se usa {d}"); v = d
        out[k] = v
    return out, avisos


def esquema():
    """Descripcion de cada parametro para el agente (sin materiales)."""
    filas = []
    for c, s, t, d, lo, hi, pan, desc in PARAMS:
        if t == "MATERIAL": continue
        f = {"clave": c, "socket": s, "tipo": t, "defecto": d, "panel": pan, "descripcion": desc}
        if lo is not None: f["min"] = lo
        if hi is not None: f["max"] = hi
        if t == "MENU": f["opciones"] = TIPOS_DUNA
        if t == "COLOR": f["opciones"] = {str(k): n for k, n in COLORES_LEGO.items()}
        filas.append(f)
    return filas
