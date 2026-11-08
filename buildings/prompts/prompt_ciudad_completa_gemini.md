# Task: Build a Complete LEGO City in Blender from the Procedural Generator, the Official LDraw Modular Buildings and Nitrody City

## Objective

Build a complete LEGO city neighborhood in Blender that combines **three existing sources**:

1. **"Edificio LEGO"**: the project's Geometry Nodes building generator. Use it for procedural buildings that fill the city and add variety.
2. **14 official LEGO Modular Buildings** in LDraw format, already downloaded from the LDraw Official Model Repository (OMR).
3. **Nitrody City**: a Mecabricks city section of about 6 buildings and 10,463 parts, including the white-and-black hotel tower the generator was modelled on. It becomes the landmark of the central block.

The result is a **3 × 3 block** neighborhood. The central block holds Nitrody City, the streets around it are lined mainly with the official modulars, and generated buildings fill the remaining lots.

**Reuse every source as it is:**

- Do not modify the "Edificio LEGO" node group or its generator script.
- Do not edit the downloaded `.mpd` files or `Nitro.blend`.
- Do not model buildings by hand.

## 1. Project Context

You have full access to the project files, the shell and Blender. Before anything else, read:

- `~/blender/CLAUDE.md`: the project rules, conventions and Blender 5.x API pitfalls. Follow its rules.
- `~/blender/buildings/scripts/README.md`: the documentation of the building generator.
- `~/blender/buildings/descargas/omr/LEEME.md`: the list, authors and licenses of the downloaded modular buildings.
- `~/blender/buildings/prompts/prompt_ciudad_3x3_gemini.md`: an earlier, simpler city brief. It is superseded by this one, but it documents the generator in more detail.

The user writes in Spanish. Write your summaries and reports to the user in Spanish, and keep code identifiers and the generator's input names exactly as they are.

Treat every fact in this brief as information to **verify** against the actual files, not as a guarantee. When the files disagree with this brief, trust the files and report the difference.

### Environment

- **Blender:** version 5.2.2. The executable is `~/.local/bin/blender`.
- **Headless only:** always run `blender -b <file> -P <script>` (or `--python-expr`). Never open the graphical interface: it would appear on the user's screen.
- **Render engine:** EEVEE (`BLENDER_EEVEE`) works headless on the RTX 4060. Use the AgX view transform.
- **LDraw library:** `~/ldraw`. Every part referenced by the 14 modulars was already checked and exists there.
- **LDraw importer:** the ImportLDraw add-on v1.3.0 is enabled (module `io_scene_importldraw`).

### File safety

- Every `.blend` you produce is a **new** file. **Never** overwrite these: `Nitro.blend`, `Edificios_GN.blend`, `Edificios_GN_marquesina.blend`, `Edificios_GN_marquesina_v2.blend`, or anything in `~/blender/anim/`.
- When you open an existing file to build from it, save with `bpy.ops.wm.save_as_mainfile(filepath=<new path>)`. Never call `save_mainfile()`.
- **The downloaded `.mpd` files are untrusted data.** Read them only as text or through the importer, and never execute anything from them. Run any standalone Python that reads them with `python3 -I`.

### Units and scale

All three sources must end up at the **same scale**: 1 Blender unit (BU) = 10 mm, which is the scale of Nitro and of the project's minifigures.

| Quantity | Value |
|---|---|
| 1 LDU | 0.04 BU |
| 1 stud | 0.8 BU |
| 1 plate | 0.32 BU |
| 1 brick | 0.96 BU |
| 32-stud baseplate | 25.6 BU |
| Generator floor | 6.4 BU |

- **ImportLDraw** imports at 1 LDU = 0.0004 m by default, which is **100 times smaller** than the project scale. Find the right setting (for example `realScale`) or scale the result afterwards. **Verify the scale by measuring:** a 1×1 brick must be 0.8 BU wide.
- **Nitro.blend** is already at the project scale. All its parts hang from a root Empty with scale 0.1.

## 2. The Three Sources

### 2.1 "Edificio LEGO" (procedural buildings)

**File:** `~/blender/buildings/Edificios_GN_marquesina_v2.blend`. It contains:

- **Node group "Edificio LEGO"**, with its subgroups `LB Emitir`, `LB Celdas`, `LB Tramo`, `LB Ventanas`, `LB Esquinas`, `LB Relleno`, `LB Colocar` and `LB Piso`.
- **Collection "Piezas LDraw":** hidden objects `LD_<part>` with the part meshes. The generator needs them, so never delete or modify them.
- **Materials:** the palette `LEGO <id> <name>` (82 Mecabricks colors, with fake users), plus `LEGO Vidrio encendido` and `LEGO 26 Black pendiente`.
- **Example objects:** three example buildings in collection "Edificios" (`Hotel`, `Tienda`, `Casa`), plus `Suelo`, `Camara`, `Sol` and the world `Cielo`.

**Modifier inputs** (exact Spanish names):

| Input | Type / range | Meaning |
|---|---|---|
| `Pisos` | int, 1–100 | Total floors, including the ground floor. |
| `Ancho (studs)` | int, 8–96 | Footprint along local X. |
| `Fondo (studs)` | int, 8–96 | Footprint along local Y. |
| `Planta baja` | menu | `Entrada hotel` (double door if `Ancho ≥ 14`, plus a black canopy with finials), `Puerta simple`, `Escaparates` or `Sin puerta`. |
| `Remate` | menu | `Alero con pináculos` (Nitro style), `Cornisa plana` or `Azotea`. |
| Variación › `Semilla` | int | Seed for blind window columns, flower boxes and lit windows. |
| Variación › `Ventanas ciegas` | factor 0–1 | Probability that a window column is bricked up. |
| Variación › `Jardineras` | factor 0–1 | Probability of a flower box under each window. |
| Variación › `Luces encendidas` | factor 0–1 | Probability that a window uses the lit-glass material. |
| Marquesina › `Ancho marquesina (studs)` | int, 8–40 | Hotel canopy width. Only applies with `Entrada hotel`. |
| Marquesina › `Vuelo marquesina (studs)` | int, 3–12 | How far the hotel canopy projects. |
| Marquesina › `Altura marquesina (placas)` | int, −3–6 | Vertical offset of the canopy. |
| Marquesina › `Pináculos superiores` | int, 0–12 | Number of top finials on the canopy. |
| Marquesina › `Separación pináculos (studs)` | int, 0–12 | Spacing of the top finials. |
| Colores › `Pared`, `Marcos`, `Vidrio`, `Vidrio encendido`, `Molduras`, `Tejado`, `Azotea`, `Detalles`, `Puerta`, `Plantas`, `Flores`, `Pendientes marquesina` | material | Material for each role. |
| `Realizar instancias` | bool | **Keep it False.** |

**Geometry facts:**

- **Origin:** at the center of the footprint, at ground level (z = 0).
- **Front facade:** faces **local −Y**. That is where the door, the canopy and the shop windows go. The other facades have windows on every side, so generated buildings look finished from any direction.
- **Envelope:** the `Alero con pináculos` and `Cornisa plana` roofs and the flower boxes project 1 stud on every side, and a hotel canopy projects `Vuelo marquesina` studs in front. So the envelope is the footprint grown by 1 stud on every side, plus `max(1, Vuelo marquesina)` studs at the front for hotels.

**Blender 5.2 API pitfalls (verified in this project):**

- **Setting modifier inputs:** `mod["Socket_N"]` does not work. Use `getattr(mod.properties.inputs, identifier).value = v`, and get the identifier from `node_group.interface.items_tree` by name. Menu inputs take the item name as a string. Material inputs take a `bpy.types.Material`.
- **Re-evaluation:** after changing inputs, call `ob.update_tag()` and then `bpy.context.view_layer.update()`, or the depsgraph returns stale results.
- **World nodes:** `World.use_nodes` is deprecated. New worlds already have a node tree.

### 2.2 The official modular buildings (LDraw OMR)

**Location:** `~/blender/buildings/descargas/omr/<set>_<name>/<set>.mpd`. There is one folder per set; provenance and licenses are in `LEEME.md`.

| Set | Name | Footprint from its baseplates (verify) |
|---|---|---|
| 10182-1 | Café Corner | 2 × 16×32 → 32×32 |
| 10185-1 | Green Grocer | 2 × 16×32 → 32×32 |
| 10190-1 | Market Street | 2 × 16×32 → 32×32 |
| 10197-1 | Fire Brigade | 2 × 16×32 → 32×32 |
| 10218-1 | Pet Shop | 2 × 16×32 → 32×32 |
| 10224-1 | Town Hall | 32×32 |
| 10232-1 | Palace Cinema | 32×32 |
| 10243-1 | Parisian Restaurant | 32×32 |
| 10246-1 | Detective's Office | 32×32 |
| 10251-1 | Brick Bank | 32×32 |
| 10264-1 | Corner Garage | 32×32 |
| 10270-1 | Bookshop | only one 16×32 baseplate found: check whether it is 16×32 or 32×32 |
| 10278-1 | Police Station | 32×32 |
| 10297-1 | Boutique Hotel | 32×32 |

