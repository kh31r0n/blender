// Subtitulos: un bloque de 3-6 palabras cada vez, en mayusculas gruesas con contorno oscuro, en el tercio inferior; la
// palabra que suena se enciende en el color 'bueno' del tema (lima en cyberpunk). Fotogramas absolutos de motion.json
// (comic/subtitulos_mc.py): cada bloque entra en `inicio`, cada palabra se enciende en su `f` y el bloque se va en `fin`.
import {Layout, makeScene2D, Txt} from '@motion-canvas/2d';
import {all, easeInCubic, easeOutCubic, ThreadGenerator} from '@motion-canvas/core';
import {D, F_TITULO, hasta, mayus, P, s} from '../estilo';
import {Bloque} from '../tipos';

// contorno del color de fondo del tema: letras claras con borde oscuro en los temas oscuros, y al reves en los claros
const CONTORNO = P.fondo;

export default makeScene2D(function* (view) {
  const S = D.subtitulos!;

  function* bloque(b: Bloque): ThreadGenerator {
    const caja = (
      <Layout layout direction={'row'} wrap={'wrap'} justifyContent={'center'} alignItems={'center'}
              gap={[S.fs * 0.32, S.fs * 0.02]} width={S.ancho} x={S.x - D.ancho / 2} y={S.y - D.alto / 2} />
    ) as Layout;
    const txts = b.palabras.map((p) => (
      <Txt text={mayus(p.t)} fontFamily={F_TITULO} fontSize={S.fs} lineHeight={S.fs * 1.1} fill={P.texto}
           stroke={CONTORNO} lineWidth={S.fs * 0.2} strokeFirst lineJoin={'round'}
           shadowColor={'rgba(0,0,0,0.35)'} shadowBlur={S.fs * 0.3} shadowOffset={[0, S.fs * 0.05]} />
    ) as Txt);
    for (const t of txts) caja.add(t);
    view.add(caja);
    caja.opacity(0);
    const y0 = caja.y();
    caja.y(y0 + S.fs * 0.2);
    const entra = Math.min(3, Math.max(1, b.fin - b.inicio - 3));
    yield* all(
      caja.opacity(1, s(entra), easeOutCubic),
      caja.y(y0, s(entra), easeOutCubic),
      (function* () {
        // la palabra activa, en el color 'bueno' (sin escalarla: invadiria el hueco con la palabra de al lado)
        for (let i = 0; i < b.palabras.length; i++) {
          yield* hasta(b.palabras[i].f);
          if (i > 0) txts[i - 1].fill(P.texto);
          txts[i].fill(P.bueno);
        }
      })(),
    );
    yield* hasta(b.fin - 2);
    yield* caja.opacity(0, s(2), easeInCubic);
    caja.remove();
  }

  for (const b of S.bloques) {
    yield* hasta(b.inicio);
    yield* bloque(b);
  }
  yield* hasta(D.frames);
});
