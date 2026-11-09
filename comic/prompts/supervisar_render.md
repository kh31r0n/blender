# Prompt: supervisar el render de un vídeo del agente de animación

Pega este texto en una sesión nueva de Claude Code abierta en `~/blender`, o lánzalo con `claude -p "$(cat ~/blender/comic/prompts/supervisar_render.md)"`.

Antes de pegarlo, cambia la línea `P=` de «Proyecto» si quieres supervisar otro vídeo.

*Actualizado el 2026-11-09. Recoge los temas cyberpunk y cristal, Cycles en la GPU, los paneles de datos y los **subtítulos** con Motion Canvas, el **revelado** de las mangueras en los temas con mallas, el **ajuste de la maqueta** (mangueras con sobres de al menos 1 m y mangueras que no aparecen antes que lo que unen), el encuadre de las escenas con flujo y las regresiones conocidas.*

---

## Tu papel

Eres el **supervisor de render** de un vídeo explicativo generado por un agente propio. Tu trabajo:
1. Ejecutar las etapas del agente en orden.
2. Vigilar cada una mientras corre.
3. Verificar el resultado con los criterios medibles de este documento.
4. Entregar un informe.

**No eres el guionista ni el diseñador:** no cambias contenido, parámetros ni código. Si algo debe cambiar, te detienes y propones el cambio exacto, con la evidencia. Trabaja y responde en español.

## Contexto fijo

**Antes de empezar, lee:**
- `~/blender/CLAUDE.md`: reglas del entorno, sobre todo las de Blender sin interfaz, Grease Pencil y Cycles en la GPU;
- `~/blender/comic/README.md`: el agente, sus etapas, los temas del estilo técnico (sección «Temas y objetos-icono») y los paneles de datos (sección «Paneles de datos con Motion Canvas»).

**Herramientas:**
- **Máquina:** Linux, GPU RTX 4060 (más una Intel UHD 770 integrada, que no se usa para renderizar).
- **Blender:** 5.2.2, en `~/.local/bin/blender`. Solo se usa sin interfaz; el agente ya lo llama así.
- **Agente:** `~/blender/comic/agente_comic.py`, con un modo por etapa. Se ejecuta siempre desde `~/blender/comic`.
- **Motion Canvas** (paneles de datos y subtítulos): proyecto en `~/blender/comic/motion` (Node 24 en `~/.local/bin/node`, dependencias en `node_modules`, instaladas con `npm ci`). El agente lo renderiza sin interfaz con `node render.mjs`, que abre `/usr/bin/google-chrome` en modo headless; no hay que abrir nada a mano.

**Proyecto** (elige uno y déjalo en `P`):

```
P=proyectos/20261108-120000_agente_soc_cristal
```

Los tres proyectos del vídeo SOC comparten guion, narración y voces; cambia el tema.

| Proyecto (`proyectos/…`) | Tema | Motor | Aspecto | Coste por fotograma (1080p) | Render completo (~3246 fotogramas) |
|---|---|---|---|---|---|
| `20261108-042439_como_un_agente_de_ia_que_tria_alertas_de` | `neon` | Cycles (parámetro `motor`) | Grease Pencil: suelo claro, peanas luminosas, colores vivos | ~0,5 s | ~30 min |
| `20261108-110000_agente_soc_cyberpunk` | `cyberpunk` | EEVEE (lo impone el tema) | Mallas toon, contornos negros con Line Art, fondo casi negro, neón con bloom mínimo | ~0,5 s | ~30 min |
| `20261108-120000_agente_soc_cristal` | `cristal` | Cycles (lo impone el tema) | Cristal translúcido con bordes de luz, líneas finas con nodos, circuito sobre azul marino | ~2–3,5 s | ~1,5–3 h |

**Tema `arcilla`** (Cycles en la GPU, sin Grease Pencil): proyecto de prueba `20261109-102341_video_1_managers_tema_arcilla`, copia del vídeo 1 para managers. ~4–5 s por fotograma al 100 % (el primer fotograma de cada proceso tarda ~1 min más: OptiX compila los núcleos con AO): unas 2,5 h para 2 000 fotogramas.

**Vídeos para managers** (verticales 1080×1920, 80–100 s, tema `cyberpunk`, con **paneles de datos de Motion Canvas** en la franja de arriba y **subtítulos** en el tercio inferior): por ejemplo `20261108-154600_video_1_para_managers_que_es_el_aprendiz` y `20261108-205522_video_4_para_managers_flujo_de_desarroll`. Cuestan ~0,45 s por fotograma (EEVEE): el 2026-11-09, el vídeo 1 renderizó 2 001 fotogramas en 15 min.

**Qué es el vídeo:**
- **Contenido:** «Cómo un agente de IA que tría alertas de seguridad (SOC) ahorra tiempo y dinero»: correlación de alertas en DynamoDB, reutilización de respuestas y prompt caching. 21 escenas con narración en español.
- **Formato:** 1920×1080 a 24 fps.
- **Voz:** Charon, con `gemini-2.5-pro-tts` y `ritmo_voz` 2,6.

**Estado:** cambia a menudo. Compruébalo siempre con el modo `estado`; no te fíes de versiones escritas aquí.

**Paneles de datos (Motion Canvas):** en el estilo técnico con el parámetro `paneles_mc` (por defecto), la etapa `paneles` (entre `audio` y `animacion`) dibuja arriba, en las escenas con datos (`CP.escenas_con_panel`), un titular que sale palabra a palabra con la voz y un visual (contador, cifras, barras, pasos, tarjeta…). Sustituye a los datos e insignias 3D, a la tira del gancho y a la gráfica comparativa del secuenciador, y la cámara deja libre esa franja. Solo se usa si la etapa `paneles` está hecha (`archivos.paneles` en `proyecto.json`); si no, el proyecto sigue con los datos en 3D.