- **Excluded:** 10230-1 Mini Modulars is a micro-scale model. **Do not use it.**
- **Size:** each model has 1,400–3,400 parts and includes interiors, furniture and minifigures. **Keep all of it**, minifigures included, as the official set.
- **Materials:** **keep the materials created by ImportLDraw**. Do not remap them to the Mecabricks palette. The resulting difference in look is accepted.
- **Licenses:** CCAL 2.0, except 10232 (CC BY 4.0). Credit the model authors listed in `LEEME.md` in the deliverables.

### 2.3 Nitrody City

**File:** `~/blender/buildings/Nitro.blend`, which is read-only. It contains:

- **Collection "Nitrody City! IV":** 10,463 parts named `part`, `part.001`, … and the root Empty `Empty` (scale 0.1). These parts carry Mecabricks `mb:*` materials.
- **Collection "Collection":** a camera, a cube and a light. **Do not bring these into the city.**
- **Extents:** the part origins span about x ∈ [−14.2, 26.8] BU and y ∈ [−9.2, 44.6] BU, which is roughly **52 × 68 studs**. The tallest point is about 55.8 BU, at the top of the hotel tower. Measure the real bounding box from the meshes.
- **Hotel entrance:** the "HOTEL" sign and entrance canopy are on the tower's **−X face**.

## 3. Inspect Before Building

1. **Generator:** open `Edificios_GN_marquesina_v2.blend` headless. Print every "Edificio LEGO" input (name, identifier, type, default, min/max, panel) and every menu item.
2. **Modulars:** for each modular, record:
   - the main model, which is the first `0 FILE` in the `.mpd`;
   - the baseplate footprint;
   - which side is the **street front**: the sidewalk tiles and the main entrance;
   - whether it is a **corner building**, with finished facades on two adjacent sides, or a **middle building**, with plain side walls meant to touch its neighbors;
   - its height in BU after scaling.

   To do this, import each modular into a test file and render a small contact sheet from four sides, plus one from above. **Look at the images.**
3. **Nitro:** measure Nitrody City's real footprint and height. Decide which rotation makes its "HOTEL" entrance face a street.
4. **Summary:** before implementing the city, summarize what you found (a table of the 14 modulars with footprint, front direction, corner or middle, and height) and the layout you plan.

## 4. City Layout

All dimensions below are in studs. Keep them as named constants in the script.

### Grid

- **Blocks:** 3 × 3. Rows A, B, C run from south (−Y) to north (+Y); columns 1, 2, 3 run from west (−X) to east (+X).
- **Block size:** each block is **96 studs wide (X) × 64 deep (Y)**. It holds **two back-to-back rows of three 32×32 lots**. The south row's lots face the street to the south, and the north row's lots face the street to the north.
- **Lot types:** in each row, the two end lots are **corner lots**; they also face the side street. The center lot is a **middle lot**.
- **Streets:** **32 studs** wide (the size of a standard LEGO road baseplate), between blocks and as a ring road around the neighborhood.
- **Total size:** 3·96 + 4·32 = 416 studs (332.8 BU) by 3·64 + 4·32 = 320 studs (256 BU), centered on the world origin.
- **Stud grid:** every lot, building and model must lie on the stud grid. Rotate only around Z, in multiples of 90°.

### Central block B2: Nitrody City

- **Placement:** place Nitrody City in block B2, choosing the rotation that puts the "HOTEL" entrance facing a street. A rotation of +90° turns the −X face toward −Y (south); verify this. With that rotation it should fit the 96 × 64 block.
- **Enlarging B2:** if it does not fit, enlarge the B row and/or the column-2 width just enough, rounding up to a multiple of 8 studs. Keep all streets straight. In the other blocks of that row or column, the extra space becomes a courtyard behind the lots.
- **Leftover space:** fill whatever remains of B2 with generated buildings, if the strip is at least 10 studs wide, or leave it as a plain plaza pad.
- **Must not be exceeded:** Nitrody City's hotel tower is the landmark. **No generated building may be taller than it.** In practice that means `Pisos ≤ 8`. Check it with measured heights.

