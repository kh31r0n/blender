// Forma de motion.json (lo escribe comic/paneles_mc.py). Fotogramas 0-based: el f de aqui es el f+1 de Blender.
export interface Numero { pre: string; v: number; suf: string; dec: number }
export interface Item { etiqueta: string; valor: string; color: string; puntos?: number[]; num?: Numero }
export interface Visual {
  tipo: 'ninguno' | 'contador' | 'cifras' | 'barras' | 'linea' | 'unidades' | 'pasos' | 'tarjeta' | 'medidor' | 'cola';
  f: number;            // aparece
  f_accion: number;     // el contador rueda, las barras crecen... (cuando la voz dice la cifra)
  titulo?: string; etiqueta?: string; valor?: string; hasta?: string; resultado?: string; color?: string; total?: number;
  items?: Item[]; valor_num?: Numero; hasta_num?: Numero;
  pasos?: string[]; activo?: number; rapido?: boolean; hechos?: number[];
}
export interface Palabra { t: string; f: number; clave: boolean }
export interface Titular { palabras: Palabra[]; color: string; bloque: boolean; grande: boolean }
export interface Cinta { pasos: string[]; activo: number; hechos: number[]; rapido: boolean }
export interface Panel { escena: number; inicio: number; fin: number; titular: Titular; visual: Visual; cinta: Cinta | null }
export interface Tramo { inicio: number; fin: number; entra: boolean; sale: boolean }
export interface Paleta { fondo: string; texto: string; bueno: string; problema: string; espera: string; neutro: string; tenue: string; acento: string }
// subtitulos (subtitulos_mc.py): un bloque cada vez; cada palabra se enciende en su fotograma f
export interface PalabraSub { t: string; f: number }
export interface Bloque { inicio: number; fin: number; palabras: PalabraSub[] }
export interface Subtitulos { fs: number; ancho: number; x: number; y: number; bloques: Bloque[] }
// miniaturas (agente_comic.modo_miniatura): un fotograma por variante sobre el render de la maqueta
export interface VarianteMiniatura { enfoque: string; titular: string; clave: string[]; cifra: string; etiqueta: string; color: string }
export interface Miniaturas { fondo: string; variantes: VarianteMiniatura[]; logo?: string }
export interface Motion {
  tipo?: 'paneles' | 'subtitulos' | 'miniatura';     // que escena se renderiza (sin tipo: paneles)
  subtitulos?: Subtitulos;
  miniaturas?: Miniaturas;
  ancho: number; alto: number; fps: number; frames: number; orientacion: 'vertical' | 'horizontal';
  banda: { x: number; y: number; w: number; h: number };
  paleta: Paleta; icono_flujo: string; tramos: Tramo[]; paneles: Panel[];
  render?: { desde: number; hasta: number | null };
}
