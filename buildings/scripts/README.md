# Edificios LEGO con Geometry Nodes (piezas LDraw)

`edificios_gn.py` genera `~/blender/buildings/Edificios_GN_marquesina_v2.blend`. Las versiones anteriores (`Edificios_GN.blend`, sin marquesina, y `Edificios_GN_marquesina.blend`, la primera marquesina) se conservan, pero el script ya no las genera. El archivo contiene el grupo de Geometry Nodes **Edificio LEGO**, que levanta edificios con piezas LDraw reales al estilo de la torre-hotel de `Nitro.blend`:

- pisos de 64 mm;
- ventanas 60592 con su vidrio;
- esquinas 2357;
- alero negro de pendientes de 33° con verja de celosía y pináculos.

Los materiales son los de Mecabricks, sacados de `Nitro.blend`.

## Uso

```bash
blender -b -P ~/blender/buildings/scripts/edificios_gn.py
```

- Lee las piezas de `~/ldraw/parts` y los materiales de `Nitro.blend`, y guarda todo en `OUT`. **Ni `Nitro.blend` ni el `.zmbx` se modifican.** Si lo vuelves a ejecutar, sobrescribe `OUT`.
- La escala es la de Nitro y las minifiguras: 1 unidad de Blender = 10 mm, de modo que 1 LDU = 0.04, 1 stud = 0.8 y 1 piso = 6.4.
- Para crear un edificio nuevo: añade un objeto malla (vale uno vacío) y ponle un modificador Geometry Nodes con **Edificio LEGO**. La malla de entrada se ignora. El origen del objeto queda en el centro de la planta, a ras de suelo.
- El grupo está marcado como asset. Si añades `~/blender/buildings` como biblioteca de assets, se puede arrastrar a otros archivos y se trae consigo las piezas y los materiales.

## Parámetros del modificador

| Parámetro | Qué hace |
|---|---|
| **Pisos** | Número total de plantas, incluida la baja (entero, 1–100). Se puede animar con fotogramas clave. |
| **Ancho / Fondo (studs)** | Planta en studs (8–96). Funciona con valores pares e impares. |
| **Planta baja** | `Entrada hotel` pone una puerta doble con la marquesina descrita más abajo; con menos de 14 studs de ancho pasa a puerta simple. `Puerta simple` pone una puerta centrada. `Escaparates` usa ventanas altas 60593 y una puerta. `Sin puerta` repite el piso tipo. |
| **Remate** | `Alero con pináculos` es el estilo Nitro. `Cornisa plana` lleva vuelo de placas, un peto de ladrillo y tiles encima. `Azotea` es un techo plano de tiles. |
| Variación › **Semilla** | Cambia qué columnas de ventanas se tapian, qué jardineras salen y qué luces se encienden. |
| Variación › **Ventanas ciegas** | Probabilidad de que una columna de ventanas se tapie con 3245. El patrón es simétrico y se repite en todos los pisos y en la fachada opuesta. |
| Variación › **Jardineras** | Probabilidad de que una ventana lleve maceta y flores. Se decide por ventana y por piso. |
| Variación › **Luces encendidas** | Probabilidad de que el vidrio de una ventana use el material *Vidrio encendido*. Se decide por ventana y por piso. |
| Marquesina › **Ancho (studs)** | Ancho total (por defecto 12). Como mínimo es la puerta + 4, para que sobresalga 2 studs por lado; como máximo llega a las esquinas del edificio. Se redondea a par para quedar centrada. |
| Marquesina › **Vuelo (studs)** | Cuánto sale de la fachada (3–12, por defecto 4). Las 2 primeras filas son pendiente; el resto, cresta de ladrillos. |
| Marquesina › **Altura (placas)** | Desplazamiento vertical en placas (por defecto 1: la marquesina arranca justo sobre el marco de la puerta). |
| Marquesina › **Pináculos superiores** | Cuántos van en la cresta (por defecto 3). Si no caben, se limitan a mitad del ancho − 2: con 12 studs, 4 como máximo. |
| Marquesina › **Separación pináculos (studs)** | 0 = la mayor separación que cabe, simétrica respecto a la puerta. Con otro valor (mínimo 2) se usa ese paso, sin pasar del máximo. |
| Colores › *Pared, Marcos, Vidrio, Vidrio encendido, Molduras, Tejado, Azotea, Detalles, Puerta, Plantas, Flores, Pendientes marquesina* | Material de cada rol. Se elige entre los `LEGO <id> <nombre>`, que son la paleta completa de Nitro con 82 colores. *Pendientes marquesina* solo se aplica a las caras inclinadas de la marquesina; por defecto es `LEGO 26 Black pendiente`, un negro con grano como el de las pendientes de Mecabricks. |
| **Realizar instancias** | Por defecto el edificio queda como instancias, que es lo más ligero: uno de 40 pisos y 32×32 studs son unas 16 000 instancias. Actívalo solo si necesitas la malla real; ese mismo edificio pasa a 5,8 M de vértices. |

