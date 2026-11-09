# Escenografia reutilizable dibujada con Grease Pencil: cielos, suelos y 29 tipos de elementos.
# Cada generador dibuja en coordenadas locales (base en el origen, frente hacia -Y) y devuelve sus "partes":
# los huesos que el modo rig creara y las capas que cuelgan de cada uno.
#   2D: todo en el plano XZ.   3D: los tipos "caja" tienen volumen; el resto son planos que miran a camara.
import math, random
from gp_base import (Lapiz, nuevo_gp, P, circulo, elipse, rect, rect_redondeado, poligono, estrella, capsula,
                     bezier, arco, nube, caja, cara_rect, temblor_linea, brillo, CFG)
import gp_base as GB
import comic_parametros as CP

R = 0.032          # tinta de la escenografia
R2 = 0.02          # detalles

def _y(p, y): return (p[0], y, p[2])

def parte(hueso, cabeza, cola, capas, padre="raiz"):
    return dict(hueso=hueso, cabeza=list(cabeza), cola=list(cola), capas=list(capas), padre=padre)

# ================================================================ elementos
def edificio(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["azul", "violeta", "turquesa", "magenta", "naranja"])
    pisos = el["pisos"] or rnd.randint(5, 10)
    w, d, hp = 3.0, 2.6, 0.9
    h = 0.6 + pisos * hp
    cols = 3 if w >= 3 else 2
    lp = Lapiz(ob, "cuerpo")
    noche = el.get("_noche", False)
    def ventana_color(): return "amarillo" if rnd.random() < (0.65 if noche else 0.3) else "celeste+"
    if m3d:
        x0, x1, y0, y1 = -w / 2, w / 2, -d / 2, d / 2
        bx = (x0, x1, y0, y1, 0, h)
        caja(lp, *bx, f"Relleno {c}", f"Semitono {c}-", f"Relleno {c}+", radio=R, caras="FLDA")
        lv = Lapiz(ob, "ventanas")
        for k in range(pisos):
            z0 = 0.9 + k * hp
            if z0 + 0.5 > h - 0.3: break
            for i in range(cols):
                u0 = x0 + 0.35 + i * (w - 0.7) / cols
                cara_rect(lv, "F", u0 + 0.12, z0, u0 + (w - 0.7) / cols - 0.12, z0 + 0.5, bx, f"Relleno {ventana_color()}", radio=R2)
                cara_rect(lv, "A", u0 + 0.12, z0, u0 + (w - 0.7) / cols - 0.12, z0 + 0.5, bx, f"Relleno {ventana_color()}", radio=R2)
            for i in range(2):
                v0 = y0 + 0.35 + i * (d - 0.7) / 2
                for cara in "LD":
                    cara_rect(lv, cara, v0 + 0.12, z0, v0 + (d - 0.7) / 2 - 0.12, z0 + 0.5, bx, f"Relleno {ventana_color()}", radio=R2)
        cara_rect(lv, "F", -0.4, 0, 0.4, 0.75, bx, "Relleno chocolate", radio=R2)
        caja(lp, x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, h, h + 0.25, f"Relleno {c}-", f"Relleno {c}--", f"Relleno {c}-", radio=R)
        if rnd.random() < 0.6:
            caja(lp, 0.2, 0.9, -0.3, 0.4, h + 0.252, h + 0.9, "Relleno rojo", "Relleno rojo-", "Relleno rojo+", radio=R2)
    else:
        lp.forma(rect(-w / 2, 0, w / 2, h), f"Relleno {c}", radio=R)
        if CFG["semitono"]: lp.forma(rect(w / 2 - 0.65, 0, w / 2, h), f"Semitono plano {c}-", linea=False)
        lp.forma(rect(-w / 2 - 0.12, h, w / 2 + 0.12, h + 0.28), f"Relleno {c}-", radio=R)
        lv = Lapiz(ob, "ventanas")
        for k in range(pisos):
            z0 = 0.9 + k * hp
            if z0 + 0.5 > h - 0.3: break
            for i in range(cols):
                u0 = -w / 2 + 0.35 + i * (w - 0.7) / cols
                lv.forma(rect_redondeado(u0 + 0.12, z0, u0 + (w - 0.7) / cols - 0.12, z0 + 0.5, 0.05), f"Relleno {ventana_color()}", radio=R2)
                lv.linea([P(u0 + 0.2, z0 + 0.38), P(u0 + 0.32, z0 + 0.45)], "Tinta blanca", radio=0.012)
        lv.forma(rect_redondeado(-0.4, 0, 0.4, 0.75, 0.08), "Relleno chocolate", radio=R2)
        if rnd.random() < 0.6:
            lp.forma(rect(0.2, h + 0.28, 0.9, h + 0.85), "Relleno rojo", radio=R2)
            lp.linea([P(-0.6, h + 0.28), P(-0.6, h + 1.3)], "Tinta", radio=R2)
            lp.forma(circulo(-0.6, h + 1.32, 0.08, 12), "Relleno rojo", radio=R2)
    return dict(alto=h, ancho=w, partes=[parte("cuerpo", (0, 0), (0, h), ["cuerpo", "ventanas"])])

def casa(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["rosa", "amarillo", "cian", "lima", "mandarina"])
    c2 = el["color2"] or "rojo"
    w, d, h, ht = 3.2, 2.8, 2.2, 1.4
    lp = Lapiz(ob, "cuerpo")
    if m3d:
        x0, x1, y0, y1 = -w / 2, w / 2, -d / 2, d / 2
        bx = (x0, x1, y0, y1, 0, h)
        caja(lp, *bx, f"Relleno {c}", f"Semitono {c}-", caras="FLDA")
        lt = Lapiz(ob, "tejado")
        for yy in (y0, y1):   # hastiales
            lt.forma([(x0, yy, h), (x1, yy, h), (0, yy, h + ht)], f"Relleno {c}", radio=R)
        e = 0.25
        lt.forma([(x0 - e, y0 - e, h - 0.1), (0, y0 - e, h + ht), (0, y1 + e, h + ht), (x0 - e, y1 + e, h - 0.1)], f"Relleno {c2}", radio=R)
        lt.forma([(x1 + e, y0 - e, h - 0.1), (0, y0 - e, h + ht), (0, y1 + e, h + ht), (x1 + e, y1 + e, h - 0.1)], f"Semitono {c2}-", radio=R)
        caja(lt, 0.6, 1.0, 0.2, 0.6, h + 0.5, h + ht + 0.2, "Relleno carmesi", "Relleno carmesi-", "Relleno negro", radio=R2)
        lv = Lapiz(ob, "detalles")
        cara_rect(lv, "F", -0.35, 0, 0.35, 1.25, bx, "Relleno chocolate", radio=R2, redondeo=0.1)
        for u in (-1.15, 0.65):
            cara_rect(lv, "F", u, 1.0, u + 0.55, 1.6, bx, "Relleno celeste+", radio=R2)
        for cara in "LD":
            cara_rect(lv, cara, -0.4, 1.0, 0.4, 1.6, bx, "Relleno celeste+", radio=R2)
    else:
        lp.forma(rect(-w / 2, 0, w / 2, h), f"Relleno {c}", radio=R)
        if CFG["semitono"]: lp.forma(rect(w / 2 - 0.55, 0, w / 2, h), f"Semitono plano {c}-", linea=False)
        lt = Lapiz(ob, "tejado")
        lt.forma(rect(0.6, h + 0.2, 1.0, h + ht + 0.1), "Relleno carmesi", radio=R2)
        lt.forma(poligono([(-w / 2 - 0.3, h - 0.05), (w / 2 + 0.3, h - 0.05), (0, h + ht)]), f"Relleno {c2}", radio=R)
        lt.linea([P(-w / 2 + 0.4, h + 0.3), P(-0.2, h + ht - 0.3)], "Tinta blanca", radio=0.015)
        lv = Lapiz(ob, "detalles")
        lv.forma(rect_redondeado(-0.35, 0, 0.35, 1.25, 0.12), "Relleno chocolate", radio=R2)
        lv.forma(circulo(0.2, 0.62, 0.05, 10), "Relleno oro", radio=0.01)
        for u in (-1.2, 0.65):
            lv.forma(rect(u, 1.0, u + 0.55, 1.6), "Relleno celeste+", radio=R2)
            lv.linea([P(u + 0.275, 1.0), P(u + 0.275, 1.6)], radio=0.012); lv.linea([P(u, 1.3), P(u + 0.55, 1.3)], radio=0.012)
        lv.forma(rect(-0.25, 0.0, 0.25, 0.08), "Relleno gris", radio=0.012)
    return dict(alto=h + ht, ancho=w, partes=[parte("cuerpo", (0, 0), (0, h + ht), ["cuerpo", "tejado", "detalles"])])

