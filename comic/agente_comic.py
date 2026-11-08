#!/usr/bin/env python3
# Agente de IA que genera animaciones de comic con Grease Pencil en Blender (sin interfaz).
# Gemini (Vertex AI) escribe y revisa el guion y pone las voces; los scripts de blender/ dibujan, riggean,
# animan y renderizan todo con trazos Grease Pencil. Solo biblioteca estandar de Python.
#
#   python3 agente_comic.py MODO [opciones]
#
# Modos (numero o nombre):
#   materiales     descarga fuentes, texturas y materiales GP y crea biblioteca/Materiales_GP.blend
#   biblioteca     crea biblioteca/Escenografia_GP.blend (escenografia y personajes reutilizables, con rig)
#   modelo         (estilo tecnico) busca un modelo prediseñado (Poly Haven / Sketchfab), Gemini elige, se descarga y se
#                  convierte en partes -> modelo/partes.json. Con --modelo-3d auto|polyhaven:<id>|<url Sketchfab>|<archivo>
#   0 guion        descripcion -> guion.json (Gemini). --audio: el guion se escribe sobre tu audio. --ejemplo: sin IA
#   1 objetos      dibuja con Grease Pencil los objetos que pide el guion        -> 01_objetos.blend
#   2 rig          esqueleto para cada personaje y elemento                      -> 02_rig.blend
#   3 audio        voces Gemini TTS (o --audio propio transcrito)               -> tiempos.json + audio/
#   4 animacion    anima rigs, escenografia y camara sincronizados con el audio -> 04_animacion.blend
#     efectos      bocadillos, cartelas, onomatopeyas, lineas de accion...      -> 04b_efectos.blend
#     previa       un fotograma por escena + revision de Gemini; si propone cambios rehace 1-4 (--iteraciones)
#   5 render       video MP4 con voces + una vineta por escena                   -> render/
#     montaje      cartelas de titulo y FIN, video final, pagina de comic y GIF  -> final/
#     todo         guion -> objetos -> rig -> audio -> animacion -> efectos -> previa -> render -> montaje
#     estado       resumen del proyecto
#
# Ejemplos:
#   python3 agente_comic.py materiales
#   python3 agente_comic.py todo --descripcion "un gato astronauta aterriza en una ciudad de caramelo" --formato 3d
#   python3 agente_comic.py guion --descripcion "..." --formato 2d --orientacion vertical --duracion 20
#   python3 agente_comic.py animacion --proyecto proyectos/20261107-1800_un_gato_astronauta
#   python3 agente_comic.py todo --ejemplo --voz-narrador silencio --calidad borrador   (prueba sin red)
#   python3 agente_comic.py todo --estilo tecnico --modelo-3d auto --descripcion "como funciona un taladro de columna"
import argparse, datetime, glob, json, os, re, shutil, subprocess, sys, time, types, urllib.request, zipfile

COMIC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, COMIC)
import comic_parametros as CP
import ia_vertex as IA
import audio_comic as AU
import modelos_3d as M3

BLENDER = os.path.expanduser("~/.local/bin/blender")
SCRIPTS = os.path.join(COMIC, "blender")
PROYECTOS = os.path.join(COMIC, "proyectos")
UA = {"User-Agent": "agente-comic-blender/1.0"}

ETAPAS = ["modelo", "guion", "detalles", "objetos", "rig", "audio", "animacion", "efectos", "previa", "render", "montaje"]
NUMEROS = {"0": "guion", "1": "objetos", "2": "rig", "3": "audio", "4": "animacion", "5": "render"}

# ================================================================ utilidades
def log(msg): print(msg, flush=True)

def leer(ruta):
    with open(ruta, encoding="utf-8") as f: return json.load(f)

