# MODO MONTAJE: cartela de titulo + animacion + cartela de FIN con creditos, y una pagina de comic con las vinetas.
#   blender -b -P b_montaje.py -- --proyecto DIR --video DIR/render/animacion.mp4 --vinetas DIR/render/vinetas
#           --salida DIR/06_montaje.blend --final DIR/final/final.mp4 --pagina DIR/final/pagina_comic.png
# Las cartelas son escenas de Grease Pencil (texto con las fuentes descargadas, estallidos, trama de puntos) que
# entran en el secuenciador como tiras de escena. La pagina dibuja con Grease Pencil marcos, titulo y cartelas;
# las imagenes de cada vineta van en planos con emision.
import os, sys, json, math, glob, shutil, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import gp_base as GB
from gp_base import Lapiz, rect, estrella, circulo, P
import comic_parametros as CP

R = 0.0035

def escena_gp(nombre, params, ancho, alto):
    """Escena nueva con camara ortografica que encuadra [-ancho/2, ancho/2] x [-alto/2, alto/2] en el plano XZ."""
    sc = bpy.data.scenes.new(nombre)
    GB.configurar_escena(params, sc)
    sc.world = bpy.data.worlds.get("Comic") or bpy.data.worlds.new("Comic")
    if sc.world.node_tree and sc.world.node_tree.nodes.get("Background"):
        sc.world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    cd = bpy.data.cameras.new(f"Cam_{nombre}"); cd.type = 'ORTHO'; cd.ortho_scale = max(ancho, alto)
    cam = bpy.data.objects.new(f"Cam_{nombre}", cd); sc.collection.objects.link(cam)
    cam.location = (0, -10, 0); cam.rotation_euler = (math.pi / 2, 0, 0); sc.camera = cam
    return sc

def gp_en(sc, nombre):
    gp = bpy.data.grease_pencils.new(nombre); ob = bpy.data.objects.new(nombre, gp); sc.collection.objects.link(ob)
    return ob

def texto_comic(lp, texto, cx, cz, tam, color="amarillo", sombra="rojo", fuente=None):
    conts, (w, h) = GB.contornos_texto(texto, fuente or CP.FUENTE_TITULOS, tam, "CENTER")
    off = tam * 0.07
    for mat, dx, dz in ((f"Relleno {sombra}", off, -off), (f"Relleno {color}", 0, 0)):
        grupos = {}
        for c, gid in conts:
            if gid not in grupos: grupos[gid] = lp._fid()
            lp.trazo([(cx + x + dx, 0, cz + y + dz) for x, y in c], mat, radio=tam * 0.012, cerrado=True, relleno=True, fid=grupos[gid])
    return w, h

def texto_plano(lp, texto, cx, cz, tam, mat="Plano negro", fuente=None, alinear="CENTER"):
    conts, (w, h) = GB.contornos_texto(texto, fuente or CP.FUENTE_TEXTO, tam, alinear, 1.0)
    grupos = {}
    for c, gid in conts:
        if gid not in grupos: grupos[gid] = lp._fid()
        lp.trazo([(cx + x, 0, cz + y) for x, y in c], mat, radio=0.0003, cerrado=True, relleno=True, fid=grupos[gid])
    return w, h

