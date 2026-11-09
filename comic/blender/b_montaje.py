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

def tira_gancho(se, params, gancho, tiempos, f_video, fps):
    """La pregunta de apertura en grande sobre el video mientras la dice la voz (primera linea de la escena 1): en redes el
    video arranca sin sonido y es lo que hace parar el scroll. Texto del secuenciador con contorno y caja translucida."""
    l0 = tiempos["escenas"][0]["lineas"][0]
    ini = f_video + max(0, int(l0["inicio"]) - 1); fin = f_video + int(l0["fin"]) - 1 + int(0.8 * fps)
    t = se.strips.new_effect("Gancho", type='TEXT', channel=3, frame_start=ini, length=max(fps, fin - ini))
    t.text = gancho["texto_pantalla"]
    fuente = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    if os.path.exists(fuente): t.font = bpy.data.fonts.load(fuente, check_existing=True)
    w, h, _ = CP.resolucion(params); vertical = h > w
    t.font_size = int(h * (0.05 if vertical else 0.07)); t.wrap_width = 0.84 if vertical else 0.8
    t.location = (0.5, 0.8 if vertical else 0.78); t.anchor_x = 'CENTER'; t.anchor_y = 'CENTER'; t.alignment_x = 'CENTER'
    t.color = (1.0, 1.0, 1.0, 1.0); t.use_outline = True; t.outline_color = (0.02, 0.04, 0.12, 1.0); t.outline_width = 0.12
    t.use_box = True; t.box_color = (0.03, 0.06, 0.16, 0.8); t.box_margin = 0.025; t.box_roundness = 0.35
    t.blend_type = 'ALPHA_OVER'
    for f_, a_ in ((ini, 0.0), (ini + 5, 1.0), (fin - 6, 1.0), (fin, 0.0)):        # entra y sale con fundido
        t.blend_alpha = a_; t.keyframe_insert("blend_alpha", frame=f_)
    return t