**Subtítulos (Motion Canvas):** con el parámetro `subtitulos` (activo por defecto en el estilo técnico), la etapa `subtitulos` (después de `paneles` y antes de `animacion`) parte la voz de `tiempos.json` en bloques de 3–6 palabras y los dibuja en el tercio inferior: mayúsculas en Archivo Black con contorno oscuro y la palabra que suena en lima. No usa Gemini: es determinista y se puede repetir sin cambiar contenido. Con la etapa hecha (`archivos.subtitulos`), la cámara deja libre la franja de abajo (`hueco_abajo` ≈ 0,22 del alto en vertical), así que **activarlos o desactivarlos obliga a rehacer `animacion`, `efectos` y el render**. El montaje los pone encima de todo (canal 4) y escribe `final/final.vN.srt`.

**Lo que hace el agente por su cuenta en `objetos`** (no es el supervisor quien cambia el contenido):
- **Ajuste de la maqueta** (`CP.ajustar_maqueta`): si una manguera por la que viajan sobres (`flujo`) mide menos de `largo_flujo` (1 m), separa las peanas con un corte por un pasillo libre; si una manguera aparece antes que alguno de los componentes que une, la pasa a la escena de ese componente con su flujo. Cuando cambia algo, archiva `guion.json` en `historial/`, lo reescribe, añade al historial una etapa `guion` con `origen: "ajuste de maqueta"` e imprime líneas `maqueta: …`. Es esperado; anótalo.
- **Revelado de mangueras** (temas `cyberpunk` y `cristal`, en `animacion`): las mangueras no caen como las demás piezas, se dibujan de su origen a su destino en 0,6 s con una chispa blanca en la punta que se apaga al llegar. Los sobres esperan a que la manguera haya llegado.
- **Cámara:** en las escenas con `flujo`, los planos medios y de detalle encuadran la manguera entera. En los planos generales, el margen de aire se reduce en proporción a los huecos del panel y los subtítulos.

**Tiempos de referencia de cada etapa:**

| Etapa | Duración |
|---|---|
| `objetos`, `rig`, `animacion`, `efectos` | 1–2 s cada una (en todos los temas) |
| `audio` | segundos si todas las líneas están en caché; varios minutos si hay líneas nuevas (el TTS pro y los reintentos de ritmo tardan) |
| `paneles` | ~40 s de render de Motion Canvas (unos 58 fotogramas/s) más, si diseña, 30–90 s de Gemini; con `--solo-render`, solo el render |
| `subtitulos` | ~30–40 s de render de Motion Canvas (2 001 fotogramas en 31 s); sin Gemini |
| `previa --sin-revision` | unos 5 s en `neon`; 10–20 s en `cyberpunk`; 1–2 min en `cristal` (Cycles) |
| `render` | ver la tabla de proyectos: fotogramas × coste por fotograma. Es una sola llamada a Blender que bloquea hasta terminar |
| `montaje` | 1–2 minutos (cartelas de título y FIN, página de cómic y GIF) |

**Gemini (Vertex AI):**
- El agente pide el token con `gcloud auth print-access-token --account=jjimenez@neosecure.com`.
- El proyecto de GCP es `project-b62861f4-f767-4aff-9f5`.
- **Nunca cambies la cuenta activa de gcloud.**
- Esa cuenta podría ser de un antiguo empleador del usuario: no la toques, pero menciónalo en el informe si falla.

## Reglas (no negociables)

1. **Nada se sobrescribe ni se borra.**
   - Cada etapa crea una versión nueva (`.v2`, `.v3`…) y `proyecto.json` apunta a la vigente.
   - No borres versiones anteriores (tampoco `paneles/fotogramas.vN/`, aunque ocupen ~170 MB cada una), ni la caché de audio (`audio/linea_*.wav`), ni logs.
2. **No toques el contenido:** ni `guion.json`, ni `adornos.json`, ni `paneles.json`, ni la narración, ni los parámetros (`--param`, `--modelo-tts`, `--motor`, `--tema`, `--subtitulos`, `--largo-flujo`…), ni el código del agente. Si encuentras un fallo, descríbelo con archivo y línea, y propón la corrección sin aplicarla.
   - **No subas `--toma-voz`:** vuelve a sintetizar todas las voces con Gemini (coste y una narración distinta). Solo si el usuario lo pide.
   - Que `objetos` reescriba `guion.json` con el ajuste de la maqueta no rompe esta regla: lo hace el agente. Anota las líneas `maqueta: …`.
3. **No publiques nada:** ni subidas, ni despliegues, ni commits, ni correos.
4. **Un solo render a la vez.**
   - Antes de empezar, `pgrep -af "blender -b|agente_comic.py|render.mjs"` tiene que salir vacío.
   - Ojo con los renders **en cola**: un `bash` que espera a que termine otro Blender para lanzar el siguiente también cuenta.
   - Si hay algo en marcha o en cola, espera o informa. **No mates procesos sin preguntar.**
5. **Paneles sin rediseño:** si ya existe `$P/paneles.json`, usa `paneles --solo-render` (vuelve a calcular los tiempos y a renderizar, sin cambiar el diseño). Solo sin `paneles.json` se lanza `paneles` a secas, que pide el diseño a Gemini: anótalo en el informe, porque cambia el contenido de la franja.
6. **Previa sin revisión de Gemini:** usa `previa --sin-revision`. La revisión puede reescribir el guion, y ya ha restaurado una versión peor por una puntuación espuria. Solo la usarás si el usuario lo pide.
7. **Reintentos:**
   - **Fallos transitorios** (red, cuota 429, proceso muerto sin Traceback): como máximo 1 reintento por etapa.
   - **Traceback de Python o de Blender:** no se reintenta; se informa.
8. **Comprobación visual:** mira las imágenes; no des nada por bueno solo porque el log no tiene errores.

## Procedimiento

### 0. Comprobaciones previas (no cambian nada)

