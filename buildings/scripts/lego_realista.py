# Shader "LEGO realista" para EEVEE: plastico ABS con variacion por pieza, huellas, arañazos y polvo (texturas CC0
# de ambientCG en descargas/cc0) y utilidades para aplicarlo a los tres sistemas de materiales del proyecto:
#   - Mecabricks (Nitro y paleta "LEGO <id>" del generador): se rehace el interior de mb_base_solid / mb_base_transparent
#   - ImportLDraw (modulares): se rehace el interior de "Lego Standard*" / "Lego Transparent" y los colores LDraw
#     pasan a la paleta Mecabricks (LDConfig.ldr da el ID LEGO de cada codigo LDraw)
# Las impresiones, stickers, grano de pendientes y mezclas de decoracion quedan intactos: viven fuera de esos grupos.
# Uso como modulo: sys.path.insert(0, ~/blender/buildings/scripts); import lego_realista as LR
import bpy, os, re, json

BASE = os.path.expanduser("~/blender/buildings")
CC0 = BASE + "/descargas/cc0"
IMPERF = CC0 + "/imperfecciones_lego_2k.png"   # R huellas, G arañazos, B polvo (empaquetar_imperfecciones.py)
BALDOSA = 10.0                                   # tamaño de la baldosa de imperfecciones, en unidades de Blender
LOGO = CC0 + "/logo_stud_altura.png"             # relieve del logo de los studs, 1 celda de stud (textura_logo.py)
STUD, PLACA = 0.8, 0.32                          # rejilla del mundo: la cara superior de un stud esta a 0.16 de un multiplo de placa
HDRI = CC0 + "/kloofendal_48d_partly_cloudy_puresky/kloofendal_48d_partly_cloudy_puresky_4k.hdr"
PALETA = BASE + "/scripts/paleta_mecabricks.json"     # id LEGO -> color (de la paleta del generador)
LDCONFIG = os.path.expanduser("~/ldraw/LDConfig.ldr")

# ---------- ayudante de nodos de shader ----------
class S:
    def __init__(self, tree): self.t = tree
    def n(self, idname, x=0, y=0, **kw):
        node = self.t.nodes.new(idname); node.location = (x, y)
        for k, v in kw.items(): setattr(node, k, v)
        return node
    def L(self, a, b):
        if isinstance(a, bpy.types.NodeSocket): self.t.links.new(a, b)
        elif a is not None: b.default_value = a
    def m(self, op, a, b=0.0, c=0.0, clamp=False):
        node = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        for s, v in zip(node.inputs, (a, b, c)): self.L(v, s)
        return node.outputs[0]
    def rango(self, v, lo, hi):
        node = self.n('ShaderNodeMapRange', clamp=True)
        self.L(v, node.inputs["Value"]); node.inputs["From Min"].default_value = lo; node.inputs["From Max"].default_value = hi
        return node.outputs["Result"]

def grupo(nombre):
    g = bpy.data.node_groups.get(nombre)
    if g: g.nodes.clear(); [g.interface.remove(i) for i in list(g.interface.items_tree)]   # se rehace (rerun seguro)
    else: g = bpy.data.node_groups.new(nombre, 'ShaderNodeTree')
    return g

def entrada(g, nombre, tipo, defecto=None, lo=None, hi=None):
    s = g.interface.new_socket(nombre, in_out='INPUT', socket_type=tipo)
    if defecto is not None: s.default_value = defecto
    if lo is not None: s.min_value = lo
    if hi is not None: s.max_value = hi
    if tipo == 'NodeSocketVector': s.hide_value = True
    return s

def imagen(ruta):
    im = bpy.data.images.load(ruta, check_existing=True)
    im.colorspace_settings.name = 'Non-Color'
    return im