## Cómo está construido cada piso

Las capas van de abajo arriba y suman 64 mm:

| Capa | Altura | Piezas |
|---|---|---|
| Banda | 1 ladrillo | 1×1 a 1×4 |
| Ventanas | 4 ladrillos | dos 60592 apiladas, pilares 14716 + 3005, columnas ciegas 3245 |
| Banda | 1 ladrillo | 1×1 a 1×4 |
| Placas | 2 placas | 1×1 a 1×4 |

En cada esquina van seis 2357 y dos 2420. Las ventanas miden 2 studs, van separadas por pilares de 1 stud y quedan centradas en cada fachada. Las bandas usan aparejo alternado y dejan el hueco de la puerta en la planta baja.

## Marquesina de la entrada del hotel

Copia la marquesina del porche del hotel de Nitro (pendientes 3037/3045, placa 3666 con verja 3633 y pináculos 59900 + 78258) y le añade pináculos superiores, faldones laterales, una capa escalonada y ménsulas. Va centrada en la puerta de la fachada 0 y solo aparece con `Entrada hotel`. De abajo arriba (`v < 0` es hacia la calle):

| Capa | Piezas |
|---|---|
| Ménsulas, bajo cada extremo | pendiente invertida 3665a + placa redonda 6141 colgada |
| Placa escalonada | 1×1, 1×2 y 2×2, 1 stud más corta delante y a los lados |
| Placa base | Ancho × Vuelo |
| Tejado | Pendientes de 45° 3040b/3039/3038/3037 al frente, esquinas 3045 y faldones laterales; detrás, cresta de ladrillos 3005/3004/3003 con los studs a la vista |
| Cumbrera | Placas 1×N sobre la fila alta, con verjas 3633 centradas |
| Pináculos laterales | 59900 + 78258 sobre los extremos de la cumbrera, igual que en Nitro |
| Pináculos superiores | 3062b + 59900 + 78258 sobre la cresta. Si caen entre dos studs se apoyan en un *jumper* 3794b; si caen sobre un stud, en una placa 1×1 |

Las jardineras del piso 1 que quedarían encima de la marquesina se quitan. Las caras inclinadas de las pendientes llevan índice de material 1 (el importador LDraw las marca como `Material_*_s`), y por eso pueden tener su propio material.

## Estructura del grupo

Todos los subgrupos trabajan con puntos. Cada punto guarda la fachada `e` (0 frente, 1 derecha, 2 fondo, 3 izquierda), su posición `(u, v, z)` en el marco de esa fachada y el índice `pi` del prototipo. Las unidades son:

- `u`: studs a lo largo de la fachada.
- `v`: studs hacia dentro; los valores negativos sobresalen.
- `z`: unidades de Blender.

Al final, **LB Colocar** pasa los puntos a coordenadas del edificio e instancia los prototipos.

| Subgrupo | Función |
|---|---|
| `LB Celdas` | Un punto por stud del perímetro. |
| `LB Tramo` | Reparte una fachada en piezas de largo 1 a 4, con desfase de aparejo y hueco centrado. |
| `LB Ventanas` | Zona de ventanas, columnas ciegas y puertas. |
| `LB Esquinas` | Una pieza en cada esquina. |
| `LB Relleno` | Rectángulo de tiles 2×2, 1×2 y 1×1. |
| `LB Piso` | Un piso completo. |
| `LB Emitir` | Filtra puntos y les pone sus atributos. |

**Prototipos:** cada par (pieza, rol) es un Object Info del objeto `LD_<pieza>` (colección oculta *Piezas LDraw*), pasado por un Set Material con el material del rol, y entra en un Geometry to Instance siguiendo el orden de `PROTOS`.

