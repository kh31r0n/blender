#!/usr/bin/env python3
# Agente que dirige el desierto LEGO v3 con Gemini (Vertex AI). El Geometry Nodes genera todas las piezas; el
# modelo solo traduce una descripcion en texto a parametros del modificador, mira el render y propone ajustes.
#
#   1. Gemini recibe la descripcion y el esquema de parametros (desierto_parametros.py) -> preset JSON
#   2. Se limitan los valores a su rango y Blender (sin interfaz) aplica el preset a una COPIA del .blend base,
#      la guarda y renderiza dos previsualizaciones (arco y vista general)
#   3. Gemini recibe las imagenes, la descripcion y el preset -> {cumple, problemas, cambios}
#   4. Se repite hasta que cumple o se agotan las iteraciones
#
# Uso:  python3 agente_desierto_gemini.py --probar
#       python3 agente_desierto_gemini.py --descripcion "dunas en estrella altas y dos arcos grandes de roca rojiza"
#       opciones: --iteraciones 3  --modelo gemini-3.1-pro-preview  --seco (solo el primer preset, sin Blender)
# Autenticacion: token de `gcloud auth print-access-token --account=CUENTA` (no cambia la cuenta activa de gcloud).
# Se envia a Google: la descripcion, el esquema de parametros, los presets y renders de 960x540. Nada mas.
# Solo biblioteca estandar de Python.
import argparse, base64, datetime, json, os, re, subprocess, sys, time, unicodedata, urllib.error, urllib.request

DESERT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DESERT)
import desierto_parametros as DP

CUENTA = "jjimenez@neosecure.com"
PROYECTO = "project-b62861f4-f767-4aff-9f5"     # configuracion gcloud "neosecure": tiene aiplatform.googleapis.com
MODELO = "gemini-3.1-pro-preview"               # alternativa rapida: gemini-3.5-flash
REGION = "global"
BLENDER = os.path.expanduser("~/.local/bin/blender")
BASE = os.path.join(DESERT, "Desierto_LEGO_GN_v3.blend")
PREVIA = os.path.join(DESERT, "previa_desierto_v3.py")

SISTEMA = """Eres director de arte técnico de un generador procedimental de desiertos hechos con piezas LEGO
(Geometry Nodes en Blender). No modelas nada: solo eliges valores para los parámetros del esquema.

Cómo funciona el generador:
- El terreno mide Dimensión X × Dimensión Y unidades. Resolución X/Y es el número de celdas (studs): cada pieza
  mide Dimensión/Resolución (por defecto 1000/250 = 4 unidades). Un escalón del relieve mide
  0.4 × celda × escalon_placas (por defecto 4.8 unidades). Las alturas de dunas, rocas y arcos van en unidades.
- Dunas (transversales, barjanes o estrella) sobre colinas suaves, con erosión térmica y cuñas LEGO en los bordes.
- Rocas: mesetas con gradas y estratos de color, más rocas sueltas al pie.
- Arcos naturales: banda curva de ladrillos con abertura; el número es min(max_arcos, densidad_arcos × área/10⁶).
  Para que un arco se lea bien: luz_arco ≥ 60, altura_arco ≥ 50 y grosor_arco ≤ 0.3 × min(luz, altura).
- Colores: ids LEGO de la lista permitida.
- La previsualización principal enfoca el primer arco; la segunda es una vista general en perspectiva.
Reglas: devuelve solo claves del esquema, con valores dentro de rango. Prefiere cambios moderados y coherentes.
No cambies dimension_x/dimension_y ni resolucion_x/resolucion_y salvo que la descripción lo pida."""

# ---------- Vertex AI ----------
def token(cuenta):
    r = subprocess.run(["gcloud", "auth", "print-access-token", f"--account={cuenta}"],
                       capture_output=True, text=True, timeout=90)
    tok = r.stdout.strip()
    if r.returncode != 0 or not tok:
        sys.exit(f"No se pudo obtener el token de {cuenta}: {r.stderr.strip()[:300]}\n"
                 f"Inicia sesión con:  ! gcloud auth login {cuenta}")
    return tok

