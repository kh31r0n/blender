# Agente de animación con Grease Pencil (cómic y técnico)

`agente_comic.py` genera animaciones completas en Blender 5.2 **sin interfaz**, dibujadas con **Grease Pencil**. Gemini (Vertex AI) escribe y revisa el guion y pone las voces; los scripts de `blender/` dibujan, riggean, animan y renderizan.

Hay dos estilos (`--estilo`):

| Estilo | Qué cuenta | Aspecto |
|---|---|---|
| `comic` (por defecto) | Historias con personajes | Colores muy vivos, tinta negra con temblor, tramas Ben-Day, bocadillos, cartelas, onomatopeyas |
| `tecnico` | Explicativos de un objeto, «así funciona X», pieza a pieza | Vista isométrica alta, papel con baldosas, paleta apagada, sombra proyectada azul cobalto, rayos X y resalte lima. Referencia en `referencias/yt_88DXBq8baS4/`; sin rótulos, lo cuenta la voz |

Los dos estilos admiten `--formato 2d|3d` y `--orientacion horizontal|vertical`. El técnico es vertical por defecto y tiene tres temas (`--tema clasico|iconos|neon`, ver «Temas y objetos-icono»).

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
| `4` `animacion` | Anima rigs, escenografía y cámara al ritmo del audio | `04_animacion.blend` |
| `efectos` | Cómic: bocadillos, cartelas, onomatopeyas, líneas de velocidad… Técnico: agua, vapor, burbujas, flechas, llama… | `04b_efectos.blend` |
| `previa` | Un fotograma por escena y revisión de Gemini en bucle (`--iteraciones`). Si una corrección empeora la nota, restaura la mejor versión | `previa/iter_N/` |
| `5` `render` | EEVEE: MP4 H.264 con voces AAC y una viñeta por escena | `render/` |
| `montaje` | Cartelas de título y FIN, vídeo final, página de viñetas y GIF | `final/` |
| `todo` | guion → (técnico: detalles) → objetos → rig → audio → animación → efectos → previa → render → montaje | — |
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
- **Montaje:** las piezas caen y rebotan por orden de montaje.
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
| `iconos` | Como un set de iconos isométricos vectoriales (`referencias/iconos/set_iconos_isometricos.png`): cuerpos blancos con el lateral en sombra azul claro, acentos lima, contorno negro grueso (×1,6) sin temblor, cajas con las esquinas redondeadas, fondo liso gris azulado sin paredes, papel ni grano, sombra azul muy clara |

- **Colores:** cada tema puede sustituir colores por nombre (`paleta`) y limitar los que usa el guion (`colores`); los demás se convierten con su `mapa` (en `iconos`, menta → lima y metal → gris_claro; en `neon`, menta → verde y violeta → morado).
- **Guía para el guionista:** cada tema puede añadir instrucciones al vocabulario (`guia`). El de `neon` pide una peana bajo cada componente (forma `peana`, con el componente encima a z = alto de la peana), un color por componente y mangueras de borde a borde a la altura de las peanas. `revisar_geometria()` avisa de los componentes que quedan en el suelo sin peana, y el validador pone las mangueras en el color del tema (`manguera`).
- **Juntas y esferas:** en los temas sin papel (`iconos`, `neon`), cada faceta lleva un borde fino de su color que tapa las juntas, y en las esferas cada faceta se recorta por los planos de las bandas de luz, así que los límites salen lisos. También se adaptan los adornos: las pantallas son claras con tinta en vez de oscuras con halo.
- **Dos tonos:** con `lateral` (tema `iconos`), las caras con luz llevan el color de la pieza y las que están en sombra, azul claro (en los cuerpos claros) o el color oscurecido.
- **Dónde se aplica:** `tecnico.aplicar_tema(params)` se llama al principio de cada etapa de `b_tecnico.py`.

**Objetos-icono** (`iconos_3d.py`, forma `icono` con `modelo`):
- **Qué son:** objetos prefabricados y ya detallados, hechos con las primitivas del estilo técnico. Gemini elige el `modelo`; `alto` es su tamaño (la dimensión mayor), `color` es el cuerpo y `acento` el color de los detalles (lima por defecto).
- **Modelos:** `reloj_arena` (TTL), `base_datos`, `embudo` (correlación), `campana` (alerta), `despertador`, `cronometro` (latencia), `candado`, `engranaje`, `monitor`, `portatil`, `servidor`, `robot` (agente), `orbe` (LLM), `llave` (clave, hash), `caja_herramientas` (tools), `diana` (acierto) y `escudo` (seguridad).
- **Datos de cada parte:** primitiva, medidas, posición y giro en coordenadas del modelo, y un rol de color: `c` cuerpo, `a` acento, `l` azul claro, `n` negro o `b` blanco. Se normalizan para que la dimensión mayor valga 1.
- **Vocabulario:** incluye las proporciones (ancho × fondo × alto por tamaño 1), para que Gemini sepa dónde acaba cada icono.
- **Dibujo:** cada parte se dibuja como una primitiva más dentro del mismo objeto GP. Las partes pequeñas (ojos, agujas) llevan la tinta más fina.
- **Para el resto del agente, un icono es una pieza normal:** rig, caída, resalte, rayos X, sombra y encuadre. No admite adornos.
- **Hoja de muestras:** `iconos_3d.LISTA` en una maqueta de prueba, renderizada con `b_tecnico.py --etapa objetos`.

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