def tiras_comparativa(se, params, comp, guion, tiempos, f_video, fps, canal=4):
    """Grafica final con tiras del secuenciador, en la franja baja (la camara de esa escena la deja libre): panel oscuro,
    dos barras que crecen (antes / despues) con su valor, el resultado grande en lima y una curva de aprendizaje que sube
    punto a punto. Todo entra y sale con fundido."""
    ids = [e["id"] for e in guion["escenas"]]
    if comp["escena"] not in ids: return 0
    te = tiempos["escenas"][ids.index(comp["escena"])]
    t0 = f_video + int(te["inicio"]) - 1; t1 = f_video + int(te["fin"]) - 1
    W, H, _ = CP.resolucion(params); vertical = H > W
    fuente = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    font = bpy.data.fonts.load(fuente, check_existing=True) if os.path.exists(fuente) else None
    estado = {"canal": canal}
    def nuevo_canal(): estado["canal"] += 1; return estado["canal"] - 1
    def fundido(t, a, b, alfa=1.0):
        for f_, a_ in ((a, 0.0), (a + 5, alfa), (max(a + 6, b - 6), alfa), (b, 0.0)):
            t.blend_alpha = a_; t.keyframe_insert("blend_alpha", frame=f_)
    def caja(color, cx, cy, w, h, a, b, alfa=1.0, crece=None):
        """Rectangulo de color centrado en (cx, cy) px; crece = (desde, hasta) fotogramas: sube desde su base."""
        t = se.strips.new_effect(f"Comp caja {estado['canal']}", type='COLOR', channel=nuevo_canal(), frame_start=a, length=max(1, b - a))
        t.color = color[:3]; t.blend_type = 'ALPHA_OVER'
        tr = t.transform; tr.scale_x = w / W
        if crece:
            tr.origin = (0.5, 0.0); tr.offset_x = cx - W / 2; tr.offset_y = cy - h / 2
            for f_, v in ((crece[0], 0.001), (crece[1], h / H)): tr.scale_y = v; tr.keyframe_insert("scale_y", frame=f_)
        else:
            tr.scale_y = h / H; tr.offset_x = cx - W / 2; tr.offset_y = cy - H / 2
        fundido(t, a, b, alfa); return t
    def texto(txt, cx, cy, tam, color, a, b, ancho=0.9):
        t = se.strips.new_effect(f"Comp texto {estado['canal']}", type='TEXT', channel=nuevo_canal(), frame_start=a, length=max(1, b - a))
        t.text = txt; t.font_size = int(tam); t.wrap_width = ancho
        if font: t.font = font
        t.location = (cx / W, cy / H); t.anchor_x = 'CENTER'; t.anchor_y = 'CENTER'; t.alignment_x = 'CENTER'
        t.color = (*color, 1.0); t.use_outline = True; t.outline_color = (0.02, 0.04, 0.12, 1.0); t.outline_width = 0.08
        t.blend_type = 'ALPHA_OVER'; fundido(t, a, b); return t
    def num(v): return f"{v:,.0f}".replace(",", ".") if abs(v) >= 1000 or float(v).is_integer() else f"{v:.1f}".replace(".", ",")
    lima, blanco, gris, azul = (0.78, 0.95, 0.29), (1.0, 1.0, 1.0), (0.62, 0.68, 0.78), (0.27, 0.55, 1.0)
    # panel en la franja baja
    pw, ph = W * (0.9 if vertical else 0.62), H * (0.36 if vertical else 0.42)
    pcx, pcy = W / 2, H * 0.05 + ph / 2 if vertical else H * 0.06 + ph / 2
    caja((0.03, 0.06, 0.16), pcx, pcy, pw, ph, t0 + 2, t1, alfa=0.9)
    caja((0.18, 0.72, 1.0), pcx, pcy + ph / 2, pw, max(3, H * 0.003), t0 + 2, t1)          # filo superior de neon
    x0 = pcx - pw / 2; y_top = pcy + ph / 2; y_base = pcy - ph / 2 + ph * 0.2; hmax = ph * 0.48
    texto(comp["titulo"].upper(), x0 + pw * 0.3, y_top - ph * 0.1, H * 0.021, blanco, t0 + 6, t1, ancho=0.5)
    # barras
    a_v, b_v = comp["a_valor"], comp["b_valor"]; m = max(a_v, b_v)
    bw = pw * 0.14; xa, xb = x0 + pw * 0.15, x0 + pw * 0.38
    for x, v, etq, col, g0 in ((xa, a_v, comp["a_etiqueta"], azul, t0 + 12), (xb, b_v, comp["b_etiqueta"], lima, t0 + 30)):
        hb = hmax * v / m; g1 = g0 + int(0.6 * fps)
        caja(col, x, y_base + hb / 2, bw, hb, g0, t1, crece=(g0, g1))
        texto(etq, x, y_base - ph * 0.07, H * 0.016, gris, t0 + 8, t1, ancho=0.2)
        texto(num(v), x, y_base + hb + ph * 0.06, H * 0.02, blanco, g1, t1, ancho=0.2)
    caja(gris, (xa + xb) / 2, y_base - 1, pw * 0.42, max(2, H * 0.002), t0 + 8, t1)        # eje
    if comp.get("resultado"):
        texto(comp["resultado"], x0 + pw * 0.565, y_base + hmax * 0.62, H * 0.032, lima, t0 + 30 + int(0.6 * fps) + 4, t1, ancho=0.3)
    # curva de aprendizaje
    cx0, cy0, cw, chh = x0 + pw * 0.69, y_base, pw * 0.27, hmax
    caja(gris, cx0 + cw / 2, cy0, cw, max(2, H * 0.002), t0 + 8, t1); caja(gris, cx0, cy0 + chh / 2, max(2, H * 0.002), chh, t0 + 8, t1)
    texto((comp.get("curva_titulo") or "Aprende con cada iteracion").upper(), cx0 + cw / 2, y_top - ph * 0.1, H * 0.014, gris, t0 + 8, t1, ancho=0.27)
    n_p = 12; inicio_c = t0 + 30 + int(0.6 * fps) + 8; paso_c = max(2, int(0.12 * fps))
    for i in range(n_p):
        u = i / (n_p - 1); v = 1 - (1 - u) ** 2.4
        caja(lima, cx0 + cw * (0.06 + 0.9 * u), cy0 + chh * (0.08 + 0.85 * v), H * 0.011, H * 0.011, inicio_c + i * paso_c, t1)
    return estado["canal"] - canal

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

