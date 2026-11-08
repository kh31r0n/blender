# Genera Edificios_GN.blend: grupo de Geometry Nodes "Edificio LEGO" que levanta edificios con piezas LDraw
# al estilo de la torre-hotel de Nitro.blend (pisos de 64 mm, ventanas 60592, esquinas 2357, alero negro con pinaculos).
# Unidades: 1 unidad de Blender = 10 mm, igual que Nitro.blend y las minifiguras de Mecabricks (1 LDU = 0.04).
# Uso: blender -b -P ~/blender/buildings/scripts/edificios_gn.py
#      (lee piezas de ~/ldraw y materiales de Nitro.blend; Nitro.blend no se modifica)
import bpy, math, addon_utils
from mathutils import Matrix, Vector

NITRO = "/home/kheiron/blender/buildings/Nitro.blend"
LDRAW = "/home/kheiron/ldraw"
OUT = "/home/kheiron/blender/buildings/Edificios_GN_marquesina_v2.blend"

LDU = 0.04                  # unidades de Blender por LDU
S, P, B = 0.8, 0.32, 0.96   # stud, placa, ladrillo
F = 6 * B + 2 * P           # piso: ladrillo + 2 ventanas 1x2x2 + ladrillo + 2 placas = 6.4 (64 mm)
PI2 = math.pi / 2

# ---------- piezas ----------
# Cada prototipo = (pieza LDraw, rol de material). Los grupos "por largo" van seguidos: indice = base + largo - 1.
LARGOS = dict(
    ladrillo=["3005", "3004", "3622", "3010"],     # ladrillos 1x1 .. 1x4
    placa=["3024", "3023b", "3623", "3710"],       # placas 1x1 .. 1x4
    placa2=["3023b", "3022", "3021", "3020"],      # placas 2x1 .. 2x4 (la 1x2 se gira 90 grados)
    teja=["3070b", "3069b", "63864", "2431"],      # tiles 1x1 .. 1x4
    pend=["4286", "3298", "4161", "3297"],         # pendientes 33 grados 3x1 .. 3x4
    relleno=["3070b", "3069b", "3068b"],           # tiles 1x1, 1x2, 2x2 para la azotea
)
PROTOS, IDX = [], {}
def proto(clave, pids, roles):
    IDX[clave] = len(PROTOS)
    pids = pids if isinstance(pids, list) else [pids]
    roles = roles if isinstance(roles, list) else [roles] * len(pids)
    PROTOS.extend(zip(pids, roles))
proto("ladrillo", LARGOS["ladrillo"], "Pared")
proto("esquina", "2357", "Pared")
proto("pilar", "14716", "Pared")               # 1x1x3: pilar entre ventanas (+ un 1x1 encima)
proto("ciega", "3245c", "Pared")               # 1x2x2: hueco de ventana tapiado
proto("placa", LARGOS["placa"], "Molduras")
proto("esquina_placa", "2420", "Molduras")
proto("teja", LARGOS["teja"], "Molduras")
proto("esquina_teja", "14719", "Molduras")
proto("alero", LARGOS["placa2"], "Tejado")
proto("cornisa", LARGOS["placa2"], "Molduras")
proto("pend", LARGOS["pend"], "Tejado")
proto("pend_esq", "3675", "Tejado")
proto("relleno", LARGOS["relleno"], "Azotea")
proto("marco", "60592", "Marcos")
proto("vidrio", ["60601", "60601"], ["Vidrio", "Vidrio encendido"])    # encendido = indice + 1
proto("marco3", "60593", "Marcos")
proto("vidrio3", ["60602", "60602"], ["Vidrio", "Vidrio encendido"])
proto("puerta_marco", "60596", "Marcos")
proto("puerta", "60616a", "Puerta")
# marquesina de la entrada del hotel
# marquesina de la entrada del hotel (como la del porche de Nitro: 3037/3045, placa 3666, verja 3633, 59900 + 78258)
TEJ2 = ("Tejado", "Pendientes marquesina")                  # caras de pendiente (indice de material 1) con grano
proto("toldo_base", ["3024", "3023b", "3022"], "Tejado")   # placas 1x1, 1x2, 2x2 (mismo orden que relleno)
proto("toldo_placa", LARGOS["placa"], "Tejado")            # cumbrera 1xN; la 1x1 tambien es base de pinaculo
proto("toldo_pend", ["3040b", "3039", "3038", "3037"], TEJ2)  # pendientes 45 grados 2x1 .. 2x4
proto("toldo_pend_esq", "3045", TEJ2)                      # esquina 45 doble convexa (cuatro aguas)
proto("toldo_cresta", ["3005", "3004", "3003"], "Tejado")  # cresta de ladrillos 1x1, 1x2, 2x2 con studs vistos
proto("mensula", ["3665a", "6141"], "Tejado")               # mensula: pendiente invertida + placa redonda colgada
proto("saltador", "3794b", "Tejado")                        # jumper: centra un pinaculo entre dos studs
proto("pinaculo", ["3062b", "59900", "78258"], "Detalles")  # base redonda + cono + barra con tope (Nitro)
BARRA = 14 * LDU                                            # la barra 78258 entra 10 LDU en el cono 59900
proto("verja", "3633", "Detalles")
proto("pin", ["3062b", "59900", "4589"], "Detalles")                   # pinaculo: ladrillo redondo + 2 conos
proto("maceta", "3023b", "Plantas")
proto("flor", "24866", "Flores")

# Desplazamientos especiales (LDU): el vidrio y la puerta comparten origen con su marco
ESPECIAL = {"60601": (48, 0), "60602": (72, 0), "60616a": (144, -32)}

# ---------- materiales (Mecabricks) ----------
NOMBRES = {1: "White", 5: "Tan", 6: "Light Green", 18: "Nougat", 21: "Bright Red", 23: "Bright Blue",
           24: "Bright Yellow", 26: "Black", 28: "Dark Green", 37: "Bright Green", 38: "Dark Orange",
           40: "Trans Clear", 41: "Trans Red", 42: "Trans Light Blue", 44: "Trans Yellow", 102: "Medium Blue",
           106: "Bright Orange", 111: "Trans Brown", 119: "Lime", 124: "Magenta", 135: "Sand Blue",
           138: "Dark Tan", 140: "Dark Blue", 141: "Earth Green", 151: "Sand Green", 153: "Sand Red",
           154: "Dark Red", 191: "Flame Yellowish Orange", 192: "Reddish Brown", 194: "Light Bluish Grey",
           199: "Dark Bluish Grey", 212: "Light Royal Blue", 216: "Rust", 221: "Bright Purple",
           222: "Light Purple", 226: "Cool Yellow", 268: "Medium Lilac", 283: "Light Nougat", 308: "Dark Brown",
           312: "Medium Nougat", 321: "Dark Azure", 322: "Medium Azure", 323: "Light Aqua", 325: "Lavender",
           326: "Yellowish Green", 330: "Olive Green", 353: "Coral", 375: "Trans Smoke"}
