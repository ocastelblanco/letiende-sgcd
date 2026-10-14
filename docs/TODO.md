# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0025**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0024 — [DATOS]: Comparar modelos y línea base de una llamada en el set real

**Origen:** Plan §4, Fase 2 («línea base medida»). T-0021 dejó el set real (20 piezas); la primera corrida con un solo modelo dio 0,997, así que hace falta comparar de verdad: ¿separar en 2 pasos aporta algo frente a 1 llamada con la imagen?, ¿qué modelo conviene?

**Archivos:**
- `scripts/eval-gemini.mjs` (modo de una llamada), `scripts/lib/eval-score.mjs`
- `docs/MEMORY.md` (tabla de resultados) y `docs/plan-actualizacion.md` (salida de la Fase 2)

**Qué hacer:**
1. Pedir al usuario que revise `golden-set/pieces/*.json` (hechos esperados, `notes`, `theme_alt`): los anotó una IA.
2. Añadir `--single <modelo>`: una sola llamada con el prompt de WF02 y la imagen como `inline_data` (control sin extracción previa).
3. Correr al menos 3 configuraciones sobre las 20 piezas: una sola llamada, 2 pasos Flash-Lite y 2 pasos con un modelo Flash. Revisar `--dry-run` primero: los Flash solo tienen 20 RPD.
4. Revisar a mano los JSONL de las piezas con peor puntaje y de una muestra al azar (el puntaje no ve datos inventados). Agregar un chequeo de nombres propios si hace falta.
5. Registrar la tabla (puntaje, tokens, latencia, cuota) en `docs/MEMORY.md` y decidir el modelo de cada paso.

**Definition of done:**
- [ ] 3 o más configuraciones medidas sobre las 20 piezas, con cuota usada anotada
- [ ] Revisión humana de los hechos esperados y de una muestra de salidas
- [ ] Decisión registrada: modelo del paso A, del paso B y si se mantienen los 2 pasos

---

## Tarea 2 — T-0025 — [FLUJO]: Subworkflow «Redactar captions» con salida estructurada (Fase 3, en dev)

**Origen:** Plan §4, Fase 3 (generación en 2 pasos). T-0023 dejó el paso A (`10 - Extraer visual`); falta el paso B, que hoy vive dentro de WF02 sin esquema.

**Archivos:**
- Workflow nuevo `11 - Redactar captions` (dev) → `n8n-workflows/11-redactar-captions.json`
- `docs/MEMORY.md`

**Qué hacer** (en dev con n8n-mcp, `N8N_MCP_TARGET=dev`; skills `n8n-*`):
1. Entrada tipada: `content_item_id`, `extraction` (objeto que devuelve WF10) y `notes` (texto de quien envió la pieza). Mismo contrato de salida que WF10 (`ok` / `error_type`).
2. Prompt y listas de hashtags **leídos de WF02** como en `scripts/eval-gemini.mjs` (`writeUserPrompt`), con los datos externos delimitados con `"""` (OWASP A03) y `WRITE_SCHEMA` como `response_format`. Modelo según T-0024 (provisional: `gemini-3.5-flash-lite`).
3. Fila `write_captions` en `pipeline_steps` y la misma ruta de error que WF10 (copiar `Preparar error` con `first(0, 0)`).
4. Decidir el manejo del 503 «high demand» que vio T-0023 (3 de 6 llamadas): reintento diferido, modelo alterno o ambos; aplicarlo también a WF10.
5. Probar con las 3 piezas sintéticas (las imágenes se sirven por `raw.githubusercontent.com`, permitido solo en dev) y el harness `zz - Prueba T-0023` adaptado.