```bash
cd ~/blender/comic
P=proyectos/20261108-120000_agente_soc_cristal          # el que hayas elegido
python3 agente_comic.py estado --proyecto $P
pgrep -af "blender -b|agente_comic.py|render.mjs" || echo "nada en marcha"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv
df -h ~/blender | tail -1                      # hacen falta al menos 3 GB libres
gcloud auth print-access-token --account=jjimenez@neosecure.com >/dev/null && echo "token ok"
python3 -c "
import json, sys; sys.path.insert(0, '.')
import comic_parametros as CP
d = json.load(open('$P/proyecto.json')); g = json.load(open('$P/guion.json'))
p = d['parametros']; t = CP.tema_tecnico(p)
print('tema:', p.get('tema'), '| motor del tema:', t.get('motor'), '| parametro motor:', p.get('motor'), '| piezas:', t.get('piezas'))
g2, av = CP.validar_guion_tecnico(g, p)
print('avisos de validacion:', av)
print('avisos de geometria:', CP.revisar_geometria(g2))
print('piezas:', len(g2['piezas']), 'escenas:', len(g2['escenas']))
p2, _ = CP.limitar_params(p)
print('paneles_mc:', p2.get('paneles_mc'), '| etapa paneles hecha:', bool(d['archivos'].get('paneles')), '| usa paneles:', CP.usa_paneles(d, p2))
print('escenas con panel:', CP.escenas_con_panel(g2, p2), '| paneles.json:', __import__('os').path.exists('$P/paneles.json'))
print('subtitulos:', p2.get('subtitulos'), '| etapa subtitulos hecha:', bool(d['archivos'].get('subtitulos')), '| usa subtitulos:', CP.usa_subtitulos(d, p2))
g3, av3 = CP.ajustar_maqueta(g, p2)
print('objetos cambiara el guion (ajuste de maqueta):', av3 or 'no')
print('largo_flujo:', p2.get('largo_flujo'), '| mangueras con flujo (m):', {h: round(CP._largo(next(q for q in g3['piezas'] if q['id'] == h)['camino']), 2) for h in sorted(CP.mangueras_flujo(g3))})"
test -d motion/node_modules/@motion-canvas/core && echo "motion canvas ok" || echo "FALTAN las dependencias de motion (npm ci)"
ls descargas/fuentes/ArchivoBlack-Regular.ttf descargas/fuentes/JetBrainsMono-Variable.ttf
```

**Paneles esperados:** si `paneles_mc` es `True` y el estilo es técnico, el vídeo debe salir con paneles. Si la etapa aún no está hecha, la cadena de la sección 1 la crea; anota que el proyecto pasa de datos 3D a paneles (la cámara y los efectos cambian).

**Subtítulos esperados:** si `subtitulos` es `True`, el vídeo debe salir con subtítulos y el montaje, con su `.srt`. Si la etapa aún no está hecha, la cadena la crea; anota que la cámara cambia (deja libre la franja de abajo).

**Ajuste de la maqueta esperado:** si `objetos cambiara el guion` no dice `no`, la etapa `objetos` reescribirá el guion (separación de peanas o mangueras que cambian de escena). La maqueta cambia de tamaño y posición, así que **la previa y el render serán distintos del montaje anterior aunque no hayas tocado nada**. Dilo antes de lanzar el render.

**Motor esperado:** si el tema impone motor (`cyberpunk` → EEVEE, `cristal` → Cycles), manda el tema. Si no, manda el parámetro `motor`. Anótalo: lo comprobarás en el render.

**Averigua qué cambió desde el último montaje:**
- **Guion:** compara `guion.json` con la versión más reciente de `historial/guion.*.json`: piezas añadidas o quitadas, texto de la narración, colores, animaciones y efectos.
- **Adornos y código:** mira las fechas de `adornos.json` y de los `.py` de `comic/` y `comic/blender/` (sobre todo `tecnico.py`, `b_tecnico.py`, `cyberpunk.py`, `gp_base.py`, `paneles_mc.py`, `subtitulos_mc.py`, `comic_parametros.py`), frente a la fecha del último `montaje` en `proyecto.json`.
- **Paneles:** fechas de `paneles.json` y de `comic/motion/src/**` y `comic/motion/renderizador/*`. Si solo cambiaron los paneles (y no la cámara ni la maqueta), basta `paneles --solo-render` y `montaje`: **no hace falta volver a renderizar Blender**. Dilo antes de lanzar un render largo.
- **Subtítulos:** fechas de `subtitulos_mc.py` y de `comic/motion/src/escenas/subtitulos.tsx`. Si solo cambió su dibujo o su reparto en bloques (no `tiempos.json`, ni si el proyecto tiene o no subtítulos), basta `subtitulos` y `montaje`, sin volver a renderizar Blender. Si el proyecto **no tenía** la etapa `subtitulos` hecha cuando se hizo `animacion`, la cámara no deja la franja libre: hay que rehacer `animacion`, `efectos` y el render.
- **Render más viejo que la animación:** si la fecha de `render` en `proyecto.json` es anterior a la de `animacion` o `efectos` (por ejemplo, porque se añadieron los paneles después), el vídeo de `render/` tiene la cámara y los datos 3D antiguos: un `montaje` pondría los paneles encima de esa película. Hay que renderizar de nuevo.
- **Si no cambió nada:** detente y pregunta antes de renderizar. Un render nuevo idéntico gasta entre 30 minutos y 3 horas de GPU para nada.

Si algo falla en este paso (falta el token, hay otro render en marcha o en cola, no hay disco o la validación da errores), detente e informa.

### 1. Ejecutar las etapas, una por una

Guarda todo en un log nuevo, sin sobrescribir nada:

```bash
LOG=$P/supervision_$(date +%Y%m%d-%H%M%S).log
PAN="paneles --solo-render"; [ -f $P/paneles.json ] || PAN="paneles"     # no rediseñar si ya hay diseño
for m in objetos rig audio "$PAN" subtitulos animacion efectos "previa --sin-revision --iteraciones 1"; do
  echo "=== $m $(date +%H:%M:%S)" | tee -a $LOG
  python3 agente_comic.py $m --proyecto $P 2>&1 | tee -a $LOG
done
```

Ejecuta las etapas en ese orden (`subtitulos` antes que `animacion`: la cámara necesita saber que hay subtítulos). Si una falla, para la cadena. Después de cada una, aplica sus comprobaciones:

| Etapa | Comprobación (criterio de aceptación) |
|---|---|
| `objetos` | En el `INFORME`, `piezas` es igual al número de piezas del guion y `avisos_adornos` está vacío. `adornos` es mayor que 0 si existe `adornos.json`. Si salen líneas `maqueta: …`, el guion se reescribió (nueva copia en `historial/`, etapa `guion` con `origen: "ajuste de maqueta"` en `proyecto.json`): comprueba con el script de la sección 0 que ahora todas las mangueras con flujo miden al menos `largo_flujo` y que un segundo `ajustar_maqueta` ya no cambia nada. Un aviso «no hay pasillo libre» es un fallo a informar (la manguera sigue corta). |
| `rig` | `desvio_max` es 0.0. `huesos` es `piezas` + 1. |
| `audio` | Comprueba `tiempos.json` (ver la tabla siguiente). |
| `paneles` | Sale una línea `E<n>: <tipo> «titular»` por cada escena de `escenas_con_panel` (ni más ni menos) y `N PNG en X s` con **N = `frame_fin`** de `tiempos.json`. Anota los `aviso:` (un visual «no válido… por reglas» es informativo: la validación quitó una cifra que no estaba en el guion). `proyecto.json` apunta a una carpeta `paneles/fotogramas.vN` nueva, con su `motion.json`. Mira 2–3 PNG sueltos de escenas distintas (con fondo transparente se ven sobre blanco o negro según el visor). Fuera del estilo técnico o con `paneles_mc` en `False`, la etapa dice «solo para el estilo tecnico» y no hace nada: no es un fallo. |
| `subtitulos` | Sale `[subtitulos] N bloques, letra L px, centro en y=… ` y `M PNG en X s` con **M = `frame_fin`**. La carpeta nueva `subtitulos/fotogramas.vN` (a la que apunta `proyecto.json`) tiene `bloques.json`, `subtitulos.srt` y `motion.json`. Comprueba en `bloques.json` que ningún bloque pasa de 6 palabras (8 en horizontal), que no se solapan (`fin` < `inicio` del siguiente) y que, unidos, sus textos son las `lineas` del guion palabra por palabra. Con `subtitulos` en `False` dice «desactivados» y no hace nada: no es un fallo. |
| `animacion` | `fotogramas` coincide con `frame_fin` de `tiempos.json`. `claves` es mayor que 0. |
| `efectos` | `avisos` es `[]`. Con paneles, `efectos` baja mucho (en los vídeos para managers, de ~116 a ~15 objetos), porque ya no se dibujan datos ni insignias 3D. |
| `previa` | Abre la `hoja.png` de la carpeta `previa/iter_*` más reciente y revísala con los criterios visuales de la sección 2. Con paneles o subtítulos, la hoja se hace con `escena_N_mc.png` (el fotograma con el panel y el subtítulo encima); si solo hay `escena_N.png`, la previa no encontró las capas de Motion Canvas. |

**Comprobación del audio** (`tiempos.json`):

| Qué | Criterio |
|---|---|
| `silabas_s` de cada línea | Entre 4,7 y 7,1 (el objetivo es 5,7). |
| Duración de cada línea (`t1 - t0`) | No más de 12 s. |
| `duracion` total | Cerca del parámetro `duracion` (±25 %): unos 80–100 s en los vídeos para managers y 110–185 s en el SOC. |
| Log | Anota cuántas líneas necesitaron «otra toma» y cuántas «ajuste atempo». |

Si una línea queda fuera de banda: informa su texto y su valor, y no la regeneres. Regenerarla exige borrar su wav en caché, y eso hay que preguntarlo antes.

### 2. Criterios visuales (previa y vídeo final)

**Comunes a todos los temas**, para cada escena de la hoja:

| Qué mirar | Defecto a señalar |
|---|---|
| **Encuadre** | La pieza o zona de la que habla la escena (columna `resaltar` y `camara.objetivo` del guion) tiene que verse entera o casi. Señala los planos generales con la maqueta diminuta en una esquina y mucho suelo vacío (regresión: el general encuadra solo lo ya montado) y los planos que cortan justo lo que se explica. |
| **Geometría** | Ninguna pieza flota, se hunde en el suelo o atraviesa otra. Las mangueras van de borde a borde y no por dentro de las piezas. Los bloques que se desplazan no cruzan otras piezas. Ninguna manguera llega a un hueco vacío: los dos componentes que une ya están en la escena en que aparece. |
| **Sobres por las mangueras** | En las escenas con `flujo`, la manguera tiene que verse entera en el plano (también en los medios) y el sobre, recorrer un tramo largo y bien visible. Señala una manguera cortada por el borde del cuadro o tan corta en pantalla que el sobre casi no se mueve (regresión de `separar_por_mangueras` o del encuadre con flujo de `b_tecnico.py`). Si la previa (al 60 % de la escena) no lo pilla, míralo en el vídeo final (sección 5). |
| **Efectos** | Cuando el guion pide `flujo`, `aprobado`, `rechazo`, `alerta`, `rayo`, `reloj` u `ondas`, el efecto se ve en el fotograma (al 60 % de la escena puede haber pasado ya; anótalo como «no verificable», no como fallo). Los efectos son Grease Pencil y se pintan siempre por encima de todo: es lo esperado. |

**Según el tema:**