## Añadir piezas o roles

1. Añade la pieza con `proto(...)` en `PROTOS`. Los grupos "por largo" deben ir seguidos, porque el índice se calcula como base + largo − 1.
2. Úsala desde un subgrupo con `emit(...)`.
3. Si es un vidrio o una puerta que comparte origen con su marco, añádela a `ESPECIAL` con el desplazamiento en LDU.

Las piezas se normalizan así:

- frente hacia −Y;
- origen en el centro de la huella y en la base del cuerpo;
- sin materiales, porque los pone Geometry Nodes.

## Comprobación

Probé 7 combinaciones de tamaño (pares e impares), planta baja y remate, y comparé la ocupación de voxels (stud × stud × placa) de todas las instancias. En todas salieron 0 solapes entre piezas, 0 huecos en los muros y el techo cubre toda la planta. El único solape permitido es la barra 78258 metida en su cono 59900.

Para la marquesina, además, hice un barrido de 21 combinaciones de ancho, vuelo, altura, número y separación de pináculos, y tamaño de edificio. En todas salieron 0 solapes y ninguna pieza delante de la fachada sin apoyo: cada pieza se apoya en otra, cuelga de otra encajada por sus studs o toca el muro. Por defecto salen 3 pináculos superiores y 2 laterales.

## Generación del barrio de 3×3 manzanas (`ciudad_3x3.py`)

El script `ciudad_3x3.py` genera el barrio completo de 3×3 manzanas LEGO en `~/blender/buildings/Ciudad_3x3.blend` y exporta los datos a `ciudad_3x3_layout.json`:

```bash
~/.local/bin/blender -b ~/blender/buildings/Edificios_GN_marquesina_v2.blend -P ~/blender/buildings/scripts/ciudad_3x3.py
```

### Características
- **9 manzanas de 32×32 studs** (25.6 BU) con calles de 16 studs (12.8 BU), en un área total de 160×160 studs (128 BU) centrada en el origen.
- **27 edificios** distribuidos en 5 arquetipos: Hotel landmark (15 pisos, manzana central B2), 8 edificios de apartamentos, 7 comercios con viviendas, 7 townhouses y 4 bloques de oficinas.
- **9 esquemas de color** tomados de la paleta Nitro / Mecabricks (3 edificios por esquema), con alternancia estricta para evitar colores de pared contiguos.
- **Organización limpia en colecciones:** Colección `Ciudad` con subcolecciones `Manzana_A1` hasta `Manzana_C3`, más plano de suelo urbano a z = -0.01 y zócalos de manzana a z = 0.0.
- **6 cámaras preconfiguradas y renderizadas:** `Camara` (aérea 3/4 general), `Cam_Planta` (planta ortográfica cenital), `Cam_Calle_1..3` (vistas peatonales a ras de calle a altura de minifigura z = 1.8 BU) y `Cam_Centro` (enfoque a la manzana B2 y marquesina del hotel).
- **Renders EEVEE** guardados en `~/blender/buildings/renders/ciudad_3x3/`.

### Cómo cambiar el layout, la semilla o edificios individuales
1. **Semilla maestra:** Cambia la variable `MASTER_SEED = 2026` al inicio de `ciudad_3x3.py`. Esto recalcula de forma determinista todas las variaciones internas (semillas de fachada, proporciones de ventanas ciegas y jardineras).
2. **Edificios individuales y lotes:** Edita la lista `BUILDINGS_DATA` en `ciudad_3x3.py`. Cada edificio especifica su manzana (`block`), lote (`lot`), arquetipo (`archetype`), pisos (`pisos`), ancho y fondo en studs (`ancho`, `fondo`), rotación (`rot_deg`), coordenadas de inicio en la manzana (`u_min`, `v_min`), tipo de planta baja (`pb`), remate (`rm`) y esquema de color (`scheme`).
3. **Re-ejecución:** Al volver a ejecutar el comando, se valida automáticamente que no existan colisiones entre sobres envolventes, se actualiza `Ciudad_3x3.blend`, se exporta el layout actualizado a `ciudad_3x3_layout.json` y se actualizan los renders.

## Ciudad Completa 3×3 con Modulares Oficiales y Nitrody City (`ciudad_completa.py`)

