# Version realista de la ciudad (EEVEE): shader "LEGO realista" comun a las tres fuentes, piezas del generador con
# bisel, suelo de baseplates y carreteras LDraw, cielo HDRI y preset de animacion 1080p.
# Genera archivos nuevos (los originales no se tocan):
#   Nitro_realista.blend, Modulares_OMR_realista.blend, Piezas_realista.blend (piezas con bisel y placas de suelo,
#   importadas en un archivo limpio) y Ciudad_realista.blend (enlaza Nitro y modulares, añade las piezas)
# Uso: blender -b -P ~/blender/buildings/scripts/ciudad_realista.py [-- nitro modulares piezas ciudad]   (por defecto, todos)
import bpy, sys, os, math, addon_utils
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import lego_realista as LR

B = os.path.expanduser("~/blender/buildings")
LDRAW = os.path.expanduser("~/ldraw")
LDU = 0.04
PASOS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["nitro", "modulares", "piezas", "ciudad"]
SUELO = ("44336p01", "44341p01", "44342p01", "44343p01", "3811")   # recta, te, curva, cruce, baseplate
COLOR_SUELO = {"3811": "71"}                                        # lotes: Light Bluish Grey; calzada: 72

def guardar(nombre):
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.ops.wm.save_as_mainfile(filepath=f"{B}/{nombre}", relative_remap=True)
    print("GUARDADO", nombre)

# ---------- 1. Nitro y 2. biblioteca de modulares ----------
def paso_nitro():
    bpy.ops.wm.open_mainfile(filepath=f"{B}/Nitro.blend")
    print("NITRO grupos", LR.aplicar_mecabricks(0.1))      # piezas de Mecabricks en mm bajo un Empty de escala 0.1
    guardar("Nitro_realista.blend")

def paso_modulares():
    bpy.ops.wm.open_mainfile(filepath=f"{B}/Modulares_OMR.blend")
    print("MODULARES", LR.aplicar_ldraw(1.0))
    guardar("Modulares_OMR_realista.blend")

# ---------- piezas LDraw ----------
ESPECIAL = {"60601": (48, 0), "60602": (72, 0), "60616a": (144, -32)}   # igual que edificios_gn.py

def importar(pid, bisel=True, normalizar=True, color='4'):
    # Igual que importar() de edificios_gn.py (origen en la base, 1 LDU = 0.04, frente -Y, indice 1 = caras de pendiente)
    # pero con el bisel del importador. normalizar=False deja el origen LDraw (cara superior de los baseplates).
    antes = set(bpy.data.objects)
    # realScale explicito: ImportLDraw guarda las ultimas opciones usadas (ImportLDrawPreferences.ini)
    bpy.ops.import_scene.importldraw(filepath=f"{LDRAW}/parts/{pid}.dat", ldrawPath=LDRAW, positionOnGround=False, realScale=1.0,
                                     bevelEdges=bisel, addEnvironment=False, positionCamera=False, importCameras=False,
                                     useLogoStuds=False, look='normal', resPrims='Standard', addGaps=False,
                                     defaultColour=color)   # color de las partes "16" (el importador usa rojo)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    src = next(o for o in nuevos if o.type == 'MESH')
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    me.transform(Matrix.Scale(LDU / 0.0004, 4) @ src.matrix_world)
    if normalizar:
        zs, xs = ESPECIAL.get(pid, (None, 0))
        dz = zs * LDU if zs is not None else -min(v.co.z for v in me.vertices)
        me.transform(Matrix.Translation((xs * LDU, 0, dz)))
        pend = [bool(me.materials) and me.materials[p.material_index].name.endswith("_s") for p in me.polygons]
        me.materials.clear()
        me.polygons.foreach_set("material_index", [int(s) for s in pend])
    for o in nuevos: bpy.data.objects.remove(o)
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'      # ImportLDraw cambia el motor a Cycles
    return me

