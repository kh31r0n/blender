# MODO BIBLIOTECA: la escenografia basica reutilizable, ya con rig, como assets de Blender.
#   blender -b -P b_biblioteca.py -- --salida biblioteca/Escenografia_GP.blend [--hojas DIR]
# Una coleccion-asset por elemento y formato ("arbol 2D", "edificio 3D"...) con su objeto Grease Pencil y su
# rig; cielos y suelos de cada ambiente; y seis personajes de muestra con su rig de 22 huesos.
# Desde el Asset Browser se arrastran a cualquier escena; el agente usa los mismos generadores con los
# colores y parametros que pide cada guion.
import os, sys, json, math, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB, escenografia as E, personajes as PJ, b_rig as BR, b_materiales as BM
import comic_parametros as CP

MUESTRAS = [
    dict(id="heroina", nombre="Heroína", tipo="humano", piel="piel_media", ropa="rojo", pantalon="azul", pelo="coleta", color_pelo="chocolate", accesorio="gafas", color_accesorio="magenta", altura=1.0, voz="Leda"),
    dict(id="robot", nombre="Robot", tipo="robot", piel="cian", ropa="naranja", pantalon="gris_oscuro", pelo="calvo", color_pelo="negro", accesorio="ninguno", color_accesorio="oro", altura=0.85, voz="Puck"),
    dict(id="gato", nombre="Gato", tipo="gato", piel="naranja", ropa="verde", pantalon="violeta", pelo="calvo", color_pelo="negro", accesorio="pajarita", color_accesorio="amarillo", altura=0.9, voz="Fenrir"),
    dict(id="perro", nombre="Perro", tipo="perro", piel="beige", ropa="azul", pantalon="rojo", pelo="calvo", color_pelo="negro", accesorio="gorra", color_accesorio="rojo", altura=1.0, voz="Orus"),
    dict(id="monstruo", nombre="Monstruo", tipo="monstruo", piel="lima", ropa="magenta", pantalon="morado", pelo="calvo", color_pelo="negro", accesorio="corona", color_accesorio="oro", altura=1.1, voz="Charon"),
    dict(id="heroe", nombre="Héroe", tipo="humano", piel="piel_oscura", ropa="amarillo", pantalon="magenta", pelo="rizado", color_pelo="negro", accesorio="capa", color_accesorio="violeta", altura=1.0, voz="Achird"),
]

def main():
    a = GB.argumentos()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    params = CP.params_por_defecto(); GB.configurar(params); sc = GB.configurar_escena(params)
    ids = BM.catalogos(os.path.dirname(a["salida"]))
    raiz = GB.coleccion("Biblioteca")
    informe = {"elementos": 0, "cielos_suelos": 0, "personajes": 0}
    for fmt in ("2d", "3d"):
        m3d = fmt == "3d"; cf = GB.coleccion(f"Escenografia {fmt.upper()}", raiz)
        for i, tipo in enumerate(CP.ELEMENTOS):
            c = GB.coleccion(f"{tipo} {fmt.upper()}", cf)
            el = dict(id=f"{tipo}_{fmt}", tipo=tipo, x=0, profundidad="personajes", escala=1.0, color=None, color2=None,
                      texto="", pisos=6, espejo=False)
            ob, meta = E.crear_elemento(el, 0, m3d, c)
            ob.location = (0, 0, 0); ob.scale = (1, 1, 1); ob.constraints.clear()
            rig = BR.rig_elemento(ob, c)
            r, k = divmod(i, 8)
            rig.location = (k * 6.0, -r * 8.0 if m3d else 0, 0 if m3d else -r * 7.0)
            if fmt == "3d": rig.location.x += 60
            c.asset_mark(); c.asset_data.catalog_id = ids[f"Escenografia/{fmt.upper()}"]
            c.asset_data.description = f"{tipo} ({fmt}): {CP.ELEMENTOS[tipo][0]}. Rig: {', '.join(b.name for b in rig.data.bones)}"
            informe["elementos"] += 1
        for cielo in CP.AMBIENTES_CIELO:
            suelo = {"interior": "madera", "espacio": "luna", "noche": "calle", "atardecer": "arena"}.get(cielo, "cesped")
            esc = dict(id=f"{cielo}_{fmt}", cielo=cielo, suelo=suelo, elementos=[], color_pared="crema")
            c = GB.coleccion(f"Ambiente {cielo} {fmt.upper()}", cf)
            o1 = E.crear_cielo(esc, 0, m3d, c, params); o2 = E.crear_suelo(esc, 0, m3d, c)
            for o in (o1, o2): o.location = (0, 0, 0) if m3d else (0, o.location.y, 0)
            c.hide_render = True; c.hide_viewport = True
            c.asset_mark(); c.asset_data.catalog_id = ids[f"Cielos y suelos/{fmt.upper()}"]
            c.asset_data.description = f"Cielo '{cielo}' y suelo '{suelo}' ({fmt})"
            informe["cielos_suelos"] += 1
    cp = GB.coleccion("Personajes", raiz)
    for i, p in enumerate(MUESTRAS):
        c = GB.coleccion(f"Personaje {p['nombre']}", cp)
        ob = PJ.crear_personaje(p, c)
        rig = PJ.rig_personaje(ob, c); rig.location = (i * 1.6, 0, -20)
        c.asset_mark(); c.asset_data.catalog_id = ids["Personajes"]
        c.asset_data.description = (f"{p['nombre']} ({p['tipo']}). Dos vistas (capas F_ frente / P_ perfil), bocas boca_0/1/2, "
                                    f"ojos_cerrados. Rig de {len(rig.data.bones)} huesos; roll a -Y: girar en Z local.")
        informe["personajes"] += 1
    GB.guardar(a["salida"])
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
