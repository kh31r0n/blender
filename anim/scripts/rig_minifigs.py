# Genera un rig por minifigura en Minifigures.blend (importado de Mecabricks).
# Unidades de pieza = mm de Mecabricks (las matrices de mundo llevan la escala 0.1 del Empty).
# Uso: blender -b ~/blender/anim/Minifigures.blend -P ~/blender/anim/scripts/rig_minifigs.py
#      (lee el .blend original y guarda el resultado en OUT; el original no se modifica)
import bpy, math
from mathutils import Matrix, Vector

OUT = "/home/kheiron/blender/anim/Minifigures_rig.blend"
P = lambda i: bpy.data.objects["part" if i == 0 else "part.%03d" % i]

# Indices de pieza (orden del .zmbx == part, part.001, ...)
FIGS = {
    "Barbudo":      dict(torso=4,  cadera=13, brazo_R=0,  brazo_L=2,  mano_R=1,  mano_L=3,  pierna_R=14, pierna_L=15, cabeza=31,
                         pelo=[44], bandolera=[51], adorno=[60, 61, 62]),
    "Chaleco":      dict(torso=9,  cadera=10, brazo_R=5,  brazo_L=7,  mano_R=6,  mano_L=8,  pierna_R=11, pierna_L=12, cabeza=47,
                         pelo=[42]),
    "Cicatriz":     dict(torso=27, cadera=28, brazo_R=23, brazo_L=25, mano_R=24, mano_L=26, pierna_R=29, pierna_L=30, cabeza=46,
                         pelo=[41], bandolera=[52]),
    "TunicaBlanca": dict(torso=37, cadera=22, brazo_R=33, brazo_L=35, mano_R=34, mano_L=36, pierna_R=21, pierna_L=20, cabeza=49,
                         pelo=[43], bandolera=[53], adorno=[45], faldon=[64]),
    "Panuelo":      dict(torso=32, cadera=40, brazo_R=18, brazo_L=19, mano_R=16, mano_L=17, pierna_R=39, pierna_L=38, cabeza=48,
                         pelo=[50], tocado=[55, 56, 57, 58, 59], bandolera=[54], faldon=[63]),
}
ACC_PARENT = dict(pelo="cabeza", tocado="cabeza", bandolera="torso", adorno="torso")

# Puntos de conexion de Mecabricks (mm, espacio local de pieza)
HOMBRO = Vector((6.265, 8.99, 0.0))
SPLAY = 2 * math.asin(0.088011)                  # caida fija del eje del hombro (10.1 grados)
BRAZO_CAIDO = math.radians(45)                   # en Mecabricks 0 = antebrazo al frente; 45 = brazo colgando
MUNECA_BRAZO = Vector((2.0, -3.3, 7.7))          # en el brazo
MUNECA_MANO = Vector((0.0, 1.119, -3.706))       # en la mano
INCL_MANO = -2 * math.atan2(-0.13105, 0.991376)  # inclinacion fija de la mano (15.06 grados)
CADERA_PIERNA = Vector((4.0, -4.8, 0.0))
CUELLO = Vector((0.0, 12.8, 0.0))
TOPE_CABEZA = Vector((0.0, 9.6, 0.0))
SUELO = Vector((0.0, -16.0, 0.0))
R = math.radians

T = Matrix.Translation
def rot(axis, ang): return Matrix.Rotation(ang, 4, axis)
def axes(M):
    m = M.to_3x3()
    return [m.col[i].normalized() for i in range(3)]
def frame(head, x, y):
    y = y.normalized(); z = x.cross(y).normalized(); x = y.cross(z).normalized()
    M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = head; return M
def bbox_center(o, M):
    pts = [M @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / 8

sc = bpy.context.scene
root_coll = bpy.data.collections["_The Chosen_ Custom Minifigures"]

# ---------- widgets ----------
wgt_coll = bpy.data.collections.new("WGT_Minifig"); sc.collection.children.link(wgt_coll)
def widget(name, verts, edges):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, edges, []); ob = bpy.data.objects.new(name, me)
    wgt_coll.objects.link(ob); return ob
