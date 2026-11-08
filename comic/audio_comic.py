# MODO 3 · AUDIO: voces (Gemini TTS) o audio propio -> tiempos.json, que sincroniza toda la animacion.
# Solo biblioteca estandar (array, wave). ffmpeg solo para convertir un audio propio que no sea WAV PCM.
#
# tiempos.json:
#   {fps, frame_inicio, frame_fin, duracion, fuente, escenas: [{id, inicio, fin, t0, t1,
#     lineas: [{quien, texto, emocion, inicio, fin, t0, t1, wav, offset, envolvente: [0..1 por fotograma]}]}]}
# 'inicio'/'fin' son fotogramas (fin exclusivo). 'wav' es relativo a la carpeta del proyecto; 'offset' es el
# segundo del wav donde empieza la linea (audio propio: un solo wav para todas).
import array, hashlib, json, math, os, re, subprocess, tempfile, wave

import ia_vertex as IA
import comic_parametros as CP

PRE, HUECO, POST = 0.35, 0.30, 0.65          # segundos: antes de la 1a linea, entre lineas, tras la ultima
VELOCIDAD = {"caminar": 1.5, "entrar": 1.5, "salir": 1.5, "correr": 4.0, "moverse": 1.0, "conducir": 5.0}
DURACION_ACCION = {"saltar": 1.0, "caer": 1.6, "girar": 0.5, "golpear": 0.7, "sorpresa": 0.7, "saludar": 1.2,
                   "despegar": 2.0, "aparecer": 0.6, "desaparecer": 0.5}

# ---------------------------------------------------------------- wav
def wav_escribir(ruta, muestras, rate):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(muestras.tobytes() if isinstance(muestras, array.array) else muestras)

def wav_leer(ruta):
    with wave.open(ruta, "rb") as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        datos = w.readframes(n)
    if sw != 2: raise ValueError(f"{ruta}: solo WAV PCM de 16 bits")
    a = array.array("h"); a.frombytes(datos)
    if ch > 1:
        a = array.array("h", (int(sum(a[i:i + ch]) / ch) for i in range(0, len(a), ch)))
    return a, rate

def a_wav_mono(entrada, salida, rate=24000):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", entrada, "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", salida],
                       capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"ffmpeg no pudo convertir {entrada}: {r.stderr[:300]}")
    return salida

def recortar_silencio(m, rate, umbral_db=-42, margen=0.05):
    if not m: return m
    pico = max(1, max(abs(x) for x in m))
    umbral = 32767 * 10 ** (umbral_db / 20)
    v = int(rate * 0.01)
    ini = next((i for i in range(0, len(m), v) if max(abs(x) for x in m[i:i + v]) > umbral), 0)
    fin = next((i for i in range(len(m) - v, 0, -v) if max(abs(x) for x in m[i:i + v]) > umbral), len(m))
    ini = max(0, ini - int(margen * rate)); fin = min(len(m), fin + v + int(margen * rate))
    return m[ini:fin]

def envolvente(m, rate, fps, t0=0.0, t1=None):
    """RMS por fotograma entre t0 y t1 (segundos del wav), normalizada a 0..1 (percentil 95)."""
    t1 = len(m) / rate if t1 is None else t1
    n = max(1, round((t1 - t0) * fps)); paso = rate / fps; out = []
    for k in range(n):
        a = int(t0 * rate + k * paso); b = int(a + paso)
        seg = m[max(0, a):max(0, min(len(m), b))]
        out.append(math.sqrt(sum(x * x for x in seg[::4]) / max(1, len(seg[::4]))) if seg else 0.0)
    ref = sorted(out)[int(len(out) * 0.95)] if out else 1.0
    return [round(min(1.0, x / ref), 3) if ref > 0 else 0.0 for x in out]

def tramos_voz(m, rate, umbral_db=-38, min_silencio=0.35):
    """Tramos con voz [(t0, t1)] separados por silencios de al menos min_silencio."""
    umbral = 32767 * 10 ** (umbral_db / 20); v = int(rate * 0.02); tramos = []; ini = None; ult = None
    for i in range(0, len(m), v):
        activo = max((abs(x) for x in m[i:i + v]), default=0) > umbral; t = i / rate
        if activo:
            if ini is None: ini = t
            ult = t + v / rate
        elif ini is not None and t - ult > min_silencio:
            tramos.append((ini, ult)); ini = None
    if ini is not None: tramos.append((ini, ult))
    return tramos