**Definition of done:**
- [ ] Valida con 0 errores (`runtime`) y JSON versionado
- [ ] Las 3 piezas sintéticas producen captions que pasan `scoreCaptions` de `scripts/lib/eval-score.mjs`
- [ ] Fila en `pipeline_steps` por ejecución y ruta de error probada con un fallo forzado; datos de prueba borrados

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
| 2026-10-14 | T-0023 | Subworkflow «10 - Extraer visual» (dev) | `n8n-workflows/10-extraer-visual.json`, 15 nodos, `runtime` sin errores ni avisos. 3 de 3 piezas sintéticas con tema y hechos correctos (`gemini-3.1-flash-lite`, imagen en `inline_data`); fila en `pipeline_steps` por ejecución; ruta de error probada (validación, descarga 404 forzada y 503 real de Gemini) con `error_log` y aviso a Telegram. Hallazgos: `URL` no existe en el sandbox, `first(0, 0)` desde ramas de error, 503 frecuente en el nivel gratuito. Datos de prueba borrados. |
| 2026-10-13 | T-0021 | Set dorado a partir de Instagram | 20 piezas reales (de 173 publicaciones) en `golden-set/` (fuera de git), con hechos esperados leídos de los afiches. Corrida de comprobación (40 llamadas): 0,962 → 0,997 tras corregir la ambigüedad de temas y de formatos de fecha. El evaluador ganó `theme_alt`, variantes de hechos y `--rescore`. Hechos pendientes de revisión humana → T-0024. |
| 2026-10-09 | T-0022 | Script de evaluación de modelos Gemini | `scripts/eval-gemini.mjs` (Interactions, `inline_data`, 2 pasos con el prompt real de WF02) y `scripts/lib/eval-score.mjs` con 9 pruebas. Corrió 2 configuraciones Flash-Lite sobre 3 piezas sintéticas: total 0,998 en ambas, 14 llamadas de cuota. El puntaje detectó un hashtag fuera de tema; no detecta datos inventados (queda para revisión humana). Falta el set real (T-0021) y una línea base de una sola llamada. |
| 2026-10-07 | T-0020 | Autenticación de Supabase y manejador de errores | 5 workflows corregidos (26 nodos), 5 de 5 validan sin errores `runtime` y desplegados con `scripts/deploy-workflows.sh`; WF04 `success` post-despliegue. Cuerpo del manejador: 400 → 201. Sin probar el disparo real del Error Trigger ni el cron de WF03 (cada 6 h). |
| 2026-10-07 | T-0011 | Estrategia de costo de Gemini | **Híbrido** (ADR-013): proyecto `letiende-sgcd` en Nivel gratuito para el flujo; el de pago (tope prepago COP 5.000) como respaldo sin usar. Tabla de límites de 12 modelos leída en AI Studio; capacidad preliminar 1.400 piezas/semana con Flash-Lite. Clave gratuita en producción, verificada en el contenedor. |
| 2026-10-07 | T-0019 | Cierre de Fase 1: 72 h de n8n 2.41.6 | Estable: 0 reinicios ni OOM, 333–405 MB disponibles, CPU en reposo. Pero **todas las ejecuciones fallaban** desde T-0016: n8n 2.x bloquea `$env`. Corregido con `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (respaldo previo, `deploy-n8n.sh --apply`); WF04 pasó a `success` a las 22:00. Quedan defectos de los JSON → T-0020. |
| 2026-10-07 | T-0018 | RLS en las 5 tablas originales de Supabase | `migration-003` aplicada en producción: RLS sin políticas, privilegios revocados a `anon`/`authenticated`, `search_path` fijo en `update_updated_at` y 3 índices de claves foráneas. Probada antes en un Postgres desechable. REST: `anon` 401, service_role 200. Ningún workflow usaba la `anon` key. |
| 2026-10-03 | T-0017 | Tabla `pipeline_steps` en Supabase | `migration-002` aplicada en producción: tabla con RLS y sin acceso para `anon`/`authenticated`, 4 índices y 3 vistas `security_invoker` (`pipeline_step_stats`, `pipeline_stuck_steps`, `pipeline_daily_usage`). Probada antes en un Postgres desechable (p50/p95 calculados a mano, 8 restricciones, roles). Destapó el hallazgo de RLS → T-0018. |
| 2026-10-03 | T-0016 | Producción a n8n 2.41.6 y compose limpio | `scripts/deploy-n8n.sh` (simula por defecto; `--apply` exige respaldo de <1 h). Imagen fijada, sin `N8N_BASIC_AUTH_*`, 5678 solo en `127.0.0.1`, 5 de 5 workflows activos, Telegram sin errores; memoria disponible 441 → ~380 MB. |
| 2026-10-03 | T-0015 | Compatibilidad de los 5 workflows con n8n 2.41.6 | Importados a dev sin cambios (idénticos al respaldo); validación `runtime`: 19 errores y 8 advertencias, todos defectos previos de los JSON (expresiones sin `=`, Switch sin salida de respaldo, `credentials` mal ubicadas); 84 nodos con `typeVersion` obsoleta pero ejecutable. Decisión: actualizar producción antes de la Fase 3. |
| 2026-10-03 | T-0014 | Instancia de desarrollo local de n8n | n8n 2.41.6 (fijada) + PostgreSQL 15 en Docker, solo en `127.0.0.1`; owner y API key creadas por la API REST; n8n-mcp con `N8N_MCP_TARGET=dev` lista 0 workflows. |
| 2026-10-03 | T-0013 | Restablecer HTTPS con renovación automática | Caddy 2.11.6 reemplaza a nginx; certificado de Let's Encrypt válido hasta 2027-01-01 con renovación automática; `/healthz` 200 sin `-k`; certbot deshabilitado. ADR-015. |
| 2026-10-02 | T-0012 | Actualizar paquetes de la VM y reiniciarla | 63 paquetes actualizados (Docker 29.3 → 29.8, containerd 2.2 → 2.3) y dos reinicios; kernel 6.17.0-1007 → 7.0.0-1013; 0 pendientes y sin `reboot-required`. n8n, postgres y nginx volvieron solos; 5 workflows en la base de n8n. |
| 2026-10-02 | T-0009 | Respaldo completo antes de tocar la plataforma | `scripts/backup.sh` (5 workflows por túnel SSH, dump de la base de n8n, configuración de la VM y esquema `public` de Supabase, con sumas SHA-256). Restauración verificada en un Postgres local desechable: 5 workflows, 4 credenciales, 1.465 ejecuciones. |
| 2026-10-02 | T-0008 | Rotar credenciales expuestas | Contraseña de la base de Supabase, token de gestión de Supabase y claves de R2 rotados y verificados; credenciales viejas rechazadas; reglas con secretos eliminadas de `settings.local.json`. |
| 2026-10-02 | T-0010 | Instalar n8n-mcp local | Servidor 2.91.0 vía `scripts/n8n-mcp.sh` (sin secretos en la config de Claude Code, telemetría desactivada); 28 herramientas verificadas. ADR-014. |
| 2026-10-02 | T-0007 | Diagnóstico y plan de actualización | Sistema caído (SSL vencido), visión de Gemini refutada con pruebas, conflicto de webhooks en Telegram. Plan por fases en `docs/plan-actualizacion.md`. |
| 2026-10-02 | T-0005 | Verificar fix de tema (libros vs. vinilos) | **Descartada:** la causa raíz era que Gemini no veía la imagen; se resuelve en la Fase 3. |
| 2026-10-02 | T-0004 | Validar `secret_token` del webhook de Telegram | **Absorbida** por la Fase 3 (router único de Telegram con `secret_token`). |
| 2026-10-02 | T-0006 | Reorganización del repo para reinicio | Docs en `docs/`, tracking de esfuerzo, rama principal renombrada a `main`, escaneo de secretos en CI. |
| 2026-04-30 | T-0003 | Hotfix calidad contenido IA — iteración 1 | Desplegado, pero basado en ADR-007, que resultó falso. |
| 2026-04-30 | T-0002 | Fix brand + multimodal + deploy | Correcciones de WF01/WF02/WF03 sobre n8n 2.12.3. |
| 2026-04-29 | T-0001 | Inicialización docs + Motor JIT | Creados PRD.md, tech-specs.md, MEMORY.md, TODO.md |

## Backlog (orden del plan)

- **Fase 2:** tabla `pipeline_steps` y vista de tablero
- **Fase 2:** exportación de Instagram y set dorado (15–20 piezas) + script de evaluación
- **Fase 2:** cálculo de capacidad semanal sin costo (plan §3)
- **Fase 3:** router único de Telegram, subworkflows, visión con `inline_data`, generación en 2 pasos con esquema, validadores
- **Fase 4:** revisión en equipo (grupo, allowlist, objeciones, `review_actions`)
- **Fase 5:** publicación automática en Instagram
- **Fase 6:** video · **Fase 7:** métricas y monitor de cuotas
