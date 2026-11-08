# Desierto LEGO con Geometry Nodes (v3)

`Desierto_LEGO_GN_v3.blend` contiene el objeto `Desierto_LEGO` con el modificador **Desierto LEGO**. Es un grupo de Geometry Nodes no destructivo que levanta un desierto hecho solo con piezas LEGO:

- dunas escalonadas con cuñas,
- colinas,
- mesetas de roca con estratos,
- rocas sueltas,
- arcos naturales con abertura.

Las piezas se crean dentro del propio grupo, a la medida de la celda: ladrillos biselados con studs, placas y cuñas. **No se reutiliza ninguna malla.** Todo sale como instancias: nada se realiza.

Las escenas `Desert1.blend` (= `Desert Arch.zmbx`), `Desert Hill.blend` y `Desert landscape.blend` han servido solo como referencia de estilo: el arco de 1×1 con placas, las laderas de cuñas y la arena Tan con rocas. Los intentos anteriores (`crear_desierto_*gn*.py` v1/v2) se conservan sin cambios.

![Vista hacia el arco](previa_desierto_v3.png)
![Vista general](previa_desierto_v3_general.png)

## Archivos

| Archivo | Qué es |
|---|---|
| `crear_desierto_lego_gn_v3.py` | Generador: materiales, grupo GN, objeto, cámaras, sol y cielo. Guarda `Desierto_LEGO_GN_v3.blend` y `presets/por_defecto.json` / `presets/esquema.json`. |
| `desierto_parametros.py` | Tabla única de parámetros (clave ASCII → socket en español, tipo, rango, descripción). La usan los tres scripts. |
| `previa_desierto_v3.py` | Aplica presets, coloca las cámaras, renderiza y ejecuta las comprobaciones numéricas y los tiempos. |
| `agente_desierto_gemini.py` | Agente que dirige el generador con Gemini (Vertex AI): descripción → preset → render → revisión. |
| `presets/` | `por_defecto.json`, `esquema.json`, `barjanes.json`, `canon_rojo.json`. |
| `agente/<fecha>_<descripción>/` | Resultados del agente (presets, `.blend`, renders y `log.json`). |

## Uso

```bash
# regenerar el .blend (sobrescribe solo Desierto_LEGO_GN_v3.blend)
blender -b -P ~/blender/desert/crear_desierto_lego_gn_v3.py

# previsualizaciones y comprobaciones
cd ~/blender/desert
blender -b Desierto_LEGO_GN_v3.blend -P previa_desierto_v3.py -- --comprobar \
    --previa previa_desierto_v3.png --general previa_desierto_v3_general.png

# aplicar un preset y guardar una copia (nunca sobrescribe un archivo existente)
blender -b Desierto_LEGO_GN_v3.blend -P previa_desierto_v3.py -- \
    --preset presets/canon_rojo.json --guardar canon_rojo.blend --previa canon_rojo.png
```

**Desde la interfaz:** selecciona `Desierto_LEGO` y ajusta las entradas del modificador. Están en seis paneles y cada una tiene su descripción emergente.

Las notas de uso también están dentro del `.blend`, en el texto `LEEME_Desierto`, que se muestra en el marco "Notas de uso" del árbol de nodos.

## Parámetros

| Panel | Entradas |
|---|---|
| **Terreno** | Dimensión X/Y (enteros, 1000), Resolución X/Y (celdas = studs, 250), Semilla, Altura de escalón (placas), Grosor de la base, Holgura entre piezas, Mostrar studs, Submuestreo en el visor |
| **Dunas** | Tipo de duna (Transversales / Barjanes / Estrella), Altura, Escala (longitud de onda), Dirección del viento, Asimetría (cara de avalancha), Agudeza de cresta, Sinuosidad, Altura y escala de colinas, Pendientes en bordes, Probabilidad de pendientes |
| **Erosión** | Iteraciones (erosión térmica), Talud máximo, Cárcavas, Escala de cárcavas, Limpiar picos sueltos |
| **Rocas** | Densidad, Tamaño, Altura, Gradas de las mesetas, Grosor de estrato, Densidad y tamaño de rocas sueltas |
| **Arcos** | Densidad (arcos por 1000×1000), Máximo, Luz, Altura, Grosor, Profundidad, Redondez, Abocinado de patas, Erosión del arco, Variación de tamaño, Radio del pedestal |
| **Materiales** | Material arena, Material roca, 3 colores de arena, 4 colores de roca, Variación de color |