def escribir(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f: json.dump(datos, f, indent=2, ensure_ascii=False)

def ruta_nueva(ruta):
    """Nunca sobrescribe: si existe, anade .v2, .v3..."""
    if not os.path.exists(ruta): return ruta
    base, ext = os.path.splitext(ruta)
    base = re.sub(r"\.v\d+$", "", base); n = 2
    while os.path.exists(f"{base}.v{n}{ext}"): n += 1
    return f"{base}.v{n}{ext}"

def archivar(dirp, nombre):
    """Guarda la version anterior de guion.json / tiempos.json en historial/ antes de reemplazarla."""
    ruta = os.path.join(dirp, nombre)
    if os.path.exists(ruta):
        h = os.path.join(dirp, "historial"); os.makedirs(h, exist_ok=True)
        sello = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(ruta, os.path.join(h, f"{os.path.splitext(nombre)[0]}.{sello}.json"))

def blender(script, args, blend=None, timeout=7200):
    cmd = [BLENDER, "-b"] + ([blend] if blend else ["--factory-startup"]) + ["-P", os.path.join(SCRIPTS, script), "--"] + args
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    salida = r.stdout + r.stderr
    informe = None
    for linea in salida.splitlines():
        if linea.startswith("INFORME "):
            try: informe = json.loads(linea[8:])
            except json.JSONDecodeError: pass
    if r.returncode != 0 or informe is None or "Traceback" in salida:
        tb = salida[salida.find("Traceback"):][:2500] if "Traceback" in salida else salida[-2500:]
        raise SystemExit(f"Blender fallo en {script} (codigo {r.returncode}):\n{tb}")
    informe["_segundos"] = round(time.time() - t0, 1)
    return informe

# ================================================================ proyecto
class Proyecto:
    def __init__(self, dirp):
        self.dir = os.path.abspath(dirp); self.ruta = os.path.join(self.dir, "proyecto.json")
        self.d = leer(self.ruta)

    @classmethod
    def crear(cls, descripcion, params):
        sello = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dirp = os.path.join(PROYECTOS, f"{sello}_{CP.slug(descripcion)}")
        os.makedirs(dirp, exist_ok=False)
        escribir(os.path.join(dirp, "proyecto.json"), dict(descripcion=descripcion, creado=sello, parametros=params,
                                                           archivos={}, historial=[]))
        return cls(dirp)

    @property
    def params(self): return self.d["parametros"]
    def p(self, rel): return os.path.join(self.dir, rel)
    def archivo(self, etapa):
        rel = self.d["archivos"].get(etapa); return self.p(rel) if rel else None
    def registrar(self, etapa, ruta=None, **info):
        if ruta: self.d["archivos"][etapa] = os.path.relpath(ruta, self.dir)
        self.d["historial"].append(dict(etapa=etapa, fecha=datetime.datetime.now().isoformat(timespec="seconds"),
                                        archivo=os.path.relpath(ruta, self.dir) if ruta else None, **info))
        self.guardar()
    def guardar(self): escribir(self.ruta, self.d)
    def necesita(self, etapa):
        a = self.archivo(etapa)
        if not a or not os.path.exists(a):
            raise SystemExit(f"Falta la etapa '{etapa}' en {self.dir}. Ejecuta antes:  python3 agente_comic.py {etapa} --proyecto {self.dir}")
        return a

def params_desde(op, base=None):
    d = dict(base or CP.params_por_defecto())
    for k in CP.PARAMS_POR_CLAVE:
        v = getattr(op, k, None)
        if v is not None: d[k] = v
    for kv in op.param or []:
        if "=" in kv: k, v = kv.split("=", 1); d[k.strip()] = v.strip()
    p, avisos = CP.limitar_params(d)
    if p["voz_narrador"] not in CP.VOCES and p["voz_narrador"] != CP.VOZ_SILENCIO:
        avisos.append(f"voz {p['voz_narrador']} desconocida: Charon"); p["voz_narrador"] = "Charon"
    for a in avisos: log(f"  aviso: {a}")
    return p

def abrir_o_crear(op, crear=False):
    if op.proyecto:
        pr = Proyecto(op.proyecto)
        nuevos = params_desde(op, pr.params)
        if nuevos != pr.params:
            cambios = {k: v for k, v in nuevos.items() if pr.params.get(k) != v}
            log(f"  parametros actualizados: {cambios}")
            pr.d["parametros"] = nuevos; pr.guardar()
        return pr
    if not crear:
        ultimos = sorted(glob.glob(os.path.join(PROYECTOS, "*", "proyecto.json")))
        if not ultimos: raise SystemExit("No hay proyectos: usa --descripcion (o --ejemplo) con el modo guion o todo")
        log(f"  (sin --proyecto: uso el ultimo, {os.path.dirname(ultimos[-1])})")
        return abrir_o_crear(types.SimpleNamespace(**dict(vars(op), proyecto=os.path.dirname(ultimos[-1]))))
    tec = getattr(op, "estilo", None) == "tecnico"
    ej = CP.guion_ejemplo_tecnico() if tec else CP.guion_ejemplo()
    desc = op.descripcion or ("ejemplo: " + ej["titulo"] if op.ejemplo else None)
    if not desc: raise SystemExit("Falta --descripcion (o --ejemplo)")
    p = params_desde(op)
    if tec and op.orientacion is None: p["orientacion"] = "vertical"      # como la referencia (short vertical)
    if tec and op.cartelas is None: p["cartelas"] = False                 # sin rotulos: lo cuenta la voz
    if tec and op.bocadillos is None: p["bocadillos"] = False
    pr = Proyecto.crear(desc, p)
    log(f"Proyecto nuevo: {pr.dir}")
    return pr

def registrar_ia(pr, etapa, meta, **extra):
    ruta = pr.p("log_ia.json")
    d = leer(ruta) if os.path.exists(ruta) else []
    d.append(dict(etapa=etapa, fecha=datetime.datetime.now().isoformat(timespec="seconds"), meta=meta, **extra))
    escribir(ruta, d)

# ================================================================ MODO materiales
DESCARGAS = [
    # (destino relativo a descargas/, url, licencia, autoria)
    ("fuentes/Bangers-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf", "OFL 1.1", "The Bangers Project Authors"),
    ("fuentes/OFL-Bangers.txt", "https://github.com/google/fonts/raw/main/ofl/bangers/OFL.txt", "OFL 1.1", ""),
    ("fuentes/ComicNeue-Bold.ttf", "https://github.com/google/fonts/raw/main/ofl/comicneue/ComicNeue-Bold.ttf", "OFL 1.1", "The Comic Neue Project Authors"),
    ("fuentes/OFL-ComicNeue.txt", "https://github.com/google/fonts/raw/main/ofl/comicneue/OFL.txt", "OFL 1.1", ""),
    ("fuentes/ArchivoBlack-Regular.ttf", "https://github.com/google/fonts/raw/main/ofl/archivoblack/ArchivoBlack-Regular.ttf", "OFL 1.1", "Omnibus-Type"),
    ("fuentes/OFL-ArchivoBlack.txt", "https://github.com/google/fonts/raw/main/ofl/archivoblack/OFL.txt", "OFL 1.1", ""),
    ("ambientcg/Paper001_1K-JPG.zip", "https://ambientcg.com/get?file=Paper001_1K-JPG.zip", "CC0", "ambientCG"),
    ("ambientcg/Cardboard002_1K-JPG.zip", "https://ambientcg.com/get?file=Cardboard002_1K-JPG.zip", "CC0", "ambientCG"),
    ("blender_demo/greasepencil-bike.blend", "https://download.blender.org/demo/greasepencil-bike.blend", "CC-BY-SA", "Dedouze (Blender demo 'Bike Ride')"),
]
TEXTURAS_ZIP = {"ambientcg/Paper001_1K-JPG.zip": "papel.jpg", "ambientcg/Cardboard002_1K-JPG.zip": "carton.jpg"}

def descargar(url, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r, open(destino + ".part", "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(destino + ".part", destino)

def modo_materiales(op):
    dd = CP.DESCARGAS; tex = os.path.join(CP.BIBLIOTECA, "texturas"); os.makedirs(tex, exist_ok=True)
    log("[materiales] descargas")
    for rel, url, lic, autor in DESCARGAS:
        dst = os.path.join(dd, rel)
        if os.path.exists(dst) and not op.forzar: log(f"  ya esta   {rel}"); continue
        try:
            descargar(url, dst); log(f"  bajado    {rel}  ({os.path.getsize(dst) // 1024} KB, {lic})")
        except Exception as e:
            log(f"  FALLO     {rel}: {e}")
    for rel, nombre in TEXTURAS_ZIP.items():   # del zip solo se extrae la imagen de color; nada se ejecuta
        z = os.path.join(dd, rel)
        if not os.path.exists(z): continue
        with zipfile.ZipFile(z) as zf:
            color = [n for n in zf.namelist() if n.lower().endswith(("_color.jpg", "_color.png"))]
            if color:
                with zf.open(color[0]) as src, open(os.path.join(tex, nombre), "wb") as out: shutil.copyfileobj(src, out)
                log(f"  textura   {nombre} <- {color[0]}")
    leeme = ["# Recursos descargados por el agente de comic", "",
             f"Descargados el {datetime.date.today().isoformat()} por `agente_comic.py materiales`. De los zip solo se extrae la imagen de color.", "",
             "| Archivo | Licencia | Autoria | Fuente |", "|---|---|---|---|"]
    for rel, url, lic, autor in DESCARGAS:
        leeme.append(f"| `{rel}` | {lic} | {autor} | {url} |")
    leeme += ["", "- Los materiales de la demo *Bike Ride* (CC-BY-SA) van en un archivo aparte, "
              "`biblioteca/Materiales_GP_bike_CC-BY-SA.blend`: si los usas, atribuye a Dedouze y comparte igual.",
              "- Packs gratuitos que piden correo (p. ej. los materiales de Line Art de Sophie Jantak en Gumroad): "
              "deja su `.blend` en `descargas/manual/` y vuelve a ejecutar el modo materiales; se anaden con su nombre como prefijo.",
              "- Las tramas Ben-Day (`biblioteca/texturas/semitono_*.png`, `puntos_blancos.png`) las genera el propio agente."]
    with open(os.path.join(dd, "LEEME.md"), "w", encoding="utf-8") as f: f.write("\n".join(leeme) + "\n")
    os.makedirs(os.path.join(dd, "manual"), exist_ok=True)
    log("[materiales] Blender: biblioteca de materiales GP")
    inf = blender("b_materiales.py", ["--descargas", dd, "--salida", CP.MATERIALES_BLEND,
                                      "--salida_bike", os.path.join(CP.BIBLIOTECA, "Materiales_GP_bike_CC-BY-SA.blend"),
                                      "--muestrario", os.path.join(CP.BIBLIOTECA, "muestrario_materiales.png")])
    log(f"  {inf}")
    log(f"  -> {CP.MATERIALES_BLEND}\n  -> {os.path.join(CP.BIBLIOTECA, 'muestrario_materiales.png')}")

def modo_biblioteca(op):
    log("[biblioteca] Blender: escenografia y personajes reutilizables con rig")
    inf = blender("b_biblioteca.py", ["--salida", CP.ESCENOGRAFIA_BLEND])
    log(f"  {inf}\n  -> {CP.ESCENOGRAFIA_BLEND}")

# ================================================================ MODO modelo (modelos prediseñados -> estilo tecnico)
def hoja_partes(pr, datos, carpeta):
    """Vista general + cada parte resaltada, con su id, en una sola imagen para Gemini."""
    fuente = CP.FUENTE_TECNICA if os.path.exists(CP.FUENTE_TECNICA) else CP.FUENTE_TITULOS
    imgs = [("general", os.path.join(carpeta, "vista_general.png"))] + [(q["id"], os.path.join(carpeta, f"parte_{q['id']}.png")) for q in datos["partes"]]
    imgs = [(e, r) for e, r in imgs if os.path.exists(r)]
    cols = 4; ent, fil = [], []
    for k, (e, r) in enumerate(imgs):
        ent += ["-i", r]
        fil.append(f"[{k}:v]scale=300:300,drawtext=fontfile='{fuente}':text='{e}':x=8:y=6:fontsize=30:fontcolor=black[t{k}]")
    lay = "|".join(f"{(k % cols) * 300}_{(k // cols) * 300}" for k in range(len(imgs)))
    hoja = os.path.join(carpeta, "hoja_partes.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", ";".join(fil) + ";" + "".join(f"[t{k}]" for k in range(len(imgs))) +
                    f"xstack=inputs={len(imgs)}:layout={lay}:fill=white", "-frames:v", "1", hoja], check=True, capture_output=True)
    return hoja

def modo_modelo(op, pr=None):
    pr = pr or abrir_o_crear(op, crear=True)
    if not es_tecnico(pr): raise SystemExit("Los modelos prediseñados son para el estilo tecnico: usa --estilo tecnico")
    spec = op.modelo_3d or pr.d.get("modelo_3d") or "auto"
    licencias = [x.strip() for x in (op.licencias or "cc0,cc-by").split(",") if x.strip()]
    carpeta = ruta_nueva(pr.p("modelo"))
    if spec == "auto":
        log(f"[modelo] busco un modelo prediseñado para: {pr.d['descripcion'][:80]}")
        cand, info = M3.elegir(op, pr.d["descripcion"], log, licencias, carpeta=os.path.join(carpeta, "busqueda"))
        registrar_ia(pr, "modelo_busqueda", {}, terminos=info.get("terminos"), elegido=info.get("elegido"), motivo=info.get("motivo"),
                     candidatos=[f"{c['fuente']}:{c['id']} {c['nombre']} ({c['licencia']})" for c in info.get("candidatos", [])])
        if not cand:
            raise SystemExit("No encontre un modelo adecuado (sigue con primitivas quitando --modelo-3d, o da uno con --modelo-3d <url|id|archivo>)")
        log(f"    elegido: {cand['nombre']} [{cand['fuente']}, {cand['licencia']}] — {info.get('motivo', '')[:140]}")
        if info.get("hoja"): log(f"    candidatos: {info['hoja']}")
    else:
        cand, _ = M3.resolver(spec); log(f"[modelo] {cand['nombre']} [{cand['fuente']}, {cand['licencia']}]")
    log("    descargando…")
    ruta = M3.descargar(cand)
    log("[modelo] Blender: partes, simplificacion, colores y vistas")
    inf = blender("b_modelo.py", ["--entrada", ruta, "--salida", os.path.join(carpeta, "partes.json"), "--hojas", carpeta])
    datos = leer(os.path.join(carpeta, "partes.json"))
    hoja = hoja_partes(pr, datos, carpeta)
    pr.d["modelo_3d"] = spec; pr.d["modelo_3d_info"] = dict(cand, credito=M3.credito(cand), archivo=ruta)
    pr.registrar("modelo", os.path.join(carpeta, "partes.json"), informe=inf, hoja=os.path.relpath(hoja, pr.dir))
    log(f"    {inf['partes']} partes, {inf['caras']} caras (de {inf['caras_originales']}), {inf['alto']} m de alto\n    -> {hoja}")
    return datos

def tiene_modelo(pr):
    a = pr.archivo("modelo"); return bool(a and os.path.exists(a) and es_tecnico(pr))

# ================================================================ MODO 0 guion
SISTEMA_GUION = """Eres guionista y director de animacion de comic para un generador automatico en Blender con
Grease Pencil. No dibujas: escribes un guion JSON que el generador convierte en una animacion de comic con colores
muy vivos y brillantes, tinta negra, tramas de puntos, bocadillos y onomatopeyas.

EL MUNDO
- Cada escenario es un decorado. X va de izquierda (-) a derecha (+) en unidades de ~1 m; el decorado util esta entre
  x=-20 y x=20. Un personaje mide ~1.8. Elementos de cielo (sol, luna, nube, planeta) se colocan solos arriba.
- Filas de profundidad (de cerca a lejos): delante (puede tapar parcialmente a los personajes), personajes (justo
  detras de ellos), medio, fondo, lejos. Un buen escenario lleva 8-14 elementos: 2-4 grandes en fondo/lejos
  (edificios, montanas, casas), 2-4 en medio (arboles, tiendas), 1-3 en personajes (farola, banco, senal), 0-2 delante
  (flores, arbustos) y 1-3 de cielo. Reparte las x; no pongas dos elementos grandes en la misma x y fila.
- Personajes normalmente entre x=-8 y x=8; separalos al menos 2 cuando comparten plano.

LAS ESCENAS
- presentes: quien esta y donde empieza (x relativa al escenario) y hacia donde mira (camara, izquierda, derecha).
  Dos personajes que conversan suelen mirarse (el de la izquierda 'derecha', el otro 'izquierda').
  Si en la escena anterior alguien camino hasta destino_x, empieza la siguiente en esa x.
- lineas: narracion ('narrador') o dialogo (id del personaje). Frases cortas (maximo 18 palabras), vivas y naturales,
  en el idioma pedido. La duracion de cada escena la marca el audio de sus lineas.
- acciones: inicio y fin son fracciones 0-1 de la escena. caminar/correr/entrar/salir necesitan destino_x (salir puede
  usar hacia). No solapes dos acciones del mismo actor. Los objetos tambien actuan (aparecer, rebotar, conducir...).
- efectos: momento 0-1 y duracion en segundos. Onomatopeyas en golpes, saltos y sorpresas; iconos (exclamacion,
  interrogacion, idea, corazones, sudor) en reacciones; lineas_foco en momentos dramaticos; confeti en celebraciones.
- camara: varia los planos (general para situar, conjunto para dialogos, medio y primer_plano para emociones,
  detalle para objetos). objetivo = id de personaje o 'escena'. temblor en impactos.

REGLAS
- Usa solo los valores del vocabulario. ids en minusculas, sin espacios ni tildes.
- Colores muy vivos y contrastados: personajes vecinos con ropa de colores distintos; escenografia variada.
- Cada personaje con una voz distinta acorde a su caracter; el narrador no es un personaje.
- Historia con inicio, conflicto y final claro, apta para todos los publicos."""

SISTEMA_TECNICO = """Eres guionista de videos de divulgacion del tipo 'asi funciona X'. No dibujas: describes el objeto como
piezas primitivas (formas del vocabulario) y escribes la explicacion narrada. Un generador en Blender lo dibuja con
Grease Pencil en vista isometrica, con papel de fondo, paleta apagada, sombra azul plana y rayos X.

COORDENADAS (metros): el objeto se apoya en el suelo z=0, centrado en x=0, y=0; su frente mira a -Y (hacia la camara).
- x, y, z de una pieza son su BASE (centro de la cara inferior) en el mundo; la forma crece hacia +Z desde la base.
  rot_x/rot_y/rot_z en grados (rot_y=90 tumba un cilindro hacia X). Para manguera, 'camino' son puntos del mundo.
- Proporciones reales y piezas apoyadas (nada flota ni se atraviesa sin motivo): la base de una pieza que va encima
  de otra es la z del techo de la de abajo. Tamano total entre 0.4 y 2.5 m (la maqueta de un sistema, hasta 5 m de
  ancho). Usa 6-18 piezas (hasta 40 en la maqueta de un sistema).
- Da SIEMPRE todas las medidas de la forma (caja: ancho, fondo y alto; panel: ancho, alto y grosor; cilindro, tubo,
  disco y varilla: radio y alto; cono: radio, radio2 y alto; esfera: radio). Si falta una se pone 0.6 m y una pieza
  pequena sale enorme. ancho, fondo, alto y radio van siempre: 0 en las que la forma no usa. camino es [] salvo en
  las mangueras, que necesitan al menos 2 puntos.
- padre: la pieza se mueve con su padre (el agua dentro de un deposito tiene padre = deposito).
- material 'transparente' para cristal/plastico, 'liquido' para agua o cafe; las carcasas opacas que tapan el
  mecanismo se ven por dentro con rayos_x en las escenas que lo necesiten.
- Paleta apagada (tema clasico): un color principal para la carcasa (menta, verde_agua, blanco_hueso...), metal y gris
  para los mecanismos, y 'lima' solo como acento puntual. Con el TEMA ICONOS (lo dice COLORES del vocabulario) usa solo
  sus colores: cuerpos 'blanco', detalles y lo activo 'lima', 'azul_claro' para lo secundario, 'negro' para piezas
  pequenas oscuras y 'rojo' solo para fallos y alertas. Accesorios del entorno: 1-3, alrededor (|x| o |y| > 1); 0-1 en
  la maqueta de un sistema (ninguno con el tema iconos).

MODELADO: reproduce las partes reconocibles del objeto real con varias primitivas por parte (un inodoro: taza
= cono con radio arriba mayor + pie de caja + asiento anillo; la cisterna es una caja apoyada sobre la parte trasera de
la taza). Las piezas finas y alargadas que no son verticales (palancas, brazos, ejes, cadenas) se tumban con rot_y=90
o rot_x=90. Conecta los mecanismos: si el flotador mueve una valvula, pon el brazo (varilla tumbada) que los une.

SISTEMAS Y PROCESOS (software, redes, logistica...): no hay un objeto fisico, asi que se construye una MAQUETA sobre el
suelo. Cada componente es un objeto reconocible de 1-4 primitivas (servidor = caja con rejilla; base de datos =
cilindro; cola = tubo o cilindro transparente tumbado con cajitas dentro; funcion = caja pequena con tapa en bisagra;
control de acceso = garita con barrera; antena = varilla con esfera; pantalla = panel). Reparte los componentes en el
plano siguiendo el recorrido de izquierda (-X) a derecha (+X), con hueco entre ellos para que se vean las conexiones, y
unelos con mangueras (tubos o cables) cuyo 'camino' va de un componente al siguiente, pegado al suelo o en arco.
OBJETOS-ICONO: la forma 'icono' dibuja un objeto prefabricado ya detallado del 'modelo' elegido (robot = el agente,
orbe = el LLM, base_datos, reloj_arena = TTL, embudo = correlar, campana = alerta, diana = acierto...), con 'alto' = su
TAMANO (dimension mayor, 0.3-0.8 m en una maqueta) y su base en x, y, z. Sus proporciones por tamano 1 vienen en MODELOS
DE ICONO: con ellas calcula donde acaban (p. ej. un servidor de tamano 0.6 mide 0.33 x 0.38 x 0.6). Usalos para los
componentes que tengan icono y completa con primitivas lo que no lo tenga (colas, cajitas de datos, soportes).
Los mensajes viajan con los efectos flujo (ida) y flujo_vuelta (respuesta) sobre la manguera que los lleva; aprobado y
rechazo marcan decisiones; reloj, esperas y tiempos limite; ondas, senales y telemetria; alerta, avisos e incidentes;
rayo, respuestas instantaneas (acierto de cache, respuesta reutilizada). Lo que hay dentro de un
componente (un grafo = esferas unidas por mangueras finas) se ve con rayos_x de su carcasa. Sigue el recorrido con
'resaltar' y con la camara ('objetivos' = las piezas de la zona de la que se habla). La narracion usa los nombres
tecnicos reales.

ESCENAS (4-8 en videos cortos; en los largos, las que pida la duracion objetivo): el objeto se construye por orden logico, problema por problema: cada escena anade 1-4 piezas
(aparecen) y explica para que sirven. 'resaltar' = piezas de las que se habla (en TODAS las escenas); 'rayos_x' =
piezas opacas que hay que atravesar para ver el interior; 'animaciones' muestran como funciona (girar, llenar, abrir...);
'efectos' para agua, vapor, flechas, llamas... La ultima escena muestra el objeto completo funcionando.
LO QUE SE CUENTA SE VE: cada escena tiene al menos un cambio visible que ilustra su frase. Si algo se acumula o se
guarda, crea piezas pequenas (fichas, bloques) que aparecen en su sitio una a una en escenas sucesivas (apiladas o en
fila); si algo viaja o se mueve de sitio, usa un flujo por su manguera o desplaza la pieza (desplazar_x, desplazar_y,
subir) hasta su destino y 'volver' despues, por un camino libre (coloca origen y destino uno al lado del otro, sin otra
pieza en medio). No repitas la misma imagen en dos escenas seguidas.
TIEMPOS: inicio y fin (animaciones) y momento (efectos) son fracciones de la escena con decimales (0.1, 0.35, 0.6...).
Reparte la accion a lo largo de la escena siguiendo lo que dice la narracion. Con momento o inicio 1 empieza cuando la
escena ya acaba y no se ve: lo mas tarde, 0.7. La 'duracion' de un efecto va en SEGUNDOS (2-6; un flujo, 2-4).
Narracion: 1-2 frases por escena, cortas (maximo 20 palabras), tono divulgativo cercano, en el idioma pedido.
Camara: general para situar, medio para el objeto, detalle para piezas pequenas (objetivo = id de pieza u 'objeto';
'objetivos' opcional = lista de ids para encuadrar una zona o un grupo de piezas).
Usa solo valores del vocabulario; ids en minusculas sin espacios ni tildes."""

SISTEMA_MODELO = SISTEMA_TECNICO.split("COORDENADAS")[0] + """LAS PIEZAS YA EXISTEN: son las partes de un modelo 3D prediseñado (descargado), ya colocado en su sitio.
No hay coordenadas ni dimensiones que decidir. La imagen muestra la vista general y cada parte resaltada en naranja
con su id. Tu trabajo:
- Agrupa las partes en piezas con nombre propio de lo que son (cada parte en una sola pieza; tornillos y detalles
  pequenos van con la pieza a la que pertenecen). Si alguna parte no se identifica, puede ir en una pieza 'carcasa' o
  'estructura'. Si la geometria trae varias cosas fundidas en una parte, nombra la pieza por lo principal.
- material: metal, solido o transparente (piezas de cristal); padre (lo que se mueve con otra) y bisagra si se abre.
- Recolorea con la paleta apagada para que se distingan: carcasa o cuerpo en un color principal (menta, verde_agua,
  blanco_hueso...), mecanismos en metal/gris, y 'lima' solo como acento puntual.

ESCENAS (4-8): se monta por orden logico (lo que va abajo o dentro primero) y se explica que hace cada pieza;
'resaltar' = piezas de las que se habla; 'rayos_x' = piezas opacas (carcasas) que tapan lo que se explica;
'animaciones' para mostrar como funciona (girar, oscilar, subir, abrir...); 'efectos' cuando ayuden. La ultima escena
muestra el objeto completo funcionando. Narracion: 1-2 frases por escena, maximo 20 palabras, tono divulgativo cercano,
en el idioma pedido. Camara: general, medio o detalle (objetivo = id de pieza u 'objeto').
Usa solo valores del vocabulario; ids de pieza en minusculas sin espacios ni tildes."""

SISTEMA_REVISION_MODELO = SISTEMA_MODELO + """

AHORA ERES TAMBIEN EL REVISOR: recibes el guion aplicado y un fotograma (al 60 %) de cada escena. Si algo no se ve o no
se entiende (pieza tapada sin rayos_x, encuadre, colores que no distinguen piezas, orden de montaje raro), devuelve en
'guion' el guion COMPLETO corregido con cambios minimos. Conserva el texto de la narracion salvo que sea incorrecto.
Si todo esta bien, cumple=true y no devuelvas guion."""

SISTEMA_REVISION_TECNICO = SISTEMA_TECNICO + """

AHORA ERES TAMBIEN EL REVISOR. Recibes el guion aplicado y un fotograma clave (al 60 %) de cada escena. Evalua:
que el objeto se reconozca, que las piezas encajen (nada flotando ni atravesado), que el interior se vea cuando
se explica (rayos_x), el encuadre y que cada imagen cuente su escena. Si algo falla devuelve en 'guion' el guion
COMPLETO corregido con cambios minimos (dimensiones y posiciones de piezas, rayos_x, planos de camara, efectos).
Conserva ids y el texto de la narracion salvo que sea incorrecto. Si todo esta bien, cumple=true y no devuelvas guion."""

def es_tecnico(pr): return pr.params.get("estilo") == "tecnico"

INTERNOS = {"guion": ("estilo", "tema", "personajes", "escenarios"), "escena": ("acciones", "presentes"), "linea": ("quien",)}
def guion_para_revision(g):
    """El guion validado sin los campos internos que el validador anade (la revision los tomaba por errores de esquema)."""
    if g.get("estilo") != "tecnico": return g
    g = {k: v for k, v in g.items() if k not in INTERNOS["guion"]}
    g["escenas"] = [dict({k: v for k, v in e.items() if k not in INTERNOS["escena"]},
                         lineas=[{k: v for k, v in l.items() if k not in INTERNOS["linea"]} for l in e["lineas"]]) for e in g["escenas"]]
    return g

def validador(pr):
    if tiene_modelo(pr):
        dm = datos_modelo(pr); return lambda g, p: CP.validar_guion_modelo(g, dm, p)
    return CP.validar_guion_tecnico if es_tecnico(pr) else CP.validar_guion

def instrucciones_formato(p):
    tec = p.get("estilo") == "tecnico"
    n = max(2, round(p["duracion"] / (7.0 if tec else 5.5)))
    f = ("2d: decorado plano visto de frente con camara ortografica; no uses 'orbita'." if p["formato"] == "2d" else
         "3d: decorado con volumen y camara en perspectiva; puedes usar 'orbita' y los angulos picado/contrapicado.")
    o = ("vertical 9:16: cuadro alto y estrecho, como maximo 2 personajes por plano, abunda en planos medios y primeros planos."
         if p["orientacion"] == "vertical" else "horizontal 16:9.")
    return (f"Formato {f}\nOrientacion {o}\nDuracion objetivo: unos {p['duracion']:.0f} s, alrededor de {n} escenas de {'5-9' if tec else '3-7'} s.\n"
            f"Idioma de lineas: {p['idioma']}.")

def modo_guion(op, pr=None):
    pr = pr or abrir_o_crear(op, crear=True)
    p = pr.params
    tec = p.get("estilo") == "tecnico"
    validar = CP.validar_guion_tecnico if tec else CP.validar_guion
    if tec and (getattr(op, "modelo_3d", None) and not tiene_modelo(pr)):
        modo_modelo(op, pr)
    if tiene_modelo(pr) and not op.ejemplo:
        return guion_modelo(op, pr)
    if op.ejemplo:
        g, av = validar(CP.guion_ejemplo_tecnico() if tec else CP.guion_ejemplo(), p)
        log("[0 guion] guion de ejemplo (sin IA)")
    else:
        desc = op.descripcion or pr.d["descripcion"]
        vocab = CP.vocabulario_tecnico(p) if tec else CP.vocabulario_texto()
        partes = [f"VOCABULARIO PERMITIDO\n{vocab}\n\n{instrucciones_formato(p)}\n\nDESCRIPCION DEL USUARIO:\n{desc}"]
        if op.audio:
            log("[0 guion] transcribiendo tu audio para escribir el guion sobre el")
            wav = pr.p("audio/audio_propio.wav"); os.makedirs(os.path.dirname(wav), exist_ok=True)
            if not os.path.exists(wav): AU.a_wav_mono(op.audio, wav)
            segs, meta = IA.transcribir(op, wav, p["idioma"])
            m, rate = AU.wav_leer(wav)
            escribir(pr.p("audio/transcripcion.json"), dict(segmentos=segs, meta=meta, tramos_voz=AU.tramos_voz(m, rate)))
            pr.d["audio_propio"] = os.path.abspath(op.audio); pr.guardar()
            partes.append("AUDIO PROPIO: la narracion ya esta grabada. Las lineas del guion deben ser EXACTAMENTE estos "
                          "segmentos, en este orden y sin cambiar el texto (uno por linea), repartidos en escenas; decide "
                          "quien dice cada uno (narrador o personaje):\n" +
                          "\n".join(f"{i + 1}. [{s['inicio']:.1f}-{s['fin']:.1f} s] {s['texto']}" for i, s in enumerate(segs)))
        log(f"[0 guion] {op.modelo} escribe el guion…")
        t0 = time.time()
        bruto, meta = IA.llamar(op, [{"text": "\n\n".join(partes)}], SISTEMA_TECNICO if tec else SISTEMA_GUION,
                                CP.esquema_guion_tecnico() if tec else CP.esquema_guion(), 0.7 if tec else 0.8)
        g, av = validar(bruto, p)
        registrar_ia(pr, "guion", meta, avisos=av)
        geo = (CP.medidas_faltantes(bruto) + CP.revisar_geometria(g)) if tec else []
        if geo:                      # una pasada de reparacion antes de gastar renders
            log(f"    {len(geo)} problemas de geometria: " + " | ".join(geo[:4]))
            log("    Gemini corrige la geometria…")
            bruto, meta = IA.llamar(op, [{"text": "\n\n".join(partes) + f"\n\nGUION PROPUESTO:\n{json.dumps(g, ensure_ascii=False)}\n\n"
                                                  "PROBLEMAS DE GEOMETRIA DETECTADOS (corrigelos con cambios minimos y devuelve el guion completo):\n- " + "\n- ".join(geo)}],
                                    SISTEMA_TECNICO, CP.esquema_guion_tecnico(), 0.4)
            g, av2 = validar(bruto, p); av += av2
            quedan = CP.medidas_faltantes(bruto) + CP.revisar_geometria(g)
            registrar_ia(pr, "guion_geometria", meta, problemas=geo, quedan=quedan)
            for q in quedan: log(f"    queda: {q}")
        log(f"    {meta['segundos']} s, {meta.get('tokens_entrada')} tokens de entrada")
    for a in av: log(f"    aviso: {a}")
    archivar(pr.dir, "guion.json"); escribir(pr.p("guion.json"), g)
    pr.registrar("guion", pr.p("guion.json"), escenas=len(g["escenas"]), avisos=av)
    resumen_guion(g)
    return pr

def datos_modelo(pr):
    return leer(pr.archivo("modelo"))

def texto_partes(datos):
    return "\n".join(f"{q['id']}: '{q['nombre_original']}' (materiales: {q['materiales'] or '-'}), color {q['color']}, "
                     f"tamano {q['bbox'][1][0] - q['bbox'][0][0]:.2f}x{q['bbox'][1][1] - q['bbox'][0][1]:.2f}x{q['bbox'][1][2] - q['bbox'][0][2]:.2f} m, "
                     f"altura {q['bbox'][0][2]:.2f}-{q['bbox'][1][2]:.2f} m" for q in datos["partes"])

def guion_modelo(op, pr):
    p = pr.params; datos = datos_modelo(pr); info = pr.d.get("modelo_3d_info", {})
    desc = op.descripcion or pr.d["descripcion"]
    hojas = [h.get("hoja") for h in pr.d["historial"] if h["etapa"] == "modelo" and h.get("hoja")]
    texto = (f"VOCABULARIO PERMITIDO\n{CP.vocabulario_tecnico(p)}\n\n{instrucciones_formato(p)}\n\nDESCRIPCION DEL USUARIO:\n{desc}\n\n"
             f"MODELO: «{info.get('nombre', '')}» ({info.get('fuente', '')}), {datos['alto']:.2f} m de alto.\nPARTES:\n{texto_partes(datos)}")
    partes = [{"text": texto}] + ([IA.imagen(pr.p(hojas[-1]))] if hojas else [])
    log(f"[0 guion] {op.modelo} agrupa las {len(datos['partes'])} partes del modelo y escribe la explicacion…")
    bruto, meta = IA.llamar(op, partes, SISTEMA_MODELO, CP.esquema_guion_modelo([q["id"] for q in datos["partes"]]), 0.6)
    g, av = CP.validar_guion_modelo(bruto, datos, p)
    registrar_ia(pr, "guion_modelo", meta, avisos=av)
    log(f"    {meta['segundos']} s, {meta.get('tokens_entrada')} tokens de entrada")
    for a in av: log(f"    aviso: {a}")
    archivar(pr.dir, "guion.json"); escribir(pr.p("guion.json"), g)
    pr.registrar("guion", pr.p("guion.json"), escenas=len(g["escenas"]), avisos=av, modelo=True)
    resumen_guion(g)
    return pr

def resumen_guion(g):
    log(f"    «{g['titulo']}» — {g['sinopsis']}")
    if g.get("estilo") == "tecnico":
        log(f"    objeto: {g['objeto']['nombre']} ({len(g['piezas'])} piezas: " + ", ".join(p['id'] for p in g['piezas']) + ")")
        for e in g["escenas"]:
            log(f"    E{e['id']} [{e['camara']['plano']}/{e['camara']['movimiento']}] +{','.join(e['aparecen']) or '-'}  {e['descripcion'][:60]}")
        return
    log(f"    personajes: " + ", ".join(f"{p['nombre']} ({p['tipo']}, voz {p['voz']})" for p in g["personajes"]))
    for e in g["escenas"]:
        log(f"    E{e['id']} [{e['camara']['plano']}/{e['camara']['movimiento']}] {e['descripcion'][:70]}")

# ================================================================ MODOS 1, 2, 4 y efectos (Blender)
def etapa_blender(pr, etapa, script, entrada, nombre, extra=()):
    salida = ruta_nueva(pr.p(nombre))
    if es_tecnico(pr) and etapa in ("objetos", "rig", "animacion", "efectos"):
        script, extra = "b_tecnico.py", ["--etapa", etapa] + list(extra)
    inf = blender(script, ["--proyecto", pr.dir, "--salida", salida] + list(extra), blend=entrada)
    pr.registrar(etapa, salida, informe=inf)
    log(f"    {json.dumps(inf, ensure_ascii=False)[:400]}\n    -> {salida}")
    return inf

def modo_objetos(op, pr=None, previa=None):
    pr = pr or abrir_o_crear(op); pr.necesita("guion")
    log("[1 objetos] " + ("dibujando las piezas, sus versiones de rayos X y el entorno" if es_tecnico(pr) else "dibujando escenarios, elementos y personajes con Grease Pencil"))
    inf = etapa_blender(pr, "objetos", "b_objetos.py", None, "01_objetos.blend", extra=["--previa", previa, "--frames", "1"] if previa else ())
    for a in inf.get("avisos_adornos") or []: log(f"    aviso: {a}")
    return inf

# ================================================================ MODO detalles (estilo tecnico): adornos sobre las piezas
SISTEMA_DETALLES = """Eres el ilustrador de detalles de un video tecnico isometrico dibujado con Grease Pencil. Las piezas ya
estan modeladas con primitivas lisas. Tu trabajo es anadir ADORNOS que las hagan reconocibles y ricas, como una
ilustracion isometrica detallada: pantallas encendidas con iconos, luces LED, rejillas, bahias de rack, tiradores,
tornillos, placas, teclados, franjas de color, carteles con icono encima...

DONDE: cada adorno va en una cara de una pieza. La camara mira desde delante a la izquierda y desde arriba: en cajas y
paneles se ven 'frente' (la mas visible), 'izquierda' y 'arriba'; 'derecha' y 'atras' NO se ven. En cilindros, tubos y
conos, 'lado' (la parte que mira a camara) o 'arriba'; en esferas, 'lado'. u y v son el centro del adorno en la cara
(0-1: u de izquierda a derecha, v de abajo arriba; en 'arriba', v va hacia el fondo); ancho y alto son la fraccion de la
cara que ocupa (0-1). Que no se salga de la cara ni se solape con otro adorno de la misma cara; deja aire alrededor.
Un 'cartel' va siempre en 'arriba' y se levanta sobre la pieza mirando a camara: usalo solo en 3-5 componentes
clave y con el simbolo de lo que es el componente (lambda en una funcion, base_datos en una base de datos...). Una
pantalla con piezas del guion delante (barras, indicadores) lleva icono 'ninguno'.

QUE: el adorno cuenta que es cada pieza (un servidor: ranuras de rack + leds + rejilla + pantalla pequena; una base de
datos: franjas + leds + icono base_datos; una funcion o herramienta: icono o cartel con su simbolo; un control de acceso:
pantalla + boton + cartel con candado o escudo; un portatil: pantalla con icono + teclado; una pantalla de monitorizacion:
pantalla grande con icono 'traza' o 'barras'). Componentes principales: los que pida la densidad; piezas pequenas,
internas o de detalle: 0-2; liquidos, transparentes, mangueras y varillas: ninguno (las mangueras llevan conectores
solos). Las piezas que estan DENTRO de una carcasa solo se ven con rayos X: adornalas poco.
COLOR: de la paleta. Luces y pantallas en lima, menta, cielo, amarillo o rojo (brillan); placas y franjas en un tono que
contraste con la pieza; iconos claros (blanco_hueso) sobre piezas oscuras y oscuros (gris_oscuro) sobre claras.
Si hay IMAGEN DE REFERENCIA, imita su nivel de detalle y el tipo de adornos de cada componente (no su estilo de dibujo:
el dibujo sigue siendo plano con tinta)."""

def piezas_para_detalles(g):
    filas = []
    for p in g["piezas"]:
        med = ", ".join(f"{k}={p[k]:.2f}" for k in CP.MEDIDAS_FORMA.get(p["forma"], ()) if isinstance(p.get(k), (int, float)))
        if p["forma"] == "icono":           # ya viene detallado: solo como contexto
            filas.append(f"- {p['id']}: {p['nombre']} (objeto-icono {p['modelo']} ya detallado, tamano {p['alto']:.2f}; "
                         f"en x={p['x']:.2f} y={p['y']:.2f}; NO admite adornos)"); continue
        caras = ", ".join(CP.CARAS_FORMA.get(p["forma"], [])[:3]) or "ninguna"
        filas.append(f"- {p['id']}: {p['nombre']} ({p['forma']}, {med}; en x={p['x']:.2f} y={p['y']:.2f} z={p['z']:.2f}; "
                     f"{p['color']}, {p['material']}{', dentro de ' + p['padre'] if p.get('padre') else ''}; caras visibles: {caras})")
    return "\n".join(filas)

def adornables(g):
    return [p["id"] for p in g["piezas"] if CP.CARAS_FORMA.get(p["forma"]) and p["material"] not in ("liquido", "transparente")]

def modo_detalles(op, pr=None, completar=None):
    """Adornos con Gemini. completar=True: conserva los que hay y solo pide los de piezas sin adornos (las que anade una revision)."""
    pr = pr or abrir_o_crear(op)
    if not es_tecnico(pr): raise SystemExit("El modo detalles es para el estilo tecnico (--estilo tecnico)")
    pr.necesita("guion"); g = leer(pr.p("guion.json"))
    completar = getattr(op, "completar", False) if completar is None else completar
    datos = leer(pr.archivo("detalles")) if (completar and pr.archivo("detalles") and os.path.exists(pr.archivo("detalles"))) else {}
    previos = datos.get("adornos", []); vistas = set(datos.get("consideradas", [])) | {a["pieza"] for a in previos}
    ids = {p["id"] for p in g["piezas"]}
    conservar = [a for a in previos if a["pieza"] in ids and a["tipo"] != "conector"]
    objetivo = [i for i in adornables(g) if i not in vistas] if completar else adornables(g)    # vistas: ya se pidieron (con o sin adornos)
    if completar and not objetivo:
        log("[detalles] todas las piezas tienen ya sus adornos"); return modo_objetos(op, pr)
    carpeta = ruta_nueva(pr.p("detalles")); os.makedirs(carpeta)
    hay = pr.archivo("detalles") and os.path.exists(pr.archivo("detalles"))
    densidad = getattr(op, "densidad", None) or (leer(pr.archivo("detalles")).get("densidad") if hay else None) or "media"
    densidad = densidad if densidad in CP.DENSIDADES else "media"
    ref = getattr(op, "referencia", None) or pr.d.get("referencia_detalles")
    log(f"[detalles] adornos {'para ' + ', '.join(objetivo) if completar else 'sobre las piezas'} (densidad {densidad}"
        f"{', referencia ' + os.path.basename(ref) if ref else ''})")
    lisas = os.path.join(carpeta, "antes.png")
    blender("b_tecnico.py", ["--etapa", "objetos"] + ([] if completar else ["--sin-adornos", "1"]) + ["--proyecto", pr.dir,
                             "--salida", os.path.join(carpeta, "lisas.blend"), "--previa", lisas.replace("antes", "antes_#"), "--frames", "1"])
    shutil.move(lisas.replace("antes", "antes_1"), lisas); os.remove(os.path.join(carpeta, "lisas.blend"))
    texto = (f"VOCABULARIO PERMITIDO\n{CP.vocabulario_adornos(pr.params)}\n\nDENSIDAD: {densidad} = {CP.DENSIDADES[densidad]}\n\n"
             f"DE QUE TRATA EL VIDEO: {pr.d['descripcion'][:1500]}\n\nPIEZAS (id: nombre, forma y medidas en metros):\n"
             f"{piezas_para_detalles(g)}\n\nLa primera imagen es la maqueta tal como esta ahora"
             + (" (ya con adornos en casi todas las piezas)." if completar else " (piezas lisas)."))
    if CP.tema_tecnico(pr.params)["carteles"] == "todos":
        texto += ("\n\nTEMA: como en la referencia, CADA componente principal (los que estan sobre una peana) lleva su "
                  "'cartel' con el simbolo de lo que es, ademas de sus otros adornos. Las peanas no llevan adornos.")
    if completar:
        texto += ("\n\nCOMPLETAR: las demas piezas ya tienen adornos (abajo). Anade adornos SOLO a estas piezas: "
                  f"{', '.join(objetivo)}. Que sean coherentes con los de piezas parecidas (mismo tipo de cartel, iconos y colores).\n"
                  "ADORNOS EXISTENTES:\n" + "\n".join(f"- {a['pieza']}: {a['tipo']} en {a['cara']}, {a['color']}" + (f", icono {a['icono']}" if a.get("icono") else "")
                                                         for a in conservar))
    partes = [{"text": texto}, IA.imagen(lisas)]
    if ref:
        ext = os.path.splitext(ref)[1].lower(); mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
        copia = os.path.join(carpeta, "referencia" + ext); shutil.copy2(ref, copia)
        pr.d["referencia_detalles"] = os.path.abspath(ref); pr.guardar()
        partes += [{"text": "IMAGEN DE REFERENCIA: el nivel de detalle y el tipo de adornos que se buscan."}, IA.imagen(copia, mime)]
    if op.ejemplo:
        bruto = {"adornos": []}; log("    (--ejemplo: sin IA, solo conectores)")
    else:
        log(f"    {op.modelo} decide los adornos…")
        bruto, meta = IA.llamar(op, partes, SISTEMA_DETALLES, CP.esquema_adornos(), 0.5)
    lista, av = CP.validar_adornos(bruto, g, params=pr.params)
    if completar:      # se conservan los de antes; de lo nuevo, solo lo de las piezas pedidas (+ conectores de todas las mangueras)
        lista = conservar + [a for a in lista if a["tipo"] == "conector" or (a["pieza"] in objetivo)]
    if not op.ejemplo: registrar_ia(pr, "detalles", meta, avisos=av, adornos=len(lista))
    for a in av[:8]: log(f"    aviso: {a}")
    archivar(pr.dir, "adornos.json")
    escribir(pr.p("adornos.json"), dict(adornos=lista, densidad=densidad, referencia=pr.d.get("referencia_detalles"),
                                        consideradas=sorted((vistas if completar else set()) | set(objetivo))))
    por_tipo = {}
    for a in lista: por_tipo[a["tipo"]] = por_tipo.get(a["tipo"], 0) + 1
    pr.registrar("detalles", pr.p("adornos.json"), adornos=len(lista), por_tipo=por_tipo, carpeta=os.path.relpath(carpeta, pr.dir))
    log(f"    {len(lista)} adornos: " + ", ".join(f"{k} {v}" for k, v in sorted(por_tipo.items(), key=lambda kv: -kv[1])))
    despues = os.path.join(carpeta, "despues_#.png")
    modo_objetos(op, pr, previa=despues)
    despues = despues.replace("#", "1")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", lisas, "-i", despues, "-filter_complex",
                        "[0:v]scale=960:-2[a];[1:v]scale=960:-2[b];[a][b]vstack=inputs=2", os.path.join(carpeta, "comparativa.png")],
                       check=True, capture_output=True)
        log(f"    -> {os.path.join(carpeta, 'comparativa.png')}")
    except Exception as e:
        log(f"    (sin comparativa: {e})")
    return lista

