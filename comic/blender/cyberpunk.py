# Tema CYBERPUNK del estilo tecnico: las piezas son MALLAS con el material toon de escenes/Cyberpunk_fixed.blend,
# contornos con Line Art (Grease Pencil) y render con EEVEE (Shader to RGB, que da las bandas, es solo de EEVEE).
#
# El material toon (copiado nodo a nodo de la referencia) no depende del color de la luz, sino de dos canales:
#   R / 1.9 -> rampa de 4 bandas constantes del color de la pieza  (luz ROJA = luz principal)
#   B / 2.6 -> rampa calida (negro, naranja, melocoton)             (luz AZUL = contraluz)
# Cada rampa se suma como color (Mix con 0.1, factor 0.817) y como Emission; las dos ramas se mezclan al 50 %.
# Por eso las luces de la escena son rojas y azules: son datos para el shader, no el color final.
import math, os, random
import bpy
import bmesh
from mathutils import Vector, Matrix
import comic_parametros as CP
import tecnico as T

RAMPA_POS = (0.0, 0.109, 0.47, 0.95)                 # posiciones de la referencia
RAMPA_FACT = (0.06, 0.16, 0.42, 0.62)                # bandas: de casi negro al color (la mezcla luego lo realza x1.7)
RAMPA_CALIDA = ((0.0, (0.0, 0.0, 0.0)), (0.395, (0.47, 0.078, 0.037)), (0.516, (0.738, 0.212, 0.139)), (0.909, (0.855, 0.617, 0.371)))

def estilo():
    """'toon' (tema cyberpunk, EEVEE), 'cristal' (tema cristal, Cycles) o 'arcilla' (tema arcilla, Cycles, sin GP)."""
    return T.TEMA.get("piezas") or "toon"

def arcilla(): return estilo() == "arcilla"

# ---------------------------------------------------------------- materiales
def _lineal(nombre):
    c = T.colt(nombre)
    return (c[0], c[1], c[2])

def material_toon(color, nombre=None, emision=6.1, alfa=1.0, contraluz="calida"):
    """Material toon de la referencia (Material.002 de Cyberpunk_fixed.blend) con las bandas del color de la pieza.
    contraluz 'calida': la rampa naranja de la referencia; 'fria': la misma rampa en tonos del propio color (en piezas
    muy rugosas, como el cerebro, la calida salia como vetas rosadas en cada grieta)."""
    nombre = nombre or f"CP toon {color}" + (f" a{alfa:.2f}" if alfa < 1 else "") + (" fria" if contraluz == "fria" else "")
    m = bpy.data.materials.get(nombre)
    if m: return m
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); bsdf = N.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1); bsdf.inputs["Roughness"].default_value = 0.5
    s2r = N.new("ShaderNodeShaderToRGB"); sep = N.new("ShaderNodeSeparateColor")
    L.new(bsdf.outputs["BSDF"], s2r.inputs["Shader"]); L.new(s2r.outputs["Color"], sep.inputs["Color"])
    base = _lineal(color); ramas = []
    calida = list(RAMPA_CALIDA) if contraluz != "fria" else [
        (0.0, (0.0, 0.0, 0.0)), (0.395, tuple(c * 0.35 for c in base)), (0.516, tuple(c * 0.6 for c in base)),
        (0.909, tuple(c * 0.6 + 0.4 * 0.55 for c in base))]
    for canal, div, stops, fuerza in (("Red", 1.9, [(p, tuple(c * f for c in base)) for p, f in zip(RAMPA_POS, RAMPA_FACT)], emision),
                                      ("Blue", 2.6, calida, 4.5)):
        div_ = N.new("ShaderNodeMath"); div_.operation = 'DIVIDE'; div_.inputs[1].default_value = div
        L.new(sep.outputs[canal], div_.inputs[0])
        rampa = N.new("ShaderNodeValToRGB"); rampa.color_ramp.interpolation = 'CONSTANT'
        els = rampa.color_ramp.elements
        while len(els) < len(stops): els.new(0.5)
        for e, (pos, col) in zip(els, stops): e.position = pos; e.color = (*col, 1.0)
        L.new(div_.outputs[0], rampa.inputs["Fac"])
        emi = N.new("ShaderNodeEmission"); emi.inputs["Strength"].default_value = fuerza
        L.new(rampa.outputs["Color"], emi.inputs["Color"])
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs["Factor"].default_value = 0.817
        mix.inputs["A"].default_value = (0.1, 0.1, 0.1, 1.0); L.new(rampa.outputs["Color"], mix.inputs["B"])
        ms = N.new("ShaderNodeMixShader"); ms.inputs["Fac"].default_value = 0.5
        L.new(mix.outputs["Result"], ms.inputs[1]); L.new(emi.outputs["Emission"], ms.inputs[2])
        ramas.append(ms)
    final = N.new("ShaderNodeMixShader"); final.inputs["Fac"].default_value = 0.5
    L.new(ramas[0].outputs[0], final.inputs[1]); L.new(ramas[1].outputs[0], final.inputs[2])
    if alfa < 1:                                         # rayos X y cristal: el toon mezclado con transparencia
        tr = N.new("ShaderNodeBsdfTransparent"); mt = N.new("ShaderNodeMixShader"); mt.inputs["Fac"].default_value = alfa
        L.new(tr.outputs[0], mt.inputs[1]); L.new(final.outputs[0], mt.inputs[2]); final = mt
        m.surface_render_method = 'BLENDED'; m.use_transparency_overlap = False
    L.new(final.outputs[0], out.inputs["Surface"])
    return m

def material_cristal(color, alfa=0.2, borde=0.6, fuerza=0.8):
    """Cristal estilizado de las referencias: translucido, mas opaco y brillante en los bordes (Fresnel por 'Facing'),
    tenido del color de la pieza, con un reflejo suave (en Cycles recoge los neones). El resalte es la propiedad de
    objeto 'resalte' (0-1, animable): sube la opacidad, aclara el color y aviva el brillo. Funciona en Cycles y EEVEE."""
    nombre = f"CP cristal {color} {alfa:.2f}"
    m = bpy.data.materials.get(nombre)
    if m: return m
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    rango = N.new("ShaderNodeMapRange"); rango.inputs["To Min"].default_value = alfa; rango.inputs["To Max"].default_value = borde
    L.new(lw.outputs["Facing"], rango.inputs["Value"])
    res = N.new("ShaderNodeAttribute"); res.attribute_type = 'OBJECT'; res.attribute_name = "resalte"
    sube = N.new("ShaderNodeMath"); sube.operation = 'MULTIPLY_ADD'; sube.use_clamp = True
    L.new(res.outputs["Fac"], sube.inputs[0]); sube.inputs[1].default_value = 0.15; L.new(rango.outputs["Result"], sube.inputs[2])
    tinte = N.new("ShaderNodeMix"); tinte.data_type = 'RGBA'
    tinte.inputs["A"].default_value = (*_lineal(color), 1); tinte.inputs["B"].default_value = (1, 1, 1, 1)
    claro = N.new("ShaderNodeMath"); claro.operation = 'MULTIPLY'; claro.inputs[1].default_value = 0.12
    L.new(res.outputs["Fac"], claro.inputs[0]); L.new(claro.outputs[0], tinte.inputs["Factor"])
    vivo = N.new("ShaderNodeMath"); vivo.operation = 'MULTIPLY_ADD'
    L.new(res.outputs["Fac"], vivo.inputs[0]); vivo.inputs[1].default_value = 0.9; vivo.inputs[2].default_value = fuerza
    emi = N.new("ShaderNodeEmission"); L.new(tinte.outputs["Result"], emi.inputs["Color"]); L.new(vivo.outputs[0], emi.inputs["Strength"])
    brillo_ = N.new("ShaderNodeBsdfGlossy"); brillo_.inputs["Roughness"].default_value = 0.12
    refl = N.new("ShaderNodeMixShader"); refl.inputs["Fac"].default_value = 0.18
    L.new(emi.outputs[0], refl.inputs[1]); L.new(brillo_.outputs[0], refl.inputs[2])
    tr = N.new("ShaderNodeBsdfTransparent"); final = N.new("ShaderNodeMixShader")
    L.new(sube.outputs[0], final.inputs["Fac"]); L.new(tr.outputs[0], final.inputs[1]); L.new(refl.outputs[0], final.inputs[2])
    L.new(final.outputs[0], out.inputs["Surface"])
    m.surface_render_method = 'BLENDED'; m.use_backface_culling = False; m.use_transparency_overlap = True
    return m

def material_neon(color, fuerza=8.0):
    """Neon: emision pura (los tubos, los bordes de las peanas, los LEDs)."""
    nombre = f"CP neon {color} {fuerza:g}"
    m = bpy.data.materials.get(nombre)
    if m: return m
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (*_lineal(color), 1); emi.inputs["Strength"].default_value = fuerza
    m.node_tree.links.new(emi.outputs[0], out.inputs["Surface"])
    return m

