# Personajes de comic dibujados con Grease Pencil y su rig.
# Cada personaje tiene DOS vistas en el mismo objeto (grupos de capas "frente" y "perfil", perfil mirando a +X);
# la animacion cambia de vista con la opacidad de las capas. Cada parte del cuerpo es una capa emparentada a un
# hueso (rig de recortes): las capas siguen al hueso sin pesos. Bocas (3 formas) y ojos (abiertos/cerrados) son
# capas aparte para la sincronia labial y los parpadeos.
#
# Convenciones: pies en z=0, centro en x=0, plano XZ (frente hacia -Y). Huesos con roll alineado a -Y: rotar en
# Z local gira la parte en el plano de la pantalla (positivo = antihorario visto desde camara).
import json, math
import bpy
from mathutils import Vector
from gp_base import (Lapiz, nuevo_gp, P, circulo, elipse, rect, rect_redondeado, poligono, estrella, capsula,
                     bezier, arco, nube, suave, temblor_linea, brillo, CFG)
import comic_parametros as CP

RI = 0.016        # tinta de los personajes (mas fina que la escenografia)
RD = 0.010        # detalles de la cara

# ---------------------------------------------------------------- esqueleto
# (hueso, cabeza (x, z), cola (x, z), padre)
HUESOS = [
    ("raiz", (0, 0), (0, 0.25), None),
    ("cadera", (0, 0.72), (0, 0.95), "raiz"),
    ("torso", (0, 0.95), (0, 1.22), "cadera"),
    ("cabeza", (0, 1.22), (0, 1.85), "torso"),
    ("ojos", (0, 1.56), (0, 1.66), "cabeza"),
    ("brazo_sup.R", (-0.25, 1.17), (-0.31, 0.93), "torso"), ("brazo_inf.R", (-0.31, 0.93), (-0.33, 0.70), "brazo_sup.R"),
    ("brazo_sup.L", (0.25, 1.17), (0.31, 0.93), "torso"), ("brazo_inf.L", (0.31, 0.93), (0.33, 0.70), "brazo_sup.L"),
    ("pierna_sup.R", (-0.11, 0.72), (-0.11, 0.40), "cadera"), ("pierna_inf.R", (-0.11, 0.40), (-0.11, 0.08), "pierna_sup.R"),
    ("pierna_sup.L", (0.11, 0.72), (0.11, 0.40), "cadera"), ("pierna_inf.L", (0.11, 0.40), (0.11, 0.08), "pierna_sup.L"),
    ("p_brazo_sup.del", (0.0, 1.17), (0.0, 0.93), "torso"), ("p_brazo_inf.del", (0.0, 0.93), (0.02, 0.70), "p_brazo_sup.del"),
    ("p_brazo_sup.tras", (-0.02, 1.17), (-0.02, 0.93), "torso"), ("p_brazo_inf.tras", (-0.02, 0.93), (0.0, 0.70), "p_brazo_sup.tras"),
    ("p_pierna_sup.del", (0.02, 0.72), (0.02, 0.40), "cadera"), ("p_pierna_inf.del", (0.02, 0.40), (0.02, 0.08), "p_pierna_sup.del"),
    ("p_pierna_sup.tras", (-0.03, 0.72), (-0.03, 0.40), "cadera"), ("p_pierna_inf.tras", (-0.03, 0.40), (-0.03, 0.08), "p_pierna_sup.tras"),
    ("cola", (-0.12, 0.72), (-0.42, 0.85), "cadera"),
]
H = {h[0]: h for h in HUESOS}

# ---------------------------------------------------------------- piezas de dibujo
def pierna(lp, h_sup, h_inf, c_pant, c_zap, perfil, piel=None):
    (x0, z0), (x1, z1) = H[h_sup][1], H[h_sup][2]
    lp[0].forma(capsula(x0, z0, x1, z1, 0.085, 0.075), f"Relleno {c_pant}", radio=RI)
    (x0, z0), (x1, z1) = H[h_inf][1], H[h_inf][2]
    lp[1].forma(capsula(x0, z0, x1, z1 + 0.02, 0.075, 0.065), f"Relleno {c_pant}", radio=RI)
    if perfil: lp[1].forma(suave([(x1 - 0.08, 0.0), (x1 + 0.2, 0.0), (x1 + 0.2, 0.07), (x1 + 0.05, 0.13), (x1 - 0.08, 0.11)], 4), f"Relleno {c_zap}", radio=RI)
    else: lp[1].forma(elipse(x1 + (0.02 if x1 > 0 else -0.02), 0.055, 0.11, 0.065, 20), f"Relleno {c_zap}", radio=RI)