def tienda(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["amarillo", "turquesa", "rosa"])
    c2 = el["color2"] or rnd.choice(["rojo", "azul", "verde"])
    w, d, h = 3.6, 2.6, 2.6
    texto = (el.get("texto") or rnd.choice(["CAFÉ", "PIZZA", "TIENDA", "HELADOS"])).upper()
    lp = Lapiz(ob, "cuerpo"); la = Lapiz(ob, "toldo"); lv = Lapiz(ob, "detalles")
    y0 = -d / 2 if m3d else 0.0
    if m3d:
        bx = (-w / 2, w / 2, -d / 2, d / 2, 0, h)
        caja(lp, *bx, f"Relleno {c}", f"Semitono {c}-", f"Relleno {c}+", radio=R)
        cara_rect(lv, "F", -1.5, 0.3, 0.6, 1.5, bx, "Relleno celeste+", radio=R2)
        cara_rect(lv, "F", 0.9, 0, 1.5, 1.4, bx, "Relleno chocolate", radio=R2)
        cara_rect(lv, "F", -1.4, 2.0, 1.4, 2.5, bx, f"Relleno {c2}", radio=R2)
    else:
        lp.forma(rect(-w / 2, 0, w / 2, h), f"Relleno {c}", radio=R)
        if CFG["semitono"]: lp.forma(rect(w / 2 - 0.5, 0, w / 2, h), f"Semitono plano {c}-", linea=False)
        lv.forma(rect(-1.5, 0.3, 0.6, 1.5), "Relleno celeste+", radio=R2)
        for k in range(2): lv.linea([P(-1.3 + k * 0.25, 0.6), P(-0.9 + k * 0.25, 1.2)], "Tinta blanca", radio=0.018)
        lv.forma(rect_redondeado(0.9, 0, 1.5, 1.4, 0.08), "Relleno chocolate", radio=R2)
        lv.forma(rect_redondeado(-1.4, 2.0, 1.4, 2.5, 0.08), f"Relleno {c2}", radio=R2)
    yt = y0 - 0.02
    lv.texto(texto, tam=0.42, centro=(0, yt - 0.01, 2.25), mat="Relleno blanco", radio=0.008)
    # toldo a rayas (inclinado hacia delante en 3d)
    n = 7; x0 = -w / 2 - 0.1; dx = (w + 0.2) / n
    for i in range(n):
        cc = c2 if i % 2 == 0 else "blanco"
        if m3d:
            pts = [(x0 + i * dx, yt, 1.95), (x0 + (i + 1) * dx, yt, 1.95), (x0 + (i + 1) * dx, yt - 0.7, 1.55), (x0 + i * dx, yt - 0.7, 1.55)]
        else:
            pts = [P(x0 + i * dx, 1.95), P(x0 + (i + 1) * dx, 1.95), P(x0 + (i + 1) * dx + 0.06, 1.6), P(x0 + i * dx + 0.06, 1.6)]
        la.forma(pts, f"Relleno {cc}", radio=R2)
        cx = x0 + (i + 0.5) * dx + (0 if m3d else 0.06)
        fest = arco(cx, 1.6 if not m3d else 1.55, dx / 2, 180, 360, 8)
        la.forma([(p[0], (yt - 0.7) if m3d else 0, p[2]) for p in fest], f"Relleno {cc}", radio=R2)
    return dict(alto=h, ancho=w, partes=[parte("cuerpo", (0, 0), (0, h), ["cuerpo", "toldo", "detalles"])])

def arbol(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["verde", "lima", "verde_oscuro"])
    lt = Lapiz(ob, "tronco")
    lt.forma(poligono([(-0.22, 0), (0.22, 0), (0.14, 1.5), (0.35, 1.9), (0.1, 1.75), (-0.1, 1.75), (-0.3, 1.95), (-0.14, 1.5)]), "Relleno marron", radio=R)
    lt.linea([P(0.05, 0.3), P(0.08, 0.9)], radio=0.012)
    lc = Lapiz(ob, "copa")
    s = rnd.randint(0, 999)
    lc.forma(nube(0, 2.45, 2.5, 2.1, 5, semilla=s), f"Relleno {c}", radio=R)
    if CFG["semitono"]: lc.forma(nube(0.25, 2.05, 1.7, 1.0, 4, semilla=s + 1), f"Semitono plano {c}-", linea=False)
    lc.forma(nube(-0.45, 2.95, 0.8, 0.55, 3, semilla=s + 2), f"Plano {c}+", linea=False)
    for k in range(3):
        a = rnd.uniform(0, 2 * math.pi); lc.forma(circulo(0.7 * math.cos(a), 2.4 + 0.6 * math.sin(a), 0.1, 10), "Relleno rojo", radio=0.012)
    return dict(alto=3.6, ancho=2.5, partes=[parte("copa", (0, 1.6), (0, 3.4), ["copa"])])

def pino(ob, el, m3d, rnd):
    c = el["color"] or "verde_oscuro"
    lt = Lapiz(ob, "tronco"); lt.forma(rect(-0.16, 0, 0.16, 0.7), "Relleno marron", radio=R)
    lc = Lapiz(ob, "copa")
    for i, (z, w) in enumerate([(0.5, 1.8), (1.5, 1.45), (2.4, 1.05)]):
        hh = 1.4
        pts = [(-w / 2, z), (-w / 4, z + 0.12), (0, z), (w / 4, z + 0.12), (w / 2, z), (0, z + hh)]
        lc.forma(poligono(pts), f"Relleno {c}", radio=R)
        if CFG["semitono"]: lc.forma(poligono([(0, z + 0.03), (w / 4, z + 0.13), (w / 2 - 0.05, z + 0.03), (0, z + hh - 0.05)]), f"Semitono plano {c}-", linea=False)
    lc.forma(estrella(0, 3.95, 0.22, 0.1), "Relleno amarillo", radio=R2)
    return dict(alto=4.1, ancho=1.8, partes=[parte("copa", (0, 0.6), (0, 3.9), ["copa"])])

