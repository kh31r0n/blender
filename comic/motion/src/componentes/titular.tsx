// Titular cinetico: mayusculas muy gruesas, cada palabra aparece cuando la dice la voz; las palabras clave en el color
// del panel (con bloque de color detras si `bloque`), como «SALEN LOS BOLETOS» o «SE TRABA» en los shorts.
import {Layout, Node, Rect, Txt} from '@motion-canvas/2d';
import {all, easeOutBack, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {ajustar, color, F_TITULO, hasta, mayus, P, s, VERTICAL, Zona} from '../estilo';
import {Titular} from '../tipos';

export function titular(t: Titular, z: Zona, inicio: number): {nodo: Node; anima: () => ThreadGenerator} {
  const texto = t.palabras.map((p) => p.t).join(' ');
  const lineas = t.grande || !VERTICAL ? 3 : 2;
  const fs = Math.min(t.grande ? ajustar(texto, z.w, 3, 66, 116) : ajustar(texto, z.w, lineas, 46, 86),
                      Math.floor(z.h / (lineas * 1.16)));         // que quepa tambien en alto
  const col = color(t.color);
  const palabras: Node[] = [];
  const caja = (
    <Layout layout direction={'row'} wrap={'wrap'} justifyContent={'center'} alignItems={'center'}
            gap={[fs * 0.3, fs * 0.08]} width={z.w} x={z.x} y={z.y} />
  ) as Layout;
  for (const p of t.palabras) {
    const fill = p.clave ? (t.bloque ? P.fondo : col) : P.texto;
    const txt = <Txt text={mayus(p.t)} fontFamily={F_TITULO} fontSize={fs} fill={fill} lineHeight={fs * 1.08} />;
    const nodo = p.clave && t.bloque
      ? <Rect layout fill={col} padding={[fs * 0.02, fs * 0.16]} radius={4}>{txt}</Rect>
      : txt;
    nodo.opacity(0);
    nodo.scale(0.82);
    caja.add(nodo);
    palabras.push(nodo);
  }
  function* anima(): ThreadGenerator {
    const hilos = t.palabras.map((p, i) => (function* () {
      yield* hasta(Math.max(p.f, inicio + 6));
      yield* all(palabras[i].opacity(1, s(4), easeOutCubic), palabras[i].scale(1, s(6), easeOutBack));
    })());
    yield* all(...hilos);
  }
  return {nodo: caja, anima};
}
