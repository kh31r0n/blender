// Catalogo cerrado de visuales de los paneles (el mismo que TIPOS_VISUAL en comic_parametros.py). Cada uno se construye
// dentro de su zona (coordenadas de la banda) y devuelve el nodo y su animacion, que arranca en visual.f (cuando la voz
// dice la cifra). Todo aparece en una sola tanda; solo los contadores y los bucles siguen moviendose despues.
import {Circle, Layout, Line, Node, Rect, Txt} from '@motion-canvas/2d';
import {
  all, createSignal, easeInCubic, easeInOutCubic, easeOutBack, easeOutCubic, linear, ThreadGenerator, Vector2,
} from '@motion-canvas/core';
import {aparecer, color, D, F_MONO, F_TITULO, FPS, formato, hasta, mayus, P, s, texto, Zona} from '../estilo';
import {Item, Numero, Panel, Visual} from '../tipos';
import {bucle, fichas} from './banda';

export interface Pieza { nodo: Node; anima: () => ThreadGenerator }

const vacio = (): Pieza => ({nodo: <Node /> as Node, anima: function* () {}});

function etiqueta(t: string, size: number, fill = P.texto, opacidad = 0.75) {
  return <Txt text={mayus(t)} fontFamily={F_MONO} fontWeight={600} fontSize={size} letterSpacing={size * 0.12}
              fill={fill} opacity={opacidad} />;
}

/** cifra que rueda de a a b (en el formato de b) con frenada final */
function cifra(n0: Numero, n1: Numero | undefined, size: number, fill: string) {
  const fin = n1 ?? n0;
  const val = createSignal(n0.v);
  const nodo = <Txt text={() => texto(fin, val())} fontFamily={F_MONO} fontWeight={800} fontSize={size} fill={fill} /> as Txt;
  function* rueda(frames: number): ThreadGenerator {
    if (n1 && n1.v !== n0.v) yield* val(n1.v, s(frames), easeOutCubic);
    yield* nodo.scale(1.08, s(3), easeOutCubic);
    yield* nodo.scale(1, s(5), easeOutCubic);
  }
  return {nodo, rueda};
}

const largo = (n: Numero) => texto(n, n.v).length;

/** frames de un contador: entre 12 y 2,5 s, y como mucho el 60 % de lo que queda de escena */
const durContador = (v: Visual, p: Panel) => Math.max(12, Math.min(Math.round(2.5 * FPS), Math.round(0.6 * (p.fin - v.f_accion))));

// ---------------------------------------------------------------- contador
function contador(v: Visual, z: Zona, p: Panel): Pieza {
  if (!v.valor_num) return tarjeta({...v, tipo: 'tarjeta', titulo: 'estado', items: [{etiqueta: v.etiqueta ?? '', valor: v.valor ?? '', color: v.color ?? 'neutro'}]}, z, p);
  const n0 = v.valor_num, n1 = v.hasta_num;
  const car = Math.max(largo(n0), n1 ? largo(n1) : 0);
  const size = Math.min(z.h * 0.6, (z.w * 0.9) / (car * 0.62), 230);
  const c = cifra(n0, n1, size, color(v.color));
  const nodo = (
    <Layout layout direction={'column'} alignItems={'center'} gap={size * 0.06} x={z.x} y={z.y}>
      {c.nodo}
      {etiqueta(v.etiqueta ?? '', Math.max(28, Math.min(40, size * 0.22)))}
    </Layout>
  ) as Layout;
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo);
    yield* hasta(v.f_accion);
    yield* c.rueda(durContador(v, p));
  }};
}

