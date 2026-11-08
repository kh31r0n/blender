# Junta las tres mascaras CC0 de ambientCG en una sola imagen RGB para el shader "LEGO realista" (una lectura de
# textura en vez de tres): R = huellas (solo en algunas manchas), G = arañazos, B = polvo.
# Uso: python3 -I ~/blender/buildings/scripts/empaquetar_imperfecciones.py   (necesita Pillow)
from PIL import Image, ImageFilter, ImageChops
import os, random

B = os.path.expanduser("~/blender/buildings/descargas/cc0")
OUT = os.path.join(B, "imperfecciones_lego_2k.png")
N = 2048

def gris(f): return Image.open(os.path.join(B, f)).convert("L").resize((N, N))
def rango(im, lo, hi):   # (v - lo) / (hi - lo), recortado a 0..255
    return im.point(lambda v: max(0, min(255, int((v / 255 - lo) / (hi - lo) * 255))))

def manchas(semilla=7, celdas=6, lo=0.52, hi=0.66):
    # Rejilla aleatoria repetida 3x3 y suavizada; se recorta la del centro para que la baldosa no tenga costura
    rnd = random.Random(semilla); g = Image.new("L", (celdas, celdas))
    g.putdata([rnd.randint(0, 255) for _ in range(celdas * celdas)])
    t = Image.new("L", (3 * celdas, 3 * celdas))
    for x in range(3):
        for y in range(3): t.paste(g, (x * celdas, y * celdas))
    t = t.resize((3 * N, 3 * N), Image.BICUBIC).crop((N, N, 2 * N, 2 * N)).filter(ImageFilter.GaussianBlur(60))
    return rango(t, lo, hi)

R = ImageChops.multiply(rango(gris("Fingerprints002/Fingerprints002_2K-JPG_Opacity.jpg"), 0.45, 0.9), manchas())
G = rango(gris("Scratches005/Scratches005_2K-JPG_Opacity.jpg"), 0.08, 0.4)
Bc = rango(gris("SurfaceImperfections015/SurfaceImperfections015_2K-JPG_Opacity.jpg"), 0.4, 0.8)
Image.merge("RGB", (R, G, Bc)).save(OUT)
print("guardado", OUT)