# ---------- grupos ----------
def crear_imperfecciones():
    # Mascaras 0..1 de huellas, arañazos y polvo desde una sola imagen RGB (una lectura de textura: compilar y
    # renderizar es mucho mas barato que con tres imagenes y ruido). Proyeccion en caja sobre coordenadas de objeto
    # (las piezas LDraw no tienen UV), desplazadas al azar por pieza para que no se repitan. "Unidad" = unidades de
    # Blender por unidad local (1 en LDraw/generador, 0.1 en Mecabricks, cuyas piezas van en mm bajo un Empty 0.1).
    g = grupo("LEGO imperfecciones"); s = S(g)
    entrada(g, "Unidad", 'NodeSocketFloat', 1.0)
    for k in ("Huellas", "Rayas", "Polvo"): g.interface.new_socket(k, in_out='OUTPUT', socket_type='NodeSocketFloat')
    gi = s.n('NodeGroupInput', -1400); go = s.n('NodeGroupOutput', 400)
    tc = s.n('ShaderNodeTexCoord', -1400, -200); oi = s.n('ShaderNodeObjectInfo', -1400, -450)
    esc = s.n('ShaderNodeVectorMath', -1150, -200, operation='SCALE')
    s.L(tc.outputs["Object"], esc.inputs[0]); s.L(s.m('DIVIDE', gi.outputs["Unidad"], BALDOSA), esc.inputs["Scale"])
    off = s.n('ShaderNodeCombineXYZ', -1150, -450)
    for i, f in enumerate((37.1, 91.7, 53.3)): s.L(s.m('MULTIPLY', oi.outputs["Random"], f), off.inputs[i])
    p = s.n('ShaderNodeVectorMath', -950, -300, operation='ADD'); s.L(esc.outputs[0], p.inputs[0]); s.L(off.outputs[0], p.inputs[1])
    tx = s.n('ShaderNodeTexImage', -700, -300, image=imagen(IMPERF), projection='BOX', projection_blend=0.3)
    s.L(p.outputs[0], tx.inputs["Vector"])
    rgb = s.n('ShaderNodeSeparateColor', -450, -300); s.L(tx.outputs["Color"], rgb.inputs[0])
    geo = s.n('ShaderNodeNewGeometry', -700, -650); sep = s.n('ShaderNodeSeparateXYZ', -450, -650)
    s.L(geo.outputs["Normal"], sep.inputs[0])
    s.L(rgb.outputs["Red"], go.inputs["Huellas"]); s.L(rgb.outputs["Green"], go.inputs["Rayas"])
    s.L(s.m('MULTIPLY', rgb.outputs["Blue"], s.rango(sep.outputs["Z"], 0.2, 0.9)), go.inputs["Polvo"])   # polvo arriba
    return g

def logo_studs(s, gi, normal):
    # Logo LEGO en relieve sobre la cara superior de cada stud, sin geometria: toda la ciudad esta en la rejilla de studs,
    # asi que en coordenadas de mundo el stud esta centrado en su celda de 0.8 y su cara superior a 0.16 de un multiplo
    # de 0.32. Solo cuenta donde la normal mira hacia arriba (los logos quedan todos con la misma orientacion).
    geo = s.n('ShaderNodeNewGeometry', -900, -900); p = s.n('ShaderNodeSeparateXYZ', -700, -900)
    nz = s.n('ShaderNodeSeparateXYZ', -700, -1150)
    s.L(geo.outputs["Position"], p.inputs[0]); s.L(geo.outputs["Normal"], nz.inputs[0])
    uv = s.n('ShaderNodeCombineXYZ', -450, -900)
    s.L(s.m('FRACT', s.m('DIVIDE', p.outputs["X"], STUD)), uv.inputs[0]); s.L(s.m('FRACT', s.m('DIVIDE', p.outputs["Y"], STUD)), uv.inputs[1])
    tx = s.n('ShaderNodeTexImage', -250, -900, image=imagen(LOGO), extension='EXTEND'); s.L(uv.outputs[0], tx.inputs["Vector"])
    d = s.m('ABSOLUTE', s.m('SUBTRACT', s.m('FRACT', s.m('DIVIDE', p.outputs["Z"], PLACA)), 0.5))
    en_cara = s.m('LESS_THAN', s.m('MULTIPLY', d, PLACA), 0.004)
    arriba = s.m('GREATER_THAN', nz.outputs["Z"], 0.98)
    h = s.m('MULTIPLY', s.m('MULTIPLY', tx.outputs["Color"], en_cara), arriba)
    b = s.n('ShaderNodeBump', 0, -900); b.inputs["Distance"].default_value = 0.008
    s.L(h, b.inputs["Height"]); s.L(gi.outputs["Logos"], b.inputs["Strength"]); s.L(normal, b.inputs["Normal"])
    return b.outputs[0]

