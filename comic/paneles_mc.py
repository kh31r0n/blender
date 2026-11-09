# PANELES CON MOTION CANVAS (estilo tecnico): del diseno validado (paneles.json) a motion.json (todo en fotogramas) y
# render sin interfaz con comic/motion/render.mjs. Sin bpy: lo usa el agente con el Python del sistema.
#
# motion.json (fotogramas de Motion Canvas, 0-based: el fotograma f de Blender es el f-1 de aqui):
#   {ancho, alto, fps, frames, orientacion, banda: {x, y, w, h}, paleta: {...}, icono_flujo,
#    tramos: [{inicio, fin, entra, sale}],             # banda visible (escenas seguidas con panel comparten banda)
#    paneles: [{escena, inicio, fin, titular: {palabras: [{t, f, clave}], color, bloque, grande},
#               visual: {tipo, f, ...}, cinta: {pasos: [...], activo, hechos, rapido} | null}]}
import json, os, re, subprocess, sys

COMIC = os.path.dirname(os.path.abspath(__file__))
if COMIC not in sys.path: sys.path.insert(0, COMIC)
import comic_parametros as CP

MOTION = os.path.join(COMIC, "motion")
UMBRAL_VOZ = 0.12          # envolvente (0..1) por debajo de la cual un fotograma es silencio
PAUSA_MIN = 3              # fotogramas seguidos de silencio que cuentan como pausa dentro de una linea

def silabas(texto):
    try:
        import audio_comic
        return audio_comic.silabas(texto)
    except Exception:                       # sin las dependencias del audio: grupos de vocales
        return max(1.0, len(re.findall(r"[aeiouáéíóúü]+", str(texto).lower())))

# ---------------------------------------------------------------- tiempos por palabra (estimados)
def palabras_estimadas(linea):
    """[(palabra, fotograma de Blender en que empieza)] de una linea de tiempos.json. Reparte el tramo con voz entre las
    palabras segun sus silabas (con un poco mas tras una coma o un punto) y salta las pausas que marca la envolvente."""
    pal = CP._palabras(linea.get("texto"))
    if not pal: return []
    ini, fin = int(linea["inicio"]), int(linea["fin"])
    env = list(linea.get("envolvente") or [])
    if len(env) < 2: env = [1.0] * max(1, fin - ini)
    voz = [x >= UMBRAL_VOZ for x in env]
    a = next((i for i, v in enumerate(voz) if v), 0)
    b = len(voz) - next((i for i, v in enumerate(reversed(voz)) if v), 0)
    # fotogramas con voz (sin las pausas largas de dentro): el «tiempo de habla»
    habla, k = [], a
    while k < b:
        if not voz[k]:
            j = k
            while j < b and not voz[j]: j += 1
            if j - k < PAUSA_MIN: habla.extend(range(k, j))
            k = j
        else:
            habla.append(k); k += 1
    if not habla: habla = list(range(a, max(a + 1, b)))
    pesos = [silabas(w) + (0.8 if re.search(r"[,;:.?!]$", w) else 0.0) for w in pal]
    total = sum(pesos); acum = 0.0; out = []
    for w, p in zip(pal, pesos):
        idx = min(len(habla) - 1, int(acum / total * len(habla)))
        out.append((w, ini + habla[idx])); acum += p
    return out

def palabras_escena(te):
    return [x for ln in te.get("lineas") or [] for x in palabras_estimadas(ln)]

def _coincide(a, b):
    """Misma palabra sin tildes ni mayusculas, o la misma raiz (pierdes ~ pierde, precios ~ precio)."""
    a, b = CP._norm_palabra(a), CP._norm_palabra(b)
    if not a or not b: return False
    if a == b: return True
    n = min(len(a), len(b))
    return n >= 4 and a[:n - 1] == b[:n - 1] and abs(len(a) - len(b)) <= 2

def _cifra_norm(s):
    n = CP.numero_texto(s)
    return None if n is None else abs(n[1])

