// «Editor» sin interfaz para Motion Canvas 3.17: el plugin de Vite importa este modulo y llama a editor(project).
// En vez de montar la interfaz, carga las fuentes y renderiza el proyecto entero con el exportador de secuencia
// de imagenes (PNG con alfa). render.mjs espera a window.__fin (0 = bien, 1 = error, 2 = abortado).
import {Renderer, Vector2} from '@motion-canvas/core';
import datos from '@datos';

const estado = (t) => { const p = document.getElementById('estado'); if (p) p.textContent = t; };
window.__log = [];

export function index() {
  estado('sin proyecto');
  window.__fin = 1;
}

export async function editor(project) {
  try {
    project.logger.onLogged.subscribe((p) => window.__log.push(`${p.level}: ${p.message}`));
    await Promise.all([
      document.fonts.load('80px "Archivo Black"'),
      document.fonts.load('700 40px "JetBrains Mono"'),
      document.fonts.load('400 40px "JetBrains Mono"'),
    ]);
    window.__fuentes = ['Archivo Black', 'JetBrains Mono'].map((f) => [f, document.fonts.check(`40px "${f}"`)]);
    const renderer = new Renderer(project);
    renderer.onFrameChanged.subscribe((f) => { window.__fotograma = f; });
    renderer.onFinished.subscribe((r) => { window.__fin = r; estado(`fin ${r}`); });
    const fps = datos.fps;
    const desde = (datos.render?.desde ?? 0) / fps;
    const hasta = datos.render?.hasta != null ? datos.render.hasta / fps : Infinity;
    estado('renderizando');
    await renderer.render({
      name: '.',                      // los PNG van directos a la carpeta de salida: 000000.png, 000001.png…
      range: [desde, hasta],
      fps,
      size: new Vector2(datos.ancho, datos.alto),
      resolutionScale: 1,
      colorSpace: 'srgb',
      background: null,               // transparente: el montaje los pone encima de la pelicula
      exporter: {
        name: '@motion-canvas/core/image-sequence',
        options: {fileType: 'image/png', quality: 100, groupByScene: false},
      },
    });
  } catch (e) {
    window.__log.push(`error: ${e && e.stack ? e.stack : e}`);
    window.__fin = 1;
  }
}