// ---------------------------------------------------------------- cifras (dos enfrentadas)
function cifras(v: Visual, z: Zona): Pieza {
  const items = (v.items ?? []).slice(0, 2);
  const car = Math.max(...items.map((it) => (it.num ? largo(it.num) : it.valor.length)));
  const size = Math.min(z.h * 0.5, (z.w * 0.42) / (car * 0.62), 190);
  const nodo = <Node x={z.x} y={z.y} /> as Node;
  const cols: Node[] = [];
  items.forEach((it, i) => {
    const col = (
      <Layout layout direction={'column'} alignItems={'center'} gap={10} x={(i === 0 ? -1 : 1) * z.w / 4}>
        <Txt text={it.valor} fontFamily={F_MONO} fontWeight={800} fontSize={size} fill={color(it.color)} />
        {etiqueta(it.etiqueta, Math.max(26, Math.min(36, size * 0.24)))}
      </Layout>
    ) as Layout;
    col.opacity(0);
    nodo.add(col);
    cols.push(col);
  });
  const raya = <Line points={[[0, -z.h * 0.34], [0, z.h * 0.34]]} stroke={P.tenue} lineWidth={3} end={0} /> as Line;
  nodo.add(raya);
  return {nodo, anima: function* () {
    yield* all(aparecer(cols[0]), raya.end(1, s(8), easeOutCubic), (function* () { yield* hasta(v.f + 4); yield* aparecer(cols[1]); })());
  }};
}

// ---------------------------------------------------------------- barras (comparativa)
function barras(v: Visual, z: Zona): Pieza {
  const items = (v.items ?? []).filter((it) => it.num).slice(0, 4);
  const n = items.length;
  const nodo = <Node x={z.x} y={z.y} /> as Node;
  const conRes = !!v.resultado;
  const anchoBarras = conRes ? z.w * 0.6 : z.w;
  const x0 = -z.w / 2 + anchoBarras / 2;
  const top = -z.h / 2 + (v.titulo ? 56 : 10), base = z.h / 2 - 44;
  const maxv = Math.max(...items.map((it) => Math.abs(it.num!.v))) * 1.08 || 1;
  const hueco = anchoBarras / n;
  const ancho = Math.min(150, hueco * 0.52);
  const altoMax = base - top - 58;
  if (v.titulo) {
    nodo.add(
      <Layout layout direction={'row'} alignItems={'center'} gap={12} x={-z.w / 2} y={-z.h / 2 + 14} offset={[-1, 0]}>
        <Rect width={18} height={18} fill={color(items[n - 1]?.color)} />
        {etiqueta(v.titulo, 28, P.texto, 0.9)}
      </Layout>,
    );
  }
  nodo.add(<Line points={[[x0 - anchoBarras / 2, base], [x0 + anchoBarras / 2, base]]} stroke={P.texto} lineWidth={3} opacity={0.6} />);
  const crecen: (() => ThreadGenerator)[] = [];
  items.forEach((it, i) => {
    const x = x0 - anchoBarras / 2 + hueco * (i + 0.5);
    const h = (Math.abs(it.num!.v) / maxv) * altoMax;
    const barra = <Rect x={x} y={base} offset={[0, 1]} width={ancho} height={0} fill={color(it.color)} /> as Rect;
    const val = createSignal(0);
    const cifraT = <Txt text={() => texto(it.num!, val())} fontFamily={F_MONO} fontWeight={800} fontSize={Math.min(50, hueco * 0.24)}
                        fill={color(it.color)} x={x} y={() => base - barra.height() - 30} opacity={0} /> as Txt;
    const lab = <Txt text={mayus(it.etiqueta)} fontFamily={F_MONO} fontWeight={600} fontSize={Math.min(30, hueco * 0.13)} letterSpacing={2}
                     fill={P.texto} opacity={0.8} x={x} y={base + 28} /> as Txt;
    nodo.add(barra); nodo.add(cifraT); nodo.add(lab);
    crecen.push(function* () {
      yield* all(cifraT.opacity(1, s(5)), barra.height(h, s(14), easeOutCubic), val(it.num!.v, s(14), easeOutCubic));
    });
  });
  let res: Txt | null = null;
  if (conRes) {
    res = <Txt text={v.resultado!} fontFamily={F_TITULO} fontSize={Math.min(z.h * 0.46, (z.w * 0.38) / (v.resultado!.length * 0.66))}
               fill={P.bueno} x={z.w / 2 - z.w * 0.2} y={(top + base) / 2} opacity={0} scale={0.6} /> as Txt;
    nodo.add(res);
  }
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 16, 6);
    yield* all(...crecen.map((g, i) => (function* () { yield* hasta(v.f_accion + i * 6); yield* g(); })()));
    if (res) yield* all(res.opacity(1, s(5)), res.scale(1, s(9), easeOutBack));
  }};
}