def palmera(ob, el, m3d, rnd):
    c = el["color"] or "verde"
    lt = Lapiz(ob, "tronco")
    eje = bezier((0, 0, 0), (0.1, 0, 1.5), (0.6, 0, 2.8), (0.45, 0, 3.6), 10)
    for i in range(len(eje) - 1):
        (xa, _, za), (xb, _, zb) = eje[i], eje[i + 1]
        r0 = 0.2 - 0.07 * i / len(eje)
        lt.forma(capsula(xa, za, xb, zb, r0, r0 * 0.92, n=4), "Relleno oro-", radio=R2)
    lc = Lapiz(ob, "copa"); top = (0.45, 3.65)
    for k, a in enumerate([10, 50, 95, 140, 175, 220, 320]):
        ar = math.radians(a); L = 1.5
        tip = (top[0] + L * math.cos(ar), top[1] + L * 0.55 * math.sin(ar) - 0.35)
        mid = ((top[0] + tip[0]) / 2 - 0.25 * math.sin(ar), (top[1] + tip[1]) / 2 + 0.35)
        up = bezier(P(*top), P(*mid), P(*mid), P(*tip), 8); dn = bezier(P(*tip), P(mid[0], mid[1] - 0.35), P(mid[0], mid[1] - 0.35), P(*top), 8)
        lc.forma(up + dn[1:-1], f"Relleno {c}", radio=R2)
    for dx in (-0.12, 0.15): lc.forma(circulo(top[0] + dx, top[1] - 0.2, 0.13, 10), "Relleno chocolate", radio=R2)
    return dict(alto=4.3, ancho=2.6, partes=[parte("copa", (0.4, 3.4), (0.45, 4.2), ["copa"])])

def arbusto(ob, el, m3d, rnd):
    c = el["color"] or "lima"; lc = Lapiz(ob, "copa"); s = rnd.randint(0, 999)
    lc.forma(nube(0, 0.45, 1.7, 0.95, 4, semilla=s), f"Relleno {c}", radio=R)
    if CFG["semitono"]: lc.forma(nube(0.2, 0.3, 1.1, 0.45, 3, semilla=s + 3), f"Semitono plano {c}-", linea=False)
    lc.forma(nube(-0.3, 0.65, 0.5, 0.3, 2, semilla=s + 1), f"Plano {c}+", linea=False)
    for k in range(4):
        lc.forma(estrella(rnd.uniform(-0.6, 0.6), rnd.uniform(0.3, 0.75), 0.07, 0.035), "Relleno blanco", radio=0.008)
    return dict(alto=0.95, ancho=1.7, partes=[parte("copa", (0, 0), (0, 0.9), ["copa"])])

def flores(ob, el, m3d, rnd):
    lc = Lapiz(ob, "copa"); cols = [el["color"] or "magenta", el["color2"] or "amarillo", "violeta", "rojo", "cian"]
    for k in range(5):
        x = -0.5 + k * 0.25 + rnd.uniform(-0.05, 0.05); hgt = rnd.uniform(0.3, 0.5)
        lc.linea(bezier(P(x, 0), P(x - 0.05, hgt * 0.4), P(x + 0.05, hgt * 0.7), P(x, hgt), 6), "Trazo verde_oscuro", radio=0.022)
        lc.forma(elipse(x + 0.07, hgt * 0.35, 0.07, 0.03, 10, giro=0.6), "Relleno verde", radio=0.01)
        cc = cols[k % len(cols)]
        for j in range(5):
            a = 2 * math.pi * j / 5
            lc.forma(circulo(x + 0.065 * math.cos(a), hgt + 0.065 * math.sin(a), 0.05, 10), f"Relleno {cc}", radio=0.01)
        lc.forma(circulo(x, hgt, 0.035, 8), "Relleno oro", radio=0.008)
    return dict(alto=0.6, ancho=1.2, partes=[parte("copa", (0, 0), (0, 0.5), ["copa"])])

def nube_el(ob, el, m3d, rnd):
    c = el["color"] or "blanco"; lc = Lapiz(ob, "cuerpo"); s = rnd.randint(0, 999)
    lc.forma(nube(0, 0.7, 3.0, 1.35, 4, semilla=s), f"Relleno {c}", radio=R)
    lc.forma(nube(0.15, 0.35, 2.3, 0.45, 3, semilla=s + 1), "Plano celeste+", linea=False)
    lc.linea(arco(-0.7, 0.9, 0.35, 100, 170, 8), "Tinta", radio=0.012)
    return dict(alto=1.4, ancho=3.0, partes=[parte("cuerpo", (0, 0), (0, 1.4), ["cuerpo"])])

def sol(ob, el, m3d, rnd):
    c = el["color"] or "amarillo"
    lr = Lapiz(ob, "rayos")
    for k in range(12):
        a = 2 * math.pi * k / 12; a2 = a + math.pi / 12
        rr = 1.25 if k % 2 == 0 else 1.05
        lr.forma(poligono([(0.82 * math.cos(a - 0.12), 0.82 * math.sin(a - 0.12)), (rr * math.cos(a), rr * math.sin(a)),
                           (0.82 * math.cos(a + 0.12), 0.82 * math.sin(a + 0.12))]), "Relleno naranja" if k % 2 else "Relleno mandarina", radio=R2)
    ln = Lapiz(ob, "nucleo")
    ln.forma(circulo(0, 0, 0.8, 40), f"Relleno {c}", radio=R)
    ln.forma(circulo(0.12, -0.1, 0.62, 30), f"Plano {c}+", linea=False)
    for dx in (-0.25, 0.25):
        ln.linea(arco(dx, 0.12, 0.1, 20, 160, 6), radio=0.03)
    ln.linea(arco(0, -0.05, 0.3, 200, 340, 10), radio=0.03)
    for dx in (-0.45, 0.45): ln.forma(elipse(dx, -0.12, 0.1, 0.06, 12), "Plano rosa", linea=False)
    brillo(ob, (1.0, 0.75, 0.1), 60)
    return dict(alto=2.5, ancho=2.5, partes=[parte("rayos", (0, -0.4), (0, 0.4), ["rayos"]), parte("nucleo", (0, -0.4), (0, 0.4), ["nucleo"])],
                origen_z=0)

def luna(ob, el, m3d, rnd):
    c = el["color"] or "crema"; ln = Lapiz(ob, "nucleo")
    r1, (cx2, cz2), r2 = 0.9, (-0.45, 0.1), 0.8          # creciente = circulo exterior menos circulo desplazado
    angs = [math.radians(-180 + 360 * i / 96) for i in range(96)]
    fuera = [(r1 * math.cos(a), r1 * math.sin(a)) for a in angs
             if math.hypot(r1 * math.cos(a) - cx2, r1 * math.sin(a) - cz2) > r2]
    dentro = [(cx2 + r2 * math.cos(a), cz2 + r2 * math.sin(a)) for a in reversed(angs)
              if math.hypot(cx2 + r2 * math.cos(a), cz2 + r2 * math.sin(a)) < r1]
    ln.forma(poligono(fuera + dentro), f"Relleno {c}", radio=R)
    for (x, z, r) in [(0.55, 0.2, 0.1), (0.4, -0.45, 0.07)]: ln.forma(circulo(x, z, r, 10), f"Plano {c}-", linea=False)
    brillo(ob, (1.0, 0.95, 0.6), 40)
    return dict(alto=1.8, ancho=1.8, partes=[parte("nucleo", (0, -0.4), (0, 0.4), ["nucleo"])], origen_z=0)

