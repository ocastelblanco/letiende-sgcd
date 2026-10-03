# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0014**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0014 — [INFRA]: Instancia de desarrollo local de n8n (versión fijada 2.41.x)

**Origen:** Plan §4 Fase 1 y ADR-014. Los workflows se construyen y validan con n8n-mcp en una instancia local, nunca en producción; además sirve de banco de pruebas de la actualización de n8n.

**Archivos:**
- `infrastructure/docker-compose.dev.yml` (nuevo)
- `credentials.env.example` (ya tiene `N8N_DEV_API_KEY`)
- `docs/MEMORY.md` (cómo levantarla y la versión elegida)

**Qué hacer:**
1. Confirmar en Docker Hub la última versión estable de n8n 2.41.x y fijarla (nunca `latest`).
2. `docker-compose.dev.yml` con n8n + PostgreSQL 15 en el Mac, puerto 5678 solo en `127.0.0.1`, volúmenes con nombre y las variables mínimas (`N8N_ENCRYPTION_KEY` propia de desarrollo, `WEBHOOK_URL=http://localhost:5678`). Sin secretos de producción: credenciales de prueba o vacías.
3. Levantarla (Docker Desktop con el disco `Auxiliar` montado), crear la cuenta owner en `http://localhost:5678` y generar una API key (*Settings → n8n API*); guardarla como `N8N_DEV_API_KEY` en `credentials.env`.
4. Comprobar que n8n-mcp apunta a ella con `N8N_MCP_TARGET=dev`.

**Definition of done:**
- [ ] `curl http://localhost:5678/healthz` → `{"status":"ok"}` con la versión fijada (sin `latest`)
- [ ] `N8N_MCP_TARGET=dev` lista 0 workflows desde la instancia local (herramienta `n8n_list_workflows`)
- [ ] `docs/MEMORY.md` documenta el comando de arranque y la versión

---

## Tarea 2 — T-0011 — [OPERACIÓN]: Verificar en AI Studio que Gemini no tiene facturación y anotar los límites

**Origen:** Plan §3 y ADR-013. Sin facturación el costo de Gemini es cero por diseño; los límites de la capa gratuita solo se ven en AI Studio y alimentan la fórmula de capacidad semanal.

**Archivos:**
- `docs/MEMORY.md` (tabla de límites vigentes)

**Qué hacer** (requiere al humano en `aistudio.google.com`):
1. En AI Studio → *Dashboard* → proyecto de la `GEMINI_API_KEY`: confirmar que **no hay facturación habilitada** (plan *Free tier*). Si estuviera habilitada, deshabilitarla o crear un proyecto nuevo sin facturación y regenerar la clave.
2. En `aistudio.google.com/rate-limit` anotar RPM, TPM y RPD de los modelos candidatos: `gemini-3.8-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.5-flash` y los `gemma-4-*`.
3. Registrar en `docs/MEMORY.md` una tabla modelo × (RPM, TPM, RPD) con la fecha de consulta.

**Definition of done:**
- [ ] Confirmado por captura o texto que el proyecto no tiene facturación
- [ ] Tabla de límites de al menos 5 modelos en `docs/MEMORY.md`, con fecha
- [ ] Cálculo preliminar de capacidad semanal con la fórmula del plan §3

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
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

- **Fase 1:** actualizar producción a n8n 2.41.x (probado antes en la instancia dev) y limpiar `docker-compose.yml` (quitar `version` y `N8N_BASIC_AUTH_*`, puerto 5678 solo en `127.0.0.1`)
- **Fase 2:** tabla `pipeline_steps` y vista de tablero
- **Fase 2:** exportación de Instagram y set dorado (15–20 piezas) + script de evaluación
- **Fase 2:** cálculo de capacidad semanal sin costo (plan §3)
- **Fase 3:** router único de Telegram, subworkflows, visión con `inline_data`, generación en 2 pasos con esquema, validadores
- **Fase 4:** revisión en equipo (grupo, allowlist, objeciones, `review_actions`)
- **Fase 5:** publicación automática en Instagram
- **Fase 6:** video · **Fase 7:** métricas y monitor de cuotas
