# Proyecto: animación LEGO en Blender

El usuario escribe en español: responde en español. Antes de tareas grandes suele pedir "hazme preguntas", así que haz una ronda corta de preguntas con opciones.

## Entorno

- **Blender 5.2.2:** instalado solo para el usuario en `~/.local/opt/blender`. El ejecutable es `~/.local/bin/blender`. La carpeta `~/blender/blender-5.2.2-linux-x64` es el tarball original y ya no se usa.
- **Modo sin interfaz:** trabaja siempre así: `blender -b archivo.blend -P script.py`, o `--python-expr`. No abras la interfaz gráfica, porque saldría en la pantalla del usuario.
- **GPU:** RTX 4060 (hay también una Intel UHD 770 integrada). EEVEE (`BLENDER_EEVEE`) y Cycles funcionan con `-b`. Desde el 2026-11-08 el usuario pide **Cycles en la GPU** para el agente de cómic (`gp_base.configurar_escena`, parámetro `motor`, por defecto `cycles`).
- **Node 24 y Motion Canvas:** Node está en `~/.local/bin/node`. El proyecto de los paneles es `comic/motion` (instalar con `npm ci`; versiones exactas, Motion Canvas 3.17.2). Se renderiza sin interfaz con `node render.mjs`, que abre `/usr/bin/google-chrome` con `playwright-core` (no descarga navegadores).
- **LDraw:** la biblioteca está en `~/ldraw`. El add-on ImportLDraw v1.3.0 está activado (módulo `io_scene_importldraw`). Se usa así: `bpy.ops.import_scene.importldraw(filepath=..., ldrawPath="/home/kheiron/ldraw")`. Crea un objeto `LegoGroundPlane` que hay que borrar, y su escala es 1 LDU = 0.0004 m (un ladrillo 2×4 mide 0.032 m).
  - **Guarda las últimas opciones usadas** en `ImportLDrawPreferences.ini`. Pasa siempre `realScale`, `defaultColour`, `useLogoStuds` y `bevelEdges` de forma explícita.
  - **Cambia el motor de la escena a Cycles** (CPU, 4 096 muestras). Después de importar, vuelve a poner `scene.render.engine = 'BLENDER_EEVEE'`.
  - **Al importar un `.dat` suelto**, el color "16" sale con `defaultColour`, que por defecto es "4" (rojo).
  - **Reutiliza mallas y materiales por nombre**, incluso de bibliotecas enlazadas. Importa en un archivo limpio y añade las mallas desde ahí.

## Estructura (`~/blender/anim`)

- `Minifigures.blend` es la importación de Mecabricks de `_The Chosen_ Custom Minifigures.zmbx`: 5 figuras y 65 piezas. **No lo sobrescribas.**
- `Minifigures_rig.blend` es la salida de `scripts/rig_minifigs.py`. El uso, el diccionario `FIGS` y los controles están en `scripts/README.md`.
- Otros archivos del proyecto: `ladrillo.*`, `ola_geonodes.*` y `edificio_lego.*` (ejemplos con LDraw y Geometry Nodes).

## Estructura (`~/blender/buildings`)

- `Nitro.blend` es la importación de Mecabricks de `Nitrody City! IV.zmbx`: unos 6 edificios y 10 463 piezas. La torre-hotel blanca y negra ocupa x∈[-140, -50] y z∈[-444, -138] mm. **No lo sobrescribas.**
- `Edificios_GN_marquesina_v2.blend` es la salida actual de `scripts/edificios_gn.py`: el grupo Geometry Nodes "Edificio LEGO", hecho con piezas LDraw y materiales de Mecabricks, con la marquesina del hotel. Los parámetros y la estructura están en `scripts/README.md`. `Edificios_GN.blend` y `Edificios_GN_marquesina.blend` son versiones anteriores que se conservan.
- `Ciudad_realista.blend` es la ciudad completa en "plástico LEGO fotografiado" para EEVEE. La genera `scripts/ciudad_realista.py`, que también crea `Nitro_realista.blend`, `Modulares_OMR_realista.blend` y `Piezas_realista.blend`. El shader común está en `scripts/lego_realista.py` y los recursos CC0, en `descargas/cc0/` (créditos en `LEEME.md`). Los detalles están en el README.
- La marquesina de la entrada de Nitro (sobre el porche, en la cara -X del hotel) está en x≈-136 y z∈[-304, -240] mm, a y=60.8: pendientes 3037/3045, placa 3666 con verja 3633 y pináculos 59900 + 78258.

