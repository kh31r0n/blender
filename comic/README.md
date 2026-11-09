# Agente de animación con Grease Pencil (cómic y técnico)

`agente_comic.py` genera animaciones completas en Blender 5.2 **sin interfaz**, dibujadas con **Grease Pencil**. Gemini (Vertex AI) escribe y revisa el guion y pone las voces; los scripts de `blender/` dibujan, riggean, animan y renderizan.

Hay dos estilos (`--estilo`):

| Estilo | Qué cuenta | Aspecto |
|---|---|---|
| `comic` (por defecto) | Historias con personajes | Colores muy vivos, tinta negra con temblor, tramas Ben-Day, bocadillos, cartelas, onomatopeyas |
| `tecnico` | Explicativos de un objeto, «así funciona X», pieza a pieza | Vista isométrica alta, papel con baldosas, paleta apagada, sombra proyectada azul cobalto, rayos X y resalte lima. Referencia en `referencias/yt_88DXBq8baS4/`; sin rótulos, lo cuenta la voz |

Los dos estilos admiten `--formato 2d|3d` y `--orientacion horizontal|vertical`. El técnico es vertical por defecto y tiene cinco temas (`--tema clasico|iconos|neon|cyberpunk|cristal`, ver «Temas y objetos-icono»). Sus datos del caso salen en paneles dibujados con **Motion Canvas** (ver «Paneles de datos con Motion Canvas»).

## Modos

```bash
python3 agente_comic.py MODO [opciones]
```

| Modo | Qué hace | Salida |
|---|---|---|
| `materiales` | Descarga fuentes, texturas y materiales GP, y crea la biblioteca de materiales | `descargas/`, `biblioteca/Materiales_GP*.blend`, `muestrario_materiales.png` |
| `biblioteca` | Escenografía básica reutilizable con rig: 29 tipos × 2D/3D, 10 ambientes y 6 personajes, como assets | `biblioteca/Escenografia_GP.blend` |
| `modelo` | Solo estilo técnico. Busca un modelo prediseñado, Gemini elige mirando las miniaturas, lo descarga y lo convierte en partes. Lo lanza solo `guion` o `todo` con `--modelo-3d` | `modelo/partes.json`, `modelo/hoja_partes.png`, `modelo/busqueda/candidatos.png` |
| `0` `guion` | Gemini convierte la descripción en guion JSON. `--audio`: lo escribe sobre tu audio. `--ejemplo`: sin IA | `guion.json` |
| `detalles` | Solo estilo técnico. Gemini mira la maqueta lisa (y una imagen de referencia, si la das) y añade adornos a las piezas; después rehace `objetos`. Lo lanza `todo` salvo con `--sin-detalles` | `adornos.json`, `detalles/comparativa.png` |
| `1` `objetos` | Dibuja con GP todo lo que pide el guion | `01_objetos.blend` |
| `2` `rig` | Un esqueleto para cada personaje, elemento o pieza (comprueba que nada se mueva en reposo) | `02_rig.blend` |
| `3` `audio` | Voces Gemini TTS por línea (en caché) o tu audio transcrito: fija los tiempos de todo | `tiempos.json`, `audio/` |
| `paneles` | Solo estilo técnico. Gemini diseña un panel de datos por escena con datos y Motion Canvas lo renderiza sin interfaz (PNG con alfa). `--sin-ia`: reglas fijas; `--solo-render`: reutiliza `paneles.json` | `paneles.json`, `paneles/fotogramas/` |
| `subtitulos` | Subtítulos con Motion Canvas desde `tiempos.json`: bloques de 3–6 palabras con la palabra que suena en lima, PNG con alfa y `.srt`. `--subtitulos 0` los quita (en el estilo cómic vienen desactivados) | `subtitulos/fotogramas/` (`bloques.json`, `subtitulos.srt`) |
| `4` `animacion` | Anima rigs, escenografía y cámara al ritmo del audio | `04_animacion.blend` |
| `efectos` | Cómic: bocadillos, cartelas, onomatopeyas, líneas de velocidad… Técnico: agua, vapor, burbujas, flechas, llama… | `04b_efectos.blend` |
| `previa` | Un fotograma por escena y revisión de Gemini en bucle (`--iteraciones`). Si una corrección empeora la nota, restaura la mejor versión | `previa/iter_N/` |
| `5` `render` | EEVEE: MP4 H.264 con voces AAC y una viñeta por escena | `render/` |
| `montaje` | Cartelas de título y FIN, vídeo final (con paneles y subtítulos encima), su `.srt`, página de viñetas y GIF | `final/` |
| `miniatura` | Solo estilo técnico. Gemini escribe 3 variantes (dolor, cifra, curiosidad; solo cifras del guion), Blender renderiza la maqueta montada (Cycles en la GPU), Motion Canvas compone titular y cifra en 1080×1920, 1920×1080 y 1280×720, y Gemini las ordena por probabilidad de clic. `--sin-ia`: por reglas | `miniaturas/miniaturas/` (`mejor_*.png`) |
| `publicacion` | Gemini escribe el copy por plataforma (LinkedIn, Shorts/Reels/TikTok, YouTube), 5 títulos alternativos y una revisión para redes de los 3 primeros segundos y la miniatura (propuestas, no se aplican) | `publicacion/publicacion/` (`publicacion.md`, `copy_*.txt`) |
| `todo` | guion → (técnico: detalles) → objetos → rig → audio → (técnico: paneles) → subtítulos → animación → efectos → previa → render → montaje → (técnico: miniatura) → publicación | — |
| `estado` | Resumen del proyecto | — |

**Nunca se sobrescribe nada:**
- Cada ejecución de una etapa crea `X.v2`, `X.v3`, etc.
- `proyecto.json` apunta a la versión vigente.
- Las versiones anteriores de `guion.json` y `tiempos.json` se guardan en `historial/`.

```bash
python3 agente_comic.py materiales
python3 agente_comic.py todo --descripcion "un gato astronauta aterriza en una ciudad de caramelo" --formato 3d
python3 agente_comic.py todo --estilo tecnico --descripcion "cómo funciona una cafetera italiana" --duracion 30
python3 agente_comic.py guion --descripcion "..." --formato 2d --orientacion vertical --duracion 20
python3 agente_comic.py guion --audio mi_narracion.mp3 --descripcion "..."     # el guion se ajusta a tu audio
python3 agente_comic.py animacion --proyecto proyectos/<carpeta>               # rehacer una etapa
python3 agente_comic.py todo --ejemplo --voz-narrador silencio --calidad borrador   # prueba sin red
```

**Parámetros:**
- **Generales:** `--estilo`, `--formato`, `--orientacion`, `--fps`, `--calidad` (borrador, previa o final, es decir 25, 50 o 100 % de 1920×1080), `--duracion`, `--idioma`.
- **Voz:** `--voz-narrador` (voz de Gemini TTS o `silencio`), `--modelo-tts` y `--ritmo-voz` (palabras/s objetivo, 2,6 por defecto).
- **Control de ritmo de la voz** (`audio_comic.voz_con_ritmo`):
  - **Instrucción:** cada petición a Gemini TTS indica idioma, tono y ritmo («Read aloud in Spanish (Spain), as a clear documentary narrator, … about 156 words per minute, without stretching syllables…: <texto>»).
  - **Medición:** las sílabas por segundo de la línea ya recortada (cada letra de una sigla como LLM o SQS cuenta 1,5).
  - **Banda y reintentos:** si la toma se sale de 0,82–1,25 × el objetivo (2,2 sílabas por palabra), se pide otra, hasta 3.
  - **Ajuste final:** si ninguna entra, la mejor se ajusta con `atempo` de ffmpeg, que conserva el tono.
  - **Motivo:** con `gemini-2.5-flash-tts` y estilos como «misterioso», algunas líneas salían a 1,3 palabras/s, arrastradas.
  - **En `tiempos.json`:** cada línea guarda sus `silabas_s`.