def modo_rig(op, pr=None):
    pr = pr or abrir_o_crear(op); ent = pr.necesita("objetos")
    log("[2 rig] esqueletos para personajes y elementos")
    inf = etapa_blender(pr, "rig", "b_rig.py", ent, "02_rig.blend")
    if inf.get("desvio_max", 0) > 1e-3: log(f"    AVISO: el rig movio trazos en reposo: {inf.get('desviados')}")
    return inf

def modo_audio(op, pr=None):
    pr = pr or abrir_o_crear(op); pr.necesita("guion")
    g = leer(pr.p("guion.json")); p = pr.params
    audio = op.audio or pr.d.get("audio_propio")
    if audio:
        log(f"[3 audio] sincronizando con tu audio: {audio}")
        pr.d["audio_propio"] = os.path.abspath(audio); pr.guardar()
        t = AU.usar_audio_propio(op, g, p, pr.dir, audio, log=log)
    else:
        log(f"[3 audio] voces {'(silencio, sin red)' if p['voz_narrador'] == CP.VOZ_SILENCIO else 'Gemini TTS ' + p['modelo_tts']}")
        t = AU.generar_tts(op, g, p, pr.dir, log=log)
    archivar(pr.dir, "tiempos.json"); escribir(pr.p("tiempos.json"), t)
    pr.registrar("audio", pr.p("tiempos.json"), duracion=t["duracion"], fotogramas=t["frame_fin"], fuente=t["fuente"])
    log(f"    {t['duracion']:.1f} s, {t['frame_fin']} fotogramas a {t['fps']} fps")
    for e in t["escenas"]: log(f"    E{e['id']}: {e['t0']:.1f}-{e['t1']:.1f} s, {len(e['lineas'])} lineas")
    return t