## Estructura (`~/blender/desert`)

- `Desert1.blend` (= `Desert Arch.zmbx`), `Desert Hill.blend` y `Desert landscape.blend` son las referencias de Mecabricks. **No las sobrescribas.** Los `crear_desierto_*gn*.py` v1/v2 y sus `.blend` son intentos anteriores que se conservan.
- `Desierto_LEGO_GN_v3.blend` es la salida de `crear_desierto_lego_gn_v3.py`: el grupo Geometry Nodes "Desierto LEGO", con las piezas construidas dentro del grupo y todo en instancias.
- Los parámetros están en `desierto_parametros.py`. Las previsualizaciones y comprobaciones se hacen con `previa_desierto_v3.py -- --comprobar`.
- `agente_desierto_gemini.py` es el agente Gemini: Vertex AI, cuenta `jjimenez@neosecure.com` y proyecto `project-b62861f4-f767-4aff-9f5`; no cambia la cuenta activa de gcloud.
- Los detalles están en `desert/README.md`.

## Estructura (`~/blender/comic`)

- `agente_comic.py` es el agente de animación con Grease Pencil. Tiene dos estilos: `--estilo comic` (historias con personajes y colores vivos) y `--estilo tecnico` (explicativo isométrico de un objeto, a partir del vídeo de `referencias/yt_88DXBq8baS4`).
  - El técnico tiene tres temas:
    - `--tema clasico`: papel y paleta apagada.
    - `--tema iconos`: set de iconos isométricos de `referencias/iconos/` (blanco, lateral azul claro, lima, contorno negro grueso).
    - `--tema neon`: maqueta de infraestructura de `referencias/maqueta_neon/`, con peanas luminosas, mangueras de neón y colores vivos.
    - `--tema cyberpunk`: como `escenes/Cyberpunk_fixed.blend`, con mallas 3D, material toon, Line Art y EEVEE (lo impone el tema). Lo dibuja `comic/blender/cyberpunk.py`.
  - Gancho (`--gancho dolor|contraintuitiva|reto|auto|ninguno`): el vídeo técnico abre con una pregunta en voz y en pantalla (sin cartela de título delante) y sigue un caso concreto (`caso`) de principio a fin.
  - Workflow visible (`datos_vivos`, `pasos_ciclo`, `comparativa`; modo `enriquecer` para un guion existente): datos con números que cambian junto a los componentes, pasos numerados del ciclo que se encienden y gráfica comparativa final en el montaje.
  - Reglas comunes del estilo técnico: las piezas nuevas aparecen en dos tandas como mucho por escena, el resalte sale con fundido y a la vez en todas, los carteles se recolocan para no chocar ni tapar, y las fichas de un contenedor llegan por su manguera. Con `--icono-flujo biohazard`, las alertas que viajan por las mangueras son biohazards de colores.
    - `--tema cristal`: piezas de cristal con bordes de luz, líneas finas con nodos, circuito y paleta azul con acentos por función; render con Cycles en la GPU.
    - `--tema arcilla`: diorama de ingeniería futurista (referencias en `comic/referencias/arcilla/`), **todo malla, sin Grease Pencil ni Line Art** (tampoco efectos ni cartelas). Un solo plástico texturizado (Leather039 de ambientCG) para todo lo opaco, en el que solo cambia el color; acrílico solo en lo transparente (cintas, filos, tarjetas, fichas); suelo blanco con plataforma gris; luz principal detrás a la derecha a 68°; marcos moldeados y líneas continuas en los adornos; Khronos PBR Neutral, cámara a 35°, profundidad de campo y órbita lenta; Cycles en la GPU.
  - Tiene objetos-icono prefabricados (forma `icono` + `modelo`) en `comic/iconos_3d.py`.
- Modos: materiales, biblioteca, 0 guion, detalles (estilo técnico: adornos decididos por Gemini, con `--referencia` de imagen), 1 objetos, 2 rig, 3 audio, paneles, subtitulos, 4 animacion, efectos, previa (con revisión de Gemini), 5 render, montaje, miniatura, publicacion, todo y estado. Los detalles están en `comic/README.md`.
- La tabla única de parámetros, la paleta, el vocabulario, los esquemas y la validación están en `comic_parametros.py`. Gemini (texto, TTS y transcripción) va en `ia_vertex.py`, con la misma cuenta que el agente del desierto. El audio y los tiempos están en `audio_comic.py`.
- Los scripts de Blender están en `comic/blender/`:
  - `gp_base.py`: utilidades GP.
  - `escenografia.py` y `personajes.py`: estilo cómic.
  - `tecnico.py` y `b_tecnico.py`: estilo técnico.
  - `b_*.py`: etapas.