def cartela_tecnica(nombre, params, titulo, subtitulo, frames, pequeno=None):
    """Cartela del estilo tecnico: papel con cuadricula y texto negro (Archivo Black), sin estallidos."""
    w, h, _ = CP.resolucion(params); A = w / h; W, H = A, 1.0; s = min(1.0, A)
    sc = escena_gp(nombre, params, W, H); sc.frame_start, sc.frame_end = 1, frames
    if sc.world.node_tree and sc.world.node_tree.nodes.get("Background"):
        sc.world.node_tree.nodes["Background"].inputs[0].default_value = CP.color_lineal(CP.PALETA_TECNICA["papel"])
    ob = gp_en(sc, f"{nombre}_fondo"); lp = Lapiz(ob, "fondo"); ob.location.y = 0.5
    lp.forma(rect(-W / 2 - 0.05, -H / 2 - 0.05, W / 2 + 0.05, H / 2 + 0.05), "Papel" if GB.imagen("papel") else "Plano crema", linea=False)
    lg = Lapiz(ob, "cuadricula")
    for k in range(-30, 31):
        lg.linea([P(k * 0.06, -H / 2 - 0.05), P(k * 0.06, H / 2 + 0.05)], "Trazo gris_claro", radio=0.0008)
        lg.linea([P(-W / 2 - 0.05, k * 0.06), P(W / 2 + 0.05, k * 0.06)], "Trazo gris_claro", radio=0.0008)
    ot = gp_en(sc, f"{nombre}_titulo"); lt = Lapiz(ot, "titulo"); ot.location.y = -0.5
    fuente = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    lineas = "\n".join(textwrap.wrap(titulo.upper(), 14 if A < 1 else 22))
    tam = 0.075 * s if A < 1 else 0.08
    tw, th = texto_plano(lt, lineas, 0, 0.04, tam, mat="Plano negro", fuente=fuente)
    lt.forma(rect(-tw / 2, 0.04 - th / 2 - 0.045, tw / 2, 0.04 - th / 2 - 0.035), "Plano lima", linea=False)
    if subtitulo:
        sub = "\n".join(textwrap.wrap(subtitulo, 30 if A < 1 else 52)[:3])
        texto_plano(lt, sub, 0, 0.04 - th / 2 - 0.12, 0.03 * s if A < 1 else 0.032, mat="Plano gris_oscuro")
    if pequeno:
        lineas_c = "\n".join(l for parrafo in pequeno.split("\n") for l in textwrap.wrap(parrafo, 46 if A < 1 else 90))
        texto_plano(lt, lineas_c, 0, -H / 2 + 0.03 + 0.012 * lineas_c.count("\n"), 0.016 if A < 1 else 0.02, mat="Plano gris_oscuro")
    GB.curva(ot, "location", 2, [(1, -0.04, "BEZIER"), (10, 0.0, "BEZIER")])
    return sc

def cartela(nombre, params, titulo, subtitulo, fondo, estallido, frames, pequeno=None):
    if params.get("estilo") == "tecnico":
        return cartela_tecnica(nombre, params, titulo, subtitulo, frames, pequeno)
    w, h, _ = CP.resolucion(params); A = w / h
    W, H = (A, 1.0)
    sc = escena_gp(nombre, params, W, H)
    sc.frame_start, sc.frame_end = 1, frames
    s = min(1.0, A)
    ob = gp_en(sc, f"{nombre}_fondo"); lp = Lapiz(ob, "fondo")
    lp.forma(rect(-W / 2 - 0.05, -H / 2 - 0.05, W / 2 + 0.05, H / 2 + 0.05), f"Cielo puntos {fondo}", linea=False)
    for m in ob.data.materials:
        if m and m.grease_pencil.fill_style == 'TEXTURE':
            m2 = m.copy(); m2.name = f"{m.name} cartela"; m2.grease_pencil.texture_scale = (14, 14)
            ob.data.materials[list(ob.data.materials).index(m)] = m2
    for k in range(24):
        ang = 2 * math.pi * k / 24
        lp.forma([P(0, 0), P(2 * math.cos(ang - 0.06), 2 * math.sin(ang - 0.06)), P(2 * math.cos(ang + 0.06), 2 * math.sin(ang + 0.06))],
                 f"Translucido blanco", linea=False)
    ot = gp_en(sc, f"{nombre}_titulo"); lt = Lapiz(ot, "titulo")
    ot.location.y = -0.5                  # delante del fondo: dos objetos 2D a la misma profundidad se mezclan
    tam = 0.14 * s if len(titulo) < 18 else 0.1 * s
    lineas = "\n".join(textwrap.wrap(titulo.upper(), 16 if A >= 1 else 11))
    conts, (tw, th) = GB.contornos_texto(lineas, CP.FUENTE_TITULOS, tam, "CENTER")
    r = max(tw * 0.62, th * 0.9) + 0.05
    lt.forma(estrella(0, 0, r * 1.3, r * 0.95, 18, irregular=0.12, semilla=3), f"Relleno {estallido}", radio=R * 1.6)
    lt.forma(estrella(0, 0, r * 1.05, r * 0.8, 18, irregular=0.1, semilla=4), "Relleno blanco", linea=False)
    texto_comic(lt, lineas, 0, 0, tam)
    if subtitulo:
        sub = "\n".join(textwrap.wrap(subtitulo, 48 if A >= 1 else 28)[:3])
        lsub = Lapiz(ot, "subtitulo")
        cw, ch = GB.contornos_texto(sub, CP.FUENTE_TEXTO, 0.034 * s, "CENTER")[1]
        z = -r * 1.25 - ch / 2 - 0.03
        lsub.forma(rect(-cw / 2 - 0.03, z - ch / 2 - 0.02, cw / 2 + 0.03, z + ch / 2 + 0.02), "Relleno amarillo", radio=R)
        texto_plano(lsub, sub, 0, z, 0.034 * s)
    if pequeno:
        lp2 = Lapiz(ot, "creditos")
        cw = GB.contornos_texto(pequeno, CP.FUENTE_TEXTO, 0.024 * s, "CENTER")[1][0]
        lp2.forma(rect(-cw / 2 - 0.03, -H / 2 + 0.05, cw / 2 + 0.03, -H / 2 + 0.13), "Relleno blanco", radio=R * 0.6)
        texto_plano(lp2, pequeno, 0, -H / 2 + 0.09, 0.024 * s, mat="Plano negro")
    # rebote de entrada del titulo
    GB.curva(ot, "scale", 0, [(1, 0.05, "BEZIER"), (6, 1.15, "BEZIER"), (10, 0.95, "BEZIER"), (14, 1.0, "BEZIER")])
    GB.curva(ot, "scale", 2, [(1, 0.05, "BEZIER"), (6, 1.15, "BEZIER"), (10, 0.95, "BEZIER"), (14, 1.0, "BEZIER")])
    GB.curva(ot, "rotation_euler", 1, [(1, -0.3, "BEZIER"), (8, 0.04, "BEZIER"), (14, 0.0, "BEZIER")])
    GB.brillo(ot, (1, 0.9, 0.3), 30)
    return sc