def modo_animacion(op, pr=None):
    pr = pr or abrir_o_crear(op); ent = pr.necesita("rig"); pr.necesita("audio")
    log("[4 animacion] personajes, escenografia y camara al ritmo del audio")
    return etapa_blender(pr, "animacion", "b_animacion.py", ent, "04_animacion.blend")

def modo_efectos(op, pr=None):
    pr = pr or abrir_o_crear(op); ent = pr.necesita("animacion")
    log("[efectos] bocadillos, cartelas, onomatopeyas y lineas de accion")
    return etapa_blender(pr, "efectos", "b_efectos.py", ent, "04b_efectos.blend")

# ================================================================ previa + revision
SISTEMA_REVISION = SISTEMA_GUION + """

AHORA ERES TAMBIEN EL REVISOR. Recibes el guion aplicado y un fotograma clave (al 60 %) de cada escena, en orden.
Evalua: que los personajes se vean bien (encuadre, que nada los tape, que no queden fuera de cuadro), que la
composicion y el color funcionen, que bocadillos y efectos no tapen lo importante, y que cada imagen cuente lo que
dice su escena. Si algo falla, devuelve en 'guion' el guion COMPLETO corregido con cambios minimos (x de personajes y
elementos, filas de profundidad, planos y objetivos de camara, acciones, efectos, colores). Conserva ids y el texto de
las lineas salvo que sea incoherente (cambiar texto obliga a regenerar voces). Si todo esta bien, cumple=true y no
devuelvas guion."""