def material_suelo(color="#0B0F1A", fuerza=1.0):
    """Suelo: emision plana oscura. Con el toon, la caida de la luz roja pintaba bandas enormes sobre el suelo."""
    m = bpy.data.materials.get(f"CP suelo {color}")
    if m: return m
    m = bpy.data.materials.new(f"CP suelo {color}"); m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = CP.color_lineal(color); emi.inputs["Strength"].default_value = fuerza
    m.node_tree.links.new(emi.outputs[0], out.inputs["Surface"])
    return m

def material_resalte():
    """Casco invertido lima del resalte: solo se ven sus caras traseras, alrededor de la silueta. Su opacidad y su brillo
    siguen la propiedad de objeto 'resalte' (0-1): la animacion la sube y la baja con un fundido (entra y sale suave)."""
    m = bpy.data.materials.get("CP resalte")
    if m: return m
    m = bpy.data.materials.new("CP resalte"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (*_lineal("lima"), 1); emi.inputs["Strength"].default_value = 3.0
    res = N.new("ShaderNodeAttribute"); res.attribute_type = 'OBJECT'; res.attribute_name = "resalte"
    tr = N.new("ShaderNodeBsdfTransparent"); mix = N.new("ShaderNodeMixShader")
    L.new(res.outputs["Fac"], mix.inputs["Fac"]); L.new(tr.outputs[0], mix.inputs[1]); L.new(emi.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    # DITHERED y no BLENDED: escribe profundidad, asi se ve dentro de piezas translucidas (las fichas del tubo SQS);
    # BLENDED se ordena por objeto y el tubo lo tapaba. Con las muestras de TAA el fundido sale liso.
    m.use_backface_culling = True; m.surface_render_method = 'DITHERED'
    return m

# ---------------------------------------------------------------- mallas
def _malla(nombre, caras, suave_grados=35.0):
    """Malla a partir de poligonos (mundo). Suelda vertices y sombrea suave por angulo."""
    bm = bmesh.new()
    for pts in caras:
        vs = [bm.verts.new(p) for p in pts]
        try: bm.faces.new(vs)
        except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(suave_grados))
    except AttributeError: pass
    return me

def caras_mundo(q, M):
    caras, _ = T.caras_forma(q)
    return [[M @ v for v in pts] for pts, nor, tipo in caras if tipo not in ("dentro", "fondo") or q["forma"] == "tubo"]

def tubo_camino(nombre, pts, radio, material, col_):
    """Manguera: curva con bisel por el camino suavizado."""
    cu = bpy.data.curves.new(nombre, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = radio; cu.bevel_resolution = 4
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1)
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(nombre, cu); col_.objects.link(ob); cu.materials.append(material)
    return ob

def caras_pieza(p, M):
    f = p["forma"]
    if f == "malla":                                     # modelo descargado: sus caras ya estan en el mundo
        V = p["_malla"]["vertices"]; return [[Vector(V[i]) for i in cara] for cara in p["_malla"]["caras"] if len(cara) >= 3]
    if f == "varilla": return caras_mundo(dict(p, forma="cilindro"), M)
    if f == "icono": return [cm for q in T.partes_icono(p) for cm in caras_mundo(q, M @ T.matriz_pieza(q))]
    return caras_mundo(p, M)

def pieza(p, col_, params, rx=False, col_neon=None):
    """Malla de una pieza del guion (o su version de rayos X, translucida). Las mangueras son tubos de neon.
    col_neon: coleccion para lo que brilla (mangueras, aros de las peanas), fuera de la que contornea Line Art."""
    col_neon = col_neon or col_
    M = T.matriz_pieza(p); f = p["forma"]; c = p["color"]
    trans = rx or p["material"] in ("transparente", "liquido")
    nombre = p["id"] + ("_rx" if rx else "")
    cristal = estilo() == "cristal"
    if arcilla(): return pieza_arcilla(p, col_, params, rx, col_neon)
    if f == "manguera":
        pts = T.suave3([Vector(v) for v in p["camino"]])
        if not cristal:
            return tubo_camino(nombre, pts, p["radio"], material_neon("azul_neon", 9.0 if not rx else 3.0), col_neon)
        # cristal: una linea de luz fina con un nodo brillante en cada esquina y en los extremos
        ob = tubo_camino(nombre, pts, min(p["radio"] * 0.35, 0.008), material_neon("azul_neon", 3.5 if not rx else 1.2), col_neon)
        if not rx: hijo(nodos(p["id"] + "_nodos", [Vector(v) for v in p["camino"]], 0.018, col_neon), ob)
        return ob
    if f == "biohazard":         # alerta: el simbolo de las fichas del flujo, de cara a la camara, como pieza
        vista = T.dir_camara(params); dere = (-vista).cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(-vista).normalized()
        cen = M @ Vector((0, 0, p["alto"] / 2))
        def pl(c0, x, y, k=0): return c0 + dere * x + arr * y + vista * (0.003 * k)
        pin = PincelMalla(nombre, vista); T.dibujar_biohazard(pin, pl, cen, p["alto"], c)
        ob = pin.objeto(col_); ob.lineart.usage = 'OCCLUSION_ONLY'      # su contorno ya es tinta
        return ob
    me = _malla(nombre, caras_pieza(p, M), suave_grados=85.0 if f == "cerebro" else 35.0)   # circunvoluciones lisas
    if cristal:
        if f == "peana": mat_ = material_cristal("azul_base", alfa=0.55, borde=0.85, fuerza=0.6)
        else: mat_ = material_cristal(c, alfa=0.1 if rx else (0.12 if trans else 0.2), borde=0.35 if rx else 0.6)
    else:
        mat_ = material_toon(c, alfa=0.25 if trans else 1.0, contraluz="fria" if f == "cerebro" else "calida")
    me.materials.append(mat_)
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    if f == "peana" and not rx:                          # borde luminoso: un aro emisivo por encima del canto
        perfil = T.perfil_redondeado(p); h = p["alto"]
        aro = [M @ Vector((x * 0.97, y * 0.97, h + 0.002)) for x, y in perfil]
        hijo(tubo_camino(p["id"] + "_neon", aro + aro[:1], 0.0045 if cristal else 0.008,
                         material_neon("cian", 4.0 if cristal else 12.0), col_neon), ob)
    return ob

def nodos(nombre, pts, radio, col_, color="cian", fuerza=5.0):
    """Puntos brillantes en las uniones de una linea de luz (los nodos de las referencias)."""
    bm = bmesh.new()
    for c in pts:
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=radio, matrix=Matrix.Translation(c))
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for pl in me.polygons: pl.use_smooth = True
    me.materials.append(material_neon(color, fuerza))
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    return ob

