# MINIATURAS (estilo tecnico): render del fondo de las miniaturas. La maqueta ya montada (casi al final del video, con
# todo a la vista) en un plano general encuadrado para dejar sitio al titular: arriba en vertical (1080x1920, dentro del
# recorte 3:4 de Reels) y a la izquierda en horizontal (1920x1080). Cycles en la GPU (con mas muestras que el video).
#   blender -b 04b_efectos.blend -P b_miniatura.py -- --proyecto DIR --carpeta DIR
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB
import tecnico as T
import b_tecnico as BT

# (ancho, alto, huecos para el texto, acercamiento): la maqueta, protagonista; en vertical, dentro del recorte 3:4
FORMATOS = {"vertical": (1080, 1920, dict(hueco_arriba=0.42, hueco_abajo=0.12), 0.82),
            "horizontal": (1920, 1080, dict(hueco_izq=0.46), 0.85)}

def main():
    a = GB.argumentos(); dirp = a["proyecto"]; carpeta = a["carpeta"]; os.makedirs(carpeta, exist_ok=True)
    proy, params = GB.proyecto(dirp)
    T.aplicar_tema(params)
    sc = bpy.context.scene; indice = json.loads(sc["comic_indice"])
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    f = max(sc.frame_start, sc.frame_end - int(params["fps"]))          # un segundo antes del final: todo montado
    sc.frame_set(f)
    visibles = [pid for pid, v in indice["piezas"].items() if not bpy.data.objects[v["objeto"]].hide_render]
    cam = sc.camera; tgt = bpy.data.objects["Camara_objetivo"]
    for idb in (cam, cam.data, tgt):                   # la camara del video, fuera: se coloca a mano
        if idb.animation_data: idb.animation_data_clear()
    if "grano" in sc.keys():                           # textura con toda su fuerza (plano general)
        if sc.animation_data: sc.animation_data_clear()
        sc["grano"] = 1.0
    informe = {"imagenes": {}, "fotograma": f, "visibles": len(visibles)}
    for nombre, (w, h, hueco, factor) in FORMATOS.items():
        p2 = dict(params, orientacion=nombre)          # el encuadre toma el aspecto de la orientacion
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
        e = BT.encuadre(p2, indice, "general", "objeto", guion, visibles=visibles, factor=factor, **hueco)
        BT.colocar(cam, e, p2)
        if T.TEMA.get("dof"):
            cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt; cam.data.dof.aperture_fstop = 20.0
        if sc.render.engine == 'CYCLES':
            informe["dispositivo"] = GB.gpu_cycles(sc); sc.cycles.samples = max(sc.cycles.samples, 160)
        sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGB'
        ruta = os.path.join(carpeta, f"fondo_{nombre}.png"); sc.render.filepath = ruta
        bpy.ops.render.render(write_still=True, scene=sc.name)
        informe["imagenes"][nombre] = ruta
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