// ---------------------------------------------------------------- linea (1-2 series, punto a punto)
function linea(v: Visual, z: Zona): Pieza {
  const series = (v.items ?? []).filter((it) => (it.puntos ?? []).length >= 2).slice(0, 2);
  const nodo = <Node x={z.x} y={z.y} /> as Node;
  const izq = -z.w / 2 + 20, der = z.w / 2 - 20, top = -z.h / 2 + 64, base = z.h / 2 - 20;
  const todos = series.flatMap((it) => it.puntos!);
  const lo = Math.min(...todos), hi = Math.max(...todos);
  const py = (y: number) => base - ((y - lo) / (hi - lo || 1)) * (base - top) * 0.9 - (base - top) * 0.05;
  nodo.add(<Line points={[[izq, top], [izq, base], [der, base]]} stroke={P.texto} lineWidth={3} opacity={0.6} />);
  for (let k = 1; k <= 3; k++) {
    const y = base - (k / 4) * (base - top);
    nodo.add(<Line points={[[izq, y], [der, y]]} stroke={P.tenue} lineWidth={2} lineDash={[8, 10]} />);
  }
  const ley = <Layout layout direction={'column'} gap={6} x={izq} y={-z.h / 2 + 10} offset={[-1, -1]} /> as Layout;
  nodo.add(ley);
  if (v.titulo) ley.add(etiqueta(v.titulo, 22, P.texto, 0.6));
  const trazos: (() => ThreadGenerator)[] = [];
  series.forEach((it) => {
    const pts = it.puntos!;
    const xy = pts.map((y, i) => new Vector2(izq + 30 + (i / (pts.length - 1)) * (der - izq - 60), py(y)));
    const l = <Line points={xy} stroke={color(it.color)} lineWidth={6} end={0} lineCap={'round'} lineJoin={'round'} /> as Line;
    const puntos = xy.map((q) => <Circle position={q} size={18} fill={color(it.color)} scale={0} /> as Circle);
    nodo.add(l); puntos.forEach((c) => nodo.add(c));
    ley.add(<Layout layout direction={'row'} alignItems={'center'} gap={10}>
      <Line points={[[0, 0], [34, 0]]} stroke={color(it.color)} lineWidth={6} />
      {etiqueta(it.etiqueta, 24, color(it.color), 1)}
    </Layout>);
    trazos.push(function* () {
      const dur = Math.round(1.2 * FPS);
      yield* all(l.end(1, s(dur), linear),
                 ...puntos.map((c, i) => (function* () { yield* hasta(v.f_accion + Math.round((i / Math.max(1, puntos.length - 1)) * dur)); yield* c.scale(1, s(5), easeOutBack); })()));
    });
  });
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 16, 6);
    yield* hasta(v.f_accion);
    yield* all(...trazos.map((g) => g()));
  }};
}