**Escala:**
- `celda = Dimensión / Resolución`, en cada eje; por defecto, 4 unidades.
- Las proporciones LEGO se mantienen respecto a la celda: placa = 0.4 × celda, stud de radio 0.3 y altura 0.2125 × celda.
- Un escalón mide `placa × Altura de escalón`; por defecto, 3 placas = 1 ladrillo = 4.8 unidades.

## Cómo está hecho

El grupo principal llama a 14 subgrupos `DL …`, cada uno con marcos etiquetados:

1. **DL Rejilla:** `Grid` de Res X × Res Y puntos, uno por stud. El índice es `i · Filas + j` (el nodo Grid recorre X por fuera). Con `Is Viewport`, el submuestreo solo afecta a la vista 3D.
2. **DL Relieve.**
   - Dunas con perfil asimétrico a lo largo del viento (`DL Perfil de duna`) y deformación del dominio con ruido.
   - Barjanes: una media luna por celda de Voronoi, con los cuernos hacia sotavento.
   - Estrella: tres trenes de dunas a 60°.
   - Colinas de fBm.
   - Mesetas: Voronoi deformado, con gradas, cima plana y cárcavas solo en los costados.
3. **DL Erosión:** zona de repetición de erosión térmica con las 4 vecinas (`DL Vecinos` + `Sample Index`). La roca casi no se erosiona.
4. **DL Arcos.**
   - **Colocación:** Poisson sin solapes, alineada a los studs y girada 0° o 90°. La base es la pata más baja.
   - **Terreno:** las dunas se rebajan alrededor del arco, se abre un cauce bajo la abertura y se levanta un pedestal de roca en las patas.
5. **DL Niveles:** cuantización, limpieza de picos y cuñas.
   - La cuña mira cuesta abajo según el gradiente de la altura continua. La de esquina solo va donde la pendiente es diagonal.
   - Una vecina con cuña cuenta un nivel menos al calcular los costados visibles.
6. **Piezas:**
   - **DL Cimas:** macrobloques de 4×4 en ranuras de 2×4. Se usa 2×4, 2×2, 1×2 o 1×1 según coincidan nivel y material, y solo emite la celda ancla. También coloca las rocas sueltas.
   - **DL Laterales:** solo los niveles visibles, con aparejo a soga de 1×2.
   - **DL Arcos: vóxeles:** banda superelíptica en una rejilla de celda × placa.
     - Solo se guardan los vóxeles de superficie.
     - Tres placas se funden en un ladrillo 1×1.
     - La erosión solo actúa en la cara exterior y por encima del pedestal: la abertura nunca se cierra y las patas apoyan macizas.
     - Si un arco pasaría de unos 150 000 vóxeles, el vóxel crece a `m` celdas.
7. **DL Color:** atributo `color_lego` por pieza.
   - Arena: Tan, con Dark Tan en los valles entre dunas y en manchas.
   - Roca: estratos cíclicos por cota (Medium Nougat / Nougat / Reddish Brown), con Dark Orange de acento.
**Juntas sin agujeros:**
- Las piezas ocupan su celda entera; la junta la dibuja el bisel de las aristas superiores ("Holgura entre piezas" fija su ancho).
- Las aristas inferiores no llevan bisel, y el bisel vertical se queda en el 70 % superior de cada pieza.
- Cada celda lleva una tapa medio escalón por debajo de su pieza visible más baja. Así, aunque los niveles ocultos no se instancian, por las juntas nunca se ve el vacío.
- Comprobado con fondo transparente: 0 píxeles sin geometría en vista cenital ortográfica, y 12 de 10 millones (grietas de rasterizado) en perspectiva.

8. **DL Prototipos:** 16 piezas (incluida la tapa del fondo de cada celda) × 2 materiales en un `Geometry to Instance`, y después `Instance on Points` con `Pick Instance`.

**Materiales "Arena LEGO" y "Roca LEGO":**
- Usan el shader "LEGO realista" de `~/blender/buildings/scripts/lego_realista.py`.
- Leen `color_lego` y `unidad_lego` como atributos de instancia (`Attribute > Instancer`).
- Las texturas CC0 se enlazan desde `~/blender/buildings/descargas/cc0`.

**Luz:**
- Cielo HDRI de `lego_realista.iluminacion()`, templado y sin extraer su sol.
- Sol de escena bajo, desde barlovento, para que las caras de avalancha queden en sombra.

## Rendimiento (RTX 4060, Blender 5.2, evaluación del modificador)