def esquema_revision(tec=False):
    return {"type": "OBJECT", "properties": {
        "problemas": {"type": "ARRAY", "items": {"type": "STRING"}}, "puntuacion": {"type": "INTEGER", "minimum": 0, "maximum": 10},
        "cumple": {"type": "BOOLEAN"}, "guion": CP.esquema_guion_tecnico() if tec else CP.esquema_guion()},
        "required": ["problemas", "puntuacion", "cumple"], "propertyOrdering": ["problemas", "puntuacion", "cumple", "guion"]}

def render_previa(pr, n):
    ent = pr.necesita("efectos"); carpeta = pr.p(f"previa/iter_{n}")
    if os.path.exists(carpeta): carpeta = ruta_nueva(carpeta)
    inf = blender("b_render.py", ["--proyecto", pr.dir, "--fotogramas", "auto", "--carpeta", carpeta, "--calidad", "previa"], blend=ent)
    hoja = os.path.join(carpeta, "hoja.png")
    imgs = [i["png"] for i in inf.get("imagenes", [])]
    try:
        cols = 3 if len(imgs) > 4 else 2
        filtro = "".join(f"[{i}:v]scale=640:-2[v{i}];" for i in range(len(imgs)))
        filas = (len(imgs) + cols - 1) // cols
        lay = "|".join(f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}" for i in range(len(imgs)))
        if len(imgs) > 1:
            subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", i] for i in imgs], []) +
                           ["-filter_complex", f"{filtro}{''.join(f'[v{i}]' for i in range(len(imgs)))}xstack=inputs={len(imgs)}:layout={lay}:fill=white", hoja],
                           check=True, capture_output=True)
    except Exception as e:
        log(f"    (sin hoja de contactos: {e})")
    return imgs, carpeta, hoja