### Placing the modulars

- Use **each of the 14 modulars exactly once.**
- **Where:** put them preferably on lots that face the **four streets surrounding B2**, so that the city center reads as a LEGO Creator modular district around Nitrody City.
- **Middle modulars** go on **middle lots** or side by side within a row, so that their plain side walls touch each other or a generated building.
- **Corner modulars** go on **corner lots**, turned so that both finished facades face the two streets.
- **Fronts:** the street front, meaning the sidewalk side, must face the lot's street. The sidewalk edge must line up with the lot's street edge.
- **A 16×32 modular** (possibly Bookshop) shares its lot with a generated building no wider than 16 studs including its envelope.
- **Ground level:** the **top surface of each modular's baseplate is at z = 0**.

### Generated buildings

- Generated buildings fill **every remaining lot**, with one or two buildings per lot.
- **Envelopes inside lots:** every envelope (section 2.1) must lie inside its lot.
- **Shared facade line:** measure the modulars' sidewalk depth, meaning the distance from the baseplate's street edge to the building facade. Set generated buildings back by the same distance so that every row has a continuous facade line.
- **Hotel canopies** project into that setback, still inside the lot.
- **Fronts:** generated buildings face the lot's street. On corner lots they may face either street.
- **Ground:** give every generated lot a flat 32×32 pad in `LEGO 194 Light Bluish Grey`, top at z = 0, so that its setback reads as sidewalk.
- **Building mix**, guided by archetypes; vary within the ranges and keep `Pisos ≤ 8`:

| Archetype | Pisos | Ancho × Fondo | Planta baja | Remate |
|---|---|---|---|---|
| Apartment building | 4–8 | 14–30 × 14–24 | `Puerta simple` | `Cornisa plana` or `Alero con pináculos` |
| Shop with flats above | 3–5 | 12–28 × 12–22 | `Escaparates` | `Cornisa plana` |
| Narrow townhouse (two per lot) | 2–4 | 8–14 × 12–20 | `Puerta simple` | `Azotea` or `Cornisa plana` |
| Small hotel | 5–8 | 16–30 × 14–24 | `Entrada hotel` | `Alero con pináculos` |
| Office block | 5–8 | 20–30 × 16–24 | `Escaparates` | `Azotea` or `Cornisa plana` |

  Use at most 3 small hotels.
- **Color schemes:** use `Pared` / `Molduras` / `Tejado` combinations from the `LEGO <id> <name>` palette. For example:
  - `LEGO 1 White` / `LEGO 1 White` / `LEGO 26 Black`
  - `LEGO 5 Tan` / `LEGO 138 Dark Tan` / `LEGO 138 Dark Tan`
  - `LEGO 154 Dark Red` / `LEGO 5 Tan` / `LEGO 199 Dark Bluish Grey`
  - `LEGO 192 Reddish Brown` / `LEGO 194 Light Bluish Grey` / `LEGO 26 Black`
  - `LEGO 151 Sand Green` / `LEGO 1 White` / `LEGO 199 Dark Bluish Grey`
  - `LEGO 135 Sand Blue` / `LEGO 1 White` / `LEGO 140 Dark Blue`
  - `LEGO 283 Light Nougat` / `LEGO 312 Medium Nougat` / `LEGO 192 Reddish Brown`
  - `LEGO 330 Olive Green` / `LEGO 5 Tan` / `LEGO 26 Black`
  - `LEGO 194 Light Bluish Grey` / `LEGO 199 Dark Bluish Grey` / `LEGO 199 Dark Bluish Grey`

  Verify that every name exists.
- **Color rules:** no two neighboring generated buildings share a `Pared` material. Glass stays `LEGO 375 Trans Smoke`. `Luces encendidas` is 0 (daytime).
- **Seeds:** each building gets a unique `Semilla`, derived from one master seed. No two buildings may have identical parameter sets.

## 5. Scene Assembly and Performance