# ---------------------------------------------------------------- motion.json
def banda(params):
    w, h, _ = CP.resolucion(params)
    p = float(params.get("tam_panel", 0.40))
    if params.get("orientacion") == "vertical": return dict(x=0, y=0, w=w, h=round(h * p))
    return dict(x=0, y=0, w=round(w * p * 0.95), h=h)

def construir_motion(guion, tiempos, paneles, params):
    w, h, _ = CP.resolucion(params)
    fps = int(tiempos.get("fps") or params.get("fps", 24))
    frames = int(tiempos.get("frame_fin") or tiempos["escenas"][-1]["fin"] - 1)
    tes = {te["id"]: te for te in tiempos["escenas"]}
    escenas = {e["id"]: e for e in guion["escenas"]}
    ciclo = [c["texto"] for c in guion.get("ciclo") or []]
    orden = [e["id"] for e in guion["escenas"]]
    hechos, primero_ciclo = set(), None
    for eid in orden:            # escena desde la que se ve la cinta de pasos
        e = escenas[eid]
        if (e.get("paso") or e.get("ciclo_rapido")) and primero_ciclo is None: primero_ciclo = orden.index(eid)
    salida = []
    for p in sorted(paneles, key=lambda q: orden.index(q["escena"])):
        eid = p["escena"]; e = escenas[eid]; te = tes.get(eid)
        if te is None: continue
        f0, f1 = int(te["inicio"]) - 1, int(te["fin"]) - 2          # 0-based e inclusivos
        voz = palabras_escena(te)
        # ---- titular: cada palabra cuando la dice la voz (o tras la anterior si no la dice)
        pal, ult, usadas = [], None, set()
        claves = {CP._norm_palabra(c) for c in p["titular"].get("clave") or []}
        for w_ in CP._palabras(p["titular"]["texto"]):
            i = next((i for i, (wv, fv) in enumerate(voz)
                      if i not in usadas and _coincide(w_, wv) and (ult is None or fv - 1 >= ult)), None)
            if i is not None: usadas.add(i); f = voz[i][1] - 1        # un fotograma antes de que suene
            else: f = (ult + 3) if ult is not None else f0 + 4
            f = max(f0 + 2, f if ult is None else max(f, ult + 2))
            pal.append(dict(t=w_, f=min(f, f1 - 6), clave=CP._norm_palabra(w_) in claves)); ult = f
        # ---- visual: aparece pronto (con la primera palabra del titular o al 25 % de la escena, lo que llegue antes) y
        # su accion (el contador rueda, las barras crecen, la aguja gira) cuando la voz dice su cifra o su etiqueta
        v = dict(p["visual"]); f_num = f_etq = None
        objetivos = [x for x in (v.get("valor"), v.get("hasta")) if x] + [it.get("valor") for it in v.get("items") or []]
        cifras = {c for c in (_cifra_norm(x) for x in objetivos) if c is not None}
        for wv, fw in voz:
            if cifras and _cifra_norm(wv) in cifras: f_num = fw - 1; break
        if v.get("etiqueta"):
            f_etq = next((fw - 1 for wv, fw in voz if any(_coincide(x, wv) for x in CP._palabras(v["etiqueta"]))), None)
        primera = pal[0]["f"] if pal else f0 + 4
        candidatos = [x for x in (f_num, primera + 6, f0 + int(0.25 * (f1 - f0))) if x is not None]
        aparece = max(f0 + 8, min(candidatos))
        accion = f_num if f_num is not None else (f_etq if f_etq is not None and f_etq > aparece else aparece + 8)
        v["f"] = min(aparece, f1 - 16)
        v["f_accion"] = max(v["f"] + 4, min(accion, f1 - 12))
        for k in ("valor", "hasta"):                     # numeros ya separados para el contador (formato es-ES)
            n = CP.numero_texto(v.get(k)) if v.get(k) else None
            if n: v[k + "_num"] = dict(pre=n[0], v=n[1], suf=n[2], dec=n[3])
        for it in v.get("items") or []:
            n = CP.numero_texto(it.get("valor"))
            if n: it["num"] = dict(pre=n[0], v=n[1], suf=n[2], dec=n[3])
        if v["tipo"] == "pasos":
            v.update(pasos=ciclo, activo=int(e.get("paso") or 0), rapido=bool(e.get("ciclo_rapido")), hechos=sorted(hechos))
        # ---- cinta de pasos (pequena, abajo) desde la primera escena del ciclo, salvo si el visual ya son los pasos
        cinta = None
        if ciclo and primero_ciclo is not None and orden.index(eid) >= primero_ciclo and v["tipo"] != "pasos":
            cinta = dict(pasos=ciclo, activo=int(e.get("paso") or 0), hechos=sorted(hechos), rapido=bool(e.get("ciclo_rapido")))
        if e.get("paso"): hechos.add(int(e["paso"]))
        if e.get("ciclo_rapido"): hechos.update(range(1, len(ciclo) + 1))
        tit = dict(palabras=pal, color=p["titular"].get("color", "neutro"), bloque=bool(p["titular"].get("bloque")),
                   grande=(v["tipo"] == "ninguno"))
        salida.append(dict(escena=eid, inicio=f0, fin=f1, titular=tit, visual=v, cinta=cinta, pieza=p.get("pieza")))
    tramos = []
    for p in salida:
        if tramos and p["inicio"] <= tramos[-1]["fin"] + 1: tramos[-1]["fin"] = p["fin"]
        else: tramos.append(dict(inicio=p["inicio"], fin=p["fin"]))
    for t in tramos: t.update(entra=True, sale=t["fin"] < frames - 1)
    tema = params.get("tema") or "clasico"
    return dict(ancho=w, alto=h, fps=fps, frames=frames, orientacion=params.get("orientacion", "horizontal"), banda=banda(params),
                paleta=CP.PALETA_PANELES.get(tema, CP.PALETA_PANELES["cyberpunk"]), icono_flujo=params.get("icono_flujo", "sobre"),
                tramos=tramos, paneles=salida)

