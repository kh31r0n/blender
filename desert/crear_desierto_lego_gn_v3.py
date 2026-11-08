# Genera Desierto_LEGO_GN_v3.blend: grupo de Geometry Nodes "Desierto LEGO" que levanta un desierto hecho solo con
# piezas LEGO creadas dentro del propio grupo (cuerpos biselados, studs, cuñas): dunas escalonadas, colinas, mesetas
# de roca con estratos, rocas sueltas y arcos naturales con abertura. Todo sale como instancias (nada se realiza).
# Referencias de estilo (no se reutilizan sus mallas): Desert1.blend (arco), Desert Hill.blend, Desert landscape.blend.
# Uso: blender -b -P ~/blender/desert/crear_desierto_lego_gn_v3.py
#      (shader "LEGO realista" e iluminacion de ~/blender/buildings/scripts/lego_realista.py; no modifica nada existente)
import bpy, sys, os, math, json
from mathutils import Vector

DESERT = os.path.expanduser("~/blender/desert")
sys.path.insert(0, DESERT)
sys.path.insert(0, os.path.expanduser("~/blender/buildings/scripts"))
import desierto_parametros as DP
import lego_realista as LR

OUT = DESERT + "/Desierto_LEGO_GN_v3.blend"
NPROTO = 16        # prototipos por material: indice de instancia = proto + NPROTO * roca
PI = math.pi
sys.setrecursionlimit(20000)