- **Base file:** open `Edificios_GN_marquesina_v2.blend` (it holds the generator, its parts and the palette). Delete the example buildings `Hotel`, `Tienda` and `Casa` **in the new file only**, and save as a new file.
- **Modular library:** import all 14 modulars **once**, in a separate script, into a new library file `~/blender/buildings/Modulares_OMR.blend`.
  - Put each modular in its own collection, named `MOD_<set>_<name>`.
  - Use ImportLDraw with `ldrawPath="/home/kheiron/ldraw"`, `linkParts=True` (shared meshes), `addEnvironment=False`, `importCameras=False`, `positionCamera=False` and `useLogoStuds=False`. Keep the importer's material settings.
  - Delete any `LegoGroundPlane` that appears.
  - Fix the scale (section 1).
  - Normalize each collection so that its origin is at the **center of its baseplate footprint, with the baseplate top at z = 0, and the street front facing −Y**. This makes placing a modular identical to placing a generated building.
- **Linking into the city:**
  - **Link** (do not append) each `MOD_*` collection from `Modulares_OMR.blend`, and the "Nitrody City! IV" collection from `Nitro.blend`.
  - Use **relative paths**.
  - Place each one with a **collection-instance Empty**. Imported parts are never duplicated as real objects in the city file.
  - Verify that the linked instances render.
- **Nitro's materials:** Nitrody City keeps its Mecabricks `mb:*` materials.
- **Collections:** create `Ciudad`, with one child collection per block (`Manzana_A1` … `Manzana_C3`).
- **Naming:** use `<block>_<lot>_<source>_<name>`, for example `A2_N2_MOD_10243_ParisianRestaurant`, `A1_S1_GEN_Apartamentos` or `B2_NITRO`. Store the block, the lot, the source and the archetype as custom properties.
- **Ground:**
  - Streets are a plain plane in `LEGO 199 Dark Bluish Grey`, slightly below z = 0 (for example −0.02) to avoid z-fighting.
  - Generated lots have pads (section 4).
  - Modulars and Nitro bring their own baseplates and ground plates.
  - No road markings.
- **Lighting:** reuse `Sol` and `Cielo`, and keep the sun angled so that facades are clearly modelled.
- **Cameras** (add the named ones as separate objects):
  - `Camara`: aerial three-quarter overview of the whole city. This is the scene camera.
  - `Cam_Planta`: top-down orthographic plan.
  - `Cam_Centro`: Nitrody City and the modular district around it.
  - `Cam_Calle_1`, `Cam_Calle_2`, `Cam_Calle_3`: street-level views at about 1.8 BU eye height. One must run along a row of modulars.
  - `Cam_Mezcla`: a close-up where a modular, a generated building and Nitrody City can be compared.
- **Render settings:** EEVEE, AgX, 1920 × 1080.
- **Budget:** buildings stay as instances, with `Realizar instancias = False`. Report the object count, the instance count, the evaluation time and the time to render one frame.

## 6. Implementation Requirements

1. **Two scripts:**
   - `~/blender/buildings/scripts/importar_modulares.py` builds `Modulares_OMR.blend`.
   - `~/blender/buildings/scripts/ciudad_completa.py` builds `~/blender/buildings/Ciudad_completa.blend`. Run it as `~/.local/bin/blender -b ~/blender/buildings/Edificios_GN_marquesina_v2.blend -P ~/blender/buildings/scripts/ciudad_completa.py`.
2. **Layout as data:** keep the whole layout in one data structure at the top of the city script: per lot, its block, lot, source, model or archetype, location, rotation and every generator input. Export it to `~/blender/buildings/ciudad_completa_layout.json`.
3. **Determinism:** the same master seed must produce the same city. Use `random.Random(seed)`, never global randomness.
4. **Safe re-runs:** running either script again must give the same output, without duplicated objects, collections, materials or library links.
5. **Fail loudly:** fail with a clear message if a file, collection, generator input, menu item or material is missing.
6. **Do not change the sources:** do not modify the generator, the `LD_*` parts, the `.mpd` files or `Nitro.blend`. If a goal needs something the sources cannot do, report it as a limitation.
7. **Code style:** follow the style of the project's existing scripts: compact Python, short comments, Spanish names for scene objects.

## 7. Validation

Validate the actual Blender result, not just that the scripts run without errors.

### Structural checks

Print a report covering all of the following:

- **Inventory:** each of the 14 modulars appears exactly once, Nitrody City appears once, Mini Modulars is absent, and every lot is filled.
- **Scale:**
  - a 1×1 brick measures 0.8 BU in the modular library;
  - baseplates measure 25.6 BU (or 12.8 BU for 16-stud ones);
  - Nitro's studs line up with the stud grid.