def crear_realista():
    # Se crean una sola vez: rehacerlos borraria sus sockets y con ellos los enlaces de los grupos ya parcheados
    if "LEGO realista" in bpy.data.node_groups and "LEGO realista transparente" in bpy.data.node_groups:
        return bpy.data.node_groups["LEGO realista"], bpy.data.node_groups["LEGO realista transparente"]
    imp = bpy.data.node_groups.get("LEGO imperfecciones") or crear_imperfecciones()
    for nombre, transparente in (("LEGO realista", False), ("LEGO realista transparente", True)):
        g = grupo(nombre); s = S(g)
        entrada(g, "Color", 'NodeSocketColor', (0.8, 0.8, 0.8, 1.0))
        entrada(g, "Normal", 'NodeSocketVector')
        entrada(g, "Unidad", 'NodeSocketFloat', 1.0)
        entrada(g, "Variación", 'NodeSocketFloat', 1.0, 0.0, 3.0)
        entrada(g, "Huellas", 'NodeSocketFloat', 1.0, 0.0, 3.0)
        entrada(g, "Rayas", 'NodeSocketFloat', 1.0, 0.0, 3.0)
        entrada(g, "Polvo", 'NodeSocketFloat', 1.0, 0.0, 3.0)
        entrada(g, "Rugosidad", 'NodeSocketFloat', 0.03 if transparente else 0.10, 0.0, 1.0)
        if transparente: entrada(g, "Emisión", 'NodeSocketFloat', 0.0, 0.0, 100.0)
        else: entrada(g, "Logos", 'NodeSocketFloat', 1.0, 0.0, 3.0)
        g.interface.new_socket("Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
        gi = s.n('NodeGroupInput', -1200); go = s.n('NodeGroupOutput', 700)
        im = s.n('ShaderNodeGroup', -900, -400, node_tree=imp); s.L(gi.outputs["Unidad"], im.inputs["Unidad"])
        oi = s.n('ShaderNodeObjectInfo', -1200, 300)
        r1 = oi.outputs["Random"]; r2 = s.m('FRACT', s.m('MULTIPLY', r1, 7.13)); r3 = s.m('FRACT', s.m('MULTIPLY', r1, 13.71))
        var = gi.outputs["Variación"]
        def jit(r, amp, centro):   # centro + (r - 0.5) * amp * Variacion
            return s.m('ADD', s.m('MULTIPLY', s.m('MULTIPLY', s.m('SUBTRACT', r, 0.5), amp), var), centro)
        hsv = s.n('ShaderNodeHueSaturation', -500, 300)   # leve diferencia de lote entre piezas del mismo color
        s.L(jit(r1, 0.008, 0.5), hsv.inputs["Hue"]); s.L(jit(r2, 0.06, 1.0), hsv.inputs["Saturation"])
        s.L(jit(r3, 0.06, 1.0), hsv.inputs["Value"]); s.L(gi.outputs["Color"], hsv.inputs["Color"])
        polvo = s.m('MULTIPLY', im.outputs["Polvo"], gi.outputs["Polvo"])
        mix = s.n('ShaderNodeMix', -250, 300, data_type='RGBA')
        s.L(s.m('MULTIPLY', polvo, 0.06), mix.inputs["Factor"]); s.L(hsv.outputs[0], mix.inputs["A"])
        mix.inputs["B"].default_value = (0.55, 0.53, 0.5, 1.0)
        huellas = s.m('MULTIPLY', im.outputs["Huellas"], gi.outputs["Huellas"])
        rayas = s.m('MULTIPLY', im.outputs["Rayas"], gi.outputs["Rayas"])
        rug = s.m('ADD', gi.outputs["Rugosidad"], s.m('MULTIPLY', s.m('MULTIPLY', r2, 0.05), var))
        rug = s.m('ADD', rug, s.m('MULTIPLY', huellas, 0.30))
        rug = s.m('ADD', rug, s.m('MULTIPLY', rayas, 0.25))
        rug = s.m('ADD', rug, s.m('MULTIPLY', polvo, 0.15), clamp=True)
        bump = s.n('ShaderNodeBump', -250, -300)    # los arañazos se notan en los reflejos
        s.L(rayas, bump.inputs["Height"]); s.L(s.m('MULTIPLY', gi.outputs["Rayas"], 0.08), bump.inputs["Strength"])
        bump.inputs["Distance"].default_value = 0.002; s.L(gi.outputs["Normal"], bump.inputs["Normal"])
        normal = bump.outputs[0]
        if not transparente: normal = logo_studs(s, gi, normal)
        bs = s.n('ShaderNodeBsdfPrincipled', 200, 0)
        s.L(mix.outputs["Result"], bs.inputs["Base Color"]); s.L(rug, bs.inputs["Roughness"]); s.L(normal, bs.inputs["Normal"])
        if transparente:
            bs.inputs["Transmission Weight"].default_value = 1.0; bs.inputs["IOR"].default_value = 1.58
            s.L(gi.outputs["Color"], bs.inputs["Emission Color"]); s.L(gi.outputs["Emisión"], bs.inputs["Emission Strength"])
        else:   # ABS: brillo plastico y un poco de luz que entra en la pieza (radio en unidades de escena: 0.5 mm)
            bs.inputs["IOR"].default_value = 1.54
            bs.inputs["Subsurface Weight"].default_value = 0.05
            bs.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.35)
            bs.inputs["Subsurface Scale"].default_value = 0.05
        s.L(bs.outputs[0], go.inputs["Shader"])
    return bpy.data.node_groups["LEGO realista"], bpy.data.node_groups["LEGO realista transparente"]