// ---------------------------------------------------------------- unidades («12 DE CADA 100»)
function unidades(v: Visual, z: Zona): Pieza {
  const total = v.total ?? 100;
  const marcados = Math.round(v.valor_num?.v ?? 0);
  const cols = 10, filas = Math.ceil(total / cols);
  const paso = Math.min((z.h * 0.92) / filas, (z.w * 0.48) / cols);
  const nodo = <Node x={z.x} y={z.y} /> as Node;
  const gx = -z.w / 2 + paso * cols / 2 + 10;
  const puntos: Circle[] = [];
  for (let i = 0; i < total; i++) {
    const c = <Circle x={gx + (i % cols - (cols - 1) / 2) * paso} y={(Math.floor(i / cols) - (filas - 1) / 2) * paso}
                      size={paso * 0.62} fill={P.tenue} opacity={0} /> as Circle;
    nodo.add(c); puntos.push(c);
  }
  const sizeN = Math.min(z.h * 0.42, (z.w * 0.4) / (String(marcados).length * 0.62));
  const lado = (
    <Layout layout direction={'column'} alignItems={'start'} gap={6} x={z.w / 2 - z.w * 0.24} offset={[0, 0]}>
      <Txt text={String(marcados)} fontFamily={F_MONO} fontWeight={800} fontSize={sizeN} fill={color(v.color)} />
      {etiqueta(`de cada ${total}`, 32, P.texto, 0.9)}
      {etiqueta(v.etiqueta ?? '', 26, P.texto, 0.7)}
    </Layout>
  ) as Layout;
  lado.opacity(0);
  nodo.add(lado);
  return {nodo, anima: function* () {
    yield* all(...puntos.map((c) => c.opacity(1, s(6))), aparecer(lado));
    const dur = Math.round(0.8 * FPS);
    yield* all(...puntos.slice(0, marcados).map((c, i) => (function* () {
      yield* hasta(v.f_accion + Math.round((i / Math.max(1, marcados)) * dur));
      c.fill(color(v.color));
      yield* c.scale(1.25, s(2)); yield* c.scale(1, s(3));
    })()));
  }};
}

// ---------------------------------------------------------------- pasos (fichas grandes del ciclo)
function pasos(v: Visual, z: Zona, p: Panel): Pieza {
  const lista = v.pasos ?? [];
  if (!lista.length) return vacio();
  const conContador = !!(v.rapido && v.valor_num);
  const f = fichas(lista, z.w, true);
  f.nodo.y(z.y - (conContador ? z.h * 0.18 : 0));
  const nodo = <Node x={z.x} /> as Node;
  nodo.add(f.nodo);
  f.pon(0, v.hechos ?? []);
  let c: ReturnType<typeof cifra> | null = null;
  let cont: Layout | null = null;
  if (conContador) {
    const n0 = v.valor_num!, n1 = v.hasta_num;
    const car = Math.max(largo(n0), n1 ? largo(n1) : 0);
    c = cifra(n0, n1, Math.min(z.h * 0.3, (z.w * 0.6) / (car * 0.62), 120), color(v.color));
    cont = <Layout layout direction={'row'} alignItems={'center'} gap={18} y={z.y + z.h * 0.3}>
      {c.nodo}
      {etiqueta(v.etiqueta ?? '', 30)}
    </Layout> as Layout;
    nodo.add(cont);
  }
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 16, 6);
    if (v.rapido) {
      const a = p.inicio + Math.round(0.1 * (p.fin - p.inicio));
      const zf = p.fin - Math.round(0.1 * (p.fin - p.inicio));
      yield* all(bucle(f, p.inicio, p.fin),
                 c ? (function* () { yield* hasta(a); yield* c!.rueda(Math.max(12, zf - a)); })() : (function* () {})());
    } else {
      yield* hasta(v.f_accion);
      f.pon(v.activo ?? 0, v.hechos ?? []);
    }
  }};
}

