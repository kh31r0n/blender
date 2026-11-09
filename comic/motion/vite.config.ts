// Proyecto Motion Canvas de los paneles de datos del estilo tecnico (agente_comic.py, modo «paneles»).
// No se usa el editor de Motion Canvas: el «editor» es renderizador/, que renderiza en cuanto carga la pagina
// (lo abre render.mjs con Chrome sin interfaz). Entradas por variables de entorno:
//   MC_DATOS   ruta absoluta del motion.json (paneles en fotogramas, paleta, tamano)
//   MC_SALIDA  carpeta donde se escriben los PNG (000000.png = fotograma 1 de Blender)
import {defineConfig} from 'vite';
import mcPlugin from '@motion-canvas/vite-plugin';
import path from 'path';
import {fileURLToPath} from 'url';

// el plugin es CommonJS: en un paquete "type": "module" el export por defecto llega envuelto
const motionCanvas = ((mcPlugin as any).default ?? mcPlugin) as typeof mcPlugin;
const aqui = path.dirname(fileURLToPath(import.meta.url));
const datos = process.env.MC_DATOS || path.join(aqui, 'prueba', 'motion.json');
const salida = process.env.MC_SALIDA || path.join(aqui, 'output');

export default defineConfig({
  // las fuentes (OFL) viven en comic/descargas/fuentes y se sirven en la raiz: /ArchivoBlack-Regular.ttf
  publicDir: path.resolve(aqui, '..', 'descargas', 'fuentes'),
  resolve: {alias: {'@datos': datos}},
  // MC_ORIGEN: la carpeta del motion.json original, donde estan los fondos de las miniaturas (render.mjs copia el
  // motion.json de un tramo a la salida, asi que path.dirname(datos) no siempre es esa carpeta)
  server: {fs: {allow: [aqui, path.dirname(datos), ...(process.env.MC_ORIGEN ? [process.env.MC_ORIGEN] : []),
                        path.resolve(aqui, '..', 'descargas')]}},
  logLevel: 'warn',
  plugins: [
    motionCanvas({
      project: './src/project.ts',
      output: salida,
      editor: path.join(aqui, 'renderizador', 'main.js'),
    }),
  ],
});
