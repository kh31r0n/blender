// Escena unica: la banda aparece en cada tramo (escenas seguidas con panel) y cada panel monta su titular (palabra a
// palabra con la voz), su visual (cuando se dice su cifra) y la cinta de pasos. Fotogramas absolutos de motion.json.
import {makeScene2D, Node} from '@motion-canvas/2d';
import {all, easeInCubic, ThreadGenerator} from '@motion-canvas/core';
import {banda, bucle, cinta, Fichas} from '../componentes/banda';
import {titular} from '../componentes/titular';
import {visual} from '../componentes/visuales';
import {BH, BW, D, hasta, s, zonas} from '../estilo';
import {Panel, Tramo} from '../tipos';

export default makeScene2D(function* (view) {
  // origen en el centro de la banda (coordenadas de Motion Canvas: centro del cuadro, y hacia abajo)
  const raiz = <Node x={D.banda.x + BW / 2 - D.ancho / 2} y={D.banda.y + BH / 2 - D.alto / 2} /> as Node;
  view.add(raiz);
  const tramoDe = (p: Panel) => D.tramos.find((t) => p.inicio >= t.inicio && p.inicio <= t.fin)!;

  function* tramo(t: Tramo): ThreadGenerator {
    yield* hasta(t.inicio);
    const b = banda();
    raiz.add(b.nodo);
    b.nodo.zIndex(0);
    // cinta de pasos: una por tramo, cambia de estado con cada panel que la lleva
    const conCinta = D.paneles.filter((p) => p.cinta && p.inicio >= t.inicio && p.inicio <= t.fin);
    let fichas: Fichas | null = null;
    if (conCinta.length) {
      fichas = cinta(conCinta[0].cinta!);
      fichas.nodo.opacity(0);
      fichas.nodo.zIndex(1);
      raiz.add(fichas.nodo);
    }
    const hilos: ThreadGenerator[] = [];
    if (fichas) {
      const f = fichas;
      hilos.push((function* () {
        for (const p of D.paneles.filter((q) => q.inicio >= t.inicio && q.inicio <= t.fin)) {
          yield* hasta(p.inicio + 2);
          if (!p.cinta) { yield* f.nodo.opacity(0, s(5)); continue; }
          f.pon(p.cinta.activo, p.cinta.hechos);
          if (f.nodo.opacity() < 1) yield* f.nodo.opacity(1, s(6));
          if (p.cinta.rapido) yield* bucle(f, p.inicio, p.fin);
        }
      })());
    }
    if (t.entra) yield* b.entra(); else b.llena();
    if (t.sale) {
      yield* all(...hilos, (function* () {
        yield* hasta(t.fin - 8);
        if (fichas) yield* fichas.nodo.opacity(0, s(4));
      })());
      yield* hasta(t.fin - 8);
      yield* b.sale();
      b.nodo.remove();
      fichas?.nodo.remove();
    } else {
      yield* all(...hilos);
    }
  }

  function* panel(p: Panel): ThreadGenerator {
    yield* hasta(p.inicio);
    const t = tramoDe(p);
    const cont = <Node /> as Node;
    cont.zIndex(2);
    raiz.add(cont);
    const z = zonas(p);
    const tit = titular(p.titular, z.titular, t.entra && p.inicio === t.inicio ? p.inicio + 8 : p.inicio);
    const vis = visual(p.visual, z.visual, p);
    cont.add(tit.nodo);
    cont.add(vis.nodo);
    // el panel se va 5 fotogramas antes de su fin (o antes de que se recoja la banda si es el ultimo del tramo)
    const salida = t.sale && p.fin === t.fin ? t.fin - 12 : p.fin - 4;
    yield* all(
      tit.anima(),
      (function* () { yield* hasta(Math.max(p.visual.f, p.inicio + 6)); yield* vis.anima(); })(),
      (function* () { yield* hasta(salida - 5); yield* cont.opacity(0, s(5), easeInCubic); cont.remove(); })(),
    );
  }

  for (const t of D.tramos) yield tramo(t);
  for (const p of D.paneles) yield panel(p);
  yield* hasta(D.frames);
});