def paso_piezas():
    # En un archivo limpio: si se importa dentro de la ciudad, ImportLDraw reutiliza las mallas del mismo nombre de la
    # biblioteca enlazada de modulares (ya a escala 100) y las piezas salen 100 veces mas grandes.
    bpy.ops.wm.read_factory_settings(use_empty=True); addon_utils.enable("io_scene_importldraw")
    with bpy.data.libraries.load(f"{B}/Edificios_GN_marquesina_v2.blend") as (src, dst):
        pids = [n[3:] for n in src.objects if n.startswith("LD_")]
    for pid in pids:
        me = importar(pid); me.name = "LDB_" + pid; me.use_fake_user = True
    for pid in SUELO:
        me = importar(pid, normalizar=False, color=COLOR_SUELO.get(pid, "72")); me.name = "Suelo_" + pid; me.use_fake_user = True
    print("PIEZAS", len(pids), "+ suelo", len(SUELO))
    guardar("Piezas_realista.blend")

def cargar_mallas(nombres):
    with bpy.data.libraries.load(f"{B}/Piezas_realista.blend", link=False) as (src, dst):
        dst.meshes = [n for n in nombres if n in src.meshes]
    return {m.name: m for m in dst.meshes}

def rebiselar():
    # Las piezas LD_* del generador se importaron sin bisel: sin juntas, las paredes parecen planchas lisas.
    # Se sustituye su malla; Object Info del grupo "Edificio LEGO" toma la nueva geometria sin tocar el grupo.
    obs = [o for o in bpy.data.collections["Piezas LDraw"].objects if o.name.startswith("LD_")]
    mallas = cargar_mallas(["LDB_" + o.name[3:] for o in obs])
    for ob in obs: ob.data = mallas["LDB_" + ob.name[3:]]
    return len(obs)

# ---------- 3. ciudad ----------
PITCH_X, PITCH_Y, MEDIA = 102.4, 76.8, 12.8     # de ciudad_completa.py: manzanas 96x64, calles de 32 studs
CALLES_X = [-153.6, -51.2, 51.2, 153.6]         # centros de las calles verticales
CALLES_Y = [-115.2, -38.4, 38.4, 115.2]         # centros de las calles horizontales
# aberturas de cada placa sin girar (direcciones por las que sigue la calzada)
ABRE = {"44343p01": {(1, 0), (-1, 0), (0, 1), (0, -1)}, "44341p01": {(0, 1), (0, -1), (1, 0)}, "44342p01": {(-1, 0), (0, -1)}}

def girar(d, ang):
    c, s = round(math.cos(ang)), round(math.sin(ang)); return (c * d[0] - s * d[1], s * d[0] + c * d[1])