ROLES = {  # rol: id de color por defecto
    "Pared": 1, "Marcos": 1, "Vidrio": 375, "Vidrio encendido": None, "Molduras": 1, "Tejado": 26,
    "Azotea": 199, "Detalles": 26, "Puerta": 192, "Plantas": 28, "Flores": 21, "Pendientes marquesina": "grano"}

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_scene_importldraw")

def cargar_paleta():
    with bpy.data.libraries.load(NITRO, link=False) as (src, dst):
        elegidos = {}
        for nm in src.materials:       # un material por color (mb:o:<objeto>:<color>)
            p = nm.split(":")
            if len(p) == 4 and p[0] == "mb" and p[3].isdigit():
                elegidos.setdefault(int(p[3]), nm)
        dst.materials = [elegidos[c] for c in sorted(elegidos)]
    pal = {}
    for c in sorted(elegidos):
        m = bpy.data.materials[elegidos[c]]
        m.name = "LEGO %d %s" % (c, NOMBRES.get(c, "")) if c in NOMBRES else "LEGO %d" % c
        m.name = m.name.strip()
        m.use_fake_user = True
        pal[c] = m
    # vidrio encendido: Trans Yellow con emision
    m = pal[44].copy(); m.name = "LEGO Vidrio encendido"; m.use_fake_user = True
    base = next(n for n in m.node_tree.nodes if n.type == 'GROUP' and n.node_tree.name == "mb_base_transparent")
    base.inputs["Color"].default_value = (1.0, 0.72, 0.32, 1.0)
    base.inputs["Emission"].default_value = 1.0
    # negro con grano para las caras inclinadas (en Mecabricks las pendientes llevan textura rugosa)
    gr = pal[26].copy(); gr.name = "LEGO 26 Black pendiente"; gr.use_fake_user = True
    nt = gr.node_tree
    base = next(n for n in nt.nodes if n.type == 'GROUP' and n.node_tree.name.startswith("mb_base"))
    normal = base.inputs["Normal"].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs["Scale"].default_value = 35.0; nz.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.01
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(normal, bump.inputs["Normal"])
    nt.links.new(bump.outputs["Normal"], base.inputs["Normal"])
    rampa = nt.nodes.new('ShaderNodeValToRGB')
    rampa.color_ramp.elements[0].position = 0.5; rampa.color_ramp.elements[0].color = (0.005, 0.005, 0.005, 1)
    rampa.color_ramp.elements[1].position = 0.62; rampa.color_ramp.elements[1].color = (0.09, 0.09, 0.095, 1)
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs["Scale"].default_value = 70.0
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"]); nt.links.new(nz2.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], base.inputs["Color"])
    return pal, m, gr

PAL, MAT_LUZ, MAT_GRANO = cargar_paleta()
MAT = {r: (MAT_LUZ if c is None else MAT_GRANO if c == "grano" else PAL[c]) for r, c in ROLES.items()}

# ---------- importacion LDraw ----------
coll_piezas = bpy.data.collections.new("Piezas LDraw")
bpy.context.scene.collection.children.link(coll_piezas)
OBJ = {}
def importar(pid):
    if pid in OBJ: return OBJ[pid]
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.importldraw(filepath=f"{LDRAW}/parts/{pid}.dat", ldrawPath=LDRAW, positionOnGround=False,
                                     bevelEdges=False, addEnvironment=False, positionCamera=False, importCameras=False,
                                     useLogoStuds=False, look='normal', resPrims='Standard', addGaps=False)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    src = next(o for o in nuevos if o.type == 'MESH')
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))           # aplica el Edge Split
    me.transform(Matrix.Scale(LDU / 0.0004, 4) @ src.matrix_world)        # 1 LDU = 0.04, Z arriba, frente = -Y
    zs, xs = ESPECIAL.get(pid, (None, 0))
    dz = zs * LDU if zs is not None else -min(v.co.z for v in me.vertices)  # origen en la base de la pieza
    me.transform(Matrix.Translation((xs * LDU, 0, dz)))
    # indice de material 1 = caras con textura de pendiente del importador (Material_*_s); el resto 0
    pend = [bool(me.materials) and me.materials[p.material_index].name.endswith("_s") for p in me.polygons]
    me.materials.clear()
    me.polygons.foreach_set("material_index", [int(s) for s in pend])
    me.name = "LD_" + pid
    ob = bpy.data.objects.new("LD_" + pid, me)
    coll_piezas.objects.link(ob)
    for o in nuevos: bpy.data.objects.remove(o)
    OBJ[pid] = ob
    return ob

for pid, _ in PROTOS: importar(pid)
for c in list(bpy.data.collections):
    if c != coll_piezas and not c.objects and not c.children: bpy.data.collections.remove(c)
coll_piezas.hide_viewport = True
coll_piezas.hide_render = True