def mezclar(lineas, dir_proy, total_s, rate, salida):
    """Pista unica con todas las lineas en su sitio (para escuchar y para el montaje)."""
    mix = array.array("h", bytes(2 * int(total_s * rate + rate)))
    cache = {}
    for ln in lineas:
        ruta = os.path.join(dir_proy, ln["wav"])
        if ruta not in cache: cache[ruta] = wav_leer(ruta)
        m, r = cache[ruta]
        a = int(ln.get("offset", 0) * r); b = a + int((ln["t1"] - ln["t0"]) * r)
        d = int(ln["t0"] * rate)
        for i, x in enumerate(m[a:b]):
            j = d + i
            if 0 <= j < len(mix): mix[j] = max(-32768, min(32767, mix[j] + x))
    wav_escribir(salida, mix, rate)

# ---------------------------------------------------------------- duraciones de las acciones
def duracion_necesaria(escena, posiciones):
    """Segundos que necesita la escena para que sus desplazamientos no vayan acelerados."""
    need = escena.get("duracion_minima", 2.5)
    for ac in escena["acciones"]:
        frac = max(0.05, ac["fin"] - ac["inicio"])
        if ac["accion"] in VELOCIDAD and "destino_x" in ac:
            x0 = posiciones.get(ac["actor"], ac["destino_x"])
            d = abs(ac["destino_x"] - x0)
            if ac["accion"] == "entrar": d = max(d, 4.0)
            need = max(need, d / VELOCIDAD[ac["accion"]] / frac)
            posiciones[ac["actor"]] = ac["destino_x"]
        elif ac["accion"] in DURACION_ACCION:
            need = max(need, DURACION_ACCION[ac["accion"]] / frac)
    return need

def posiciones_iniciales(guion):
    pos = {}
    for esc in guion["escenarios"]:
        for el in esc["elementos"]: pos[el["id"]] = el["x"]
    return pos

SILABAS_POR_PALABRA = 2.2        # para pasar el ritmo en palabras/s (parametro ritmo_voz) a silabas/s
RITMO_MIN, RITMO_MAX = 0.82, 1.25 # banda aceptada respecto al objetivo; fuera se regenera (y al final se ajusta con atempo)
INTENTOS_TTS = 3

def silabas(texto):
    """Silabas habladas aproximadas: grupos de vocales por palabra; cada letra de una sigla (LLM, SQS, DB) cuenta 1.5."""
    total = 0.0
    for tok in re.findall(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto):
        if tok.isdigit(): total += 2 * len(tok); continue
        for parte in re.findall(r"[A-ZÁÉÍÓÚÑ]{2,}(?![a-záéíóúüñ])|[A-ZÁÉÍÓÚÑ]?[a-záéíóúüñ]+|[A-ZÁÉÍÓÚÑ0-9]", tok):
            if parte.isupper() or parte.isdigit(): total += 1.5 * len(parte)
            else: total += max(1, len(re.findall(r"[aeiouáéíóúü]+|y(?![aeiouáéíóú])", parte.lower())))
    return max(1.0, total)

def ritmo_linea(texto, m, rate):
    """(silabas por segundo, palabras por segundo) de una linea ya recortada."""
    d = max(0.1, len(m) / rate); return silabas(texto) / d, len(texto.split()) / d

def atempo(m, rate, factor):
    """Cambia la velocidad sin cambiar el tono (ffmpeg atempo); factor > 1 acelera."""
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, "a.wav"), os.path.join(tmp, "b.wav"); wav_escribir(a, m, rate)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-filter:a", f"atempo={factor:.4f}", "-ar", str(rate), "-ac", "1",
                        "-c:a", "pcm_s16le", b], check=True)
        return wav_leer(b)[0]

