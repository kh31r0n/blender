// Miniaturas (thumbnails) del video: un fotograma por variante. Fondo: el render de la maqueta (b_miniatura.py); encima,
// el titular en mayusculas muy gruesas (las palabras clave en el color de la variante) y la cifra clave en una pastilla.
// Vertical: titular arriba y cifra a la derecha, todo dentro del recorte central 3:4 (Reels, grid de Instagram).
// Horizontal: titular y cifra en la columna izquierda. Lo construye agente_comic.modo_miniatura (motion.json).
import {Img, Layout, makeScene2D, Node, Rect, Txt} from '@motion-canvas/2d';
import {ajustar, color, D, F_TITULO, hasta, mayus, P} from '../estilo';

export default makeScene2D(function* (view) {
  const M = D.miniaturas!;
  const vertical = D.alto > D.ancho;
  const raiz = <Node /> as Node;
  view.add(raiz);
  for (let i = 0; i < M.variantes.length; i++) {
    yield* hasta(i);
    raiz.removeChildren();
    const v = M.variantes[i];
    const col = color(v.color);
    raiz.add(<Img src={M.fondo} width={D.ancho} height={D.alto} />);
    // titular: palabra a palabra para colorear las claves; contorno del color de fondo del tema (se lee sobre todo)
    const palabras = v.titular.split(/\s+/).filter((w) => w);
    const claves = new Set(v.clave.map((c) => c.toLocaleLowerCase('es')));
    const ancho = vertical ? D.ancho * 0.86 : D.ancho * 0.42;
    // Archivo Black en mayusculas es ancha (~0,9 em por letra): la palabra mas larga tiene que caber en una linea
    const larga = Math.max(...palabras.map((w) => w.length));
    const fs = Math.min(ajustar(v.titular, ancho, 3, vertical ? 90 : 80, vertical ? 170 : 146, 0.9),
                        Math.floor(ancho / (larga * 0.9)));
    const caja = (
      <Layout layout direction={'row'} wrap={'wrap'} justifyContent={vertical ? 'center' : 'start'} alignItems={'center'}
              gap={[fs * 0.26, fs * 0.02]} width={ancho}
              x={vertical ? 0 : -D.ancho / 2 + D.ancho * 0.05 + ancho / 2}
              y={vertical ? -D.alto / 2 + D.alto * 0.265 : -D.alto * 0.1} />
    ) as Layout;
    for (const w of palabras) {
      const clave = claves.has(w.toLocaleLowerCase('es').replace(/[¿?¡!.,]/g, '')) || claves.has(w.toLocaleLowerCase('es'));
      caja.add(<Txt text={mayus(w)} fontFamily={F_TITULO} fontSize={fs} lineHeight={fs * 1.02} fill={clave ? col : P.texto}
                    stroke={P.fondo} lineWidth={fs * 0.14} strokeFirst lineJoin={'round'}
                    shadowColor={'rgba(0,0,0,0.25)'} shadowBlur={fs * 0.25} shadowOffset={[0, fs * 0.06]} />);
    }
    raiz.add(caja);
    // donde acaba el titular (la maqueta del layout ya esta calculada al anadirlo): la cifra va justo debajo
    const bajoTitular = caja.y() + caja.height() / 2;
    // cifra clave en una pastilla del color de la variante, con su etiqueta
    if (v.cifra) {
      const fc = vertical ? 150 : 120;
      const pastilla = (
        <Rect layout direction={'column'} alignItems={'center'} fill={col} radius={fc * 0.28} padding={[fc * 0.16, fc * 0.34]}
              shadowColor={'rgba(0,0,0,0.3)'} shadowBlur={fc * 0.35} shadowOffset={[0, fc * 0.1]} rotation={-4}
              x={vertical ? D.ancho * 0.2 : -D.ancho / 2 + D.ancho * 0.05 + fc * 1.6}
              y={bajoTitular + (vertical ? fc * 1.05 : fc * 1.15)}>
          <Txt text={v.cifra} fontFamily={F_TITULO} fontSize={fc} fill={P.fondo} lineHeight={fc * 1.05} />
          {v.etiqueta ? <Txt text={mayus(v.etiqueta)} fontFamily={F_TITULO} fontSize={fc * 0.26} fill={P.fondo} letterSpacing={2} /> : null}
        </Rect>
      ) as Rect;
      raiz.add(pastilla);
    }
    // logo de la marca: horizontal, abajo a la derecha; en vertical, dentro del recorte 3:4 (borde de abajo al 87,5 %).
    // Tal cual: sin sombra, contorno ni efectos (guia de la marca), con margen de proteccion
    if (M.logo) {
      const lw = Math.round(Math.min(D.ancho, D.alto) * (vertical ? 0.24 : 0.17));
      const lh = Math.round(lw * 552 / 2048);
      const margen = Math.round(lh * 0.9);
      const fondoY = vertical ? D.alto * 0.875 : D.alto;
      raiz.add(<Img src={M.logo} width={lw} height={lh} x={D.ancho / 2 - margen - lw / 2} y={-D.alto / 2 + fondoY - margen - lh / 2} />);
    }
  }
  yield* hasta(D.frames);
});
