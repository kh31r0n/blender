# MODO 2 · RIG: un esqueleto para cada elemento animable.
#   blender -b 01_objetos.blend -P b_rig.py -- --proyecto DIR --salida DIR/02_rig.blend [--previa png]
# - Personajes: RIG_<id> con 22 huesos (frente y perfil), cada capa emparentada a su hueso (rig de recortes).
# - Escenografia: RIG_<id> con "raiz" (mover, aplastar/estirar desde la base) y las partes del generador
#   (copa de arboles, ruedas de coches, rayos del sol, llama del cohete...).
# - En 3D la restriccion "mirar a camara" (Locked Track) pasa del objeto al rig.
# Comprobacion: la posicion de cada trazo en reposo no cambia al emparentar (se compara antes/despues).
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import gp_base as GB, personajes as PJ
import comic_parametros as CP

def rig_elemento(ob, col_):
    meta = json.loads(ob.get("comic_meta", "{}"))
    alto = meta.get("alto", 1.0)
    huesos = [("raiz", (0, 0), (0, max(0.3, alto * 0.3)), None)]
    capa_hueso = {}
    for pt in meta.get("partes", []):
        h = pt["hueso"]
        if h != "raiz": huesos.append((h, tuple(pt["cabeza"]), tuple(pt["cola"]), pt.get("padre") or "raiz"))
        for c in pt["capas"]: capa_hueso[c] = h
    rig = PJ.crear_armature(f"RIG_{ob.name}", huesos, col_)
    loc, rot, esc = ob.location.copy(), ob.rotation_euler.copy(), ob.scale.copy()
    restr = [(c.type, c.target) for c in ob.constraints]
    for c in list(ob.constraints): ob.constraints.remove(c)
    ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    for L in ob.data.layers:
        L.parent = rig; L.parent_bone = capa_hueso.get(L.name, "raiz")
    rig.location, rig.rotation_euler, rig.scale = loc, rot, esc
    for tipo, tgt in restr:
        c = rig.constraints.new(tipo); c.target = tgt
        if tipo == 'LOCKED_TRACK': c.track_axis = 'TRACK_NEGATIVE_Y'; c.lock_axis = 'LOCK_Z'
    ob.parent = rig; ob.matrix_parent_inverse = rig.matrix_world.inverted()
    rig["comic_tipo"] = "rig_elemento"; rig["comic_id"] = ob.name; rig["comic_meta"] = ob.get("comic_meta", "{}")
    rig["comic_elemento_tipo"] = ob.get("comic_tipo", "")
    ob["comic_rig"] = rig.name
    return rig

def rig_personaje(ob, col_):
    restr = [(c.type, c.target) for c in ob.constraints]
    for c in list(ob.constraints): ob.constraints.remove(c)
    s = ob.scale.copy(); ob.scale = (1, 1, 1)
    rig = PJ.rig_personaje(ob, col_)
    for tipo, tgt in restr:
        c = rig.constraints.new(tipo); c.target = tgt
        if tipo == 'LOCKED_TRACK': c.track_axis = 'TRACK_NEGATIVE_Y'; c.lock_axis = 'LOCK_Z'
    return rig

def bbox_capas_mundo(ob):
    """Caja de los trazos en mundo, aplicando la transformacion de capa (padre) o la del objeto."""
    pts = []
    for L in ob.data.layers:
        if L.hide: continue
        if L.parent is not None:
            pm = L.parent.matrix_world
            if L.parent_bone: pm = pm @ L.parent.pose.bones[L.parent_bone].matrix
            M = pm @ L.matrix_parent_inverse
        else:
            M = ob.matrix_world
        M = M @ L.matrix_local
        for f in L.frames:
            for st in f.drawing.strokes:
                for p in st.points: pts.append(M @ Vector(p.position))
    if not pts: return None
    return [round(min(p[i] for p in pts), 4) for i in range(3)] + [round(max(p[i] for p in pts), 4) for i in range(3)]

def main():
    a = GB.argumentos()
    proy, params = GB.proyecto(a["proyecto"])
    sc = bpy.context.scene
    c_rig = GB.coleccion("Rigs", bpy.data.collections.get("Comic"))
    informe = {"personajes": {}, "elementos": {}, "desvio_max": 0.0}
    antes = {o.name: bbox_capas_mundo(o) for o in bpy.data.objects if o.type == 'GREASEPENCIL' and o.get("comic_tipo") not in ("cielo", "suelo")}
    for ob in [o for o in bpy.data.objects if o.type == 'GREASEPENCIL']:
        t = ob.get("comic_tipo")
        if t == "personaje":
            rig = rig_personaje(ob, c_rig); informe["personajes"][ob.name] = dict(rig=rig.name, huesos=len(rig.data.bones), capas=len(ob.data.layers))
        elif t in CP.ELEMENTOS:
            rig = rig_elemento(ob, c_rig); informe["elementos"][ob.name] = dict(rig=rig.name, huesos=[b.name for b in rig.data.bones])
    bpy.context.view_layer.update()
    for nombre, bb0 in antes.items():
        bb1 = bbox_capas_mundo(bpy.data.objects[nombre])
        if bb0 and bb1:
            d = max(abs(x - y) for x, y in zip(bb0, bb1)); informe["desvio_max"] = max(informe["desvio_max"], round(d, 5))
            if d > 1e-3: informe.setdefault("desviados", {})[nombre] = round(d, 4)
    GB.guardar(a["salida"])
    if a.get("previa"): GB.render_fotograma(a["previa"], 1)
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
