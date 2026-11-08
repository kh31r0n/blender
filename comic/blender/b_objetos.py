# MODO 1 · OBJETOS: construye con Grease Pencil todos los objetos que pide el guion.
#   blender -b -P b_objetos.py -- --proyecto DIR --salida DIR/01_objetos.blend
# Cielo y suelo de cada escenario, elementos de escenografia, personajes (dos vistas) y la camara.
# Los escenarios se colocan separados en X (CP.SEPARACION_ESCENARIOS) para que una camara no vea otro.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB, escenografia as E, personajes as PJ, camara as CAM
import comic_parametros as CP

def construir(guion, params):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    GB.configurar(params)
    sc = GB.configurar_escena(params)
    sc.name = "Comic"
    m3d = params["formato"] == "3d"
    raiz = GB.coleccion("Comic")
    c_esc = GB.coleccion("Escenarios", raiz); c_per = GB.coleccion("Personajes", raiz); c_cam = GB.coleccion("Camara", raiz)
    indice = {"escenarios": {}, "elementos": {}, "personajes": {}, "formato": params["formato"]}
    for k, esc in enumerate(guion["escenarios"]):
        x0 = k * CP.SEPARACION_ESCENARIOS
        ce = GB.coleccion(f"Escenario_{esc['id']}", c_esc)
        cielo = E.crear_cielo(esc, x0, m3d, ce, params)
        suelo = E.crear_suelo(esc, x0, m3d, ce)
        noche = esc["cielo"] in ("noche", "espacio")
        indice["escenarios"][esc["id"]] = dict(x0=x0, cielo=cielo.name, suelo=suelo.name)
        for el in esc["elementos"]:
            ob, meta = E.crear_elemento(el, x0, m3d, ce, noche=noche)
            indice["elementos"][el["id"]] = dict(objeto=ob.name, tipo=el["tipo"], escenario=esc["id"], meta=meta)
    # personajes: aparecen donde entran por primera vez
    x_ini = {}
    for escena in guion["escenas"]:
        x0 = indice["escenarios"][escena["escenario"]]["x0"]
        for q in escena["presentes"]:
            x_ini.setdefault(q["actor"], x0 + q["x"])
    for i, p in enumerate(guion["personajes"]):
        ob = PJ.crear_personaje(p, c_per, m3d)
        ob.location = (x_ini.get(p["id"], i * 1.5), 0, 0)
        s = p["altura"]; ob.scale = (s, s, s)
        indice["personajes"][p["id"]] = dict(objeto=ob.name)
    cam, obj = CAM.crear(params, c_cam)
    # vista inicial: la primera escena en plano general
    if guion["escenas"]:
        e0 = guion["escenas"][0]; x0 = indice["escenarios"][e0["escenario"]]["x0"]
        xs = [x0 + q["x"] for q in e0["presentes"]] or [x0]
        enc = CAM.encuadre("general", sum(xs) / len(xs), 1.0, max(xs) - min(xs), params)
        cam.location, obj.location = enc["cam"], enc["obj"]
        if enc["ortho"]: cam.data.ortho_scale = enc["ortho"]
    if m3d:   # lo plano mira siempre a camara
        for ob in list(c_esc.all_objects) + list(c_per.all_objects):
            if ob.get("comic_billboard") or ob.get("comic_tipo") == "personaje":
                c = ob.constraints.new('LOCKED_TRACK'); c.target = cam; c.track_axis = 'TRACK_NEGATIVE_Y'; c.lock_axis = 'LOCK_Z'
    sc["comic_indice"] = json.dumps(indice)
    return indice

if __name__ == "__main__":
    a = GB.argumentos()
    proy, params = GB.proyecto(a["proyecto"])
    guion = GB.leer_json(os.path.join(a["proyecto"], "guion.json"))
    indice = construir(guion, params)
    GB.guardar(a["salida"])
    if a.get("previa"):
        GB.render_fotograma(a["previa"], 1)
    n_gp = sum(1 for o in bpy.data.objects if o.type == 'GREASEPENCIL')
    n_tr = sum(len(f.drawing.strokes) for o in bpy.data.objects if o.type == 'GREASEPENCIL' for L in o.data.layers for f in L.frames)
    print("INFORME " + json.dumps(dict(objetos_gp=n_gp, trazos=n_tr, escenarios=len(indice["escenarios"]),
                                       elementos=len(indice["elementos"]), personajes=len(indice["personajes"])), ensure_ascii=False))