def montana(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["violeta", "azul", "morado"])
    lp = Lapiz(ob, "cuerpo")
    picos = [(-6, 0), (-3.5, 4.5), (-2.2, 3.4), (0.3, 7.0), (2.5, 4.2), (3.6, 5.0), (6, 0)]
    lp.forma(poligono(picos), f"Relleno {c}", radio=R)
    if CFG["semitono"]: lp.forma(poligono([(0.3, 7.0), (2.5, 4.2), (3.6, 5.0), (6, 0), (1.5, 0)]), f"Semitono plano {c}-", linea=False)
    for (px, pz), s in [((0.3, 7.0), 1.3), ((-3.5, 4.5), 0.9), ((3.6, 5.0), 0.7)]:
        lp.forma(poligono([(px, pz), (px + 0.45 * s, pz - 0.75 * s), (px + 0.15 * s, pz - 0.6 * s), (px, pz - 0.85 * s),
                           (px - 0.2 * s, pz - 0.6 * s), (px - 0.5 * s, pz - 0.8 * s)]), "Relleno blanco", radio=R2)
    return dict(alto=7.0, ancho=12.0, partes=[parte("cuerpo", (0, 0), (0, 7), ["cuerpo"])])

def colina(ob, el, m3d, rnd):
    c = el["color"] or "verde"; lp = Lapiz(ob, "cuerpo")
    pts = [P(5 * math.cos(math.pi * i / 30), 2.5 * math.sin(math.pi * i / 30)) for i in range(31)]
    lp.forma(pts, f"Relleno {c}", radio=R)
    if CFG["semitono"]: lp.forma([P(5 * math.cos(math.pi * i / 30), 2.5 * math.sin(math.pi * i / 30)) for i in range(0, 13)] + [P(1.0, 0)], f"Semitono plano {c}-", linea=False)
    for k in range(6):
        x = rnd.uniform(-3.5, 3.5); z = rnd.uniform(0.3, 1.6) * (1 - abs(x) / 5)
        lp.linea([P(x - 0.08, z), P(x, z + 0.15), P(x + 0.08, z)], "Trazo verde_oscuro", radio=0.015)
    return dict(alto=2.5, ancho=10, partes=[parte("cuerpo", (0, 0), (0, 2.5), ["cuerpo"])])

def roca(ob, el, m3d, rnd):
    c = el["color"] or "gris"; lp = Lapiz(ob, "cuerpo")
    perfil = [(-0.6, 0), (0.6, 0), (0.55, 0.45), (0.25, 0.8), (-0.2, 0.75), (-0.55, 0.4)]
    if m3d:
        y0, y1 = -0.4, 0.4
        lp.forma([(x, y0, z) for x, z in perfil], f"Relleno {c}", radio=R)
        lp.forma([(x, y1, z) for x, z in perfil], f"Relleno {c}", radio=R)
        for i in range(1, len(perfil)):
            a, b = perfil[i - 1], perfil[i]
            if a[1] == 0 and b[1] == 0: continue
            lp.forma([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])], f"Semitono {c}-", radio=R)
        a, b = perfil[-1], perfil[0]
        lp.forma([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])], f"Semitono {c}-", radio=R)
    else:
        lp.forma(poligono(perfil), f"Relleno {c}", radio=R)
        if CFG["semitono"]: lp.forma(poligono([(0.05, 0), (0.6, 0), (0.55, 0.45), (0.25, 0.8), (0.2, 0.4)]), f"Semitono plano {c}-", linea=False)
        lp.linea([P(-0.35, 0.45), P(-0.15, 0.62)], "Tinta blanca", radio=0.015)
    return dict(alto=0.8, ancho=1.2, partes=[parte("cuerpo", (0, 0), (0, 0.8), ["cuerpo"])])

def farola(ob, el, m3d, rnd):
    c = el["color"] or "gris_oscuro"; lp = Lapiz(ob, "poste")
    lp.forma(rect(-0.2, 0, 0.2, 0.18), f"Relleno {c}", radio=R2)
    lp.forma(rect(-0.07, 0.18, 0.07, 3.1), f"Relleno {c}", radio=R2)
    lp.forma(poligono([(-0.28, 3.1), (0.28, 3.1), (0.18, 3.45), (-0.18, 3.45)]), f"Relleno {c}", radio=R2)
    lp.forma(rect(-0.3, 3.45, 0.3, 3.55), f"Relleno {c}-", radio=R2)
    ll = Lapiz(ob, "luz")
    ll.forma(circulo(0, 2.98, 0.17, 16), "Relleno amarillo", radio=R2)
    ll.forma(poligono([(-0.17, 2.95), (0.17, 2.95), (0.9, 0.05), (-0.9, 0.05)]), "Translucido amarillo", linea=False)
    return dict(alto=3.6, ancho=0.6, partes=[parte("cuerpo", (0, 0), (0, 3.5), ["poste", "luz"])], luz=["luz"])

def banco(ob, el, m3d, rnd):
    c = el["color"] or "naranja"; lp = Lapiz(ob, "cuerpo")
    if m3d:
        for x in (-0.75, 0.65):
            caja(lp, x, x + 0.1, -0.25, -0.15, 0, 0.448, "Relleno gris_oscuro", radio=R2, caras="FLDA")
            caja(lp, x, x + 0.1, 0.252, 0.33, 0, 0.898, "Relleno gris_oscuro", radio=R2)
        caja(lp, -0.9, 0.9, -0.3, 0.25, 0.45, 0.55, f"Relleno {c}", f"Relleno {c}-", f"Relleno {c}+", radio=R2)
        caja(lp, -0.9, 0.9, 0.18, 0.25, 0.6, 0.9, f"Relleno {c}", f"Relleno {c}-", f"Relleno {c}+", radio=R2)
    else:
        for x in (-0.75, 0.65): lp.forma(rect(x, 0, x + 0.1, 0.5), "Relleno gris_oscuro", radio=R2)
        for z in (0.62, 0.78): lp.forma(rect_redondeado(-0.9, z, 0.9, z + 0.12, 0.04), f"Relleno {c}", radio=R2)
        lp.forma(rect_redondeado(-0.95, 0.42, 0.95, 0.55, 0.04), f"Relleno {c}-", radio=R2)
    return dict(alto=0.9, ancho=1.8, partes=[parte("cuerpo", (0, 0), (0, 0.9), ["cuerpo"])])