def brazo(lp, h_sup, h_inf, c_manga, c_piel, robot=False):
    (x0, z0), (x1, z1) = H[h_sup][1], H[h_sup][2]
    lp[0].forma(capsula(x0, z0, x1, z1, 0.075, 0.062), f"Relleno {c_manga}", radio=RI)
    (x0, z0), (x1, z1) = H[h_inf][1], H[h_inf][2]
    lp[1].forma(capsula(x0, z0, x1, z1, 0.058, 0.05), f"Relleno {c_piel if not robot else 'gris'}", radio=RI)
    if robot:
        lp[1].forma(suave([(x1 - 0.07, z1 - 0.02), (x1 - 0.05, z1 - 0.13), (x1, z1 - 0.07), (x1 + 0.05, z1 - 0.13), (x1 + 0.07, z1 - 0.02), (x1, z1 + 0.04)], 3), f"Relleno {c_piel}", radio=RI)
    else:
        lp[1].forma(circulo(x1, z1 - 0.045, 0.072, 18), f"Relleno {c_piel}", radio=RI)

def torso_frente(lp, c, robot=False):
    if robot:
        lp.forma(rect_redondeado(-0.24, 0.66, 0.24, 1.24, 0.06), f"Relleno {c}", radio=RI)
        lp.forma(rect_redondeado(-0.13, 0.82, 0.13, 1.08, 0.03), "Relleno gris_oscuro", radio=RD)
        for k, cc in enumerate(["rojo", "amarillo", "verde"]): lp.forma(circulo(-0.07 + k * 0.07, 0.95, 0.025, 10), f"Relleno {cc}", radio=RD)
        return
    lp.forma(suave([(-0.2, 0.68), (0.2, 0.68), (0.23, 0.95), (0.27, 1.17), (0.18, 1.25), (0, 1.27), (-0.18, 1.25), (-0.27, 1.17), (-0.23, 0.95)], 5), f"Relleno {c}", radio=RI)
    if CFG["semitono"]: lp.forma(suave([(0.08, 0.70), (0.2, 0.69), (0.23, 0.95), (0.25, 1.12), (0.14, 1.0)], 4), f"Semitono plano {c}", linea=False)
    lp.forma(poligono([(-0.08, 1.26), (0.08, 1.26), (0, 1.16)]), "Relleno blanco", radio=RD)

def torso_perfil(lp, c, robot=False):
    if robot:
        lp.forma(rect_redondeado(-0.15, 0.66, 0.17, 1.24, 0.05), f"Relleno {c}", radio=RI)
        lp.forma(rect(0.17, 0.85, 0.2, 1.05), "Relleno gris_oscuro", radio=RD)
        return
    lp.forma(suave([(-0.13, 0.68), (0.15, 0.68), (0.17, 0.95), (0.18, 1.15), (0.08, 1.27), (-0.08, 1.26), (-0.15, 1.12), (-0.15, 0.9)], 5), f"Relleno {c}", radio=RI)
    if CFG["semitono"]: lp.forma(suave([(-0.13, 0.70), (0.0, 0.69), (-0.02, 1.0), (-0.12, 1.1)], 4), f"Semitono plano {c}", linea=False)

def pelvis(lp, c, perfil):
    if perfil: lp.forma(rect_redondeado(-0.14, 0.6, 0.15, 0.8, 0.06), f"Relleno {c}", radio=RI)
    else: lp.forma(rect_redondeado(-0.21, 0.6, 0.21, 0.8, 0.07), f"Relleno {c}", radio=RI)