- **Paneles de datos con Motion Canvas** (estilo técnico, modo `paneles`, parámetro `paneles_mc`): los datos del caso, los pasos del ciclo, el gancho y la comparativa van en una franja arriba (vertical, `tam_panel` = 40 %) o una columna a la izquierda (horizontal), solo en las escenas con datos (`CP.escenas_con_panel`). Gemini diseña `paneles.json` (titular palabra a palabra con la voz + un visual de `CP.TIPOS_VISUAL`, sin cifras que no estén en el guion); `paneles_mc.py` lo pasa a `motion.json` y `comic/motion/render.mjs` lo renderiza en PNG con alfa (`paneles/fotogramas.vN/`), que el montaje pone encima de la película. Sin la etapa `paneles` hecha, Blender sigue dibujando los datos en 3D. Detalles en `comic/README.md`.
- **Subtítulos con Motion Canvas** (modo `subtitulos`, parámetro `subtitulos`, activo salvo en el estilo cómic): `subtitulos_mc.py` parte la voz de `tiempos.json` en bloques de 3–6 palabras (tiempos por sílabas, como los titulares) y el mismo proyecto `comic/motion` los dibuja (`src/escenas/subtitulos.tsx`, elegido por `tipo` en `motion.json`): mayúsculas con contorno y la palabra que suena en lima, en el tercio inferior. El montaje los pone en el canal 4 y escribe `final/final.vN.srt`; la cámara técnica deja libre esa franja (`hueco_abajo`).
- **Maqueta técnica** (`CP.ajustar_maqueta`, al validar el guion y en `objetos`): las mangueras con flujo miden al menos `largo_flujo` (1 m; separa las peanas con cortes por pasillos libres) y ninguna manguera aparece antes que los componentes que une. En los temas con mallas las mangueras no caen: se dibujan en 0,6 s con una chispa en la punta. En escenas con flujo, la cámara encuadra la manguera entera. `audio --toma-voz N` vuelve a sintetizar todas las voces.
- **Marca** (parámetro `marca`, por defecto el kit `~/Pictures/logo/vervux`; `marca.py`): logo pequeño abajo a la derecha todo el vídeo (por encima de los subtítulos), cartela de cierre con el logo y `web_marca` en lugar de «¡FIN!», y logo en las miniaturas, según la guía del kit (versión por fondo, área de protección, sin efectos). Va en el montaje: no hace falta volver a renderizar.
- **Difusión** (modos `miniatura` y `publicacion`, al final de `todo`): 3 miniaturas con titular y cifra del guion sobre un render de la maqueta (Blender + Motion Canvas; 1080×1920, 1920×1080 y 1280×720) ordenadas por Gemini según su probabilidad de clic, y el copy por plataforma (`copy_*.txt`), títulos alternativos y una revisión para redes sin aplicar (`publicacion.md`).
- **Modelos prediseñados** (estilo técnico, modo `modelo` o `--modelo-3d auto|polyhaven:<id>|<url de Sketchfab>|<archivo>`): `modelos_3d.py` busca en Poly Haven (CC0) y en Sketchfab, que necesita token en `~/.config/agente_comic/sketchfab_token`. Gemini elige el modelo, `blender/b_modelo.py` lo convierte en partes y se dibuja con GP (`forma: malla`). Lo descargado va en `comic/descargas/modelos/`.
- Cada proyecto vive en `comic/proyectos/<fecha>_<descripción>/`. Las etapas nunca sobrescriben: crean `.v2`, `.v3`, y `proyecto.json` apunta a la versión vigente. `biblioteca/` se regenera con los modos materiales y biblioteca.

## Reglas de trabajo

- **Archivos del usuario:** genera siempre un archivo nuevo y no modifiques los `.blend` del usuario.
- **Comprobación:** verifica con renders EEVEE y míralos. En los rigs, compara además las matrices evaluadas de las piezas con las del archivo original.
- **Archivos descargados** (`.zmbx`, `.zip`): léelos sin ejecutarlos. Un `.zmbx` es un zip con `scene.mbx` (JSON); léelo con `zipfile` y `python3 -I`.