def valla(ob, el, m3d, rnd):
    c = el["color"] or "blanco"; lp = Lapiz(ob, "cuerpo")
    for z in (0.3, 0.62): lp.forma(rect(-1.5, z, 1.5, z + 0.1), f"Relleno {c}-", radio=R2)
    for k in range(7):
        x = -1.4 + k * 0.47
        lp.forma(poligono([(x - 0.12, 0), (x + 0.12, 0), (x + 0.12, 0.8), (x, 0.92), (x - 0.12, 0.8)]), f"Relleno {c}", radio=R2)
    return dict(alto=0.95, ancho=3.0, partes=[parte("cuerpo", (0, 0), (0, 0.9), ["cuerpo"])])

def senal(ob, el, m3d, rnd):
    c = el["color"] or "verde"; lp = Lapiz(ob, "cuerpo")
    lp.forma(rect(-0.05, 0, 0.05, 1.7), "Relleno gris", radio=R2)
    flecha = [(-0.5, 1.55), (0.3, 1.55), (0.55, 1.8), (0.3, 2.05), (-0.5, 2.05)]
    if el.get("espejo"): flecha = [(-x, z) for x, z in flecha]
    lp.forma(poligono(flecha), f"Relleno {c}", radio=R2)
    if el.get("texto"): lp.texto(el["texto"].upper(), tam=0.24, centro=(-0.07 if not el.get("espejo") else 0.07, -0.01, 1.8), mat="Relleno blanco", radio=0.006)
    return dict(alto=2.1, ancho=1.1, partes=[parte("cuerpo", (0, 0), (0, 2.0), ["cuerpo"])])

def coche(ob, el, m3d, rnd):
    c = el["color"] or rnd.choice(["rojo", "amarillo", "cian", "magenta"])
    lp = Lapiz(ob, "carroceria")
    ruedas = [-0.85, 0.85]; rz = 0.32
    if m3d:
        caja(lp, -1.4, 1.4, -0.65, 0.65, 0.3, 0.85, f"Relleno {c}", f"Semitono {c}-", f"Relleno {c}+", radio=R)
        caja(lp, -0.7, 0.6, -0.55, 0.55, 0.852, 1.35, "Relleno celeste+", "Relleno celeste", f"Relleno {c}", radio=R)
        for x in (1.392, ):
            for yy in (-0.4, 0.4): lp.forma([(x + 0.02, yy - 0.12, 0.6), (x + 0.02, yy + 0.12, 0.6), (x + 0.02, yy + 0.12, 0.72), (x + 0.02, yy - 0.12, 0.72)], "Relleno amarillo", radio=R2)
        ys = (-0.67, 0.67)
    else:
        cuerpo = rect_redondeado(-1.4, 0.3, 1.4, 0.85, 0.18)
        lp.forma(cuerpo, f"Relleno {c}", radio=R)
        lp.forma(poligono([(-0.75, 0.85), (0.55, 0.85), (0.3, 1.35), (-0.55, 1.35)]), f"Relleno {c}", radio=R)
        lp.forma(poligono([(-0.62, 0.9), (-0.12, 0.9), (-0.12, 1.28), (-0.47, 1.28)]), "Relleno celeste+", radio=R2)
        lp.forma(poligono([(-0.02, 0.9), (0.45, 0.9), (0.26, 1.28), (-0.02, 1.28)]), "Relleno celeste+", radio=R2)
        lp.forma(elipse(1.33, 0.65, 0.07, 0.1, 10), "Relleno amarillo", radio=R2)
        lp.forma(rect(-1.42, 0.62, -1.3, 0.75), "Relleno rojo", radio=R2)
        lp.linea([P(-1.2, 0.55), P(1.2, 0.55)], f"Trazo {c}-", radio=0.02)
        ys = (-0.01,)
    partes = [parte("carroceria", (0, 0.2), (0, 1.3), ["carroceria"])]
    for nombre, x in zip(("rueda_tras", "rueda_del"), ruedas):
        lr = Lapiz(ob, nombre)
        for yy in ys:
            lr.forma([_y(p, yy) for p in circulo(x, rz, rz, 24)], "Relleno negro", radio=R2)
            lr.forma([_y(p, yy - 0.005 * (1 if yy <= 0 else -1)) for p in circulo(x, rz, rz * 0.5, 16)], "Relleno gris_claro", radio=R2)
            for k in range(3):
                a = 2 * math.pi * k / 3
                lr.linea([_y(P(x, rz), yy - 0.01 * (1 if yy <= 0 else -1)), _y(P(x + rz * 0.5 * math.cos(a), rz + rz * 0.5 * math.sin(a)), yy - 0.01 * (1 if yy <= 0 else -1))], radio=0.015)
        partes.append(parte(nombre, (x, rz), (x, rz + 0.3), [nombre], padre="raiz"))
    return dict(alto=1.35, ancho=2.8, partes=partes, ruedas=["rueda_tras", "rueda_del"], radio_rueda=rz)

def cartel(ob, el, m3d, rnd):
    c = el["color"] or "amarillo"; c2 = el["color2"] or "magenta"; lp = Lapiz(ob, "cuerpo")
    for x in (-1.3, 1.3): lp.forma(rect(x - 0.08, 0, x + 0.08, 1.4), "Relleno gris_oscuro", radio=R2)
    lp.forma(rect(-2.0, 1.3, 2.0, 3.2), f"Relleno {c2}", radio=R)
    lp.forma(rect(-1.85, 1.45, 1.85, 3.05), f"Relleno {c}", radio=R2)
    texto = (el.get("texto") or "¡WOW!").upper()
    lp.texto(texto, tam=0.85 if len(texto) <= 8 else 0.55, centro=(0, -0.02, 2.25), mat=f"Relleno {c2}", radio=0.02)
    for k in range(3): lp.forma(estrella(-1.6 + k * 1.6, 2.95, 0.12, 0.05), "Relleno blanco", radio=0.008)
    return dict(alto=3.2, ancho=4.0, partes=[parte("cuerpo", (0, 0), (0, 3.1), ["cuerpo"])])

def caja_el(ob, el, m3d, rnd):
    lp = Lapiz(ob, "cuerpo"); w, h = 0.9, 0.8
    if m3d:
        caja(lp, -w / 2, w / 2, -0.4, 0.4, 0, h, "Carton", "Carton", "Carton", radio=R2)
        lp.forma([(-0.08, -0.41, 0), (0.08, -0.41, 0), (0.08, -0.41, h), (-0.08, -0.41, h)], "Relleno beige", radio=0.01)
    else:
        lp.forma(rect(-w / 2, 0, w / 2, h), "Carton", radio=R2)
        lp.forma(rect(-0.08, 0, 0.08, h), "Relleno beige", radio=0.01)
        lp.linea([P(-w / 2, h - 0.12), P(w / 2, h - 0.12)], radio=0.012)
    return dict(alto=h, ancho=w, partes=[parte("cuerpo", (0, 0), (0, h), ["cuerpo"])])