def cabeza_frente(lp, p):
    t, piel = p["tipo"], p["piel"]
    cz = 1.52
    if t == "robot":
        lp.forma(rect(-0.04, 1.2, 0.04, 1.3), "Relleno gris", radio=RD)
        lp.forma(rect_redondeado(-0.3, 1.27, 0.3, 1.8, 0.07), f"Relleno {piel}", radio=RI)
        lp.linea([P(0, 1.8), P(0, 1.95)], radio=0.018); lp.forma(circulo(0, 1.97, 0.045, 12), "Relleno rojo", radio=RD)
        for s in (-1, 1): lp.forma(rect(min(0.3 * s, 0.34 * s), 1.45, max(0.3 * s, 0.34 * s), 1.62), f"Relleno {piel}-", radio=RD)
        return
    lp.forma(rect(-0.06, 1.18, 0.06, 1.3), f"Relleno {piel}", radio=RI)
    if t in ("humano", "monstruo"):
        for s in (-1, 1): lp.forma(elipse(0.29 * s, 1.5, 0.06, 0.08, 14), f"Relleno {piel}", radio=RI)
    if t == "gato":
        for s in (-1, 1): lp.forma(poligono([(0.12 * s, 1.75), (0.3 * s, 1.92), (0.27 * s, 1.62)]), f"Relleno {piel}", radio=RI)
    if t == "monstruo":
        for s in (-1, 1): lp.forma(suave([(0.12 * s, 1.74), (0.22 * s, 1.97), (0.2 * s, 1.72)], 4), "Relleno blanco", radio=RI)
    lp.forma(suave([(0, 1.22), (0.2, 1.26), (0.3, 1.42), (0.3, 1.62), (0.2, 1.78), (0, 1.82), (-0.2, 1.78), (-0.3, 1.62), (-0.3, 1.42), (-0.2, 1.26)], 5), f"Relleno {piel}", radio=RI)
    if t == "perro":
        for s in (-1, 1): lp.forma(suave([(0.22 * s, 1.75), (0.36 * s, 1.68), (0.34 * s, 1.42), (0.26 * s, 1.5)], 4), f"Relleno {piel}-", radio=RI)
    if t in ("gato", "perro"):
        lp.forma(elipse(0, 1.4, 0.13, 0.09, 18), f"Relleno {piel}+", radio=RD)
        lp.forma(poligono([(-0.04, 1.47), (0.04, 1.47), (0, 1.43)]), "Relleno negro", radio=RD)
        if t == "gato":
            for s in (-1, 1):
                for dz in (0.0, 0.03): lp.linea([P(0.1 * s, 1.43 + dz), P(0.28 * s, 1.45 + dz * 2)], radio=0.006)

def cara_frente(capas, p):
    t = p["tipo"]; robot = t == "robot"; cic = t == "monstruo"
    ojos, pupilas, cerrados, cejas = capas["F_ojos"], capas["F_pupilas"], capas["F_ojos_cerrados"], capas["F_cejas"]
    xs = [0.0] if cic else [-0.11, 0.11]
    for x in xs:
        if robot:
            ojos.forma(circulo(x, 1.6, 0.07, 18), "Relleno gris_oscuro", radio=RD)
            pupilas.forma(circulo(x, 1.6, 0.045, 14), "Relleno cian", radio=0.004)
            cerrados.forma(rect(x - 0.07, 1.585, x + 0.07, 1.615), "Relleno gris_oscuro", radio=RD)
            continue
        rx, rz = (0.13, 0.13) if cic else (0.075, 0.095)
        ojos.forma(elipse(x, 1.57, rx, rz, 20), "Relleno blanco", radio=RD)
        pupilas.forma(circulo(x + 0.01, 1.565, rx * 0.5, 14), "Relleno negro", radio=0.004)
        pupilas.forma(circulo(x + 0.03, 1.59, rx * 0.17, 8), "Plano blanco", linea=False)
        cerrados.linea(arco(x, 1.6, rx, 200, 340, 8), radio=0.014)
        cejas.linea(arco(x, 1.6, rx * 1.3, 60 if x <= 0 else 50, 130 if x <= 0 else 120, 6), radio=0.014)
    if t in ("humano",): capas["F_mejillas"].forma(suave([(-0.02, 1.49), (0.02, 1.47), (0.0, 1.44)], 3), f"Relleno {p['piel']}-", radio=0.006)
    if not robot:
        for s in (-1, 1): capas["F_mejillas"].forma(elipse(0.19 * s, 1.43, 0.05, 0.03, 12), "Translucido rosa", linea=False)
    bz = 1.37
    if robot:
        capas["F_boca_0"].forma(rect_redondeado(-0.11, bz - 0.03, 0.11, bz + 0.03, 0.02), "Relleno gris_oscuro", radio=RD)
        capas["F_boca_1"].forma(rect_redondeado(-0.11, bz - 0.05, 0.11, bz + 0.05, 0.02), "Relleno cian", radio=RD)
        capas["F_boca_2"].forma(rect_redondeado(-0.12, bz - 0.08, 0.12, bz + 0.07, 0.03), "Relleno cian", radio=RD)
        for c in ("F_boca_1", "F_boca_2"):
            for k in range(-2, 3): capas[c].linea([P(k * 0.04, bz - 0.06), P(k * 0.04, bz + 0.05)], "Trazo gris_oscuro", radio=0.006)
        return
    capas["F_boca_0"].linea(arco(0, bz + 0.07, 0.1, 230, 310, 10), radio=0.014)
    capas["F_boca_1"].forma(suave([(-0.08, bz + 0.01), (0.08, bz + 0.01), (0.05, bz - 0.04), (0, bz - 0.055), (-0.05, bz - 0.04)], 4), "Relleno carmesi--", radio=RD)
    capas["F_boca_2"].forma(suave([(-0.09, bz + 0.03), (0.09, bz + 0.03), (0.07, bz - 0.06), (0, bz - 0.1), (-0.07, bz - 0.06)], 4), "Relleno carmesi--", radio=RD)
    capas["F_boca_2"].forma(elipse(0, bz - 0.06, 0.045, 0.025, 12), "Plano rosa", linea=False)
    if cic:
        for s in (-1, 1): capas["F_boca_0"].forma(poligono([(0.04 * s, bz + 0.0), (0.06 * s, bz - 0.05), (0.08 * s, bz + 0.0)]), "Relleno blanco", radio=0.006)

