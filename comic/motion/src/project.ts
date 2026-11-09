import {makeProject} from '@motion-canvas/core';
import datos from '@datos';
import paneles from './escenas/paneles?scene';
import subtitulos from './escenas/subtitulos?scene';
import miniatura from './escenas/miniatura?scene';

// el mismo proyecto renderiza los paneles de datos (modo «paneles»), los subtitulos (modo «subtitulos») o las miniaturas
// (modo «miniatura») segun el campo 'tipo' de motion.json
const tipo = (datos as {tipo?: string}).tipo;
export default makeProject({scenes: [tipo === 'subtitulos' ? subtitulos : tipo === 'miniatura' ? miniatura : paneles]});