def cartela_malla(nombre, params, titulo, subtitulo, frames, pequeno=None):
    """Cartela sin Grease Pencil (temas con 'sin_gp', como arcilla): fondo claro del tema, titulo en Archivo Black grafito
    con una barra turquesa debajo y los creditos en gris. Objetos de texto (FONT) planos con emision, en EEVEE."""
    w, h, _ = CP.resolucion(params); A = w / h; W, H = A, 1.0; s = min(1.0, A)
    sc = escena_gp(nombre, params, W, H); sc.frame_start, sc.frame_end = 1, frames
    sc.render.engine = 'BLENDER_EEVEE'; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    pal = CP.PALETA_PANELES.get(params.get("tema"), CP.PALETA_PANELES["arcilla"])
    sc.world = bpy.data.worlds.new(f"{nombre}_mundo"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = CP.color_lineal(pal["fondo"])
    ruta = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    fuente = bpy.data.fonts.load(ruta, check_existing=True)
    def mat(color):
        m = bpy.data.materials.get(f"Cartela {color}")
        if m: return m
        m = bpy.data.materials.new(f"Cartela {color}"); m.use_nodes = True; N = m.node_tree.nodes
        for n in list(N): N.remove(n)
        out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission"); emi.inputs["Color"].default_value = CP.color_lineal(color)
        m.node_tree.links.new(emi.outputs[0], out.inputs["Surface"])
        return m
    def texto(cuerpo, z, tam, color):
        cu = bpy.data.curves.new(f"{nombre}_texto", 'FONT'); cu.body = cuerpo; cu.font = fuente; cu.size = tam
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_line = 0.95; cu.materials.append(mat(color))
        ob = bpy.data.objects.new(f"{nombre}_texto", cu); sc.collection.objects.link(ob)
        ob.rotation_euler = (math.pi / 2, 0, 0); ob.location = (0, 0, z)
        return ob
    lineas = "\n".join(textwrap.wrap(titulo.upper(), 14 if A < 1 else 22)); tam = 0.075 * s if A < 1 else 0.08
    th = (lineas.count("\n") + 1) * tam * 1.05
    tit = texto(lineas, 0.04, tam, pal["texto"])
    import bmesh
    bm = bmesh.new(); ancho = min(0.6 * W, max(len(l) for l in lineas.split("\n")) * tam * 0.62)
    zb = 0.04 - th / 2 - 0.04
    bm.faces.new([bm.verts.new(v) for v in ((-ancho / 2, -0.001, zb - 0.006), (ancho / 2, -0.001, zb - 0.006),
                                             (ancho / 2, -0.001, zb + 0.006), (-ancho / 2, -0.001, zb + 0.006))])
    me = bpy.data.meshes.new(f"{nombre}_barra"); bm.to_mesh(me); bm.free(); me.materials.append(mat(pal["acento"]))
    sc.collection.objects.link(bpy.data.objects.new(f"{nombre}_barra", me))
    if subtitulo:
        texto("\n".join(textwrap.wrap(subtitulo, 30 if A < 1 else 52)[:3]), zb - 0.08, 0.03 * s if A < 1 else 0.032, "#5B6B78")
    if pequeno:
        lineas_c = "\n".join(l for parrafo in pequeno.split("\n") for l in textwrap.wrap(parrafo, 46 if A < 1 else 90))
        texto(lineas_c, -H / 2 + 0.05 + 0.012 * lineas_c.count("\n"), 0.016 if A < 1 else 0.02, "#6E7D89")
    GB.curva(tit, "location", 2, [(1, 0.0, "BEZIER"), (10, 0.04, "BEZIER")])
    return sc

def cartela(nombre, params, titulo, subtitulo, fondo, estallido, frames, pequeno=None):
    if params.get("estilo") == "tecnico" and CP.tema_tecnico(params).get("sin_gp"):
        return cartela_malla(nombre, params, titulo, subtitulo, frames, pequeno)
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

def tira_paneles(se, pngs, f_video, canal=3, nombre="Paneles"):
    """Secuencia de PNG de Motion Canvas (000000.png = fotograma 1 de la pelicula) como tira de imagen ALPHA_OVER."""
    st = se.strips.new_image(nombre, pngs[0], channel=canal, frame_start=f_video)
    for ruta in pngs[1:]: st.elements.append(os.path.basename(ruta))
    st.blend_type = 'ALPHA_OVER'; st.alpha_mode = 'STRAIGHT'
    return dict(fotogramas=len(pngs), canal=canal, carpeta=os.path.dirname(pngs[0]))

def main():
    a = GB.argumentos(); dirp = a["proyecto"]
    proy, params = GB.proyecto(dirp)
    guion = GB.leer_json(os.path.join(dirp, "guion.json"))
    tiempos = GB.leer_json(os.path.join(dirp, "tiempos.json"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fps = params["fps"]
    creditos = ("Blender 5.2 · Cycles  ·  Fuente Archivo Black (OFL)" if CP.tema_tecnico(params).get("sin_gp") and params.get("estilo") == "tecnico"
                else "Blender 5.2 · Grease Pencil  ·  Fuente Archivo Black (OFL)  ·  Texturas ambientCG (CC0)" if params.get("estilo") == "tecnico"
                else "Blender 5.2 · Grease Pencil  ·  Fuentes Bangers y Comic Neue (OFL)  ·  Texturas ambientCG (CC0)")
    paneles = sorted(glob.glob(os.path.join(a["paneles"], "[0-9]" * 6 + ".png"))) if a.get("paneles") else []
    if paneles: creditos += "  ·  Paneles Motion Canvas (MIT)  ·  JetBrains Mono (OFL)"
    subs = sorted(glob.glob(os.path.join(a["subtitulos"], "[0-9]" * 6 + ".png"))) if a.get("subtitulos") else []
    if subs and not paneles: creditos += "  ·  Subtitulos Motion Canvas (MIT)"
    if tiempos.get("fuente") == "tts": creditos += "  ·  Voces Gemini TTS"
    if (proy.get("modelo_3d_info") or {}).get("credito"): creditos += "\n" + proy["modelo_3d_info"]["credito"]
    # con gancho, el video arranca con la pregunta (sobre la animacion), no con una cartela de titulo que haria pasar de largo
    gancho = guion.get("gancho") if params.get("gancho", "dolor") != "ninguno" else None
    c_tit = None if gancho else cartela("Titulo", params, guion["titulo"], guion.get("sinopsis", "").split(".")[0], "magenta", "amarillo", 3 * fps)
    cierre = a.get("cierre")            # cierre de marca (PNG de marca.py): sustituye a la cartela «¡FIN!»
    c_fin = None if cierre else cartela("Fin", params, "¡FIN!", "", "cian", "magenta", 4 * fps, pequeno=creditos)
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
    if c_tit:
        st = se.strips.new_scene("Titulo", c_tit, channel=2, frame_start=f); st.scene_input = 'CAMERA'; f += c_tit.frame_end
    if a.get("video") and os.path.exists(a["video"]):
        mv = se.strips.new_movie("Animacion", a["video"], channel=2, frame_start=f)
        snd = se.strips.new_sound("Voces", a["video"], channel=1, frame_start=f)
        informe["inicio_video"] = f
        if a.get("logo"):  # logo de la marca en la esquina (PNG transparente del tamano del cuadro), canal 5
            lg = se.strips.new_image("Logo", a["logo"], channel=5, frame_start=f)
            lg.frame_final_duration = mv.frame_final_duration; lg.blend_type = 'ALPHA_OVER'; lg.alpha_mode = 'STRAIGHT'
            informe["logo"] = a["logo"]
        if subs:           # subtitulos de Motion Canvas: encima de todo (canal 4)
            informe["subtitulos"] = tira_paneles(se, subs, f, canal=4, nombre="Subtitulos")
        if paneles:        # paneles de Motion Canvas (gancho, datos y comparativa incluidos): PNG con alfa encima de la pelicula
            informe["paneles"] = tira_paneles(se, paneles, f)
        else:
            if gancho: tira_gancho(se, params, gancho, tiempos, f, fps); informe["gancho"] = gancho["texto_pantalla"]
            comp = guion.get("comparativa") if params.get("comparativa", True) else None
            if comp: informe["comparativa_tiras"] = tiras_comparativa(se, params, comp, guion, tiempos, f, fps)
        f += mv.frame_final_duration
    if cierre:         # entra con un fundido de 8 fotogramas sobre el final de la pelicula y dura 4 s
        fade = 8; st2 = se.strips.new_image("Cierre", cierre, channel=6, frame_start=max(1, f - fade))
        st2.frame_final_duration = 4 * fps + fade
        st2.blend_alpha = 0.0; st2.keyframe_insert("blend_alpha", frame=max(1, f - fade))
        st2.blend_alpha = 1.0; st2.keyframe_insert("blend_alpha", frame=f)
        f += 4 * fps; informe["cierre"] = cierre
    else:
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