def pelo_frente(atras, delante, p):
    est, c = p["pelo"], p["color_pelo"]
    if p["tipo"] != "humano" or est == "calvo": return
    if est == "largo":
        atras.forma(suave([(-0.33, 1.75), (-0.36, 1.35), (-0.3, 1.12), (0.3, 1.12), (0.36, 1.35), (0.33, 1.75), (0, 1.86)], 5), f"Relleno {c}", radio=RI)
    if est == "coleta":
        atras.forma(suave([(0.22, 1.72), (0.45, 1.75), (0.5, 1.45), (0.42, 1.25), (0.35, 1.5)], 5), f"Relleno {c}", radio=RI)
        atras.forma(circulo(0.3, 1.72, 0.06, 12), "Relleno magenta", radio=RD)
    if est == "mono":
        atras.forma(circulo(0, 1.9, 0.13, 20), f"Relleno {c}", radio=RI)
    if est == "rizado":
        delante.forma(nube(0, 1.78, 0.78, 0.36, 5, semilla=3), f"Relleno {c}", radio=RI)
        return
    if est == "pincho":
        pts = [(-0.31, 1.6), (-0.36, 1.8), (-0.2, 1.78), (-0.18, 1.98), (-0.04, 1.84), (0.05, 2.02), (0.12, 1.84), (0.26, 1.95), (0.24, 1.76), (0.36, 1.74), (0.31, 1.6), (0.1, 1.68), (-0.1, 1.66)]
        delante.forma(poligono(pts), f"Relleno {c}", radio=RI)
        return
    cap = [(-0.31, 1.52), (-0.3, 1.72), (-0.18, 1.84), (0, 1.88), (0.18, 1.84), (0.3, 1.72), (0.31, 1.52), (0.26, 1.62),
           (0.12, 1.69), (0.05, 1.64), (-0.05, 1.7), (-0.18, 1.66), (-0.26, 1.62)]
    delante.forma(poligono(cap) if est != "largo" else suave(cap, 3), f"Relleno {c}", radio=RI)
    delante.linea(arco(-0.08, 1.7, 0.14, 100, 160, 5), "Tinta blanca", radio=0.01)

def accesorio_frente(capas, p):
    a, c = p["accesorio"], p["color_accesorio"]; L = capas["F_accesorio"]
    if a == "gafas":
        for x in (-0.11, 0.11): L.trazo(circulo(x, 1.57, 0.1, 20), f"Trazo {c}", radio=0.018, cerrado=True)
        L.linea([P(-0.01, 1.59), P(0.01, 1.59)], f"Trazo {c}", radio=0.015)
    elif a == "gorra":
        L.forma(suave([(-0.31, 1.66), (-0.27, 1.82), (0, 1.9), (0.27, 1.82), (0.31, 1.66)], 4), f"Relleno {c}", radio=RI)
        L.forma(elipse(0, 1.66, 0.36, 0.05, 20), f"Relleno {c}-", radio=RI)
    elif a == "sombrero":
        L.forma(rect_redondeado(-0.22, 1.74, 0.22, 2.12, 0.03), f"Relleno {c}", radio=RI)
        L.forma(rect(-0.22, 1.78, 0.22, 1.85), "Relleno rojo", radio=RD)
        L.forma(elipse(0, 1.74, 0.4, 0.05, 20), f"Relleno {c}", radio=RI)
    elif a == "corona":
        L.forma(poligono([(-0.2, 1.76), (0.2, 1.76), (0.24, 1.98), (0.12, 1.86), (0, 2.02), (-0.12, 1.86), (-0.24, 1.98)]), "Relleno oro", radio=RI)
        L.forma(circulo(0, 1.83, 0.035, 10), "Relleno rojo", radio=RD)
    elif a == "pajarita":
        T = capas["F_accesorio_torso"]
        T.forma(poligono([(0, 1.22), (-0.11, 1.28), (-0.11, 1.16)]), f"Relleno {c}", radio=RD)
        T.forma(poligono([(0, 1.22), (0.11, 1.28), (0.11, 1.16)]), f"Relleno {c}", radio=RD)
        T.forma(circulo(0, 1.22, 0.03, 10), f"Relleno {c}-", radio=RD)
    elif a == "mochila":
        for s in (-1, 1): capas["F_accesorio_torso"].forma(rect(0.13 * s - 0.03, 0.85, 0.13 * s + 0.03, 1.24), f"Relleno {c}", radio=RD)
    elif a == "capa":
        capas["F_capa"].forma(poligono([(-0.25, 1.22), (0.25, 1.22), (0.42, 0.25), (0.15, 0.32), (0, 0.22), (-0.15, 0.32), (-0.42, 0.25)]), f"Relleno {c}", radio=RI)

