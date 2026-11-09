# SUBTITULOS CON MOTION CANVAS: de tiempos.json a bloques de 3-6 palabras con la palabra que suena resaltada, su
# motion.json (lo dibuja comic/motion/src/escenas/subtitulos.tsx) y el archivo .srt. Sin bpy: lo usa el agente.
#
# Los tiempos por palabra son los mismos que los titulares de los paneles (paneles_mc.palabras_estimadas: cada linea
# repartida por silabas dentro del tramo con voz de su envolvente). Error tipico 0,1-0,2 s.
#
# motion.json (fotogramas de Motion Canvas, 0-based: el f de Blender es el f-1 de aqui):
#   {tipo: 'subtitulos', ancho, alto, fps, frames, orientacion, paleta, banda: {0,0,0,0}, tramos: [], paneles: [],
#    subtitulos: {fs, ancho, x, y, bloques: [{inicio, fin, palabras: [{t, f}]}]}}
import math, os, re, sys

COMIC = os.path.dirname(os.path.abspath(__file__))
if COMIC not in sys.path: sys.path.insert(0, COMIC)
import comic_parametros as CP
import paneles_mc as PM

FUERTE = re.compile(r"[.?!;:…]$")
COMA = re.compile(r",$")

def _texto(pal): return " ".join(w for w, _ in pal)

def _repartir(frase, k):
    """La frase en k trozos de largo parecido: cada corte, en la palabra que deja el trozo mas cerca de su parte justa."""
    out, i = [], 0
    for j in range(k, 1, -1):
        resto = frase[i:]; meta = len(_texto(resto)) / j
        acum, mejor = 0, None
        for m, (w, _) in enumerate(resto[:len(resto) - (j - 1)]):      # deja al menos una palabra a cada trozo
            acum += len(w) + (1 if m else 0)
            if mejor is None or abs(acum - meta) < mejor[0]: mejor = (abs(acum - meta), m + 1)
        out.append(resto[:mejor[1]]); i += mejor[1]
    return out + [frase[i:]]

def _partir(frase, max_pal, max_car):
    """Una frase en el minimo de trozos parecidos que no pasen de max_pal palabras ni de max_car caracteres."""
    k = max(1, math.ceil(len(frase) / max_pal), math.ceil(len(_texto(frase)) / max_car))
    while k < len(frase):
        trozos = _repartir(frase, k)
        if all(len(t) <= max_pal and (len(t) == 1 or len(_texto(t)) <= max_car) for t in trozos): return trozos
        k += 1
    return _repartir(frase, k) if k > 1 else [frase]

def bloques_linea(pal, zona):
    """[(palabra, f)] de una linea -> bloques: se corta tras punto (o coma con 3+ palabras) y cada frase se reparte en
    trozos parecidos de como mucho max_pal palabras y dos lineas de texto."""
    max_car = zona["car_linea"] * zona["lineas"] - 2
    frases, cur = [], []
    for w, f in pal:
        cur.append((w, f))
        if FUERTE.search(w) or (COMA.search(w) and len(cur) >= 3): frases.append(cur); cur = []
    if cur: frases.append(cur)
    unidas = []                       # sin palabra huerfana ('..., resta.'): se une a la frase anterior y se reparte con ella
    for fr in frases:
        if unidas and len(fr) == 1: unidas[-1] = unidas[-1] + fr
        else: unidas.append(fr)
    return [t for fr in unidas for t in _partir(fr, zona["max_pal"], max_car)]

def bloques(tiempos, params):
    """Bloques de subtitulo en fotogramas de Blender: [{inicio, fin, palabras: [{t, f}], texto}] sin solapes."""
    fps = int(tiempos.get("fps") or params.get("fps", 24)); zona = CP.zona_subtitulos(params)
    lineas = [ln for te in tiempos["escenas"] for ln in te.get("lineas") or []]
    out = []
    for ln in lineas:
        pal = PM.palabras_estimadas(ln)
        if not pal: continue
        trozos = bloques_linea(pal, zona)
        for j, t in enumerate(trozos):
            ini = max(1, t[0][1] - 1)                              # un fotograma antes de que suene
            fin = (trozos[j + 1][0][1] - 2) if j + 1 < len(trozos) else int(ln["fin"]) + 3
            out.append(dict(inicio=ini, fin=fin, palabras=[dict(t=w, f=f) for w, f in t], texto=_texto(t)))
    out.sort(key=lambda b: b["inicio"])
    for a, b in zip(out, out[1:]):                                   # sin solapes entre lineas seguidas
        a["fin"] = max(a["inicio"] + 4, min(a["fin"], b["inicio"] - 1))
    frames = int(tiempos.get("frame_fin") or 0)
    if frames and out: out[-1]["fin"] = min(out[-1]["fin"], frames - 1)
    return out

def construir_motion(tiempos, params, bl=None):
    w, h, _ = CP.resolucion(params)
    fps = int(tiempos.get("fps") or params.get("fps", 24))
    frames = int(tiempos.get("frame_fin") or tiempos["escenas"][-1]["fin"] - 1)
    z = CP.zona_subtitulos(params); bl = bloques(tiempos, params) if bl is None else bl
    tema = params.get("tema") or "cyberpunk"
    sub = dict(fs=z["fs"], ancho=z["ancho"], x=z["x"], y=z["y"],
               bloques=[dict(inicio=b["inicio"] - 1, fin=b["fin"] - 1, palabras=[dict(t=p["t"], f=p["f"] - 1) for p in b["palabras"]])
                        for b in bl])
    return dict(tipo="subtitulos", ancho=w, alto=h, fps=fps, frames=frames, orientacion=params.get("orientacion", "horizontal"),
                paleta=CP.PALETA_PANELES.get(tema, CP.PALETA_PANELES["cyberpunk"]), icono_flujo=params.get("icono_flujo", "sobre"),
                banda=dict(x=0, y=0, w=0, h=0), tramos=[], paneles=[], subtitulos=sub)

# ---------------------------------------------------------------- .srt
def _hora(seg):
    ms = int(round(max(0.0, seg) * 1000)); hh, ms = divmod(ms, 3600000); mm, ms = divmod(ms, 60000); ss, ms = divmod(ms, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

def _dos_lineas(texto, maxc=32):
    if len(texto) <= maxc: return texto
    pal = texto.split(); mejor = None
    for i in range(1, len(pal)):
        a, b = " ".join(pal[:i]), " ".join(pal[i:]); d = abs(len(a) - len(b))
        if mejor is None or d < mejor[0]: mejor = (d, a + "\n" + b)
    return mejor[1]

def srt(bl, fps, desplazamiento=0):
    """Texto SRT de los bloques. desplazamiento: fotogramas del video final antes de la pelicula (cartela de titulo)."""
    filas = []
    for i, b in enumerate(bl, 1):
        t0 = (b["inicio"] - 1 + desplazamiento) / fps; t1 = (b["fin"] + desplazamiento) / fps
        filas.append(f"{i}\n{_hora(t0)} --> {_hora(t1)}\n{_dos_lineas(b['texto'])}\n")
    return "\n".join(filas)
