# Modelos 3D prediseñados para el estilo tecnico: busqueda, eleccion con Gemini y descarga.
#   Poly Haven: modelos CC0, descarga directa (glTF 1k).
#   Sketchfab: busqueda libre; la descarga necesita un token de API (SKETCHFAB_TOKEN o el archivo
#              ~/.config/agente_comic/sketchfab_token). Por defecto solo CC0 y CC-BY (con credito en la cartela de FIN).
# Lo descargado se guarda en descargas/modelos/<fuente>_<id>/ y solo se lee (lo importa Blender: glTF no ejecuta codigo).
import io, json, os, re, shutil, subprocess, time, urllib.parse, urllib.request, zipfile

import comic_parametros as CP
import ia_vertex as IA

UA = {"User-Agent": "agente-comic-blender/1.0"}
DIR_MODELOS = os.path.join(CP.DESCARGAS, "modelos")
TOKEN_ARCHIVO = os.path.expanduser("~/.config/agente_comic/sketchfab_token")
LICENCIAS = {"cc0": ["CC0 Public Domain", "CC0"], "cc-by": ["CC Attribution"], "cc-by-sa": ["CC Attribution-ShareAlike"]}
MAX_CARAS = 250000

def _get(url, cabeceras=None, timeout=60):
    req = urllib.request.Request(url, headers=dict(UA, **(cabeceras or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def _json(url, cabeceras=None): return json.loads(_get(url, cabeceras))

def token_sketchfab():
    t = os.environ.get("SKETCHFAB_TOKEN")
    if not t and os.path.exists(TOKEN_ARCHIVO):
        with open(TOKEN_ARCHIVO) as f: t = f.read().strip()
    return t or None

# ---------------------------------------------------------------- busqueda
_cache_ph = {}
def catalogo_polyhaven():
    ruta = os.path.join(DIR_MODELOS, "_polyhaven_catalogo.json")
    if not _cache_ph:
        if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < 7 * 86400:
            _cache_ph.update(json.load(open(ruta)))
        else:
            _cache_ph.update(_json("https://api.polyhaven.com/assets?t=models"))
            os.makedirs(DIR_MODELOS, exist_ok=True); json.dump(_cache_ph, open(ruta, "w"))
    return _cache_ph

def buscar_polyhaven(terminos, n=8):
    cat = catalogo_polyhaven(); out = []
    palabras = {w for t in terminos for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 2}
    frases = [t.lower() for t in terminos]
    for aid, v in cat.items():
        texto = " ".join([v.get("name", ""), aid.replace("_", " ")] + v.get("tags", []) + v.get("categories", [])).lower()
        p = sum(3 for f in frases if f in texto) + sum(1 for w in palabras if re.search(rf"\b{re.escape(w)}", texto))
        if p > 0:
            out.append(dict(fuente="polyhaven", id=aid, nombre=v.get("name", aid), licencia="CC0", autor=", ".join(v.get("authors", {}).keys()),
                            caras=v.get("polycount"), puntos=p, url=f"https://polyhaven.com/a/{aid}",
                            miniatura=f"https://cdn.polyhaven.com/asset_img/thumbs/{aid}.png?width=256&height=256"))
    return sorted(out, key=lambda c: -c["puntos"])[:n]

def buscar_sketchfab(terminos, licencias, n=6):
    permitidas = {l for k in licencias for l in LICENCIAS.get(k, [])}
    out, vistos = [], set()
    for t in terminos[:3]:
        try:
            d = _json("https://api.sketchfab.com/v3/search?" + urllib.parse.urlencode(dict(type="models", q=t, downloadable="true", count=12)))
        except Exception as e:
            continue
        for m in d.get("results", []):
            lic = m.get("license", {}).get("label") if isinstance(m.get("license"), dict) else m.get("license")
            if m["uid"] in vistos or lic not in permitidas or (m.get("faceCount") or 0) > MAX_CARAS: continue
            vistos.add(m["uid"])
            imgs = sorted(m.get("thumbnails", {}).get("images", []), key=lambda i: abs(i.get("width", 0) - 256))
            out.append(dict(fuente="sketchfab", id=m["uid"], nombre=m.get("name", ""), licencia=lic,
                            autor=(m.get("user") or {}).get("displayName", ""), caras=m.get("faceCount"),
                            url=m.get("viewerUrl") or f"https://sketchfab.com/3d-models/{m['uid']}",
                            miniatura=imgs[0]["url"] if imgs else None))
    return out[:n]

def hoja_candidatos(cands, carpeta):
    """Miniaturas numeradas en una hoja (para Gemini y para ti)."""
    os.makedirs(carpeta, exist_ok=True); rutas = []
    for i, c in enumerate(cands):
        r = os.path.join(carpeta, f"cand_{i + 1}.img")
        try:
            if c.get("miniatura"):
                with open(r, "wb") as f: f.write(_get(c["miniatura"]))
                rutas.append(r)
            else: rutas.append(None)
        except Exception:
            rutas.append(None)
    ok = [(i, r) for i, r in enumerate(rutas) if r]
    if not ok: return None
    fuente = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    ent, filt = [], []
    for k, (i, r) in enumerate(ok):
        ent += ["-i", r]
        filt.append(f"[{k}:v]scale=256:256:force_original_aspect_ratio=decrease,pad=256:256:(ow-iw)/2:(oh-ih)/2:white,"
                    f"drawtext=fontfile='{fuente}':text='{i + 1}':x=8:y=6:fontsize=38:fontcolor=red:borderw=3:bordercolor=white[t{k}]")
    cols = min(4, len(ok)); lay = "|".join(f"{(k % cols) * 256}_{(k // cols) * 256}" for k in range(len(ok)))
    hoja = os.path.join(carpeta, "candidatos.png")
    cmd = ["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", ";".join(filt) + ";" + "".join(f"[t{k}]" for k in range(len(ok))) +
                                                   (f"xstack=inputs={len(ok)}:layout={lay}:fill=white" if len(ok) > 1 else "null"), "-frames:v", "1", hoja]
    subprocess.run(cmd, check=True, capture_output=True)
    return hoja

# ---------------------------------------------------------------- eleccion con Gemini
def elegir(op, descripcion, log=print, licencias=("cc0", "cc-by"), carpeta=None):
    """Terminos de busqueda (Gemini) -> candidatos (Poly Haven + Sketchfab) -> Gemini mira la hoja y elige."""
    esq = {"type": "OBJECT", "properties": {"objeto": {"type": "STRING"}, "terminos": {"type": "ARRAY", "items": {"type": "STRING"}}},
           "required": ["objeto", "terminos"]}
    r, meta = IA.llamar(op, [{"text": f"Descripcion de un video explicativo: {descripcion}\n\nDevuelve el objeto principal y 3-5 "
                                      "terminos de busqueda EN INGLES para encontrar su modelo 3D en Poly Haven o Sketchfab "
                                      "(del mas especifico al mas general, 1-3 palabras cada uno)."}],
                        "Eres documentalista 3D.", esq, 0.2, modelo=IA.MODELO_RAPIDO)
    terminos = [t for t in r.get("terminos", []) if t][:5] or [descripcion]
    log(f"    objeto: {r.get('objeto')} · busqueda: {terminos}")
    cands = buscar_polyhaven(terminos)
    tok = token_sketchfab()
    if tok: cands += buscar_sketchfab(terminos, licencias)
    else: log(f"    (Sketchfab: sin token, solo Poly Haven; guardalo en {TOKEN_ARCHIVO} o en SKETCHFAB_TOKEN)")
    cands = cands[:12]
    if not cands: return None, dict(terminos=terminos, candidatos=[])
    carpeta = carpeta or os.path.join(DIR_MODELOS, "_busquedas", CP.slug(descripcion, 30))
    hoja = hoja_candidatos(cands, carpeta)
    lista = "\n".join(f"{i + 1}. [{c['fuente']}] {c['nombre']} · {c['licencia']} · {c.get('caras') or '?'} caras" for i, c in enumerate(cands))
    esq2 = {"type": "OBJECT", "properties": {"elegido": {"type": "INTEGER"}, "motivo": {"type": "STRING"}}, "required": ["elegido", "motivo"]}
    partes = [{"text": f"Video explicativo: {descripcion}\n\nCandidatos (la imagen muestra sus miniaturas numeradas):\n{lista}\n\n"
                       "Elige el modelo que mejor representa el objeto a explicar: que sea ese objeto (no un accesorio), "
                       "reconocible, con partes separables y detalle moderado. Devuelve su numero (0 si ninguno sirve)."}]
    if hoja: partes.append(IA.imagen(hoja))
    e, meta2 = IA.llamar(op, partes, "Eres director de arte de videos de divulgacion.", esq2, 0.1)
    k = int(e.get("elegido") or 0)
    info = dict(terminos=terminos, candidatos=cands, hoja=hoja, motivo=e.get("motivo"), elegido=k)
    if not 1 <= k <= len(cands): return None, info
    return cands[k - 1], info

# ---------------------------------------------------------------- descarga
def descargar_polyhaven(aid, resolucion="1k"):
    dst = os.path.join(DIR_MODELOS, f"polyhaven_{aid}")
    gl = os.path.join(dst, f"{aid}.gltf")
    if os.path.exists(gl): return gl
    files = _json(f"https://api.polyhaven.com/files/{aid}")
    g = files["gltf"].get(resolucion) or files["gltf"][sorted(files["gltf"])[0]]
    g = g["gltf"]
    os.makedirs(dst, exist_ok=True)
    for rel, d in g.get("include", {}).items():
        destino = os.path.normpath(os.path.join(dst, rel))
        if not destino.startswith(dst): continue           # nada fuera de su carpeta
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f: f.write(_get(d["url"], timeout=180))
    with open(gl, "wb") as f: f.write(_get(g["url"], timeout=180))
    return gl

def descargar_sketchfab(uid):
    tok = token_sketchfab()
    if not tok: raise RuntimeError(f"Sketchfab necesita un token de API: guardalo en {TOKEN_ARCHIVO} (o SKETCHFAB_TOKEN)")
    dst = os.path.join(DIR_MODELOS, f"sketchfab_{uid}")
    previos = [os.path.join(r, f) for r, _, fs in os.walk(dst) for f in fs if f.endswith((".gltf", ".glb"))] if os.path.isdir(dst) else []
    if previos: return previos[0]
    d = _json(f"https://api.sketchfab.com/v3/models/{uid}/download", {"Authorization": f"Token {tok}"})
    info = d.get("gltf") or d.get("glb")
    if not info: raise RuntimeError(f"Sketchfab no ofrece glTF para {uid}")
    datos = _get(info["url"], timeout=300)
    os.makedirs(dst, exist_ok=True)
    if datos[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(datos)) as z:          # solo se extrae; nada se ejecuta
            for n in z.namelist():
                destino = os.path.normpath(os.path.join(dst, n))
                if not destino.startswith(dst) or n.endswith("/"): continue
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with z.open(n) as s, open(destino, "wb") as f: shutil.copyfileobj(s, f)
    else:
        with open(os.path.join(dst, f"{uid}.glb"), "wb") as f: f.write(datos)
    gl = [os.path.join(r, f) for r, _, fs in os.walk(dst) for f in fs if f.endswith((".gltf", ".glb"))]
    if not gl: raise RuntimeError(f"el paquete de Sketchfab {uid} no trae glTF")
    return gl[0]

def info_sketchfab(uid):
    m = _json(f"https://api.sketchfab.com/v3/models/{uid}")
    lic = m.get("license", {}).get("label") if isinstance(m.get("license"), dict) else m.get("license")
    return dict(fuente="sketchfab", id=uid, nombre=m.get("name", uid), licencia=lic, autor=(m.get("user") or {}).get("displayName", ""),
                caras=m.get("faceCount"), url=m.get("viewerUrl") or f"https://sketchfab.com/3d-models/{uid}")

def resolver(spec):
    """'polyhaven:<id>', URL de Poly Haven o de Sketchfab, uid de Sketchfab o archivo local -> (info, ruta)."""
    s = spec.strip()
    if os.path.exists(os.path.expanduser(s)):
        r = os.path.abspath(os.path.expanduser(s))
        return dict(fuente="archivo", id=os.path.basename(r), nombre=os.path.splitext(os.path.basename(r))[0], licencia="propia", autor="", url=r), r
    m = re.match(r"(?:polyhaven:|https?://polyhaven\.com/a/)([A-Za-z0-9_]+)", s)
    if m:
        aid = m.group(1); v = catalogo_polyhaven().get(aid, {})
        info = dict(fuente="polyhaven", id=aid, nombre=v.get("name", aid), licencia="CC0", autor=", ".join(v.get("authors", {}).keys()),
                    caras=v.get("polycount"), url=f"https://polyhaven.com/a/{aid}")
        return info, None
    m = re.search(r"([0-9a-f]{32})", s)
    if m: return info_sketchfab(m.group(1)), None
    raise ValueError(f"no reconozco el modelo '{spec}' (polyhaven:<id>, URL de Poly Haven/Sketchfab, uid o archivo)")

def descargar(info):
    if info["fuente"] == "polyhaven": return descargar_polyhaven(info["id"])
    if info["fuente"] == "sketchfab": return descargar_sketchfab(info["id"])
    return info["url"]

def credito(info):
    if not info or info.get("fuente") == "archivo": return ""
    a = f" de {info['autor']}" if info.get("autor") else ""
    return f"Modelo «{info['nombre']}»{a} ({info['licencia']}, {info['fuente']})"
