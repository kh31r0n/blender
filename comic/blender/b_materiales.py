# MODO MATERIALES (2/2): construye la biblioteca de materiales Grease Pencil con lo descargado.
#   blender -b -P b_materiales.py -- --descargas DIR_DESCARGAS --salida biblioteca/Materiales_GP.blend [--muestrario png]
# - Paleta viva: Relleno / Plano / Trazo / Semitono / Translucido por color (y variantes claras + y oscuras -)
# - Especiales: Tinta, Tinta blanca, Sombra, Brillo, Papel y Carton (texturas ambientCG CC0), tramas Ben-Day
# - Descargados tal cual: materiales GP oficiales de Blender (Essentials) y, en un archivo aparte por su licencia
#   CC-BY-SA, los de la demo "Bike Ride"; tambien cualquier .blend dejado en descargas/manual/.
# Todos quedan marcados como assets (catalogos en blender_assets.cats.txt) para el Asset Browser.
import os, sys, json, uuid, math, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB
from gp_base import Lapiz, rect, circulo
import comic_parametros as CP

# un solo blender_assets.cats.txt para toda la carpeta biblioteca/ (materiales y escenografia)
CATALOGOS = {"Paleta": None, "Paleta/Relleno": None, "Paleta/Plano": None, "Paleta/Trazo": None, "Paleta/Semitono": None,
             "Especiales": None, "Descargados/Blender Essentials": None, "Descargados/Manual": None,
             "Descargados/Bike Ride (CC-BY-SA)": None, "Escenografia/2D": None, "Escenografia/3D": None,
             "Cielos y suelos/2D": None, "Cielos y suelos/3D": None, "Personajes": None}

def catalogos(carpeta, extra=()):
    ids = {}
    lineas = ["VERSION 1", ""]
    for ruta in list(CATALOGOS) + list(extra):
        u = str(uuid.uuid5(uuid.NAMESPACE_URL, "comic-gp/" + ruta)); ids[ruta] = u
        lineas.append(f"{u}:{ruta}:{ruta.replace('/', '-')}")
    with open(os.path.join(carpeta, "blender_assets.cats.txt"), "w") as f: f.write("\n".join(lineas) + "\n")
    return ids

def marcar(m, cat_id, desc):
    m.asset_mark(); m.asset_data.catalog_id = cat_id; m.asset_data.description = desc
    m.asset_data.author = "agente_comic"

def anexar_materiales(ruta, prefijo=""):
    out = []
    with bpy.data.libraries.load(ruta, link=False) as (src, dst):
        dst.materials = list(src.materials)
    for m in dst.materials:
        if m and m.grease_pencil:
            if prefijo: m.name = prefijo + m.name
            out.append(m)
        elif m:
            bpy.data.materials.remove(m)
    return out

