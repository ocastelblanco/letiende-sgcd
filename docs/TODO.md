# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0012**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0012 — [OPERACIÓN]: Actualizar paquetes de la VM y reiniciarla

**Origen:** Plan §4 Fase 0. La VM lleva 27 semanas sin reiniciar, corre el kernel 6.17.0-1007 con versiones 1009 a 1011 ya instaladas, tiene 63 paquetes pendientes (1 de seguridad) y `/var/run/reboot-required` activo. El respaldo (T-0009) ya existe.

**Archivos:**
- `docs/MEMORY.md` (registrar fecha, kernel y resultado)

**Qué hacer:**
1. Ejecutar `bash scripts/backup.sh` justo antes, para tener un respaldo del mismo día.
2. Por SSH: `sudo apt update && sudo apt upgrade -y`. No ejecutar `do-release-upgrade`: Ubuntu 24.04 LTS tiene soporte hasta 2029.
3. `sudo reboot` y esperar a que la VM vuelva (SSH y contenedores).
4. Verificar: `uname -r` (kernel nuevo), `docker compose ps` (los 3 contenedores arriba sin intervención), `/var/run/reboot-required` ausente, `free -h`.

**Definition of done:**
- [ ] `uname -r` muestra un kernel posterior a 6.17.0-1007 y `reboot-required` ya no existe
- [ ] n8n, postgres y nginx vuelven solos (`restart: always`); `docker exec infrastructure-postgres-1 psql -U n8n -d n8n -tAc "select count(*) from workflow_entity"` devuelve 5
- [ ] `apt list --upgradable` queda en 0 o solo con retenidos justificados

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

- **Fase 0:** restablecer HTTPS con renovación automática (decidir Caddy vs. certbot webroot)
- **Fase 1:** n8n 2.41.x con versión fijada y limpieza de `docker-compose.yml`
- **Fase 1:** instancia de desarrollo local (`infrastructure/docker-compose.dev.yml`) + `N8N_DEV_API_KEY` en `credentials.env`
- **Fase 2:** tabla `pipeline_steps` y vista de tablero
- **Fase 2:** exportación de Instagram y set dorado (15–20 piezas) + script de evaluación
- **Fase 2:** cálculo de capacidad semanal sin costo (plan §3)
- **Fase 3:** router único de Telegram, subworkflows, visión con `inline_data`, generación en 2 pasos con esquema, validadores
- **Fase 4:** revisión en equipo (grupo, allowlist, objeciones, `review_actions`)
- **Fase 5:** publicación automática en Instagram
- **Fase 6:** video · **Fase 7:** métricas y monitor de cuotas
