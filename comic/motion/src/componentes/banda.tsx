// Banda de los paneles: fondo oscuro propio con rejilla tenue, degradado hacia la maqueta y filo de acento. En vertical
// ocupa la parte de arriba del cuadro y crece hacia abajo; en horizontal, la columna izquierda y crece hacia la derecha.
// La cinta de pasos (fichas pequenas del ciclo) vive en la banda y cambia de estado con cada panel.
import {Gradient, Line, Node, Rect, Txt} from '@motion-canvas/2d';
import {createSignal, easeInCubic, easeOutCubic, SimpleSignal, ThreadGenerator, all} from '@motion-canvas/core';
import {ALTO_CINTA, BH, BW, color, F_MONO, F_TITULO, filasCinta, FPS, hasta, mayus, P, PAD, s, VERTICAL} from '../estilo';
import {Cinta} from '../tipos';

const transparente = (hex: string) => hex + '00';

export function banda(): {nodo: Node; entra: () => ThreadGenerator; sale: () => ThreadGenerator; llena: () => void} {
  const nodo = <Node /> as Node;
  const tam = createSignal(0);            // 0..1 de la banda desplegada
  const fondo = (
    <Rect fill={P.fondo} clip
          offset={VERTICAL ? [0, -1] : [-1, 0]}
          position={VERTICAL ? [0, -BH / 2] : [-BW / 2, 0]}
          width={() => (VERTICAL ? BW : BW * tam())}
          height={() => (VERTICAL ? BH * tam() : BH)} />
  ) as Rect;
  // rejilla tenue (como el papel milimetrado de los graficos de las referencias)
  const paso = 60;
  for (let x = -BW / 2 + paso; x < BW / 2; x += paso)
    fondo.add(<Line points={[[x + BW / 2 * (VERTICAL ? 0 : 1), VERTICAL ? 0 : -BH / 2], [x + BW / 2 * (VERTICAL ? 0 : 1), VERTICAL ? BH : BH / 2]]}
                    stroke={P.tenue} lineWidth={1} opacity={0.35} />);
  for (let y = paso; y < BH; y += paso)
    fondo.add(<Line points={VERTICAL ? [[-BW / 2, y], [BW / 2, y]] : [[0, y - BH / 2], [BW, y - BH / 2]]}
                    stroke={P.tenue} lineWidth={1} opacity={0.35} />);
  // degradado hacia la maqueta y filo de acento en el borde
  const largo = 90;
  const borde = VERTICAL
    ? <Rect width={BW} height={largo} y={() => -BH / 2 + BH * tam() + largo / 2}
            fill={new Gradient({type: 'linear', from: [0, -largo / 2], to: [0, largo / 2],
                                stops: [{offset: 0, color: P.fondo}, {offset: 1, color: transparente(P.fondo)}]})} />
    : <Rect width={largo} height={BH} x={() => -BW / 2 + BW * tam() + largo / 2}
            fill={new Gradient({type: 'linear', from: [-largo / 2, 0], to: [largo / 2, 0],
                                stops: [{offset: 0, color: P.fondo}, {offset: 1, color: transparente(P.fondo)}]})} />;
  const filo = VERTICAL
    ? <Rect width={BW} height={3} fill={P.acento} opacity={0.75} y={() => -BH / 2 + BH * tam()} />
    : <Rect width={3} height={BH} fill={P.acento} opacity={0.75} x={() => -BW / 2 + BW * tam()} />;
  nodo.add(borde);
  nodo.add(fondo);
  nodo.add(filo);
  return {
    nodo,
    entra: function* () { yield* tam(1, s(8), easeOutCubic); },
    sale: function* () { yield* tam(0, s(8), easeInCubic); },
    llena: () => tam(1),
  };
}

// ---------------------------------------------------------------- cinta de pasos (abajo de la banda)
type Estado = 0 | 1 | 2;      // apagado, activo, hecho

export interface Fichas { nodo: Node; estados: SimpleSignal<number>[]; pon: (activo: number, hechos: number[]) => void }

