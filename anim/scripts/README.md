# Rig de minifiguras LEGO (Mecabricks → Blender)

`rig_minifigs.py` crea un rig de animación para cada minifigura de un `.blend` importado de Mecabricks. Toma las piezas sueltas (`part`, `part.001`, …), las coloca en una pose neutra y las emparenta a huesos con controles. La pose que traían de Mecabricks se aplica al terminar y se guarda como asset de la Pose Library.

## Uso

```bash
blender -b ~/blender/anim/Minifigures.blend -P ~/blender/anim/scripts/rig_minifigs.py
```

- Lee el `.blend` original y guarda el resultado en la ruta `OUT` del principio del script (por defecto `~/blender/anim/Minifigures_rig.blend`). **El original no se modifica.** Si lo ejecutas otra vez, sobrescribe `OUT`.
- Al terminar imprime una línea `INFORME` por figura. Ahí aparece la orientación que se tomó para la cabeza y cualquier pieza que se tuvo que reencajar en su articulación, por ejemplo `brazo.L desplazado 0.72 mm`.
- Necesita Blender 5.x (probado con 5.2.2).

## Riggear otras figuras: el diccionario `FIGS`

Cada entrada de `FIGS` es una figura. Su nombre se usa en el rig (`RIG_<nombre>`), en la colección y en las piezas (`<nombre>_torso`, …). Los números son los índices de pieza: `4` significa `part.004` y `0` significa `part`.

```python
"Barbudo": dict(torso=4, cadera=13, brazo_R=0, brazo_L=2, mano_R=1, mano_L=3,
                pierna_R=14, pierna_L=15, cabeza=31,
                pelo=[44], bandolera=[51], adorno=[60, 61, 62]),
```

| Clave | Obligatoria | Va unida a |
|---|---|---|
| `torso`, `cadera`, `cabeza` | sí | — |
| `brazo_R/L`, `mano_R/L`, `pierna_R/L` | sí | — |
| `pelo`, `tocado` | no (lista) | cabeza |
| `bandolera`, `adorno` | no (lista) | torso |
| `faldon` | no (lista) | piezas textiles (`txt…`). Se deforman con las piernas |

`_R` y `_L` son la derecha y la izquierda **de la figura**, no las del espectador. Si las piernas están al revés, el script se detiene con `lado pierna`. En ese caso intercambia `pierna_R` y `pierna_L`.

### Cómo encontrar los índices

El orden de las piezas en Blender es el mismo que en el `.zmbx` exportado de Mecabricks. Este comando lista cada pieza con su ID LEGO y su posición en Blender:

```bash
python3 -I - "mi_modelo.zmbx" <<'EOF'
import json, sys, zipfile
d = json.loads(zipfile.ZipFile(sys.argv[1]).read("scene.mbx"))
for i, p in enumerate(d["parts"]):
    m = p["matrix"]
    name = "part" if i == 0 else f"part.{i:03d}"
    print(f"{name:9s} {p['configuration']:14s} x={m[3]/10:7.3f} y={-m[11]/10:7.3f} z={m[7]/10:6.3f}")
EOF
```

Las piezas de una misma figura comparten aproximadamente la misma `x, y`. IDs habituales:

| ID (o variante) | Pieza |
|---|---|
| `3814`, `3814uv…` | torso |
| `3815`, `3815uv…` | cadera |
| `3816…` / `3817…` | pierna derecha / izquierda |
| `20926` / `20932` | piernas alternativas (el lado se ve por la posición) |
| `3818v2` / `3819v2` | brazo derecho / izquierdo |
| `16000` / `16001` | brazos alternativos |
| `3820v2` | mano (cada una va con el brazo más cercano) |
| `3626v2` | cabeza |
| `txt…uv.json` | pieza textil (faldón, capa) |

## Qué contiene el rig

| Hueso | Movimiento LEGO real | Extras (con límite) |
|---|---|---|
| `raiz` | mover o girar la figura (círculo con flecha en el suelo) | — |
| `cuerpo` | botes, saltos e inclinación (caja en la cadera) | — |
| `torso` | — | cintura: giro ±60°, flexión ±30°, lado ±20° |
| `cabeza` | girar en el cuello (Y) | asentir ±35°, inclinar ±25° |
| `brazo.L/R` | girar en el hombro (X) | abrir hasta 85° hacia fuera |
| `mano.L/R` | girar en la muñeca (Y) | — |
| `pierna.L/R` | girar en la cadera (X) | separar ±30°, girar el pie ±45° |
| `agarre.L/R` | socket en el centro del hueco de la mano | — |
| `pelo`, `tocado`, `bandolera`, `adorno`, `faldon` | controles de accesorios | — |

- **Pose neutra:** todos los giros a 0 dejan la figura de pie, con los brazos colgando. Se vuelve a ella con Alt+R en modo pose.
- **Pose original:** se guarda como asset `Pose original <figura>` en la Pose Library.
- **Objetos en la mano:** añade al objeto una restricción **Child Of** con objetivo `RIG_<figura>` y hueso `agarre.L/R`. El eje Y del hueso sigue la barra del agarre (3,2 mm).
- **Colecciones de huesos:** Principal, Torso_Cabeza, Brazos, Piernas, Accesorios y Agarres. Colores: .L en azul, .R en rojo, centro en amarillo, accesorios en verde y agarres en morado.
- **Faldones:** se doblan con un modificador Armature. Los grupos de vértices `faldon`, `pierna.L` y `pierna.R` se reparten según la altura y el lado de cada vértice.

## Limitaciones

- Funciona con las piezas estándar de minifigura. Los puntos de articulación (hombro, muñeca, cadera, cuello) están fijados en el script con las medidas de Mecabricks. Un torso o unos brazos no estándar pueden no encajar.
- **Cabezas:** Mecabricks imprime la cara con un giro distinto en cada cabeza. Por eso la pose neutra mantiene la dirección en que ya miraba cada cabeza y solo le quita la inclinación.
- **Piezas desencajadas:** las que en Mecabricks estaban fuera de su articulación se reencajan en ella. La pose original las muestra encajadas, y el `INFORME` las lista.