## Convenciones de Mecabricks

- **Orden y nombres:** las piezas se importan como `part`, `part.001`, … en el mismo orden que la lista `parts` del `scene.mbx`. Cada entrada trae `configuration` (ID LEGO) y `matrix` (fila mayor, en mm, con Y hacia arriba). La posición en Blender es `(m[3], -m[11], m[7]) / 10`.
- **Unidades:** todas las piezas cuelgan de un `Empty` con escala 0.1, y sus ejes locales son los de Mecabricks (X = izquierda de la figura, Y = arriba, Z = frente). Así, 1 unidad local = 1 mm y 1 unidad de Blender = 10 mm.
- **Mallas compartidas:** varias piezas usan la misma malla (por ejemplo, todas las manos). No identifiques piezas por `obj.data.name`.
- **Puntos de articulación** (mm, en el espacio local de la pieza):
  - Hombro en el torso: `(±6.265, 8.99, 0)`, con 10.1° de caída fija en Z.
  - Muñeca: `(±2, -3.3, 7.7)` en el brazo y `(0, 1.119, -3.706)` en la mano, con 15.06° de inclinación en X. La mano gira sobre el eje Z del brazo.
  - Cadera a pierna: `(±4, -4.8, 0)`.
  - Cuello: `(0, 12.8, 0)`.
  - Parte superior de la cabeza: `(0, 9.6, 0)`.
  - Suelo: `(0, -16, 0)` desde la cintura.
  - Agarre de la mano: hueco de radio 1.6 mm a lo largo de la Y local, con el centro en Y≈2.2.
- **Brazos:** el giro 0 en Mecabricks deja el antebrazo al frente. Con +45° en X el brazo cuelga, y esa es la pose neutra.
- **Cabezas:** la cara de cada cabeza está impresa con un giro distinto. Como neutra se toma la dirección actual de la cabeza (solo la guiñada).

## Particularidades de la API de Blender 5.x

- **Vídeo:** pon `scene.render.image_settings.media_type = 'VIDEO'` antes de `file_format = 'FFMPEG'`.
- **`obj.matrix_world = M`:** no actualiza `matrix_world` hasta la siguiente evaluación del depsgraph. Para encadenar cálculos, calcula `matrix_basis` y `matrix_parent_inverse` directamente.
- **Emparentar a un hueso:** el espacio padre es la **cola** del hueso: `rig.matrix_world @ bone.matrix_local @ Translation((0, bone.length, 0))`.
- **`EditBone.matrix`:** asigna la posición de la cabeza, la dirección y el roll, y conserva la longitud. Pon `eb.length` después.
- **Pose Library:** una acción con un fotograma clave a la que se le aplica `action.asset_mark()` y se quita del rig (`animation_data.action = None`).
- **Entradas del modificador Geometry Nodes:** `mod["Socket_N"]` ya no existe. Usa `getattr(mod.properties.inputs, "Socket_N").value = v`; los menús se asignan por el nombre del elemento. Después llama a `ob.update_tag()` para que el depsgraph lo vuelva a evaluar.
- **Entradas múltiples** (Geometry to Instance, Join): toman primero el enlace con `multi_input_sort_id` mayor. Para fijar un orden con Pick Instance, enlaza en orden inverso.
- **Entradas con campo implícito** (`Instance Index`, el `ID` de Random Value): sin enlazar, usan el índice, y poner `default_value` no tiene efecto. Enlaza un valor.
- **Instancias evaluadas:** se leen con `ob.evaluated_get(dg).evaluated_geometry().instances_pointcloud()` (`instance_transform` y atributos). Conserva la referencia al `GeometrySet`. `.reference_index` se compacta, así que identifica los prototipos con un atributo propio.
- **Grid:** el nodo `Grid` ordena los vértices con X por fuera: `índice = i · VérticesY + j`.
- **Acciones:** `action.fcurves` ya no existe. Usa `bpy_extras.anim_utils.action_ensure_channelbag_for_slot(action, slot)` y `.fcurves`. El `id_type` de los datos GP es `GREASEPENCIL_V3`.
- **Render de otra escena:** `bpy.ops.render.render(write_still=True, scene=sc.name)`. Sin `scene=` renderiza la del contexto. `ortho_scale` se aplica a la dimensión mayor del cuadro.
- **Cycles en la GPU:** el dispositivo de cómputo (OptiX/CUDA) vive en las preferencias de Blender, no en el `.blend`. Hay que activarlo en cada proceso que renderiza, porque si no Cycles cae en silencio a la CPU: en el vídeo SOC fueron 5,2 s por fotograma frente a 0,5 con OptiX. Lo hace `gp_base.gpu_cycles(sc)`, que da error si no hay GPU. Para verificarlo, el proceso que renderiza tiene que tener cargadas `libcuda`/`libnvoptix` (`grep libnvoptix /proc/PID/maps`).