# ---------------------------------------------------------------- perfil (mirando a +X)
def cabeza_perfil(lp, p):
    t, piel = p["tipo"], p["piel"]
    if t == "robot":
        lp.forma(rect(-0.04, 1.2, 0.04, 1.3), "Relleno gris", radio=RD)
        lp.forma(rect_redondeado(-0.25, 1.27, 0.3, 1.8, 0.07), f"Relleno {piel}", radio=RI)
        lp.linea([P(-0.05, 1.8), P(-0.05, 1.95)], radio=0.018); lp.forma(circulo(-0.05, 1.97, 0.045, 12), "Relleno rojo", radio=RD)
        lp.forma(rect(-0.1, 1.45, 0.0, 1.62), f"Relleno {piel}-", radio=RD)
        return
    lp.forma(rect(-0.06, 1.18, 0.06, 1.3), f"Relleno {piel}", radio=RI)
    if t == "gato": lp.forma(poligono([(-0.05, 1.76), (0.05, 1.95), (0.14, 1.74)]), f"Relleno {piel}", radio=RI)
    if t == "monstruo": lp.forma(suave([(-0.02, 1.76), (0.06, 1.98), (0.08, 1.74)], 4), "Relleno blanco", radio=RI)
    hocico = [(0.28, 1.5), (0.38, 1.46), (0.35, 1.38), (0.27, 1.36)] if t in ("gato", "perro") else [(0.29, 1.52), (0.34, 1.47), (0.29, 1.43)]
    lp.forma(suave([(0.02, 1.22), (0.2, 1.27), (0.28, 1.36)] + hocico + [(0.3, 1.62), (0.2, 1.78), (0.02, 1.83), (-0.18, 1.77), (-0.28, 1.6), (-0.28, 1.42), (-0.16, 1.27)], 4), f"Relleno {piel}", radio=RI)
    if t == "humano": lp.forma(elipse(-0.04, 1.5, 0.06, 0.08, 14), f"Relleno {piel}", radio=RI)
    if t == "perro": lp.forma(suave([(-0.02, 1.76), (-0.18, 1.7), (-0.2, 1.42), (-0.06, 1.5)], 4), f"Relleno {piel}-", radio=RI)
    if t in ("gato", "perro"): lp.forma(circulo(0.37, 1.47, 0.03, 10), "Relleno negro", radio=RD)

def cara_perfil(capas, p):
    t = p["tipo"]; robot = t == "robot"; cic = t == "monstruo"
    x, z = (0.15, 1.6) if not cic else (0.12, 1.6)
    if robot:
        capas["P_ojos"].forma(circulo(0.2, 1.6, 0.07, 18), "Relleno gris_oscuro", radio=RD)
        capas["P_pupilas"].forma(circulo(0.21, 1.6, 0.045, 14), "Relleno cian", radio=0.004)
        capas["P_ojos_cerrados"].forma(rect(0.13, 1.585, 0.27, 1.615), "Relleno gris_oscuro", radio=RD)
        capas["P_boca_0"].forma(rect(0.12, 1.34, 0.3, 1.39), "Relleno gris_oscuro", radio=RD)
        capas["P_boca_1"].forma(rect(0.12, 1.32, 0.3, 1.41), "Relleno cian", radio=RD)
        capas["P_boca_2"].forma(rect(0.12, 1.29, 0.3, 1.43), "Relleno cian", radio=RD)
        return
    rx, rz = (0.09, 0.12) if cic else (0.055, 0.09)
    capas["P_ojos"].forma(elipse(x, z, rx, rz, 18), "Relleno blanco", radio=RD)
    capas["P_pupilas"].forma(circulo(x + 0.025, z - 0.005, rx * 0.6, 12), "Relleno negro", radio=0.004)
    capas["P_ojos_cerrados"].linea(arco(x, z + 0.03, rx, 200, 340, 8), radio=0.014)
    capas["P_cejas"].linea(arco(x, z + 0.03, rx * 1.4, 50, 120, 6), radio=0.014)
    if not robot: capas["P_mejillas"].forma(elipse(0.1, 1.43, 0.045, 0.028, 12), "Translucido rosa", linea=False)
    bx, bz = 0.25, 1.37
    capas["P_boca_0"].linea(arco(bx - 0.05, bz + 0.06, 0.07, 270, 330, 6), radio=0.014)
    capas["P_boca_1"].forma(suave([(bx - 0.07, bz + 0.01), (bx + 0.04, bz + 0.02), (bx + 0.02, bz - 0.04), (bx - 0.05, bz - 0.03)], 3), "Relleno carmesi--", radio=RD)
    capas["P_boca_2"].forma(suave([(bx - 0.08, bz + 0.03), (bx + 0.05, bz + 0.04), (bx + 0.03, bz - 0.08), (bx - 0.06, bz - 0.06)], 3), "Relleno carmesi--", radio=RD)