/** fichas numeradas del ciclo; `grande` para el visual «pasos», pequenas para la cinta */
export function fichas(pasos: string[], ancho: number, grande: boolean): Fichas {
  const n = pasos.length;
  const filas = grande ? 1 : filasCinta(n);
  const porFila = Math.ceil(n / filas);
  const nodo = <Node /> as Node;
  const estados = pasos.map(() => createSignal<number>(0));
  const hueco = ancho / porFila;
  const r = grande ? Math.min(54, hueco * 0.32) : 17;
  const fsN = grande ? r * 0.95 : 17;
  const largoMax = Math.max(...pasos.map((p) => p.length));
  const fsT = grande ? Math.min(32, (hueco - 12) / (largoMax * 0.78)) : Math.min(21, (hueco - 30) / ((largoMax + 2) * 0.7));
  for (let i = 0; i < n; i++) {
    const fila = Math.floor(i / porFila), col = i % porFila;
    const enFila = fila === filas - 1 ? n - porFila * (filas - 1) : porFila;      // la ultima fila, centrada
    const x = -ancho / 2 + hueco * (col + 0.5) + (porFila - enFila) * hueco / 2;
    const yf = (fila - (filas - 1) / 2) * ALTO_CINTA;
    if (grande && i < n - 1)
      nodo.add(<Line points={[[x + r + 8, 0], [x + hueco - r - 8, 0]]} stroke={P.tenue} lineWidth={3} lineDash={[6, 6]} y={-14} />);
    const e = estados[i];
    const fill = () => (e() === 1 ? P.bueno : 'rgba(0,0,0,0)');
    const borde = () => (e() === 1 ? P.bueno : e() === 2 ? P.espera : P.texto + '33');
    const apagado = P.texto + '66';     // texto al 40 %: se lee, pero no compite con el paso activo
    const tinta = () => (e() === 1 ? P.fondo : e() === 2 ? P.espera : apagado);
    if (grande) {
      nodo.add(
        <Node x={x} y={-14} scale={() => (e() === 1 ? 1.16 : 1)}>
          <Rect size={r * 2} radius={r} fill={fill} stroke={borde} lineWidth={4} />
          <Txt text={String(i + 1)} fontFamily={F_TITULO} fontSize={fsN} fill={tinta} />
          <Txt text={mayus(pasos[i])} fontFamily={F_MONO} fontWeight={700} fontSize={fsT} letterSpacing={2}
               fill={() => (e() === 0 ? apagado : e() === 1 ? P.bueno : P.texto)} y={r + 34} />
        </Node>,
      );
    } else {
      nodo.add(
        <Rect x={x} y={yf} width={hueco - 14} height={ALTO_CINTA - 18} radius={(ALTO_CINTA - 18) / 2} fill={fill} stroke={borde} lineWidth={2}>
          <Txt text={`${i + 1} ${mayus(pasos[i])}`} fontFamily={F_MONO} fontWeight={700} fontSize={fsT} letterSpacing={1} fill={tinta} />
        </Rect>,
      );
    }
  }
  const pon = (activo: number, hechos: number[]) =>
    estados.forEach((e, i) => e(i + 1 === activo ? 1 : hechos.includes(i + 1) ? 2 : 0));
  return {nodo, estados, pon};
}

/** ciclo rapido: el bucle de pasos se repite cada vez mas deprisa (0,5 s por paso y x0,72 por vuelta), del 10 al 90 % */
export function* bucle(f: Fichas, inicio: number, fin: number): ThreadGenerator {
  const n = f.estados.length;
  const a = inicio + Math.round(0.1 * (fin - inicio));
  const z = fin - Math.round(0.1 * (fin - inicio));
  let d = 0.5 * FPS;
  let t = a;
  yield* hasta(a);
  while (t < z) {
    for (let i = 1; i <= n && t < z; i++) {
      const dd = Math.max(3, Math.round(d));
      f.pon(i, Array.from({length: n}, (_, k) => k + 1).filter((k) => k !== i));
      t += dd;
      yield* hasta(t);
    }
    d *= 0.72;
  }
  f.pon(0, Array.from({length: n}, (_, k) => k + 1));
}

export function cinta(c: Cinta): Fichas {
  const f = fichas(c.pasos, BW - 2 * PAD, false);
  f.nodo.y(BH / 2 - PAD / 2 - (ALTO_CINTA * filasCinta(c.pasos.length)) / 2 + 6);
  return f;
}