def main():
    a = GB.argumentos()
    desc = a.get("descargas", CP.DESCARGAS)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    params = CP.params_por_defecto(); GB.configurar(params); sc = GB.configurar_escena(params)
    os.makedirs(GB.TEXTURAS, exist_ok=True)
    for t in ("semitono_oscuro", "semitono_claro", "puntos_blancos", "semitono_denso"):
        GB.generar_trama(t)
    ids = catalogos(os.path.dirname(a["salida"]))
    informe = {"paleta": 0, "especiales": 0, "essentials": 0, "manual": 0, "texturas": sorted(os.listdir(GB.TEXTURAS))}
    for c in CP.COLORES:
        for base, cat in (("Relleno", "Paleta/Relleno"), ("Plano", "Paleta/Plano"), ("Trazo", "Paleta/Trazo"), ("Semitono", "Paleta/Semitono")):
            for suf in ("", "+", "-") if base in ("Relleno", "Plano") else ("",):
                m = GB.material(f"{base} {c}{suf}")
                marcar(m, ids[cat], f"{base} {c}{suf}: color de la paleta viva del agente de comic")
                informe["paleta"] += 1
        m = GB.material(f"Translucido {c}"); marcar(m, ids["Paleta/Plano"], "relleno al 45 %"); informe["paleta"] += 1
        m = GB.material(f"Cielo puntos {c}"); marcar(m, ids["Paleta/Semitono"], "trama de puntos blancos (cielos pop)"); informe["paleta"] += 1
    for n in ("Tinta", "Tinta blanca", "Sombra", "Brillo", "Papel", "Carton", "Agujero"):
        marcar(GB.material(n), ids["Especiales"], n); informe["especiales"] += 1
    # oficiales de Blender
    ess = os.path.join(os.path.dirname(bpy.app.binary_path), f"{bpy.app.version[0]}.{bpy.app.version[1]}", "datafiles", "assets", "brushes")
    for f in sorted(glob.glob(os.path.join(ess, "essentials_brushes-gp_*.blend"))):
        for m in anexar_materiales(f, "Essentials · "):
            marcar(m, ids["Descargados/Blender Essentials"], f"Material GP oficial de Blender ({os.path.basename(f)})"); informe["essentials"] += 1
    # dejados a mano (p. ej. packs gratuitos de Gumroad que piden correo)
    for f in sorted(glob.glob(os.path.join(desc, "manual", "*.blend"))):
        for m in anexar_materiales(f, os.path.splitext(os.path.basename(f))[0] + " · "):
            marcar(m, ids["Descargados/Manual"], f"De {os.path.basename(f)} (revisa su licencia)"); informe["manual"] += 1
    # muestrario
    ob = GB.nuevo_gp("Muestrario"); mats = [m for m in bpy.data.materials if m.grease_pencil and m.asset_data]
    lp = Lapiz(ob, "muestras"); cols = 16
    for i, m in enumerate(mats):
        r, c = divmod(i, cols); x, z = c * 1.2, -r * 1.2
        if m.grease_pencil.show_fill: lp.forma(rect(x, z, x + 1.0, z + 1.0), m.name, radio=0.03)
        else: lp.linea([(x, 0, z + 0.2), (x + 0.5, 0, z + 0.8), (x + 1.0, 0, z + 0.3)], m.name, radio=0.06)
    ob.use_fake_user = True
    GB.guardar(a["salida"])
    # aparte: los materiales CC-BY-SA de la demo Bike Ride
    bike = os.path.join(desc, "blender_demo", "greasepencil-bike.blend")
    if os.path.exists(bike) and a.get("salida_bike"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ids_b = catalogos(os.path.dirname(a["salida_bike"]))
        ms = anexar_materiales(bike, "Bike · ")
        for m in ms: marcar(m, ids_b["Descargados/Bike Ride (CC-BY-SA)"], "Demo Bike Ride de Dedouze, CC-BY-SA (atribucion y compartir igual)")
        bpy.ops.wm.save_as_mainfile(filepath=a["salida_bike"], compress=True)
        informe["bike"] = len(ms)
    if a.get("muestrario"):
        bpy.ops.wm.open_mainfile(filepath=a["salida"])
        sc = bpy.context.scene; ob = bpy.data.objects.get("Muestrario")
        if ob and ob.name not in sc.collection.objects: sc.collection.objects.link(ob)
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
        n = len([m for m in bpy.data.materials if m.grease_pencil and m.asset_data]); filas = math.ceil(n / 16)
        W, Hh = 19.6, filas * 1.2 + 0.4                 # la escala ortografica se aplica a la dimension mayor
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(W, Hh)
        cam.location = (9.6, -10, (1.2 - (filas - 1) * 1.2) / 2); cam.rotation_euler = (math.pi / 2, 0, 0)
        sc.render.resolution_x, sc.render.resolution_y = 1600, int(1600 * Hh / W); sc.render.resolution_percentage = 100
        GB.render_fotograma(a["muestrario"], 1, sc)
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