def pelo_perfil(atras, delante, p):
    est, c = p["pelo"], p["color_pelo"]
    if p["tipo"] != "humano" or est == "calvo": return
    if est == "largo": atras.forma(suave([(-0.05, 1.82), (-0.3, 1.7), (-0.36, 1.3), (-0.25, 1.1), (-0.1, 1.3), (0.0, 1.6)], 5), f"Relleno {c}", radio=RI)
    if est == "coleta":
        atras.forma(suave([(-0.22, 1.7), (-0.45, 1.68), (-0.55, 1.4), (-0.48, 1.18), (-0.38, 1.45), (-0.25, 1.55)], 5), f"Relleno {c}", radio=RI)
        atras.forma(circulo(-0.28, 1.65, 0.06, 12), "Relleno magenta", radio=RD)
    if est == "mono": atras.forma(circulo(-0.12, 1.88, 0.13, 20), f"Relleno {c}", radio=RI)
    if est == "rizado": delante.forma(nube(-0.05, 1.74, 0.62, 0.4, 5, semilla=4), f"Relleno {c}", radio=RI); return
    if est == "pincho":
        delante.forma(poligono([(-0.29, 1.55), (-0.45, 1.75), (-0.25, 1.78), (-0.3, 1.98), (-0.1, 1.86), (-0.02, 2.02), (0.08, 1.86), (0.25, 1.9), (0.24, 1.72), (0.05, 1.7), (-0.12, 1.62)]), f"Relleno {c}", radio=RI)
        return
    delante.forma(poligono([(-0.29, 1.45), (-0.28, 1.7), (-0.15, 1.83), (0.05, 1.87), (0.22, 1.8), (0.3, 1.68), (0.18, 1.66), (0.06, 1.7), (-0.06, 1.62), (-0.14, 1.66), (-0.2, 1.5)]), f"Relleno {c}", radio=RI)

def accesorio_perfil(capas, p):
    a, c = p["accesorio"], p["color_accesorio"]; L = capas["P_accesorio"]
    if a == "gafas":
        L.trazo(circulo(0.17, 1.58, 0.085, 18), f"Trazo {c}", radio=0.018, cerrado=True)
        L.linea([P(0.09, 1.6), P(-0.06, 1.56)], f"Trazo {c}", radio=0.015)
    elif a == "gorra":
        L.forma(suave([(-0.28, 1.64), (-0.22, 1.82), (0.05, 1.9), (0.27, 1.76), (0.28, 1.66)], 4), f"Relleno {c}", radio=RI)
        L.forma(poligono([(0.15, 1.66), (0.48, 1.62), (0.45, 1.68), (0.2, 1.72)]), f"Relleno {c}-", radio=RI)
    elif a == "sombrero":
        L.forma(rect_redondeado(-0.2, 1.74, 0.22, 2.12, 0.03), f"Relleno {c}", radio=RI)
        L.forma(elipse(0.01, 1.74, 0.38, 0.05, 20), f"Relleno {c}", radio=RI)
    elif a == "corona":
        L.forma(poligono([(-0.18, 1.76), (0.2, 1.76), (0.22, 1.98), (0.1, 1.86), (0.0, 2.0), (-0.1, 1.86), (-0.2, 1.98)]), "Relleno oro", radio=RI)
    elif a == "pajarita":
        capas["P_accesorio_torso"].forma(poligono([(0.12, 1.22), (0.2, 1.28), (0.2, 1.16)]), f"Relleno {c}", radio=RD)
    elif a == "mochila":
        capas["P_accesorio_torso"].forma(rect_redondeado(-0.36, 0.78, -0.12, 1.2, 0.06), f"Relleno {c}", radio=RI)
    elif a == "capa":
        capas["P_capa"].forma(poligono([(-0.05, 1.24), (-0.15, 1.22), (-0.55, 0.3), (-0.2, 0.25)]), f"Relleno {c}", radio=RI)