| Tema | Aspecto correcto | Resalte correcto | Defectos a señalar |
|---|---|---|---|
| `neon` | Suelo claro con cuadrícula fina, cada componente sobre su peana azul luminosa, mangueras azules de neón, cartel con icono en los componentes principales | Contorno lima **continuo** del grosor de la tinta | Contorno lima a trozos, alternando con negro (regresión del z-fighting, `EMPUJE_RESALTE` en `tecnico.py`) |
| `cyberpunk` | Fondo casi negro con rejilla azul, piezas toon de colores planos con contorno negro fino (Line Art), aros cian en las peanas y mangueras de neón nítidas (bloom mínimo, sin halo). Las mangueras **se dibujan** de origen a destino con una chispa blanca en la punta, no caen | Contorno lima alrededor de la silueta (casco invertido) | Tubos o piezas transparentes rellenos de lima; adornos (pantallas, LEDs) visibles **a través** de piezas de delante (deberían ser malla); motor que no sea EEVEE (sin bandas toon); mangueras que caen desde arriba o aparecen de golpe; chispa que se queda encendida al final de la manguera |
| `cristal` | Fondo azul marino con circuito tenue, piezas de cristal translúcido tintadas por función (azul o cian; morado para bases de datos; verde para aciertos y caché; magenta para alertas y fallos), bordes azul claro **nítidos**, conexiones finas con nodos, brillo corto. Las conexiones se dibujan de origen a destino con la chispa, y sus nodos salen cuando la línea ha llegado | La pieza se aviva y se aclara un poco, con fundido, sin perder su color | Piezas resaltadas convertidas en bloques blancos opacos; bordes granulados o emborronados; halo ancho alrededor del neón |
| `arcilla` | Suelo blanco puro con una plataforma gris claro neutro bajo el workflow; todo lo opaco del MISMO plástico con grano fino (Leather039), solo cambia el color; acrílico turquesa translúcido en las cintas (se ve la banda dentro), filo cian en las peanas, tarjetas esmeriladas; acentos saturados; sombras cortas que caen hacia la cámara (luz detrás a la derecha) y sombra de contacto bajo cada pieza; marcos de carteles y alertas moldeados de una pieza; cubos naranjas sobre las cintas; desenfoque en planos medios y de detalle | La pieza se ilumina con un borde turquesa (Fresnel) con fundido | **Cualquier objeto de Grease Pencil o modificador Line Art** (compruébalo en `04b_efectos` con `bpy.data.grease_pencils` y los modificadores `LINEART`); bordes con pliegues o vértices visibles en carteles y alertas; aros de LEDs separados de su disco (imagen doble); manchas de sombra de tarjetas o iconos que flotan; acabados distintos entre objetos; blancos quemados o acentos en pastel (debe ser `Khronos PBR Neutral`); el objetivo del plano desenfocado |

**Paneles de datos (Motion Canvas)**, si el proyecto los usa:

| Qué mirar | Correcto | Defecto a señalar |
|---|---|---|
| **Dónde** | La banda oscura (con rejilla tenue, degradado y filo de acento) sale solo en las escenas de `escenas_con_panel`: arriba, el 40 % del alto en vertical; columna izquierda, el 38 % del ancho, en horizontal. En las demás escenas, la maqueta usa el cuadro entero | Banda en escenas sin datos, o escenas con datos sin banda |
| **Maqueta** | Cabe entera en la parte libre (debajo o a la derecha de la banda), centrada en ella | La banda tapa la pieza de la que habla la escena (regresión de `encuadre(hueco_arriba / hueco_izq)` en `b_tecnico.py`) |
| **Sin duplicados** | No hay etiquetas de datos ni insignias numeradas 3D junto a las piezas, ni la tira del gancho ni la gráfica comparativa del secuenciador | Datos 3D y panel a la vez: `animacion`/`efectos` se hicieron antes de la etapa `paneles`, o el render es anterior |
| **Titular** | Mayúsculas en Archivo Black, 2–6 palabras (el gancho, hasta 8), la palabra clave en color o sobre un bloque de color; no se sale de la banda ni se corta por arriba | Letra de reserva (serif o sans fina: fuentes no cargadas), texto cortado, palabras que se pisan. Al 60 % de la escena puede faltar alguna palabra que la voz aún no ha dicho: anótalo como «no verificable», no como fallo |
| **Visual** | Las cifras coinciden con el guion (`datos`, `comparativa`, `caso`); en la comparativa, barras con el resultado en lima; textos que no se pisan (etiquetas de pasos, clave y valor de la tarjeta) | Una cifra que no está en el guion (no debería pasar la validación: es un fallo), textos superpuestos, un visual vacío a mitad de escena |
| **Cinta de pasos** | Desde la primera escena del ciclo, una fila de fichas pequeñas abajo de la banda, con encendido el `paso` de la escena (en el ciclo rápido, uno cualquiera del bucle). No sale si el visual ya son los pasos | Paso activo equivocado, fichas ilegibles |

**Subtítulos (Motion Canvas)**, si el proyecto los usa:

| Qué mirar | Correcto | Defecto a señalar |
|---|---|---|
| **Dónde** | En el tercio inferior, centrados, con el borde de abajo a ~12 % del alto en vertical (margen de la interfaz del móvil); en horizontal, a ~7 % y, con paneles, centrados en la parte libre de la derecha. Nunca dentro de la banda del panel | Subtítulo pegado al borde inferior o dentro del panel |
| **Maqueta** | Lo que encuadra el plano (`camara.objetivo`/`objetivos` y, con flujo, su manguera) queda por encima del texto. Otras piezas que entran en un plano medio pueden quedar detrás del subtítulo: es aceptable (le pasa al simulador en la escena 7 del vídeo 1 para managers) | El subtítulo tapa la pieza de la que habla la escena (regresión de `hueco_abajo` en `b_tecnico.encuadre`, o `animacion` hecha antes que la etapa `subtitulos`) |
| **Texto** | 1–2 líneas, 3–6 palabras, mayúsculas en Archivo Black blanca con contorno oscuro; una sola palabra en lima (la que suena); palabras separadas | Letra de reserva; palabras pegadas («TUAEROLÍNEA»); varias palabras en lima a la vez; dos bloques a la vez; más de 2 líneas |
| **Coherencia** | Lo que dice el subtítulo es lo que dice la voz en ese momento (el bloque entra un fotograma antes de su primera palabra) | Bloque adelantado o retrasado más de ~0,3 s respecto a la voz, o texto de otra escena |

Si hay defectos graves en la previa (escenas ilegibles, piezas que se atraviesan o un aspecto que no corresponde al tema), **detente antes del render** e informa con la imagen y la escena.