// ---------------------------------------------------------------- tarjeta (el registro de ejemplo del caso)
function tarjeta(v: Visual, z: Zona, _p?: Panel): Pieza {
  const items = (v.items ?? []).slice(0, 4);
  const w = Math.min(z.w, 820);
  const fila = Math.min(108, (z.h - 96) / Math.max(1, items.length));
  const h = 72 + fila * items.length + 18;
  const tinta = P.fondo;
  const nodo = (
    <Rect x={z.x} y={z.y} width={w} height={h} radius={10} fill={P.texto}
          shadowColor={'#00000088'} shadowBlur={30} shadowOffset={[0, 12]} />
  ) as Rect;
  // barra de titulo con los tres puntos (como las ventanas de los shorts)
  nodo.add(<Rect y={-h / 2 + 30} width={w} height={60} radius={[10, 10, 0, 0]} fill={'#00000010'} />);
  [P.problema, P.acento, P.bueno].forEach((c, i) => nodo.add(<Circle x={-w / 2 + 32 + i * 28} y={-h / 2 + 30} size={18} fill={c} />));
  nodo.add(<Txt text={v.titulo ?? ''} fontFamily={F_MONO} fontWeight={700} fontSize={28} fill={tinta} x={-w / 2 + 120} y={-h / 2 + 30} offset={[-1, 0]} />);
  nodo.add(<Line points={[[-w / 2, -h / 2 + 60], [w / 2, -h / 2 + 60]]} stroke={tinta} lineWidth={2} opacity={0.25} />);
  const lineas: (() => ThreadGenerator)[] = [];
  const largo = Math.max(...items.map((it) => it.etiqueta.length + 1 + it.valor.length), 8);
  const fs = Math.min(44, fila * 0.5, (w - 120) / (largo * 0.62));      // clave y valor caben en una linea
  items.forEach((it, i) => {
    const y = -h / 2 + 72 + fila * (i + 0.5) + 6;
    const clave = `${it.etiqueta}:`;
    const n = createSignal(0);
    const k = <Txt text={() => clave.slice(0, Math.round(n()))} fontFamily={F_MONO} fontWeight={500} fontSize={fs} fill={tinta}
                   opacity={0.7} x={-w / 2 + 30} y={y} offset={[-1, 0]} /> as Txt;
    const pill = (
      <Rect layout x={w / 2 - 30} y={y} offset={[1, 0]} padding={[6, 14]} radius={6}
            fill={it.color === 'neutro' ? P.fondo : color(it.color)} opacity={0} scale={0.8}>
        <Txt text={it.valor} fontFamily={F_MONO} fontWeight={800} fontSize={fs} fill={it.color === 'neutro' ? P.texto : P.fondo} />
      </Rect>
    ) as Rect;
    nodo.add(k); nodo.add(pill);
    lineas.push(function* () {
      yield* n(clave.length, s(Math.max(4, Math.round(clave.length * 0.6))), linear);
      yield* all(pill.opacity(1, s(4)), pill.scale(1, s(6), easeOutBack));
    });
  });
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 30, 8);
    yield* all(...lineas.map((g, i) => (function* () { yield* hasta(Math.min(v.f + 8, v.f_accion) + i * 5); yield* g(); })()));
  }};
}

// ---------------------------------------------------------------- medidor (semicirculo con aguja)
function medidor(v: Visual, z: Zona): Pieza {
  const pct = Math.max(0, Math.min(100, v.valor_num?.v ?? 0));
  const r = Math.min(z.h * 0.62, z.w * 0.3);
  const nodo = <Node x={z.x} y={z.y + r * 0.35} /> as Node;
  const marco = <Rect width={r * 2 + 120} height={r + 150} y={-r / 2 + 10} radius={12} stroke={P.tenue} lineWidth={2} /> as Rect;
  nodo.add(marco);
  nodo.add(<Txt text={mayus(v.etiqueta ?? '')} fontFamily={F_MONO} fontWeight={700} fontSize={26} letterSpacing={3} fill={P.texto}
                opacity={0.7} x={-r - 44} y={-r - 40} offset={[-1, 0]} />);
  nodo.add(<Circle size={r * 2} startAngle={180} endAngle={360} stroke={P.tenue} lineWidth={18} />);
  const arco = createSignal(0);
  nodo.add(<Circle size={r * 2} startAngle={180} endAngle={() => 180 + 180 * arco()} stroke={color(v.color)} lineWidth={18} />);
  const aguja = <Line points={[[0, 0], [r * 0.82, 0]]} stroke={P.texto} lineWidth={6} lineCap={'round'} rotation={180} /> as Line;
  nodo.add(aguja);
  nodo.add(<Circle size={24} fill={P.texto} />);
  const val = createSignal(0);
  nodo.add(<Txt text={() => texto(v.valor_num!, val())} fontFamily={F_MONO} fontWeight={800} fontSize={r * 0.42} fill={color(v.color)} y={r * 0.32} />);
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 20, 6);
    yield* hasta(v.f_accion);
    const d = s(Math.round(1.1 * FPS));
    yield* all(arco(pct / 100, d, easeInOutCubic), aguja.rotation(180 + 180 * pct / 100, d, easeInOutCubic), val(pct, d, easeInOutCubic));
  }};
}