- **Aspecto:** `--tema` (estilo técnico), `--grosor-tinta`, `--temblor-linea`, `--semitono`, `--papel`, `--bocadillos`, `--cartelas`, `--saturacion`, `--brillo-fx`, `--en-dos`.
- **Cualquier parámetro:** `--param clave=valor`.

La tabla única está en `comic_parametros.py`.

## Cómo está hecho

**Estilo cómic:**
- **Personajes** (`blender/personajes.py`):
  - Hay cinco tipos: humano, robot, gato, perro y monstruo, con peinados, accesorios y colores configurables.
  - Cada uno tiene **dos vistas** en el mismo objeto: las capas `F_*` (frente) y `P_*` (perfil, mirando a +X).
  - Rig de recortes: cada capa se emparenta a uno de los 22 huesos, sin pesos. El roll de los huesos está alineado a -Y, así que girar en Z local gira la parte en el plano de la pantalla.
  - Para mirar a izquierda o derecha, el hueso `raiz` lleva escala x = -1.
  - Hay tres bocas y unos ojos cerrados como capas separadas, que se encienden y apagan con `hide` (claves constantes).
- **Animación** (`blender/b_animacion.py`):
  - La pose se calcula «en dos» (cada 2 fotogramas, constante).
  - Hay 19 acciones. El ciclo de paso depende de la distancia recorrida, así los pies no patinan.
  - La boca sigue la envolvente RMS de la voz de cada línea; hay parpadeos y mirada.
- **Escenografía** (`blender/escenografia.py`):
  - En 3D, las cajas son de trazos con caras rellenas; lo plano mira a cámara con *Locked Track*.
  - En 2D, las capas van por profundidad con escala de lejanía.
- **Efectos:** van en espacio de pantalla (`Pantalla`, hijo de la cámara, con 1 unidad = alto del cuadro), anclados a la cabeza proyectada del actor. Los que se redibujan (líneas, confeti, humo) son fotogramas GP cada 2.

**Estilo técnico** (`blender/tecnico.py` y `b_tecnico.py`):
- **Piezas:** Gemini describe el objeto con 11 primitivas paramétricas (caja, cilindro, tubo, cono, esfera, anillo, disco, muelle, varilla, manguera y panel), con su posición, rotación, material, detalle (perforado, nervado, rayado o rejilla), padre y bisagra.
- **Dibujo:**
  - Cada cara lleva una banda de color según su orientación.
  - La tinta va en aristas y en siluetas vistas desde la cámara isométrica.
  - Translúcidos: los líquidos, el cristal y la versión de rayos X `<id>_rx` usan orden 2D, con el origen adelantado hacia la cámara.
- **Montaje:** las piezas caen y rebotan por orden de montaje. En los temas con mallas (`cyberpunk`, `cristal`) las mangueras no caen: se **dibujan** de su origen a su destino en 0,6 s (`b_tecnico.REVELA_S`; `bevel_factor_end` de la curva con mapeo `SPLINE`) con una **chispa** blanca en la punta (`cyberpunk.chispa`) que se encoge y se apaga al llegar. Los flujos esperan a que la manguera haya llegado.
- **Sombra:** la sombra azul es el casco convexo de cada pieza proyectado con la luz, y se rehace en cada cambio.
- **Revisión geométrica previa:** `comic_parametros.revisar_geometria` detecta piezas que flotan y palancas de pie. Gemini corrige el guion una vez antes de renderizar.

## Sistemas y procesos (estilo técnico)

Para temas sin objeto físico (arquitecturas de software, redes, logística), el guionista construye una **maqueta** en el suelo:
- **Componentes:** cada uno es un objeto reconocible de 1-4 primitivas (servidor = caja con rejilla, base de datos = cilindro, cola = tubo transparente tumbado, función = caja con tapa, control de acceso = garita con barrera…). Van repartidos de izquierda a derecha siguiendo el recorrido y unidos con mangueras. La maqueta mide hasta 5 m de ancho y tiene hasta 40 piezas.
- **Efectos para mensajes y decisiones:**
  - `flujo`: sobres blancos que recorren el camino de una manguera.
  - `flujo_vuelta`: sobres mostaza de respuesta, en sentido contrario.
  - `aprobado` (✓) y `rechazo` (✗).
  - `reloj`: esperas, tiempos límite y reintentos.
  - `ondas`: señales y telemetría.
  - `alerta`: triángulo rojo con exclamación que late (incidentes, avisos).
  - `rayo`: rayo lima que destella (respuesta instantánea, acierto de caché).
- **Movimientos:** `subir`, `bajar` y `desplazar_*` se acumulan entre sí, y `volver` devuelve la pieza a su sitio.
- **Cámara:** `camara.objetivos` (lista de ids) encuadra una zona o un grupo de piezas.
- **Plano general:** encuadra solo las piezas ya montadas en esa escena, así que al principio del montaje no se ve una maqueta casi vacía. Con `alejar`, la cámara se aleja hasta el plano general y no más allá.
- **Escenas:** su número sale de la duración (unas 7 s por escena en el estilo técnico).
- **Reglas del guion:**
  - **Esquema:** obliga a dar `ancho`, `fondo`, `alto`, `radio` y `camino` en todas las piezas, con 0 o `[]` si no se usan. Sin eso, Gemini se saltaba medidas en guiones largos.
  - **Reparación:** `medidas_faltantes()` detecta lo que falte y lo manda a la pasada de reparación.
  - **Tiempos:** `momento` e `inicio` se limitan a 0,75 y 0,8, para que ningún efecto empiece con la escena ya terminada.
  - **Duración de efectos:** va en segundos; si es ≤ 1, se toma como fracción de la escena (Gemini a veces la confunde con `momento`).
  - **Mangueras:** `revisar_geometria()` avisa si una manguera atraviesa otra pieza (también pegada al suelo por debajo) o si un extremo queda suelto a más de 8 cm de cualquier pieza. Esos avisos van a la pasada de reparación y a la revisión de la previa. El validador apoya los puntos del camino en el suelo (z ≥ radio).
  - **Movimientos:** `revisar_movimientos()` avisa si una pieza que se desplaza (`desplazar_*`, `subir`, `bajar`, `volver`) atraviesa otra por el camino.
  - **Suelo:** el validador sube las piezas que, por su giro o su `z`, quedan por debajo del suelo.
  - **Lo que se cuenta se ve:** el guionista debe dar a cada escena un cambio visible (fichas que aparecen, piezas que se desplazan, flujos) y usar `resaltar` en todas.

## Temas y objetos-icono (estilo técnico)

```bash
python3 agente_comic.py todo --estilo tecnico --tema iconos --orientacion horizontal --duracion 150 \
    --referencia referencias/iconos/set_iconos_isometricos.png --descripcion "..."
```

**Tema** (`--tema`, `comic_parametros.TEMAS_TECNICOS`):