# ---------- ayudante de nodos ----------
class G:
    def __init__(self, name):
        self.t = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        self.gi = self.t.nodes.new('NodeGroupInput')
        self.go = self.t.nodes.new('NodeGroupOutput')
    def inp(self, name, typ, default=None, lo=None, hi=None, parent=None, subtype=None):
        s = self.t.interface.new_socket(name, in_out='INPUT', socket_type=typ, parent=parent)
        if subtype: s.subtype = subtype
        if default is not None: s.default_value = default
        if lo is not None: s.min_value = lo
        if hi is not None: s.max_value = hi
        return self.gi.outputs[s.identifier]
    def out(self, name, typ):
        s = self.t.interface.new_socket(name, in_out='OUTPUT', socket_type=typ)
        return self.go.inputs[s.identifier]
    def n(self, idname, **kw):
        node = self.t.nodes.new(idname)
        for k, v in kw.items(): setattr(node, k, v)
        return node
    def L(self, a, b):
        if isinstance(a, bpy.types.NodeSocket): self.t.links.new(a, b)
        elif a is not None: b.default_value = a
    # matematicas en float (enteros exactos; logica con 0/1)
    def m(self, op, a, b=0.0, c=0.0):
        node = self.n('ShaderNodeMath', operation=op)
        for s, v in zip(node.inputs, (a, b, c)): self.L(v, s)
        return node.outputs[0]
    def add(self, a, b): return self.m('ADD', a, b)
    def sub(self, a, b): return self.m('SUBTRACT', a, b)
    def mul(self, a, b): return self.m('MULTIPLY', a, b)
    def div(self, a, b): return self.m('DIVIDE', a, b)
    def floor(self, a): return self.m('FLOOR', a)
    def ceil(self, a): return self.m('CEIL', a)
    def mod(self, a, b): return self.m('FLOORED_MODULO', a, b)
    def min(self, a, b): return self.m('MINIMUM', a, b)
    def max(self, a, b): return self.m('MAXIMUM', a, b)
    def lt(self, a, b): return self.m('LESS_THAN', a, b)
    def gt(self, a, b): return self.m('GREATER_THAN', a, b)
    def ge(self, a, b): return self.m('GREATER_THAN', a, self.sub(b, 0.5) if isinstance(b, bpy.types.NodeSocket) else b - 0.5)
    def eq(self, a, b): return self.m('COMPARE', a, b, 0.01)
    def no(self, a): return self.sub(1.0, a)
    def sel(self, c, a, b): return self.add(b, self.mul(c, self.sub(a, b)))   # c ? a : b
    def vec(self, x, y, z):
        node = self.n('ShaderNodeCombineXYZ')
        for s, v in zip(node.inputs, (x, y, z)): self.L(v, s)
        return node.outputs[0]
    def attr(self, name, dtype='FLOAT'):
        node = self.n('GeometryNodeInputNamedAttribute', data_type=dtype)
        node.inputs["Name"].default_value = name
        return node.outputs["Attribute"]
    def store(self, geo, name, val, dtype):
        node = self.n('GeometryNodeStoreNamedAttribute', data_type=dtype, domain='POINT')
        self.L(geo, node.inputs["Geometry"]); node.inputs["Name"].default_value = name; self.L(val, node.inputs["Value"])
        return node.outputs[0]
    def index(self): return self.n('GeometryNodeInputIndex').outputs[0]
    def points(self, count):
        node = self.n('GeometryNodePoints'); self.L(count, node.inputs["Count"]); return node.outputs[0]
    def rand(self, ident, seed):
        node = self.n('FunctionNodeRandomValue', data_type='FLOAT')
        self.L(ident, node.inputs["ID"]); self.L(seed, node.inputs["Seed"])
        return node.outputs["Value"]
    def join(self, *geos):
        node = self.n('GeometryNodeJoinGeometry')
        for gg in geos: self.L(gg, node.inputs[0])
        return node.outputs[0]
    def call(self, group, *outs, **ins):
        node = self.n('GeometryNodeGroup'); node.node_tree = group.t
        for k, v in ins.items(): self.L(v, node.inputs[k])
        return node.outputs[0]

# ---------- subgrupos ----------
# Convencion: cada punto lleva la posicion (u, v, z) en el marco de su fachada e (0 frente, 1 derecha, 2 fondo,
# 3 izquierda). u = studs a lo largo de la fachada desde su esquina izquierda vista desde fuera, v = studs hacia
# dentro (v < 0 sobresale), z en unidades de Blender. "Colocar" lo pasa a coordenadas del edificio.

def g_emitir():
    g = G("LB Emitir")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    sel = g.inp("Seleccion", 'NodeSocketBool', True)
    pi = g.inp("PI", 'NodeSocketInt'); u = g.inp("U", 'NodeSocketFloat'); v = g.inp("V", 'NodeSocketFloat')
    z = g.inp("Z", 'NodeSocketFloat'); rz = g.inp("RZ", 'NodeSocketFloat')
    tipo = g.inp("Tipo", 'NodeSocketInt'); vid = g.inp("VID", 'NodeSocketInt')
    out = g.out("Geometry", 'NodeSocketGeometry')
    no = g.n('FunctionNodeBooleanMath', operation='NOT'); g.L(sel, no.inputs[0])
    d = g.n('GeometryNodeDeleteGeometry', domain='POINT'); g.L(geo, d.inputs[0]); g.L(no.outputs[0], d.inputs[1])
    sp = g.n('GeometryNodeSetPosition'); g.L(d.outputs[0], sp.inputs["Geometry"]); g.L(g.vec(u, v, z), sp.inputs["Position"])
    x = sp.outputs[0]
    for name, val, dt in (("pi", pi, 'INT'), ("rz", rz, 'FLOAT'), ("tipo", tipo, 'INT'), ("vid", vid, 'INT')):
        x = g.store(x, name, val, dt)
    g.L(x, out)
    return g
EMITIR = g_emitir()
def emit(g, geo, sel, pi, u, v, z, rz=0.0, tipo=0, vid=0):
    return g.call(EMITIR, Geometry=geo, Seleccion=sel, PI=pi, U=u, V=v, Z=z, RZ=rz, Tipo=tipo, VID=vid)

def g_celdas():
    # Un punto por stud del perimetro: fachada e, celda i y largo L de la fachada (= lado + Delta)
    g = G("LB Celdas")
    W = g.inp("Ancho", 'NodeSocketInt', 16); D = g.inp("Fondo", 'NodeSocketInt', 12); dL = g.inp("Delta", 'NodeSocketInt', -4)
    out = g.out("Geometry", 'NodeSocketGeometry')
    Lx = g.max(g.add(W, dL), 0); Ly = g.max(g.add(D, dL), 0)
    pts = g.points(g.mul(g.add(Lx, Ly), 2))
    i0 = g.index()
    g0 = g.ge(i0, Lx); g1 = g.ge(i0, g.add(Lx, Ly)); g2 = g.ge(i0, g.add(g.mul(Lx, 2), Ly))
    e = g.add(g.add(g0, g1), g2)
    i = g.sub(g.sub(g.sub(i0, g.mul(g0, Lx)), g.mul(g1, Ly)), g.mul(g2, Lx))
    L = g.add(Lx, g.mul(g.mod(e, 2), g.sub(Ly, Lx)))
    x = g.store(pts, "e", e, 'INT'); x = g.store(x, "i", i, 'INT'); x = g.store(x, "L", L, 'INT')
    g.L(x, out)
    return g
CELDAS = g_celdas()

