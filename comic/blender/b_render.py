# MODO 5 · RENDER (y fotogramas sueltos para la previa): EEVEE, sin interfaz.
#   video:   blender -b 04b_efectos.blend -P b_render.py -- --proyecto DIR --video DIR/render/animacion.mp4 [--vinetas DIR/render/vinetas]
#   previa:  blender -b 04b_efectos.blend -P b_render.py -- --proyecto DIR --fotogramas auto|10,20 --carpeta DIR/previa/iter_1 [--calidad previa]
# El video lleva el audio del secuenciador (voces) en AAC. Las vinetas son un fotograma clave por escena (al 60 %),
# que usan la revision de Gemini y la pagina de comic del montaje.
import os, sys, json, glob, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB
import comic_parametros as CP

def fotograma_clave(e, frac=0.6):
    return int(e["inicio"] + (e["fin"] - 1 - e["inicio"]) * frac)

def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    if a.get("calidad"): params["calidad"] = a["calidad"]
    tiempos = GB.leer_json(os.path.join(dirp, "tiempos.json"))
    sc = bpy.context.scene
    w, h, pct = CP.resolucion(params)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, pct
    informe = dict(resolucion=f"{w * pct // 100}x{h * pct // 100}")
    t0 = time.time()
    if a.get("fotogramas"):
        carpeta = a["carpeta"]; os.makedirs(carpeta, exist_ok=True)
        if a["fotogramas"] == "auto":
            lista = [(e["id"], fotograma_clave(e)) for e in tiempos["escenas"]]
        else:
            lista = [(None, int(x)) for x in str(a["fotogramas"]).split(",") if x]
        salidas = []
        for eid, f in lista:
            ruta = os.path.join(carpeta, f"escena_{eid}.png" if eid is not None else f"fotograma_{f:05d}.png")
            GB.render_fotograma(ruta, f); salidas.append(dict(escena=eid, fotograma=f, png=ruta))
        informe["imagenes"] = salidas
    if a.get("vinetas"):
        os.makedirs(a["vinetas"], exist_ok=True); informe["vinetas"] = []
        for e in tiempos["escenas"]:
            ruta = os.path.join(a["vinetas"], f"escena_{e['id']}.png")
            GB.render_fotograma(ruta, fotograma_clave(e)); informe["vinetas"].append(ruta)
    if a.get("video"):
        destino = a["video"]; os.makedirs(os.path.dirname(destino), exist_ok=True)
        tmp = os.path.join(os.path.dirname(destino), "_tmp_video_")
        r = sc.render
        r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
        r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'
        r.ffmpeg.constant_rate_factor = 'HIGH'; r.ffmpeg.ffmpeg_preset = 'GOOD'
        r.ffmpeg.audio_codec = 'AAC'; r.ffmpeg.audio_bitrate = 192; r.ffmpeg.audio_channels = 'STEREO'; r.ffmpeg.audio_mixrate = 48000
        r.use_sequencer = True        # solo hay tiras de sonido: la imagen sigue siendo la de la camara
        r.filepath = tmp
        for viejo in glob.glob(tmp + "*"): os.remove(viejo)     # restos de un render interrumpido: no son el resultado
        informe["dispositivo"] = GB.gpu_cycles(sc)                # Cycles en la GPU en ESTE proceso (no viaja en el .blend)
        bpy.ops.render.render(animation=True)
        hechos = sorted(glob.glob(tmp + "*"), key=os.path.getmtime)
        if not hechos: raise SystemExit("el render de video no produjo archivo")
        if os.path.exists(destino): os.remove(destino)
        shutil.move(hechos[-1], destino)
        informe.update(video=destino, fotogramas=sc.frame_end - sc.frame_start + 1)
    informe["segundos"] = round(time.time() - t0, 1)
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