def reconstruir(op, pr):
    if es_tecnico(pr) and pr.archivo("detalles") and not op.ejemplo and not getattr(op, "sin_detalles", False):
        modo_detalles(op, pr, completar=True)      # adornos para las piezas que haya anadido la revision (y objetos)
    else: modo_objetos(op, pr)
    modo_rig(op, pr)
    modo_audio(op, pr)            # las voces sin cambios salen de la cache (no se vuelven a pagar)
    modo_animacion(op, pr); modo_efectos(op, pr)

def modo_previa(op, pr=None):
    pr = pr or abrir_o_crear(op)
    iteraciones = max(1, op.iteraciones)
    mejor = None                  # (puntuacion, guion): una correccion que empeora se deshace
    for n in range(1, iteraciones + 1):
        log(f"[previa] iteracion {n}: un fotograma por escena")
        imgs, carpeta, hoja = render_previa(pr, n)
        log(f"    {len(imgs)} imagenes en {carpeta}" + (f"  (hoja: {hoja})" if os.path.exists(hoja) else ""))
        pr.registrar("previa", carpeta, imagenes=len(imgs))
        if op.sin_revision or op.ejemplo: return
        g = leer(pr.p("guion.json"))
        log(f"    revision de {op.modelo}…")
        partes = [{"text": f"VOCABULARIO PERMITIDO\n{CP.vocabulario_tecnico(pr.params) if es_tecnico(pr) else CP.vocabulario_texto()}\n\n{instrucciones_formato(pr.params)}\n\n"
                           f"DESCRIPCION ORIGINAL: {pr.d['descripcion']}\n\nGUION APLICADO (ya validado: sin las medidas que cada forma no usa "
                           f"y sin campos internos; no lo cuentes como fallo):\n{json.dumps(guion_para_revision(g), ensure_ascii=False)}\n\n"
                           + (("COMPROBACIONES AUTOMATICAS DE GEOMETRIA:\n- " + "\n- ".join(CP.revisar_geometria(g)) + "\n\n") if es_tecnico(pr) and CP.revisar_geometria(g) else "") +
                           f"Siguen {len(imgs)} imagenes: la imagen i es la escena i."}] + [IA.imagen(i) for i in imgs]
        if tiene_modelo(pr):
            dm = datos_modelo(pr)
            partes[0]["text"] += f"\n\nPARTES DEL MODELO:\n{texto_partes(dm)}"
            esq = esquema_revision(True); esq["properties"]["guion"] = CP.esquema_guion_modelo([q["id"] for q in dm["partes"]])
            rev, meta = IA.llamar(op, partes, SISTEMA_REVISION_MODELO, esq, 0.3)
        else:
            rev, meta = IA.llamar(op, partes, SISTEMA_REVISION_TECNICO if es_tecnico(pr) else SISTEMA_REVISION, esquema_revision(es_tecnico(pr)), 0.3)
        registrar_ia(pr, "revision", meta, iteracion=n, problemas=rev.get("problemas"), puntuacion=rev.get("puntuacion"))
        log(f"    puntuacion {rev.get('puntuacion')}/10, cumple={rev.get('cumple')}")
        for pb in rev.get("problemas", [])[:8]: log(f"      - {pb}")
        escribir(os.path.join(carpeta, "revision.json"), rev)
        punt = rev.get("puntuacion") or 0
        if mejor is not None and punt < mejor[0]:
            log(f"    la correccion empeoro ({punt} < {mejor[0]}): vuelvo al guion de {mejor[0]}/10 y lo reconstruyo")
            archivar(pr.dir, "guion.json"); escribir(pr.p("guion.json"), mejor[1])
            pr.registrar("guion", pr.p("guion.json"), origen=f"restaurado (mejor puntuacion {mejor[0]})")
            reconstruir(op, pr)
            return
        mejor = (punt, g)
        if rev.get("cumple") or not rev.get("guion") or n == iteraciones:
            if not rev.get("cumple") and rev.get("guion") and n == iteraciones:
                escribir(os.path.join(carpeta, "guion_propuesto.json"), validador(pr)(rev["guion"], pr.params)[0])
                log(f"    (ultima iteracion: la propuesta queda en {carpeta}/guion_propuesto.json sin aplicar)")
            return
        nuevo, av = validador(pr)(rev["guion"], pr.params)
        cambia_audio = [[(l["quien"], l["texto"], l["emocion"]) for l in e["lineas"]] for e in nuevo["escenas"]] != \
                       [[(l["quien"], l["texto"], l["emocion"]) for l in e["lineas"]] for e in g["escenas"]]
        archivar(pr.dir, "guion.json"); escribir(pr.p("guion.json"), nuevo)
        pr.registrar("guion", pr.p("guion.json"), origen=f"revision {n}", avisos=av)
        log(f"    aplicado el guion corregido ({'con' if cambia_audio else 'sin'} cambios de audio); rehaciendo 1-4")
        reconstruir(op, pr)