def g_tramo():
    # Reparte cada fachada en piezas de largo 1..4 (aparejo con Desfase); en la fachada 0 deja un Hueco centrado
    g = G("LB Tramo")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    U0 = g.inp("U0", 'NodeSocketFloat', 2.0); V = g.inp("V", 'NodeSocketFloat', 0.5); Z = g.inp("Z", 'NodeSocketFloat')
    O = g.inp("Desfase", 'NodeSocketInt'); PIb = g.inp("PI base", 'NodeSocketInt'); H = g.inp("Hueco", 'NodeSocketInt')
    Rz1 = g.inp("RZ largo 1", 'NodeSocketFloat')
    out = g.out("Geometry", 'NodeSocketGeometry')
    e, i, L = g.attr("e"), g.attr("i"), g.attr("L")
    gw = g.mul(g.eq(e, 0), H)
    gs = g.floor(g.div(g.sub(L, gw), 2))
    has = g.gt(gw, 0.5)
    en_hueco = g.mul(g.ge(i, gs), g.lt(i, g.add(gs, gw)))
    seg0 = g.mul(g.mul(has, g.ge(i, g.add(gs, gw))), g.add(gs, gw))
    segL = g.sel(has, g.sel(g.lt(i, gs), gs, g.sub(g.sub(L, gs), gw)), L)
    li = g.sub(i, seg0)
    t = g.add(li, O)
    inicio = g.max(g.eq(li, 0), g.eq(g.mod(t, 4), 0))
    sig = g.sub(g.mul(g.add(g.floor(g.div(t, 4)), 1), 4), O)
    ln = g.sub(g.min(sig, segL), li)
    keep = g.mul(inicio, g.no(en_hueco))
    u = g.add(g.add(U0, i), g.div(ln, 2))
    g.L(emit(g, geo, keep, g.add(PIb, g.sub(ln, 1)), u, V, Z, g.mul(g.eq(ln, 1), Rz1)), out)
    return g
TRAMO = g_tramo()

def g_ventanas():
    # Zona de ventanas (filas 1-4 del piso): ventanas de 2 studs separadas por pilares de 1 stud, centradas;
    # columnas ciegas simetricas segun la semilla; puerta(s) centrada(s) en la fachada 0.
    g = G("LB Ventanas")
    geo = g.inp("Geometry", 'NodeSocketGeometry'); H = g.inp("Hueco", 'NodeSocketInt')
    esc = g.inp("Escaparate", 'NodeSocketInt'); seed = g.inp("Semilla", 'NodeSocketInt')
    pc = g.inp("Ciegas", 'NodeSocketFloat')
    out = g.out("Geometry", 'NodeSocketGeometry')
    e, i, R = g.attr("e"), g.attr("i"), g.attr("L")
    n = g.floor(g.div(g.sub(R, 1), 3))
    mL = g.floor(g.div(g.add(g.sub(R, g.mul(n, 3)), 1), 2))
    j = g.sub(i, mL)
    en_bloque = g.mul(g.ge(j, 0), g.lt(j, g.sub(g.mul(n, 3), 1)))
    k = g.mod(j, 3)
    col = g.floor(g.div(j, 3))
    col_sim = g.min(col, g.sub(g.sub(n, 1), col))
    ciega = g.lt(g.rand(g.add(g.mul(g.mod(e, 2), 97), col_sim), seed), pc)
    gw = g.mul(g.eq(e, 0), H)
    gs = g.floor(g.div(g.sub(R, gw), 2))
    def en_puerta(x): return g.mul(g.ge(x, gs), g.lt(x, g.add(gs, gw)))
    iL = g.sub(i, g.eq(k, 1))
    bloqueada = g.max(en_puerta(iL), en_puerta(g.add(iL, 1)))
    puerta = en_puerta(i)
    celda_v = g.mul(g.mul(en_bloque, g.lt(k, 1.5)), g.no(bloqueada))
    izq = g.mul(celda_v, g.eq(k, 0))
    vent = g.mul(izq, g.no(ciega)); ciega_izq = g.mul(izq, ciega)
    maciza = g.mul(g.no(puerta), g.no(celda_v))
    normal = g.no(esc)
    uc = g.add(i, 2.5); u2 = g.add(i, 3.0)
    vid = g.add(g.mul(e, 1000), i)
    I = IDX
    partes = [
        emit(g, geo, maciza, I["pilar"], uc, 0.5, B),
        emit(g, geo, maciza, I["ladrillo"], uc, 0.5, 4 * B),
        emit(g, geo, g.mul(vent, normal), I["marco"], u2, 0.5, B),
        emit(g, geo, g.mul(vent, normal), I["marco"], u2, 0.5, 3 * B),
        emit(g, geo, g.mul(vent, normal), I["vidrio"], u2, 0.5, B, tipo=1, vid=vid),
        emit(g, geo, g.mul(vent, normal), I["vidrio"], u2, 0.5, 3 * B, tipo=1, vid=vid),
        emit(g, geo, g.mul(vent, normal), I["maceta"], u2, -0.5, B - P, tipo=2, vid=vid),
        emit(g, geo, g.mul(vent, normal), I["flor"], uc, -0.5, B, tipo=2, vid=vid),
        emit(g, geo, g.mul(vent, normal), I["flor"], g.add(uc, 1.0), -0.5, B, tipo=2, vid=vid),
        emit(g, geo, g.mul(vent, esc), I["marco3"], u2, 0.5, B),
        emit(g, geo, g.mul(vent, esc), I["vidrio3"], u2, 0.5, B, tipo=1, vid=vid),
        emit(g, geo, g.mul(vent, esc), I["ladrillo"] + 1, u2, 0.5, 4 * B),
        emit(g, geo, ciega_izq, I["ciega"], u2, 0.5, B),
        emit(g, geo, ciega_izq, I["ciega"], u2, 0.5, 3 * B),
    ]
    # puertas: marco 1x4x6 + hoja; con hueco 8 van dos, la segunda girada 180 (bisagra a la derecha)
    segunda = g.mul(g.eq(gw, 8), g.eq(i, g.add(gs, 4)))
    ini = g.mul(g.gt(gw, 0.5), g.max(g.eq(i, gs), segunda))
    up = g.add(i, 4.0)
    partes += [emit(g, geo, ini, I["puerta_marco"], up, 0.5, 0.0),
               emit(g, geo, ini, I["puerta"], up, 0.5, 0.0, g.mul(segunda, math.pi))]
    g.L(g.join(*partes), out)
    return g
VENTANAS = g_ventanas()