Integra las tres fuentes en una maqueta urbana cohesiva de 3×3 manzanas (416×320 studs / 332.8×256.0 BU):
1. **Nitrody City:** Sección urbana de Mecabricks (10.463 piezas) como hito central en la manzana B2.
2. **14 Edificios Modulares Oficiales LEGO (OMR):** Importados desde LDraw, normalizados e instanciados rodeando la manzana B2.
3. **Edificios Procedurales "Edificio LEGO":** Generados paramétricamente mediante Geometry Nodes en los 34 lotes restantes con arquetipos variados (apartamentos, comercios, adosados, oficinas y pequeños hoteles).

### Scripts del flujo de trabajo

1. **Construir biblioteca modular (`importar_modulares.py`):**
   ```bash
   ~/.local/bin/blender -b -P ~/blender/buildings/scripts/importar_modulares.py
   ```
   - Importa los 14 sets oficiales desde `descargas/omr/` a escala 1 BU = 10 mm (0.8 BU/stud).
   - Normaliza cada modelo en su colección `MOD_<set>_<nombre>`: centro de placa en (0, 0), superficie superior en z = 0 y fachada a la calle orientada hacia −Y (Sur).
   - Guarda el resultado en `~/blender/buildings/Modulares_OMR.blend` (26 MB).

2. **Generar la ciudad completa y renders (`ciudad_completa.py`):**
   ```bash
   ~/.local/bin/blender -b ~/blender/buildings/Edificios_GN_marquesina_v2.blend -P ~/blender/buildings/scripts/ciudad_completa.py
   ```
   - Abre headless el generador base.
   - Vincula de forma relativa (`//Modulares_OMR.blend` y `//Nitro.blend`) las colecciones pesadas como empties de tipo `COLLECTION`.
   - Genera los edificios procedurales respetando la línea continua de fachada (retranqueo de 8 studs / acera de 6.4 BU) y la regla de no repetición de color de pared entre vecinos.
   - Limita todas las alturas generadas (`Pisos <= 8`) para subordinarse a la Torre Nitro (56.55 BU).
   - Exporta el layout a `ciudad_completa_layout.json` y guarda `Ciudad_completa.blend`.
   - Renderiza las 7 cámaras a 1080p con EEVEE (AgX) en `~/blender/buildings/renders/ciudad_completa/`.

3. **Ejecutar la suite de validación (`validate_ciudad_completa.py`):**
   ```bash
   ~/.local/bin/blender -b ~/blender/buildings/Ciudad_completa.blend -P ~/blender/buildings/scripts/validate_ciudad_completa.py
   ```
   - Valida en un proceso Blender limpio: resolución de enlaces, inventario de 14 modulares, ausencia de Mini Modulars, alturas, integridad de nodos (0 advertencias, instancias puras), nivel z = 0 y confinamiento sin solapes.

### Personalización: Layout, semillas e intercambio de modulares

- **Cambiar la semilla maestra:** Modifica `MASTER_SEED = 2026` en `ciudad_completa.py`. La aleatoriedad determinista recalcula todas las semillas de fachada y probabilidades de jardineras y ventanas ciegas.
- **Intercambiar o mover un modular:** Modifica el diccionario `MODULAR_ASSIGNMENTS` en `ciudad_completa.py`. Asigna la clave del lote (ej. `"A2_N1"`) a la colección deseada (`MOD_...`), especificando el ángulo de rotación (`rot_deg`: 0 para Sur, 90 para Este, 180 para Norte, 270 para Oeste).
- **Modificar arquetipos generados:** Edita la lista `GENERATED_LOTS` en `ciudad_completa.py` ajustando pisos, ancho, fondo, arquetipo y esquema cromático.


## Ciudad realista en EEVEE (`ciudad_realista.py`)

Convierte la ciudad completa en "plástico LEGO fotografiado", pensada para animación a 1080p. Un fotograma tarda unos 16 s en la RTX 4060; el primero tarda algo más porque compila los shaders.

```bash
python3 -I ~/blender/buildings/scripts/empaquetar_imperfecciones.py      # solo si cambian las texturas CC0
blender -b -P ~/blender/buildings/scripts/textura_logo.py                # solo si se quiere otro logo
blender -b -P ~/blender/buildings/scripts/ciudad_realista.py             # los cuatro pasos (~5 min)
blender -b -P ~/blender/buildings/scripts/ciudad_realista.py -- ciudad   # o solo algunos: nitro modulares piezas ciudad
```