def cohete(ob, el, m3d, rnd):
    c = el["color"] or "blanco"; c2 = el["color2"] or "rojo"
    ll = Lapiz(ob, "llama")
    ll.forma(poligono([(-0.3, 0.55), (0.3, 0.55), (0.18, 0.1), (0.0, -0.75), (-0.18, 0.1)]), "Relleno naranja", radio=R2)
    ll.forma(poligono([(-0.16, 0.55), (0.16, 0.55), (0.0, -0.25)]), "Relleno amarillo", radio=0.01)
    lp = Lapiz(ob, "cuerpo")
    for s in (-1, 1): lp.forma(poligono([(0.3 * s, 0.6), (0.75 * s, 0.4), (0.7 * s, 1.1), (0.3 * s, 1.5)]), f"Relleno {c2}", radio=R2)
    lp.forma(bezier(P(-0.42, 0.55), P(-0.5, 1.8), P(-0.3, 2.9), P(0, 3.5), 12) + bezier(P(0, 3.5), P(0.3, 2.9), P(0.5, 1.8), P(0.42, 0.55), 12)[1:], f"Relleno {c}", radio=R)
    lp.forma(bezier(P(-0.33, 2.7), P(-0.2, 3.1), P(-0.1, 3.3), P(0, 3.5), 8) + bezier(P(0, 3.5), P(0.1, 3.3), P(0.2, 3.1), P(0.33, 2.7), 8)[1:], f"Relleno {c2}", radio=R2)
    lp.forma(circulo(0, 2.0, 0.24, 20), "Relleno gris", radio=R2); lp.forma(circulo(0, 2.0, 0.16, 16), "Relleno celeste+", radio=0.01)
    return dict(alto=3.6, ancho=1.5, partes=[parte("cuerpo", (0, 0), (0, 3.5), ["cuerpo", "llama"])], llama=["llama"])

def planeta(ob, el, m3d, rnd):
    c = el["color"] or "magenta"; c2 = el["color2"] or "amarillo"
    la = Lapiz(ob, "anillo_atras"); la.trazo(arco(0, 0, 1.0, 0, 180, 24), f"Trazo {c2}", radio=0.08)
    lp = Lapiz(ob, "nucleo")
    lp.forma(circulo(0, 0, 1.3, 40), f"Relleno {c}", radio=R)
    for z in (-0.5, 0.35): lp.linea([P(-1.2, z), P(1.2, z + 0.1)], f"Trazo {c}-", radio=0.07)
    lf = Lapiz(ob, "anillo")
    lf.trazo([(2.0 * math.cos(math.radians(a)), 0, 0.45 * math.sin(math.radians(a)) - 0.05) for a in range(180, 361, 8)], f"Trazo {c2}", radio=0.09)
    return dict(alto=2.8, ancho=4.0, partes=[parte("nucleo", (0, -0.5), (0, 0.5), ["nucleo", "anillo", "anillo_atras"])], origen_z=0)

def mesa(ob, el, m3d, rnd):
    c = el["color"] or "marron"; lp = Lapiz(ob, "cuerpo")
    if m3d:
        for x in (-0.8, 0.7):
            for yy in (-0.4, 0.3): caja(lp, x, x + 0.1, yy, yy + 0.1, 0, 0.798, f"Relleno {c}-", radio=R2, caras="FLDA")
        caja(lp, -0.9, 0.9, -0.5, 0.5, 0.8, 0.92, f"Relleno {c}", f"Relleno {c}-", f"Relleno {c}+", radio=R2)
    else:
        for x in (-0.8, 0.7): lp.forma(rect(x, 0, x + 0.1, 0.82), f"Relleno {c}-", radio=R2)
        lp.forma(rect_redondeado(-0.95, 0.8, 0.95, 0.94, 0.03), f"Relleno {c}", radio=R2)
    return dict(alto=0.95, ancho=1.9, partes=[parte("cuerpo", (0, 0), (0, 0.9), ["cuerpo"])])

def silla(ob, el, m3d, rnd):
    c = el["color"] or "rojo"; lp = Lapiz(ob, "cuerpo")
    for x in (-0.25, 0.18): lp.forma(rect(x, 0, x + 0.07, 0.48), "Relleno chocolate", radio=R2)
    lp.forma(rect_redondeado(-0.3, 0.45, 0.3, 0.55, 0.03), f"Relleno {c}", radio=R2)
    lp.forma(rect_redondeado(-0.28, 0.55, 0.28, 1.1, 0.08), f"Relleno {c}", radio=R2)
    return dict(alto=1.1, ancho=0.6, partes=[parte("cuerpo", (0, 0), (0, 1.0), ["cuerpo"])])

def ventana(ob, el, m3d, rnd):
    c = el["color"] or "rojo"; lp = Lapiz(ob, "cuerpo")
    lp.forma(rect(-0.8, 0, 0.8, 1.6), "Relleno blanco", radio=R2)
    lp.forma(rect(-0.68, 0.12, 0.68, 1.48), "Cielo puntos celeste", radio=R2)
    lp.linea([P(0, 0.12), P(0, 1.48)], radio=0.02); lp.linea([P(-0.68, 0.8), P(0.68, 0.8)], radio=0.02)
    for s in (-1, 1):
        lp.forma(poligono([(0.95 * s, 1.7), (0.45 * s, 1.7), (0.6 * s, 0.9), (0.7 * s, -0.1), (1.0 * s, -0.1)]), f"Relleno {c}", radio=R2)
    lp.forma(rect(-1.05, 1.68, 1.05, 1.78), "Relleno chocolate", radio=R2)
    return dict(alto=1.8, ancho=2.0, partes=[parte("cuerpo", (0, 0), (0, 1.7), ["cuerpo"])])

def cuadro(ob, el, m3d, rnd):
    c = el["color"] or "oro"; lp = Lapiz(ob, "cuerpo")
    lp.forma(rect(-0.6, 0, 0.6, 1.0), f"Relleno {c}", radio=R2)
    lp.forma(rect(-0.48, 0.12, 0.48, 0.88), "Relleno celeste", radio=R2)
    lp.forma([P(-0.48, 0.12), P(0.48, 0.12), P(0.48, 0.45), P(0.1, 0.62), P(-0.2, 0.4), P(-0.48, 0.5)], "Relleno verde", radio=0.01)
    lp.forma(circulo(0.25, 0.7, 0.09, 12), "Relleno amarillo", radio=0.01)
    return dict(alto=1.0, ancho=1.2, partes=[parte("cuerpo", (0, 0), (0, 1.0), ["cuerpo"])])

def planta(ob, el, m3d, rnd):
    c = el["color"] or "naranja"; lp = Lapiz(ob, "copa")
    for k, a in enumerate([-50, -20, 10, 40, 70]):
        ar = math.radians(90 + a); tip = (0.55 * math.cos(ar), 0.5 + 0.75 * math.sin(ar))
        lp.forma(bezier(P(0, 0.45), P(tip[0] * 0.4 - 0.1, tip[1] * 0.8), P(tip[0], tip[1] - 0.1), P(*tip), 6)
                 + bezier(P(*tip), P(tip[0] * 0.8, tip[1] - 0.3), P(tip[0] * 0.3 + 0.1, 0.6), P(0, 0.45), 6)[1:-1], "Relleno verde", radio=0.015)
    lm = Lapiz(ob, "maceta")
    lm.forma(poligono([(-0.3, 0), (0.3, 0), (0.36, 0.42), (-0.36, 0.42)]), f"Relleno {c}", radio=R2)
    lm.forma(rect(-0.4, 0.4, 0.4, 0.52), f"Relleno {c}-", radio=R2)
    return dict(alto=1.3, ancho=0.8, partes=[parte("copa", (0, 0.45), (0, 1.2), ["copa"])])