def g_esquinas():
    # Una pieza en cada esquina (al inicio de cada fachada)
    g = G("LB Esquinas")
    PIc = g.inp("PI", 'NodeSocketInt'); U = g.inp("U", 'NodeSocketFloat', 0.5); V = g.inp("V", 'NodeSocketFloat', 0.5)
    Z = g.inp("Z", 'NodeSocketFloat'); RZ = g.inp("RZ", 'NodeSocketFloat')
    out = g.out("Geometry", 'NodeSocketGeometry')
    x = g.store(g.points(4), "e", g.index(), 'INT')
    g.L(emit(g, x, True, PIc, U, V, Z, RZ), out)
    return g
ESQUINAS = g_esquinas()

def g_relleno():
    # Rectangulo de A x B studs (desde X0, Y0 en el marco de la fachada 0) con tiles 2x2, 1x2 y 1x1
    g = G("LB Relleno")
    X0 = g.inp("X0", 'NodeSocketInt'); Y0 = g.inp("Y0", 'NodeSocketInt')
    A = g.inp("A", 'NodeSocketInt', 8); Bd = g.inp("B", 'NodeSocketInt', 8)
    Z = g.inp("Z", 'NodeSocketFloat'); PIb = g.inp("PI base", 'NodeSocketInt')
    out = g.out("Geometry", 'NodeSocketGeometry')
    nx = g.ceil(g.div(A, 2)); ny = g.ceil(g.div(Bd, 2))
    x = g.store(g.points(g.mul(nx, ny)), "e", 0, 'INT')
    idx = g.index()
    a = g.mod(idx, nx); b = g.floor(g.div(idx, nx))
    w = g.min(2.0, g.sub(A, g.mul(a, 2))); h = g.min(2.0, g.sub(Bd, g.mul(b, 2)))
    area = g.mul(w, h)
    pi = g.add(PIb, g.sel(g.eq(area, 4), 2.0, g.sel(g.eq(area, 1), 0.0, 1.0)))
    rz = g.mul(g.mul(g.eq(w, 1), g.eq(h, 2)), PI2)
    u = g.add(g.add(X0, g.mul(a, 2)), g.div(w, 2)); v = g.add(g.add(Y0, g.mul(b, 2)), g.div(h, 2))
    g.L(emit(g, x, True, pi, u, v, Z, rz), out)
    return g
RELLENO = g_relleno()

def g_colocar():
    # (u, v, z) de cada fachada -> coordenadas del edificio (origen en el centro de la planta, a ras de suelo)
    g = G("LB Colocar")
    geo = g.inp("Geometry", 'NodeSocketGeometry'); protos = g.inp("Prototipos", 'NodeSocketGeometry')
    W = g.inp("Ancho", 'NodeSocketInt', 16); D = g.inp("Fondo", 'NodeSocketInt', 12)
    out = g.out("Instances", 'NodeSocketGeometry')
    e = g.attr("e"); rz = g.attr("rz"); pi = g.attr("pi", 'INT')
    sep = g.n('ShaderNodeSeparateXYZ'); g.L(g.n('GeometryNodeInputPosition').outputs[0], sep.inputs[0])
    u, v, z = sep.outputs
    th = g.mul(e, PI2); c = g.m('COSINE', th); s = g.m('SINE', th)
    sx = g.sub(s, c); sy = g.sub(g.mul(c, -1.0), s)
    X = g.mul(g.add(g.mul(sx, g.div(W, 2)), g.sub(g.mul(u, c), g.mul(v, s))), S)
    Y = g.mul(g.add(g.mul(sy, g.div(D, 2)), g.add(g.mul(u, s), g.mul(v, c))), S)
    sp = g.n('GeometryNodeSetPosition'); g.L(geo, sp.inputs["Geometry"]); g.L(g.vec(X, Y, z), sp.inputs["Position"])
    rot = g.n('FunctionNodeEulerToRotation'); g.L(g.vec(0.0, 0.0, g.add(th, rz)), rot.inputs[0])
    iop = g.n('GeometryNodeInstanceOnPoints')
    g.L(sp.outputs[0], iop.inputs["Points"]); g.L(protos, iop.inputs["Instance"])
    iop.inputs["Pick Instance"].default_value = True
    g.L(pi, iop.inputs["Instance Index"]); g.L(rot.outputs[0], iop.inputs["Rotation"])
    g.L(iop.outputs[0], out)
    return g
COLOCAR = g_colocar()

def g_piso():
    # Un piso completo a z = 0: banda de ladrillo, zona de ventanas, banda de ladrillo, 2 placas, esquinas 2357/2420
    g = G("LB Piso")
    W = g.inp("Ancho", 'NodeSocketInt', 16); D = g.inp("Fondo", 'NodeSocketInt', 12)
    H = g.inp("Hueco", 'NodeSocketInt'); esc = g.inp("Escaparate", 'NodeSocketInt')
    seed = g.inp("Semilla", 'NodeSocketInt'); pc = g.inp("Ciegas", 'NodeSocketFloat')
    out = g.out("Geometry", 'NodeSocketGeometry')
    cel = g.call(CELDAS, Ancho=W, Fondo=D, Delta=-4)
    def tramo(z, o, pib, h): return g.call(TRAMO, Geometry=cel, U0=2.0, V=0.5, Z=z, Desfase=o, **{"PI base": pib, "Hueco": h})
    partes = [tramo(0.0, 0, IDX["ladrillo"], H), tramo(5 * B, 2, IDX["ladrillo"], H),
              tramo(6 * B, 1, IDX["placa"], 0), tramo(6 * B + P, 3, IDX["placa"], 0),
              g.call(VENTANAS, Geometry=cel, Hueco=H, Escaparate=esc, Semilla=seed, Ciegas=pc)]
    partes += [g.call(ESQUINAS, PI=IDX["esquina"], Z=r * B) for r in range(6)]
    partes += [g.call(ESQUINAS, PI=IDX["esquina_placa"], Z=6 * B + r * P) for r in range(2)]
    g.L(g.join(*partes), out)
    return g
PISO = g_piso()

# ---------- grupo principal ----------
def menu(g, sock, items, dtype, valores=None):
    ms = g.n('GeometryNodeMenuSwitch'); ms.data_type = dtype
    ms.enum_items.clear()
    for nm in items: ms.enum_items.new(nm)
    for k, nm in enumerate(items):
        g.L(valores[k] if valores else k, ms.inputs[nm])
    g.L(sock, ms.inputs["Menu"])
    return ms.outputs[0]