# ---------------------------------------------------------------- render
def node_listo():
    return os.path.isdir(os.path.join(MOTION, "node_modules", "@motion-canvas", "core"))

def renderizar(ruta_motion, carpeta, desde=None, hasta=None, timeout=3600, log=print):
    """Renderiza motion.json en PNG (000000.png = fotograma 1 de Blender). Devuelve el INFORME de render.mjs."""
    if not node_listo():
        raise RuntimeError(f"faltan las dependencias de Motion Canvas: cd {MOTION} && npm ci")
    ruta_motion, carpeta = os.path.abspath(ruta_motion), os.path.abspath(carpeta)     # render.mjs corre en motion/
    datos = json.load(open(ruta_motion))
    cmd = ["node", os.path.join(MOTION, "render.mjs"), "--datos", ruta_motion, "--salida", carpeta,
           "--desde", str(0 if desde is None else desde), "--hasta", str(datos["frames"] - 1 if hasta is None else hasta)]
    r = subprocess.run(cmd, cwd=MOTION, capture_output=True, text=True, timeout=timeout)
    inf = next((json.loads(l[8:]) for l in r.stdout.splitlines() if l.startswith("INFORME ")), None)
    if r.returncode != 0 or not inf or inf.get("resultado") != 0:
        raise RuntimeError(f"render de Motion Canvas fallido ({r.returncode}): {(inf or {}).get('log')}\n{r.stderr[-2000:]}")
    return inf

def fotograma_png(carpeta, f_blender):
    """PNG de Motion Canvas que corresponde al fotograma f de Blender (o None si no existe)."""
    ruta = os.path.join(carpeta, f"{int(f_blender) - 1:06d}.png")
    return ruta if os.path.exists(ruta) else None

def superponer(fondo, panel, destino):
    """Previa: el PNG del panel (cuadro completo, con alfa) encima de la imagen de Blender, escalado a su tamano."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", fondo, "-i", panel, "-filter_complex",
                    "[1:v][0:v]scale2ref[p][f];[f][p]overlay=0:0:format=auto", "-frames:v", "1", destino],
                   check=True, capture_output=True)
    return destino