### 3. Render (largo): lanzar en segundo plano y vigilar

Calcula antes el tiempo esperado: `frame_fin` de `tiempos.json` × el coste por fotograma del tema (tabla de proyectos).

```bash
echo "=== render $(date +%H:%M:%S)" | tee -a $LOG
nohup python3 agente_comic.py render --proyecto $P >> $LOG 2>&1 &
```

**En el primer minuto, comprueba que usa la GPU:**
- **Cycles:**
  - `grep -cE "libnvoptix|libcuda" /proc/<PID de blender>/maps` tiene que ser mayor que 0;
  - `nvidia-smi` debe mostrar uso alto;
  - Blender no puede estar a más del 300 % de CPU.

  Si no hay `libnvoptix`/`libcuda` cargadas y Blender está a ~1300 % de CPU con la GPU al 1 %, Cycles ha caído a CPU (regresión de `gp_base.gpu_cycles`). El vídeo tardaría horas: detente e informa.
- **EEVEE:** `nvidia-smi` debe mostrar un uso del 80–100 %.

**Después, vigila cada 60 s, sin saturar la máquina:**
- **Proceso:** `pgrep -af "blender -b"` sigue vivo.
- **Archivo:** mientras renderiza, el que crece es **`$P/render/_tmp_video_0001-<frame_fin>.mp4`** (`ls -la --time-style=+%T $P/render/`). Al terminar, el agente lo mueve a `render/animacion.vN.mp4`. Los fotogramas se escriben en bloques, así que el tamaño sube a saltos.
- **GPU:** `nvidia-smi` muestra uso.

**Alarmas:**
- **Atasco:** el archivo temporal no crece en 5 minutos (10 en `cristal`) con Blender vivo. Informa con el tamaño, la hora y el uso de GPU y CPU. Mátalo y reintenta una vez solo si no hay más remedio, y dilo en el informe.
- **Lentitud:** el doble del tiempo esperado.
- **Caída:** el proceso termina sin `fotogramas en … s` en el log. Copia las últimas 40 líneas.

**Al terminar:**
- **Formato:** con `ffprobe`, el vídeo es H.264 a 24 fps, con audio AAC, y 1920×1080 en horizontal o 1080×1920 en vertical (`orientacion`).
- **Duración:** coincide con `duracion` de `tiempos.json`, ±0,5 s.
- **Fotogramas:** los del log coinciden con `frame_fin`.
- **Dispositivo (Cycles):** el informe del render incluye `dispositivo` y debe decir `OPTIX: NVIDIA GeForce RTX 4060`. Míralo en el historial de `proyecto.json` (campo `informe` de la etapa `render`).

### 4. Montaje

```bash
echo "=== montaje $(date +%H:%M:%S)" | tee -a $LOG
python3 agente_comic.py montaje --proyecto $P 2>&1 | tee -a $LOG
```

**Comprueba:**
- existen `final/final.vN.mp4`, `final/pagina_comic.vN.png` y `final/animacion.vN.gif`, todos nuevos;
- con paneles, el log dice `paneles de Motion Canvas: paneles/fotogramas.vN` con la versión **vigente** de `proyecto.json`, y el informe de Blender trae `paneles` con `fotogramas` = `frame_fin` (tira de imagen `ALPHA_OVER` en el canal 3). Con paneles no hay cartela de título, ni tira del gancho, ni tiras de la comparativa; el GIF sale de `final.mp4` y lleva los paneles;
- con subtítulos, el log dice `subtitulos de Motion Canvas: subtitulos/fotogramas.vN` (la versión vigente) y `-> …/final/final.vN.srt`, con el mismo `vN` que el vídeo. En `proyecto.json`, el historial de `montaje` trae `srt`. El informe de Blender trae `subtitulos` con `fotogramas` = `frame_fin` (canal 4) e `inicio_video` (1 sin cartela de título);
- con `ffprobe`, el vídeo final dura lo del render más las cartelas de título y FIN, que son unos segundos.

### 5. Control de calidad del vídeo final

Usa `F=$(ls -t $P/final/final*.mp4 | head -1)`.

1. **Hoja de control:** extrae 12 fotogramas repartidos por toda la duración, móntalos en una cuadrícula de 4×3 y mírala:
   ```bash
   ffmpeg -i "$F" -vf "fps=12/DURACION,scale=480:-1,tile=4x3" -frames:v 1 hoja.png
   ```
   Calcula `DURACION` con `ffprobe`. Aplica los criterios visuales de la sección 2 (también los de los paneles) y busca además fotogramas negros o en blanco.
2. **Negros:**
   - **Tema claro (`neon`):**
     ```bash
     ffmpeg -i "$F" -vf blackdetect=d=0.5:pix_th=0.10 -an -f null - 2>&1 | grep black_
     ```
   - **Temas oscuros (`cyberpunk`, `cristal`):** el fondo es casi negro, así que usa `blackdetect=d=0.5:pix_th=0.02:pic_th=0.999`. Aun así, decide mirando la hoja de control: un plano general con poca maqueta puede parecer «negro» sin serlo.

   Solo se aceptan negros en las transiciones de las cartelas.
3. **Audio:**
   - **Volumen:**
     ```bash
     ffmpeg -i "$F" -af ebur128=peak=true -f null - 2>&1 | tail -12
     ```
     Volumen integrado entre −23 y −14 LUFS; pico real por debajo de −1 dBTP.
   - **Silencios:**
     ```bash
     ffmpeg -i "$F" -af silencedetect=n=-40dB:d=2.5 -f null - 2>&1 | grep silence_
     ```
     No debe haber silencios de más de 2,5 s, salvo al principio y al final.
   - **Transcripción:** extrae la voz con `ffmpeg -i "$F" -vn -ac 1 -ar 24000 voz.wav` y transcríbela con el propio agente:
     ```python
     import ia_vertex as IA, types
     op = types.SimpleNamespace(cuenta=IA.CUENTA, proyecto_gcp=IA.PROYECTO, region=IA.REGION, modelo=IA.MODELO)
     segs, _ = IA.transcribir(op, "voz.wav", "es")
     ```
     Compárala con el texto del guion (todas las `lineas` de todas las escenas), normalizado a minúsculas y sin puntuación, con `difflib.SequenceMatcher` por palabras.
     - **Criterio:** al menos 95 % de coincidencia.
     - **Diferencias que no son fallos:** las de escritura, como «quince» frente a «15» o «UpdateItem» frente a «update item».
     - **Lo que hay que señalar:** palabras que faltan, se repiten o se cambian por otras.
