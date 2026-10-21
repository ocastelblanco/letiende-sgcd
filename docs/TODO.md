# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0028**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0027 — [FLUJO]: Orquestador de una pieza (10 → 11 → 12) con reintento diferido (Fase 3, en dev)

**Origen:** Plan §4, Fase 3 (subworkflows). T-0025 dejó WF10 y WF11 con modelo alterno ante 503/429 inmediatos, pero un fallo que persiste (`gemini_http`, `waiting_quota`) queda solo en `pipeline_steps` sin quien lo reintente.

**Archivos:**
- Workflow nuevo `20 - Procesar pieza` (dev) → `n8n-workflows/20-procesar-pieza.json`
- `docs/MEMORY.md`

**Qué hacer** (en dev con n8n-mcp, `N8N_MCP_TARGET=dev`; skills `n8n-*`):
1. Entrada: `content_item_id`, `image_url`, `notes`. Encadena WF10 → WF11 → WF12 con `Execute Workflow`, pasando la extracción y los captions por el contrato `ok` / `error_type`. Si WF12 devuelve `valid: false`, un único reintento a WF11 con `retry_feedback` (hay que agregar a WF11 la entrada opcional `feedback`, delimitada con `"""`) y una segunda pasada por WF12.
2. Guarda captions y hashtags en `content_items` y pasa el estado a `ready_for_review` solo si todo el encadenado terminó `ok`.
3. Reintento diferido: si un paso termina `failed` con `gemini_http` o `waiting_quota`, deja el item en `waiting_quota` y un cron lo retoma (máx. 3 intentos totales por paso, contados en `pipeline_steps`).
4. Probar con las 3 piezas sintéticas y un fallo forzado en cada paso; datos de prueba borrados.

**Definition of done:**
- [ ] Valida con 0 errores (`runtime`) y JSON versionado
- [ ] Las 3 piezas llegan a `ready_for_review` con 3 filas por pieza en `pipeline_steps`
- [ ] Un fallo forzado deja el item en `waiting_quota` y el cron lo retoma una vez

---

## Tarea 2 — T-0028 — [FLUJO]: Router único de Telegram con `secret_token` (Fase 3, en dev)

**Origen:** Plan §4, Fase 3 y ADR-012. WF01 y WF03 tienen cada uno su Telegram Trigger y se quitan el webhook mutuamente; los botones de aprobación no llegan a ningún flujo. Absorbe la tarea descartada T-0004 (OWASP A01).

**Archivos:**
- Workflow nuevo `00 - Router de Telegram` (dev) → `n8n-workflows/00-router-telegram.json`
- `docs/MEMORY.md`

**Qué hacer** (en dev con n8n-mcp, `N8N_MCP_TARGET=dev`; skills `n8n-*`):
1. Un único Telegram Trigger (`message` + `callback_query`) que valida `x-telegram-bot-api-secret-token` contra `$TELEGRAM_WEBHOOK_SECRET` y responde 403 si no coincide.
2. Despacho por `Execute Workflow` a subworkflows: pieza nueva (foto/video con caption) y botones de revisión; el resto de updates se ignora con aviso en `error_log`.
3. Solo se aceptan updates de chats en la lista permitida (`TELEGRAM_ADMIN_CHAT_ID` y aprobadores).
4. Probar con updates sintéticos (token correcto, incorrecto, chat ajeno, tipo no soportado).

**Definition of done:**
- [ ] Valida con 0 errores (`runtime`) y JSON versionado
- [ ] Token incorrecto → 403 sin ejecutar nada; chat ajeno → ignorado y registrado
- [ ] Update válido llega al subworkflow correcto; datos de prueba borrados

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
| 2026-10-21 | T-0026 | Subworkflow «12 - Validar captions» (dev) | `n8n-workflows/12-validar-captions.json`, 12 nodos, `runtime` sin errores ni avisos. Sin llamadas a la API. Sobre las 20 salidas guardadas de `3.5-flash-lite → 3.5-flash-lite` (pasadas por el workflow vivo): `marca` 0,900 → 1,000 y `hashtags_tema` 0,907 → 1,000; 19 de 20 quedan `valid`, la otra pide reintento (título de 82 caracteres). Fila `validate_captions` por ejecución (20 `succeeded`, 1 `failed`); ruta de error probada (tema inválido y fallo forzado en las reglas). Datos de prueba borrados. |
| 2026-10-21 | T-0025 | Subworkflow «11 - Redactar captions» (dev) | `n8n-workflows/11-redactar-captions.json`, 14 nodos, `runtime` sin errores ni avisos (WF10 también). Entrada tipada con `extraction` validada y reconstruida; prompt y listas de WF02 con datos delimitados por `"""` (OWASP A03); `write_captions` en `pipeline_steps`. 3 de 3 sintéticas con `scoreCaptions` 0,989–1,000 (`gemini-3.5-flash-lite`, ~1,5 K tokens de entrada y ~0,6 K de salida, 2,8–6,0 s). WF10 y WF11 usan `gemini-3.5-flash-lite` con alterno `gemini-3.1-flash-lite` ante 429/500/503 persistentes. Rutas de error probadas (modelo inexistente → `gemini_http`; `notes` de 2.001 caracteres → `validation`) con fila `failed`, `error_log` y aviso. Datos de prueba borrados. |
| 2026-10-14 | T-0024 | Comparar modelos y línea base de una llamada (set real, 20 piezas) | `--single` y chequeo `datos_respaldados` en el evaluador (11 pruebas). 1 llamada vs 2 pasos con `3.5-flash-lite`: captions 0,976 vs 0,973, o sea sin diferencia; los 2 pasos cuestan el doble de cuota. `3.1-flash-lite` dio 503 en 11 de 20 extracciones; los Flash no caben en el nivel gratuito (429 o 10 piezas). Revisión a mano: ningún dato inventado. Decisión: 2 pasos, ambos `gemini-3.5-flash-lite`. |
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