| Tema | Aspecto |
|---|---|
| `clasico` (por defecto) | Papel con baldosas y paredes, paleta apagada, cuatro bandas de luz, tinta fina con temblor, grano de lápiz, sombra azul cobalto |
| `neon` | Maqueta de infraestructura como `referencias/maqueta_neon/maqueta_bases_neon.png`: cada componente sobre una **peana** azul de esquinas redondeadas con el borde luminoso y halo en el suelo, **mangueras de neón** azules (halo en el suelo, brillo claro y conectores metálicos), colores vivos por componente (verde, morado, naranja, rojo, azul, metal plateado), suelo de baldosas blanco y gris claro sin paredes, tinta negra limpia (×1,3) sin temblor ni papel, sombra gris muy clara y un cartel con icono en cada componente principal (modo `detalles`). Sin objetos-icono |
| `cyberpunk` | Como `escenes/Cyberpunk_fixed.blend`. Las piezas son **mallas 3D** con el material toon de la referencia (`Shader to RGB` → rampas de 4 bandas constantes + emisión). Contornos con **Line Art**, adelantado 5 cm hacia la cámara. Fondo casi negro con rejilla azul de neón, peanas con aro cian y mangueras de neón. El bloom (Glare) es **mínimo** (`bloom: minimo`): umbral 3, intensidad 0,06; solo brilla lo más intenso, sin halo. Render con **EEVEE**, que impone el tema porque `Shader to RGB` solo funciona ahí. Lo dibuja `blender/cyberpunk.py` |
| `cristal` | Con las referencias de cristal (cubos de un LLM sobre un circuito, flujo azul, blueprint). Piezas de **cristal** translúcido tintado por función, más opaco en los bordes, con bordes de luz azul claro nítidos (Line Art sin brillo GP). Conexiones como líneas de luz finas con nodos, suelo de circuito tenue sobre azul marino, poco bloom. Paleta: azul y cian; morado para bases de datos; verde solo para aciertos y caché; magenta (`rojo`) solo para alertas y fallos. Render **Cycles** en la GPU (32 muestras, denoise OptiX). Lo dibuja `blender/cyberpunk.py` con `piezas: cristal` |
| `arcilla` | **Diorama de ingeniería industrial futurista** (referencias en `referencias/arcilla/` y el vídeo `referencias/pin_945052303052175320/`). **Todo malla: sin Grease Pencil ni Line Art** (parámetro de tema `sin_gp`), tampoco en los efectos (`hervir_malla`: una malla por dibujo, sin sombra) ni en la cartela de FIN (`b_montaje.cartela_malla`, objetos de texto). **Un solo material para todo lo opaco** (cuerpos, acentos, peanas, patas, adornos, rótulos): plástico mate (`SUPERFICIES["plastico"]`) con la **textura descargada Leather039** de ambientCG (CC0, `descargas/ambientcg/`; tema `textura`: relieve por Bump de 12 mm de distancia a 1,6 repeticiones/m y su rugosidad; el color es siempre el de la paleta; la fuerza del relieve es la propiedad de escena `grano`, que la animación baja con el zoom: entera con encuadres de 3 m de alto o más y hasta 0,35 en los planos muy cercanos, `b_tecnico.fuerza_grano`, donde el grano salía aumentado como piedra); **solo cambia el color**. El acrílico translúcido queda para lo transparente por función: canales de las cintas (turquesa), filo de las peanas (cian, brillo 0,1), tarjetas y fichas. Peanas con AO de contacto. Adornos: placas con 1,8 mm de relieve apiladas por orden de dibujo, **líneas continuas** a inglete con vértices compartidos y **marcos moldeados** (tubo redondeado de una pieza) en los contornos cerrados grandes de tinta (carteles, alertas, relojes, pantallas); todo se adelanta por la vista (`PincelMalla`, en este tema). Paleta: turquesa y cian para lo tecnológico y el flujo; acentos por sistema en naranja, lima, violeta (`morado`), magenta (`rosa_vivo`) y amarillo; rojo solo para fallos. **Cintas transportadoras** (`cyberpunk.cinta`: canal en U de acrílico con el perfil redondeado, banda con lamas que avanzan y patas) a 8,5 cm, reveladas con chispa turquesa; las fichas son cubos de acrílico naranja que brillan. Rótulos «01.»… (paso del ciclo) y tarjetas flotantes sin sombra. **Entorno:** suelo blanco puro y una **plataforma** gris claro neutro bajo todo el workflow (`cyberpunk.PLATAFORMA`: cara de arriba en z=0, canto de 7 cm redondeado; el suelo baja a su base). **Luz:** principal **detrás a la derecha a 68°** (sombras cortas que caen hacia la cámara, suaves pero definidas), relleno suave desde el lado de la cámara y cenital tenue. **Cycles** en la GPU: 96 muestras adaptativas con denoise, transformada **Khronos PBR Neutral**, exposición −0,3, bloom mínimo. Cámara a **35°**, **profundidad de campo** (f/6 en medios, f/3,2 en detalle) y **órbita lenta** (±5°) en los generales fijos. Paneles y subtítulos en claro (`PALETA_PANELES["arcilla"]`). ~4–5 s por fotograma al 100 %. Lo dibuja `blender/cyberpunk.py` con `piezas: arcilla` |
| `iconos` | Como un set de iconos isométricos vectoriales (`referencias/iconos/set_iconos_isometricos.png`): cuerpos blancos con el lateral en sombra azul claro, acentos lima, contorno negro grueso (×1,6) sin temblor, cajas con las esquinas redondeadas, fondo liso gris azulado sin paredes, papel ni grano, sombra azul muy clara |

- **Colores:** cada tema puede sustituir colores por nombre (`paleta`) y limitar los que usa el guion (`colores`); los demás se convierten con su `mapa` (en `iconos`, menta → lima y metal → gris_claro; en `neon`, menta → verde y violeta → morado).
- **Guía para el guionista:** cada tema puede añadir instrucciones al vocabulario (`guia`). El de `neon` pide una peana bajo cada componente (forma `peana`, con el componente encima a z = alto de la peana), un color por componente y mangueras de borde a borde a la altura de las peanas. `revisar_geometria()` avisa de los componentes que quedan en el suelo sin peana, y el validador pone las mangueras en el color del tema (`manguera`).
- **Juntas y esferas:** en los temas sin papel (`iconos`, `neon`), cada faceta lleva un borde fino de su color que tapa las juntas, y en las esferas cada faceta se recorta por los planos de las bandas de luz, así que los límites salen lisos. También se adaptan los adornos: las pantallas son claras con tinta en vez de oscuras con halo.
- **Dos tonos:** con `lateral` (tema `iconos`), las caras con luz llevan el color de la pieza y las que están en sombra, azul claro (en los cuerpos claros) o el color oscurecido.
- **Dónde se aplica:** `tecnico.aplicar_tema(params)` se llama al principio de cada etapa de `b_tecnico.py`.
- **Resalte sin z-fighting:** el contorno lima de las piezas resaltadas se dibuja adelantado `EMPUJE_RESALTE` (2 cm) hacia la cámara, igual que el `stroke_depth_offset` de Line Art en `escenes/Cyberpunk_fixed.blend`. A la misma profundidad que la tinta y las caras salía a trozos. Su grosor por tema es `resalte`: 1,3 en `clasico` y 1,0 (el de la tinta) en `iconos` y `neon`.

**Gancho y caso concreto** (estilo técnico):
- **Gancho:** el vídeo abre con una pregunta que deja pensando. El parámetro `gancho` fija el tipo: `dolor` (por defecto), `contraintuitiva`, `reto`, `auto` o `ninguno`.
  - **Guion:** Gemini la escribe en `gancho.pregunta` (8–14 palabras, en segunda persona, con el caso) y en `gancho.texto_pantalla` (3–7 palabras, para leer sin sonido).
  - **Validación:** `poner_gancho` garantiza que la pregunta sea la primera línea del narrador de la escena 1.
  - **Montaje:** con gancho no hay cartela de título al principio. El vídeo arranca con la animación y `b_montaje.tira_gancho` pone el texto en grande (Archivo Black blanca, contorno y caja translúcida, arriba en vertical) mientras suena la pregunta, con fundido de entrada y salida.
  - **Cámara:** en la escena 1 deja libre la franja de arriba para el texto (`encuadre(..., hueco_arriba=0.21)`: algo más de cuadro y la maqueta más abajo).