def g_edificio():
    g = G("Edificio LEGO")
    t = g.t
    g.inp("Geometry", 'NodeSocketGeometry')
    pisos = g.inp("Pisos", 'NodeSocketInt', 6, 1, 100)
    W = g.inp("Ancho (studs)", 'NodeSocketInt', 16, 8, 96)
    D = g.inp("Fondo (studs)", 'NodeSocketInt', 12, 8, 96)
    s_pb = g.inp("Planta baja", 'NodeSocketMenu'); s_rm = g.inp("Remate", 'NodeSocketMenu')
    pv = t.interface.new_panel("Variación")
    seed = g.inp("Semilla", 'NodeSocketInt', 0, parent=pv)
    pc = g.inp("Ventanas ciegas", 'NodeSocketFloat', 0.15, 0.0, 1.0, parent=pv, subtype='FACTOR')
    pj = g.inp("Jardineras", 'NodeSocketFloat', 0.3, 0.0, 1.0, parent=pv, subtype='FACTOR')
    pl = g.inp("Luces encendidas", 'NodeSocketFloat', 0.0, 0.0, 1.0, parent=pv, subtype='FACTOR')
    pm = t.interface.new_panel("Marquesina")
    m_ancho = g.inp("Ancho marquesina (studs)", 'NodeSocketInt', 12, 8, 40, parent=pm)
    m_fondo = g.inp("Vuelo marquesina (studs)", 'NodeSocketInt', 4, 3, 12, parent=pm)
    m_alt = g.inp("Altura marquesina (placas)", 'NodeSocketInt', 1, -3, 6, parent=pm)
    m_n = g.inp("Pináculos superiores", 'NodeSocketInt', 3, 0, 12, parent=pm)
    m_sep = g.inp("Separación pináculos (studs)", 'NodeSocketInt', 0, 0, 12, parent=pm)
    pcol = t.interface.new_panel("Colores")
    mats = {r: g.inp(r, 'NodeSocketMaterial', MAT[r], parent=pcol) for r in ROLES}
    realizar = g.inp("Realizar instancias", 'NodeSocketBool', False)
    out = g.out("Geometry", 'NodeSocketGeometry')

    # prototipos: pieza LDraw con el material de su rol, en el orden de PROTOS
    # (la entrada multiple toma primero el enlace con multi_input_sort_id mayor: se enlaza en orden inverso)
    gti = g.n('GeometryNodeGeometryToInstance')
    for pid, rol in reversed(PROTOS):
        oi = g.n('GeometryNodeObjectInfo', transform_space='ORIGINAL'); oi.inputs["Object"].default_value = OBJ[pid]
        geo = oi.outputs["Geometry"]
        # rol doble (cuerpo, caras inclinadas): un Set Material por indice de material original
        for k, r in enumerate(rol if isinstance(rol, tuple) else (rol,)):
            sm = g.n('GeometryNodeSetMaterial'); g.L(geo, sm.inputs["Geometry"]); g.L(mats[r], sm.inputs["Material"])
            if isinstance(rol, tuple):
                g.L(g.eq(g.n('GeometryNodeInputMaterialIndex').outputs[0], k), sm.inputs["Selection"])
            geo = sm.outputs[0]
        g.L(geo, gti.inputs[0])
    def objeto(sock):   # sube por los Set Material hasta el Object Info
        n = sock.node
        while n.bl_idname == 'GeometryNodeSetMaterial': n = n.inputs["Geometry"].links[0].from_node
        return n.inputs["Object"].default_value.name
    links = sorted([l for l in t.links if l.to_node == gti], key=lambda l: -l.multi_input_sort_id)
    orden = [objeto(l.from_socket) for l in links]
    assert orden == ["LD_" + p for p, _ in PROTOS], "orden de Geometry to Instance distinto de PROTOS"
    protos = gti.outputs[0]

    # planta baja
    modo = menu(g, s_pb, ["Entrada hotel", "Puerta simple", "Escaparates", "Sin puerta"], 'INT')
    R0 = g.sub(W, 4)
    w_hotel = g.sel(g.ge(R0, 10), 8.0, g.sel(g.ge(R0, 6), 4.0, 0.0))
    w_una = g.sel(g.ge(R0, 6), 4.0, 0.0)
    Wd = g.sel(g.eq(modo, 0), w_hotel, g.sel(g.eq(modo, 3), 0.0, w_una))
    esc = g.eq(modo, 2)
    baja = g.call(PISO, Ancho=W, Fondo=D, Hueco=Wd, Escaparate=esc, Semilla=seed, Ciegas=pc)
    # marquesina del hotel sobre la puerta de la fachada 0, como la del porche de Nitro. De abajo arriba (v < 0 = calle):
    #   mensulas 3665a + 6141 | placa escalonada (1 stud mas corta delante y a los lados) | placa base |
    #   pendientes 45 al frente con esquinas 3045 y faldones laterales; detras, cresta de ladrillos con studs vistos |
    #   cumbrera de placas sobre la fila alta con verja 3633 y un pinaculo Nitro (59900 + 78258) en cada extremo |
    #   N pinaculos superiores en la cresta: 3062b + 59900 + 78258 sobre jumper 3794b (o placa 1x1 si caen en un stud)
    hotel = g.mul(g.eq(modo, 0), g.gt(Wd, 0.5))
    gs = g.floor(g.div(g.sub(R0, Wd), 2))
    uc = g.add(g.add(gs, 2), g.div(Wd, 2))                          # centro de la puerta
    Lt = g.max(m_ancho, g.add(Wd, 4))                               # sobresale al menos 2 studs por lado
    Lt = g.add(Lt, g.mod(Lt, 2))                                    # par, para que quede centrada en la puerta
    Lt = g.min(Lt, g.mul(g.floor(g.min(uc, g.sub(W, uc))), 2))      # sin pasar de las esquinas del edificio
    a = g.sub(uc, g.div(Lt, 2)); b = g.add(a, Lt)
    Dp = m_fondo
    zt = g.add(6 * B, g.mul(m_alt, P)); zp = g.add(zt, P); zc = g.add(zp, B); zr = g.add(zc, P)  # Altura 1: sobre el marco
    def linea(n, e=0):                                 # puntos de un tramo recto en la fachada e
        x = g.store(g.points(g.mul(hotel, n)), "e", e, 'INT')
        x = g.store(x, "i", g.index(), 'INT')
        return g.store(x, "L", n, 'INT')
    def tramo_e(n, e, u0, v, z, o, pib):
        return g.call(TRAMO, Geometry=linea(n, e), U0=u0, V=v, Z=z, Desfase=o, **{"PI base": pib})
    def rect(x0, y0, A, Bd, z, pib):
        return g.call(RELLENO, X0=x0, Y0=y0, A=g.mul(hotel, A), B=Bd, Z=z, **{"PI base": pib})
    vf = g.sub(1.5, Dp)                                             # fila alta de las pendientes frontales
    extremos = g.store(g.points(g.mul(hotel, 2)), "e", 0, 'INT')    # 0 = izquierda, 1 = derecha
    ux = g.add(g.add(a, 1.5), g.mul(g.index(), g.sub(Lt, 3)))      # 1 stud hacia dentro del borde
    # verjas 1x4 centradas entre los pinaculos laterales
    Lf = g.sub(Lt, 4)
    verjas = g.store(g.points(g.mul(hotel, g.floor(g.div(Lf, 4)))), "e", 0, 'INT')
    uv = g.add(g.add(a, 4.0), g.add(g.floor(g.div(g.mod(Lf, 4), 2)), g.mul(g.index(), 4)))
    # pinaculos superiores: simetricos respecto a la puerta; Separacion 0 = la mayor que cabe en la cresta
    hw = g.sub(g.div(Lt, 2), 3)                                     # el jumper ocupa +-1 stud
    N = g.max(g.min(m_n, g.add(hw, 1)), 0)
    smax = g.floor(g.div(g.mul(hw, 2), g.max(g.sub(N, 1), 1)))
    sp_ = g.sel(g.gt(m_sep, 0.5), g.min(g.max(m_sep, 2), smax), smax)
    sup = g.store(g.points(g.mul(hotel, N)), "e", 0, 'INT')
    up = g.add(uc, g.mul(g.sub(g.index(), g.div(g.sub(N, 1), 2)), sp_))
    en_junta = g.lt(g.sub(up, g.floor(up)), 0.25)                  # entre dos studs -> jumper
    pib = g.sel(en_junta, float(IDX["saltador"]), float(IDX["toldo_placa"]))
    pin = IDX["pinaculo"]
    toldo = g.join(
        emit(g, extremos, True, IDX["mensula"] + 1, ux, -0.5, g.sub(zt, 2 * P + B)),
        emit(g, extremos, True, IDX["mensula"], ux, -0.5, g.sub(zt, P + B)),
        rect(g.add(a, 1), g.sub(1, Dp), g.sub(Lt, 2), g.sub(Dp, 1), g.sub(zt, P), IDX["toldo_base"]),
        rect(a, g.mul(Dp, -1), Lt, Dp, zt, IDX["toldo_base"]),
        tramo_e(g.sub(Lt, 4), 0, g.add(a, 2), vf, zp, 0, IDX["toldo_pend"]),
        emit(g, extremos, True, IDX["toldo_pend_esq"], ux, vf, zp, g.sub(g.mul(g.index(), PI2), PI2)),
        tramo_e(g.sub(Dp, 2), 3, D, g.add(a, 1.5), zp, 0, IDX["toldo_pend"]),                     # faldon izquierdo
        tramo_e(g.sub(Dp, 2), 1, g.sub(2, Dp), g.add(g.sub(W, b), 1.5), zp, 0, IDX["toldo_pend"]),  # faldon derecho
        rect(g.add(a, 2), g.sub(2, Dp), g.sub(Lt, 4), g.sub(Dp, 2), zp, IDX["toldo_cresta"]),
        tramo_e(g.sub(Lt, 2), 0, g.add(a, 1), vf, zc, 1, IDX["toldo_placa"]),
        emit(g, verjas, True, IDX["verja"], uv, vf, zr),
        emit(g, extremos, True, pin + 1, ux, vf, zr),
        emit(g, extremos, True, pin + 2, ux, vf, g.add(zr, BARRA)),
        emit(g, sup, True, pib, up, -0.5, zc),
        emit(g, sup, True, pin, up, -0.5, g.add(zc, P)),
        emit(g, sup, True, pin + 1, up, -0.5, g.add(zc, P + B)),
        emit(g, sup, True, pin + 2, up, -0.5, g.add(zc, P + B + BARRA)))
    baja = g.store(g.join(baja, toldo), "piso", 0, 'INT')

    # pisos tipo: el mismo piso duplicado (Pisos - 1) veces hacia arriba
    tipo = g.call(PISO, Ancho=W, Fondo=D, Hueco=0, Escaparate=0, Semilla=seed, Ciegas=pc)
    dup = g.n('GeometryNodeDuplicateElements', domain='POINT')
    g.L(tipo, dup.inputs["Geometry"]); g.L(g.sub(pisos, 1), dup.inputs["Amount"])
    d1 = g.add(dup.outputs["Duplicate Index"], 1)
    sp = g.n('GeometryNodeSetPosition'); g.L(dup.outputs[0], sp.inputs["Geometry"]); g.L(g.vec(0.0, 0.0, g.mul(d1, F)), sp.inputs["Offset"])
    altos = g.store(sp.outputs[0], "piso", d1, 'INT')
    fach = g.join(baja, altos)

    # variacion por piso: jardineras y luces
    tipo_a = g.attr("tipo"); idr = g.add(g.attr("vid"), g.mul(g.attr("piso"), 7919))
    quitar = g.mul(g.eq(tipo_a, 2), g.no(g.lt(g.rand(idr, g.add(seed, 11)), pj)))
    ux = g.n('ShaderNodeSeparateXYZ'); g.L(g.n('GeometryNodeInputPosition').outputs[0], ux.inputs[0])
    sobre = g.mul(g.mul(hotel, g.eq(g.attr("piso"), 1)), g.mul(g.eq(g.attr("e"), 0),
                  g.mul(g.gt(ux.outputs[0], g.sub(a, 1)), g.lt(ux.outputs[0], g.add(b, 1)))))
    quitar = g.max(quitar, g.mul(g.eq(tipo_a, 2), sobre))
    dl = g.n('GeometryNodeDeleteGeometry', domain='POINT'); g.L(fach, dl.inputs[0]); g.L(quitar, dl.inputs[1])
    luz = g.mul(g.eq(tipo_a, 1), g.lt(g.rand(idr, g.add(seed, 23)), pl))
    fach = g.store(dl.outputs[0], "pi", g.add(g.attr("pi"), luz), 'INT')

    # remates
    z0 = g.mul(pisos, F)
    celW = g.call(CELDAS, Ancho=W, Fondo=D, Delta=-4)
    celR = g.call(CELDAS, Ancho=W, Fondo=D, Delta=0)
    def tramo(cel, u0, v, z, o, pib, rz1=0.0):
        return g.call(TRAMO, Geometry=cel, U0=u0, V=v, Z=z, Desfase=o, **{"PI base": pib, "RZ largo 1": rz1})
    def esq(pi, z, u=0.5, v=0.5, rz=0.0): return g.call(ESQUINAS, PI=pi, U=u, V=v, Z=z, RZ=rz)
    relleno_int = g.call(RELLENO, X0=1, Y0=1, A=g.sub(W, 2), B=g.sub(D, 2), Z=z0, **{"PI base": IDX["relleno"]})
    # alero: anillo de placas 2xN que vuela 1 stud, pendientes 33 con esquinas 3675, verjas 3633 y pinaculos
    zp = g.add(z0, P); zt = g.add(zp, B)
    Lc = g.attr("L"); ic = g.attr("i")
    off = g.floor(g.div(g.mod(Lc, 4), 2)); lv = g.sub(ic, off)
    sel_verja = g.mul(g.mul(g.ge(lv, 0), g.eq(g.mod(lv, 4), 0)), g.lt(g.add(lv, 3.5), Lc))
    alero = g.join(
        tramo(celR, -1.0, 0.0, z0, 0, IDX["alero"], PI2), relleno_int,
        tramo(celW, 2.0, 1.5, zp, 0, IDX["pend"]),
        esq(IDX["pend_esq"], zp, 1.5, 1.5, -PI2),
        emit(g, celW, sel_verja, IDX["verja"], g.add(ic, 4.0), 1.5, zt),
        esq(IDX["pin"], zt, 1.5, 1.5), esq(IDX["pin"] + 1, g.add(zt, B), 1.5, 1.5), esq(IDX["pin"] + 2, g.add(zt, 2 * B), 1.5, 1.5))
    # cornisa: anillo de placas que vuela 1 stud, peto de 1 ladrillo y tiles encima
    cornisa = g.join(
        tramo(celR, -1.0, 0.0, z0, 0, IDX["cornisa"], PI2), relleno_int,
        tramo(celW, 2.0, 0.5, zp, 0, IDX["ladrillo"]), esq(IDX["esquina"], zp),
        tramo(celW, 2.0, 0.5, zt, 2, IDX["teja"]), esq(IDX["esquina_teja"], zt))
    azotea = g.call(RELLENO, X0=0, Y0=0, A=W, B=D, Z=z0, **{"PI base": IDX["relleno"]})
    remate = menu(g, s_rm, ["Alero con pináculos", "Cornisa plana", "Azotea"], 'GEOMETRY', [alero, cornisa, azotea])

    inst = g.call(COLOCAR, Geometry=g.join(fach, remate), Prototipos=protos, Ancho=W, Fondo=D)
    ri = g.n('GeometryNodeRealizeInstances'); g.L(inst, ri.inputs[0])
    sw = g.n('GeometryNodeSwitch', input_type='GEOMETRY')
    g.L(realizar, sw.inputs["Switch"]); g.L(inst, sw.inputs["False"]); g.L(ri.outputs[0], sw.inputs["True"])
    g.L(sw.outputs[0], out)
    for it in t.interface.items_tree:
        if it.item_type == 'SOCKET' and it.socket_type == 'NodeSocketMenu':
            it.default_value = "Entrada hotel" if it.name == "Planta baja" else "Alero con pináculos"
    t.asset_mark()
    t.asset_data.description = "Edificio LEGO con piezas LDraw: pisos, planta, planta baja, remate, variación y colores editables"
    return g