# ---------- ayudante de nodos (patron de buildings/scripts/edificios_gn.py) ----------
class G:
    def __init__(self, name, modificador=False):
        self.t = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        if modificador: self.t.is_modifier = True
        self.frame = None
        self.gi = self.n('NodeGroupInput'); self.go = self.n('NodeGroupOutput')
    def marco(self, etiqueta):
        f = self.t.nodes.new('NodeFrame'); f.label = etiqueta; f.label_size = 28; f.shrink = True
        self.frame = f
        return f
    def inp(self, name, typ, default=None, lo=None, hi=None, parent=None, desc="", subtype=None):
        s = self.t.interface.new_socket(name, in_out='INPUT', socket_type=typ, parent=parent)
        if subtype: s.subtype = subtype
        if default is not None: s.default_value = default
        if lo is not None: s.min_value = lo
        if hi is not None: s.max_value = hi
        if desc: s.description = desc
        return self.gi.outputs[s.identifier]
    def out(self, name, typ):
        s = self.t.interface.new_socket(name, in_out='OUTPUT', socket_type=typ)
        return self.go.inputs[s.identifier]
    def n(self, idname, **kw):
        node = self.t.nodes.new(idname)
        for k, v in kw.items(): setattr(node, k, v)
        if self.frame is not None and idname not in ('NodeGroupInput', 'NodeGroupOutput'): node.parent = self.frame
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
    def round(self, a): return self.m('ROUND', a)
    def mod(self, a, b): return self.m('FLOORED_MODULO', a, b)
    def min(self, a, b): return self.m('MINIMUM', a, b)
    def max(self, a, b): return self.m('MAXIMUM', a, b)
    def abs(self, a): return self.m('ABSOLUTE', a)
    def pow(self, a, b): return self.m('POWER', a, b)
    def lt(self, a, b): return self.m('LESS_THAN', a, b)
    def gt(self, a, b): return self.m('GREATER_THAN', a, b)
    def ge(self, a, b): return self.m('GREATER_THAN', a, self.sub(b, 0.5) if isinstance(b, bpy.types.NodeSocket) else b - 0.5)
    def le(self, a, b): return self.m('LESS_THAN', a, self.add(b, 0.5) if isinstance(b, bpy.types.NodeSocket) else b + 0.5)
    def eq(self, a, b): return self.m('COMPARE', a, b, 0.01)
    def no(self, a): return self.sub(1.0, a)
    def sel(self, c, a, b): return self.add(b, self.mul(c, self.sub(a, b)))   # c ? a : b
    def clamp(self, a, lo, hi): return self.min(self.max(a, lo), hi)
    def suma(self, *xs):
        r = xs[0]
        for x in xs[1:]: r = self.add(r, x)
        return r
    def prod(self, *xs):
        r = xs[0]
        for x in xs[1:]: r = self.mul(r, x)
        return r
    def mins(self, *xs):
        r = xs[0]
        for x in xs[1:]: r = self.min(r, x)
        return r
    def maxs(self, *xs):
        r = xs[0]
        for x in xs[1:]: r = self.max(r, x)
        return r
    def suave(self, e0, e1, x):   # smoothstep(e0, e1, x)
        node = self.n('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='SMOOTHSTEP', clamp=True)
        self.L(x, node.inputs[0]); self.L(e0, node.inputs[1]); self.L(e1, node.inputs[2])
        node.inputs[3].default_value = 0.0; node.inputs[4].default_value = 1.0
        return node.outputs[0]
    def bool(self, a):            # float 0/1 -> booleano
        node = self.n('FunctionNodeCompare', data_type='FLOAT', operation='GREATER_THAN')
        self.L(a, node.inputs[0]); node.inputs[1].default_value = 0.5
        return node.outputs[0]
    def vec(self, x, y, z):
        node = self.n('ShaderNodeCombineXYZ')
        for s, v in zip(node.inputs, (x, y, z)): self.L(v, s)
        return node.outputs[0]
    def sep(self, v):
        node = self.n('ShaderNodeSeparateXYZ'); self.L(v, node.inputs[0])
        return node.outputs[0], node.outputs[1], node.outputs[2]
    def vm(self, op, a, b=None, escala=None):
        node = self.n('ShaderNodeVectorMath', operation=op)
        self.L(a, node.inputs[0])
        if b is not None: self.L(b, node.inputs[1])
        if escala is not None: self.L(escala, node.inputs["Scale"])
        return node.outputs[1] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else node.outputs[0]
    def attr(self, name, dtype='FLOAT'):
        node = self.n('GeometryNodeInputNamedAttribute', data_type=dtype)
        node.inputs["Name"].default_value = name
        return node.outputs["Attribute"]
    def store(self, geo, name, val, dtype='FLOAT'):
        node = self.n('GeometryNodeStoreNamedAttribute', data_type=dtype, domain='POINT')
        self.L(geo, node.inputs["Geometry"]); node.inputs["Name"].default_value = name; self.L(val, node.inputs["Value"])
        return node.outputs[0]
    def stores(self, geo, valores):
        for name, (val, dtype) in valores.items(): geo = self.store(geo, name, val, dtype)
        return geo
    def index(self): return self.n('GeometryNodeInputIndex').outputs[0]
    def pos(self): return self.n('GeometryNodeInputPosition').outputs[0]
    def points(self, count, posicion=None):
        node = self.n('GeometryNodePoints'); self.L(count, node.inputs["Count"])
        if posicion is not None: self.L(posicion, node.inputs["Position"])
        return node.outputs[0]
    def rand(self, ident, seed):
        node = self.n('FunctionNodeRandomValue', data_type='FLOAT')
        self.L(ident, node.inputs["ID"]); self.L(seed, node.inputs["Seed"])
        return node.outputs["Value"]
    def ruido(self, v, escala=1.0, detalle=2.0, rugosidad=0.5):
        node = self.n('ShaderNodeTexNoise', noise_dimensions='3D')
        self.L(v, node.inputs["Vector"]); self.L(escala, node.inputs["Scale"])
        self.L(detalle, node.inputs["Detail"]); self.L(rugosidad, node.inputs["Roughness"])
        return node.outputs["Factor"]
    def voronoi(self, v, escala, aleatoriedad=1.0):
        node = self.n('ShaderNodeTexVoronoi', voronoi_dimensions='2D', feature='F1', distance='EUCLIDEAN')
        self.L(v, node.inputs["Vector"]); self.L(escala, node.inputs["Scale"]); self.L(aleatoriedad, node.inputs["Randomness"])
        return node
    def sample(self, geo, val, idx, dtype='FLOAT'):
        node = self.n('GeometryNodeSampleIndex', data_type=dtype, domain='POINT', clamp=True)
        self.L(geo, node.inputs["Geometry"]); self.L(val, node.inputs["Value"]); self.L(idx, node.inputs["Index"])
        return node.outputs[0]
    def switch(self, dtype, c, falso, cierto):
        node = self.n('GeometryNodeSwitch', input_type=dtype)
        self.L(c, node.inputs["Switch"]); self.L(falso, node.inputs["False"]); self.L(cierto, node.inputs["True"])
        return node.outputs[0]
    def join(self, *geos):
        node = self.n('GeometryNodeJoinGeometry')
        for gg in reversed(geos): self.L(gg, node.inputs[0])   # orden inverso: el ultimo enlace va primero
        return node.outputs[0]
    def borrar(self, geo, sel):
        node = self.n('GeometryNodeDeleteGeometry', domain='POINT', mode='ALL')
        self.L(geo, node.inputs["Geometry"]); self.L(sel, node.inputs["Selection"])
        return node.outputs[0]
    def setpos(self, geo, posicion=None, offset=None, sel=None):
        node = self.n('GeometryNodeSetPosition')
        self.L(geo, node.inputs["Geometry"]); self.L(posicion, node.inputs["Position"])
        self.L(offset, node.inputs["Offset"]); self.L(sel, node.inputs["Selection"])
        return node.outputs[0]
    def mover(self, geo, t=None, r=None, s=None):
        node = self.n('GeometryNodeTransform')
        self.L(geo, node.inputs["Geometry"]); self.L(t, node.inputs["Translation"])
        self.L(r, node.inputs["Rotation"]); self.L(s, node.inputs["Scale"])
        return node.outputs[0]
    def cuenta(self, geo, componente='POINTCLOUD'):
        node = self.n('GeometryNodeAttributeDomainSize', component=componente)
        self.L(geo, node.inputs[0])
        return node.outputs["Point Count"]
    def call(self, group, ins):
        node = self.n('GeometryNodeGroup'); node.node_tree = group.t
        for k, v in ins.items(): self.L(v, node.inputs[k])
        return node

def semilla_vec(g, seed, k):
    # Desplazamiento de ruido por semilla, acotado (precision de float con coordenadas moderadas)
    fx = g.mul(g.m('FRACT', g.add(g.mul(seed, 0.6180339), 0.11 * k)), 911.0)
    fy = g.mul(g.m('FRACT', g.add(g.mul(seed, 0.7548777), 0.37 * k)), 787.0)
    return g.vec(fx, fy, 3.7 * k)

# ---------- subgrupos ----------
def g_vecinos():
    # Indices de las 4 celdas vecinas en la rejilla (orden del nodo Grid: indice = i * Filas + j). En el borde
    # devuelve la propia celda y marca Borde = 1.
    g = G("DL Vecinos")
    idx = g.inp("Índice", 'NodeSocketFloat'); cols = g.inp("Columnas", 'NodeSocketFloat'); fil = g.inp("Filas", 'NodeSocketFloat')
    i = g.floor(g.div(idx, fil)); j = g.sub(idx, g.mul(i, fil))
    hay_xm = g.gt(i, 0.5); hay_xp = g.lt(i, g.sub(cols, 1.5)); hay_ym = g.gt(j, 0.5); hay_yp = g.lt(j, g.sub(fil, 1.5))
    for nombre, val in (("I", i), ("J", j),
                        ("XM", g.sel(hay_xm, g.sub(idx, fil), idx)), ("XP", g.sel(hay_xp, g.add(idx, fil), idx)),
                        ("YM", g.sel(hay_ym, g.sub(idx, 1.0), idx)), ("YP", g.sel(hay_yp, g.add(idx, 1.0), idx)),
                        ("Borde XM", g.no(hay_xm)), ("Borde XP", g.no(hay_xp)),
                        ("Borde YM", g.no(hay_ym)), ("Borde YP", g.no(hay_yp))):
        g.L(val, g.out(nombre, 'NodeSocketFloat'))
    return g

def g_perfil():
    # Perfil de una duna a lo largo del viento, fase 0..1: sube por barlovento hasta la cresta y cae por la cara de
    # avalancha. Asimetria desplaza la cresta a sotavento; Agudeza afila la cresta y aplana los valles.
    g = G("DL Perfil de duna")
    f = g.inp("Fase", 'NodeSocketFloat'); a = g.inp("Asimetría", 'NodeSocketFloat'); k = g.inp("Agudeza", 'NodeSocketFloat')
    c = g.add(0.5, g.mul(0.45, a))
    tau = g.sel(g.lt(f, c), g.div(f, c), g.div(g.no(f), g.max(g.no(c), 0.01)))
    h0 = g.sub(0.5, g.mul(0.5, g.m('COSINE', g.mul(tau, PI))))
    mezcla = g.add(h0, g.mul(k, g.sub(tau, h0)))
    g.L(g.pow(g.max(mezcla, 0.0), g.add(1.0, k)), g.out("Altura", 'NodeSocketFloat'))
    return g

def g_rejilla():
    g = G("DL Rejilla")
    dx = g.inp("Dimensión X", 'NodeSocketFloat'); dy = g.inp("Dimensión Y", 'NodeSocketFloat')
    rx0 = g.inp("Resolución X", 'NodeSocketFloat'); ry0 = g.inp("Resolución Y", 'NodeSocketFloat')
    sub = g.inp("Submuestreo en el visor", 'NodeSocketFloat'); e = g.inp("Altura de escalón (placas)", 'NodeSocketFloat')
    isv = g.n('GeometryNodeIsViewport').outputs[0]
    f = g.switch('FLOAT', isv, 1.0, g.max(sub, 1.0))
    rx = g.max(g.floor(g.div(rx0, f)), 4.0); ry = g.max(g.floor(g.div(ry0, f)), 4.0)
    cx = g.div(dx, rx); cy = g.div(dy, ry); cmin = g.min(cx, cy)
    placa = g.mul(0.4, cmin)
    grid = g.n('GeometryNodeMeshGrid')
    g.L(g.sub(dx, cx), grid.inputs["Size X"]); g.L(g.sub(dy, cy), grid.inputs["Size Y"])
    g.L(rx, grid.inputs["Vertices X"]); g.L(ry, grid.inputs["Vertices Y"])
    pts = g.n('GeometryNodeMeshToPoints'); g.L(grid.outputs[0], pts.inputs["Mesh"])
    geo = g.store(pts.outputs[0], "celda", g.index(), 'INT')
    for nombre, val, typ in (("Rejilla", geo, 'NodeSocketGeometry'), ("Columnas", rx, 'NodeSocketFloat'),
                             ("Filas", ry, 'NodeSocketFloat'), ("Celda X", cx, 'NodeSocketFloat'),
                             ("Celda Y", cy, 'NodeSocketFloat'), ("Celda mínima", cmin, 'NodeSocketFloat'),
                             ("Placa", placa, 'NodeSocketFloat'), ("Escalón", g.mul(placa, e), 'NodeSocketFloat')):
        g.L(val, g.out(nombre, typ))
    return g

def g_relieve(perfil):
    g = G("DL Relieve")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    seed = F("Semilla"); tipo = F("Tipo"); esc = F("Escalón")
    A = F("Altura de dunas"); Ld = F("Escala de dunas"); ang = F("Dirección del viento (°)")
    asim = F("Asimetría"); agu = F("Agudeza de cresta"); sinu = F("Sinuosidad")
    HC = F("Altura de colinas"); LC = F("Escala de colinas")
    dens = F("Densidad de rocas"); tam = F("Tamaño de rocas"); HR = F("Altura de rocas"); grad = F("Gradas de las mesetas")
    carc = F("Cárcavas"); lcarc = F("Escala de cárcavas")
    P = g.pos(); x, y, _ = g.sep(P)
    def perf(fase): return g.call(perfil, {"Fase": fase, "Asimetría": asim, "Agudeza": agu}).outputs[0]
    def ruido_en(escala_u, k, detalle=2.0, rug=0.5):   # ruido 3D de P / escala_u desplazado por la semilla
        return g.ruido(g.vm('ADD', g.vm('SCALE', P, escala=g.div(1.0, escala_u)), semilla_vec(g, seed, k)), 1.0, detalle, rug)

    g.marco("Dunas: perfil asimétrico a lo largo del viento")
    th = g.mul(ang, PI / 180.0); cw = g.m('COSINE', th); sw = g.m('SINE', th)
    s0 = g.add(g.mul(x, cw), g.mul(y, sw)); t0 = g.sub(g.mul(y, cw), g.mul(x, sw))
    warp = g.mul(g.sub(ruido_en(g.mul(Ld, 1.6), 1), 0.5), g.mul(g.mul(sinu, 1.1), Ld))
    amp = g.clamp(g.add(0.55, g.mul(1.7, g.sub(ruido_en(g.mul(Ld, 2.7), 2, 1.0), 0.5))), 0.2, 1.3)
    # Transversales
    h_tr = g.prod(A, amp, perf(g.m('FRACT', g.div(g.add(s0, warp), Ld))))
    # Estrella: tres trenes de dunas a 60 grados; los picos salen donde coinciden las crestas
    suma = None
    for k in range(3):
        a_k = g.add(th, k * PI / 3)
        s_k = g.add(g.add(g.mul(x, g.m('COSINE', a_k)), g.mul(y, g.m('SINE', a_k))), g.mul(warp, 0.5))
        p_k = perf(g.m('FRACT', g.add(g.div(s_k, g.mul(Ld, 1.15)), 0.37 * k)))
        suma = p_k if suma is None else g.add(suma, p_k)
    h_st = g.prod(A, amp, g.min(g.mul(g.pow(g.div(suma, 3.0), 1.4), 1.9), 1.25))
    # Barjanes: una media luna por celda de Voronoi en coordenadas del viento, cuernos hacia sotavento
    sb = g.add(s0, g.mul(warp, 0.3))
    vo = g.voronoi(g.vm('ADD', g.vec(sb, t0, 0.0), semilla_vec(g, seed, 3)), g.div(1.0, g.mul(Ld, 1.25)), 0.85)
    cs, ct, _ = g.sep(g.vm('SUBTRACT', vo.outputs["Position"], semilla_vec(g, seed, 3)))
    cr, cg, cb = g.sep(vo.outputs["Color"])
    R = g.prod(0.26, Ld, 1.25, g.add(0.75, g.mul(0.5, cg)))   # cabe en su celda con los cuernos incluidos
    along = g.sub(sb, cs); across = g.sub(t0, ct)
    along = g.add(along, g.mul(R, 0.5))                       # centra la media luna (cuerpo + cuernos) en la celda
    along2 = g.sub(along, g.div(g.mul(1.3, g.mul(across, across)), R))   # cuernos curvados hacia sotavento
    fase_b = g.div(g.add(g.div(along2, R), 1.0), 2.0)
    dentro_b = g.mul(g.gt(fase_b, 0.0), g.lt(fase_b, 1.0))
    ancho_b = g.pow(g.max(g.sub(1.0, g.pow(g.div(across, R), 2.0)), 0.0), 0.45)
    h_ba = g.prod(A, g.add(0.55, g.mul(0.45, cr)), perf(g.clamp(fase_b, 0.0, 1.0)), dentro_b, ancho_b, g.gt(cb, 0.15))
    h_d = g.sel(g.eq(tipo, 0.0), h_tr, g.sel(g.eq(tipo, 1.0), h_ba, h_st))

    g.marco("Colinas y cárcavas")
    surco = g.sub(1.0, g.abs(g.sub(g.mul(2.0, ruido_en(lcarc, 4)), 1.0)))
    gc = g.mul(carc, g.pow(surco, 5.0))
    h_c = g.prod(HC, g.suave(0.3, 0.75, ruido_en(LC, 5, 3.0, 0.55)), g.sub(1.0, g.mul(0.4, gc)))

    g.marco("Mesetas de roca: Voronoi deformado con gradas")
    # dominio deformado por ruido: contornos irregulares en vez de discos; costados cortos y escalonados, cima plana
    nr = g.n('ShaderNodeTexNoise', noise_dimensions='3D'); nr.inputs["Detail"].default_value = 2.0
    g.L(g.vm('ADD', g.vm('SCALE', P, escala=g.div(1.0, g.mul(tam, 0.45))), semilla_vec(g, seed, 11)), nr.inputs["Vector"])
    wv = g.vm('SCALE', g.vm('SUBTRACT', nr.outputs["Color"], (0.5, 0.5, 0.5)), escala=g.mul(tam, 0.55))
    vr = g.voronoi(g.vm('ADD', g.vm('ADD', P, wv), semilla_vec(g, seed, 6)), g.div(1.0, tam), 0.9)
    rr, rg, rb = g.sep(vr.outputs["Color"])
    rc = g.add(0.24, g.mul(0.16, rg))
    d2 = g.add(vr.outputs["Distance"], g.mul(0.10, g.sub(ruido_en(g.mul(tam, 0.25), 7), 0.5)))
    rel = g.div(g.sub(rc, d2), rc)                      # 1 en el centro, 0 en el contorno, < 0 fuera
    nucleo = g.clamp(g.div(rel, 0.45), 0.0, 1.0)
    grada = g.min(g.div(g.ceil(g.mul(nucleo, grad)), grad), 1.0)
    elegida = g.lt(rr, dens)
    costado = g.lt(nucleo, 0.999)                       # las carcavas muerden los costados; la cima queda plana
    h_r = g.prod(HR, g.add(0.7, g.mul(0.3, rb)), grada, elegida, g.sub(1.0, g.prod(0.55, gc, costado)))
    cerca = g.mul(elegida, g.suave(-0.6, 0.0, rel))     # entorno de la meseta: ahi caen las rocas sueltas

    g.marco("Composición: arena o roca")
    h_s = g.suma(h_c, h_d, esc)
    h_rk = g.suma(h_c, h_r, esc)
    hay_r = g.gt(h_r, g.mul(0.5, esc))
    roca = g.mul(hay_r, g.gt(h_rk, g.sub(h_s, g.mul(0.5, esc))))
    h = g.max(h_s, g.mul(hay_r, h_rk))
    geo = g.stores(geo, {"altura": (h, 'FLOAT'), "roca": (roca, 'FLOAT'), "cerca_roca": (cerca, 'FLOAT'),
                         "duna": (g.div(h_d, g.max(A, 1e-3)), 'FLOAT')})
    g.frame = None
    g.L(geo, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def zona_repeticion(g, geo, iteraciones):
    rin = g.n('GeometryNodeRepeatInput'); rout = g.n('GeometryNodeRepeatOutput'); rin.pair_with_output(rout)
    g.L(geo, rin.inputs["Geometry"]); g.L(iteraciones, rin.inputs["Iterations"])
    return rin.outputs["Geometry"], rout.inputs["Geometry"], rout.outputs["Geometry"]

def g_erosion(vecinos):
    # Erosion termica: en cada pasada cada celda intercambia material con sus 4 vecinas donde el desnivel supera el
    # talud. La roca se erosiona mucho menos (conserva sus cortados).
    g = G("DL Erosión")
    geo = g.inp("Geometry", 'NodeSocketGeometry'); it = g.inp("Iteraciones", 'NodeSocketInt')
    tal = g.inp("Talud (escalones)", 'NodeSocketFloat'); esc = g.inp("Escalón", 'NodeSocketFloat')
    cols = g.inp("Columnas", 'NodeSocketFloat'); fil = g.inp("Filas", 'NodeSocketFloat')
    g.marco("Repetición: erosión térmica")
    gin, gout_in, gout = zona_repeticion(g, geo, it)
    h = g.attr("altura"); r = g.attr("roca")
    v = g.call(vecinos, {"Índice": g.index(), "Columnas": cols, "Filas": fil})
    T = g.mul(tal, esc); flujo = None
    for k in ("XM", "XP", "YM", "YP"):
        hn = g.sample(gin, h, v.outputs[k])
        f = g.sub(g.max(g.sub(g.sub(hn, h), T), 0.0), g.max(g.sub(g.sub(h, hn), T), 0.0))
        flujo = f if flujo is None else g.add(flujo, f)
    g.L(g.store(gin, "altura", g.add(h, g.prod(0.2, g.sub(1.0, g.mul(0.95, r)), flujo))), gout_in)
    g.frame = None
    g.L(gout, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_arcos_colocacion():
    g = G("DL Arcos: colocación")
    rej = g.inp("Rejilla", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    seed = F("Semilla"); DX = F("Dimensión X"); DY = F("Dimensión Y"); cx = F("Celda X"); cy = F("Celda Y")
    cmin = F("Celda mínima"); cols = F("Columnas"); fil = F("Filas"); esc = F("Escalón")
    dens = F("Densidad de arcos"); mx = F("Máximo de arcos"); luz = F("Luz del arco"); alt = F("Altura del arco")
    gro = F("Grosor del arco"); prof = F("Profundidad del arco"); var = F("Variación de tamaño")
    g.marco("Posiciones: Poisson sin solapes, alineadas a la rejilla de studs")
    n = g.min(mx, g.round(g.prod(dens, DX, DY, 1e-6)))
    wmax = g.mul(luz, g.add(1.0, var))
    margen = g.suma(g.mul(wmax, 0.5), gro, g.mul(cmin, 4.0))
    px = g.max(g.sub(DX, g.mul(2.0, margen)), 1.0); py = g.max(g.sub(DY, g.mul(2.0, margen)), 1.0)
    plano = g.n('GeometryNodeMeshGrid'); g.L(px, plano.inputs["Size X"]); g.L(py, plano.inputs["Size Y"])
    plano.inputs["Vertices X"].default_value = 2; plano.inputs["Vertices Y"].default_value = 2
    dist = g.n('GeometryNodeDistributePointsOnFaces', distribute_method='POISSON')
    g.L(plano.outputs[0], dist.inputs["Mesh"]); g.L(g.mul(wmax, 1.5), dist.inputs["Distance Min"])
    g.L(g.div(80.0, g.mul(px, py)), dist.inputs["Density Max"]); g.L(g.add(seed, 11.0), dist.inputs["Seed"])
    k = g.index()
    pts = g.borrar(dist.outputs["Points"], g.bool(g.ge(k, n)))
    g.marco("Tamaño y base de cada arco")
    sv = g.add(1.0, g.mul(var, g.sub(g.mul(2.0, g.rand(k, g.add(seed, 23.0))), 1.0)))
    W = g.mul(luz, sv); Ha = g.mul(alt, sv)
    t = g.clamp(g.mul(gro, g.add(0.85, g.mul(0.3, g.rand(k, g.add(seed, 31.0))))), g.mul(cmin, 2.4), g.mul(0.3, g.min(W, Ha)))
    D = g.max(g.mul(prof, g.add(0.8, g.mul(0.4, g.rand(k, g.add(seed, 37.0))))), cmin)
    giro = g.lt(g.rand(k, g.add(seed, 29.0)), 0.5)
    x, y, _ = g.sep(g.pos())
    def celda(c, d, tam, nmax): return g.clamp(g.floor(g.div(g.add(c, g.mul(d, 0.5)), tam)), 0.0, g.sub(nmax, 1.0))
    def centro(i, d, tam): return g.sub(g.mul(g.add(i, 0.5), tam), g.mul(d, 0.5))
    xs = centro(celda(x, DX, cx, cols), DX, cx); ys = centro(celda(y, DY, cy, fil), DY, cy)
    A = g.mul(W, 0.5); hpie = []
    for sgn in (-1.0, 1.0):
        fx = g.add(xs, g.prod(sgn, A, g.no(giro))); fy = g.add(ys, g.prod(sgn, A, giro))
        fidx = g.add(g.mul(celda(fx, DX, cx, cols), fil), celda(fy, DY, cy, fil))
        hpie.append(g.sample(rej, g.attr("altura"), fidx))
    base = g.mul(g.max(g.round(g.div(g.min(*hpie), esc)), 1.0), esc)
    pts = g.setpos(pts, g.vec(xs, ys, 0.0))
    pts = g.stores(pts, {"luz": (W, 'FLOAT'), "alto": (Ha, 'FLOAT'), "grosor": (t, 'FLOAT'), "fondo": (D, 'FLOAT'),
                         "giro": (giro, 'FLOAT'), "base": (base, 'FLOAT'), "arco": (g.add(k, 1.0), 'FLOAT')})
    g.frame = None
    g.L(pts, g.out("Arcos", 'NodeSocketGeometry'))
    g.L(g.cuenta(pts), g.out("Número de arcos", 'NodeSocketFloat'))
    return g

def g_arcos_terreno():
    # Abre un cauce bajo cada arco (la abertura queda libre y se ve a traves) y envuelve las patas en un pedestal de roca
    g = G("DL Arcos: terreno")
    rej = g.inp("Rejilla", 'NodeSocketGeometry'); arcos = g.inp("Arcos", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    narc = F("Número de arcos"); cmin = F("Celda mínima"); esc = F("Escalón"); R = F("Radio del pedestal")
    Fb = F("Abocinado de patas")
    x, y, _ = g.sep(g.pos())
    sn = g.n('GeometryNodeSampleNearest', domain='POINT')
    g.L(arcos, sn.inputs["Geometry"]); g.L(g.vec(x, y, 0.0), sn.inputs["Sample Position"])
    k = sn.outputs["Index"]
    def at(nombre): return g.sample(arcos, g.attr(nombre), k)
    cx_, cy_, _ = g.sep(g.sample(arcos, g.pos(), k, 'FLOAT_VECTOR'))
    giro = at("giro"); W = at("luz"); t = at("grosor"); D = at("fondo"); bz = at("base"); Ha = at("alto")
    hay = g.gt(narc, 0.5)
    dx = g.sub(x, cx_); dy = g.sub(y, cy_)
    au = g.abs(g.sel(giro, dy, dx)); av = g.abs(g.sel(giro, dx, dy))
    A = g.mul(W, 0.5)
    tin = g.mul(0.5, t); tout = g.prod(0.5, t, g.add(1.0, Fb))
    g.marco("Cauce bajo la abertura")
    largo = g.suma(g.mul(D, 0.5), g.max(R, g.mul(Ha, 0.5)), g.mul(cmin, 6.0))
    franja = g.prod(hay, g.lt(au, g.sub(g.sub(A, tin), g.mul(cmin, 0.5))), g.lt(av, largo))
    # el arco queda exento: alrededor de su huella la arena no pasa de la base + 2 escalones (ladera suave hacia fuera)
    dfu = g.max(g.sub(au, g.add(A, tout)), 0.0); dfv = g.max(g.sub(av, g.prod(0.5, D, g.add(1.0, g.mul(0.6, Fb)))), 0.0)
    tope = g.add(g.add(bz, g.mul(esc, 2.0)), g.mul(g.m('SQRT', g.add(g.mul(dfu, dfu), g.mul(dfv, dfv))), 0.6))
    h = g.sel(hay, g.min(g.attr("altura"), tope), g.attr("altura"))
    h_cauce = g.add(bz, g.mul(g.max(g.sub(av, g.add(g.mul(D, 0.5), g.mul(cmin, 2.0))), 0.0), 0.7))
    h1 = g.sel(franja, g.min(h, h_cauce), h)
    g.marco("Pedestal de roca en las patas")
    du = g.max(g.sub(g.abs(g.sub(au, A)), tout), 0.0)
    dv = g.max(g.sub(av, g.prod(0.5, D, g.add(1.0, g.mul(0.6, Fb)))), 0.0)
    df = g.m('SQRT', g.add(g.mul(du, du), g.mul(dv, dv)))
    ped = g.prod(hay, g.gt(R, 0.01), g.lt(df, R), g.no(franja))
    h_ped = g.add(bz, g.prod(2.0, esc, g.sub(1.0, g.suave(0.0, R, df))))
    h2 = g.sel(ped, g.max(h1, h_ped), h1)
    roca = g.max(g.attr("roca"), g.mul(ped, g.gt(h_ped, g.sub(h1, g.mul(0.5, esc)))))
    zona = g.prod(hay, g.lt(au, g.suma(A, tout, R, g.mul(cmin, 4.0))), g.lt(av, g.add(largo, R)))
    geo = g.stores(rej, {"altura": (h2, 'FLOAT'), "roca": (roca, 'FLOAT'), "zona_arco": (zona, 'FLOAT')})
    g.frame = None
    g.L(geo, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_niveles(vecinos):
    g = G("DL Niveles")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    esc = F("Escalón"); base = F("Grosor de la base (escalones)"); limp = F("Limpiar picos sueltos")
    pend_on = F("Pendientes en bordes"); prob = F("Probabilidad de pendientes"); seed = F("Semilla")
    cols = F("Columnas"); fil = F("Filas")
    g.marco("Cuantización en niveles")
    geo = g.store(geo, "nivel", g.max(g.round(g.div(g.attr("altura"), esc)), 1.0))
    g.marco("Limpieza de picos y hoyos de una celda")
    gin, gout_in, gout = zona_repeticion(g, geo, g.mul(limp, 2.0))
    L = g.attr("nivel")
    v = g.call(vecinos, {"Índice": g.index(), "Columnas": cols, "Filas": fil})
    ln = [g.sample(gin, L, v.outputs[k]) for k in ("XM", "XP", "YM", "YP")]
    g.L(g.store(gin, "nivel", g.clamp(L, g.mins(*ln), g.maxs(*ln))), gout_in)
    geo = gout
    g.marco("Vecinos, pendientes y clave de fusión")
    v = g.call(vecinos, {"Índice": g.index(), "Columnas": cols, "Filas": fil})
    fondo = g.mul(base, -1.0)
    nb, bajo = {}, {}
    for k in ("XM", "XP", "YM", "YP"):
        borde = v.outputs["Borde " + k]
        nb[k] = g.sel(borde, fondo, g.sample(geo, L, v.outputs[k]))
        bajo[k] = g.mul(g.eq(nb[k], g.sub(L, 1.0)), g.no(borde))
    roca = g.attr("roca")
    permite = g.prod(pend_on, g.lt(g.rand(g.attr("celda", 'INT'), g.add(seed, 41.0)), g.mul(prob, g.sub(1.0, g.mul(0.75, roca)))))
    # la cuña mira cuesta abajo segun el gradiente de la altura continua (filas coherentes en cada ladera);
    # la de esquina solo donde la pendiente es diagonal y las dos vecinas de ese cuadrante estan un nivel mas abajo
    h = g.attr("altura")
    hn = {k: g.sample(geo, h, v.outputs[k]) for k in ("XM", "XP", "YM", "YP")}
    gx = g.sub(hn["XP"], hn["XM"]); gy = g.sub(hn["YP"], hn["YM"])
    ax = g.m('GREATER_THAN', g.abs(gx), g.abs(gy))
    hacia_xp = g.lt(gx, 0.0); hacia_yp = g.lt(gy, 0.0)
    bajo_x = g.sel(hacia_xp, bajo["XP"], bajo["XM"]); bajo_y = g.sel(hacia_yp, bajo["YP"], bajo["YM"])
    diagonal = g.gt(g.div(g.min(g.abs(gx), g.abs(gy)), g.max(g.max(g.abs(gx), g.abs(gy)), 1e-6)), 0.55)
    esquina = g.prod(permite, diagonal, bajo_x, bajo_y)
    recta = g.prod(permite, g.no(esquina), g.sel(ax, bajo_x, bajo_y))
    giro_r = g.sel(ax, g.sel(hacia_xp, 0.0, PI), g.sel(hacia_yp, PI / 2, 3 * PI / 2))
    giro_e = g.sel(hacia_xp, g.sel(hacia_yp, 0.0, 3 * PI / 2), g.sel(hacia_yp, PI / 2, PI))
    pend = g.add(recta, g.mul(2.0, esquina))
    clave = g.sel(g.gt(pend, 0.5), g.mul(g.add(g.attr("celda", 'INT'), 10.0), -1.0), g.add(g.mul(L, 2.0), roca))
    geo = g.stores(geo, {"pend": (pend, 'FLOAT'), "pend_giro": (g.sel(esquina, giro_e, giro_r), 'FLOAT'),
                         "clave": (clave, 'FLOAT')})
    # nivel visible mas bajo de los costados: una vecina con cuña cuenta un nivel menos (su cara inclinada deja
    # al aire la parte alta de ese nivel en la columna de al lado)
    g.marco("Costados visibles (vecinas con cuña cuentan un nivel menos)")
    nb2 = [g.sel(v.outputs["Borde " + k], fondo,
                 g.sub(g.sample(geo, L, v.outputs[k]), g.gt(g.sample(geo, g.attr("pend"), v.outputs[k]), 0.5)))
           for k in ("XM", "XP", "YM", "YP")]
    geo = g.store(geo, "nmin", g.mins(*nb2))
    g.frame = None
    g.L(geo, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_cimas():
    # Pieza superior de cada columna. Las celdas se agrupan en macrobloques 4x4 (filas alternas desplazadas 2 celdas,
    # orientacion al azar) partidos en dos ranuras 2x4; cada ranura usa la pieza mas grande cuyas celdas comparten
    # nivel y material: 2x4, 2x2, 1x2 o 1x1. Solo la celda ancla de cada pieza la emite. Las celdas en pendiente
    # llevan una cuña y no se fusionan.
    g = G("DL Cimas")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    seed = F("Semilla"); cx = F("Celda X"); cy = F("Celda Y"); cols = F("Columnas"); fil = F("Filas"); esc = F("Escalón")
    dsu = F("Densidad de rocas sueltas"); tsu = F("Tamaño de rocas sueltas")
    g.marco("Ranuras 2x4 dentro de macrobloques 4x4")
    idx = g.attr("celda", 'INT')
    i = g.floor(g.div(idx, fil)); j = g.sub(idx, g.mul(i, fil))
    mj = g.floor(g.div(j, 4.0)); despl = g.mul(2.0, g.mod(mj, 2.0))
    ii = g.add(i, despl); mi = g.floor(g.div(ii, 4.0))
    o = g.lt(g.rand(g.add(g.mul(mi, 1009.0), mj), g.add(seed, 53.0)), 0.5)
    il = g.sub(ii, g.mul(mi, 4.0)); jl = g.sub(j, g.mul(mj, 4.0))
    a = g.sel(o, jl, il); q = g.sel(o, il, jl); s = g.floor(g.div(q, 2.0)); b = g.sub(q, g.mul(s, 2.0))
    clave = g.attr("clave")
    claves = []
    for kk in range(8):
        ka, kb = kk % 4, kk // 4
        ilk = g.sel(o, g.add(g.mul(s, 2.0), kb), float(ka)); jlk = g.sel(o, float(ka), g.add(g.mul(s, 2.0), kb))
        ik = g.sub(g.add(g.mul(mi, 4.0), ilk), despl); jk = g.add(g.mul(mj, 4.0), jlk)
        dentro = g.prod(g.gt(ik, -0.5), g.lt(ik, g.sub(cols, 0.5)), g.gt(jk, -0.5), g.lt(jk, g.sub(fil, 0.5)))
        claves.append(g.sel(dentro, g.sample(geo, clave, g.add(g.mul(ik, fil), jk)), -1e6 - 7.0 * kk))
    def iguales(*ks): return g.lt(g.sub(g.maxs(*ks), g.mins(*ks)), 0.5)
    k = claves
    u8 = iguales(*k)
    h = g.floor(g.div(a, 2.0))
    u4 = g.sel(h, iguales(k[2], k[3], k[6], k[7]), iguales(k[0], k[1], k[4], k[5]))
    u2 = g.sel(b, g.sel(h, iguales(k[6], k[7]), iguales(k[4], k[5])), g.sel(h, iguales(k[2], k[3]), iguales(k[0], k[1])))
    g.marco("Pieza, ancla, giro y posición")
    tam = g.sel(u8, 3.0, g.sel(u4, 2.0, g.sel(u2, 1.0, 0.0)))
    apar = g.eq(g.mod(a, 2.0), 0.0); b0 = g.eq(b, 0.0)
    ancla = g.sel(g.eq(tam, 3.0), g.mul(g.eq(a, 0.0), b0),
                  g.sel(g.eq(tam, 2.0), g.mul(apar, b0), g.sel(g.eq(tam, 1.0), apar, 1.0)))
    oa = g.sel(g.eq(tam, 3.0), 1.5, g.sel(g.gt(tam, 0.5), 0.5, 0.0)); ob = g.sel(g.gt(tam, 1.5), 0.5, 0.0)
    offx = g.mul(g.sel(o, ob, oa), cx); offy = g.mul(g.sel(o, oa, ob), cy)
    pend = g.attr("pend")
    proto = g.sel(g.eq(pend, 1.0), 6.0, g.sel(g.eq(pend, 2.0), 7.0, tam))
    largo = g.max(g.eq(tam, 1.0), g.eq(tam, 3.0))
    giro = g.sel(g.gt(pend, 0.5), g.attr("pend_giro"), g.prod(o, largo, PI / 2))
    escala = g.switch('VECTOR', g.bool(g.gt(g.abs(g.m('SINE', giro)), 0.5)), (1.0, 1.0, 1.0),
                      g.vec(g.div(cy, cx), g.div(cx, cy), 1.0))
    L = g.attr("nivel")
    x, y, _ = g.sep(g.pos())
    geo2 = g.stores(geo, {"proto": (proto, 'FLOAT'), "giro": (giro, 'FLOAT'), "escala": (escala, 'FLOAT_VECTOR'),
                          "tam": (tam, 'FLOAT'), "pcelda": (g.pos(), 'FLOAT_VECTOR')})
    geo2 = g.setpos(geo2, g.vec(g.add(x, offx), g.add(y, offy), g.mul(g.sub(L, 1.0), esc)))
    cimas = g.borrar(geo2, g.bool(g.no(ancla)))
    g.marco("Rocas sueltas sobre las cimas planas")
    celda = g.attr("celda", 'INT')
    # mas probables al pie de las mesetas (derrubios) que en mitad de las dunas
    prob_s = g.mul(dsu, g.add(0.2, g.mul(2.5, g.attr("cerca_roca"))))
    cand = g.prod(g.lt(g.rand(celda, g.add(seed, 61.0)), prob_s), g.eq(g.attr("pend"), 0.0), g.no(g.attr("zona_arco")),
                  g.no(g.attr("roca")))
    grande = g.gt(g.attr("tam"), 1.5)
    proto_s = g.sel(grande, g.sel(g.lt(g.rand(celda, g.add(seed, 67.0)), tsu), 14.0, 13.0), 12.0)
    pc = g.attr("pcelda", 'FLOAT_VECTOR'); px, py, _ = g.sep(pc)
    off = g.mul(grande, 0.5)
    sueltas = g.borrar(cimas, g.bool(g.no(cand)))      # antes de sobrescribir "roca", que la seleccion lee
    sueltas = g.stores(sueltas, {"proto": (proto_s, 'FLOAT'), "roca": (1.0, 'FLOAT'), "escala": ((1.0, 1.0, 1.0), 'FLOAT_VECTOR'),
                                 "giro": (g.mul(g.lt(g.rand(celda, g.add(seed, 71.0)), 0.5), PI), 'FLOAT')})
    sueltas = g.setpos(sueltas, g.vec(g.add(px, g.mul(off, cx)), g.add(py, g.mul(off, cy)), g.mul(L, esc)))
    g.frame = None
    g.L(cimas, g.out("Cimas", 'NodeSocketGeometry'))
    g.L(sueltas, g.out("Rocas sueltas", 'NodeSocketGeometry'))
    # tapa de cada celda bajo su pieza visible mas baja: cierra el fondo de las juntas biseladas (los niveles
    # ocultos no se instancian y, sin tapa, por las esquinas donde se juntan cuatro piezas se veria el vacio)
    g.marco("Tapas: fondo de las juntas")
    x0, y0, _ = g.sep(g.pos())
    tapas = g.stores(geo, {"proto": (15.0, 'FLOAT'), "giro": (0.0, 'FLOAT'), "escala": ((1.0, 1.0, 1.0), 'FLOAT_VECTOR')})
    # medio escalon por debajo: tambien cierra la ranura del bisel de la vecina, que queda justo bajo la pieza
    tapas = g.setpos(tapas, g.vec(x0, y0, g.mul(g.sub(g.min(g.attr("nmin"), g.sub(L, 1.0)), 0.5), esc)))
    g.frame = None
    g.L(tapas, g.out("Tapas", 'NodeSocketGeometry'))
    return g

def g_laterales():
    # Solo los niveles visibles por los costados: de la cima hacia abajo hasta la vecina mas baja (en el borde, hasta
    # el zocalo). Aparejo a soga: los niveles pares se emparejan en X y los impares en Y, alternando la junta.
    g = G("DL Laterales")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    cx = F("Celda X"); cy = F("Celda Y"); cols = F("Columnas"); fil = F("Filas"); esc = F("Escalón")
    g.marco("Un punto por nivel visible")
    L = g.attr("nivel"); nmin = g.attr("nmin")
    dup = g.n('GeometryNodeDuplicateElements', domain='POINT')
    g.L(geo, dup.inputs["Geometry"]); g.L(g.max(g.sub(g.sub(L, 1.0), nmin), 0.0), dup.inputs["Amount"])
    pts = dup.outputs["Geometry"]
    lv = g.sub(g.sub(L, 2.0), dup.outputs["Duplicate Index"])
    g.marco("Ladrillos 1x2 a soga")
    idx = g.attr("celda", 'INT'); i = g.floor(g.div(idx, fil)); j = g.sub(idx, g.mul(i, fil))
    ejx = g.eq(g.mod(lv, 2.0), 0.0)
    par = g.mod(g.add(g.sel(ejx, i, j), g.floor(g.div(lv, 2.0))), 2.0)
    izq = g.eq(par, 0.0); paso = g.sel(izq, 1.0, -1.0)
    pi_ = g.add(i, g.mul(paso, ejx)); pj = g.add(j, g.mul(paso, g.no(ejx)))
    dentro = g.sel(ejx, g.mul(g.gt(pi_, -0.5), g.lt(pi_, g.sub(cols, 0.5))), g.mul(g.gt(pj, -0.5), g.lt(pj, g.sub(fil, 0.5))))
    pidx = g.add(g.mul(pi_, fil), pj)
    lp = g.sample(geo, g.attr("nivel"), pidx); nminp = g.sample(geo, g.attr("nmin"), pidx)
    rp = g.sample(geo, g.attr("roca"), pidx)
    pareja = g.prod(dentro, g.le(lv, g.sub(lp, 2.0)), g.eq(rp, g.attr("roca")))
    salta = g.prod(g.no(izq), pareja, g.ge(lv, nminp))
    off = g.prod(pareja, 0.5, paso)
    x, y, _ = g.sep(g.pos())
    girado = g.mul(pareja, g.no(ejx))
    pts = g.stores(pts, {"proto": (g.sel(pareja, 5.0, 4.0), 'FLOAT'), "giro": (g.mul(girado, PI / 2), 'FLOAT'),
                         "escala": (g.switch('VECTOR', g.bool(girado), (1.0, 1.0, 1.0), g.vec(g.div(cy, cx), g.div(cx, cy), 1.0)), 'FLOAT_VECTOR')})
    pts = g.setpos(pts, g.vec(g.add(x, g.prod(off, ejx, cx)), g.add(y, g.prod(off, g.no(ejx), cy)), g.mul(lv, esc)))
    pts = g.borrar(pts, g.bool(salta))
    g.frame = None
    g.L(pts, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_arco_dentro():
    # Banda superelíptica de un arco en su plano local: U a lo largo de la luz, V de fondo, Z sobre la base.
    # Distancia aproximada a la linea media = (rho - 1) / |grad rho|. La erosion solo muerde la cara exterior y el
    # fondo, y se desvanece hacia la base: la abertura nunca se cierra, la banda conserva al menos ~0.6 de su grosor
    # y las patas apoyan macizas (sin aleros sobre el suelo).
    g = G("DL Arco: dentro")
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    U = F("U"); V = F("V"); Z = F("Z"); luz = F("Luz"); alto = F("Alto"); t = F("Grosor"); D = F("Fondo")
    p = F("Redondez"); Fb = F("Abocinado"); E = F("Erosión"); seed = F("Semilla"); esc = F("Escalón")
    A = g.mul(luz, 0.5); B = g.max(g.sub(alto, g.mul(t, 0.5)), t)
    ze = g.max(Z, 0.0)                                 # bajo la base las patas siguen en vertical
    X = g.div(g.abs(U), A); Zn = g.div(ze, B)
    rho = g.max(g.pow(g.add(g.pow(X, p), g.pow(Zn, p)), g.div(1.0, p)), 1e-3)
    r1p = g.pow(rho, g.sub(1.0, p)); p1 = g.sub(p, 1.0)
    gx = g.div(g.mul(r1p, g.pow(X, p1)), A); gz = g.div(g.mul(r1p, g.pow(Zn, p1)), B)
    grad = g.max(g.m('SQRT', g.add(g.mul(gx, gx), g.mul(gz, gz))), 1e-5)
    dist = g.div(g.sub(rho, 1.0), grad)
    s = g.max(g.sub(1.0, g.div(ze, g.mul(0.45, B))), 0.0); s2 = g.mul(s, s)
    # 0 hasta por encima del pedestal (2 escalones sobre la base): la erosion no socava las patas
    sube = g.clamp(g.div(g.sub(ze, g.mul(esc, 2.5)), g.mul(0.3, B)), 0.0, 1.0)
    tin = g.mul(0.5, t)                                # cara interior sin abocinar: nunca se inclina hacia fuera
    q = g.vm('ADD', g.vm('SCALE', g.vec(U, V, Z), escala=g.div(1.0, g.mul(1.3, t))), semilla_vec(g, seed, 8))
    ef = g.sub(1.0, g.prod(E, 0.75, g.suave(0.42, 0.72, g.ruido(q, 1.0, 2.0)), sube))
    tout = g.prod(0.5, t, g.add(1.0, g.mul(Fb, s2)), ef)
    banda = g.mul(g.gt(dist, g.mul(tin, -1.0)), g.lt(dist, tout))
    q2 = g.vm('ADD', g.vm('SCALE', g.vec(U, V, Z), escala=g.div(1.0, t)), semilla_vec(g, seed, 9))
    dv = g.prod(0.5, D, g.add(1.0, g.prod(0.6, Fb, s2)), g.sub(1.0, g.prod(0.35, E, g.suave(0.45, 0.75, g.ruido(q2, 1.0, 1.0)), sube)))
    g.L(g.mul(banda, g.lt(g.abs(V), dv)), g.out("Dentro", 'NodeSocketFloat'))
    return g

def g_arcos_voxeles(dentro_g):
    # Rejilla de voxeles (celda x celda x placa) alrededor de cada arco. Se guardan solo los de superficie; tres placas
    # apiladas se funden en un ladrillo 1x1 (como en Desert1.blend) y los studs solo salen donde no hay nada encima.
    # Con resoluciones muy altas el voxel crece (m celdas) para no pasar de ~150 000 puntos por arco.
    g = G("DL Arcos: vóxeles")
    arcos = g.inp("Arcos", 'NodeSocketGeometry'); niv = g.inp("Niveles", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    narc = F("Número de arcos"); cx = F("Celda X"); cy = F("Celda Y"); cmin = F("Celda mínima"); placa = F("Placa")
    esc = F("Escalón"); cols = F("Columnas"); fil = F("Filas"); DX = F("Dimensión X"); DY = F("Dimensión Y")
    luz = F("Luz del arco"); alt = F("Altura del arco"); gro = F("Grosor del arco"); prof = F("Profundidad del arco")
    var = F("Variación de tamaño"); red = F("Redondez del arco"); Fb = F("Abocinado de patas"); E = F("Erosión del arco")
    seed = F("Semilla")
    g.marco("Tamaño de la caja de vóxeles (valores únicos)")
    wm = g.mul(luz, g.add(1.0, var)); hm = g.mul(alt, g.add(1.0, var))
    tm = g.min(g.mul(gro, 1.15), g.mul(0.3, g.min(wm, hm))); dm = g.mul(prof, 1.2)
    eu = g.suma(g.mul(wm, 0.5), g.mul(tm, g.add(1.6, Fb)), g.mul(cmin, 2.0))
    ev = g.add(g.prod(0.5, dm, g.add(1.0, g.mul(0.6, Fb))), g.mul(cmin, 2.0))
    ezu = g.suma(hm, g.mul(tm, 0.5), g.mul(placa, 2.0)); ezd = g.add(g.mul(esc, 2.0), placa)
    n1 = g.prod(g.add(g.div(g.mul(eu, 2.0), cmin), 1.0), g.add(g.div(g.mul(ev, 2.0), cmin), 1.0),
                g.add(g.div(g.add(ezu, ezd), placa), 1.0))
    mv = g.max(g.ceil(g.pow(g.div(n1, 150000.0), 1.0 / 3.0)), 1.0)
    na = g.ceil(g.div(eu, g.mul(mv, cmin))); nb = g.ceil(g.div(ev, g.mul(mv, cmin)))
    ku = g.ceil(g.div(ezu, g.mul(mv, placa))); kd = g.ceil(g.div(ezd, g.mul(mv, placa)))
    NA = g.add(g.mul(na, 2.0), 1.0); NB = g.add(g.mul(nb, 2.0), 1.0); NK = g.suma(ku, kd, 1.0)
    S = g.mul(NA, NB); NV = g.mul(S, NK)
    g.marco("Vóxel: arco, a, b, k y prueba de banda")
    pts = g.points(g.mul(narc, NV))
    idx = g.index()
    arc = g.floor(g.div(idx, NV)); r = g.sub(idx, g.mul(arc, NV))
    a = g.sub(g.mod(r, NA), na); b = g.sub(g.mod(g.floor(g.div(r, NA)), NB), nb)
    kk = g.floor(g.div(r, S)); k = g.sub(kk, kd)
    def at(nombre): return g.sample(arcos, g.attr(nombre), arc)
    giro = at("giro"); bz = at("base"); ida = at("arco")
    cu = g.sel(giro, cy, cx); cv = g.sel(giro, cx, cy)
    offc = g.mul(g.eq(g.mod(mv, 2.0), 0.0), 0.5)
    u = g.mul(g.add(g.mul(a, mv), offc), cu); v = g.mul(g.add(g.mul(b, mv), offc), cv)
    zc = g.prod(g.add(k, 0.5), mv, placa)
    d = g.call(dentro_g, {"U": u, "V": v, "Z": zc, "Luz": at("luz"), "Alto": at("alto"), "Grosor": at("grosor"),
                          "Fondo": at("fondo"), "Redondez": red, "Abocinado": Fb, "Erosión": E, "Escalón": esc,
                          "Semilla": g.add(seed, g.mul(ida, 7.0))}).outputs[0]
    g1 = g.store(pts, "dentro", d)
    g.marco("Superficie: algún vecino de los 6 fuera")
    dd = g.attr("dentro")
    def vecino(off, valido): return g.mul(valido, g.sample(g1, dd, g.add(idx, off)))
    vec6 = [vecino(-1.0, g.gt(a, g.sub(0.5, na))), vecino(1.0, g.lt(a, g.sub(na, 0.5))),
            vecino(g.mul(NA, -1.0), g.gt(b, g.sub(0.5, nb))), vecino(NA, g.lt(b, g.sub(nb, 0.5))),
            vecino(g.mul(S, -1.0), g.gt(kk, 0.5)), vecino(S, g.lt(kk, g.sub(NK, 1.5)))]
    g2 = g.store(g1, "superficie", g.mul(dd, g.no(g.mins(*vec6))))
    g.marco("Fusión de 3 placas en ladrillo, studs y pieza")
    sup = g.attr("superficie")
    pin = g.mod(kk, 3.0); b0 = g.sub(idx, g.mul(pin, S)); g0 = g.sub(kk, pin)
    def en(campo, nivel): return g.sample(g2, campo, g.add(b0, g.mul(S, float(nivel))))
    lleno = g.prod(en(dd, 0), en(dd, 1), en(dd, 2), g.lt(g.add(g0, 2.0), NK))
    alguna = g.maxs(en(sup, 0), en(sup, 1), en(sup, 2))
    emite = g.mul(dd, g.sel(lleno, g.mul(g.eq(pin, 0.0), alguna), sup))
    encima = g.sel(lleno, g.mul(g.lt(g.add(g0, 3.0), NK), en(dd, 3)),
                   g.mul(g.lt(g.add(kk, 1.0), NK), g.sample(g2, dd, g.add(idx, S))))
    proto = g.sel(lleno, g.sel(encima, 11.0, 10.0), g.sel(encima, 9.0, 8.0))
    g.marco("Posición en el mundo y vóxeles enterrados")
    ccx, ccy, _ = g.sep(g.sample(arcos, g.pos(), arc, 'FLOAT_VECTOR'))
    X = g.add(ccx, g.sel(giro, v, u)); Y = g.add(ccy, g.sel(giro, u, v)); Zb = g.add(bz, g.prod(k, mv, placa))
    ci = g.clamp(g.floor(g.div(g.add(X, g.mul(DX, 0.5)), cx)), 0.0, g.sub(cols, 1.0))
    cj = g.clamp(g.floor(g.div(g.add(Y, g.mul(DY, 0.5)), cy)), 0.0, g.sub(fil, 1.0))
    techo = g.mul(g.sample(niv, g.attr("nivel"), g.add(g.mul(ci, fil), cj)), esc)
    ztop = g.add(Zb, g.prod(g.sel(lleno, 3.0, 1.0), mv, placa))
    enterrado = g.lt(ztop, g.add(techo, 1e-3))
    g3 = g.stores(g2, {"proto": (proto, 'FLOAT'), "giro": (0.0, 'FLOAT'), "roca": (1.0, 'FLOAT'), "arco": (ida, 'FLOAT'),
                       "escala": (g.vec(mv, mv, mv), 'FLOAT_VECTOR')})
    g3 = g.setpos(g3, g.vec(X, Y, Zb))
    g3 = g.borrar(g3, g.bool(g.no(g.mul(emite, g.no(enterrado)))))
    g.frame = None
    g.L(g3, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_color():
    # Color de cada pieza (atributo color_lego, que los materiales leen como atributo de instancia).
    # Arena: dominante con manchas y zocalo en el tono oscuro. Roca: estratos por cota absoluta.
    g = G("DL Color")
    geo = g.inp("Geometry", 'NodeSocketGeometry')
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    esc = F("Escalón"); gest = F("Grosor de estrato (escalones)"); var = F("Variación de color"); seed = F("Semilla")
    cmin = F("Celda mínima")
    C = {n: g.inp(n, 'NodeSocketColor') for n in ("Color arena principal", "Color arena oscura", "Color arena cálida",
                                                    "Color roca principal", "Color roca clara", "Color roca oscura",
                                                    "Color roca acento")}
    P = g.pos(); _, _, z = g.sep(P)
    hv = g.n('FunctionNodeHashValue', data_type='VECTOR'); g.L(P, hv.inputs[0])
    r1 = g.rand(hv.outputs[0], g.add(seed, 79.0))
    def si(c, a_si, b_no): return g.switch('RGBA', g.bool(c), b_no, a_si)
    g.marco("Arena")
    mancha = g.ruido(g.vm('ADD', g.vm('MULTIPLY', P, (1 / 230.0, 1 / 230.0, 0.0)), semilla_vec(g, seed, 10)), 1.0, 2.0)
    ca = C["Color arena principal"]
    valle = g.mul(g.lt(g.attr("duna"), 0.1), g.gt(mancha, 0.46))
    ca = si(g.max(valle, g.gt(mancha, 0.74)), C["Color arena oscura"], ca)
    ca = si(g.lt(r1, g.mul(var, 0.22)), C["Color arena oscura"], ca)
    ca = si(g.lt(r1, g.mul(var, 0.04)), C["Color arena cálida"], ca)
    ca = si(g.lt(z, -0.01), C["Color arena oscura"], ca)
    g.marco("Roca: estratos")
    # secuencia ciclica de 6 bandas: principal, principal, clara, principal, oscura, principal (desfase por semilla)
    banda = g.floor(g.add(g.div(z, g.mul(esc, gest)), 0.001))
    desfase = g.floor(g.mul(g.m('FRACT', g.mul(seed, 0.6180339)), 6.0))   # solo de la semilla (Random Value usaria el indice)
    kb = g.mod(g.add(banda, desfase), 6.0)
    cr = si(g.eq(kb, 2.0), C["Color roca clara"], si(g.eq(kb, 4.0), C["Color roca oscura"], C["Color roca principal"]))
    cr = si(g.lt(r1, g.mul(var, 0.12)), C["Color roca clara"], cr)
    cr = si(g.gt(r1, g.sub(1.0, g.mul(var, 0.06))), C["Color roca acento"], cr)
    col = si(g.attr("roca"), cr, ca)
    geo = g.stores(geo, {"color_lego": (col, 'FLOAT_COLOR'), "unidad_lego": (g.div(0.8, cmin), 'FLOAT')})
    g.frame = None
    g.L(geo, g.out("Geometry", 'NodeSocketGeometry'))
    return g

def g_prototipos():
    # Las piezas, construidas aqui mismo a la medida de la celda: cuerpo biselado (Cube + Mesh Bevel), studs
    # (Cylinder con borde biselado), cuñas (cuerpo con la cara superior inclinada). Origen = centro de la base.
    # Dos juegos (arena y roca) en un unico Geometry to Instance: indice = proto + 16 * roca.
    g = G("DL Prototipos")
    F = lambda n: g.inp(n, 'NodeSocketFloat')
    cx = F("Celda X"); cy = F("Celda Y"); cmin = F("Celda mínima"); placa = F("Placa"); esc = F("Escalón")
    hol = F("Holgura entre piezas"); studs_on = g.inp("Mostrar studs", 'NodeSocketBool')
    mat_a = g.inp("Material arena", 'NodeSocketMaterial'); mat_r = g.inp("Material roca", 'NodeSocketMaterial')
    # las piezas ocupan su celda entera (una holgura real abriria ranuras hacia los niveles ocultos, que no se
    # instancian): la junta la dibuja el bisel superior, cuyo ancho fija "Holgura entre piezas"
    bis = g.mul(g.clamp(g.add(0.04, hol), 0.01, 0.18), cmin); lad = g.mul(placa, 3.0)

    g.marco("Stud")
    hs = g.mul(0.2125, cmin)
    cil = g.n('GeometryNodeMeshCylinder', fill_type='NGON'); cil.inputs["Vertices"].default_value = 16
    g.L(g.mul(0.3, cmin), cil.inputs["Radius"]); g.L(hs, cil.inputs["Depth"])
    stud = g.mover(cil.outputs["Mesh"], t=g.vec(0.0, 0.0, g.mul(hs, 0.5)))
    _, _, pz = g.sep(g.pos())
    bv = g.n('GeometryNodeMeshBevel'); g.L(stud, bv.inputs["Mesh"]); g.L(g.bool(g.gt(pz, g.sub(hs, 1e-4))), bv.inputs["Selection"])
    for nombre in ("Offset", "Start Left Offset", "Start Right Offset", "End Left Offset", "End Right Offset"):
        g.L(g.mul(0.035, cmin), bv.inputs[nombre])
    bv.inputs["Segments"].default_value = 2
    nz = g.sep(g.n('GeometryNodeInputNormal').outputs[0])[2]
    ss = g.n('GeometryNodeSetShadeSmooth'); g.L(bv.outputs["Mesh"], ss.inputs["Mesh"])
    g.L(g.bool(g.lt(g.abs(nz), 0.95)), ss.inputs["Selection"])
    stud = ss.outputs[0]

    def cuerpo(nx, ny, h, cuña=0):
        cu = g.n('GeometryNodeMeshCube')
        w = g.mul(cx, float(nx)); d = g.mul(cy, float(ny))
        g.L(g.vec(w, d, h), cu.inputs["Size"]); cu.inputs["Vertices Z"].default_value = 3
        # anillo intermedio al 30 % de la altura: por debajo, aristas vivas. Las juntas verticales biseladas no
        # llegan al pie de la pieza, asi que donde se juntan cuatro esquinas no queda un pozo abierto hacia abajo.
        corte = g.mul(h, -0.2)
        _, _, zv = g.sep(g.pos())
        cub = g.setpos(cu.outputs["Mesh"], g.vec(g.sep(g.pos())[0], g.sep(g.pos())[1], g.sel(g.lt(g.abs(zv), 1e-5), corte, zv)))
        b = g.n('GeometryNodeMeshBevel'); g.L(cub, b.inputs["Mesh"])
        _, _, zc = g.sep(g.pos())                          # aristas por encima del anillo (en el dominio de arista)
        g.L(g.bool(g.gt(zc, g.add(corte, 1e-4))), b.inputs["Selection"])
        for nombre in ("Offset", "Start Left Offset", "Start Right Offset", "End Left Offset", "End Right Offset"):
            g.L(bis, b.inputs[nombre])
        b.inputs["Segments"].default_value = 2
        sm = g.n('GeometryNodeSetShadeSmooth'); g.L(b.outputs["Mesh"], sm.inputs["Mesh"]); g.L(b.outputs["Edge Face"], sm.inputs["Selection"])
        geo = g.mover(sm.outputs[0], t=g.vec(0.0, 0.0, g.mul(h, 0.5)))
        if cuña:   # escala la altura de cada vertice: alto atras (-X), labio delante (+X); la esquina baja hacia +X y +Y
            x, y, z = g.sep(g.pos())
            xn = g.clamp(g.div(g.add(x, g.mul(w, 0.5)), w), 0.0, 1.0)
            if cuña == 2: xn = g.max(xn, g.clamp(g.div(g.add(y, g.mul(d, 0.5)), d), 0.0, 1.0))
            labio = g.min(g.mul(h, 0.25), g.mul(placa, 0.5))
            H = g.sub(h, g.mul(g.sub(h, labio), xn))
            geo = g.setpos(geo, g.vec(x, y, g.mul(z, g.div(H, h))))
        return geo
    def studs(nx, ny, h):
        if nx == 1 and ny == 1: puntos = g.points(1)
        else:
            gr = g.n('GeometryNodeMeshGrid'); gr.inputs["Vertices X"].default_value = nx; gr.inputs["Vertices Y"].default_value = ny
            g.L(g.mul(cx, float(nx - 1)), gr.inputs["Size X"]); g.L(g.mul(cy, float(ny - 1)), gr.inputs["Size Y"])
            puntos = gr.outputs[0]
        io = g.n('GeometryNodeInstanceOnPoints'); g.L(puntos, io.inputs["Points"]); g.L(stud, io.inputs["Instance"])
        re = g.n('GeometryNodeRealizeInstances'); g.L(io.outputs[0], re.inputs[0])
        return g.switch('GEOMETRY', studs_on, None, g.mover(re.outputs[0], t=g.vec(0.0, 0.0, h)))
    def pieza(nx, ny, h, con_studs=True, t=None):
        geo = g.join(cuerpo(nx, ny, h), studs(nx, ny, h)) if con_studs else cuerpo(nx, ny, h)
        return g.mover(geo, t=t) if t is not None else geo

    tapa_g = g.n('GeometryNodeMeshGrid'); tapa_g.inputs["Vertices X"].default_value = 2; tapa_g.inputs["Vertices Y"].default_value = 2
    g.L(cx, tapa_g.inputs["Size X"]); g.L(cy, tapa_g.inputs["Size Y"]); tapa = tapa_g.outputs[0]
    g.marco("Prototipos (orden = índice de instancia)")
    protos = [
        pieza(1, 1, esc), pieza(2, 1, esc), pieza(2, 2, esc), pieza(4, 2, esc),        # 0-3 cimas 1x1, 1x2, 2x2, 2x4
        pieza(1, 1, esc, False), pieza(2, 1, esc, False),                               # 4-5 laterales sin studs
        cuerpo(1, 1, esc, 1), cuerpo(1, 1, esc, 2),                                     # 6-7 cuña recta y de esquina
        pieza(1, 1, placa), pieza(1, 1, placa, False),                                  # 8-9 arco: placa 1x1
        pieza(1, 1, lad), pieza(1, 1, lad, False),                                      # 10-11 arco: ladrillo 1x1
        pieza(1, 1, lad),                                                               # 12 roca suelta pequeña
        g.join(pieza(2, 2, lad), pieza(2, 1, lad, t=g.vec(0.0, g.mul(cy, -0.5), lad))),  # 13 roca suelta mediana
        g.join(pieza(2, 2, lad), pieza(2, 1, lad, t=g.vec(0.0, g.mul(cy, -0.5), lad)),   # 14 roca suelta grande
               pieza(1, 1, lad, t=g.vec(g.mul(cx, -0.5), g.mul(cy, -0.5), g.mul(lad, 2.0)))),
        tapa,                                                                           # 15 tapa del fondo
    ]
    assert len(protos) == NPROTO
    gti = g.n('GeometryNodeGeometryToInstance')
    juegos = []
    for mat in (mat_a, mat_r):
        lista = []
        for p in protos:
            sm = g.n('GeometryNodeSetMaterial'); g.L(p, sm.inputs["Geometry"]); g.L(mat, sm.inputs["Material"])
            lista.append(sm.outputs[0])
        juegos.append(lista)
    for s in reversed(juegos[0] + juegos[1]):   # orden inverso: la referencia 0 es el ultimo enlace (CLAUDE.md)
        g.L(s, gti.inputs[0])
    g.frame = None
    g.L(gti.outputs[0], g.out("Instancias", 'NodeSocketGeometry'))
    return g

# ---------- grupo principal ----------
LEEME = """DESIERTO LEGO (Geometry Nodes, no destructivo)

Todo el terreno sale de este grupo: no hay mallas guardadas. Las piezas
(ladrillos biselados con studs, cuñas, placas) se construyen en
"DL Prototipos" a la medida de la celda y se instancian (nada se realiza).

USO
- Dimensión X/Y: tamaño del terreno en unidades de Blender.
- Resolución X/Y: número de celdas (studs). Pieza = Dimensión / Resolución.
  Para editar con fluidez sube "Submuestreo en el visor" (2-4): solo afecta
  a la vista 3D; el render usa siempre la resolución completa.
- Altura de escalón: niveles del relieve en placas (3 = ladrillo).
- Semilla: otra variante del mismo desierto.
- Dunas: tipo, altura, escala (longitud de onda), viento, asimetría
  (cara de avalancha), agudeza y sinuosidad. Colinas: relieve de fondo.
- Erosión: pasadas de erosión térmica, talud, cárcavas y limpieza.
- Rocas: mesetas con gradas y estratos de color, más rocas sueltas.
- Arcos: densidad, máximo, luz, altura, grosor, profundidad, redondez,
  abocinado, erosión y pedestal. La abertura nunca se cierra: el grosor
  se limita a 0.3 x min(luz, altura) y la erosión solo actúa por fuera.
- Materiales: "Arena LEGO" y "Roca LEGO" leen el color de cada pieza del
  atributo de instancia color_lego (Attribute > Instancer).

ETAPAS
1 Rejilla > 2 Relieve > 3 Erosión > 4 Arcos (colocación, terreno)
> 5 Niveles > 6 Cimas, laterales, rocas sueltas, vóxeles de arco
> 7 Color > 8 Instancias.

RENDIMIENTO (medido con RTX 4060, Blender 5.2)
250 x 250 celdas: ~0.1 s por cambio y ~113 000 instancias
(62 500 son tapas planas que cierran el fondo de las juntas).
500 x 500: ~0.3 s (~450 000). 1024 x 1024: ~1.5 s (~1 900 000).
Con resoluciones altas sube el submuestreo del visor mientras ajustas.
"""

def g_principal():
    vec = g_vecinos(); perfil = g_perfil()
    sub = dict(rejilla=g_rejilla(), relieve=g_relieve(perfil), erosion=g_erosion(vec), colocar=g_arcos_colocacion(),
               terreno=g_arcos_terreno(), niveles=g_niveles(vec), cimas=g_cimas(), laterales=g_laterales(),
               voxeles=g_arcos_voxeles(g_arco_dentro()), color=g_color(), protos=g_prototipos())
    for x in list(sub.values()) + [vec, perfil]: ordenar(x.t)
    g = G("Desierto LEGO", modificador=True)
    g.t.description = "Terreno desértico LEGO procedimental: dunas, colinas, mesetas, rocas sueltas y arcos naturales."
    paneles = {p: g.t.interface.new_panel(p) for p in DP.PANELES}
    pal = DP.paleta(); P = {}
    tipos = {"INT": 'NodeSocketInt', "FLOAT": 'NodeSocketFloat', "FACTOR": 'NodeSocketFloat', "BOOL": 'NodeSocketBool',
             "MENU": 'NodeSocketMenu', "COLOR": 'NodeSocketColor', "MATERIAL": 'NodeSocketMaterial'}
    for clave, nombre, tipo, defecto, lo, hi, panel, desc in DP.PARAMS:
        d = defecto
        if tipo == "COLOR": d = tuple(pal[defecto])
        elif tipo == "MATERIAL": d = bpy.data.materials[defecto]
        elif tipo == "MENU": d = None
        P[nombre] = g.inp(nombre, tipos[tipo], d, lo, hi, paneles[panel], desc, 'FACTOR' if tipo == "FACTOR" else None)
    salida = g.out("Geometría", 'NodeSocketGeometry')
    def pasar(grupo, extra):   # enlaza cada entrada del subgrupo con el valor calculado o con la entrada del mismo nombre
        ins = {}
        for it in grupo.t.interface.items_tree:
            if it.item_type == 'SOCKET' and it.in_out == 'INPUT':
                if it.name in extra: ins[it.name] = extra[it.name]
                elif it.name in P: ins[it.name] = P[it.name]
                else: raise KeyError(f"{grupo.t.name}: entrada sin origen '{it.name}'")
        return g.call(grupo, ins)

    g.marco("1 · Rejilla de celdas (un stud por celda)")
    rj = pasar(sub["rejilla"], {}); R = {s.name: s for s in rj.outputs}
    comun = {k: R[k] for k in ("Columnas", "Filas", "Celda X", "Celda Y", "Celda mínima", "Placa", "Escalón")}
    g.marco("2 · Relieve: dunas, colinas y mesetas")
    ms = g.n('GeometryNodeMenuSwitch', data_type='INT')
    ms.enum_items[0].name = DP.TIPOS_DUNA[0]; ms.enum_items[1].name = DP.TIPOS_DUNA[1]; ms.enum_items.new(DP.TIPOS_DUNA[2])
    for i, nombre in enumerate(DP.TIPOS_DUNA): ms.inputs[nombre].default_value = i
    g.L(P["Tipo de duna"], ms.inputs["Menu"])
    rel = pasar(sub["relieve"], dict(comun, Geometry=R["Rejilla"], Tipo=ms.outputs[0]))
    g.marco("3 · Erosión")
    ero = pasar(sub["erosion"], dict(comun, Geometry=rel.outputs[0], Iteraciones=P["Iteraciones de erosión"],
                                     **{"Talud (escalones)": P["Talud máximo (escalones)"]}))
    g.marco("4 · Arcos: colocación y cauce/pedestal en el terreno")
    col = pasar(sub["colocar"], dict(comun, Rejilla=ero.outputs[0]))
    arcos = col.outputs["Arcos"]; narc = col.outputs["Número de arcos"]
    ter = pasar(sub["terreno"], dict(comun, Rejilla=ero.outputs[0], Arcos=arcos, **{"Número de arcos": narc}))
    g.marco("5 · Niveles, limpieza y pendientes")
    niv = pasar(sub["niveles"], dict(comun, Geometry=ter.outputs[0]))
    g.marco("6 · Piezas: cimas, laterales, rocas sueltas y vóxeles de arco")
    ci = pasar(sub["cimas"], dict(comun, Geometry=niv.outputs[0]))
    la = pasar(sub["laterales"], dict(comun, Geometry=niv.outputs[0]))
    vx = pasar(sub["voxeles"], dict(comun, Arcos=arcos, Niveles=niv.outputs[0], **{"Número de arcos": narc}))
    puntos = g.join(ci.outputs["Cimas"], ci.outputs["Rocas sueltas"], ci.outputs["Tapas"], la.outputs[0], vx.outputs[0])
    g.marco("7 · Color por pieza")
    co = pasar(sub["color"], dict(comun, Geometry=puntos))
    g.marco("8 · Prototipos e instancias")
    pr = pasar(sub["protos"], comun)
    io = g.n('GeometryNodeInstanceOnPoints')
    g.L(co.outputs[0], io.inputs["Points"]); g.L(pr.outputs[0], io.inputs["Instance"])
    io.inputs["Pick Instance"].default_value = True
    g.L(g.add(g.attr("proto"), g.mul(g.attr("roca"), float(NPROTO))), io.inputs["Instance Index"])
    g.L(g.vec(0.0, 0.0, g.attr("giro")), io.inputs["Rotation"])
    g.L(g.attr("escala", 'FLOAT_VECTOR'), io.inputs["Scale"])
    g.frame = None
    g.L(io.outputs[0], salida)
    # el menu toma sus opciones del Menu Switch enlazado: el valor por defecto se pone despues de enlazar
    for it in g.t.interface.items_tree:
        if it.item_type == 'SOCKET' and it.name == "Tipo de duna": it.default_value = DP.TIPOS_DUNA[0]
    ordenar(g.t)
    txt = bpy.data.texts.get("LEEME_Desierto") or bpy.data.texts.new("LEEME_Desierto")
    txt.clear(); txt.write(LEEME)
    nota = g.t.nodes.new('NodeFrame'); nota.label = "Notas de uso"; nota.text = txt; nota.shrink = False
    nota.label_size = 32; nota.width = 900; nota.height = 1100
    xs = [n.location_absolute[0] for n in g.t.nodes if n.bl_idname != 'NodeFrame']
    nota.location_absolute = (min(xs) - 1100, 600)
    return g

# ---------- disposicion de nodos ----------
def ordenar(t):
    # Columnas por profundidad (camino mas largo desde las entradas) y una franja horizontal por marco
    nodos = [n for n in t.nodes if n.bl_idname != 'NodeFrame']
    previos = {n.name: set() for n in nodos}
    for l in t.links:
        if l.to_node.name in previos and l.from_node.name in previos: previos[l.to_node.name].add(l.from_node.name)
    prof = {}
    for n in nodos:
        pila = [n.name]
        while pila:
            x = pila[-1]
            if x in prof: pila.pop(); continue
            pend = [p for p in previos[x] if p not in prof]
            if pend: pila.extend(pend); continue
            prof[x] = 1 + max((prof[p] for p in previos[x]), default=-1)
            pila.pop()
    marcos = [None] + [f for f in t.nodes if f.bl_idname == 'NodeFrame']
    y0 = 0.0
    for f in marcos:
        grupo = [n for n in nodos if n.parent == f]
        if not grupo: continue
        cols = {}
        for n in grupo: cols.setdefault(prof[n.name], []).append(n)
        alto_max = 0.0
        for c, lista in cols.items():
            y = y0
            for n in lista:
                n.location_absolute = (c * 260.0, y)
                h = 60 + 22 * (sum(1 for s in n.inputs if s.enabled and not s.hide) + sum(1 for s in n.outputs if s.enabled))
                y -= h + 30
            alto_max = max(alto_max, y0 - y)
        y0 -= alto_max + 200

# ---------- materiales ----------
def material(nombre, rugosidad, polvo):
    real, _ = LR.crear_realista()
    m = bpy.data.materials.new(nombre)
    if m.node_tree is None: m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); s = LR.S(nt)
    col = s.n('ShaderNodeAttribute', -700, 200, attribute_type='INSTANCER', attribute_name='color_lego')
    uni = s.n('ShaderNodeAttribute', -700, -50, attribute_type='INSTANCER', attribute_name='unidad_lego')
    geo = s.n('ShaderNodeNewGeometry', -700, -300)
    gr = s.n('ShaderNodeGroup', -350, 0, node_tree=real)
    s.L(col.outputs["Color"], gr.inputs["Color"]); s.L(uni.outputs["Fac"], gr.inputs["Unidad"])
    s.L(geo.outputs["Normal"], gr.inputs["Normal"])
    gr.inputs["Logos"].default_value = 0.0          # la textura de logos va en la rejilla de la ciudad (stud 0.8)
    gr.inputs["Rugosidad"].default_value = rugosidad; gr.inputs["Polvo"].default_value = polvo
    out = s.n('ShaderNodeOutputMaterial', 0, 0); s.L(gr.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (0.7, 0.55, 0.3, 1.0)
    return m

# ---------- escena ----------
def escena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.name = "Desierto"
    material("Arena LEGO", 0.34, 1.2); material("Roca LEGO", 0.32, 1.5)
    g = g_principal()
    me = bpy.data.meshes.new("Desierto_LEGO")
    ob = bpy.data.objects.new("Desierto_LEGO", me); sc.collection.objects.link(ob)
    mod = ob.modifiers.new("Desierto LEGO", 'NODES'); mod.node_group = g.t
    # luz y render (EEVEE): cielo HDRI CC0 de la ciudad, mas un sol bajo para marcar los escalones
    LR.iluminacion(sc, fuerza=0.35)
    sc.world.sun_threshold = 1000.0                 # el sol del HDRI no se extrae: las sombras las da el sol de la escena
    nt = sc.world.node_tree; bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tinte = nt.nodes.new('ShaderNodeMix'); tinte.data_type = 'RGBA'; tinte.blend_type = 'MULTIPLY'
    tinte.inputs["Factor"].default_value = 0.7; tinte.inputs["B"].default_value = (1.0, 0.86, 0.72, 1.0)
    nt.links.new(bg.inputs["Color"].links[0].from_socket, tinte.inputs["A"]); nt.links.new(tinte.outputs["Result"], bg.inputs["Color"])
    sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", 'SUN')); sc.collection.objects.link(sol)
    sol.data.energy = 3.0; sol.data.angle = math.radians(1.2); sol.data.color = (1.0, 0.90, 0.76)
    # sol bajo desde barlovento (viento por defecto): las caras de avalancha quedan en sombra y las crestas se leen
    viento = math.radians(DP.POR_CLAVE["direccion_viento"][3] + 25.0); elev = math.radians(34.0)
    d = Vector((math.cos(viento) * math.cos(elev), math.sin(viento) * math.cos(elev), -math.sin(elev)))
    sol.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.look = 'AgX - Punchy'          # conserva la saturacion de los naranjas de la roca
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    for nombre in ("Cámara_Previa", "Cámara_General"):
        cam = bpy.data.objects.new(nombre, bpy.data.cameras.new(nombre)); sc.collection.objects.link(cam)
        cam.data.lens = 35; cam.data.clip_start = 0.5; cam.data.clip_end = 6000
    sc.camera = bpy.data.objects["Cámara_Previa"]
    return sc, ob

if __name__ == "__main__":
    sc, ob = escena()
    import previa_desierto_v3 as PV
    PV.colocar_camaras(sc, ob)
    os.makedirs(DESERT + "/presets", exist_ok=True)
    json.dump(DP.por_defecto(), open(DESERT + "/presets/por_defecto.json", "w"), indent=2, ensure_ascii=False)
    json.dump(DP.esquema(), open(DESERT + "/presets/esquema.json", "w"), indent=2, ensure_ascii=False)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("GUARDADO", OUT)
