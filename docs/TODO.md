# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0022**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0022 — [DATOS]: Script de evaluación de modelos Gemini

**Origen:** Plan §4, Fase 2. ADR-013 deja los modelos Flash-Lite (500 RPD) como candidatos para el flujo; hay que compararlos contra el set dorado (T-0021) con un método repetible. El script puede escribirse y probarse antes de tener el set completo.

**Archivos:**
- `scripts/eval-gemini.mjs` (nuevo), `golden-set/README.md`, `docs/MEMORY.md`

**Qué hacer:**
1. Definir el formato de entrada (una pieza = imagen + caption publicado + tipo) y de salida (JSONL por corrida, con modelo, tokens, latencia y puntuación).
2. El script envía la imagen como `inline_data` (ADR-011), con 3 s entre llamadas y reintentos con backoff, y lee `GEMINI_API_KEY` del entorno.
3. Puntuar con criterios automáticos: JSON válido contra el esquema, caption dentro del límite de la plataforma, hashtags, ausencia de contenido inventado (cruce con el tipo de producto).
4. Probarlo con 2–3 piezas sintéticas y registrar el consumo de cuota del proyecto gratuito.

**Definition of done:**
- [ ] El script corre contra 2 modelos y deja un JSONL comparable
- [ ] Consumo de cuota anotado (las evaluaciones restan RPD: plan §3)
- [ ] Sin secretos en el código ni en los resultados

---

## Tarea 2 — T-0021 — [DATOS]: Exportación de Instagram para el set dorado

**Origen:** Plan §4, Fase 2. El set dorado (15–20 piezas reales publicadas en Instagram) es la línea base para evaluar prompts y modelos; ADR-013 deja como candidatos los modelos Flash-Lite, que hay que comparar contra él.

**Archivos:**
- `golden-set/` (nuevo; imágenes fuera de git si pesan) y `docs/MEMORY.md`

**Qué hacer** (requiere al usuario en Instagram):
1. El usuario descarga la exportación de su cuenta (Configuración → Centro de cuentas → Descargar tu información, formato JSON, solo publicaciones).
2. Elegir 15–20 publicaciones representativas (libros, vinilos, eventos) con imagen y caption.
3. Normalizar a un JSON por pieza: imagen, caption publicado, hashtags, tipo de producto y fecha.

**Definition of done:**
- [ ] 15–20 piezas normalizadas en `golden-set/`
- [ ] Criterios de selección anotados en `docs/MEMORY.md`

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
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