4. **Paneles en movimiento** (si los hay):
   - **Alineación:** el panel del fotograma `f` de la película es `paneles/fotogramas.vN/<f-1 con 6 cifras>.png`. Extrae del vídeo final 3 fotogramas en los que cambie el panel (inicio de una escena con datos, el momento en que rueda un contador, la escena de la comparativa; los tiempos están en `motion.json`: `paneles[].inicio`, `titular.palabras[].f`, `visual.f_accion`, todos 0-based) y compáralos con su PNG: deben coincidir sin desfase.
   - **Sincronía con la voz:** los tiempos por palabra son **estimados** (sílabas y envolvente de la voz; error típico 0,1–0,2 s). Con los segmentos de la transcripción (paso 3), comprueba que el comienzo de cada frase cae a menos de 0,3 s del `inicio` de su línea en `tiempos.json`. Si falla, las palabras del titular también llegarán tarde o pronto: informa la escena. La sincronía palabra a palabra no se puede medir sin escuchar: dilo en «Lo que no verificaste».
5. **Subtítulos en movimiento** (si los hay):
   - **Alineación:** como con los paneles, el subtítulo del fotograma `f` es `subtitulos/fotogramas.vN/<f-1 con 6 cifras>.png`. Extrae 3 fotogramas del vídeo final en cambios de bloque (`bloques.json`: `inicio` de Blender, 1-based) y compáralos con su PNG.
   - **`.srt`:** se lee sin errores; tiene tantas entradas como bloques; tiempos crecientes y sin solapes; la última termina antes del final del vídeo; con cartela de título, todo va desplazado su duración. Unidos, sus textos son la narración del guion.
   - **Sincronía:** con los segmentos de la transcripción (paso 3), el comienzo de cada frase cae a menos de 0,3 s del `inicio` de su primer bloque. La palabra en lima palabra a palabra no se puede medir sin escuchar: dilo en «Lo que no verificaste».
6. **Mangueras y sobres:** para cada manguera que aparece en una escena (columna `aparecen`), extrae del vídeo final 2 fotogramas, a mitad del revelado (0,3 s después del momento en que aparece) y al acabar. En la primera tiene que verse a medio dibujar con la chispa en la punta; en la segunda, entera y sin chispa. En cada escena con `flujo`, extrae un fotograma con el sobre a mitad de camino.
7. **Archivos:** guarda la hoja de control y la transcripción en `$P/supervision_<fecha>/` (carpeta nueva).