EDIF = g_edificio()

# ordenar nodos en columnas para que se puedan leer
def ordenar(t):
    nivel = {n: 0 for n in t.nodes}
    for _ in range(len(t.nodes)):
        cambio = False
        for l in t.links:
            if nivel[l.to_node] < nivel[l.from_node] + 1:
                nivel[l.to_node] = nivel[l.from_node] + 1; cambio = True
        if not cambio: break
    filas = {}
    for n, lv in nivel.items():
        n.location = (lv * 220, -filas.get(lv, 0) * 180); filas[lv] = filas.get(lv, 0) + 1
for gg in (EMITIR, CELDAS, TRAMO, VENTANAS, ESQUINAS, RELLENO, COLOCAR, PISO, EDIF): ordenar(gg.t)

# ---------- escena de ejemplo ----------
sc = bpy.context.scene
coll_ed = bpy.data.collections.new("Edificios"); sc.collection.children.link(coll_ed)
def ident(nombre):
    return next(i.identifier for i in EDIF.t.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'INPUT' and i.name == nombre)
def edificio(nombre, loc, **params):
    me = bpy.data.meshes.new(nombre); ob = bpy.data.objects.new(nombre, me); coll_ed.objects.link(ob)
    ob.location = loc
    mod = ob.modifiers.new("Edificio LEGO", 'NODES'); mod.node_group = EDIF.t
    for k, v in params.items():          # Blender 5.x: mod.properties.inputs.<identificador>.value
        getattr(mod.properties.inputs, ident(k)).value = v
    return ob