Genera cuatro archivos nuevos y no toca ninguno de los anteriores:

| Archivo | Contenido |
|---|---|
| `Nitro_realista.blend` | Nitro con el shader nuevo (unidad 0.1, porque sus piezas van en mm). |
| `Modulares_OMR_realista.blend` | Los modulares con el shader nuevo y sus colores pasados a la paleta Mecabricks. |
| `Piezas_realista.blend` | Las piezas del generador con bisel, y las placas de suelo, importadas en un archivo limpio. |
| `Ciudad_realista.blend` | La ciudad; enlaza los dos primeros y añade las piezas del tercero. |

Los renders de las 7 cámaras y las comparaciones antes/después están en `renders/ciudad_realista/`.

### Shader común (`lego_realista.py`)

**Grupo "LEGO realista"** (y su variante transparente): Principled de ABS (IOR 1.54, subsurface leve) con las entradas *Variación*, *Huellas*, *Rayas*, *Polvo*, *Logos* y *Rugosidad*.

- **Variación por pieza:** se toma de *Object Info › Random*. Funciona con objetos, con instancias de colección y con instancias de Geometry Nodes.
- **Imperfecciones:** una sola textura RGB (R huellas, G arañazos, B polvo) con proyección en caja sobre las coordenadas del objeto, desplazada al azar por pieza. El polvo solo cae en las caras que miran hacia arriba.
- **Logos de los studs:** no son geometría, sino un relieve sacado de un mapa de alturas en coordenadas de mundo. Funciona porque toda la ciudad está en la rejilla de studs: el centro del stud está en el centro de su celda de 0.8, y su cara superior, a 0.16 de un múltiplo de 0.32.

  Un stud con logo en geometría multiplica por 25 los vértices de la pieza, y a 1080p el relieve se ve igual. Por eso el logo va en el shader para todas las fuentes y a cualquier distancia.

**Cómo se aplica:** no se tocan los materiales uno a uno; se rehace el interior de los grupos base que comparten.

| Fuente | Grupo base | Unidad |
|---|---|---|
| Mecabricks (Nitro y la paleta del generador) | `mb_base_solid` / `mb_base_transparent` | Nitro 0.1; el generador 1 |
| ImportLDraw (modulares, placas) | `Lego Standard*` / `Lego Transparent` | 1 |

Las impresiones, los stickers, el grano de las pendientes y las mezclas de decoración viven fuera de esos grupos y no cambian.

**Colores LDraw:** se traducen a la paleta Mecabricks (`paleta_mecabricks.json`) con el ID LEGO de `LDConfig.ldr`. Los 16 códigos sin equivalente conservan el color del importador.

### Ciudad

- **Piezas del generador:** las `LD_*` se cambian por versiones con el bisel del importador, y así se ven las juntas entre ladrillos. El grupo "Edificio LEGO" no se modifica.
- **Calles:** placas de carretera oficiales con borde amarillo:

  | Placa | Uso |
  |---|---|
  | 44336p01 | recta |
  | 44341p01 | te (bordes de la circunvalación) |
  | 44342p01 | curva (esquinas) |
  | 44343p01 | cruce con paso de peatones |

- **Lotes y manzana B2:** baseplates 3811 en Light Bluish Grey en cada lote generado y en toda la manzana B2. En B2 sus studs quedan dentro de las placas de Nitro, como en un montaje real.
- **Acabado mate:** los baseplates y la calzada usan una copia mate del grupo base (rugosidad 0.38); con la rugosidad normal la calle hacía de espejo.
- **Luz:** cielo HDRI de Poly Haven. EEVEE saca el sol del HDRI con sombras, así que la lámpara `Sol` queda oculta.
- **Render:** EEVEE con raytracing en pantalla, Fast GI, 32 muestras y AgX con *Medium High Contrast*.

### Limitaciones

- Los logos del shader tienen todos la misma orientación. No salen en studs fuera de la rejilla (piezas desplazadas medio stud o studs laterales).
- Nitro no tiene bisel en geometría: el bisel de los materiales de Mecabricks solo funciona en Cycles.
- La exposición depende de la fuerza del HDRI (`LR.iluminacion(..., fuerza=1.0)`): con esta luz los colores oscuros, como el Dark Red, se ven más vivos que con la iluminación plana anterior.