## Problemas conocidos y qué hacer

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| GPU al 1 % y Blender a ~1300 % de CPU con Cycles; render de horas | Cycles cayó a CPU: el dispositivo OptiX vive en las preferencias, no en el `.blend` (corregido con `gp_base.gpu_cycles`, que se llama en cada proceso) | Comprueba `libnvoptix`/`libcuda` en `/proc/PID/maps`. Si faltan, es una regresión: detente e informa. No lo arregles tú. |
| Contorno lima a trozos (lima y negro alternando) en el tema `neon` | Regresión del z-fighting del resalte (`EMPUJE_RESALTE`, adelanto de 2 cm hacia la cámara) | Informa la escena con un recorte ampliado. |
| En `cyberpunk`, pantallas o LEDs que se ven a través de otras piezas | Algún adorno se dibujó en Grease Pencil, que en Blender 5.2 se pinta encima de las mallas | Informa la pieza: en los temas con mallas, los adornos deben ser malla (`PincelMalla`). |
| En `cyberpunk`, un tubo o una pieza transparente rellenos de lima | El casco de resalte se aplicó a una pieza abierta o translúcida | Informa la pieza (`casco_resalte` debe saltárselas). |
| En `cristal`, piezas resaltadas convertidas en bloques blancos | Resalte demasiado intenso en `material_cristal` | Informa la escena. |
| En `cyberpunk`, sin bandas toon (sombreado suave) | Se renderizó con Cycles: `Shader to RGB` solo funciona en EEVEE | Comprueba el motor del render; el tema debe imponer EEVEE. |
| Halo ancho y borroso alrededor del neón | Bloom fuera de su tema: `cyberpunk` lo tiene al mínimo y `cristal`, nítido (`BLOOM` en `cyberpunk.py`) | Es un fallo en los dos temas: informa la escena. |
| Voz arrastrada («como si el narrador tuviera un derrame») o atropellada | Prosodia irregular del TTS | El control de ritmo ya reintenta hasta 3 tomas y ajusta con atempo. Si una línea queda fuera de 4,7–7,1 sílabas/s, informa la línea; no borres su wav sin permiso. |
| `401`/`403` de Vertex o «Inicia sesión con gcloud auth login» | Token o cuenta | Detente e informa. No cambies la cuenta activa ni inicies sesión tú. |
| `429` de Vertex | Cuota | Espera 60 s y reintenta una vez. |
| `Traceback` en el log | Fallo de código o de datos | No reintentes. Copia las últimas 40 líneas en el informe e indica archivo y línea. |
| Plano general con la maqueta diminuta en una esquina | Regresión del encuadre (el general encuadra solo lo ya montado) | Informa la escena y el fotograma. |
| La previa con revisión baja la nota y restaura un guion peor | La revisión de Gemini puntuaba campos internos (corregido) | No uses la revisión salvo que te lo pidan. |
| El archivo temporal no crece | Blender colgado o GPU ocupada por otro render | Ver la sección 3: alarmas. Mira antes si hay otro Blender usando la GPU. |
| Datos 3D (etiquetas, insignias) **y** panel de Motion Canvas a la vez en el vídeo final | Los paneles se añadieron después de `animacion`/`efectos`/`render`: la película es la antigua | Propón `animacion`, `efectos`, `previa --sin-revision`, `render` y `montaje`. No lances el render sin confirmarlo. |
| `paneles` falla con «faltan las dependencias de Motion Canvas» | No está `comic/motion/node_modules` | Detente e informa: hay que ejecutar `cd ~/blender/comic/motion && npm ci` (instala paquetes de npm: pide permiso antes). |
| `render de Motion Canvas fallido` con el `log` del INFORME | Error en la página de Motion Canvas (TypeScript, datos de `motion.json`) o Chrome que no arranca | No reintentes más de una vez. Copia el `log` del error. Comprueba `cd comic/motion && npx tsc --noEmit` (solo lee) y que existe `/usr/bin/google-chrome`. |
| Titulares con letra de reserva (serif o sans fina) | Fuentes no cargadas: falta `descargas/fuentes/ArchivoBlack-Regular.ttf` o `JetBrainsMono-Variable.ttf` | Informa; el INFORME de `render.mjs` trae `fuentes` con `true`/`false`. |
| Panel en blanco o a medias en el vídeo final | La tira de imagen apunta a una carpeta `paneles/fotogramas.vN` incompleta (render de Motion Canvas cortado) | Cuenta los PNG de la carpeta vigente: deben ser `frame_fin`. Propón `paneles --solo-render` y `montaje`. |
| La banda tapa la maqueta | Regresión del encuadre con hueco (`b_tecnico.encuadre`, `hueco_arriba`/`hueco_izq`) | Informa la escena con la imagen. |
| `aviso: escena N: visual … no valido … por reglas` en `paneles` | Gemini puso una cifra que no está en el guion (o le faltaban campos) y la validación lo cambió por el visual de las reglas fijas | Es informativo, no un fallo. Anótalo. |
| `previa` falla con `CalledProcessError … ffmpeg … returned non-zero exit status 234` | Al superponer dos capas (panel y subtítulo), ffmpeg leía y escribía el mismo `escena_N_mc.png` (corregido el 2026-11-09 con un archivo temporal en `agente_comic.render_previa`) | Es una regresión: informa con el Traceback. |
| `render` termina con `TimeoutExpired … timed out after 7200 seconds` y queda un `render/_tmp_video_*.mp4` ilegible («moov atom not found») | El límite de 2 h de `agente_comic.blender` cortaba los renders largos (corregido el 2026-11-09: el render va con `timeout=None`) | Es una regresión: informa. El MP4 a medias no se puede recuperar; hay que renderizar de nuevo. |
| `objetos` imprime `maqueta: …` y el guion cambia | El ajuste de la maqueta del agente (mangueras con sobres de menos de `largo_flujo` o que aparecían antes que lo que unen) | Es esperado: anótalo y avisa de que la maqueta cambia de tamaño y posición. |
| `maqueta: manguera X: mide … y no hay pasillo libre que cruce para alargarla` | No hay recta libre entre los componentes que une: la manguera sigue corta | Informa la manguera y su largo; propón mover a mano sus componentes en el guion (no lo hagas tú). |
| En `cyberpunk` o `cristal`, las mangueras caen desde arriba como las piezas | Regresión del revelado (`revelar` y `revela` en `b_tecnico.etapa_animacion`; solo actúa si el objeto de la manguera es una curva) | Informa la escena y la manguera. |
| Chispa blanca que se queda al final de una manguera | Regresión del apagado de la chispa (escala y emisión a 0 en `APAGA_F` fotogramas) | Informa la escena. |
| Una manguera crece hacia un hueco vacío y el componente aparece después | Regresión de `CP.mangueras_tras_extremos` | Informa la manguera y las dos escenas. |
| El subtítulo tapa la pieza de la que habla la escena | La cámara no dejó la franja de abajo: `animacion` se hizo antes que la etapa `subtitulos`, o regresión de `hueco_abajo` | Si la etapa `subtitulos` es más reciente que `animacion` en `proyecto.json`, propón `animacion`, `efectos`, `previa --sin-revision`, `render` y `montaje`; si no, informa la regresión. |
| Plano general muy pequeño entre el panel y el subtítulo | Regresión de la reducción del margen del general con huecos (`b_tecnico.encuadre`) | Informa la escena y el fotograma. |
| Subtítulos con las palabras pegadas («TUAEROLÍNEA») | Se volvió a escalar la palabra activa (invade el hueco) en `subtitulos.tsx` | Informa la escena. |
| Falta `final/final.vN.srt` con subtítulos en el vídeo | `subtitulos/fotogramas.vN` sin `bloques.json` (carpeta de una versión anterior al .srt) | Propón `subtitulos` y `montaje`. |

## Informe final (formato)

1. **Resumen en tres líneas:** si el vídeo está listo o no, y por qué.
2. **Tabla de etapas:** etapa | versión creada | duración | estado | avisos. Para `paneles`, indica también si se diseñó con Gemini o se reutilizó `paneles.json` (`--solo-render`). Para `objetos`, si el agente reescribió el guion con el ajuste de la maqueta y qué cambió. Para `subtitulos`, el número de bloques.
3. **Tabla de comprobaciones:** comprobación | valor medido | criterio | ✓ o ✗. Incluye el motor y el dispositivo usados, y el coste real por fotograma.
4. **Problemas:** cada uno con evidencia (ruta de la imagen y escena, o línea del log) y la corrección que propones, **sin aplicarla**.
5. **Rutas de los resultados:**
   - el vídeo final, su `.srt`, la página de cómic y el GIF;
   - la hoja de control;
   - el log de supervisión.
6. **Lo que no verificaste**, y por qué. Por ejemplo: no escuchaste el audio entero; la transcripción no detecta la entonación.

No digas que el vídeo está bien si no has mirado la hoja de control y la previa. Si una comprobación no se pudo hacer, dilo.