EJEMPLOS = [
    ("Hotel", (0, 0, 0), {"Pisos": 9, "Ancho (studs)": 16, "Fondo (studs)": 12}),
    ("Tienda", (16.0, 0, 0), {"Pisos": 5, "Ancho (studs)": 14, "Fondo (studs)": 12, "Planta baja": "Escaparates", "Remate": "Cornisa plana",
                              "Semilla": 4, "Pared": PAL[5], "Molduras": PAL[138], "Tejado": PAL[138]}),
    ("Casa", (-15.2, 0, 0), {"Pisos": 3, "Ancho (studs)": 12, "Fondo (studs)": 12, "Planta baja": "Puerta simple", "Remate": "Azotea",
                             "Semilla": 7, "Pared": PAL[151], "Puerta": PAL[154], "Jardineras": 0.6}),
]
for nombre, loc, params in EJEMPLOS:
    edificio(nombre, loc, **params)

me = bpy.data.meshes.new("Suelo"); me.from_pydata([(-60, -40, 0), (60, -40, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
suelo = bpy.data.objects.new("Suelo", me); sc.collection.objects.link(suelo); me.materials.append(PAL[194])
cam = bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 32; cam.data.clip_end = 2000
cam.location = (-52, -112, 44)
cam.rotation_euler = ((cam.location * -1) + Vector((1, 0, 30))).to_track_quat('-Z', 'Y').to_euler()
sun = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.5; sun.data.angle = math.radians(3); sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
w = bpy.data.worlds.new("Cielo"); sc.world = w
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.65, 0.8, 1); bg.inputs[1].default_value = 0.8
sc.render.engine = 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'AgX'
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080

bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("GUARDADO", OUT, "prototipos", len(PROTOS), "piezas", len(OBJ))
