// Estilo comun de los paneles: tipografia y maquetacion de los shorts de referencia (mayusculas muy gruesas, cifras
// monoespaciadas, etiquetas pequenas con espaciado) con los acentos del tema (motion.json -> paleta).
import {Node} from '@motion-canvas/2d';
import {all, easeOutCubic, ThreadGenerator, usePlayback} from '@motion-canvas/core';
import datos from '@datos';
import {Motion, Numero, Panel} from './tipos';

export const D = datos as Motion;
export const P = D.paleta;
export const FPS = D.fps;
export const VERTICAL = D.orientacion === 'vertical';
export const F_TITULO = 'Archivo Black';
export const F_MONO = 'JetBrains Mono';
export const BW = D.banda.w;
export const BH = D.banda.h;
export const PAD = VERTICAL ? 56 : 48;
export const ALTO_CINTA = 66;
/** filas de la cinta de pasos: dos si en una no caben las fichas (columna estrecha del video horizontal) */
export const filasCinta = (n: number) => ((BW - 2 * PAD) / Math.max(1, n) < 160 ? 2 : 1);

/** segundos de n fotogramas */
export const s = (n: number) => n / FPS;

export function color(c?: string): string {
  return (P as unknown as Record<string, string>)[c ?? 'neutro'] ?? P.neutro;
}

/** espera hasta el fotograma f (0-based) de la reproduccion */
export function* hasta(f: number): ThreadGenerator {
  while (usePlayback().frame < f) yield;
}

/** 16800.5 -> «16.800,5» (formato espanol) */
export function formato(v: number, dec: number): string {
  const neg = v < 0;
  const [ent, frac] = Math.abs(v).toFixed(dec).split('.');
  const miles = ent.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return (neg ? '-' : '') + miles + (frac ? ',' + frac : '');
}

export function texto(n: Numero, v: number): string {
  return `${n.pre}${formato(v, n.dec)}${n.suf}`;
}

export const mayus = (t: string) => t.toLocaleUpperCase('es');

/** caja (centro y tamano, en coordenadas de la banda) donde va cada parte de un panel */
export interface Zona { x: number; y: number; w: number; h: number }

export function zonas(p: Panel): { titular: Zona; visual: Zona } {
  const w = BW - 2 * PAD;
  const top = -BH / 2 + PAD;
  const abajo = BH / 2 - PAD - (p.cinta ? ALTO_CINTA * filasCinta(p.cinta.pasos.length) + 14 : 0);
  if (p.titular.grande) return {titular: {x: 0, y: (top + abajo) / 2, w, h: abajo - top}, visual: {x: 0, y: 0, w: 0, h: 0}};
  const ht = VERTICAL ? 180 : 240;
  const v0 = top + ht + 16;
  return {titular: {x: 0, y: top + ht / 2, w, h: ht}, visual: {x: 0, y: (v0 + abajo) / 2, w, h: abajo - v0}};
}

/** tamano de letra para que el texto quepa en `lineas` lineas de ancho w (Archivo Black ~0.8 em por caracter) */
export function ajustar(txt: string, w: number, lineas: number, min: number, max: number, em = 0.8): number {
  const n = Math.max(4, txt.length);
  return Math.max(min, Math.min(max, Math.floor((w * lineas * 0.92) / (n * em))));
}

/** entrada estandar de un bloque: sube dy px mientras aparece, en `frames` fotogramas */
export function* aparecer(n: Node, dy = 24, frames = 8): ThreadGenerator {
  const y0 = n.y();
  n.y(y0 + dy);
  n.opacity(0);
  yield* all(n.opacity(1, s(frames), easeOutCubic), n.y(y0, s(frames), easeOutCubic));
}
