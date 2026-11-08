# Llamadas a Vertex AI (Gemini) sin dependencias: texto/JSON con esquema, voz (Gemini TTS) y transcripcion.
# Autenticacion: `gcloud auth print-access-token --account=CUENTA` (no cambia la cuenta activa de gcloud),
# igual que ~/blender/desert/agente_desierto_gemini.py.
import base64, json, re, subprocess, sys, time, urllib.error, urllib.request

CUENTA = "jjimenez@neosecure.com"
PROYECTO = "project-b62861f4-f767-4aff-9f5"
MODELO = "gemini-3.1-pro-preview"
MODELO_RAPIDO = "gemini-3.5-flash"
REGION = "global"

class ErrorIA(RuntimeError):
    pass

_tok = {"t": None, "exp": 0}
def token(cuenta=CUENTA):
    if _tok["t"] and time.time() < _tok["exp"]: return _tok["t"]
    r = subprocess.run(["gcloud", "auth", "print-access-token", f"--account={cuenta}"],
                       capture_output=True, text=True, timeout=90)
    t = r.stdout.strip()
    if r.returncode != 0 or not t:
        raise ErrorIA(f"No se pudo obtener el token de {cuenta}: {r.stderr.strip()[:300]}\n"
                      f"Inicia sesion con:  ! gcloud auth login {cuenta}")
    _tok.update(t=t, exp=time.time() + 600)
    return t

def _post(url, cuerpo, cuenta, timeout=300):
    datos = json.dumps(cuerpo).encode()
    for intento in range(4):
        req = urllib.request.Request(url, data=datos, method="POST", headers={
            "Authorization": f"Bearer {token(cuenta)}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")[:600]
            if e.code in (429, 500, 502, 503, 504) and intento < 3:
                espera = 5 * 2 ** intento
                print(f"  Vertex AI {e.code}, reintento en {espera} s", flush=True); time.sleep(espera); continue
            raise ErrorIA(f"Vertex AI respondio {e.code}: {err}")
        except (urllib.error.URLError, TimeoutError) as e:
            if intento < 3: time.sleep(5); continue
            raise ErrorIA(f"No se pudo conectar con Vertex AI: {e}")

def _url(op, modelo):
    region = getattr(op, "region", REGION)
    host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
    return (f"https://{host}/v1/projects/{getattr(op, 'proyecto_gcp', PROYECTO)}/locations/{region}"
            f"/publishers/google/models/{modelo}:generateContent")

def llamar(op, partes, sistema, esquema=None, temperatura=0.5, modelo=None):
    """Devuelve (respuesta, meta). Con esquema, la respuesta es el JSON ya decodificado."""
    modelo = modelo or getattr(op, "modelo", MODELO)
    cfg = {"temperature": temperatura}
    if esquema: cfg.update(responseMimeType="application/json", responseSchema=esquema)
    cuerpo = {"contents": [{"role": "user", "parts": partes}], "generationConfig": cfg}
    if sistema: cuerpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    t0 = time.time()
    resp = _post(_url(op, modelo), cuerpo, getattr(op, "cuenta", CUENTA))
    cand = (resp.get("candidates") or [{}])[0]
    texto = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
    uso = resp.get("usageMetadata", {})
    meta = dict(modelo=resp.get("modelVersion") or modelo, fin=cand.get("finishReason"), segundos=round(time.time() - t0, 1),
                tokens_entrada=uso.get("promptTokenCount"), tokens_salida=uso.get("candidatesTokenCount"),
                tokens_razonamiento=uso.get("thoughtsTokenCount"))
    if not esquema: return texto, meta
    try:
        return json.loads(texto), meta
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if m:
            try: return json.loads(m.group(0)), meta
            except json.JSONDecodeError: pass
        raise ErrorIA(f"Respuesta no JSON del modelo ({meta}): {texto[:400]}")

def imagen(ruta, mime="image/png"):
    with open(ruta, "rb") as f:
        return {"inlineData": {"mimeType": mime, "data": base64.b64encode(f.read()).decode()}}

# ---------------------------------------------------------------- voz
# tono por emocion; el ritmo va aparte y manda (los estilos 'misterioso' o 'susurro' sueltos alargaban las palabras)
ESTILO_TTS = {
    "neutral": "", "alegre": "with a cheerful tone", "triste": "with a sad tone", "enfadado": "with an angry tone",
    "sorprendido": "with a surprised tone", "asustado": "with a fearful tone", "emocionado": "with an excited tone",
    "susurro": "softly, almost whispering", "misterioso": "with an intriguing tone",
}
IDIOMA_TTS = {"es": "Spanish (Spain)", "en": "English", "pt": "Portuguese", "fr": "French", "it": "Italian"}

def instruccion_tts(texto, emocion="neutral", idioma=None, ritmo=None):
    """Indicacion de direccion para Gemini TTS: idioma, tono y ritmo (palabras por segundo) antes del texto a leer."""
    if not idioma and not ritmo:
        estilo = ESTILO_TTS.get(emocion, "")
        return f"Say {estilo}: {texto}" if estilo else texto
    partes = [f"Read aloud in {IDIOMA_TTS.get(idioma, idioma or 'the language of the text')}, as a clear documentary narrator"]
    if ESTILO_TTS.get(emocion): partes.append(ESTILO_TTS[emocion])
    if ritmo: partes.append(f"at a natural, steady pace of about {round(ritmo * 60)} words per minute, "
                            "without stretching syllables or adding long pauses")
    return ", ".join(partes) + f": {texto}"

def tts(op, texto, voz, modelo, emocion="neutral", idioma=None, ritmo=None):
    """Gemini TTS en Vertex. Devuelve (pcm16 mono bytes, frecuencia)."""
    prompt = instruccion_tts(texto, emocion, idioma, ritmo)
    cuerpo = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"responseModalities": ["AUDIO"],
                                   "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    resp = _post(_url(op, modelo), cuerpo, getattr(op, "cuenta", CUENTA), timeout=180)
    for p in (resp.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
        d = p.get("inlineData")
        if d and d.get("data"):
            m = re.search(r"rate=(\d+)", d.get("mimeType", "")); rate = int(m.group(1)) if m else 24000
            return base64.b64decode(d["data"]), rate
    raise ErrorIA(f"Gemini TTS no devolvio audio para {texto[:60]!r}")

# ---------------------------------------------------------------- transcripcion
def transcribir(op, ruta_wav, idioma="es", modelo=None):
    """Segmentos [{inicio, fin, texto}] (segundos) de un audio, con Gemini."""
    esquema = {"type": "OBJECT", "properties": {"segmentos": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "inicio": {"type": "NUMBER"}, "fin": {"type": "NUMBER"}, "texto": {"type": "STRING"}},
        "required": ["inicio", "fin", "texto"]}}}, "required": ["segmentos"]}
    with open(ruta_wav, "rb") as f: datos = base64.b64encode(f.read()).decode()
    partes = [{"inlineData": {"mimeType": "audio/wav", "data": datos}},
              {"text": f"Transcribe este audio (idioma {idioma}) en segmentos por frase, con tiempos de inicio y fin "
                       "en segundos desde el principio del archivo. Respeta el texto literal."}]
    r, meta = llamar(op, partes, "Eres un transcriptor preciso.", esquema, 0.0, modelo or MODELO_RAPIDO)
    return r.get("segmentos", []), meta