- **Plano general en vertical:** deja el mismo margen lateral que en horizontal (1,3). Con 1,75, una maqueta isométrica, más ancha que alta, se quedaba en la mitad del ancho del móvil.
- **Caso concreto:** en sistemas y conceptos abstractos, el guion sigue un solo ejemplo real de principio a fin (`caso`, p. ej. una aerolínea que pone precio a los 180 asientos de un vuelo). Cada componente, flujo y efecto es algo de ese caso, y la narración usa sus números. La última escena responde a la pregunta del gancho.

**Workflow visible** (estilo técnico; referencias `referencias/yt_pNu03D7n4jQ` y `yt_HkNCz3d31To`, shorts de divulgación). Lo propone Gemini en el guion; `agente_comic.py enriquecer` lo añade a un guion existente sin tocar lo demás.
- **Dónde se dibuja:** con `paneles_mc` (por defecto) y la etapa `paneles` hecha, todo esto (y el gancho) va en los paneles de Motion Canvas de arriba (ver «Paneles de datos con Motion Canvas»). Lo que sigue describe el dibujo en 3D y en el secuenciador, que se usa con `--paneles-mc 0` o mientras el proyecto no tenga la etapa `paneles`.
- **Datos vivos** (`datos_vivos`; `datos` de cada escena, 0–2):
  - **Contenido:** paneles con un número del caso junto al componente: estado, acción o resultado. Llevan etiqueta y valor; el color del valor tiene significado: lima, bueno; rojo, problema; azul (en pantalla, cielo), espera o referencia; blanco, neutro.
  - **Contador:** con `hasta`, el número sube durante la escena (con frenada al final y el formato del valor final).
  - **Entre escenas:** el mismo dato (misma pieza y etiqueta) en escenas seguidas se actualiza en su sitio.
  - **Posición:** van por el lado libre de la pieza (`tecnico.sitio_dato`).
- **Pasos del ciclo** (`pasos_ciclo`; `ciclo` del guion y `paso` de cada escena):
  - **Insignias:** numeradas, con la palabra del paso. Van por el lado contrario a los datos y tienen tres estados: apagado (gris), activo (lima y algo mayor) y hecho (cian).
  - **Ciclo rápido:** con `ciclo_rapido`, los pasos se encienden en bucle cada vez más rápido (cada vuelta, al 72 % de la anterior).
  - **Cámara:** los planos encuadran las insignias de su pieza (`puntos_workflow` → `encuadre(extra=...)`). En vertical, un plano medio no deja sitio a los lados y se salían.
- **Comparativa** (`comparativa`):
  - **Gráfica:** en la escena del resultado, tiras del secuenciador en la franja baja (`b_montaje.tiras_comparativa`): panel, dos barras que crecen (antes y después) con su valor, el resultado grande en lima y una curva de aprendizaje que sube punto a punto.
  - **Cámara:** en esa escena deja libre la franja baja (`hueco_arriba=-0.22`).
- **Implementación:** en malla, cada estado de una insignia es un objeto con claves de visibilidad, en «Fichas del flujo» como oclusor de Line Art, y entra y sale con escala. En GP, un dibujo por cambio.

**Apariciones, resalte, carteles y fichas** (todos los temas técnicos, `b_tecnico.py` y `tecnico.py`):
- **Dos momentos como mucho:** `tandas()` reparte las piezas nuevas de cada escena. Hasta 3 entran juntas; con más, se parten en dos tandas por la peana (inicio de componente) más cercana a la mitad, y la segunda entra hacia el 40 % de la escena.
- **Los hijos siguen a su pieza:** en los temas con mallas, los adornos, los aros de neón y los surcos son objetos hijos. La animación les pone las mismas claves de visibilidad que a su pieza; antes flotaban en escena antes de que la pieza apareciera.
- **El resalte sale a la vez:** cada pieza lo enciende al entrar (con su tanda), pero todas las de la escena lo apagan juntas, con un fin común (`fin_r`) y el mismo fundido.
- **Carteles sin choques:** `recolocar_carteles()` comprueba, antes de dibujar, que el poste y el tablero de cada cartel de `arriba` no atraviesan otras piezas ni tapan lo que se posa encima (fichas, esferas, balizas). Si chocan, busca sobre la misma cara el sitio libre más cercano y, si no hay, alarga el poste (hasta 30 cm); si nada vale, quita el cartel. Lo anota en `avisos_adornos`.
- **Fichas que entran en un contenedor:** las piezas nuevas que quedan dentro de una pieza transparente (las alertas en la cola SQS) no caen: llegan en movimiento por la manguera que alimenta el contenedor (la que termina junto a él; los caminos van del origen al destino) y entran por la boca del eje largo.
- **Ficha del flujo:** el parámetro `icono_flujo` elige lo que viaja por las mangueras: `sobre` (por defecto) o `biohazard` (alertas de seguridad; un color por ficha, en ciclo rojo, amarillo, lima, naranja, cian y rosa). `flujo_vuelta` (respuestas) sigue siendo un sobre mostaza.
- **Forma `biohazard`:** una alerta como pieza (`alto` es su diámetro). Con mallas es el mismo símbolo que las fichas del flujo y mira a la cámara; en GP, las medias lunas en el plano XZ. Se usa para las alertas que esperan en una cola: llegan por su manguera hasta un contenedor transparente. `tecnico.dibujar_biohazard` dibuja el símbolo para la pieza y para los efectos.
- **Nitidez en malla:** en los temas con mallas no se dibujan los halos y discos translúcidos que imitan el brillo en GP (icono de pantalla oscura, líneas de pantalla, LEDs, ranuras), porque en malla salen como un borde borroso. Los iconos quedan nítidos.
- **Placa:** es un panel de servicio con tres ranuras de ventilación y tornillos visibles (antes era un cuadrado con borde).
- **Icono `grafica`:** ejes y una línea que sube con un punto al final (ingresos, mejora), para pantallas de resultados.
- **Flujos y mangueras:** un flujo no empieza hasta que su manguera se ve y se ha posado (la caída dura 16 fotogramas, más 0,2 s). Antes las fichas viajaban por una manguera que aparecía después en la misma escena.
- **Adorno `barras`:** un indicador LED con `cantidad` barras apiladas de color plano y borde fino. Las franjas muy finas se las comía su propia tinta.
- **Líneas sin z-fighting en malla:** `PincelMalla.linea` adelanta cada cinta 1,5 mm sobre lo que bordea (hacia la cámara, o según la normal en caras curvas). En GP manda el orden de dibujo; en malla, la profundidad, y el contorno de un cartel en el mismo plano que su relleno parpadeaba. El trazo gris del poste va por delante de su tinta, y el halo de los iconos por detrás del relleno.
- **Carteles con texto:** un adorno `cartel` puede llevar `texto` (una sigla de 2–6 letras, validada en mayúsculas) en lugar de `icono`. Se rotula en Archivo Black (`FUENTE_TECNICA`), relleno del color del adorno y con borde de tinta como los iconos, sea en malla o en GP (`tecnico.dibujar_texto`). El borde sale del contorno de cada letra (las aristas del texto convertido en malla) y va debajo del relleno, así que solo asoma por fuera. El cerebro admite un único cartel, encima (cara `arriba`).
- **Icono `base_datos`:** la tapa es una elipse isométrica, igual de achatada que las bandas (antes era un círculo).
- **Forma `cerebro`** (un LLM o un modelo de IA):
  - **Medidas:** `radio` es la media longitud, con el frente hacia −X.
  - **Modelo:** usa el cerebro descargado de NIH 3D (CC BY 4.0; créditos en `descargas/modelos/nih_3dpx_002739_cerebro/LEEME.md`), ya preparado con `blender/preparar_modelo_forma.py`. Este script importa, suelda, reduce a 40 000 y 7 400 caras y normaliza.
  - **Trazo de neón (temas con mallas):** el cerebro va en la colección «Piezas trazo neon», con su propio Line Art («Contornos neon»), que dibuja la silueta y los surcos en cian plano y sin brillo (`TEMA['trazo_neon']`, por defecto `cian`). Su toon usa `contraluz='fria'`: la rampa de contraluz en tonos del propio color, porque la cálida de la referencia salía como vetas rosadas en cada grieta. El Line Art negro general no lo traza, pero sí lo usa para tapar: Line Art considera oclusores también los objetos que no son su origen (comprobado con dos cubos).
  - **Sin el modelo:** se usa uno procedural (`tecnico.caras_cerebro`, surcos dibujados como líneas), más pobre.
  - **Adornos:** no admite.
