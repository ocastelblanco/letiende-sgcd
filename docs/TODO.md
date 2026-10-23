# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0030**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0029 — [DEPLOY]: Subworkflows 10, 11, 12, 20 y 21 a producción con IDs remapeados (Fase 3) · **falta la prueba en producción**

**Origen:** Plan §4, Fase 3. Los `Execute Workflow` de WF20 y WF21 llevan los IDs de **dev** (`Mk5c87FiPDMnyDR9`, `XZzEGJbQgrAix36s`, `KdnMvPmOQgb1BvwI`, `kWf4GBbaNpNaulxY`); en producción los IDs serán otros y los workflows deben activarse en orden (subworkflows primero).

**Archivos:**
- `scripts/deploy-workflows.sh` (soportar workflows nuevos y remapeo de IDs)
- `docs/MEMORY.md`

**Qué hacer:**
1. Extender `scripts/deploy-workflows.sh` para crear los workflows nuevos en producción en orden (10, 11, 12, 20, 21), sustituir en cada `Execute Workflow` el ID de dev por el de producción y activar.
2. Dejar un mapa `dev → prod` versionado (sin secretos) y que el script falle si queda algún ID de dev.
3. Simular por defecto, exigir respaldo de <1 h para `--apply` (como hoy). WF21 queda **inactivo** hasta que el usuario confirme.
4. Tras desplegar, una ejecución real de WF20 con una pieza sintética y borrado de sus datos.

**Definition of done:**
- [x] `--apply` crea y activa los workflows en producción sin IDs de dev (2026-10-23: 10, 11, 12 y 20 activos; IDs en `n8n-workflows/id-map.json`)
- [ ] Una pieza sintética llega a `ready_for_review` en producción; datos de prueba borrados
- [x] WF21 desplegado e inactivo (`MVwKBIVdP41fZc0h`); el usuario decide cuándo activarlo

---

## Tarea 2 — T-0030 — [DEPLOY]: Router de Telegram a producción y registro del webhook con `secret_token` (Fase 3)

**Origen:** Plan §4, Fase 3 y ADR-012. T-0028 dejó `00 - Router de Telegram` y los provisionales 30 y 31 en dev; mientras WF01 y WF03 conserven su Telegram Trigger, registrar el webhook del router los deja sin entrada.

**Archivos:**
- `scripts/deploy-workflows.sh` (incluir 00, 30 y 31 con remapeo de IDs; depende de T-0029)
- `infrastructure/docker-compose.yml` (inyectar `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_APPROVER_CHAT_ID`) y `scripts/deploy-n8n.sh` si aplica
- `docs/MEMORY.md`

**Qué hacer:**
1. Decidir con el usuario qué hacen WF01 y WF03 al retirar sus Telegram Trigger (WF30 y WF31 son provisionales): o el router los despacha tal cual, o se adaptan a `Execute Workflow Trigger`.
2. Inyectar `TELEGRAM_WEBHOOK_SECRET` en producción (con respaldo previo), desplegar 30, 31 y 00 en ese orden.
3. Registrar el webhook con `setWebhook` (`secret_token`, `allowed_updates`) y verificar con `getWebhookInfo`; probar un update real del administrador.

**Definition of done:**
- [ ] Router activo en producción; token incorrecto → 403
- [ ] `getWebhookInfo` muestra la URL del router y sin errores pendientes
- [ ] Un mensaje real del administrador llega al subworkflow correcto

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
| 2026-10-21 | T-0028 | Router único de Telegram «00» y subworkflows provisionales 30 y 31 (dev) | `n8n-workflows/00-router-telegram.json` (12 nodos), `30-recibir-pieza.json` y `31-atender-revision.json` (2), `runtime` sin errores ni avisos. Nodo Webhook en vez de Telegram Trigger (este no expone cabeceras): valida `x-telegram-bot-api-secret-token` en tiempo constante, 403 si falla o si la variable falta, 200 inmediato y despacho por `Execute Workflow` con lista permitida de chats. 10 updates sintéticos: foto y video llegan a WF30, botón a WF31, chat ajeno y tipos no soportados a `error_log`. Sin probar el aviso por fallo de subworkflow ni el registro real del webhook. Datos de prueba borrados. |
| 2026-10-21 | T-0027 | Orquestador «20 - Procesar pieza» y cron «21 - Reintentar pendientes» (dev) | `n8n-workflows/20-procesar-pieza.json` (23 nodos) y `21-reintentar-pendientes.json` (5), ambos `runtime` sin errores ni avisos; WF11 ganó la entrada opcional `feedback`. Encadena 10 → 11 → 12, con un reintento a WF11 si WF12 pide correcciones. 3 de 3 sintéticas a `ready_for_review` con 3 filas en `pipeline_steps`. Pruebas forzadas: fallo persistente de Gemini → item en `processing`, el cron no lo toma antes de la espera y sí después (queda `ready_for_review`, `write_captions` intento 2); tope de 3 intentos respetado; validación persistente → un reintento, captions guardados y `error` con `error_log`; host no permitido → `error` sin reintento. Datos de prueba borrados. |
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