// ---------------------------------------------------------------- cola (fichas que se apilan o se vacian)
function cola(v: Visual, z: Zona, p: Panel): Pieza {
  const a = Math.round(v.valor_num?.v ?? 0), b = Math.round(v.hasta_num?.v ?? a);
  const tope = 40;
  const maximo = Math.max(1, a, b);
  const n = Math.min(tope, maximo);                       // cada ficha vale maximo / n unidades
  const cols = 8, filas = Math.ceil(tope / cols);
  const lado = Math.min((z.h * 0.9) / filas, (z.w * 0.55) / cols);
  const nodo = <Node x={z.x} y={z.y} /> as Node;
  const gx = -z.w / 2 + lado * cols / 2 + 10;
  const bio = D.icono_flujo === 'biohazard';
  const tonos = [P.problema, P.acento, P.bueno, P.espera];
  const val = createSignal(a);
  for (let i = 0; i < n; i++) {
    const x = gx + (i % cols - (cols - 1) / 2) * lado, y = (filas - 1) / 2 * lado - Math.floor(i / cols) * lado;
    const u = () => Math.max(0, Math.min(1, (n * val()) / maximo - i));      // 0 = vacia, 1 = llena
    const c = bio
      ? <Node x={x} y={y} opacity={u} scale={() => 0.4 + 0.6 * u()}>
          <Circle size={lado * 0.78} stroke={tonos[i % 4]} lineWidth={4} />
          {[0, 120, 240].map((ang) => <Circle size={lado * 0.26} fill={tonos[i % 4]}
                                             position={Vector2.fromDegrees(ang - 90).scale(lado * 0.2)} />)}
        </Node>
      : <Rect x={x} y={y} size={lado * 0.74} radius={lado * 0.18} fill={color(v.color)} opacity={u} scale={() => 0.4 + 0.6 * u()} />;
    nodo.add(c);
  }
  const sizeN = Math.min(z.h * 0.4, (z.w * 0.36) / (String(maximo).length * 0.62));
  const lat = (
    <Layout layout direction={'column'} alignItems={'start'} gap={6} x={z.w / 2 - z.w * 0.2}>
      <Txt text={() => formato(Math.round(val()), 0)} fontFamily={F_MONO} fontWeight={800} fontSize={sizeN} fill={color(v.color)} />
      {etiqueta(v.etiqueta ?? '', 28, P.texto, 0.8)}
    </Layout>
  ) as Layout;
  nodo.add(lat);
  nodo.opacity(0);
  return {nodo, anima: function* () {
    yield* aparecer(nodo, 16, 6);
    yield* hasta(v.f_accion);
    if (a !== b) yield* val(b, s(durContador(v, p)), easeInOutCubic);
  }};
}

export function visual(v: Visual, z: Zona, p: Panel): Pieza {
  switch (v.tipo) {
    case 'contador': return contador(v, z, p);
    case 'cifras': return cifras(v, z);
    case 'barras': return barras(v, z);
    case 'linea': return linea(v, z);
    case 'unidades': return unidades(v, z);
    case 'pasos': return pasos(v, z, p);
    case 'tarjeta': return tarjeta(v, z, p);
    case 'medidor': return medidor(v, z);
    case 'cola': return cola(v, z, p);
    default: return vacio();
  }
}

export type {Item};
