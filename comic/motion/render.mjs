#!/usr/bin/env node
// Render sin interfaz de los paneles de Motion Canvas.
//   node render.mjs --datos motion.json --salida DIR [--desde F --hasta F] [--chrome RUTA] [--timeout S]
// Arranca Vite con el proyecto de esta carpeta (vite.config.ts), abre la pagina con Chrome sin interfaz
// (playwright-core, el Chrome del sistema) y espera a que renderizador/main.js termine. Los PNG (RGBA, cuadro
// completo) quedan en DIR: 000000.png es el fotograma 1 de Blender. Imprime una linea «INFORME {json}».
// --desde/--hasta (fotogramas 0-based, inclusivos) sustituyen a datos.render del motion.json.
import fs from 'fs';
import net from 'net';
import path from 'path';
import {fileURLToPath} from 'url';

const aqui = path.dirname(fileURLToPath(import.meta.url));

function argumentos(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const k = argv[i].slice(2);
    const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    out[k] = v;
  }
  return out;
}

function puertoLibre() {
  return new Promise((ok, mal) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => ok(p)); });
    s.on('error', mal);
  });
}

const a = argumentos(process.argv.slice(2));
if (!a.datos || !a.salida) {
  console.error('uso: node render.mjs --datos motion.json --salida DIR [--desde F --hasta F]');
  process.exit(2);
}
const t0 = Date.now();
let datosRuta = path.resolve(a.datos);
process.env.MC_ORIGEN = path.dirname(datosRuta);   // carpeta del motion.json original (fondos de las miniaturas)
const salida = path.resolve(a.salida);
fs.mkdirSync(salida, {recursive: true});

// --desde/--hasta: copia del motion.json con el tramo, junto a la salida (no se toca el original)
if (a.desde != null || a.hasta != null) {
  const d = JSON.parse(fs.readFileSync(datosRuta, 'utf8'));
  d.render = {desde: Number(a.desde ?? 0), hasta: a.hasta != null ? Number(a.hasta) : null};
  datosRuta = path.join(salida, '_motion_tramo.json');
  fs.writeFileSync(datosRuta, JSON.stringify(d));
}
process.env.MC_DATOS = datosRuta;
process.env.MC_SALIDA = salida;

const {createServer} = await import('vite');
const {chromium} = await import('playwright-core');
const puerto = await puertoLibre();
const servidor = await createServer({
  configFile: path.join(aqui, 'vite.config.ts'),
  root: aqui,
  server: {port: puerto, strictPort: true, host: '127.0.0.1', hmr: {port: puerto}},
});
await servidor.listen();

const informe = {salida, fotogramas: 0, segundos: 0, resultado: null, log: [], fuentes: null};
let navegador;
try {
  navegador = await chromium.launch({
    executablePath: a.chrome || '/usr/bin/google-chrome',
    headless: true,
    args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--mute-audio'],
  });
  const pagina = await navegador.newPage({viewport: {width: 800, height: 600}});
  pagina.on('pageerror', (e) => informe.log.push(`pageerror: ${e.message}`));
  pagina.on('console', (m) => { if (m.type() === 'error') informe.log.push(`console: ${m.text()}`); });
  await pagina.goto(`http://127.0.0.1:${puerto}/`, {waitUntil: 'load'});
  const limite = Number(a.timeout || 3600) * 1000;
  let ultimo = -1;
  const tic = setInterval(async () => {
    try {
      const f = await pagina.evaluate(() => window.__fotograma);
      if (f != null && f !== ultimo && f % 240 === 0) console.error(`  fotograma ${f}`);
      ultimo = f ?? ultimo;
    } catch { /* la pagina puede estar ocupada */ }
  }, 2000);
  await pagina.waitForFunction(() => window.__fin !== undefined, null, {timeout: limite, polling: 250});
  clearInterval(tic);
  informe.resultado = await pagina.evaluate(() => window.__fin);
  informe.log.push(...(await pagina.evaluate(() => window.__log || [])));
  informe.fuentes = await pagina.evaluate(() => window.__fuentes || null);
} catch (e) {
  informe.log.push(`error: ${e.message}`);
  informe.resultado = informe.resultado ?? 1;
} finally {
  if (navegador) await navegador.close();
  await servidor.close();
}
if (datosRuta.endsWith('_motion_tramo.json')) fs.rmSync(datosRuta, {force: true});
informe.fotogramas = fs.readdirSync(salida).filter((n) => /^\d{6}\.png$/.test(n)).length;
informe.segundos = Math.round((Date.now() - t0) / 100) / 10;
console.log(`INFORME ${JSON.stringify(informe)}`);
process.exit(informe.resultado === 0 ? 0 : 1);