def plano_imagen(sc, nombre, ruta, x0, z0, x1, z1):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new();
    for i, co in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]): uv.data[i].uv = co
    m = bpy.data.materials.new(nombre); nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(ruta, check_existing=True)
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
    me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me); sc.collection.objects.link(ob)
    return ob

def pagina(params, guion, tiempos, vinetas, ruta_png):
    w, h, _ = CP.resolucion(params); vertical = h > w
    cols = 3 if vertical else 2
    ancho = 12.4; g = 0.28
    pw = (ancho - (cols + 1) * g) / cols; ph = pw * h / w
    n = len(vinetas)
    filas = []; i = 0
    if not vertical and n % 2 == 1: filas.append([0]); i = 1     # la primera vineta a todo lo ancho
    while i < n: filas.append(list(range(i, min(n, i + cols)))); i += cols
    cab = 1.9
    alto_filas = []
    for fila in filas:
        if len(fila) == 1 and not vertical: alto_filas.append((ancho - 2 * g) * h / w)
        else: alto_filas.append(ph)
    alto = cab + sum(alto_filas) + g * (len(filas) + 1) + 0.5
    sc = escena_gp("Pagina", params, ancho, alto)
    sc.render.resolution_x = 1240; sc.render.resolution_y = int(1240 * alto / ancho); sc.render.resolution_percentage = 100
    sc.camera.data.ortho_scale = max(ancho, alto)
    top = alto / 2
    # el fondo es una malla: un objeto GP se dibuja encima de las mallas aunque este detras (tambien en orden 3D)
    papel = os.path.join(GB.TEXTURAS, "papel.jpg")
    if os.path.exists(papel):
        fondo = plano_imagen(sc, "Pagina_fondo", papel, -ancho / 2, -alto / 2, ancho / 2, alto / 2); fondo.location.y = 1.0
    tit = gp_en(sc, "Pagina_titulo"); lt = Lapiz(tit, "titulo")
    texto_comic(lt, guion["titulo"].upper(), 0, top - cab / 2 - 0.05, 1.3 if len(guion["titulo"]) < 20 else 0.95)
    tit.location.y = -0.2
    marcos = gp_en(sc, "Pagina_marcos"); lm = Lapiz(marcos, "marcos"); lc = Lapiz(marcos, "cartelas")
    marcos.location.y = -0.3
    z = top - cab - g
    # si el video ya lleva cartelas, la vineta las trae: no se repiten en la pagina
    narr = {} if params.get("cartelas", True) else {e["id"]: [ln["texto"] for ln in e["lineas"] if ln["quien"] == "narrador"] for e in tiempos["escenas"]}
    k = 0
    for fila, fh in zip(filas, alto_filas):
        fw = (ancho - (len(fila) + 1) * g) / len(fila) if (len(fila) > 1 or vertical) else ancho - 2 * g
        for j, idx in enumerate(fila):
            x0 = -ancho / 2 + g + j * (fw + g); x1 = x0 + fw; z1 = z; z0 = z - (fw * h / w if not vertical else fh)
            plano_imagen(sc, f"Vineta_{idx + 1}", vinetas[idx], x0, z0, x1, z1)
            lm.trazo(rect(x0, z0, x1, z1, y=-0.01), "Tinta", radio=0.045, cerrado=True)
            eid = guion["escenas"][idx]["id"] if idx < len(guion["escenas"]) else None
            textos = narr.get(eid) or []
            if textos:
                txt = "\n".join(textwrap.wrap(textos[0], 30)[:3])
                tw, th = GB.contornos_texto(txt, CP.FUENTE_TEXTO, 0.17, "LEFT")[1]
                bx0, bz1 = x0 + 0.12, z1 - 0.12
                lc.forma(rect(bx0, bz1 - th - 0.24, bx0 + tw + 0.3, bz1, y=-0.02), "Relleno amarillo", radio=0.02)
                texto_plano(lc, txt, bx0 + 0.15 + tw / 2, bz1 - 0.12 - th / 2, 0.17)
            k += 1
        z = z - fh - g
    GB.render_fotograma(ruta_png, 1, sc)
    return sc