- **Colores `rosa_vivo` y `rosa_brillo`:** están en la paleta técnica; en el tema `cristal`, `rosa_vivo` pasa a su magenta.

**Tema cyberpunk** (`blender/cyberpunk.py`, `TEMA["mallas"]`):
- **Material toon:** copiado nodo a nodo de la referencia. Solo depende de dos canales de la luz que llega:
  - R ÷ 1,9: rampa de 4 bandas del color de la pieza;
  - B ÷ 2,6: rampa cálida de contraluz.
- **Luces de datos:** las luces son rojas (principal y relleno) y azul (contraluz bajo, detrás). No dan el color final.
- **Adornos en malla:** en Blender 5.2 el Grease Pencil se pinta encima de las mallas aunque esté detrás. Por eso los adornos (pantallas, LEDs, carteles) se dibujan con `PincelMalla`, que tiene la misma interfaz que el pincel GP (`cara`, `linea`). Así reutilizan `tecnico.dibujar_adornos` tal cual, y las líneas son cintas perpendiculares a la vista.
  - **Caras curvas:** en cilindros, tubos y esferas, `dibujar_adornos` pasa los rellenos rectangulares como `_Rejilla` (una cuadrícula de cuadriláteros que sigue la superficie, con tramos de 2 cm como mucho) y las líneas como `_Trazo` (con la normal de la superficie en cada punto). `PincelMalla` tiende entonces la cinta pegada a la superficie. Un polígono no plano que envuelve un cilindro se triangulaba por dentro de la pieza (z-fighting en las franjas), y una cinta que mira a la cámara fija se veía de canto al girarla o a través de un tubo transparente (trazo de cera). El GP ignora ambos atributos.
  - **Franjas en piezas transparentes:** dan la vuelta entera (se ven por detrás).
- **Fichas del flujo en malla:** los sobres y biohazards que viajan por las mangueras son mallas animadas (una por ficha; la malla se comparte por color), visibles solo mientras viajan y adelantadas el grosor de la manguera hacia la cámara. Van en la colección «Fichas del flujo», dentro de la que lee Line Art, con `lineart.usage = 'OCCLUSION_ONLY'`: las piezas de delante las tapan y los contornos de lo que queda detrás no se pintan encima. En GP salían por encima de todo.
- **Qué sigue en GP:** los demás efectos (✓, ✗, reloj, ondas), porque flotan encima de los componentes a propósito, y los contornos de Line Art, que calculan ellos mismos qué líneas se ven.
- **Resalte:** un casco invertido (`Solidify`) en la propia pieza. Su material (`CP resalte`) mezcla transparente y emisión lima con la propiedad de objeto `resalte` (0–1) como factor, así que entra y sale con fundido; el modificador solo se enciende mientras dura. Es `DITHERED`, no `BLENDED`: escribe profundidad y se ve dentro de piezas translúcidas (las fichas del tubo SQS); con `BLENDED` el tubo lo tapaba. No se pone en piezas transparentes ni en tubos abiertos.
- **Sombra y paredes:** no hay sombra GP ni paredes. El suelo es emisión plana oscura, para que la caída de la luz roja no pinte bandas en él.
- **Coste:** unos 0,5 s por fotograma a 1080p con la GPU al 90 %. El vídeo SOC (3246 fotogramas) tarda unos 30 minutos.
- **Variante cristal** (tema `cristal`, `TEMA["piezas"] = "cristal"`):
  - **Material:** `material_cristal` es transparente, emisión tintada, Fresnel (`Layer Weight → Facing`) para los bordes y un reflejo suave. En Cycles ese reflejo recoge los neones.
  - **Resalte:** la propiedad de objeto `resalte` (0–1, con fundido), que el material lee con un nodo `Attribute`; aviva el color sin quemarlo. El casco invertido no sirve en piezas transparentes: se vería entero.
  - **Mangueras:** líneas de 8 mm con nodos esféricos emisivos en cada esquina.
  - **Suelo:** `suelo_circuito`, pistas procedurales a 45° con pastillas, con semilla fija.
  - **Sin luces:** todo es emisivo.
  - **Coste:** unos 3,5 s por fotograma con 48 muestras compartiendo la GPU; con 32 muestras y la GPU libre, menos.

**Objetos-icono** (`iconos_3d.py`, forma `icono` con `modelo`):
- **Qué son:** objetos prefabricados y ya detallados, hechos con las primitivas del estilo técnico. Gemini elige el `modelo`; `alto` es su tamaño (la dimensión mayor), `color` es el cuerpo y `acento` el color de los detalles (lima por defecto).
- **Modelos:** `reloj_arena` (TTL), `base_datos`, `embudo` (correlación), `campana` (alerta), `despertador`, `cronometro` (latencia), `candado`, `engranaje`, `monitor`, `portatil`, `servidor`, `robot` (agente), `orbe` (LLM), `llave` (clave, hash), `caja_herramientas` (tools), `diana` (acierto) y `escudo` (seguridad).
- **Datos de cada parte:** primitiva, medidas, posición y giro en coordenadas del modelo, y un rol de color: `c` cuerpo, `a` acento, `l` azul claro, `n` negro o `b` blanco. Se normalizan para que la dimensión mayor valga 1.
- **Vocabulario:** incluye las proporciones (ancho × fondo × alto por tamaño 1), para que Gemini sepa dónde acaba cada icono.
- **Dibujo:** cada parte se dibuja como una primitiva más dentro del mismo objeto GP. Las partes pequeñas (ojos, agujas) llevan la tinta más fina.
- **Para el resto del agente, un icono es una pieza normal:** rig, caída, resalte, rayos X, sombra y encuadre. No admite adornos.
- **Hoja de muestras:** `iconos_3d.LISTA` en una maqueta de prueba, renderizada con `b_tecnico.py --etapa objetos`.
- **Ajustes de la maqueta** (`CP.ajustar_maqueta`, al validar el guion y al empezar la etapa `objetos`; si cambian algo, el guion se archiva y se reescribe):
  - **Mangueras con sobres de largo fijo** (`--largo-flujo`, 1 m por defecto; 0 lo desactiva): si una manguera por la que viaja un `flujo` mide menos, `separar_por_mangueras` abre hueco entre los componentes con **cortes**: una recta x=c o y=c por un pasillo libre (ninguna pieza la cruza); lo que queda a un lado se aparta d/2 y lo del otro −d/2. Las piezas se mueven enteras y las mangueras solo se estiran en el tramo que cruza el pasillo, así que nada nuevo se atraviesa y los codos siguen rectos. Elige el corte que deja menos mangueras cortas, con menos separación y que alarga menos las demás.
  - **Mangueras después de sus extremos** (`mangueras_tras_extremos`): una manguera que aparece antes que alguno de los componentes que une (la peana, o la pieza, más cercana a cada punta) pasa a la escena de ese componente, al final de su lista, y sus flujos de la escena original pasan con ella.