def rehacer(g, realista, unidad, mapa):
    # Vacia el grupo base (conservando su interfaz) y pone dentro el grupo realista. mapa: entrada base -> realista
    for n in list(g.nodes): g.nodes.remove(n)
    s = S(g); gi = s.n('NodeGroupInput', -400); go = s.n('NodeGroupOutput', 400)
    r = s.n('ShaderNodeGroup', 0, 0, node_tree=realista)
    for a, b in mapa.items():
        if a in gi.outputs and b in r.inputs: s.L(gi.outputs[a], r.inputs[b])
    r.inputs["Unidad"].default_value = unidad
    salida = next(o for o in go.inputs if o.type == 'SHADER')
    s.L(r.outputs["Shader"], salida)

def materiales_con(grupos):
    return [m for m in bpy.data.materials if not m.library and m.node_tree and
            any(n.type == 'GROUP' and n.node_tree in grupos for n in m.node_tree.nodes)]

def ajustar_transparentes(mats):
    for m in mats:
        m.surface_render_method = 'DITHERED'; m.use_raytrace_refraction = True; m.use_transparent_shadow = True

# ---------- aplicar ----------
def aplicar_mecabricks(unidad):
    # Nitro (unidad 0.1: piezas en mm) y paleta "LEGO <id>" del generador (unidad 1)
    sol, tra = crear_realista()
    hechos = []
    for g in [g for g in bpy.data.node_groups if not g.library]:
        if g.name.split(".")[0] == "mb_base_solid":
            rehacer(g, sol, unidad, {"Color": "Color", "Normal": "Normal"}); hechos.append(g.name)
        elif g.name.split(".")[0] == "mb_base_transparent":
            rehacer(g, tra, unidad, {"Color": "Color", "Normal": "Normal", "Emission": "Emisión"}); hechos.append(g.name)
    ajustar_transparentes(materiales_con([g for g in bpy.data.node_groups if g.name.split(".")[0] == "mb_base_transparent"]))
    return hechos

def leer_ldconfig():
    cod = {}; legoid = None
    for l in open(LDCONFIG, encoding="utf-8", errors="replace"):
        m = re.match(r"0\s+//\s*LEGOID\s+(\d+)", l)
        if m: legoid = int(m.group(1)); continue
        m = re.match(r"0\s+!COLOUR\s+(\S+)\s+CODE\s+(\d+)", l)
        if m:
            if legoid is not None: cod[int(m.group(2))] = legoid
            legoid = None
    return cod

