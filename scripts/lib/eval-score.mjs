// Puntuación automática del set dorado (T-0022). Funciones puras: sin red ni archivos.
// Las reglas salen del prompt real de WF02 (n8n-workflows/02-generacion.json) para que no se desvíen.

export const THEMES = [
  'Libros', 'Vinilos', 'Teatro', 'Fiestas', 'Conciertos', 'Conversatorios',
  'Proyecciones', 'Presentaciones', 'Café', 'Comida', 'Licores',
];

// Nombre de tema del prompt → clave de la lista de hashtags ("Café" en la lista temática)
const normalize = (s) => String(s ?? '')
  .normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Extrae del código del nodo «Preparar prompt Gemini» el prompt de sistema y el de usuario. */
export function parsePromptNode(jsCode) {
  const grab = (name) => {
    const m = jsCode.match(new RegExp('const ' + name + ' = `([\\s\\S]*?)`;'));
    if (!m) throw new Error(`No encuentro ${name} en el nodo de WF02`);
    return m[1];
  };
  const systemPrompt = grab('systemPrompt');
  const userTemplate = grab('userPrompt');

  const generic = [];
  const themed = {};
  for (const line of systemPrompt.split('\n')) {
    const g = line.match(/Hashtags genéricos permitidos SIEMPRE.*?:\s*(.+)$/);
    if (g) generic.push(...g[1].split(',').map((x) => x.trim()));
    const t = line.match(/^\s+([A-Za-zéÉ]+):\s+([A-Za-z]+(?:,\s*[A-Za-z]+)+)\s*$/);
    if (t && THEMES.includes(t[1])) themed[t[1]] = t[2].split(',').map((x) => x.trim());
  }
  if (generic.length === 0 || Object.keys(themed).length < 8) {
    throw new Error('El prompt de WF02 cambió de formato: no pude leer las listas de hashtags');
  }
  return { systemPrompt, userTemplate, generic, themed };
}

const EMOJI = /\p{Extended_Pictographic}/gu;
// \b no reconoce los límites tras vocales con tilde (í, á, é): se usan lookarounds de letras Unicode
const VOSEO = /(?<!\p{L})(vos|tenés|querés|sabés|podés|vení|mirá|descubrí|encontrá|disfrutá|visitá|conocé|pedí|probá|acompañá|llevate|sumate|animate)(?!\p{L})/iu;
const GENERICAS = /no te lo pierdas|haz clic aquí/i;