def voz_con_ritmo(op, texto, voz, params, emocion, log=print):
    """TTS con control de ritmo: mide silabas/s, regenera las lineas arrastradas o atropelladas (hasta INTENTOS_TTS)
    y, si ninguna toma entra en la banda, ajusta la mejor con atempo. Devuelve (muestras, rate, informe)."""
    obj = params.get("ritmo_voz", 2.6) * SILABAS_POR_PALABRA; mejor = None
    for k in range(INTENTOS_TTS):
        pcm, rate = IA.tts(op, texto, voz, params["modelo_tts"], emocion, idioma=params.get("idioma"), ritmo=params.get("ritmo_voz", 2.6))
        m = array.array("h"); m.frombytes(pcm); m = recortar_silencio(m, rate)
        sps, _ = ritmo_linea(texto, m, rate); desvio = abs(math.log(sps / obj))
        if mejor is None or desvio < mejor[0]: mejor = (desvio, m, rate, sps)
        if RITMO_MIN <= sps / obj <= RITMO_MAX: break
        log(f"      ritmo {sps:.1f} silabas/s (objetivo {obj:.1f}): {'arrastrada' if sps < obj else 'atropellada'}, otra toma")
    _, m, rate, sps = mejor; inf = dict(tomas=k + 1, silabas_s=round(sps, 2))
    if not RITMO_MIN <= sps / obj <= RITMO_MAX:
        meta = obj * (0.92 if sps < obj else 1.12); f = max(0.75, min(1.4, meta / sps))
        m = atempo(m, rate, f); inf.update(atempo=round(f, 3), silabas_s=round(sps * f, 2))
        log(f"      ajuste atempo x{f:.2f} -> {sps * f:.1f} silabas/s")
    return m, rate, inf

def estimar_duracion(texto):
    palabras = max(1, len(texto.split()))
    return 0.35 + palabras / 2.6

# ---------------------------------------------------------------- tiempos con voces generadas
def generar_tts(op, guion, params, dir_proy, log=print):
    """Sintetiza cada linea (cache por contenido) y devuelve tiempos.json."""
    fps = params["fps"]; voces = {p["id"]: p["voz"] for p in guion["personajes"]}
    adir = os.path.join(dir_proy, "audio"); os.makedirs(adir, exist_ok=True)
    pos = posiciones_iniciales(guion)
    t = 0.0; escenas = []; todas = []
    for esc in guion["escenas"]:
        for q in esc["presentes"]: pos.setdefault(q["actor"], q["x"])
        lineas = []; tl = t + PRE
        for ln in esc["lineas"]:
            voz = params["voz_narrador"] if ln["quien"] == "narrador" else voces.get(ln["quien"], "Puck")
            if params.get("voz_narrador") == CP.VOZ_SILENCIO: voz = CP.VOZ_SILENCIO
            clave = hashlib.sha1(f"{params['modelo_tts']}|{voz}|{ln['emocion']}|{ln['texto']}|ritmo{params.get('ritmo_voz', 2.6)}"
                                 .encode()).hexdigest()[:16]
            rel = f"audio/linea_{clave}.wav"; ruta = os.path.join(dir_proy, rel)
            if not os.path.exists(ruta):
                if voz == CP.VOZ_SILENCIO:
                    rate = 24000; m = array.array("h", bytes(2 * int(estimar_duracion(ln["texto"]) * rate)))
                    # "voz" sintetica minima para que la boca se mueva en pruebas sin red
                    for i in range(len(m)): m[i] = int(3000 * math.sin(i * 0.05) * (0.5 + 0.5 * math.sin(i / rate * 2 * math.pi * 4)))
                else:
                    log(f"    voz {voz} ({ln['emocion']}): {ln['texto'][:60]}")
                    m, rate, _ = voz_con_ritmo(op, ln["texto"], voz, params, ln["emocion"], log)
                wav_escribir(ruta, m, rate)
            m, rate = wav_leer(ruta); dur = len(m) / rate
            d = dict(quien=ln["quien"], texto=ln["texto"], emocion=ln["emocion"], t0=round(tl, 3), t1=round(tl + dur, 3),
                     wav=rel, offset=0.0, voz=voz, envolvente=envolvente(m, rate, fps),
                     silabas_s=round(ritmo_linea(ln["texto"], m, rate)[0], 2))
            lineas.append(d); todas.append(d); tl += dur + HUECO
        fin_lineas = (tl - HUECO + POST) if lineas else t
        dur_esc = max(fin_lineas - t, duracion_necesaria(esc, dict(pos)), esc.get("duracion_minima", 2.5))
        duracion_necesaria(esc, pos)   # actualiza posiciones para la siguiente escena
        escenas.append(dict(id=esc["id"], t0=round(t, 3), t1=round(t + dur_esc, 3), lineas=lineas))
        t += dur_esc
    return _a_fotogramas(dict(fuente="tts", duracion=round(t, 3), escenas=escenas), fps, dir_proy, todas)