def llamar(op, partes, esquema=None, temperatura=0.4):
    host = "aiplatform.googleapis.com" if op.region == "global" else f"{op.region}-aiplatform.googleapis.com"
    url = (f"https://{host}/v1/projects/{op.proyecto}/locations/{op.region}/publishers/google/models/"
           f"{op.modelo}:generateContent")
    cfg = {"temperature": temperatura}
    if esquema: cfg.update(responseMimeType="application/json", responseSchema=esquema)
    cuerpo = {"contents": [{"role": "user", "parts": partes}],
              "systemInstruction": {"parts": [{"text": SISTEMA}]}, "generationConfig": cfg}
    datos = json.dumps(cuerpo).encode()
    for intento in range(4):
        req = urllib.request.Request(url, data=datos, method="POST", headers={
            "Authorization": f"Bearer {token(op.cuenta)}", "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            cuerpo_err = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 503) and intento < 3:
                print(f"  Vertex AI {e.code}, reintento en {5 * 2 ** intento} s"); time.sleep(5 * 2 ** intento); continue
            sys.exit(f"Vertex AI respondió {e.code}: {cuerpo_err}")
        except urllib.error.URLError as e:
            if intento < 3: time.sleep(5); continue
            sys.exit(f"No se pudo conectar con Vertex AI: {e}")
    cand = (resp.get("candidates") or [{}])[0]
    texto = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
    uso = resp.get("usageMetadata", {})
    meta = dict(modelo=resp.get("modelVersion"), fin=cand.get("finishReason"), segundos=round(time.time() - t0, 1),
                tokens_entrada=uso.get("promptTokenCount"), tokens_salida=uso.get("candidatesTokenCount"),
                tokens_razonamiento=uso.get("thoughtsTokenCount"))
    if not esquema: return texto, meta
    try:
        return json.loads(texto), meta
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if m: return json.loads(m.group(0)), meta
        sys.exit(f"Respuesta no JSON del modelo ({meta}): {texto[:500]}")

# ---------- esquemas de respuesta ----------
def esquema_preset():
    # Lista de pares clave/valor: con un objeto de ~50 propiedades opcionales el modelo omitia claves que si
    # mencionaba en su explicacion. Los valores llegan como texto y DP.limitar los convierte y acota.
    return {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "clave": {"type": "STRING", "enum": [f["clave"] for f in DP.esquema()]},
        "valor": {"type": "STRING", "description": "número, true/false, tipo de duna o id LEGO del color"}},
        "required": ["clave", "valor"]}}

def a_dict(pares):
    return {p["clave"]: p["valor"] for p in pares or [] if isinstance(p, dict) and "clave" in p and "valor" in p}

def esquema_plan():
    return {"type": "OBJECT", "properties": {
        "explicacion": {"type": "STRING", "description": "Por qué estos valores, en 1-3 frases."},
        "cambios": esquema_preset()}, "required": ["explicacion", "cambios"], "propertyOrdering": ["explicacion", "cambios"]}

def esquema_revision():
    return {"type": "OBJECT", "properties": {
        "cumple": {"type": "BOOLEAN", "description": "true si las imágenes ya encajan bien con la descripción."},
        "puntuacion": {"type": "INTEGER", "minimum": 0, "maximum": 10},
        "problemas": {"type": "ARRAY", "items": {"type": "STRING"}},
        "cambios": esquema_preset()}, "required": ["cumple", "puntuacion", "problemas", "cambios"],
        "propertyOrdering": ["problemas", "puntuacion", "cumple", "cambios"]}

def tabla_parametros():
    return json.dumps(DP.esquema(), ensure_ascii=False)

# ---------- Blender ----------
def generar(preset, carpeta, n):
    ruta_preset = os.path.join(carpeta, f"preset_{n}.json")
    json.dump(preset, open(ruta_preset, "w"), indent=2, ensure_ascii=False)
    salida = dict(blend=os.path.join(carpeta, f"desierto_{n}.blend"), previa=os.path.join(carpeta, f"previa_{n}.png"),
                  general=os.path.join(carpeta, f"general_{n}.png"), informe=os.path.join(carpeta, f"informe_{n}.json"))
    cmd = [BLENDER, "-b", BASE, "-P", PREVIA, "--", "--preset", ruta_preset, "--previa", salida["previa"],
           "--general", salida["general"], "--res", "960x540", "--muestras", "16",
           "--guardar", salida["blend"], "--informe", salida["informe"]]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not os.path.exists(salida["previa"]):
        sys.exit(f"Blender falló ({r.returncode}):\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    salida["segundos"] = round(time.time() - t0, 1)
    return salida

def imagen(ruta):
    return {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(open(ruta, "rb").read()).decode()}}

# ---------- bucle ----------
def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40] or "desierto"