def cola(lp, p, perfil):
    if p["tipo"] not in ("gato", "perro", "monstruo"): return
    c = p["piel"]
    pts = [(-0.1, 0.72), (-0.3, 0.75), (-0.42, 0.95), (-0.36, 1.05)] if p["tipo"] == "gato" else [(-0.1, 0.72), (-0.3, 0.8), (-0.42, 0.9)]
    lp.linea(suave(pts, 5, cerrado=False), "Tinta", radio=0.058)          # contorno debajo
    lp.linea(suave(pts, 5, cerrado=False), f"Trazo {c}", radio=0.042)

# ---------------------------------------------------------------- personaje completo
ORDEN_F = ["F_capa", "F_pelo_atras", "F_cola", "F_pierna_sup.R", "F_pierna_inf.R", "F_pierna_sup.L", "F_pierna_inf.L",
           "F_pelvis", "F_torso", "F_accesorio_torso", "F_brazo_sup.R", "F_brazo_inf.R", "F_brazo_sup.L", "F_brazo_inf.L",
           "F_cabeza", "F_mejillas", "F_ojos", "F_pupilas", "F_ojos_cerrados", "F_cejas", "F_boca_0", "F_boca_1", "F_boca_2",
           "F_pelo", "F_accesorio"]
ORDEN_P = ["P_cola", "P_brazo_sup.tras", "P_brazo_inf.tras", "P_pierna_sup.tras", "P_pierna_inf.tras", "P_capa", "P_pelo_atras",
           "P_pierna_sup.del", "P_pierna_inf.del", "P_pelvis", "P_torso", "P_accesorio_torso", "P_cabeza", "P_mejillas", "P_ojos",
           "P_pupilas", "P_ojos_cerrados", "P_cejas", "P_boca_0", "P_boca_1", "P_boca_2", "P_pelo", "P_accesorio",
           "P_brazo_sup.del", "P_brazo_inf.del"]
HUESO_DE_CAPA = {
    "capa": "torso", "pelo_atras": "cabeza", "cola": "cola", "pelvis": "cadera", "torso": "torso", "accesorio_torso": "torso",
    "cabeza": "cabeza", "mejillas": "cabeza", "ojos": "cabeza", "pupilas": "ojos", "ojos_cerrados": "cabeza", "cejas": "cabeza",
    "boca_0": "cabeza", "boca_1": "cabeza", "boca_2": "cabeza", "pelo": "cabeza", "accesorio": "cabeza",
}

def hueso_de_capa(nombre):
    if nombre == "sombra": return ""
    base = nombre[2:]
    if base in HUESO_DE_CAPA: return HUESO_DE_CAPA[base]
    return ("p_" + base) if nombre.startswith("P_") else base   # brazos y piernas: mismo nombre que el hueso

