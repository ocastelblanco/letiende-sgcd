# Set dorado

> **El set real contiene contenido de la cuenta de Instagram y no se sube al repositorio público** (plan §4, Fase 2).
> `.gitignore` excluye `pieces/`, `images/` y `results/`. A git solo van resultados **agregados** (tablas en `docs/MEMORY.md`).

Piezas reales ya publicadas en Instagram, con su resultado conocido, para comparar modelos y prompts de
forma repetible (plan de actualización §4, Fase 2; tarea T-0021 las reúne y T-0022 las evalúa).

```
golden-set/
  pieces/          una pieza por archivo .json (el set real; lo arma T-0021). FUERA de git
  images/          imágenes del set real. FUERA de git
  results/         una corrida por archivo .jsonl. FUERA de git
  synthetic/       3 piezas ficticias para probar el script (única parte en git)
```

## Formato de una pieza (`pieces/<id>.json`)

| Campo | Obligatorio | Significado |
|---|---|---|
| `id` | sí | kebab-case, único |
| `theme` | sí | `Libros`, `Vinilos`, `Teatro`, `Fiestas`, `Conciertos`, `Conversatorios`, `Proyecciones`, `Presentaciones`, `Café`, `Comida` o `Licores` |
| `image` | sí | ruta relativa al `.json`; debe quedar dentro de `golden-set/` (png, jpg o webp) |
| `notes` | no | el tema/dato que el equipo escribiría al subir la pieza (puede ir vacío) |
| `key_facts` | no | datos que el caption de Instagram **debe** nombrar (título, autor, fecha…); mide la especificidad. Un dato puede ser una lista de variantes de escritura: `["21 de agosto", "21.08.2026"]` (basta una) |
| `theme_alt` | no | otros temas igualmente válidos para la extracción (p. ej. un lanzamiento de libro: `Presentaciones` o `Libros`) |
| `visible_facts` | no | datos que se **ven** en la imagen; mide la extracción visual (si falta se usa `key_facts`) |
| `published_caption`, `source`, `nota` | no | referencia humana (el caption real publicado, de dónde salió); el script no los usa |

## Ejecutar

```bash
set -a && source credentials.env && set +a
node scripts/eval-gemini.mjs --pieces golden-set/synthetic/pieces --dry-run     # plan y cuota, sin llamadas
node scripts/eval-gemini.mjs --pieces golden-set/synthetic/pieces \
  --config gemini-3.1-flash-lite:gemini-3.5-flash-lite \
  --config gemini-3.5-flash-lite:gemini-3.5-flash-lite
node scripts/eval-gemini.mjs --rescore golden-set/results/<corrida>.jsonl                    # vuelve a puntuar una corrida guardada: 0 llamadas, 0 cuota
node --test scripts/lib/eval-score.test.mjs                                      # pruebas de la puntuación (sin red)
```

`--config extracción:redacción` es repetible. `--single <modelo>` hace una sola llamada con la imagen y el prompt de WF02 (control sin extracción previa; su total es el de los captions). Cada corrida consume cuota diaria (RPD) del proyecto gratuito;
el script la calcula antes de llamar y la resume al final. Programar las evaluaciones fuera del horario de operación.

## Cómo se puntúa

Reglas automáticas, sin LLM como juez (no gasta cuota). Cada chequeo da 0–1 y el total es el promedio de los dos pasos.

- **Extracción:** esquema válido, tema correcto, hechos visibles encontrados.
- **Redacción:** esquema, límites de longitud y de cantidad de hashtags, tuteo (sin voseo), máximo 3 emojis por texto,
  **Le Tiende** en negrita, sin frases genéricas, sin «Chapinero», «Parkway» con artículo y sin «Teusaquillo», hashtags solo del tema, y especificidad (`key_facts` en el caption).

Las reglas y las listas de hashtags se leen del prompt real de WF02, para que no se desvíen. Lo que **no** mide: calidad
literaria ni acierto de los datos que el modelo agrega por su cuenta. Eso lo revisa una persona sobre el JSONL.

## Cómo se armó el set real (T-0021)

Origen: la exportación oficial de Instagram (JSON), solo `your_instagram_activity/media/posts_1.json` y `media/posts/`.
La exportación completa (mensajes, información personal…) se guarda **fuera** del repositorio y no se lee.

- **Universo:** 173 publicaciones (2023-07 a 2026-10); 56 sin caption y 56 carruseles. Se usa la primera imagen de cada una.
- **Selección (20):** mayoría de eventos de teatro y de la casa cultural, porque es el caso real del flujo (afiche → captions):
  Teatro 6 · Conciertos 3 · Presentaciones 3 · Fiestas 2 · Conversatorios 2 · Libros 1 · Vinilos 1 · Licores 1 · Café 1.
  La mayoría son **afiches con la fecha, la hora y el precio impresos**; 4 son fotos de producto para cubrir otros temas.
  Se excluyeron las fichas de libros y vinilos de enero de 2024 (captions copiados de editoriales), los carruseles sin caption
  y los avisos (horarios, tarjeta de fidelidad, felicitaciones).
- **Hechos esperados:** leídos de la **imagen** y contrastados con el caption (no solo del caption). Dos afiches difieren del
  caption en el formato de la fecha. Una pieza (Facundo Cámpora) tiene la fecha solo en el afiche.
- **`notes`:** solo el tema («Teatro», «Conciertos»…), que es lo mínimo que escribiría el equipo; el modelo debe leer los datos del afiche.
  Las 2 piezas de producto sin texto en la imagen (cóctel, café) llevan además el nombre en `notes`.
- **Pendiente de revisión humana:** los hechos esperados los anotó una IA. Hay que confirmarlos antes de usar el puntaje para decidir.
