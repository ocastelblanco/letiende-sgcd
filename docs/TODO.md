# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0024**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0023 — [FLUJO]: Subworkflow «Extraer visual» con inline_data (Fase 3, en dev)

**Origen:** Plan §4, Fase 3; ADR-011. T-0022 midió que la extracción visual estructurada con Flash-Lite funciona con la imagen enviada como `inline_data` (3 de 3 piezas sintéticas, tema y hechos visibles correctos). Falta llevarla al flujo en n8n: es el cambio que corrige la causa raíz (Gemini no veía la imagen).

**Archivos:**
- Workflow nuevo `10 - Extraer visual` (instancia de dev) → `n8n-workflows/10-extraer-visual.json`
- `docs/MEMORY.md`

**Qué hacer** (en dev con n8n-mcp: reiniciar Claude Code con `N8N_MCP_TARGET=dev`; usar las skills `n8n-*`):
1. Subworkflow con entrada tipada `content_item_id` y `image_url` (Execute Workflow Trigger). Descarga la imagen **validando el host** (OWASP A10) y obtiene los bytes con `this.helpers.getBinaryDataBuffer()` (skill `n8n-binary-and-data`).
2. Llamada a Interactions con `response_format` (esquema de `scripts/eval-gemini.mjs`), `gemini-3.1-flash-lite` o el que gane la evaluación, `store: false`, 3 s de espera y reintentos 1/2/4 s.
3. Escribe una fila en `pipeline_steps` (paso `extract_visual`: duración, modelo, tokens) y devuelve el JSON de extracción; ante un error, `error_log` con las columnas reales y aviso a Telegram.
4. Probarlo en dev con las 3 imágenes sintéticas de `golden-set/synthetic/`.

**Preparación (verificada el 2026-10-13):**
- La instancia dev está arriba (`sgcd-dev-n8n-1`, healthz 200, `127.0.0.1:5678`). Abrir Claude Code con `N8N_MCP_TARGET=dev` y comprobar con `n8n_health_check` que apunta a dev, no a producción.
- **Bloqueo a resolver al empezar:** el contenedor dev no tiene `GEMINI_API_KEY`, `SUPABASE_*` ni `TELEGRAM_*`, ni `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, y n8n 2.x bloquea `$env`. Hay que añadirlos a `infrastructure/docker-compose.dev.yml` y recrear solo n8n. Decisión para el usuario: dev no tiene Supabase propio, así que `pipeline_steps` y `error_log` escribirían en producción con la service role; alternativa: probar sin escribir a Supabase (rama de prueba) y dejar esas escrituras para el despliegue.
- Las imágenes sintéticas (`golden-set/synthetic/images/`) deben servirse por una URL alcanzable desde el contenedor (p. ej. `python3 -m http.server` en el Mac y `host.docker.internal`); recordar que el host debe pasar la lista permitida de A10.
- El esquema y los prompts de extracción están en `scripts/eval-gemini.mjs`.

**Definition of done:**
- [ ] Valida con 0 errores (`n8n_validate_workflow`, perfil `runtime`) y el JSON versionado en `n8n-workflows/`
- [ ] Las 3 piezas sintéticas devuelven tema y hechos correctos en dev
- [ ] Cada ejecución deja su fila en `pipeline_steps` y el manejador de errores se probó con un fallo forzado

---

## Tarea 2 — T-0024 — [DATOS]: Comparar modelos y línea base de una llamada en el set real

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

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
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
