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
| `key_facts` | no | datos que el caption de Instagram **debe** nombrar (título, autor, fecha…); mide la especificidad |
| `visible_facts` | no | datos que se **ven** en la imagen; mide la extracción visual (si falta se usa `key_facts`) |
| `published_caption`, `nota` | no | referencia humana; el script no los usa |

## Ejecutar

```bash
set -a && source credentials.env && set +a
node scripts/eval-gemini.mjs --pieces golden-set/synthetic/pieces --dry-run     # plan y cuota, sin llamadas
node scripts/eval-gemini.mjs --pieces golden-set/synthetic/pieces \
  --config gemini-3.1-flash-lite:gemini-3.5-flash-lite \
  --config gemini-3.5-flash-lite:gemini-3.5-flash-lite
node --test scripts/lib/eval-score.test.mjs                                      # pruebas de la puntuación (sin red)
```

`--config extracción:redacción` es repetible. Cada corrida consume cuota diaria (RPD) del proyecto gratuito;
el script la calcula antes de llamar y la resume al final. Programar las evaluaciones fuera del horario de operación.

## Cómo se puntúa

Reglas automáticas, sin LLM como juez (no gasta cuota). Cada chequeo da 0–1 y el total es el promedio de los dos pasos.

- **Extracción:** esquema válido, tema correcto, hechos visibles encontrados.
- **Redacción:** esquema, límites de longitud y de cantidad de hashtags, tuteo (sin voseo), máximo 3 emojis por texto,
  **Le Tiende** en negrita, sin frases genéricas, sin «Chapinero», hashtags solo del tema, y especificidad (`key_facts` en el caption).

Las reglas y las listas de hashtags se leen del prompt real de WF02, para que no se desvíen. Lo que **no** mide: calidad
literaria ni acierto de los datos que el modelo agrega por su cuenta. Eso lo revisa una persona sobre el JSONL.