def lampara(ob, el, m3d, rnd):
    c = el["color"] or "amarillo"; lp = Lapiz(ob, "poste")
    lp.forma(elipse(0, 0.04, 0.28, 0.06, 16), "Relleno gris_oscuro", radio=R2)
    lp.forma(rect(-0.03, 0.05, 0.03, 1.55), "Relleno gris_oscuro", radio=0.012)
    lp.forma(poligono([(-0.32, 1.45), (0.32, 1.45), (0.2, 1.95), (-0.2, 1.95)]), f"Relleno {c}", radio=R2)
    ll = Lapiz(ob, "luz")
    ll.forma(poligono([(-0.3, 1.45), (0.3, 1.45), (0.7, 0.2), (-0.7, 0.2)]), "Translucido amarillo", linea=False)
    return dict(alto=2.0, ancho=0.7, partes=[parte("cuerpo", (0, 0), (0, 1.9), ["poste", "luz"])], luz=["luz"])

GENERADORES = {
    "edificio": edificio, "casa": casa, "tienda": tienda, "arbol": arbol, "pino": pino, "palmera": palmera,
    "arbusto": arbusto, "flores": flores, "nube": nube_el, "sol": sol, "luna": luna, "montana": montana,
    "colina": colina, "roca": roca, "farola": farola, "banco": banco, "valla": valla, "senal": senal,
    "coche": coche, "cartel": cartel, "caja": caja_el, "cohete": cohete, "planeta": planeta, "mesa": mesa,
    "silla": silla, "ventana": ventana, "cuadro": cuadro, "planta": planta, "lampara": lampara,
}
EN_CIELO = {"sol": 6.8, "luna": 6.8, "nube": 6.0, "planeta": 7.5}
EN_PARED = {"cuadro": 1.5, "ventana": 1.0}

def crear_elemento(el, x0_esc, m3d, col_, semilla=0, noche=False):
    """Crea el objeto GP de un elemento del guion en su sitio. Devuelve (objeto, meta)."""
    tipo = el["tipo"]
    rnd = random.Random(f"{el['id']}:{semilla}")
    vol = CP.ELEMENTOS[tipo][1] == "caja"
    ob = nuevo_gp(el["id"], col_, profundidad3d=(m3d and vol))
    el = dict(el, _noche=noche)
    meta = GENERADORES[tipo](ob, el, m3d, rnd)
    prof = el["profundidad"]; y = CP.PROFUNDIDADES[prof]
    esc = el.get("escala", 1.0)
    z = 0.0
    if tipo in EN_CIELO:
        z = EN_CIELO[tipo]
        if m3d: y, z, esc = 40.0, 13.0 + rnd.uniform(-1.5, 1.5), esc * 3.0
        else: y = CP.PROFUNDIDADES["lejos"] + 8.0     # siempre detras de los edificios lejanos
    elif tipo in EN_PARED:
        z = EN_PARED[tipo]; y = 7.9 if not m3d else 5.9
    if not m3d: esc *= CP.ESCALA_2D_PROFUNDIDAD.get(prof, 1.0)
    ob.location = (x0_esc + el["x"], y, z)
    ob.scale = (-esc if el.get("espejo") and tipo not in ("senal",) else esc, esc, esc)
    ob["comic_tipo"] = tipo; ob["comic_id"] = el["id"]; ob["comic_profundidad"] = prof
    ob["comic_billboard"] = bool(m3d and not vol and tipo not in EN_PARED)
    ob["comic_meta"] = __import__("json").dumps(meta)
    temblor_linea(ob, semilla=hash(el["id"]) % 1000)
    return ob, meta

# ================================================================ cielo y suelo
BANDAS_CIELO = {
    "dia": [(0, "celeste++"), (3.5, "celeste+"), (9, "celeste"), (18, "azul")],
    "atardecer": [(0, "amarillo"), (2.5, "mandarina"), (6, "magenta"), (11, "violeta"), (18, "morado-")],
    "noche": [(0, "morado-"), (5, "azul_marino"), (12, "azul_marino-"), (20, "negro")],
    "espacio": [(0, "azul_marino--"), (8, "negro")],
}

def crear_cielo(esc, x0, m3d, col_, params):
    cielo = esc["cielo"]
    if cielo == "interior": return crear_pared(esc, x0, m3d, col_)
    ob = nuevo_gp(f"Cielo_{esc['id']}", col_, profundidad3d=m3d)
    lp = Lapiz(ob, "bandas")
    bandas = BANDAS_CIELO[cielo] + [(200, None)]
    rnd = random.Random(esc["id"])
    if m3d:
        Rc, n = 70.0, 48
        for (z0, c), (z1, _) in zip(bandas, bandas[1:]):
            z1 = min(z1, 90); mat = f"Cielo puntos {c}" if (cielo == "dia" and z0 == 3.5) else f"Plano {c}"
            for i in range(n):
                a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                lp.forma([(Rc * math.cos(a0), Rc * math.sin(a0), z0 - 0.5), (Rc * math.cos(a1), Rc * math.sin(a1), z0 - 0.5),
                          (Rc * math.cos(a1), Rc * math.sin(a1), z1), (Rc * math.cos(a0), Rc * math.sin(a0), z1)], mat, linea=False)
        ob.location = (x0, 0, -1.0)
    else:
        for (z0, c), (z1, _) in zip(bandas, bandas[1:]):
            mat = f"Cielo puntos {c}" if (cielo == "dia" and z0 == 3.5) else f"Plano {c}"
            lp.forma(rect(-160, z0 - 0.05, 160, min(z1, 70) + 0.05), mat, linea=False)
        ob.location = (x0, 60, 0)
    if cielo in ("noche", "espacio"):
        le = Lapiz(ob, "estrellas")
        for k in range(160 if cielo == "espacio" else 90):
            if m3d:
                a = rnd.uniform(0, 2 * math.pi); z = rnd.uniform(4, 40); r = rnd.uniform(0.15, 0.45)
                cx, cy = 69 * math.cos(a), 69 * math.sin(a)
                t = (-math.sin(a), math.cos(a))
                pts = [(cx + t[0] * u, cy + t[1] * u, z + v) for (u, _, v) in estrella(0, 0, r, r * 0.4, 4)]
            else:
                pts = estrella(rnd.uniform(-60, 60), rnd.uniform(3, 40), rnd.uniform(0.06, 0.22), 0.03, 4, y=-0.1)
            le.forma(pts, "Plano amarillo" if rnd.random() < 0.6 else "Plano blanco", linea=False)
        brillo(ob, (1, 0.95, 0.5), 20)
    if cielo == "espacio":
        ln = Lapiz(ob, "nebulosa")
        for k in range(5):
            cx, cz = rnd.uniform(-30, 30), rnd.uniform(8, 25)
            pts = nube(cx, cz, rnd.uniform(8, 16), rnd.uniform(3, 6), 4, semilla=k, y=-0.05)
            if m3d: pts = [(68 * math.cos(p[0] / 68), 68 * math.sin(p[0] / 68), p[2]) for p in pts]
            ln.forma(pts, f"Translucido {rnd.choice(['magenta', 'violeta', 'cian'])}", linea=False)
    ob["comic_tipo"] = "cielo"
    return ob