def aplicar_ldraw(unidad=1.0):
    # Modulares importados con ImportLDraw: grupos base -> realista y colores LDraw -> paleta Mecabricks
    sol, tra = crear_realista()
    std = [g for g in bpy.data.node_groups if not g.library and g.name.startswith("Lego Standard")]
    trn = [g for g in bpy.data.node_groups if not g.library and g.name.split(" (")[0] == "Lego Transparent"]
    for g in std: rehacer(g, sol, unidad, {"Color": "Color", "Normal": "Normal"})
    for g in trn: rehacer(g, tra, unidad, {"Color": "Color", "Normal": "Normal"})
    ajustar_transparentes(materiales_con(trn))
    paleta = {int(k): v for k, v in json.load(open(PALETA)).items()}
    cod = leer_ldconfig(); cambiados = 0; sin = set()
    for m in materiales_con(std + trn):
        mt = re.match(r"Material_(\d+)_", m.name)
        if not mt: continue
        lid = cod.get(int(mt.group(1)))
        if lid not in paleta: sin.add(int(mt.group(1))); continue
        for n in m.node_tree.nodes:   # el color esta en la entrada Color del grupo o, en piezas impresas, en el Mix previo
            if n.type == 'GROUP' and n.node_tree in std + trn:
                c = n.inputs["Color"]
                if not c.is_linked: c.default_value = paleta[lid]; cambiados += 1
                else:
                    src = c.links[0].from_node
                    for nombre in ("Color1", "A"):
                        if nombre in src.inputs and not src.inputs[nombre].is_linked:
                            src.inputs[nombre].default_value = paleta[lid]; cambiados += 1; break
    return {"grupos": [g.name for g in std + trn], "colores_cambiados": cambiados, "codigos_sin_paleta": sorted(sin)}

def exportar_paleta():
    # Desde un archivo con la paleta "LEGO <id> <nombre>" (generador): id -> color de mb_base_*
    pal = {}
    for m in bpy.data.materials:
        mt = re.match(r"LEGO (\d+)", m.name)
        if not mt or not m.node_tree: continue
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree.name.split(".")[0] in ("mb_base_solid", "mb_base_transparent"):
                pal[int(mt.group(1))] = list(n.inputs["Color"].default_value)
    json.dump(pal, open(PALETA, "w"), indent=0)
    return len(pal)

def iluminacion(escena, fuerza=1.0, giro=0.0):
    # Cielo HDRI (con el sol extraido para sombras nitidas) y EEVEE con raytracing, ajustado para animacion 1080p
    w = bpy.data.worlds.get("Cielo realista") or bpy.data.worlds.new("Cielo realista")
    nt = w.node_tree; nt.nodes.clear(); s = S(nt)
    tc = s.n('ShaderNodeTexCoord', -800); mp = s.n('ShaderNodeMapping', -600); mp.inputs["Rotation"].default_value[2] = giro
    env = s.n('ShaderNodeTexEnvironment', -350, image=bpy.data.images.load(HDRI, check_existing=True))
    bg = s.n('ShaderNodeBackground', -50); bg.inputs["Strength"].default_value = fuerza
    out = s.n('ShaderNodeOutputWorld', 200)
    s.L(tc.outputs["Generated"], mp.inputs["Vector"]); s.L(mp.outputs[0], env.inputs["Vector"])
    s.L(env.outputs["Color"], bg.inputs["Color"]); s.L(bg.outputs[0], out.inputs["Surface"])
    w.use_sun_shadow = True; w.sun_threshold = 5.0; w.sun_angle = 0.03
    escena.world = w
    e = escena.eevee
    e.use_raytracing = True; e.ray_tracing_method = 'SCREEN'
    e.ray_tracing_options.resolution_scale = '2'; e.ray_tracing_options.use_denoise = True
    e.use_fast_gi = True; e.fast_gi_method = 'GLOBAL_ILLUMINATION'
    e.taa_render_samples = 32; e.use_shadows = True; e.shadow_ray_count = 2; e.shadow_step_count = 6
    escena.view_settings.view_transform = 'AgX'
    escena.view_settings.look = 'AgX - Medium High Contrast'
    return w