# ---------------------------------------------------------------- tiempos con audio propio
def usar_audio_propio(op, guion, params, dir_proy, ruta_audio, transcripcion=None, log=print):
    fps = params["fps"]
    adir = os.path.join(dir_proy, "audio"); os.makedirs(adir, exist_ok=True)
    rel = "audio/audio_propio.wav"; ruta = os.path.join(dir_proy, rel)
    if not os.path.exists(ruta):
        a_wav_mono(ruta_audio, ruta)
    m, rate = wav_leer(ruta); total = len(m) / rate
    if transcripcion is None:
        tp = os.path.join(adir, "transcripcion.json")
        if os.path.exists(tp):
            transcripcion = json.load(open(tp, encoding="utf-8"))
        else:
            log("    transcribiendo el audio con Gemini…")
            segs, meta = IA.transcribir(op, ruta, params.get("idioma", "es"))
            transcripcion = dict(segmentos=segs, meta=meta, tramos_voz=tramos_voz(m, rate))
            json.dump(transcripcion, open(tp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    segs = transcripcion["segmentos"]
    lineas_g = [(i, j, ln) for i, esc in enumerate(guion["escenas"]) for j, ln in enumerate(esc["lineas"])]
    tiempos_ln = {}
    if len(segs) == len(lineas_g) and segs:
        for (i, j, ln), s in zip(lineas_g, segs): tiempos_ln[(i, j)] = (float(s["inicio"]), float(s["fin"]))
    elif segs and lineas_g:
        # reparto proporcional por caracteres a lo largo de la transcripcion
        acum = []; c = 0
        for s in segs: acum.append((c, float(s["inicio"]), float(s["fin"]), len(s["texto"]))); c += len(s["texto"])
        total_c = max(1, c); tot_g = sum(len(ln["texto"]) for *_, ln in lineas_g); cg = 0
        def t_de(chars):
            x = chars / max(1, tot_g) * total_c
            for c0, a, b, n in acum:
                if x <= c0 + n: return a + (b - a) * (x - c0) / max(1, n)
            return acum[-1][2]
        for i, j, ln in lineas_g:
            n = len(ln["texto"]); tiempos_ln[(i, j)] = (t_de(cg), t_de(cg + n)); cg += n
    escenas = []; todas = []
    inicios = []
    for i, esc in enumerate(guion["escenas"]):
        ts = [tiempos_ln[(i, j)] for j in range(len(esc["lineas"])) if (i, j) in tiempos_ln]
        inicios.append(max(0.0, ts[0][0] - PRE) if ts else None)
    # escenas sin lineas: reparten el hueco entre vecinas
    for i in range(len(inicios)):
        if inicios[i] is None:
            prev = next((inicios[k] for k in range(i - 1, -1, -1) if inicios[k] is not None), 0.0)
            nxt = next((inicios[k] for k in range(i + 1, len(inicios)) if inicios[k] is not None), total)
            inicios[i] = prev + (nxt - prev) / 2
    inicios[0] = 0.0
    for i, esc in enumerate(guion["escenas"]):
        t0 = inicios[i]; t1 = inicios[i + 1] if i + 1 < len(inicios) else total + POST
        lineas = []
        for j, ln in enumerate(esc["lineas"]):
            if (i, j) not in tiempos_ln: continue
            a, b = tiempos_ln[(i, j)]
            d = dict(quien=ln["quien"], texto=ln["texto"], emocion=ln["emocion"], t0=round(a, 3), t1=round(b, 3), wav=rel,
                     offset=round(a, 3), voz="audio_propio", envolvente=envolvente(m, rate, fps, a, b))
            lineas.append(d)
        escenas.append(dict(id=esc["id"], t0=round(t0, 3), t1=round(max(t1, t0 + 0.5), 3), lineas=lineas))
    # la pista entera va una vez, desde el fotograma 1
    return _a_fotogramas(dict(fuente="audio_propio", duracion=round(escenas[-1]["t1"], 3), escenas=escenas,
                              pista_unica=rel), fps, dir_proy, [], mezclar_pista=False)

def _a_fotogramas(t, fps, dir_proy, todas, mezclar_pista=True):
    f = lambda s: 1 + int(round(s * fps))
    for e in t["escenas"]:
        e["inicio"], e["fin"] = f(e["t0"]), f(e["t1"])
        for ln in e["lineas"]: ln["inicio"], ln["fin"] = f(ln["t0"]), max(f(ln["t1"]), f(ln["t0"]) + 1)
    t.update(fps=fps, frame_inicio=1, frame_fin=t["escenas"][-1]["fin"] - 1 if t["escenas"] else 1)
    if mezclar_pista and todas:
        mezclar(todas, dir_proy, t["duracion"] + 1, 24000, os.path.join(dir_proy, "audio", "narracion.wav"))
        t["mezcla"] = "audio/narracion.wav"
    return t