def main():
    ap = argparse.ArgumentParser(description="Agente Gemini para el desierto LEGO v3")
    ap.add_argument("--descripcion", help="cómo quieres el desierto, en lenguaje natural")
    ap.add_argument("--iteraciones", type=int, default=3, help="máximo de renders revisados (por defecto 3)")
    ap.add_argument("--modelo", default=MODELO); ap.add_argument("--proyecto", default=PROYECTO)
    ap.add_argument("--cuenta", default=CUENTA); ap.add_argument("--region", default=REGION)
    ap.add_argument("--salida", help="carpeta de resultados (por defecto agente/<fecha>_<descripcion>)")
    ap.add_argument("--probar", action="store_true", help="solo comprueba el token y una llamada mínima")
    ap.add_argument("--seco", action="store_true", help="solo pide el primer preset, sin Blender ni revisión")
    op = ap.parse_args()

    if op.probar:
        texto, meta = llamar(op, [{"text": "Responde solo con la palabra OK."}], temperatura=0.0)
        print(f"Cuenta {op.cuenta} · proyecto {op.proyecto} · modelo {op.modelo}\nRespuesta: {texto.strip()!r}  {meta}")
        return
    if not op.descripcion: ap.error("falta --descripcion")
    if not os.path.exists(BASE): sys.exit(f"No existe {BASE}: ejecuta antes crear_desierto_lego_gn_v3.py")

    carpeta = op.salida or os.path.join(DESERT, "agente", datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + slug(op.descripcion))
    os.makedirs(carpeta, exist_ok=False)
    log = dict(descripcion=op.descripcion, modelo=op.modelo, proyecto=op.proyecto, cuenta=op.cuenta, iteraciones=[])
    def guardar_log(): json.dump(log, open(os.path.join(carpeta, "log.json"), "w"), indent=2, ensure_ascii=False)

    print(f"[1] Plan inicial con {op.modelo}…")
    plan, meta = llamar(op, [{"text": f"Parámetros disponibles (JSON):\n{tabla_parametros()}\n\n"
                                      f"Descripción del usuario: {op.descripcion}\n\n"
                                      "Devuelve en 'cambios' TODOS los parámetros que deben cambiar respecto a sus "
                                      "valores por defecto para conseguir esa descripción (un par clave/valor por "
                                      "parámetro), coherentes con tu explicación."}], esquema_plan())
    cambios, avisos = DP.limitar(a_dict(plan.get("cambios")))
    print(f"    {plan.get('explicacion', '')}\n    cambios: {cambios}")
    log["plan"] = dict(respuesta=plan, avisos=avisos, meta=meta); guardar_log()
    if op.seco:
        print(json.dumps(dict(DP.por_defecto(), **cambios), indent=2, ensure_ascii=False)); return

    for n in range(1, op.iteraciones + 1):
        preset = dict(DP.por_defecto(), **cambios)
        print(f"[{n + 1}] Blender: generando y renderizando la iteración {n}…")
        res = generar(preset, carpeta, n)
        print(f"    {res['previa']}  ({res['segundos']} s)")
        print(f"    Revisión de {op.modelo}…")
        rev, meta = llamar(op, [
            {"text": f"Descripción del usuario: {op.descripcion}\n\nPreset aplicado (JSON):\n"
                     f"{json.dumps(preset, ensure_ascii=False)}\n\nParámetros disponibles (JSON):\n{tabla_parametros()}\n\n"
                     "Imagen 1: vista hacia el primer arco. Imagen 2: vista general. Evalúa si el resultado encaja con "
                     "la descripción (forma y altura de las dunas, rocas, arcos, colores). Si no encaja, indica los "
                     "problemas y devuelve en 'cambios' todos los parámetros a modificar respecto al preset aplicado "
                     "(un par clave/valor por parámetro, solo los que cambian)."},
            imagen(res["previa"]), imagen(res["general"])], esquema_revision(), temperatura=0.3)
        nuevos, avisos = DP.limitar(a_dict(rev.get("cambios")))
        nuevos = {k: v for k, v in nuevos.items() if preset.get(k) != v}
        print(f"    cumple={rev.get('cumple')} puntuación={rev.get('puntuacion')} problemas={rev.get('problemas')}")
        log["iteraciones"].append(dict(n=n, preset=preset, render=res, revision=rev, avisos=avisos, meta=meta)); guardar_log()
        if rev.get("cumple") or not nuevos: break
        cambios.update(nuevos)
        print(f"    nuevos cambios: {nuevos}")

    ultimo = log["iteraciones"][-1]["render"]
    log["resultado"] = ultimo; guardar_log()
    print(f"\nResultado: {ultimo['blend']}\nPrevisualización: {ultimo['previa']}\nRegistro: {os.path.join(carpeta, 'log.json')}")

if __name__ == "__main__":
    main()