def suelo_lego(col):
    cargadas = cargar_mallas(["Suelo_" + p for p in SUELO])
    mallas = {p: cargadas["Suelo_" + p] for p in SUELO}
    hechos = []
    def poner(pid, x, y, ang):
        ob = bpy.data.objects.new(f"Calle_{pid}_{len(hechos):03d}", mallas[pid]); col.objects.link(ob)
        ob.location = (x, y, 0.0); ob.rotation_euler = (0, 0, ang); hechos.append(ob)
    for x in CALLES_X:                       # cruces, tes y curvas
        for y in CALLES_Y:
            abre = {d for d, ok in (((1, 0), x < CALLES_X[-1]), ((-1, 0), x > CALLES_X[0]), ((0, 1), y < CALLES_Y[-1]), ((0, -1), y > CALLES_Y[0])) if ok}
            pid = {4: "44343p01", 3: "44341p01", 2: "44342p01"}[len(abre)]
            ang = next(a for a in (0, math.pi / 2, math.pi, -math.pi / 2) if {girar(d, a) for d in ABRE[pid]} == abre)
            poner(pid, x, y, ang)
    for y in CALLES_Y:                       # rectas a lo largo de X (girada 90: la calzada va en Y sin girar)
        for x0, x1 in zip(CALLES_X, CALLES_X[1:]):
            for k in range(1, round((x1 - x0) / (2 * MEDIA))): poner("44336p01", x0 + 2 * MEDIA * k, y, math.pi / 2)
    for x in CALLES_X:
        for y0, y1 in zip(CALLES_Y, CALLES_Y[1:]):
            for k in range(1, round((y1 - y0) / (2 * MEDIA))): poner("44336p01", x, y0 + 2 * MEDIA * k, 0.0)
    # baseplates en los lotes generados (sustituyen a los zocalos lisos)
    for pad in [o for o in bpy.data.objects if o.name.startswith("Pad_") and not o.library]:
        ob = bpy.data.objects.new("Base_" + pad.name[4:], mallas["3811"])
        for c in pad.users_collection: c.objects.link(ob)
        ob.location = pad.location; bpy.data.objects.remove(pad); hechos.append(ob)
    # manzana B2: baseplates en toda la manzana; los studs quedan dentro de las placas de Nitrody City, como en un
    # montaje real. El zocalo liso baja un poco para no coincidir con su cara superior.
    b2 = bpy.data.objects["B2_Plaza_Pad"]; b2.location.z = -0.005
    for i, (cx, cy) in enumerate((x, y) for x in (-25.6, 0.0, 25.6) for y in (-12.8, 12.8)):
        ob = bpy.data.objects.new(f"Base_B2_{i}", mallas["3811"]); b2.users_collection[0].objects.link(ob)
        ob.location = (cx, cy, 0.0); hechos.append(ob)
    bpy.data.objects["Suelo"].location.z = -0.2      # debajo de los baseplates (miden 0.16 de grueso)
    print("SUELO piezas", len(hechos))

def suelo_mate(col, rugosidad=0.38):
    # Los baseplates y la calzada son mas mates que un ladrillo: con la rugosidad normal la calle hace de espejo.
    # Sus materiales pasan a una copia del grupo base con mas rugosidad (los demas no cambian).
    mats = {ms.material for o in col.all_objects if o.type == 'MESH' for ms in o.material_slots if ms.material}
    mats |= {ms.material for o in bpy.data.objects if o.name.startswith("Base_") for ms in o.material_slots if ms.material}
    copias = {}
    for m in mats:
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree and n.node_tree.name.startswith("Lego Standard") and not n.node_tree.name.endswith(" mate"):
                g = copias.get(n.node_tree.name)
                if not g:
                    g = n.node_tree.copy(); g.name = n.node_tree.name + " mate"; copias[n.node_tree.name] = g
                    for r in g.nodes:
                        if r.type == 'GROUP' and r.node_tree.name == "LEGO realista": r.inputs["Rugosidad"].default_value = rugosidad
                n.node_tree = g
    print("MATE", len(mats), "materiales")

def paso_ciudad():
    bpy.ops.wm.open_mainfile(filepath=f"{B}/Ciudad_completa.blend")
    addon_utils.enable("io_scene_importldraw")
    for lib, nuevo in (("Nitro.blend", "//Nitro_realista.blend"), ("Modulares_OMR.blend", "//Modulares_OMR_realista.blend")):
        l = bpy.data.libraries[lib]; l.filepath = nuevo; l.reload()
    print("GENERADOR grupos", LR.aplicar_mecabricks(1.0))
    print("BISEL piezas", rebiselar())
    col = bpy.data.collections.get("Suelo LEGO") or bpy.data.collections.new("Suelo LEGO")
    if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
    suelo_lego(col)
    print("CALLES", LR.aplicar_ldraw(1.0))           # materiales LDraw de las placas de carretera y baseplates
    suelo_mate(col)
    sc = bpy.context.scene
    if "Sol" in bpy.data.objects: bpy.data.objects["Sol"].hide_render = True   # el sol sale del HDRI
    LR.iluminacion(sc, fuerza=1.0, giro=math.radians(140))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
    sc.render.fps = 24
    guardar("Ciudad_realista.blend")

for p in PASOS: {"nitro": paso_nitro, "modulares": paso_modulares, "piezas": paso_piezas, "ciudad": paso_ciudad}[p]()