- **Ground level:** the baseplate tops of the modulars, Nitro's ground plates and the generated pads all sit at z = 0, within ±0.05 BU.
- **No overlaps:**
  - For collection instances, use the bounding boxes of the instanced collection's objects transformed by the instance Empty.
  - For generated buildings, iterate `depsgraph.object_instances` with `inst.is_instance and inst.parent.original == building`, applying `inst.matrix_world` to the bounding box of `inst.object.data`.
  - No two models' XY boxes overlap (tolerance 0.01 BU), and every model stays inside its lot or block.
- **Orientation:** every street front faces its lot's street, corner modulars sit on corner lots, and generated facades line up with the modulars' facade line.
- **Heights:** no generated building is taller than Nitrody City's hotel tower.
- **Generator:** every modifier has empty `mod.node_warnings` and more than 0 instances.
- **Variety:** the color-adjacency rule holds, seeds are unique and parameter sets are unique.
- **Reopen test:** open `Ciudad_completa.blend` in a fresh Blender process. Confirm that the linked libraries resolve, then re-evaluate and confirm that the counts match.

### Visual checks

- Render all seven cameras with EEVEE into `~/blender/buildings/renders/ciudad_completa/`.
- **Open and inspect every image.** Check for:
  - mismatched scales or floating models;
  - z-fighting at ground level;
  - models facing the wrong way;
  - blank side walls exposed where they should not be;
  - collisions;
  - repetition;
  - a weak skyline.
- Fix problems and render again. Repeat until the result meets the acceptance criteria.
- **Do not claim visual validation unless you actually looked at the rendered images.**

## 8. Acceptance Criteria

The task is complete only when all of the following hold:

- `Ciudad_completa.blend` contains a 3 × 3 block city with:
  - Nitrody City in block B2, with its "HOTEL" entrance facing a street;
  - all 14 modulars, each exactly once, lining the streets around B2;
  - generated buildings filling every remaining lot.
- All three sources share one scale, one ground level and the stud grid.
- There are no overlaps, everything respects its lot, and every front faces its street.
- Corner and middle modulars are used correctly.
- The modulars keep their interiors, minifigures and ImportLDraw materials. Generated buildings keep the Mecabricks palette. Nitro keeps its original materials.
- No generated building is taller than the Nitro hotel tower. There are no Geometry Nodes warnings, and the generated buildings remain instances.
- The heavy assets are linked from their source files and placed as collection instances.
- Both scripts are deterministic and safe to re-run, the reopen test passes, and no source file was modified.

## 9. Deliverables

1. `~/blender/buildings/Modulares_OMR.blend` and `~/blender/buildings/Ciudad_completa.blend`, both new files.
2. `~/blender/buildings/scripts/importar_modulares.py` and `~/blender/buildings/scripts/ciudad_completa.py`.
3. `~/blender/buildings/ciudad_completa_layout.json`.
4. The seven renders in `~/blender/buildings/renders/ciudad_completa/`, plus the modular contact sheets from step 2 of section 3.
5. A lot table listing block, lot, source, model or archetype, location, rotation and the main generator inputs.
6. The validation report from section 7.
7. **Credits:**
   - a section in `~/blender/buildings/scripts/README.md` explaining how to regenerate the library and the city, change the layout or master seed, and swap a modular;
   - a text datablock `Creditos` inside `Ciudad_completa.blend` listing every modular with its LDraw author and license (from `LEEME.md`), and crediting Nitrody City as a Mecabricks model.
8. A list of remaining limitations or deviations from this brief.

## 10. Out of Scope

Do not add any of the following:

- road baseplates, road markings or crossings;
- street furniture, trees or vehicles beyond what the modulars already include;
- the project's rigged minifigures;
- animation.

Keep streets as plain ground, with the dimensions as named constants, so that road baseplates can be added later.

## Execution Instructions

- Start with section 3 (inspection and contact sheets), then build the modular library, then the city. After that, validate, iterate and save.
- **Importing the modulars is the slowest step.** Run it once, cache the result in `Modulares_OMR.blend`, and run long Blender jobs in the background with a log file.
- You have full access to the project, the shell and Blender. Run everything yourself, and do not hand steps back to the user.
- Do not stop after producing a plan or example code: carry the work through to the saved files, the renders and the report.
- **If a critical blocker prevents completion,** describe exactly what you verified, what failed (with the error text), and the minimum information needed to continue.