# ================================================================ MODO 5 render y montaje
def modo_render(op, pr=None):
    pr = pr or abrir_o_crear(op); ent = pr.necesita("efectos")
    w, h, pct = CP.resolucion(pr.params)
    log(f"[5 render] EEVEE {w * pct // 100}x{h * pct // 100}, {pr.params['fps']} fps")
    video = ruta_nueva(pr.p("render/animacion.mp4")); vin = ruta_nueva(pr.p("render/vinetas"))
    inf = blender("b_render.py", ["--proyecto", pr.dir, "--video", video, "--vinetas", vin], blend=ent)
    pr.registrar("render", video, vinetas=os.path.relpath(vin, pr.dir), informe=inf)
    pr.d["vinetas"] = os.path.relpath(vin, pr.dir); pr.guardar()
    log(f"    {inf.get('fotogramas')} fotogramas en {inf['_segundos']} s\n    -> {video}")
    return video

def modo_montaje(op, pr=None):
    pr = pr or abrir_o_crear(op); video = pr.necesita("render")
    vin = pr.p(pr.d.get("vinetas", "render/vinetas"))
    final = ruta_nueva(pr.p("final/final.mp4")); pagina = ruta_nueva(pr.p("final/pagina_comic.png"))
    log("[montaje] cartelas, video final y pagina de comic")
    inf = blender("b_montaje.py", ["--proyecto", pr.dir, "--video", video, "--vinetas", vin, "--salida", ruta_nueva(pr.p("06_montaje.blend")),
                                   "--final", final, "--pagina", pagina])
    gif = ruta_nueva(pr.p("final/animacion.gif"))
    ancho = 480 if pr.params["orientacion"] == "horizontal" else 270
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf",
                        f"fps=12,scale={ancho}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer",
                        gif], check=True, capture_output=True)
        inf["gif"] = gif
    except Exception as e:
        log(f"    (sin GIF: {e})")
    pr.registrar("montaje", final, pagina=os.path.relpath(pagina, pr.dir), gif=os.path.relpath(gif, pr.dir) if inf.get("gif") else None)
    log(f"    -> {final}\n    -> {pagina}" + (f"\n    -> {gif}" if inf.get("gif") else ""))
    return inf

