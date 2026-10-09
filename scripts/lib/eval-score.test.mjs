// Pruebas de la puntuación (sin red): node --test scripts/lib/eval-score.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { parsePromptNode, scoreCaptions, scoreExtraction, factsFound, mean, percentile } from './eval-score.mjs';

const wf2 = JSON.parse(fs.readFileSync(new URL('../../n8n-workflows/02-generacion.json', import.meta.url), 'utf8'));
const code = wf2.nodes.find((n) => n.name === 'Preparar prompt Gemini').parameters.jsCode;
const rules = parsePromptNode(code);

const bueno = {
  caption_instagram: 'Descubre "El laberinto de las palabras" de Marta Quintero, ya en **Le Tiende**. 📚',
  hashtags_instagram: ['LeTiende', 'CulturaBogota', 'CafeCultural', 'PuntoDeEncuentro', 'AgendaCultural', 'Lectura', 'LibrosColombia', 'Bookstagram', 'NovedadEditorial', 'RecomendacionDeLectura'],
  caption_tiktok: 'Lo nuevo en Le Tiende',
  hashtags_tiktok: ['LeTiende', 'Lectura', 'Bookstagram', 'LibrosColombia', 'CulturaBogota'],
  title_youtube: 'El laberinto de las palabras | Le Tiende',
  caption_youtube: 'Descripción completa.',
  tags_youtube: ['libros', 'bogota'],
  suggested_time_note: 'Viernes 6 p. m.',
};
const piece = { theme: 'Libros', key_facts: ['El laberinto de las palabras', 'Marta Quintero'] };

test('el parser lee las listas de hashtags del prompt real de WF02', () => {
  assert.ok(rules.generic.includes('LeTiende'));
  assert.ok(rules.themed.Libros.includes('Bookstagram'));
  assert.ok(rules.themed['Café'] || rules.themed.Café);
  assert.ok(rules.systemPrompt.includes('Carrera 24 #37-44'));
});

test('una salida correcta puntúa 1 en todos los chequeos', () => {
  const c = scoreCaptions(bueno, piece, rules);
  for (const [k, v] of Object.entries(c)) assert.equal(v, 1, `${k}=${v}`);
});

test('detecta voseo, Chapinero, frases genéricas y marca ausente', () => {
  const malo = { ...bueno, caption_instagram: 'Descubrí esto en Chapinero. ¡No te lo pierdas! Le Tiende' };
  const c = scoreCaptions(malo, piece, rules);
  assert.equal(c.tuteo, 0);
  assert.equal(c.geografia, 0);
  assert.equal(c.sin_frases_genericas, 0);
  assert.equal(c.marca, 0);
});

test('penaliza hashtags de otro tema y límites excedidos', () => {
  const mezcla = { ...bueno, hashtags_tiktok: ['Vinilos', 'Tocadiscos', 'LeTiende', 'Lectura', 'Bookstagram'], caption_tiktok: 'x'.repeat(200) };
  const c = scoreCaptions(mezcla, piece, rules);
  assert.ok(c.hashtags_tema < 1);
  assert.ok(c.limites < 1);
});

test('más de 3 emojis baja el chequeo de emojis', () => {
  const c = scoreCaptions({ ...bueno, caption_instagram: '📚📚📚📚 **Le Tiende**' }, piece, rules);
  assert.equal(c.emojis, 0.75);
});

test('especificidad ignora tildes y mayúsculas; sin hechos clave no aplica', () => {
  assert.equal(factsFound('EL LABERINTO DE LAS PALABRAS', ['el laberinto de las palabras', 'Marta Quintero']), 0.5);
  assert.equal(factsFound('x', []), null);
  assert.equal(scoreCaptions(bueno, { theme: 'Libros' }, rules).especificidad, null);
});

test('esquema inválido da 0', () => {
  assert.equal(scoreCaptions({ caption_instagram: 'solo esto' }, piece, rules).schema, 0);
  assert.equal(scoreExtraction({ tema: 'Libros' }, piece).schema, 0);
});

test('extracción: tema y hechos visibles', () => {
  const ext = { tema: 'libros', titulo: 'El laberinto de las palabras', autor_o_artista: null, texto_visible: ['MARTA QUINTERO'], descripcion: 'Portada.' };
  const c = scoreExtraction(ext, piece);
  assert.deepEqual(c, { schema: 1, tema: 1, hechos_visibles: 1 });
});

test('mean ignora null y percentile es de rango más cercano', () => {
  assert.equal(mean({ a: 1, b: null, c: 0 }), 0.5);
  assert.equal(percentile([5, 1, 3, 2, 4], 50), 3);
  assert.equal(percentile([], 95), null);
});
