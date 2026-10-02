# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0011**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0009 — [OPERACIÓN]: Respaldo completo antes de tocar la plataforma

**Origen:** Plan §4 Fase 0. Las fases 1 y 3 cambian la versión de n8n y reemplazan los workflows; sin respaldo, un fallo no tiene vuelta atrás.

**Archivos:**
- `scripts/backup.sh` (nuevo)
- `.gitignore` (agregar `backups/`)

**Qué hacer:**
1. `scripts/backup.sh` crea `backups/<fecha>/` con:
   - cada workflow vivo exportado por la API de n8n (`GET /api/v1/workflows/{id}`). Mientras el certificado esté vencido, usar `curl -k` solo contra `n8n.letiende.co`, o hacer la llamada por SSH a `localhost:5678`;
   - `pg_dump` de la base de n8n ejecutado en la VM (`docker exec … pg_dump`) y copiado por `scp`;
   - `pg_dump` del esquema y los datos de Supabase.
2. Todos los secretos salen de `credentials.env` (`source`), nunca escritos en el script.
3. Probar la restauración del dump de n8n en un PostgreSQL local temporal (contenedor desechable).

**Definition of done:**
- [ ] `bash scripts/backup.sh` termina sin errores y crea los 3 tipos de respaldo
- [ ] El dump de n8n se restaura en un contenedor local y contiene las tablas `workflow_entity` y `credentials_entity`
- [ ] `backups/` está en `.gitignore` y `git status` no lo muestra

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

- **Fase 0 (después de T-0009):** actualizar paquetes de la VM y reiniciarla (kernel pendiente desde hace semanas)
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