- **Cámara en escenas con flujo:** en planos medios y de detalle, las mangueras por las que viajan sobres se añaden a los `objetivos`, así que entran enteras en el plano.

## Paneles de datos con Motion Canvas (estilo técnico)

La explicación con los datos del caso va **arriba** (vertical: franja del 40 % del alto; horizontal: columna izquierda del 38 % del ancho), dibujada con [Motion Canvas](https://motioncanvas.io) 3.17.2 al estilo de los shorts de referencia (`referencias/yt_pNu03D7n4jQ`, `yt_HkNCz3d31To`): titulares en mayúsculas muy gruesas que salen **palabra a palabra con la voz**, la palabra clave en color, y un visual con los números del caso.

- **Cuándo:** solo en las escenas con datos (`CP.escenas_con_panel`): la 1 si hay gancho, las que traen `datos`, `paso` o `ciclo_rapido`, y la de la `comparativa`. Es la única regla, y la comparten la cámara y el diseño. En las demás escenas la maqueta usa el cuadro entero.
- **Qué sustituye:** los datos vivos y las insignias de pasos en 3D (`workflow_visible` no se llama), la tira del gancho y la gráfica comparativa del secuenciador. Se activa con el parámetro `paneles_mc` (por defecto) **y** la etapa `paneles` hecha (`CP.usa_paneles`); sin la etapa, Blender sigue dibujándolo todo como antes.
- **Diseño** (`agente_comic.modo_paneles`, `SISTEMA_PANELES`): Gemini recibe la voz y los datos de cada escena, el caso, el ciclo, la comparativa y las hojas de los dos shorts, y devuelve un panel por escena (`CP.esquema_paneles`). `CP.validar_paneles`:
  - deja solo escenas con datos (las que falten salen por reglas fijas, `CP.paneles_por_reglas`);
  - titular de 6 palabras como mucho (8 el gancho, que es siempre su `texto_pantalla`), 1–2 palabras clave, colores con significado (`bueno` lima, `problema` rojo, `espera` azul, `neutro`);
  - **ninguna cifra que no esté en el guion** (datos, comparativa, caso o voz): si la hay, el visual pasa a la regla fija;
  - la comparativa va siempre en barras.
- **Catálogo de visuales** (`CP.TIPOS_VISUAL`, `motion/src/componentes/visuales.tsx`): `contador` (cifra monoespaciada que rueda de `valor` a `hasta`), `cifras` (dos enfrentadas), `barras`, `linea`, `unidades` («12 de cada 100»), `pasos` (fichas del ciclo; en el ciclo rápido, el bucle que se acelera ×0,72 con su contador), `tarjeta` (ventana con el registro de ejemplo del caso), `medidor`, `cola` (fichas que se apilan o se vacían; biohazards con `--icono-flujo biohazard`) y `ninguno` (solo titular).
- **Cinta de pasos:** desde la primera escena del ciclo, una fila pequeña de fichas abajo de la banda con el paso activo (dos filas en la columna estrecha del horizontal). No sale si el visual ya son los pasos.
- **Tiempos** (`paneles_mc.py`): no hay marcas por palabra, así que `palabras_estimadas` reparte cada línea de `tiempos.json` entre sus palabras por sílabas (`audio_comic.silabas`, algo más tras coma o punto) dentro del tramo con voz de la `envolvente`, saltando las pausas de 3 fotogramas o más. Error típico: 0,1–0,2 s.
  - Cada palabra del titular sale un fotograma antes de que la diga la voz (sin tildes ni mayúsculas, o la misma raíz: «pierdes» ~ «pierde»); si no la dice, tras la anterior.
  - El visual **aparece** pronto (con la primera palabra o al 25 % de la escena) y su **acción** (el contador rueda, las barras crecen, la aguja gira) llega cuando la voz dice su cifra o su etiqueta (`f_accion`).
  - Las escenas seguidas con panel comparten banda; la banda entra y sale con una cortinilla de 8 fotogramas.
- **Estilo híbrido** (`CP.PALETA_PANELES`): la tipografía (Archivo Black y JetBrains Mono) y la maquetación de los shorts sobre un fondo oscuro propio con rejilla tenue, un degradado hacia la maqueta y un filo de acento, con los colores del tema activo.
- **Cámara** (`b_tecnico.encuadre`): `hueco_arriba` (vertical) y `hueco_izq` (horizontal) son ahora exactos: el objeto cabe entero en la parte libre del cuadro y se centra en ella. En las escenas con panel no se encuadran las insignias 3D (`extra`). Si el panel nombra una pieza y la escena no resalta ninguna, se resalta esa.
- **Montaje:** `b_montaje.py --paneles DIR` pone los PNG como tira de imagen `ALPHA_OVER` en el canal 3 (000000.png = fotograma 1 de la película) y no pone `tira_gancho` ni `tiras_comparativa`. El GIF sale entonces de `final.mp4`.
- **Previa:** cada `escena_N.png` lleva encima su fotograma de Motion Canvas (`escena_N_mc.png`); la hoja y la revisión de Gemini usan esas.
- **Versiones:** `paneles.json` se archiva en `historial/` y cada render crea `paneles/fotogramas.vN/` (con su `motion.json`). Son unos 1 970 PNG y 170 MB por versión para 80 s: las versiones viejas se pueden borrar a mano.

**Proyecto Motion Canvas** (`comic/motion/`; instalar una vez con `cd comic/motion && npm ci`, Node 24):
- `render.mjs --datos motion.json --salida DIR [--desde F --hasta F]` arranca Vite por programa, abre la página con el Chrome del sistema (`playwright-core`, `/usr/bin/google-chrome`, sin interfaz) y espera a que termine. Imprime `INFORME {json}`. Unos 58 fotogramas/s: 80 s de vídeo en ~35 s.
- **Sin el editor de Motion Canvas:** no tiene CLI de render, pero su plugin de Vite admite un `editor` propio. El nuestro (`renderizador/main.js`) carga las fuentes y renderiza en cuanto abre la página con `Renderer` y el exportador de secuencia de imágenes (PNG con alfa, `background: null`); el plugin escribe los fotogramas en `MC_SALIDA`.
- `vite.config.ts`: `MC_DATOS` (ruta del `motion.json`, alias `@datos`) y `MC_SALIDA`; las fuentes se sirven desde `descargas/fuentes` (`publicDir`).
- `src/escenas/paneles.tsx` orquesta tramos y paneles por fotograma absoluto (`hasta(f)` espera a `usePlayback().frame`); `src/componentes/` tiene la banda y la cinta, el titular y los visuales; `src/estilo.ts`, la paleta, las zonas y los formatos (es-ES). Comprobar tipos: `npx tsc --noEmit`.
- **Formato de `motion.json`:** en la cabecera de `paneles_mc.py`. Fotogramas 0-based: el `f` de Motion Canvas es el `f + 1` de Blender.

## Subtítulos con Motion Canvas

Subtítulos quemados al estilo de los shorts, para ver el vídeo sin sonido, más un `.srt` para subirlo aparte (LinkedIn, YouTube). Etapa `subtitulos`, parámetro `subtitulos` (activo por defecto; desactivado al crear un proyecto de estilo cómic, que ya lleva bocadillos y cartelas).

- **Bloques** (`subtitulos_mc.bloques`): los tiempos por palabra son los de los titulares de los paneles (`paneles_mc.palabras_estimadas`, por sílabas dentro de la envolvente de la voz; error 0,1–0,2 s). Cada línea se corta tras punto, dos puntos o punto y coma (y tras coma con 3 palabras o más). Cada frase se reparte en el mínimo de trozos de largo parecido con 6 palabras como mucho (8 en horizontal) y 2 líneas de texto. Una palabra suelta se une a la frase anterior. Un bloque entra un fotograma antes de su primera palabra y dura hasta el siguiente, o hasta el final de la línea de voz.
- **Dibujo** (`motion/src/escenas/subtitulos.tsx`): Archivo Black en mayúsculas, blanco con contorno oscuro y sombra; la palabra que suena, en el color `bueno` del tema (lima en cyberpunk). El bloque sube 0,2 em mientras aparece (3 fotogramas) y se va con un fundido de 2.
- **Dónde** (`CP.zona_subtitulos`, `CP.SUBTITULOS`): en vertical, letra de 62 px (1080 de ancho), 86 % del ancho, con el borde de abajo al 12 % del alto (margen de la interfaz del móvil). En horizontal, letra de 50 px, al 7 %, y con paneles, centrados en la parte libre de la derecha.
- **Cámara:** con la etapa hecha (`CP.usa_subtitulos`), `b_tecnico.encuadre` recibe `hueco_abajo` (≈ 0,22 del alto en vertical) además del hueco del panel, así que la maqueta no queda debajo del texto. Hay que rehacer `animacion` después de activarlos o desactivarlos.
- **Mismo proyecto Motion Canvas que los paneles:** `motion.json` lleva `tipo: "subtitulos"` y `src/project.ts` elige la escena según ese campo. Se renderiza con el mismo `render.mjs` (unos 40 s para 80 s de vídeo).
- **Montaje:** `b_montaje.py --subtitulos DIR` los pone como tira `ALPHA_OVER` en el canal 4, encima de los paneles. El `.srt` va junto al vídeo final con su mismo nombre (`final/final.vN.srt`), desplazado si hay cartela de título. La previa los superpone también (`escena_N_mc.png`).
- **Versiones:** cada ejecución crea `subtitulos/fotogramas.vN/` con `bloques.json`, `subtitulos.srt` (sin desplazamiento) y `motion.json`.

## Miniaturas y publicación (difusión en redes)

Nada garantiza que un vídeo se vuelva viral; estas etapas cuidan lo que más pesa en el clic y la retención.

- **`miniatura`** (`agente_comic.modo_miniatura`, `blender/b_miniatura.py`, `motion/src/escenas/miniatura.tsx`):
  - **Diseño** (`SISTEMA_MINIATURA`): 3 variantes con enfoques distintos (`dolor`, `cifra`, `curiosidad`): titular de 2–4 palabras, 1–2 palabras clave en color, una **cifra que tiene que estar en el guion** (`CP.numeros_guion`; si no, se quita) con su etiqueta, y el color (`bueno`, `problema`, `espera`). Sin IA, `miniaturas_por_reglas` (gancho, comparativa, título).
  - **Fondo**: la maqueta montada un segundo antes del final, en plano general acercado (×0,82–0,85) y con hueco para el texto: arriba en vertical (dentro del recorte central 3:4 de Reels) y a la izquierda en horizontal. Cycles en la GPU con 160 muestras como mínimo; la textura, con toda su fuerza.
  - **Composición** en Motion Canvas (`tipo: "miniatura"`, un fotograma por variante): titular en Archivo Black con el contorno del fondo del tema y la cifra en una pastilla inclinada justo debajo. Formatos: `variante_N_vertical.png` (1080×1920: portada de LinkedIn, Shorts, Reels y TikTok), `variante_N_linkedin.png` (1920×1080) y `variante_N_youtube.png` (1280×720).
  - **Ranking** (`SISTEMA_RANKING_MINIATURAS`): Gemini mira las 3 verticales y las ordena por probabilidad de clic para managers, con nota, motivo y una mejora. La mejor se copia como `mejor_vertical.png`, `mejor_linkedin.png` y `mejor_youtube.png`. Todo queda en `miniaturas.json`.
- **`publicacion`** (`modo_publicacion`, `SISTEMA_PUBLICACION`): con el guion, 7 fotogramas de los 3 primeros segundos del vídeo final y la mejor miniatura, Gemini escribe:
  - el **copy** de LinkedIn (primera línea de 150 caracteres como mucho, que es lo que se ve antes de «ver más»; texto breve; pregunta para comentar; 3–5 hashtags), de Shorts/Reels/TikTok y de YouTube;
  - 5 **títulos alternativos** para probar;
  - una **revisión para redes**: notas de 0 a 10 de gancho, claridad sin sonido, retención y miniatura, con fortalezas y cambios concretos que **no se aplican**.
  - Las cifras que no estén en el guion salen como avisos. Archivos: `publicacion.md` (todo), `copy_linkedin.txt`, `copy_shorts.txt` y `copy_youtube.txt` (listos para pegar) y `publicacion.json`.

## Marca (logo de la empresa)

Parámetro `marca`: carpeta del kit de marca (por defecto `~/Pictures/logo/vervux`, con `png/` y `fuentes/static/`); vacío, sin marca. `web_marca`: la web del cierre (`vervux.com`). Lo hace `marca.py` (PIL, sin Blender) siguiendo la guía del kit (`guia/index.html`): versión a color sobre fondos claros y la de fondo oscuro sobre oscuros (temas `cyberpunk` y `cristal`); área de protección de 1x (x = altura de la «v»); horizontal de 96 px de ancho como mínimo; sin sombras, contornos, efectos, rotaciones ni deformaciones.

- **Esquina:** `capa_esquina` compone un PNG transparente del tamaño del vídeo con el logo horizontal (17,5 % del lado corto, 189 px en 1080) abajo a la derecha, justo por encima de los subtítulos (o del margen de la interfaz si no hay subtítulos). El montaje lo pone en el canal 5 durante toda la película (`--logo`).
- **Cierre de marca:** `cartela_cierre` sustituye a la cartela «¡FIN!»: fondo Niebla (`#F4F5F8`; Noche `#10121B` en los temas oscuros), el logo vertical grande, la web en Plus Jakarta Sans y los créditos pequeños. Entra con un fundido de 8 fotogramas sobre el final de la película y dura 4 s (`--cierre`, canal 6).
- **Miniaturas:** el logo horizontal abajo a la derecha (en vertical, dentro del recorte 3:4), copiado junto a su `motion.json`. `miniatura --solo-render` reutiliza las variantes y el orden de la versión vigente y solo recompone.
- Los PNG quedan en `marca/` (`logo_esquina.png`, `cierre.png`, versionados). El logo va en el montaje: añadirlo o cambiarlo no obliga a volver a renderizar.

## Voz: tomas nuevas

La caché de voces es por contenido (modelo, voz, emoción, texto y ritmo). Para volver a sintetizar todas las líneas sin cambiar el guion: `audio --toma-voz N` (parámetro `toma_voz`, 0 por defecto, que es la clave de siempre). Las tomas anteriores siguen en `audio/`.

## Detalles (estilo técnico)

```bash
python3 agente_comic.py detalles --proyecto proyectos/<carpeta> --referencia referencias/detalles/maqueta_isometrica_detallada.jpg --densidad alta
python3 agente_comic.py todo --estilo tecnico --referencia mi_ilustracion.png --descripcion "..."
```

**Funcionamiento:**
1. Se renderiza la maqueta con las piezas lisas (`detalles/antes.png`).
2. Gemini recibe esa imagen, la lista de piezas con sus medidas y, opcionalmente, la imagen de referencia (`--referencia`). Con ellas decide **adornos** (`--densidad baja|media|alta`).
3. Se rehace `objetos` y se guarda `detalles/comparativa.png` (antes y después).

**`--completar`:**
- Conserva los adornos que ya hay y solo pide los de las piezas que aún no se han considerado (`consideradas` en `adornos.json`).
- A Gemini se le pasan los adornos existentes para que los nuevos sean coherentes: la tercera Lambda lleva el mismo cartel λ que las otras.
- La previa lo lanza sola cuando una revisión añade piezas.

**Adornos** (`comic_parametros.ADORNOS`):

| Tipo | Qué dibuja |
|---|---|
| `pantalla` | Encendida con halo, con un icono o con líneas de texto |
| `leds` | Fila de luces |
| `ranuras` | Bahías de rack con luz |
| `rejilla` | Lamas de ventilación |
| `tirador` | Asa o tirador |
| `tornillos` | Uno en cada esquina de la zona |
| `placa` | Tapa atornillada |
| `franja` | Banda de color |
| `boton` | Botón redondo |
| `teclado` | Teclado |
| `icono` | Icono pintado sobre la cara |
| `cartel` | Placa con icono sobre la pieza, mirando a cámara |
| `conector` | Bridas en los extremos de las mangueras; se añaden solas |

**Iconos vectoriales:** `sobre`, `lambda`, `candado`, `engranaje`, `nube`, `base_datos`, `grafo`, `ojo`, `rayo`, `llave`, `documento`, `chip`, `escudo`, `check`, `cruz`, `barras`, `traza`, `onda`, `persona` y `reloj`. Con `ninguno`, la pantalla queda vacía, para cuando hay piezas del guion delante.

**Colocación:**
- Cada adorno va en una cara de la pieza:
  - Cajas y paneles: `frente`, `izquierda` o `arriba`. Si se pide una cara que no se ve, pasa a la más visible.
  - Cilindros, conos y esferas: `lado` (envuelto sobre la superficie) o `arriba`.
- La posición `u, v` y el tamaño `ancho, alto` son fracciones de esa cara.
- Se dibujan en la capa `adornos` del propio objeto GP de la pieza, así que caen, se mueven y se ocultan con ella. En rayos X no se ven.
- Una pieza con adornos no lleva su detalle genérico (rayado, rejilla…).
- `adornos.json` va aparte del guion: sobrevive a las revisiones de la previa (los ids se conservan).

## Modelos prediseñados (estilo técnico)

```bash
python3 agente_comic.py todo --estilo tecnico --modelo-3d auto --descripcion "cómo funciona un taladro de columna"
python3 agente_comic.py todo --estilo tecnico --modelo-3d polyhaven:drill_press_01 --descripcion "..."
python3 agente_comic.py todo --estilo tecnico --modelo-3d https://sketchfab.com/3d-models/<nombre>-<uid> --descripcion "..."
python3 agente_comic.py todo --estilo tecnico --modelo-3d ~/modelos/motor.glb --descripcion "..."   # también .gltf .obj .fbx .stl .blend
```

**`auto`:**
1. Gemini Flash propone términos de búsqueda en inglés.
2. Se buscan candidatos en **Poly Haven** (más de 500 modelos CC0, descarga directa) y en **Sketchfab**.
3. Gemini mira la hoja de miniaturas numeradas (`modelo/busqueda/candidatos.png`) y elige uno.

**Sketchfab:**
- La búsqueda es libre, pero la descarga necesita tu token de API: <https://sketchfab.com/settings/password> → *API Token*.
- Guárdalo tú en `~/.config/agente_comic/sketchfab_token` (con `chmod 600`) o en la variable `SKETCHFAB_TOKEN`. Sin token, `auto` solo usa Poly Haven.
- Licencias aceptadas: `--licencias cc0,cc-by` por defecto (añade `cc-by-sa` si quieres). Nunca se aceptan NC ni ND.
- El crédito del modelo sale en la cartela de FIN.

**Conversión** (`blender/b_modelo.py`), sin ejecutar nada de lo descargado:
- **Importación:** glTF, que es solo datos. El modelo se apoya en el suelo, centrado; conserva su escala real si mide entre 0,15 y 3 m.
- **Partes:**
  - Un objeto del modelo es una parte.
  - Si viene en una sola malla, se separa por islas o por material.
  - Las partes diminutas se unen a la más cercana, hasta un máximo de 14.
- **Simplificación:** primero planar y después colapso, hasta unas 8 000 caras en total, repartidas por las caras originales de cada parte.
- **Color:** la textura se muestrea en las UV de cada cara y la media se pasa a la paleta técnica.
- **Hoja de partes:** `modelo/hoja_partes.png` tiene una vista con cada parte resaltada y su id.

**Guion:**
- Gemini agrupa las partes en piezas con nombre (cada parte en una sola pieza; las sobrantes van a `resto`).
- Recolorea con la paleta, decide rayos X, bisagras y movimientos, y escribe la explicación.
- La geometría ya está fijada; la revisión visual puede reagrupar, recolorear o cambiar planos.

**Dibujo** (`tecnico.dibujar_malla`):
- Cada cara es un relleno GP con su banda y un borde del mismo color que tapa las juntas.
- Las caras traseras se omiten en las piezas opacas.
- La tinta va en aristas vivas (más de 35° o de borde) y en las siluetas vistas desde la cámara, encadenadas en trazos largos.
- Los rayos X, el resalte, la sombra y el rig funcionan igual que con las primitivas.

## Recursos descargados (`descargas/LEEME.md`)

- **Fuentes** (OFL): Bangers y Comic Neue para el cómic; Archivo Black para el estilo técnico.
- **Texturas** (CC0): papel y cartón de ambientCG.
- **Materiales GP** de la demo *Bike Ride* (CC-BY-SA): van aparte, en `biblioteca/Materiales_GP_bike_CC-BY-SA.blend`.
- **Materiales GP oficiales** de Blender (Essentials).
- **Packs que piden correo:** deja su `.blend` en `descargas/manual/` y vuelve a ejecutar `materiales`.

## Acceso a Gemini

Es el mismo que el del agente del desierto:
- Cuenta `jjimenez@neosecure.com`, proyecto `project-b62861f4-f767-4aff-9f5`, región `global`.
- El token se obtiene con `gcloud auth print-access-token --account=…`, **sin cambiar la cuenta activa**.

Modelos:
- **Texto:** `gemini-3.1-pro-preview` por defecto; `--modelo gemini-3.5-flash` es más rápido.
- **Voz:** `gemini-2.5-flash-tts` por defecto; `gemini-2.5-pro-tts` da un ritmo y una entonación más estables. La API clásica de Cloud TTS no está habilitada en el proyecto.

**Qué se envía a Google:** la descripción, el guion, el texto de cada línea y los fotogramas de la previa. Con `--audio`, también tu audio, y con `detalles`, el render de la maqueta y la imagen de `--referencia`.

## Tiempos de referencia (RTX 4060)

- Las etapas de Blender tardan menos de 2 s cada una.
- Render: unos 35 s por 570 fotogramas a 960×540, y unos 2 min por 850 fotogramas a 1920×1080 o 1080×1920.
- Una ejecución de `todo` con Gemini y dos revisiones tarda entre 6 y 8 minutos.