def circle(plane, n=32, r=1.0):
    v = []
    for i in range(n):
        a = 2 * math.pi * i / n; c, s = r * math.cos(a), r * math.sin(a)
        v.append({"XZ": (c, 0, s), "YZ": (0, c, s), "XY": (c, s, 0)}[plane])
    return v, [(i, (i + 1) % n) for i in range(n)]
W = {}
for pl in ("XZ", "YZ"):
    W[pl] = widget("WGT_circulo_" + pl, *circle(pl))
v, e = circle("XY"); k = len(v)
v += [(0, -1.0, 0), (0, -1.45, 0), (-0.15, -1.25, 0), (0.15, -1.25, 0)]
e += [(k, k + 1), (k + 1, k + 2), (k + 1, k + 3)]
W["raiz"] = widget("WGT_raiz", v, e)
cv = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
ce = [(a, b) for a in range(8) for b in range(a + 1, 8) if sum(cv[a][i] != cv[b][i] for i in range(3)) == 1]
W["caja"] = widget("WGT_caja", cv, ce)
dv = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
W["diamante"] = widget("WGT_diamante", dv, [(a, b) for a in range(6) for b in range(a + 1, 6) if a // 2 != b // 2])
v, e = circle("XZ", 16, 0.5); k = len(v)
v += [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]
e += [(k, k + 1), (k + 2, k + 3), (k + 4, k + 5)]
W["ejes"] = widget("WGT_ejes", v, e)
wgt_coll.hide_render = True
sc.view_layers[0].layer_collection.children[wgt_coll.name].exclude = True

COLOR = {"C": "THEME09", "L": "THEME04", "R": "THEME01", "ACC": "THEME03", "SOCK": "THEME06"}
COLLS = ["Principal", "Torso_Cabeza", "Brazos", "Piernas", "Accesorios", "Agarres"]

def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return t * t * (3 - 2 * t)

empty = bpy.data.objects["Empty"]
informe = []

for fig, d in FIGS.items():
    orig = {}
    def reg(key, idx): orig[key] = P(idx).matrix_world.copy()
    for key in ("torso", "cadera", "brazo_R", "brazo_L", "mano_R", "mano_L", "pierna_R", "pierna_L", "cabeza"):
        reg(key, d[key])
    MT = orig["torso"]
    rel_hips = MT.inverted() @ orig["cadera"]
    assert rel_hips.translation.length < 1e-3 and rel_hips.to_quaternion().angle < 1e-3, (fig, "torso y cadera no coinciden")

    # ---------- pose neutra de cada pieza (mundo) ----------
    neu = {"torso": MT, "cadera": orig["cadera"]}; neu0 = {}
    for s, sg in (("R", -1), ("L", 1)):
        neu["pierna_" + s] = orig["cadera"] @ T(Vector((sg * CADERA_PIERNA.x, CADERA_PIERNA.y, 0)))
        neu0["brazo_" + s] = MT @ T(Vector((sg * HOMBRO.x, HOMBRO.y, 0))) @ rot("Z", sg * SPLAY)
        neu["brazo_" + s] = neu0["brazo_" + s] @ rot("X", BRAZO_CAIDO)
        neu["mano_" + s] = (neu["brazo_" + s] @ T(Vector((sg * MUNECA_BRAZO.x, MUNECA_BRAZO.y, MUNECA_BRAZO.z)))
                            @ rot("X", INCL_MANO) @ T(-MUNECA_MANO))
        assert (orig["pierna_" + s].inverted() @ orig["cadera"]).translation.x * sg < 0, (fig, "lado pierna", s)
    rel_head = MT.inverted() @ orig["cabeza"]
    fz = rel_head.to_3x3() @ Vector((0, 0, 1))
    yaw = math.atan2(fz.x, fz.z)              # la cara mira donde ya miraba; solo se quita inclinacion
    neu["cabeza"] = MT @ T(CUELLO) @ rot("Y", yaw)

    acc_parts = {}
    for acc, par in ACC_PARENT.items():
        for idx in d.get(acc, []):
            key = f"{acc}_{idx}"; reg(key, idx); acc_parts.setdefault(acc, []).append(key)
            neu[key] = neu[par] @ orig[par].inverted() @ orig[key]

    # ---------- coloca las piezas en pose neutra ----------
    part_obj = {}
    for key, M in neu.items():
        idx = d[key] if key in d else int(key.rsplit("_", 1)[1])
        o = P(idx); part_obj[key] = o
        o.parent = None; o.matrix_world = M
    skirts = [P(i) for i in d.get("faldon", [])]
    for o in skirts:
        M = o.matrix_world.copy(); o.parent = None; o.matrix_world = M

    # ---------- armature ----------
    side, up, front = axes(MT)
    ground = MT @ SUELO
    rig_mat = frame(ground, side, -front)
    arm = bpy.data.armatures.new("RIG_" + fig); rig = bpy.data.objects.new("RIG_" + fig, arm)
    coll = bpy.data.collections.new(fig); root_coll.children.link(coll); coll.objects.link(rig)
    rig.matrix_world = rig_mat
    arm.display_type = "OCTAHEDRAL"; rig.show_in_front = True
    for c in COLLS: arm.collections.new(c)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    rinv = rig_mat.inverted()
    specs = {}   # nombre -> (padre, coleccion, color, pieza_motriz)
    def bone(name, parent, M_world, length, bcoll, color, driver=None):
        eb = arm.edit_bones.new(name); eb.head = (0, 0, 0); eb.tail = (0, length, 0)
        eb.matrix = rinv @ M_world; eb.length = length
        if parent: eb.parent = arm.edit_bones[parent]
        eb.use_deform = False
        arm.collections[bcoll].assign(eb); eb.color.palette = COLOR[color]
        specs[name] = (parent, driver)
    waist = MT.translation
    bone("raiz", None, frame(ground, side, -front), 1.4, "Principal", "C")
    bone("cuerpo", "raiz", frame(waist, side, up), 0.5, "Principal", "C", "cadera")
    bone("torso", "cuerpo", frame(waist, side, up), 1.28, "Torso_Cabeza", "C", "torso")
    bone("cabeza", "torso", frame(MT @ CUELLO, side, up), 0.96, "Torso_Cabeza", "C", "cabeza")
    for s in ("R", "L"):
        A = neu["brazo_" + s]; ax, ay, az = axes(A)
        _, ay0, _ = axes(neu0["brazo_" + s])      # hueso vertical (con la caida de 10 grados)
        bone(f"brazo.{s}", "torso", frame(A.translation, ax, -ay0), 0.7, "Brazos", s, "brazo_" + s)
        sg = -1 if s == "R" else 1
        wrist = A @ Vector((sg * MUNECA_BRAZO.x, MUNECA_BRAZO.y, MUNECA_BRAZO.z))
        H = neu["mano_" + s]; hx, hy, hz = axes(H)
        # centro del agarre: vertices interiores del hueco (radio < 2 mm alrededor del eje Y local)
        inner = [v.co.y for v in part_obj["mano_" + s].data.vertices if (v.co.x ** 2 + v.co.z ** 2) ** 0.5 < 2.0]
        yc = (min(inner) + max(inner)) / 2 if inner else 2.2
        grip = H @ Vector((0, yc, 0))
        bone(f"mano.{s}", f"brazo.{s}", frame(wrist, ax, az), (grip - wrist).length, "Brazos", s, "mano_" + s)
        bone(f"agarre.{s}", f"mano.{s}", frame(grip, hx, hy), 0.3, "Agarres", "SOCK")
        Lg = neu["pierna_" + s]; lx, ly, lz = axes(Lg)
        bone(f"pierna.{s}", "cuerpo", frame(Lg.translation, lx, -ly), 0.9, "Piernas", s, "pierna_" + s)
    for acc, keys in acc_parts.items():
        if acc == "pelo":
            head = neu["cabeza"] @ TOPE_CABEZA
        else:
            head = sum((bbox_center(part_obj[k], neu[k]) for k in keys), Vector()) / len(keys)
        bone(acc, ACC_PARENT[acc], frame(head, side, up), 0.3, "Accesorios", "ACC")
    if skirts:
        bone("faldon", "cuerpo", frame(waist, side, -up), 0.6, "Accesorios", "ACC")
    for n in ("faldon", "pierna.L", "pierna.R"):
        if n in arm.edit_bones and skirts: arm.edit_bones[n].use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")

    # ---------- emparenta piezas rigidas a sus huesos ----------
    owner = {"cadera": "cuerpo", "torso": "torso", "cabeza": "cabeza",
             "brazo_R": "brazo.R", "brazo_L": "brazo.L", "mano_R": "mano.R", "mano_L": "mano.L",
             "pierna_R": "pierna.R", "pierna_L": "pierna.L"}
    for acc, keys in acc_parts.items():
        for k in keys: owner[k] = acc
    nombre_pieza = {"cadera": "cadera", "torso": "torso", "cabeza": "cabeza", "brazo_R": "brazo.R", "brazo_L": "brazo.L",
                    "mano_R": "mano.R", "mano_L": "mano.L", "pierna_R": "pierna.R", "pierna_L": "pierna.L"}
    for key, o in part_obj.items():
        b = arm.bones[owner[key]]
        tail_world = rig_mat @ b.matrix_local @ T(Vector((0, b.length, 0)))
        o.parent = rig; o.parent_type = "BONE"; o.parent_bone = b.name
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = tail_world.inverted() @ neu[key]
        for c in list(o.users_collection): c.objects.unlink(o)
        coll.objects.link(o)
        if key in nombre_pieza:
            o.name = f"{fig}_{nombre_pieza[key]}"
        else:
            acc = key.rsplit("_", 1)[0]; n = len(acc_parts[acc])
            o.name = f"{fig}_{acc}" + (f"_{acc_parts[acc].index(key) + 1}" if n > 1 else "")

    # ---------- faldones flexibles ----------
    Hinv = orig["cadera"].inverted()
    for o in skirts:
        Mw = o.matrix_world.copy()
        o.parent = rig; o.matrix_parent_inverse = rig_mat.inverted(); o.matrix_basis = Mw
        gF = o.vertex_groups.new(name="faldon"); gL = o.vertex_groups.new(name="pierna.L"); gR = o.vertex_groups.new(name="pierna.R")
        for v in o.data.vertices:
            p = Hinv @ (Mw @ v.co)            # mm en espacio de cadera: x lado, y arriba
            wl = smooth(-1.5, -7.5, p.y); s = smooth(-2.5, 2.5, p.x)
            gF.add([v.index], 1 - wl, "REPLACE"); gL.add([v.index], wl * s, "REPLACE"); gR.add([v.index], wl * (1 - s), "REPLACE")
        mod = o.modifiers.new("Armature", "ARMATURE"); mod.object = rig
        for c in list(o.users_collection): c.objects.unlink(o)
        coll.objects.link(o); o.name = f"{fig}_faldon"

    # ---------- controles: formas, bloqueos y limites ----------
    def shape(pb, w, scale, trans=(0, 0, 0)):
        pb.custom_shape = W[w]; pb.use_custom_shape_bone_size = False
        pb.custom_shape_scale_xyz = scale if isinstance(scale, tuple) else (scale,) * 3
        pb.custom_shape_translation = trans
        if hasattr(pb, "custom_shape_wire_width"): pb.custom_shape_wire_width = 2.0
    def limit(pb, **lims):
        c = pb.constraints.new("LIMIT_ROTATION"); c.owner_space = "LOCAL"; c.use_transform_limit = True
        for ax, (lo, hi) in lims.items():
            setattr(c, f"use_limit_{ax}", True); setattr(c, f"min_{ax}", R(lo)); setattr(c, f"max_{ax}", R(hi))
    pose = rig.pose.bones
    for pb in pose:
        pb.rotation_mode = "XYZ"; pb.lock_scale = (True,) * 3
    pose["raiz"].lock_scale = (False,) * 3
    shape(pose["raiz"], "raiz", 1.6)
    shape(pose["cuerpo"], "caja", (0.9, 0.32, 0.75), (0, -0.25, 0))
    shape(pose["torso"], "XZ", 1.05, (0, 0.85, 0))
    shape(pose["cabeza"], "XZ", 0.9, (0, 0.5, 0))
    for n in ("torso", "cabeza"): pose[n].lock_location = (True,) * 3
    limit(pose["torso"], x=(-30, 30), y=(-60, 60), z=(-20, 20))
    limit(pose["cabeza"], x=(-35, 35), z=(-25, 25))
    for s in ("R", "L"):
        sg = -1 if s == "R" else 1
        b = pose[f"brazo.{s}"]; shape(b, "YZ", 0.38, (sg * 0.25, 0, 0)); b.lock_location = (True,) * 3
        b.lock_rotation = (False, True, False)
        # signo de "abrir": +Z aleja la punta del cuerpo?
        bb = arm.bones[f"brazo.{s}"]
        zax = bb.matrix_local.to_3x3().col[2]; yax = bb.matrix_local.to_3x3().col[1]
        outward = zax.cross(yax).x * sg > 0
        limit(b, z=(-5, 85) if outward else (-85, 5))
        m = pose[f"mano.{s}"]; shape(m, "XZ", 0.28, (0, 0.2, 0)); m.lock_location = (True,) * 3
        m.lock_rotation = (True, False, True)
        g = pose[f"agarre.{s}"]; shape(g, "ejes", 0.18)
        p = pose[f"pierna.{s}"]; shape(p, "YZ", 0.5, (sg * 0.4, 0, 0)); p.lock_location = (True,) * 3
        limit(p, y=(-45, 45), z=(-30, 30))
    for acc in list(acc_parts) + (["faldon"] if skirts else []):
        b = pose[acc]
        if acc == "faldon": shape(b, "XZ", 1.0, (0, 0.65, 0))
        else: shape(b, "diamante", 0.18)

    # ---------- pose original (desde la posicion que tenian en Mecabricks) ----------
    rest = {b.name: b.matrix_local.copy() for b in arm.bones}
    Pm = {}
    errores = []
    order = [b.name for b in arm.bones if b.parent is None]
    i = 0
    while i < len(order):
        order += [c.name for c in arm.bones[order[i]].children]; i += 1
    for name in order:
        parent, driver = specs[name]
        pb = pose[name]
        base = rest[name] if parent is None else Pm[parent] @ rest[parent].inverted() @ rest[name]
        if driver:
            delta = orig[driver] @ neu[driver].inverted()
            want = rinv @ delta @ rig_mat @ rest[name]
            basis = base.inverted() @ want
            loc, q, _ = basis.decompose()
            e = q.to_euler("XYZ")
            for ax in range(3):
                if pb.lock_rotation[ax] and abs(e[ax]) > 1e-4:
                    errores.append(f"{name} giro {'XYZ'[ax]} {math.degrees(e[ax]):.1f} grados")
                    e[ax] = 0.0
            if pb.lock_location[0] and loc.length > 1e-4:
                errores.append(f"{name} desplazado {loc.length * 10:.2f} mm"); loc = Vector()
            pb.location = loc; pb.rotation_euler = e
            basis = T(loc) @ e.to_matrix().to_4x4()
        else:
            basis = Matrix.Identity(4)
        Pm[name] = base @ basis
    # Pose original como asset de Pose Library
    rig.animation_data_create()
    for pb in pose:
        for path in ("location", "rotation_euler", "scale"):
            pb.keyframe_insert(path, frame=1, group=pb.name)
    act = rig.animation_data.action; act.name = f"Pose original {fig}"
    rig.animation_data.action = None
    act.use_fake_user = True; act.asset_mark()
    informe.append((fig, errores, math.degrees(yaw)))

assert not empty.children, "quedan piezas bajo el Empty"
bpy.data.objects.remove(empty)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
for fig, errs, yaw in informe:
    print("INFORME", fig, "| cabeza yaw %.1f" % yaw, "| ajustes:", errs or "ninguno")