def chispa(nombre, radio, col_, color="blanco", fuerza=30.0):
    """Bola de luz de la punta de una manguera que se esta dibujando. Material propio (la animacion apaga su emision) y
    fuera de Line Art (va en la coleccion del neon). Devuelve (objeto, nodo de emision)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=radio)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for pl in me.polygons: pl.use_smooth = True
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (*_lineal(color), 1); emi.inputs["Strength"].default_value = fuerza
    m.node_tree.links.new(emi.outputs[0], out.inputs["Surface"])
    me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    ob.hide_render = True; ob.hide_viewport = True; ob.visible_shadow = False
    return ob, emi

def hijo(ob, padre):
    """Emparenta conservando la posicion de mundo (las piezas se construyen en coordenadas de mundo)."""
    ob.parent = padre; ob.matrix_parent_inverse = padre.matrix_world.inverted()
    return ob

RESALTE = "Resalte"                                       # nombre del modificador (la animacion lo enciende y apaga)

def casco_resalte(ob, p=None, grosor=0.012):
    """Resalte lima: casco invertido en la PROPIA pieza (Solidify hacia fuera, normales giradas, material lima con la
    cara trasera oculta): solo asoma alrededor de la silueta. En la pieza y no en una copia, porque una copia repetiria
    sus caras a la misma profundidad (z-fighting). Es malla: respeta la profundidad, que el GP no respeta.
    Apagado por defecto; la animacion lo enciende con modifiers["Resalte"].show_render."""
    if ob.type != 'MESH': return None
    if p and (p["material"] in ("transparente", "liquido") or p["forma"] in ("tubo", "biohazard")):
        return None            # piezas abiertas o translucidas: el casco se ve entero (un tubo lima relleno)
    ob.data.materials.append(material_resalte())
    mod = ob.modifiers.new(RESALTE, 'SOLIDIFY'); mod.thickness = grosor; mod.offset = 1.0
    mod.use_flip_normals = True; mod.material_offset = len(ob.data.materials) - 1; mod.use_rim = False
    mod.show_render = False; mod.show_viewport = False
    ob["resalte"] = 0.0                                   # opacidad del casco (fundido); el material la lee
    return mod

# ---------------------------------------------------------------- pincel de mallas: el dibujo de adornos sin GP
def _material_plano(nombre_gp):
    """Material de malla para un nombre de material GP del estilo tecnico ('T plano lima 0.3', 'T tinta', 'T verde b2'...)."""
    if arcilla(): return material_adorno_arcilla(nombre_gp)       # diorama: plastico PBR, no emision plana
    m = bpy.data.materials.get("CPm " + nombre_gp)
    if m: return m
    partes = nombre_gp.split(" "); alfa = 1.0; valor = 1.0
    if nombre_gp.startswith("T tinta"): color = "negro" if nombre_gp == "T tinta" else "gris_oscuro"   # arcilla: grafito
    elif partes[1] in ("plano", "trazo"):
        color = partes[2]; alfa = float(partes[3]) if len(partes) > 3 else 1.0
    else:
        color = partes[1]; b = partes[2] if len(partes) > 2 else "b1"
        valor = T.BANDAS[int(b[1])] if b.startswith("b") and b[1:2].isdigit() else 1.0
    m = bpy.data.materials.new("CPm " + nombre_gp); m.use_nodes = True
    N = m.node_tree.nodes
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); emi = N.new("ShaderNodeEmission")
    col = T.colt(color, valor=valor); emi.inputs["Color"].default_value = (col[0], col[1], col[2], 1)
    emi.inputs["Strength"].default_value = 1.6 if color not in ("negro", "gris_oscuro") else 1.0
    final = emi
    if alfa < 1:
        tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader"); mx.inputs["Fac"].default_value = alfa
        m.node_tree.links.new(tr.outputs[0], mx.inputs[1]); m.node_tree.links.new(emi.outputs[0], mx.inputs[2]); final = mx
        m.surface_render_method = 'BLENDED'
    m.node_tree.links.new(final.outputs[0], out.inputs["Surface"])
    return m

def _filete(q, rad, n=4):
    """Poligono 3D cerrado con las esquinas redondeadas (Bezier cuadratica de n tramos y radio hasta 'rad')."""
    out = []
    for i, p in enumerate(q):
        a, c = q[i - 1], q[(i + 1) % len(q)]; u, v = a - p, c - p
        if u.length < 1e-9 or v.length < 1e-9 or u.normalized().dot(v.normalized()) < -0.985: out.append(p); continue
        rr = min(rad, u.length / 2.2, v.length / 2.2)
        p0, p1 = p + u.normalized() * rr, p + v.normalized() * rr
        for k in range(n + 1):
            t = k / n; out.append(p0 * (1 - t) ** 2 + p * 2 * t * (1 - t) + p1 * t * t)
    return out

class PincelMalla:
    """Misma interfaz que tecnico.Pincel (cara, linea), pero escribe poligonos en una malla: los adornos se dibujan con
    el codigo de siempre (tecnico.dibujar_adornos) y quedan ocultos por las piezas de delante, que el GP no respeta.
    Las lineas son cintas perpendiculares a la direccion de vista (la camara isometrica no cambia de angulo)."""
    ADELANTE_LINEA = 0.0015
    CAPA = 0.0003          # arcilla: cada cara, un poco por delante de la anterior (el orden de dibujo, como en GP)
    RELIEVE = 0.0018       # arcilla: grosor de las placas (pantallas, rejillas, carteles) hacia la camara
    def __init__(self, nombre, vista):
        self.nombre = nombre; self.vista = vista.normalized(); self.bm = bmesh.new(); self.mats = []
        self.empuje = None; self.lp = self; self.n_caras = 0
    def _mi(self, nombre):
        if nombre not in self.mats: self.mats.append(nombre)
        return self.mats.index(nombre)
    def _capa(self):
        """Arcilla: desplazamiento (por la vista) de la siguiente cara: una capa mas por cada llamada a cara()."""
        d = self.vista * self.CAPA * min(self.n_caras, 30); self.n_caras += 1
        return d
    def _cara(self, pts, mi, d=None):
        if len(pts) < 3: return
        if arcilla():                     # capas sin z-fighting (el punto de la exclamacion sobre el triangulo)
            pts = [p + (self._capa() if d is None else d) for p in pts]
        try:
            f = self.bm.faces.new([self.bm.verts.new(p) for p in pts]); f.material_index = mi; f.smooth = False
        except ValueError: return
        if arcilla():                     # placa con grosor: la cara se adelanta y deja cantos (recoge luz y sombra)
            r = bmesh.ops.extrude_face_region(self.bm, geom=[f])
            nuevos = [v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(self.bm, verts=nuevos, vec=self.vista * self.RELIEVE)
            for g in r["geom"]:
                if isinstance(g, bmesh.types.BMFace): g.material_index = mi
    def cara(self, pts, nombre, radio=0.0004):
        if nombre.startswith("T resalte"): return
        rej = getattr(pts, "rejilla", None)
        if rej:                       # relleno sobre cara curva: cuadrilateros que siguen la superficie (sin z-fighting)
            mi = self._mi(nombre); d = self._capa() if arcilla() else None     # toda la rejilla en la misma capa
            for A, B in zip(rej, rej[1:]):
                for i in range(len(A) - 1): self._cara([Vector(A[i]), Vector(A[i + 1]), Vector(B[i + 1]), Vector(B[i])], mi, d)
            return
        self._cara([Vector(p) for p in pts], self._mi(nombre))
    def linea(self, pts, nombre="T tinta", radio=None, cerrado=False, afilar=False):
        if nombre.startswith("T resalte"): return
        r = T.R_TINTA if radio is None else radio
        nor = getattr(pts, "normales", None); pts = [Vector(p) for p in pts]
        if nor and len(nor) != len(pts): nor = None
        if cerrado and len(pts) > 2: pts = pts + pts[:1]; nor = (nor + nor[:1]) if nor else None
        mi = self._mi(nombre)
        if arcilla(): return self._linea_continua(pts, nor, r, mi, nombre)
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            t = b - a
            if t.length < 1e-7: continue
            n = (Vector(nor[i]) + Vector(nor[i + 1])) if nor else None
            # sobre una cara curva la cinta va pegada a la superficie; si no, perpendicular a la vista
            lado = t.cross(n) if n is not None and n.length > 1e-6 else t.cross(self.vista)
            # la linea, 1.5 mm por delante de su sitio: en GP manda el orden de dibujo, en malla la profundidad, y una
            # linea en el mismo plano que el relleno que bordea parpadea (z-fighting en carteles y pantallas)
            sube = (n.normalized() if n is not None and n.length > 1e-6 else self.vista) * self.ADELANTE_LINEA
            a, b = a + sube, b + sube
            if lado.length < 1e-7: continue
            lado = lado.normalized() * r; ext = t.normalized() * r * 0.5      # un poco de solape: sin huecos en los codos
            self._cara([a - ext - lado, b + ext - lado, b + ext + lado, a - ext + lado], mi)
    def _linea_continua(self, pts, nor, r, mi, nombre):
        """Arcilla: la linea es UNA tira con los vertices compartidos y las esquinas a inglete (sin solapes que se vean
        como pliegues). Un contorno cerrado grande de tinta (cartel, alerta, reloj, pantalla) es un marco moldeado."""
        q, nq = [pts[0]], ([nor[0]] if nor else None)
        for i, p in enumerate(pts[1:], 1):
            if (p - q[-1]).length > 1e-6:
                q.append(p)
                if nq is not None: nq.append(nor[i])
        if len(q) < 2: return
        cerrada = len(q) > 3 and (q[0] - q[-1]).length < 1e-5
        if cerrada: q = q[:-1]; nq = nq[:-1] if nq else None
        n = len(q); segs = n if cerrada else n - 1
        perimetro = sum((q[(i + 1) % n] - q[i]).length for i in range(segs))
        if cerrada and nombre.startswith("T tinta") and nq is None and perimetro >= 0.25:
            return self._marco(q, r, mi)
        def normal(i):
            if nq is not None and Vector(nq[i]).length > 1e-6: return Vector(nq[i]).normalized()
            return self.vista
        lados = []
        for i in range(segs):
            a, b = q[i], q[(i + 1) % n]; N = normal(i) + normal((i + 1) % n)
            l = (b - a).cross(N.normalized() if N.length > 1e-6 else self.vista)
            lados.append(l.normalized() if l.length > 1e-9 else None)
        for i in range(segs):                              # tramos degenerados: el lado del vecino
            if lados[i] is None: lados[i] = next((l for l in lados if l is not None), Vector((1, 0, 0)))
        # por delante de las placas ya dibujadas (que tienen relieve): si no, la barra de la exclamacion queda tapada
        delante = self.ADELANTE_LINEA + (self.RELIEVE + self.CAPA * min(self.n_caras, 30) if self.n_caras else 0.0)
        izq, der = [], []
        for i in range(n):
            if cerrada: lp, ln = lados[i - 1], lados[i % segs]
            else: lp, ln = lados[max(0, i - 1)], lados[min(segs - 1, i)]
            m = lp + ln; m = m.normalized() if m.length > 1e-6 else ln
            esc = min(2.5, 1.0 / max(0.4, m.dot(ln)))     # inglete, con tope en los picos muy agudos
            # adelantar SIEMPRE por la vista: con la camara ortografica no mueve nada en pantalla. Por la normal de una cara
            # lateral, el aro de un LED se separaba de su disco (que se adelanta por la vista) y se veia doble y borroso
            c = q[i] + self.vista * delante
            izq.append(self.bm.verts.new(c + m * r * esc)); der.append(self.bm.verts.new(c - m * r * esc))
        for i in range(segs):
            j = (i + 1) % n
            try:
                f = self.bm.faces.new([izq[i], izq[j], der[j], der[i]]); f.material_index = mi; f.smooth = False
            except ValueError: pass

    def _marco(self, q, r, mi, lados=10):
        """Marco moldeado: tubo redondeado de una pieza por el contorno (esquinas redondeadas), medio hundido en la placa."""
        R = max(r * 1.15, 0.006)
        pts = _filete(q, R * 1.4); n = len(pts); N0 = self.vista      # radio <= 1,4 R: el tubo tapa la esquina de la placa
        anillos = []
        for i in range(n):
            t = pts[(i + 1) % n] - pts[i - 1]
            t = t.normalized() if t.length > 1e-9 else Vector((1, 0, 0))
            u = t.cross(N0); u = u.normalized() if u.length > 1e-9 else Vector((0, 0, 1)); v = u.cross(t).normalized()
            if v.dot(N0) < 0: v = -v
            c = pts[i] + N0 * (self.ADELANTE_LINEA + self.RELIEVE + R * 0.3)
            anillos.append([self.bm.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * R)
                            for a in [2 * math.pi * k / lados for k in range(lados)]])
        for i in range(n):
            A, B = anillos[i], anillos[(i + 1) % n]
            for k in range(lados):
                try:
                    f = self.bm.faces.new([A[k], A[(k + 1) % lados], B[(k + 1) % lados], B[k]]); f.material_index = mi; f.smooth = True
                except ValueError: pass

    def objeto(self, col_):
        if not self.bm.faces: self.bm.free(); return None
        me = bpy.data.meshes.new(self.nombre); self.bm.normal_update(); self.bm.to_mesh(me); self.bm.free()
        for n in self.mats: me.materials.append(_material_plano(n))
        ob = bpy.data.objects.new(self.nombre, me); col_.objects.link(ob)
        return ob

def adornos_pieza(p, ob, col_, params):
    """Adornos (o el detalle generico) de la pieza como malla hija de la pieza. Devuelve puntos extra (carteles)."""
    if arcilla() and p["forma"] == "manguera": return []          # las cintas no llevan los conectores de las mangueras
    vista = T.dir_camara(params); M = T.matriz_pieza(p)
    pin = PincelMalla(p["id"] + "_adornos", vista); extra = []
    if p.get("_adornos"):
        extra = T.dibujar_adornos(p, M, pin, vista, p["color"]) or []
    elif p["forma"] not in ("manguera", "varilla", "muelle", "peana", "icono") and p["material"] not in ("transparente", "liquido"):
        T.detalles(p, M, pin, vista)
    a = pin.objeto(col_)
    if a is not None:
        hijo(a, ob)
    return extra

# ---------------------------------------------------------------- entorno
def suelo_y_rejilla(col_, centro, tam, paso=0.85):
    """Suelo oscuro (emision plana) con una rejilla de neon tenue, todo malla."""
    W = max(12.0, tam * 3)
    bm = bmesh.new()
    vs = [bm.verts.new((centro.x + x, centro.y + y, 0)) for x, y in ((-W, -W), (W, -W), (W, W), (-W, W))]
    bm.faces.new(vs); me = bpy.data.meshes.new("Suelo"); bm.to_mesh(me); bm.free()
    me.materials.append(material_suelo()); suelo = bpy.data.objects.new("Suelo", me); col_.objects.link(suelo)
    bm = bmesh.new(); r = 0.006; n = int(2 * W / paso)
    for k in range(n + 1):
        u = -W + k * paso
        for (x0, y0, x1, y1) in ((centro.x + u - r, centro.y - W, centro.x + u + r, centro.y + W),
                                 (centro.x - W, centro.y + u - r, centro.x + W, centro.y + u + r)):
            bm.faces.new([bm.verts.new(v) for v in ((x0, y0, 0.002), (x1, y0, 0.002), (x1, y1, 0.002), (x0, y1, 0.002))])
    me = bpy.data.meshes.new("Rejilla"); bm.to_mesh(me); bm.free()
    me.materials.append(material_neon("azul", 0.35)); rej = bpy.data.objects.new("Rejilla", me); col_.objects.link(rej)
    return suelo

def suelo_circuito(col_, centro, tam, semilla=11):
    """Suelo azul marino con pistas de circuito finas y apagadas (la placa de la referencia de los cubos del LLM):
    trazos rectos que giran 45 grados, con una pastilla redonda en cada extremo; algunas pastillas en magenta."""
    W = max(10.0, tam * 2.2)
    bm = bmesh.new()
    vs = [bm.verts.new((centro.x + x, centro.y + y, 0)) for x, y in ((-W, -W), (W, -W), (W, W), (-W, W))]
    bm.faces.new(vs); me = bpy.data.meshes.new("Suelo"); bm.to_mesh(me); bm.free()
    me.materials.append(material_suelo("#070D22")); suelo = bpy.data.objects.new("Suelo", me); col_.objects.link(suelo)
    rnd = random.Random(semilla); bm = bmesh.new(); r = 0.0045; z = 0.003
    def cinta(a, b, mi):
        t = (b - a); lado = Vector((-t.y, t.x, 0)).normalized() * r
        f = bm.faces.new([bm.verts.new(v) for v in (a - lado, b - lado, b + lado, a + lado)]); f.material_index = mi
    def pastilla(c, mi, rr=0.016):
        f = bm.faces.new([bm.verts.new(c + Vector((rr * math.cos(2 * math.pi * i / 10), rr * math.sin(2 * math.pi * i / 10), 0.001)))
                          for i in range(10)]); f.material_index = mi
    for _ in range(int(60 * (W / 10.0) ** 2)):
        p = Vector((centro.x + rnd.uniform(-W, W), centro.y + rnd.uniform(-W, W), z)); ang = rnd.choice((0, 90, 180, 270))
        inicio = p.copy()
        for _ in range(rnd.randint(2, 5)):
            L = rnd.uniform(0.15, 0.9); q = p + Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)) * L
            cinta(p, q, 0); p = q
            ang += rnd.choice((0, 0, 45, -45))
        pastilla(inicio, 1 if rnd.random() > 0.2 else 2); pastilla(p, 1 if rnd.random() > 0.2 else 2)
    me = bpy.data.meshes.new("Circuito"); bm.to_mesh(me); bm.free()
    for mt in (material_neon("azul_base", 2.6), material_neon("azul_neon", 1.3), material_neon("rojo", 0.9)): me.materials.append(mt)
    pistas = bpy.data.objects.new("Circuito", me); col_.objects.link(pistas)
    return suelo

def suelo(col_, centro, tam, caja=None):
    if arcilla(): return suelo_claro(col_, centro, tam, caja)
    return suelo_circuito(col_, centro, tam) if estilo() == "cristal" else suelo_y_rejilla(col_, centro, tam)

# ---------------------------------------------------------------- escena
def luces(centro, tam, col_):
    """Luces de datos para el toon, como en la referencia: roja = principal (arriba, delante a la derecha),
    azul = contraluz (detras a la izquierda), blancas debiles de relleno. Escaladas al tamano de la maqueta."""
    if arcilla(): return luces_estudio(centro, tam, col_)
    k = max(1.0, tam / 3.0)
    def area(nombre, color, energia, desde, tamano):
        d = bpy.data.lights.new(nombre, 'AREA'); d.color = color; d.energy = energia * k * k; d.size = tamano * k
        ob = bpy.data.objects.new(nombre, d); col_.objects.link(ob)
        ob.location = centro + Vector(desde) * k
        ob.rotation_euler = (centro - ob.location).to_track_quat('-Z', 'Y').to_euler()
        return ob
    area("Luz principal (R)", (1, 0, 0), 900, (2.5, -4.0, 5.5), 3.0)
    area("Contraluz (B)", (0, 0, 1), 700, (-4.0, 5.0, 0.6), 3.0)        # detras y bajo: solo perfila los bordes
    area("Relleno (R)", (1, 0, 0), 120, (-4.5, -3.0, 2.0), 2.5)          # sube la cara izquierda una banda

def contornos(col_piezas, col_, radio=None, color=None, nombre="Contornos"):
    """Line Art sobre la coleccion de piezas, adelantado hacia la camara (stroke_depth_offset) como la referencia.
    Toon: tinta negra. Cristal: bordes de luz azul claro, finos y nitidos. 'color' (de la paleta del tema): trazo plano
    de ese color, sin brillo (el cerebro: sus surcos en neon). Las piezas de otras colecciones tambien ocultan lineas."""
    cristal = estilo() == "cristal"; radio = radio or (0.0035 if cristal else 0.006)
    gp = bpy.data.grease_pencils.new(nombre); ob = bpy.data.objects.new(nombre, gp); col_.objects.link(ob)
    L = gp.layers.new("lineas"); L.frames.new(1); L.use_lights = False
    mt = bpy.data.materials.new("CP linea" + (f" {color}" if color else "")); bpy.data.materials.create_gpencil_data(mt)
    if color: color = (*_lineal(color), 1.0)
    else: color = CP.color_lineal("#A8DCFF") if cristal else (0.0, 0.0, 0.0, 1.0)
    mt.grease_pencil.show_stroke = True; mt.grease_pencil.show_fill = False; mt.grease_pencil.color = color
    # sin FX Glow: con pocas muestras granulaba los bordes y los emborronaba (las referencias tienen la linea nitida)
    gp.materials.append(mt)
    mod = ob.modifiers.new("Line Art", 'LINEART')
    mod.source_type = 'COLLECTION'; mod.source_collection = col_piezas
    mod.target_layer = "lineas"; mod.target_material = mt
    mod.radius = radio; mod.stroke_depth_offset = 0.05; mod.use_intersection = True; mod.use_crease = True
    return ob

def render(sc, params):
    """Toon (cyberpunk): EEVEE como la referencia (raytracing por pantalla, sombras, Medium Contrast, fondo casi negro).
    Cristal: Cycles en la GPU, con rebotes de transparencia de sobra (capas de cristal) y fondo azul marino."""
    import gp_base as GB
    if arcilla(): return render_arcilla(sc, params)
    if estilo() == "cristal":
        sc.render.engine = 'CYCLES'; GB.gpu_cycles(sc)
        cy = sc.cycles; cy.samples = 32; cy.use_denoising = True; cy.use_adaptive_sampling = True
        cy.max_bounces = 8; cy.transparent_max_bounces = 24; cy.transmission_bounces = 8
        cy.caustics_reflective = False; cy.caustics_refractive = False; cy.sample_clamp_indirect = 4.0
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'Medium High Contrast'
        fondo = CP.color_lineal("#050A1A")
    else:
        sc.render.engine = 'BLENDER_EEVEE'
        e = sc.eevee; e.taa_render_samples = 32; e.use_shadows = True; e.use_raytracing = True
        e.ray_tracing_method = 'SCREEN'; e.use_fast_gi = True; e.shadow_resolution_scale = 1.0
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'Medium Contrast'
        fondo = (0.051, 0.051, 0.051, 1)
    if not sc.world: sc.world = bpy.data.worlds.new("Cyberpunk")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[0].default_value = fondo; bg.inputs[1].default_value = 1.0
    brillo(sc, T.TEMA.get("bloom") or ("nitido" if estilo() == "cristal" else "normal"))

# Glare del compositor por tema: (umbral, intensidad, tamano). 'minimo' (cyberpunk): solo lo mas intenso (aros de las
# peanas y mangueras) y casi sin halo; 'nitido' (cristal): brillo corto pegado a las lineas; 'normal': el de antes.
BLOOM = {"normal": (1.2, 0.4, 0.45), "nitido": (1.5, 0.22, 0.22), "minimo": (3.0, 0.06, 0.08),
         "arcilla": (2.6, 0.05, 0.12)}          # arcilla: un halo minimo solo en lo que emite (fichas, chispa)

def brillo(sc, nivel="normal"):
    """Glare (bloom) en el compositor: el neon brilla, con la intensidad del tema (BLOOM)."""
    try:
        grupo = bpy.data.node_groups.new("CP compositor", 'CompositorNodeTree')
        sc.compositing_node_group = grupo
    except (AttributeError, TypeError):
        sc.use_nodes = True; grupo = sc.node_tree
    N = grupo.nodes; Lk = grupo.links
    for n in list(N): N.remove(n)
    rl = N.new("CompositorNodeRLayers"); gl = N.new("CompositorNodeGlare")
    if hasattr(gl, "glare_type"): gl.glare_type = 'BLOOM'            # Blender 4.x
    else: gl.inputs["Type"].default_value = 'Bloom'                   # 5.x: el tipo es una entrada (menu)
    umbral, fuerza, tam = BLOOM.get(nivel, BLOOM["normal"])
    for nombre, valor in (("Threshold", umbral), ("Strength", fuerza), ("Size", tam), ("Quality", 'High')):
        if nombre in gl.inputs: gl.inputs[nombre].default_value = valor
    if hasattr(grupo, "interface") and not any(i.in_out == 'OUTPUT' for i in grupo.interface.items_tree):
        grupo.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    out = N.new("NodeGroupOutput") if hasattr(grupo, "interface") else N.new("CompositorNodeComposite")
    Lk.new(rl.outputs["Image"], gl.inputs["Image"]); Lk.new(gl.outputs["Image"], out.inputs[0])


# ================================================================ tema ARCILLA (todo malla, Cycles, sin Grease Pencil)
# Referencias en comic/referencias/arcilla y pin_945052303052175320: maquetas de arcilla blanca mate, el color solo en
# los acentos (turquesa el sistema, naranja los datos), cintas transportadoras con fichas brillantes, luz de estudio suave
# y fondo claro. Sin contornos: las formas se leen por la luz, la oclusion y las esquinas redondeadas (Bevel).
CLAROS_ARCILLA = ("blanco", "blanco_hueso", "gris_claro", "azul_claro", "papel", "baldosa", "metal", "azul_base")

# Superficies del diorama (PBR): rugosidad, capa (coat) y su rugosidad, subsurface (peso; escala en m, de maqueta),
# transmision. Primarias: polimero blanco mate, plastico gris satinado, ceramica blanca calida. Secundarias: acrilico
# (translucido esmerilado), vidrio (claro), polimero brillante (acentos de color), goma (bandas).
SUPERFICIES = {
    # UN SOLO material para todo lo opaco (el usuario: "el mismo material y solo cambiarle el color"): plastico mate
    # texturizado. Los demas tipos opacos se tratan como este; solo el acrilico y el vidrio (transparentes) son otros.
    "plastico": dict(rug=0.45, coat=0.12, coat_rug=0.22, sss=0.08, trans=0.0, spec=0.45),
    "polimero": dict(rug=0.52, coat=0.0, coat_rug=0.3, sss=0.12, trans=0.0, spec=0.42),
    "satinado": dict(rug=0.34, coat=0.15, coat_rug=0.25, sss=0.05, trans=0.0, spec=0.5),
    "ceramica": dict(rug=0.3, coat=0.35, coat_rug=0.18, sss=0.1, trans=0.0, spec=0.5),
    "brillante": dict(rug=0.2, coat=0.5, coat_rug=0.08, sss=0.06, trans=0.0, spec=0.55),
    "acrilico": dict(rug=0.2, coat=0.3, coat_rug=0.05, sss=0.0, trans=1.0, spec=0.5),
    "vidrio": dict(rug=0.03, coat=0.0, coat_rug=0.0, sss=0.0, trans=1.0, spec=0.5),
    "goma": dict(rug=0.72, coat=0.0, coat_rug=0.3, sss=0.0, trans=0.0, spec=0.3),
}

def textura_plastico(N, L, b, tx, rug, con_rugosidad=True):
    """Textura descargada de plastico (ambientCG, CC0; tema: 'textura') en un material del diorama: su relieve
    (Displacement por Bump) y su rugosidad; el color sigue siendo el de la paleta. Proyeccion de caja en coordenadas
    de objeto (las piezas no tienen UV). Sin la descarga hecha, no hace nada."""
    carpeta = os.path.join(CP.DESCARGAS, "ambientcg", tx["id"])
    disp = os.path.join(carpeta, f'{tx["id"]}_1K-JPG_Displacement.jpg'); rugo = os.path.join(carpeta, f'{tx["id"]}_1K-JPG_Roughness.jpg')
    if not os.path.exists(disp): return
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); e = float(tx.get("escala", 3.0))
    mp.inputs["Scale"].default_value = (e, e, e); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    def imagen(ruta):
        im = bpy.data.images.load(ruta, check_existing=True); im.colorspace_settings.name = 'Non-Color'
        n = N.new("ShaderNodeTexImage"); n.image = im; n.projection = 'BOX'; n.projection_blend = 0.3; n.interpolation = 'Cubic'
        L.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    bump = N.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = tx.get("distancia", 0.002)
    # fuerza = relieve x 'grano' de la escena (propiedad que la animacion baja en los planos de detalle, donde el grano
    # se ve aumentado): atributo de capa de vista, que busca en la capa, la escena y el mundo
    grano = N.new("ShaderNodeAttribute"); grano.attribute_type = 'VIEW_LAYER'; grano.attribute_name = "grano"
    fz = N.new("ShaderNodeMath"); fz.operation = 'MULTIPLY'; fz.inputs[1].default_value = tx.get("relieve", 0.35)
    L.new(grano.outputs["Fac"], fz.inputs[0]); L.new(fz.outputs[0], bump.inputs["Strength"])
    L.new(imagen(disp).outputs["Color"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])
    if con_rugosidad and os.path.exists(rugo):
        mr = N.new("ShaderNodeMapRange"); d = tx.get("rug", 0.12)
        mr.inputs["To Min"].default_value = max(0.03, rug - d); mr.inputs["To Max"].default_value = min(1.0, rug + d)
        L.new(imagen(rugo).outputs["Color"], mr.inputs["Value"]); L.new(mr.outputs["Result"], b.inputs["Roughness"])

def material_arcilla(color, acento=None, alfa=1.0, brillo=0.0, vidrio=False, rugosidad=None, tipo=None, liso=False, ao=False):
    """Material PBR del diorama. tipo: una de SUPERFICIES (por defecto polimero; vidrio=True equivale a 'vidrio').
    Con 'acento', las caras que miran arriba (normal z > 0.6) son polimero brillante de ese color (mas lisas y con capa)
    y los lados conservan el cuerpo con un 8 % del acento. El resalte (propiedad de objeto 'resalte', 0-1, animable)
    enciende un borde turquesa (Fresnel). alfa < 1: rayos X. brillo: emision propia (fichas, filos, LEDs)."""
    tipo = "vidrio" if vidrio else (tipo or "plastico")
    if tipo in ("polimero", "satinado", "ceramica", "brillante", "goma"): tipo = "plastico"      # un unico plastico
    S = SUPERFICIES[tipo]
    rug = S["rug"] if rugosidad is None else rugosidad
    nombre = f"AR {color}" + (f" {acento}" if acento else "") + (f" a{alfa:.2f}" if alfa < 1 else "") + \
             (f" e{brillo:g}" if brillo else "") + ("" if tipo == "plastico" else f" {tipo}") + (" ao" if ao else "") + \
             (f" r{rugosidad:g}" if rugosidad is not None else "") + (" liso" if liso else "")
    m = bpy.data.materials.get(nombre)
    if m: return m
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); b = N.new("ShaderNodeBsdfPrincipled")
    def pon(nombre_in, valor):
        if nombre_in in b.inputs: b.inputs[nombre_in].default_value = valor
    pon("Roughness", rug); pon("Specular IOR Level", S["spec"]); pon("Coat Weight", S["coat"]); pon("Coat Roughness", S["coat_rug"])
    pon("Subsurface Weight", S["sss"]); pon("Subsurface Scale", 0.004)
    pon("Transmission Weight", S["trans"]); pon("IOR", 1.49 if tipo == "acrilico" else 1.45)
    if S["sss"]: pon("Subsurface Radius", (1.0, 0.8, 0.65))
    if acento:
        geo = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep.inputs[0])
        arriba = N.new("ShaderNodeMapRange"); arriba.clamp = True
        arriba.inputs["From Min"].default_value = 0.55; arriba.inputs["From Max"].default_value = 0.75
        L.new(sep.outputs["Z"], arriba.inputs["Value"])
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
        mix.inputs["A"].default_value = (*_lineal(color), 1); mix.inputs["B"].default_value = (*_lineal(acento), 1)
        tinte = N.new("ShaderNodeMapRange"); tinte.clamp = True; tinte.inputs["To Min"].default_value = 0.08
        L.new(arriba.outputs["Result"], tinte.inputs["Value"])
        L.new(tinte.outputs["Result"], mix.inputs["Factor"]); L.new(mix.outputs["Result"], b.inputs["Base Color"])
    elif ao:                                # sombra de contacto: el color se oscurece donde algo se apoya (AO de Cycles)
        L.new(oclusion(N, L, _lineal(color), 0.06, 0.78), b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*_lineal(color), 1)
    if brillo:
        b.inputs["Emission Color"].default_value = (*_lineal(color), 1); b.inputs["Emission Strength"].default_value = brillo
    else:                                   # resalte: borde turquesa por Fresnel, con la propiedad de objeto 'resalte'
        res = N.new("ShaderNodeAttribute"); res.attribute_type = 'OBJECT'; res.attribute_name = "resalte"
        lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
        borde = N.new("ShaderNodeMath"); borde.operation = 'MULTIPLY_ADD'
        L.new(lw.outputs["Facing"], borde.inputs[0]); borde.inputs[1].default_value = 3.0; borde.inputs[2].default_value = 0.25
        fuerza = N.new("ShaderNodeMath"); fuerza.operation = 'MULTIPLY'
        L.new(res.outputs["Fac"], fuerza.inputs[0]); L.new(borde.outputs[0], fuerza.inputs[1])
        b.inputs["Emission Color"].default_value = (*_lineal("turquesa"), 1); L.new(fuerza.outputs[0], b.inputs["Emission Strength"])
    if alfa < 1: b.inputs["Alpha"].default_value = alfa
    tx = T.TEMA.get("textura")
    if tx and not liso and alfa >= 1 and tipo == "plastico":
        textura_plastico(N, L, b, tx, rug)
    L.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m

def oclusion(N, L, color, distancia, minimo):
    """Color multiplicado por la oclusion ambiental de Cycles (nodo AO): 'minimo' en los rincones, 1 al aire libre.
    Da la sombra de contacto blanda bajo cada pieza sin oscurecer la escena. Devuelve la salida de color."""
    ao = N.new("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.inputs["Distance"].default_value = distancia
    rango = N.new("ShaderNodeMapRange"); rango.inputs["To Min"].default_value = minimo
    L.new(ao.outputs["AO"], rango.inputs["Value"])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = (*color, 1)
    comb = N.new("ShaderNodeCombineColor"); L.new(rango.outputs["Result"], comb.inputs[0]); L.new(rango.outputs["Result"], comb.inputs[1])
    L.new(rango.outputs["Result"], comb.inputs[2]); L.new(comb.outputs[0], mix.inputs["B"])
    return mix.outputs["Result"]

def material_adorno_arcilla(nombre_gp):
    """Adornos y efectos en el diorama: el MISMO plastico que las piezas, solo cambia el color (sin emision)."""
    m = bpy.data.materials.get("ARm " + nombre_gp)
    if m: return m
    partes = nombre_gp.split(" "); alfa = 1.0
    if nombre_gp.startswith("T tinta"): color = "negro" if nombre_gp == "T tinta" else "gris_oscuro"
    elif partes[1] in ("plano", "trazo"): color = partes[2]; alfa = float(partes[3]) if len(partes) > 3 else 1.0
    else: color = partes[1]
    m = material_arcilla(color, alfa=alfa).copy(); m.name = "ARm " + nombre_gp
    return m

def redondear(ob, ancho=0.006, segmentos=4):
    """Esquinas redondeadas de plastico fabricado (Bevel por angulo, sin solapes, normales endurecidas: caras limpias)."""
    mod = ob.modifiers.new("Redondeo", 'BEVEL'); mod.width = ancho; mod.segments = segmentos
    mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(40); mod.use_clamp_overlap = True
    try: mod.harden_normals = True
    except (AttributeError, TypeError): pass
    return mod

def _redondear_perfil(pts, r, n=3):
    """Esquinas redondeadas (arco de n tramos y radio r) en un poligono 2D cerrado: perfiles de las cintas."""
    out = []
    for i, p in enumerate(pts):
        a, c = Vector(pts[i - 1]), Vector(pts[(i + 1) % len(pts)]); p = Vector(p)
        u, v = (a - p), (c - p); rr = min(r, u.length / 2.2, v.length / 2.2)
        if rr < 1e-5: out.append((p.x, p.y)); continue
        p0, p1 = p + u.normalized() * rr, p + v.normalized() * rr
        for k in range(n + 1):                          # Bezier cuadratica con control en la esquina
            t = k / n; q = p0 * (1 - t) ** 2 + p * 2 * t * (1 - t) + p1 * t * t; out.append((q.x, q.y))
    return out

def _remuestrear(pts, paso=0.01):
    """Puntos a distancias iguales por el poligono: las UV de una curva avanzan por punto, asi siguen la longitud."""
    out = [pts[0]]; resto = 0.0
    for a, b in zip(pts, pts[1:]):
        d = (b - a).length; t = paso - resto
        while t <= d:
            out.append(a.lerp(b, t / d)); t += paso
        resto = d - (t - paso)
    if (out[-1] - pts[-1]).length > 1e-6: out.append(pts[-1])
    return out

def _perfil(nombre, pts, col_):
    """Curva 2D cerrada para biselar por objeto: X es el lateral de la cinta e Y la altura (twist Z_UP)."""
    ob = bpy.data.objects.get(nombre)
    if ob: return ob
    cu = bpy.data.curves.new(nombre, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'NONE'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, (x, y) in enumerate(pts): sp.points[i].co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(nombre, cu); col_.objects.link(ob)       # sin bisel ni relleno: no se renderiza
    return ob

def material_banda(nombre, largo, paso=0.035, velocidad=0.22):
    """Banda de la cinta: grafito con lamas claras que avanzan del origen al destino (driver sobre el fotograma)."""
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); b = N.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.62
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.3
    uv = N.new("ShaderNodeUVMap"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv.outputs["UV"], sep.inputs[0])
    esc = N.new("ShaderNodeMath"); esc.operation = 'MULTIPLY'; esc.inputs[1].default_value = largo / paso
    L.new(sep.outputs["X"], esc.inputs[0])
    avance = N.new("ShaderNodeValue"); avance.name = "Avance"
    d = avance.outputs[0].driver_add("default_value").driver; d.type = 'SCRIPTED'
    d.expression = f"frame*{velocidad / paso / 24.0:.5f}"
    resta = N.new("ShaderNodeMath"); resta.operation = 'SUBTRACT'
    L.new(esc.outputs[0], resta.inputs[0]); L.new(avance.outputs[0], resta.inputs[1])
    fr = N.new("ShaderNodeMath"); fr.operation = 'FRACT'; L.new(resta.outputs[0], fr.inputs[0])
    lama = N.new("ShaderNodeMath"); lama.operation = 'LESS_THAN'; lama.inputs[1].default_value = 0.16
    L.new(fr.outputs[0], lama.inputs[0])
    mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (*_lineal("gris_oscuro"), 1); mix.inputs["B"].default_value = (*_lineal("gris"), 1)
    L.new(lama.outputs[0], mix.inputs["Factor"]); L.new(mix.outputs["Result"], b.inputs["Base Color"])
    L.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m

def cinta(nombre, camino, col_, rx=False):
    """Cinta transportadora por el camino (eje a la altura del tema): canal en U de arcilla gris claro, banda grafito con
    lamas que avanzan dentro del canal y patas hasta el suelo. Devuelve el canal (curva: la animacion la revela con
    bevel_factor_end); la banda (curva) y las patas (malla) son sus hijas."""
    c = T.TEMA.get("cinta") or dict(z=0.085, ancho=0.105, alto=0.03)
    W, H = c["ancho"], c["alto"]; t = 0.011; suelo_c = 0.011
    pts = _remuestrear(T.suave3([Vector(v) for v in camino]), 0.01)
    largo = sum((b - a).length for a, b in zip(pts, pts[1:]))
    col_p = bpy.data.collections.get("Perfiles") or bpy.data.collections.new("Perfiles")
    if col_p.name not in [ch.name for ch in bpy.context.scene.collection.children]: bpy.context.scene.collection.children.link(col_p)
    canal = _perfil("Perfil cinta canal", _redondear_perfil([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (W / 2 - t, H / 2),
                                           (W / 2 - t, -H / 2 + suelo_c), (-W / 2 + t, -H / 2 + suelo_c), (-W / 2 + t, H / 2),
                                           (-W / 2, H / 2)], 0.0035), col_p)
    banda = _perfil("Perfil cinta banda", [(-W / 2 + t + 0.002, -H / 2 + suelo_c), (W / 2 - t - 0.002, -H / 2 + suelo_c),
                                           (W / 2 - t - 0.002, -H / 2 + suelo_c + 0.006), (-W / 2 + t + 0.002, -H / 2 + suelo_c + 0.006)], col_p)
    def curva(nom, perfil, material):
        cu = bpy.data.curves.new(nom, 'CURVE'); cu.dimensions = '3D'; cu.bevel_mode = 'OBJECT'; cu.bevel_object = perfil
        cu.twist_mode = 'Z_UP'; cu.use_fill_caps = True; cu.bevel_factor_mapping_end = 'SPLINE'
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1)
        ob = bpy.data.objects.new(nom, cu); col_.objects.link(ob); cu.materials.append(material)
        return ob
    if rx:
        return curva(nombre, canal, material_arcilla("gris_claro", alfa=0.25))
    # canal de acrilico turquesa translucido (la banda se ve a traves), como los tubos de la referencia 1
    ob = curva(nombre, canal, material_arcilla(T.TEMA.get("manguera") or "turquesa", tipo="acrilico", rugosidad=0.16))
    hijo(curva(nombre + "_banda", banda, material_banda(f"AR banda {nombre}", largo)), ob)
    # patas cada ~0.24 m (no en los extremos, que entran en las peanas), con un pie redondo
    bm = bmesh.new(); z0 = pts[0].z - H / 2; acu = 0.0; prox = 0.12
    for a, b in zip(pts, pts[1:]):
        d = (b - a).length
        while prox <= acu + d and prox < largo - 0.1:
            q = a.lerp(b, (prox - acu) / max(d, 1e-6))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.008, radius2=0.008, depth=z0,
                                  matrix=Matrix.Translation((q.x, q.y, z0 / 2)))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.022, radius2=0.018, depth=0.006,
                                  matrix=Matrix.Translation((q.x, q.y, 0.003)))
            prox += 0.24
        acu += d
    if bm.verts:
        me = bpy.data.meshes.new(nombre + "_patas"); bm.to_mesh(me)
        for pl in me.polygons: pl.use_smooth = True
        me.materials.append(material_arcilla("gris_claro"))
        patas = bpy.data.objects.new(nombre + "_patas", me); col_.objects.link(patas); hijo(patas, ob)
    bm.free()
    return ob

def pieza_arcilla(p, col_, params, rx=False, col_neon=None):
    """Pieza del tema arcilla: malla con esquinas redondeadas; el color de la pieza va en la cara de arriba (las piezas
    pequenas y las de color claro, enteras). Las mangueras son cintas transportadoras; las peanas, losas blancas con un
    filo turquesa."""
    M = T.matriz_pieza(p); f = p["forma"]; c = p["color"]
    trans = p["material"] in ("transparente", "liquido")
    nombre = p["id"] + ("_rx" if rx else "")
    if f == "manguera":
        return cinta(nombre, p["camino"], col_neon or col_, rx=rx)
    if f == "biohazard":
        vista = T.dir_camara(params); dere = (-vista).cross(Vector((0, 0, 1))).normalized(); arr = dere.cross(-vista).normalized()
        cen = M @ Vector((0, 0, p["alto"] / 2))
        def pl(c0, x, y, k=0): return c0 + dere * x + arr * y + vista * (0.003 * k)
        pin = PincelMalla(nombre, vista); T.dibujar_biohazard(pin, pl, cen, p["alto"], c)
        return pin.objeto(col_)
    me = _malla(nombre, caras_pieza(p, M), suave_grados=85.0 if f == "cerebro" else 35.0)
    tam = max((p.get(k) or 0) for k in ("ancho", "fondo", "alto", "radio"))
    if rx: mat_ = material_arcilla(c if c not in CLAROS_ARCILLA else "cian", alfa=0.22, tipo="acrilico")
    elif trans: mat_ = material_arcilla(c if c not in CLAROS_ARCILLA else "cian", tipo="acrilico" if p["material"] == "transparente" else "vidrio")
    elif f == "peana": mat_ = material_arcilla("blanco_hueso", ao=True)                       # sombra de contacto
    elif c in CLAROS_ARCILLA or tam < 0.13: mat_ = material_arcilla(c)                       # el plastico, entero de su color
    else: mat_ = material_arcilla("blanco", acento=c)
    me.materials.append(mat_)
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    if not rx and not trans and f not in ("cerebro", "malla"): redondear(ob, 0.012 if f == "peana" else 0.006)
    if f == "peana" and not rx:                          # filo turquesa por encima del canto (como la referencia 1)
        perfil = T.perfil_redondeado(p); h = p["alto"]
        aro = [M @ Vector((x * 0.985, y * 0.985, h + 0.001)) for x, y in perfil]
        hijo(tubo_camino(p["id"] + "_filo", aro + aro[:1], 0.0042, material_arcilla("cian", tipo="acrilico", brillo=0.1), col_neon or col_), ob)
    return ob

def ficha_cubo(lado, color):
    """Ficha del flujo en una cinta: cubo redondeado que brilla (naranja los datos, turquesa las respuestas)."""
    nombre = f"AR ficha {color} {lado:.3f}"
    me = bpy.data.meshes.get(nombre)
    if me: return me
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=lado)
    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=lado * 0.18, segments=3, affect='EDGES')
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for pl in me.polygons: pl.use_smooth = True
    me.materials.append(material_arcilla(color, brillo=2.2, tipo="acrilico", rugosidad=0.12))
    return me

def rotulo(nombre, texto, pos, altura, col_, color="gris", rot_z=0.0):
    """Rotulo numerado ('01.') tumbado sobre una peana, como malla (texto convertido): sin Grease Pencil."""
    fnt = bpy.data.fonts.get("AR rotulos")
    if fnt is None:
        ruta = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
        fnt = bpy.data.fonts.load(ruta); fnt.name = "AR rotulos"
    cu = bpy.data.curves.new(nombre, 'FONT'); cu.body = texto; cu.font = fnt; cu.size = altura
    cu.extrude = 0.0012; cu.align_x = 'LEFT'; cu.align_y = 'BOTTOM'
    tmp = bpy.data.objects.new(nombre + "_tmp", cu); col_.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    me.materials.clear(); me.materials.append(material_arcilla(color))
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    ob.location = pos; ob.rotation_euler = (0, 0, rot_z)
    return ob

def tarjeta(nombre, tipo, centro, vista, ancho, col_):
    """Tarjeta de interfaz flotante (referencias 1 y 3), toda malla y de cara a la camara: 'mensaje' (naranja con un
    circulo y dos lineas blancas), 'grafica' (blanca con tres barras turquesa) o 'estado' (turquesa con un circulo y una
    linea). Devuelve el objeto (centrado en 'centro')."""
    n = Vector((vista.x, vista.y, 0)).normalized(); r = (-vista).cross(Vector((0, 0, 1))).normalized(); up = Vector((0, 0, 1))
    w, h, e = ancho, ancho * 0.62, ancho * 0.09
    bm = bmesh.new(); mats = []
    def caja(cx, cy, bw, bh, prof, dz, mat):
        if mat not in mats: mats.append(mat)
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co = (centro + r * (cx + v.co.x * bw) + up * (cy + v.co.z * bh) + n * (dz + v.co.y * prof))
        for fc in {fc for v in res["verts"] for fc in v.link_faces}: fc.material_index = mats.index(mat)
    fondo = {"mensaje": "naranja", "grafica": "blanco", "estado": "turquesa"}[tipo]
    tinta = "blanco" if tipo != "grafica" else "turquesa"
    caja(0, 0, w, h, e, 0, fondo)
    if tipo == "grafica":
        for i, hb in enumerate((0.35, 0.6, 0.85)):
            bh = h * 0.6 * hb; caja(-w * 0.25 + i * w * 0.25, -h * 0.3 + bh / 2, w * 0.16, bh, e * 0.5, e * 0.6, tinta)
        caja(0, -h * 0.32, w * 0.8, h * 0.03, e * 0.5, e * 0.6, "gris")
    else:
        caja(-w * 0.3, 0, h * 0.42, h * 0.42, e * 0.5, e * 0.6, tinta)
        for j, lw in enumerate((0.42, 0.3) if tipo == "mensaje" else (0.42,)):
            caja(w * 0.12 - (0.42 - lw) * w / 2, (h * 0.12 if tipo == "mensaje" else 0) - j * h * 0.24, w * lw, h * 0.1, e * 0.5, e * 0.6, tinta)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    for k, mat in enumerate(mats):                    # el panel (el primero) es acrilico esmerilado; el contenido, polimero
        me.materials.append(material_arcilla(mat, tipo="acrilico", rugosidad=0.35) if k == 0 else material_arcilla(mat))
    ob = bpy.data.objects.new(nombre, me); col_.objects.link(ob)
    redondear(ob, min(0.006, e * 0.45), 2)
    ob["comic_tarjeta"] = 1
    ob.visible_shadow = False             # flota: su sombra en la plataforma se leia como una mancha
    return ob

PLATAFORMA = dict(margen=0.3, radio=0.2, alto=0.07, bisel=0.016)   # m: la base gris del diorama bajo el workflow

def _material_ao(nombre, color, tipo, distancia, minimo):
    """Copia de un material del diorama con la oclusion ambiental en el color (sombra de contacto)."""
    m = material_arcilla(color, tipo=tipo, liso=True).copy(); m.name = nombre
    N = m.node_tree.nodes; b = N["Principled BSDF"]
    if "Subsurface Weight" in b.inputs: b.inputs["Subsurface Weight"].default_value = 0.0
    m.node_tree.links.new(oclusion(N, m.node_tree.links, _lineal(color), distancia, minimo), b.inputs["Base Color"])
    return m

def plataforma(col_, caja):
    """Base del diorama: losa gris claro neutro con las esquinas y el canto redondeados, con la cara de arriba en z=0
    (las piezas no se mueven) y el canto hacia abajo hasta el suelo blanco. Cubre el workflow con un margen."""
    x0, y0, x1, y1 = caja; m_, R, h = PLATAFORMA["margen"], PLATAFORMA["radio"], PLATAFORMA["alto"]
    x0, y0, x1, y1 = x0 - m_, y0 - m_, x1 + m_, y1 + m_
    perfil = []
    for cx, cy, a0 in ((x1 - R, y0 + R, -90), (x1 - R, y1 - R, 0), (x0 + R, y1 - R, 90), (x0 + R, y0 + R, 180)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8); perfil.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    bm = bmesh.new()
    arriba = bm.faces.new([bm.verts.new((x, y, 0.0)) for x, y in perfil])
    r = bmesh.ops.extrude_face_region(bm, geom=[arriba])
    bmesh.ops.translate(bm, verts=[v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)], vec=(0, 0, -h))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Plataforma"); bm.to_mesh(me); bm.free()
    me.materials.append(_material_ao("AR plataforma", "plataforma", "satinado", 0.08, 0.68))
    ob = bpy.data.objects.new("Plataforma", me); col_.objects.link(ob)
    redondear(ob, PLATAFORMA["bisel"], 5)
    return ob

def suelo_claro(col_, centro, tam, caja=None):
    """Suelo de estudio blanco puro (sin tinte), con oclusion para la sombra de contacto. Con 'caja' (x0, y0, x1, y1 del
    workflow) pone debajo la plataforma gris del diorama y baja el suelo a la base de su canto."""
    W = max(14.0, tam * 4); z = -PLATAFORMA["alto"] if caja else 0.0
    bm = bmesh.new()
    vs = [bm.verts.new((centro.x + x, centro.y + y, z)) for x, y in ((-W, -W), (W, -W), (W, W), (-W, W))]
    bm.faces.new(vs); me = bpy.data.meshes.new("Suelo"); bm.to_mesh(me); bm.free()
    me.materials.append(_material_ao("AR suelo", "suelo_estudio", "polimero", 0.25, 0.6))
    ob = bpy.data.objects.new("Suelo", me); col_.objects.link(ob)
    if caja: plataforma(col_, caja)
    return ob

def luces_estudio(centro, tam, col_):
    """Estudio para que la sombra se vea desde la camara: la principal va DETRAS a la derecha (enfrente de la camara,
    girada hacia la derecha del cuadro) a ~68 grados (sombras cortas), de tamano medio (sombra suave pero con la forma reconocible), asi
    la sombra de cada pieza viene hacia el espectador en diagonal. Un relleno grande y suave desde el lado de la camara
    aclara las caras que la miran (mas oscuras que las de arriba: volumen) y una cenital tenue levanta el conjunto."""
    k = max(1.0, tam / 3.0)
    vista = T.dir_camara({})
    cam = Vector((vista.x, vista.y, 0)).normalized()                  # hacia la camara, en el suelo
    dere = (-vista).cross(Vector((0, 0, 1))); dere = Vector((dere.x, dere.y, 0)).normalized()
    def area(nombre, color, energia, direccion, elev, dist, tamano):
        d = bpy.data.lights.new(nombre, 'AREA'); d.color = color; d.energy = energia * k * k; d.size = tamano * k
        ob = bpy.data.objects.new(nombre, d); col_.objects.link(ob)
        e = math.radians(elev); ob.location = centro + (direccion.normalized() * math.cos(e) + Vector((0, 0, math.sin(e)))) * dist * k
        ob.rotation_euler = (centro - ob.location).to_track_quat('-Z', 'Y').to_euler()
        return ob
    area("Luz principal", (1.0, 0.98, 0.96), 1700, -cam + dere * 0.55, 68, 7.4, 1.6)     # alta: sombras cortas
    area("Relleno", (1.0, 1.0, 1.0), 320, cam, 28, 7.0, 6.0)
    area("Cenital", (1.0, 1.0, 1.0), 140, Vector((0.001, 0, 0)), 89, 7.0, 9.0)

def render_arcilla(sc, params):
    """Cycles en la GPU: iluminacion global con rebotes suficientes para el acrilico y la sombra de contacto, 96 muestras
    adaptativas con denoise, filtro de 1,5 px; 'Khronos PBR Neutral' (la transformada de visualizacion de producto:
    conserva los colores base y no quema los blancos; con AgX los acentos de las caras iluminadas salian en pastel);
    mundo claro uniforme; bloom solo para lo que emite (fichas, chispa)."""
    import gp_base as GB
    sc.render.engine = 'CYCLES'; GB.gpu_cycles(sc)
    cy = sc.cycles; cy.samples = 96; cy.adaptive_threshold = 0.02; cy.use_denoising = True; cy.use_adaptive_sampling = True
    cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 4; cy.transmission_bounces = 8
    cy.transparent_max_bounces = 16; cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = 5.0; cy.filter_width = 1.5
    try: sc.view_settings.view_transform = 'Khronos PBR Neutral'; sc.view_settings.look = 'None'
    except TypeError: sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -0.3
    if not sc.world: sc.world = bpy.data.worlds.new("Arcilla")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[0].default_value = (*_lineal("suelo_estudio"), 1); bg.inputs[1].default_value = 0.35
    sc["grano"] = 1.0                      # fuerza de la textura (la animacion la baja en los planos de detalle)
    brillo(sc, T.TEMA.get("bloom") or "arcilla")