def crear_personaje(p, col_, m3d=False):
    """Dibuja el personaje con las dos vistas. El objeto queda en el origen (el rig lo coloca)."""
    ob = nuevo_gp(p["id"], col_, profundidad3d=False)
    gp = ob.data
    robot = p["tipo"] == "robot"
    piel, ropa, pant = p["piel"], p["ropa"], p["pantalon"]
    zap = "negro" if not robot else "gris_oscuro"
    sombra = Lapiz(ob, "sombra"); sombra.forma(elipse(0, 0.0, 0.42, 0.07, 24, y=0.01), "Sombra", linea=False)
    capas = {}
    for grupo, orden in (("frente", ORDEN_F), ("perfil", ORDEN_P)):
        for nombre in orden: capas[nombre] = Lapiz(ob, nombre, grupo=grupo)
    # frente
    cola(capas["F_cola"], p, False)
    pierna((capas["F_pierna_sup.R"], capas["F_pierna_inf.R"]), "pierna_sup.R", "pierna_inf.R", pant, zap, False)
    pierna((capas["F_pierna_sup.L"], capas["F_pierna_inf.L"]), "pierna_sup.L", "pierna_inf.L", pant, zap, False)
    pelvis(capas["F_pelvis"], pant, False)
    torso_frente(capas["F_torso"], ropa, robot)
    brazo((capas["F_brazo_sup.R"], capas["F_brazo_inf.R"]), "brazo_sup.R", "brazo_inf.R", ropa, piel, robot)
    brazo((capas["F_brazo_sup.L"], capas["F_brazo_inf.L"]), "brazo_sup.L", "brazo_inf.L", ropa, piel, robot)
    cabeza_frente(capas["F_cabeza"], p)
    cara_frente(capas, p)
    pelo_frente(capas["F_pelo_atras"], capas["F_pelo"], p)
    accesorio_frente(capas, p)
    # perfil
    cola(capas["P_cola"], p, True)
    brazo((capas["P_brazo_sup.tras"], capas["P_brazo_inf.tras"]), "p_brazo_sup.tras", "p_brazo_inf.tras", ropa + "-", piel + "-" if piel in CP.PALETA else piel, robot)
    pierna((capas["P_pierna_sup.tras"], capas["P_pierna_inf.tras"]), "p_pierna_sup.tras", "p_pierna_inf.tras", pant + "-", zap, True)
    pierna((capas["P_pierna_sup.del"], capas["P_pierna_inf.del"]), "p_pierna_sup.del", "p_pierna_inf.del", pant, zap, True)
    pelvis(capas["P_pelvis"], pant, True)
    torso_perfil(capas["P_torso"], ropa, robot)
    cabeza_perfil(capas["P_cabeza"], p)
    cara_perfil(capas, p)
    pelo_perfil(capas["P_pelo_atras"], capas["P_pelo"], p)
    accesorio_perfil(capas, p)
    brazo((capas["P_brazo_sup.del"], capas["P_brazo_inf.del"]), "p_brazo_sup.del", "p_brazo_inf.del", ropa, piel, robot)
    # capas vacias fuera; estado inicial: vista de frente, boca cerrada, ojos abiertos
    for L in list(gp.layers):
        if L.name != "sombra" and all(len(f.drawing.strokes) == 0 for f in L.frames):
            gp.layers.remove(L)
    for L in gp.layers:   # ocultar con hide (una opacidad 0 animada deja huecos de profundidad en 3D)
        L.hide = L.name.startswith("P_") or L.name.endswith(("boca_1", "boca_2", "ojos_cerrados"))
    if robot:
        brillo(ob, (0.2, 1.0, 1.0), 12)
    temblor_linea(ob, factor=CFG["temblor_linea"] * 0.6, semilla=hash(p["id"]) % 1000)
    ob["comic_tipo"] = "personaje"; ob["comic_id"] = p["id"]; ob["comic_personaje"] = json.dumps(p)
    return ob

# ---------------------------------------------------------------- rig
def crear_armature(nombre, huesos, col_, mostrar="STICK"):
    """huesos: [(nombre, cabeza(x,z), cola(x,z), padre)]; roll alineado a -Y (giro en el plano de pantalla)."""
    arm = bpy.data.armatures.new(nombre); arm.display_type = mostrar
    rig = bpy.data.objects.new(nombre, arm); col_.objects.link(rig)
    rig.show_in_front = True
    vl = bpy.context.view_layer
    prev = vl.objects.active
    vl.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for n, (x0, z0), (x1, z1), padre in huesos:
        eb = arm.edit_bones.new(n); eb.head = (x0, 0, z0); eb.tail = (x1, 0, z1)
        if (Vector(eb.tail) - Vector(eb.head)).length < 1e-4: eb.tail = (x0, 0, z0 + 0.1)
        eb.align_roll((0, -1, 0)); ebs[n] = eb
    for n, _, _, padre in huesos:
        if padre: ebs[n].parent = ebs[padre]
    bpy.ops.object.mode_set(mode='OBJECT')
    vl.objects.active = prev
    for pb in rig.pose.bones: pb.rotation_mode = 'XYZ'
    return rig

def rig_personaje(ob, col_):
    """Crea RIG_<id>, emparenta cada capa a su hueso y mueve el personaje al rig."""
    p = json.loads(ob["comic_personaje"])
    rig = crear_armature(f"RIG_{p['id']}", HUESOS, col_)
    loc = ob.location.copy(); ob.location = (0, 0, 0)
    bpy.context.view_layer.update()
    for L in ob.data.layers:
        h = hueso_de_capa(L.name)
        L.parent = rig
        if h: L.parent_bone = h
    rig.location = loc
    s = p.get("altura", 1.0); rig.scale = (s, s, s)
    ob.parent = rig            # solo para organizar: las capas emparentadas ignoran la transformacion del objeto
    ob.matrix_parent_inverse = rig.matrix_world.inverted()
    rig["comic_personaje"] = ob["comic_personaje"]; rig["comic_tipo"] = "rig_personaje"; rig["comic_id"] = p["id"]
    ob["comic_rig"] = rig.name
    return rig