def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    tiempos = GB.leer_json(os.path.join(dirp, "tiempos.json"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fps = params["fps"]
    creditos = ("Blender 5.2 · Grease Pencil  ·  Fuente Archivo Black (OFL)  ·  Texturas ambientCG (CC0)" if params.get("estilo") == "tecnico"
                else "Blender 5.2 · Grease Pencil  ·  Fuentes Bangers y Comic Neue (OFL)  ·  Texturas ambientCG (CC0)")
    if tiempos.get("fuente") == "tts": creditos += "  ·  Voces Gemini TTS"
    if (proy.get("modelo_3d_info") or {}).get("credito"): creditos += "\n" + proy["modelo_3d_info"]["credito"]
    c_tit = cartela("Titulo", params, guion["titulo"], guion.get("sinopsis", "").split(".")[0], "magenta", "amarillo", 3 * fps)
    c_fin = cartela("Fin", params, "¡FIN!", "", "cian", "magenta", 4 * fps, pequeno=creditos)
    informe = {}
    vinetas = sorted(glob.glob(os.path.join(a.get("vinetas", ""), "escena_*.png")), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))
    if a.get("pagina") and vinetas:
        os.makedirs(os.path.dirname(a["pagina"]), exist_ok=True)
        pagina(params, guion, tiempos, vinetas, a["pagina"]); informe["pagina"] = a["pagina"]
    # secuenciador
    mon = bpy.data.scenes.get("Scene") or bpy.data.scenes.new("Montaje")
    mon.name = "Montaje"
    GB.configurar_escena(params, mon)
    se = mon.sequence_editor_create()
    f = 1
    st = se.strips.new_scene("Titulo", c_tit, channel=2, frame_start=f); st.scene_input = 'CAMERA'; f += c_tit.frame_end
    if a.get("video") and os.path.exists(a["video"]):
        mv = se.strips.new_movie("Animacion", a["video"], channel=2, frame_start=f)
        snd = se.strips.new_sound("Voces", a["video"], channel=1, frame_start=f)
        f += mv.frame_final_duration
    st2 = se.strips.new_scene("Fin", c_fin, channel=2, frame_start=f); st2.scene_input = 'CAMERA'; f += c_fin.frame_end
    mon.frame_start, mon.frame_end = 1, f - 1
    GB.guardar(a["salida"])
    if a.get("final"):
        destino = a["final"]; os.makedirs(os.path.dirname(destino), exist_ok=True)
        r = mon.render; tmp = os.path.join(os.path.dirname(destino), "_tmp_final_")
        r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
        r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'HIGH'
        r.ffmpeg.audio_codec = 'AAC'; r.ffmpeg.audio_bitrate = 192; r.ffmpeg.audio_channels = 'STEREO'; r.ffmpeg.audio_mixrate = 48000
        r.use_sequencer = True; r.filepath = tmp
        bpy.ops.render.render(animation=True, scene=mon.name)
        hechos = sorted(glob.glob(tmp + "*"), key=os.path.getmtime)
        if hechos:
            if os.path.exists(destino): os.remove(destino)
            shutil.move(hechos[-1], destino); informe["final"] = destino
    informe["fotogramas"] = mon.frame_end
    print("INFORME " + json.dumps(informe, ensure_ascii=False))

if __name__ == "__main__":
    main()