| Caso | Tiempo | Instancias |
|---|---|---|
| 250 × 250 (por defecto) | ~0.1 s | ~113 000 (62 500 son tapas de 4 vértices) |
| 500 × 500 | ~0.3 s | ~450 000 |
| 1024 × 1024 (máximo) | ~1.5 s | ~1 900 000 |
| 250 × 250 con submuestreo 2 en el visor | ~0.04 s | ~28 000 |

## Comprobaciones (`--comprobar`)

**Generales:**
- Todas las piezas dentro de Dimensión X/Y.
- Las cimas están en niveles cuantizados.
- Hay cuñas, roca y rocas sueltas, y ninguna roca suelta flota.

**En cada arco:**
- Abertura libre: no hay vóxeles en el vano.
- Banda continua de pata a pata (inundación con 26 vecinos sobre las celdas ocupadas).
- Patas apoyadas: el contorno exterior de cada pata toca el terreno.

**Tiempos:** se mide la evaluación en 16 variantes.

Además, la última revisión pasó estas mismas comprobaciones de arcos en otras 7 configuraciones: por defecto, semilla 123, resolución 100, 500 y 1024, dunas de 250 con arcos grandes, y barjanes con 3 arcos.

## Agente Gemini (`agente_desierto_gemini.py`)

El Geometry Nodes genera todas las piezas. El agente solo traduce una descripción en parámetros, mira el render y corrige:

1. Gemini recibe la descripción y el esquema, y devuelve una lista de pares `clave`/`valor`.
2. `desierto_parametros.limitar()` convierte los tipos y acota los rangos.
3. Blender, sin interfaz, aplica el preset a una **copia** del `.blend`, la guarda y renderiza las dos vistas a 960×540.
4. Gemini revisa las imágenes y devuelve `{problemas, puntuacion, cumple, cambios}`.
5. Se repite hasta que cumpla o se llegue a `--iteraciones` (3 por defecto).

```bash
python3 agente_desierto_gemini.py --probar                      # token + llamada mínima
python3 agente_desierto_gemini.py --descripcion "dunas altas en estrella y dos arcos grandes de roca rojiza"
python3 agente_desierto_gemini.py --seco --descripcion "..."    # solo el primer preset, sin Blender
python3 agente_desierto_gemini.py --modelo gemini-3.5-flash --descripcion "..."   # más rápido
```

**Acceso:**
- Vertex AI en el proyecto `project-b62861f4-f767-4aff-9f5`: es el de la configuración gcloud "neosecure" y tiene `aiplatform.googleapis.com` habilitado.
- El token se obtiene con `gcloud auth print-access-token --account=jjimenez@neosecure.com`. **No cambia la cuenta activa de gcloud.**
- Si el token caduca, ejecuta `gcloud auth login jjimenez@neosecure.com`.
- La API de "Gemini Enterprise" (Discovery Engine) no está habilitada; por eso se usa la API de Gemini en Vertex.

**Modelo:**
- Por defecto, `gemini-3.1-pro-preview`, el Pro más reciente disponible en el proyecto en noviembre de 2026.
- También responden `gemini-3.5-flash` y `gemini-3-flash-preview`.

**Qué se envía a Google:** la descripción, el esquema de parámetros, los presets y los renders de 960×540. Cada iteración son dos llamadas, de unos 10 000 tokens de entrada cada una, con imágenes en la revisión.

**Salida:** `agente/<fecha>_<descripción>/`, con `preset_N.json`, `desierto_N.blend`, `previa_N.png`, `general_N.png`, `informe_N.json` y `log.json`, donde quedan todas las respuestas, avisos, tiempos y tokens.

## Particularidades de Blender 5.2 encontradas aquí

- **`Instance Index` y el `ID` de Random Value:** sin enlazar, usan el índice implícito; poner `default_value` no tiene efecto. Hay que enlazar un valor, o calcular a partir de la semilla sin nodo aleatorio.
- **Leer instancias desde Python:** `obj.evaluated_get(dg).evaluated_geometry().instances_pointcloud()` da `instance_transform` y los atributos de las instancias.
  - Conserva la referencia al `GeometrySet`; si no, la nube de puntos se libera.
  - `.reference_index` se compacta (Instance on Points quita las referencias sin usar), así que no sirve para identificar el prototipo: usa un atributo propio (`proto`).
- **Ruta del render:** `scene.render.filepath` relativa se toma respecto al `.blend`. Usa rutas absolutas.