def modo_todo(op):
    pr = abrir_o_crear(op, crear=True)
    if es_tecnico(pr) and getattr(op, "modelo_3d", None) and not tiene_modelo(pr): modo_modelo(op, pr)
    pr = modo_guion(op, pr)
    if es_tecnico(pr) and not getattr(op, "sin_detalles", False): modo_detalles(op, pr)     # adornos + objetos
    else: modo_objetos(op, pr)
    modo_rig(op, pr); modo_audio(op, pr); modo_animacion(op, pr); modo_efectos(op, pr)
    modo_previa(op, pr)
    modo_render(op, pr); modo_montaje(op, pr)
    log(f"\nListo: {pr.dir}")

def modo_estado(op):
    pr = abrir_o_crear(op)
    log(f"Proyecto {pr.dir}\n  {pr.d['descripcion']}\n  parametros: {json.dumps(pr.params, ensure_ascii=False)}")
    for e in ETAPAS:
        a = pr.archivo(e)
        log(f"  {e:10s} {'OK  ' + os.path.relpath(a, pr.dir) if a and os.path.exists(a) else '--'}")

# ================================================================ CLI
def main():
    ap = argparse.ArgumentParser(description="Agente de animacion de comic con Grease Pencil (Blender + Gemini)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", help="materiales, biblioteca, modelo, guion(0), detalles, objetos(1), rig(2), audio(3), animacion(4), efectos, previa, render(5), montaje, todo, estado")
    ap.add_argument("--proyecto", help="carpeta del proyecto (por defecto, el ultimo)")
    ap.add_argument("--descripcion", help="la historia que quieres, en lenguaje natural")
    ap.add_argument("--ejemplo", action="store_true", help="usa el guion de ejemplo (sin IA)")
    ap.add_argument("--audio", help="audio propio (wav/mp3/...) con la narracion; se transcribe y manda en los tiempos")
    ap.add_argument("--iteraciones", type=int, default=2, help="vueltas de previa + revision (por defecto 2)")
    ap.add_argument("--sin-revision", action="store_true", help="la previa solo renderiza, sin Gemini")
    ap.add_argument("--forzar", action="store_true", help="materiales: vuelve a descargar aunque ya existan")
    ap.add_argument("--param", action="append", help="cualquier parametro clave=valor (ver comic_parametros.PARAMS)")
    ap.add_argument("--modelo-3d", dest="modelo_3d", help="estilo tecnico: 'auto' (busca en Poly Haven/Sketchfab y Gemini elige), "
                    "polyhaven:<id>, URL de Poly Haven o Sketchfab, uid de Sketchfab, o un archivo .glb/.gltf/.obj/.fbx/.stl/.blend")
    ap.add_argument("--referencia", help="detalles (estilo tecnico): imagen de referencia del nivel de detalle y los adornos que se buscan")
    ap.add_argument("--densidad", choices=list(CP.DENSIDADES), help="detalles: cuantos adornos por componente (por defecto media)")
    ap.add_argument("--sin-detalles", dest="sin_detalles", action="store_true", help="todo (estilo tecnico): no anade adornos")
    ap.add_argument("--completar", action="store_true", help="detalles: conserva los adornos y solo anade los de piezas sin ellos")
    ap.add_argument("--licencias", default="cc0,cc-by", help="licencias aceptadas de Sketchfab: cc0, cc-by, cc-by-sa (por defecto cc0,cc-by)")
    for k, tipo, dflt, opc, desc in CP.PARAMS:
        flag = "--" + k.replace("_", "-"); desc = f"{desc} (por defecto {dflt})".replace("%", "%%")
        if tipo == "BOOL": ap.add_argument(flag, dest=k, type=lambda s: s.lower() in ("1", "true", "si", "sí", "yes"), help=desc)
        elif tipo == "INT": ap.add_argument(flag, dest=k, type=int, help=desc)
        elif tipo == "FLOAT": ap.add_argument(flag, dest=k, type=float, help=desc)
        else: ap.add_argument(flag, dest=k, choices=opc if opc else None, help=desc)
    ap.add_argument("--modelo", default=IA.MODELO, help=f"modelo Gemini (por defecto {IA.MODELO}; rapido: {IA.MODELO_RAPIDO})")
    ap.add_argument("--cuenta", default=IA.CUENTA); ap.add_argument("--proyecto-gcp", dest="proyecto_gcp", default=IA.PROYECTO)
    ap.add_argument("--region", default=IA.REGION)
    op = ap.parse_args()
    modo = NUMEROS.get(op.modo, op.modo)
    funciones = {"materiales": modo_materiales, "biblioteca": modo_biblioteca, "modelo": modo_modelo, "guion": modo_guion, "objetos": modo_objetos,
                 "detalles": modo_detalles, "rig": modo_rig, "audio": modo_audio, "animacion": modo_animacion, "efectos": modo_efectos,
                 "previa": modo_previa, "render": modo_render, "montaje": modo_montaje, "todo": modo_todo, "estado": modo_estado}
    if modo not in funciones: ap.error(f"modo desconocido: {op.modo}")
    if not os.path.exists(CP.FUENTE_TITULOS) and modo not in ("materiales", "estado"):
        log("Faltan las fuentes descargadas: ejecuto antes el modo materiales")
        modo_materiales(op)
    try:
        funciones[modo](op)
    except IA.ErrorIA as e:
        raise SystemExit(f"Error de Vertex AI: {e}")

if __name__ == "__main__":
    main()