def crear_pared(esc, x0, m3d, col_):
    c = esc.get("color_pared") or "crema"
    ob = nuevo_gp(f"Pared_{esc['id']}", col_, profundidad3d=m3d)
    lp = Lapiz(ob, "pared")
    if m3d:
        y = 6.0; Wd = 26
        lp.forma([(-Wd / 2, y, 0), (Wd / 2, y, 0), (Wd / 2, y, 9), (-Wd / 2, y, 9)], f"Relleno {c}", radio=R)
        for s in (-1, 1):
            lp.forma([(s * Wd / 2, y, 0), (s * Wd / 2, -14, 0), (s * Wd / 2, -14, 9), (s * Wd / 2, y, 9)], f"Semitono {c}-", radio=R)
        for k in range(-12, 13):
            lp.linea([(k, y - 0.01, 0.35), (k, y - 0.01, 9)], f"Trazo {c}-", radio=0.04)
        lp.forma([(-Wd / 2, y - 0.02, 0), (Wd / 2, y - 0.02, 0), (Wd / 2, y - 0.02, 0.35), (-Wd / 2, y - 0.02, 0.35)], "Relleno blanco", radio=R2)
        ob.location = (x0, 0, 0)
    else:
        lp.forma(rect(-60, 0, 60, 40), f"Relleno {c}", radio=R)
        for k in range(-60, 61):
            lp.linea([P(k * 1.0, 0.35), P(k * 1.0, 40)], f"Trazo {c}-", radio=0.04)
        lp.forma(rect(-60, 0, 60, 0.35), "Relleno blanco", radio=R2)
        ob.location = (x0, 8.0, 0)
    ob["comic_tipo"] = "cielo"
    return ob

SUELOS = {"cesped": ("verde", "verde_oscuro"), "calle": ("gris_oscuro", "amarillo"), "arena": ("oro", "mandarina"),
          "nieve": ("blanco", "celeste+"), "agua": ("azul", "blanco"), "madera": ("marron", "chocolate"), "luna": ("gris", "gris_oscuro")}

def crear_suelo(esc, x0, m3d, col_):
    tipo = esc["suelo"]; c, c2 = SUELOS[tipo]
    ob = nuevo_gp(f"Suelo_{esc['id']}", col_, profundidad3d=m3d)
    lp = Lapiz(ob, "suelo"); ld = Lapiz(ob, "detalles")
    rnd = random.Random(esc["id"] + tipo)
    if m3d:
        Rr = 70
        lp.forma([(-Rr, -Rr, 0), (Rr, -Rr, 0), (Rr, Rr, 0), (-Rr, Rr, 0)], f"Semitono plano {c}" if tipo in ("arena", "nieve", "luna") else f"Plano {c}", linea=False)
        if tipo == "cesped":
            for k in range(-20, 20):
                ld.forma([(-Rr, k * 3.0, 0.005), (Rr, k * 3.0, 0.005), (Rr, k * 3.0 + 1.5, 0.005), (-Rr, k * 3.0 + 1.5, 0.005)], f"Plano {c}+", linea=False)
            for k in range(120):
                x, yy = rnd.uniform(-30, 30), rnd.uniform(-12, 25)
                ld.linea([(x - 0.12, yy, 0.01), (x, yy, 0.2), (x + 0.12, yy, 0.01)], f"Trazo {c2}", radio=0.025)
        elif tipo == "calle":
            ld.forma([(-Rr, -2.2, 0.01), (Rr, -2.2, 0.01), (Rr, 3.5, 0.01), (-Rr, 3.5, 0.01)], "Plano gris_claro", linea=False)
            for k in range(-35, 35):
                ld.linea([(k * 2.0, -2.2, 0.02), (k * 2.0, 3.5, 0.02)], "Trazo gris", radio=0.03)
                ld.forma([(k * 4.0, -6.1, 0.02), (k * 4.0 + 2, -6.1, 0.02), (k * 4.0 + 2, -5.8, 0.02), (k * 4.0, -5.8, 0.02)], "Plano amarillo", linea=False)
            ld.linea([(-Rr, -2.2, 0.03), (Rr, -2.2, 0.03)], radio=0.05)
        elif tipo == "madera":
            for k in range(-20, 20):
                ld.linea([(-Rr, k * 0.7, 0.01), (Rr, k * 0.7, 0.01)], f"Trazo {c2}", radio=0.03)
        elif tipo == "agua":
            for k in range(160):
                x, yy = rnd.uniform(-40, 40), rnd.uniform(-20, 40)
                ld.linea([(x + u, yy, 0.02 + 0.0 * u) for u in (-0.4, -0.2, 0, 0.2, 0.4)], "Trazo blanco", radio=0.04)
        elif tipo in ("arena", "luna", "nieve"):
            for k in range(60):
                x, yy = rnd.uniform(-30, 30), rnd.uniform(-12, 30); r = rnd.uniform(0.2, 0.6)
                ld.forma([(x + r * math.cos(a), yy + r * 0.8 * math.sin(a), 0.01) for a in [2 * math.pi * i / 12 for i in range(12)]],
                         f"Plano {c2}" if tipo != "nieve" else "Plano celeste+", linea=False)
        ob.location = (x0, 0, 0)
    else:
        base = rect(-160, -40, 160, 0.0)
        lp.forma(base, f"Semitono plano {c}" if tipo in ("arena", "nieve", "luna") else f"Plano {c}", linea=False)
        lp.linea([P(-160, 0), P(160, 0)], radio=0.04)
        if tipo == "cesped":
            for k in range(8):
                z = -0.6 - k * 1.3
                ld.forma(rect(-160, z - 0.5, 160, z), f"Plano {c}+", linea=False)
            for k in range(140):
                x, z = rnd.uniform(-40, 40), rnd.uniform(-8, -0.2)
                ld.linea([P(x - 0.1, z), P(x, z + 0.18), P(x + 0.1, z)], f"Trazo {c2}", radio=0.022)
        elif tipo == "calle":
            ld.forma(rect(-160, -1.0, 160, 0), "Plano gris_claro", linea=False)
            ld.linea([P(-160, -1.0), P(160, -1.0)], radio=0.04)
            for k in range(-80, 80):
                ld.linea([P(k * 1.2, -1.0), P(k * 1.2, 0)], "Trazo gris", radio=0.025)
                ld.forma(rect(k * 3.0, -3.3, k * 3.0 + 1.5, -3.1), "Plano amarillo", linea=False)
        elif tipo == "madera":
            for k in range(1, 12): ld.linea([P(-160, -k * 0.6), P(160, -k * 0.6)], f"Trazo {c2}", radio=0.03)
        elif tipo == "agua":
            for k in range(120):
                x, z = rnd.uniform(-40, 40), rnd.uniform(-8, -0.3)
                ld.linea([P(x + u, z + 0.08 * math.sin(u * 8)) for u in (-0.4, -0.2, 0, 0.2, 0.4)], "Trazo blanco", radio=0.035)
        else:
            for k in range(70):
                x, z = rnd.uniform(-40, 40), rnd.uniform(-8, -0.3); r = rnd.uniform(0.12, 0.4)
                ld.forma(elipse(x, z, r, r * 0.4, 12), f"Plano {c2}" if tipo != "nieve" else "Plano celeste+", linea=False)
        ob.location = (x0, 30, 0)
    ob["comic_tipo"] = "suelo"
    return ob