## Particularidades de Motion Canvas 3.17

- **Sin CLI de render:** el plugin de Vite admite `editor: <ruta a main.js>`, un «editor» propio que recibe el proyecto. El de `comic/motion/renderizador` renderiza al abrir la página con `new Renderer(project).render({..., size: new Vector2(w, h), background: null, exporter: {name: '@motion-canvas/core/image-sequence', ...}})`; el plugin escribe los PNG en su `output`. Con `name: '.'` van directos a esa carpeta (`000000.png`…).
- **El plugin es CommonJS:** en un paquete `"type": "module"`, `import motionCanvas from '@motion-canvas/vite-plugin'` da el módulo envuelto; usa `.default`.
- **Fuentes:** decláralas con `@font-face` en la página del editor y espera a `document.fonts.load(...)` antes de renderizar; si no, el canvas usa la de reserva.
- **Tramo:** `range` va en segundos e incluye el último fotograma: `[0, (N-1)/fps]` da N PNG.
- **Tiempos absolutos:** para sincronizar con `tiempos.json`, espera con `while (usePlayback().frame < f) yield;` en vez de acumular `waitFor`.
- **Tipos:** `src/` necesita `/// <reference types="@motion-canvas/core/project" />` (define `Callback` y los módulos `*?scene`).

## Particularidades de Grease Pencil v3 en Blender 5.2

- **API:** `bpy.data.grease_pencils.new()`; el tipo de objeto es `GREASEPENCIL`. `gp.layers.new(nombre, layer_group=grupo)`, `L.frames.new(n).drawing` y `drawing.add_strokes([n_puntos, …])`. Cada punto tiene `position`, `radius` (en unidades de mundo) y `opacity`.
- **Rellenos:** solo se pintan si `stroke.fill_id ≠ 0`. Los trazos con el mismo `fill_id` se rellenan juntos y forman agujeros (letras con «O»).
- **Colores planos:** pon `layer.use_lights = False`. Activado (es el valor por defecto) y sin luces, oscurece los colores al 25 %.
- **Ocultar capas:** usa claves en `layer.hide`. Una opacidad animada a 0 sigue escribiendo profundidad y deja huecos blancos en 3D.
- **Texturas de relleno:** son transparentes entre los motivos. Para que no se vea el fondo, dibuja debajo un relleno con el color base.
  - Una imagen generada por código y empaquetada con `pack()` pierde los píxeles. Guárdala como PNG y cárgala.
  - Las UV dependen del tamaño del trazo: en formas grandes la trama sale enorme.
- **Profundidad entre objetos:**
  - Comprobado el 2026-11-08 con EEVEE: un trazo GP situado detrás de un cubo de malla sale por encima, tanto en orden 3D como en 2D. Lo que deba quedar tapado por mallas tiene que ser malla. Line Art sí funciona, porque calcula qué líneas se ven.
  - Dos objetos GP en orden `2D` con el origen a la misma profundidad se mezclan mal (se pierden rellenos). Sepáralos.
  - Un objeto GP se dibuja encima de las mallas aunque esté detrás, también en orden `3D`. Un fondo bajo mallas tiene que ser una malla.
- **Emparentar capas:** `layer.parent = rig` y `layer.parent_bone = "hueso"`. El `matrix_parent_inverse` se fija al asignar. Una vez emparentadas, las capas ignoran la transformación del objeto GP.
- **Modificadores y efectos:** `GREASE_PENCIL_NOISE` con `step` hace la línea temblorosa, `GREASE_PENCIL_THICKNESS` compensa el grosor por plano y `FX_GLOW` da brillo. `MaterialGPencilStyle.show_stroke` y `.show_fill` funcionan, pero avisan de que desaparecerán en Blender 6.
- **Sonido:** un secuenciador con solo tiras de sonido no sustituye a la cámara. El render sale con la imagen 3D y el audio mezclado.
