# MARCA: el logo de la empresa en el video (parametro 'marca': carpeta del kit, con png/ y fuentes/static/; vacio = sin
# marca). Reglas de la guia de Vervux (guia/index.html): a color sobre fondos claros (Blanco, Niebla) y la version para
# fondo oscuro sobre oscuro (Tinta, Noche); area de proteccion de 1x alrededor (x = altura de la «v»); horizontal de 96 px
# de ancho como minimo; sin sombras, contornos, efectos, rotaciones ni deformaciones. Sin bpy: PIL con el Python del sistema.
#   capa_esquina  -> PNG transparente del tamano del video con el logo abajo a la derecha, por encima de los subtitulos
#   cartela_cierre -> PNG opaco con el logo vertical grande, la web y los creditos (sustituye a «¡FIN!»)
#   logo_para     -> ruta del PNG del logo adecuado al fondo (las miniaturas lo copian junto a su motion.json)
import os, sys

COMIC = os.path.dirname(os.path.abspath(__file__))
if COMIC not in sys.path: sys.path.insert(0, COMIC)
import comic_parametros as CP

NIEBLA, NOCHE, TINTA = "#F4F5F8", "#10121B", "#1B1E27"
TEMAS_OSCUROS = ("cyberpunk", "cristal")          # la maqueta (y el fondo bajo el logo) es oscura

def activa(params):
    d = (params or {}).get("marca") or ""
    return bool(d) and os.path.isdir(os.path.join(d, "png"))

def escena_clara(params):
    return not (params.get("estilo") == "tecnico" and (params.get("tema") or "clasico") in TEMAS_OSCUROS)

def logo_para(params, claro=True, tipo="horizontal"):
    """PNG del logo: 'horizontal' (2048 px) o 'vertical' (1024 px), a color o para fondo oscuro."""
    png = os.path.join(params["marca"], "png")
    nombre = {("horizontal", True): "vervux-horizontal-2048.png", ("horizontal", False): "vervux-horizontal-fondo-oscuro-2048.png",
              ("vertical", True): "vervux-vertical-1024.png", ("vertical", False): "vervux-vertical-fondo-oscuro-1024.png"}[(tipo, claro)]
    ruta = os.path.join(png, nombre)
    if not os.path.exists(ruta): raise FileNotFoundError(f"falta el logo {ruta}")
    return ruta

def fuente(params, peso="Bold"):
    ruta = os.path.join(params["marca"], "fuentes", "static", f"PlusJakartaSans-{peso}.ttf")
    return ruta if os.path.exists(ruta) else CP.FUENTE_TECNICA

def _hex(c): c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

def capa_esquina(params, salida):
    """Logo horizontal abajo a la derecha, encima de la zona de los subtitulos (si los hay) o del margen de la interfaz
    de las redes. Ancho: 17,5 % del lado corto (189 px en 1080), por encima del minimo de 96 px."""
    from PIL import Image
    w, h, _ = CP.resolucion(params)
    logo = Image.open(logo_para(params, escena_clara(params))).convert("RGBA")
    ancho = max(96, round(min(w, h) * 0.175)); alto = round(logo.height * ancho / logo.width)
    logo = logo.resize((ancho, alto), Image.LANCZOS)
    x_alto = alto * 0.36                                   # x: altura de la «v» (~36 % del alto del logotipo)
    margen = round(max(36, 2 * x_alto))                    # area de proteccion (1x) con holgura
    if CP.subtitulos_activos(params):
        z = CP.zona_subtitulos(params); suelo = z["y"] - z["alto"] / 2 - x_alto * 1.5
    else:
        suelo = h * (1 - (0.12 if params.get("orientacion") == "vertical" else 0.07))
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    capa.alpha_composite(logo, (w - margen - ancho, round(suelo - alto)))
    os.makedirs(os.path.dirname(salida), exist_ok=True); capa.save(salida)
    return dict(ruta=salida, ancho=ancho, alto=alto, x=w - margen - ancho, y=round(suelo - alto))

def cartela_cierre(params, salida, web="", creditos=""):
    """Cierre de marca: fondo Niebla (o Noche en los temas oscuros), el logo vertical en grande, la web debajo en Plus
    Jakarta Sans y los creditos pequenos abajo."""
    from PIL import Image, ImageDraw, ImageFont
    w, h, _ = CP.resolucion(params); claro = escena_clara(params)
    fondo, tinta = (NIEBLA, TINTA) if claro else (NOCHE, "#FFFFFF")
    img = Image.new("RGB", (w, h), _hex(fondo)); d = ImageDraw.Draw(img)
    logo = Image.open(logo_para(params, claro, "vertical")).convert("RGBA")
    ancho = round(min(w, h) * 0.42); alto = round(logo.height * ancho / logo.width)
    logo = logo.resize((ancho, alto), Image.LANCZOS)
    y_logo = round(h * 0.44 - alto / 2)
    img.paste(logo, ((w - ancho) // 2, y_logo), logo)
    if web:
        fw = ImageFont.truetype(fuente(params, "SemiBold"), round(min(w, h) * 0.045))
        bw = d.textbbox((0, 0), web, font=fw)
        d.text(((w - (bw[2] - bw[0])) / 2, y_logo + alto + min(w, h) * 0.07), web, font=fw, fill=_hex(tinta))
    if creditos:
        fc = ImageFont.truetype(fuente(params, "Regular"), round(min(w, h) * 0.017))
        lineas = creditos.split("\n"); y = h * (0.9 if h > w else 0.88)
        for ln in lineas:
            bc = d.textbbox((0, 0), ln, font=fc)
            d.text(((w - (bc[2] - bc[0])) / 2, y), ln, font=fc, fill=_hex("#7C7E86")); y += (bc[3] - bc[1]) * 1.6
    os.makedirs(os.path.dirname(salida), exist_ok=True); img.save(salida)
    return salida