const countEmoji = (s) => (String(s).match(EMOJI) || []).length;
const hashes = (arr) => (Array.isArray(arr) ? arr : []).map((h) => String(h).replace(/^#/, '').trim());
const inRange = (n, lo, hi) => n >= lo && n <= hi;

/**
 * Fracción de hechos que aparecen en el texto, sin distinguir tildes ni mayúsculas.
 * Un hecho es una cadena o una lista de variantes de escritura (basta con una): ["21 de agosto", "21.08.2026"].
 */
export function factsFound(texto, facts) {
  if (!facts || facts.length === 0) return null;
  const t = normalize(texto);
  const hit = (f) => [].concat(f).some((v) => t.includes(normalize(v)));
  return facts.filter(hit).length / facts.length;
}

const MESES = 'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre';
// Datos que un modelo suele inventar: precios, horas, fechas y dominios web
const DATO = new RegExp(
  `\\$\\s?\\d[\\d.,]*|\\b\\d{1,2}:\\d{2}\\b|\\b\\d{1,2}\\s?[ap]\\.?\\s?m\\b|\\b\\d{1,2} de (?:${MESES})(?: de \\d{4})?|\\b[a-z0-9-]+\\.(?:com|co|org|net)\\b`, 'gi');
// Compara sin espacios ni puntuación y sin ceros a la izquierda («08:00» = «8:00»; «p.m.» = «pm»)
const compact = (s) => normalize(s).replace(/\$/g, '').replace(/:00/g, '').replace(/\b0(\d)/g, '$1').replace(/[\s.,]/g, '');

/**
 * Fracción de datos concretos del texto que aparecen en la verdad conocida (caption publicado, hechos del afiche, notas).
 * Un dato ausente de la verdad es un posible dato inventado: se revisa a mano. null = el texto no trae datos de ese tipo.
 */
export function dataSupported(texto, ground) {
  const datos = datosDe(texto);
  if (datos.length === 0) return null;
  const g = compact(ground);
  const ok = (d) => g.includes(compact(d)) || g.includes(compact(d.replace(/ de \d{4}$/, '')));
  return datos.filter(ok).length / datos.length;
}

const datosDe = (texto) => [...new Set((String(texto ?? '').match(DATO) ?? []).map((d) => d.replace(/[.,]+$/, '')))];

export const unsupportedData = (texto, ground) => {
  const g = compact(ground);
  return datosDe(texto).filter((d) => !g.includes(compact(d)) && !g.includes(compact(d.replace(/ de \d{4}$/, ''))));
};

export const WRITE_KEYS = {
  caption_instagram: 'string', hashtags_instagram: 'array', caption_tiktok: 'string', hashtags_tiktok: 'array',
  title_youtube: 'string', caption_youtube: 'string', tags_youtube: 'array', suggested_time_note: 'string',
};

const typeOk = (v, t) => (t === 'array' ? Array.isArray(v) : typeof v === t);

/** Puntúa la salida del paso de redacción. Cada chequeo da 0..1; null = no aplica. */
export function scoreCaptions(out, piece, rules) {
  const c = {};
  const o = out ?? {};
  c.schema = Object.entries(WRITE_KEYS).every(([k, t]) => typeOk(o[k], t)) ? 1 : 0;

  const limites = [
    String(o.caption_instagram ?? '').length <= 2000,
    String(o.caption_tiktok ?? '').length <= 150,
    String(o.title_youtube ?? '').length <= 80,
    inRange(hashes(o.hashtags_instagram).length, 10, 15),
    inRange(hashes(o.hashtags_tiktok).length, 5, 7),
    hashes(o.tags_youtube).length <= 15,
  ];
  c.limites = limites.filter(Boolean).length / limites.length;

  const textos = ['caption_instagram', 'caption_tiktok', 'title_youtube', 'caption_youtube'].map((k) => String(o[k] ?? ''));
  c.tuteo = textos.some((t) => VOSEO.test(t)) ? 0 : 1;
  c.emojis = textos.filter((t) => countEmoji(t) <= 3).length / textos.length;
  c.marca = /\*\*Le Tiende\*\*|\*Le Tiende\*/.test(String(o.caption_instagram ?? '')) ? 1 : 0;
  c.sin_frases_genericas = textos.some((t) => GENERICAS.test(t)) ? 0 : 1;
  c.geografia = textos.some((t) => /chapinero/i.test(t)) ? 0 : 1;
  // «Parkway» lleva artículo en el texto (solo va sin él como hashtag) y nunca se acompaña de Teusaquillo
  const hashtagsTodos = [...hashes(o.hashtags_instagram), ...hashes(o.hashtags_tiktok), ...hashes(o.tags_youtube)];
  const parkwaySinArticulo = textos.some((t) => /(?<!el |El |al |del )(?<![#\p{L}])parkway(?!\p{L})/iu.test(t));
  const teusaquillo = [...textos, ...hashtagsTodos].some((t) => /teusaquillo/i.test(t));
  c.parkway = parkwaySinArticulo || teusaquillo ? 0 : 1;

  const permitidos = new Set([...rules.generic, ...(rules.themed[piece.theme] ?? [])].map(normalize));
  const todos = [...hashes(o.hashtags_instagram), ...hashes(o.hashtags_tiktok)];
  c.hashtags_tema = todos.length === 0 ? 0 : todos.filter((h) => permitidos.has(normalize(h))).length / todos.length;

  c.especificidad = factsFound(o.caption_instagram, piece.key_facts);
  // Verdad conocida: lo que publicó el centro, los hechos leídos del afiche y las notas de quien envió la pieza
  const ground = [piece.published_caption, ...(piece.visible_facts ?? []), ...(piece.key_facts ?? []), piece.notes, 'letiende.co'].flat().join(' ');
  c.datos_respaldados = piece.published_caption ? dataSupported(textos.join(' '), ground) : null;
  return c;
}

export const EXTRACT_KEYS = { tema: 'string', titulo: 'string|null', autor_o_artista: 'string|null', texto_visible: 'array', descripcion: 'string' };

/** Puntúa la salida del paso de extracción visual. */
export function scoreExtraction(ext, piece) {
  const c = {};
  const e = ext ?? {};
  const okTipo = (v, t) => t.split('|').some((x) => (x === 'null' ? v === null : typeOk(v, x)));
  c.schema = Object.entries(EXTRACT_KEYS).every(([k, t]) => okTipo(e[k], t)) ? 1 : 0;
  // theme_alt: otros temas igualmente válidos para la pieza (p. ej. un lanzamiento de libro: Presentaciones o Libros)
  c.tema = [piece.theme, ...(piece.theme_alt ?? [])].map(normalize).includes(normalize(e.tema)) ? 1 : 0;
  const visto = [e.titulo, e.autor_o_artista, ...(Array.isArray(e.texto_visible) ? e.texto_visible : []), e.descripcion].join(' | ');
  c.hechos_visibles = factsFound(visto, piece.visible_facts ?? piece.key_facts);
  return c;
}

/** Promedio de los chequeos que aplican (ignora null). */
export function mean(obj) {
  const v = Object.values(obj).filter((x) => typeof x === 'number');
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

export function percentile(values, p) {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.ceil((p / 100) * s.length) - 1)];
}
