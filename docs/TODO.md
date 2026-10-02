# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0009**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0008 — [SEGURIDAD]: Rotar credenciales expuestas en texto plano

**Origen:** Plan §4 Fase 0. `.claude/settings.local.json` guarda en reglas de permiso la contraseña de la base de Supabase, un token de gestión `sbp_…` y claves de R2/Cloudflare. El archivo nunca se versionó; la rotación es por higiene.

**Archivos:**
- `credentials.env` (local, ignorado por git)
- `.claude/settings.local.json` (local, ignorado por git)
- `docs/MEMORY.md` (registrar la fecha de rotación, sin valores)

**Qué hacer** (requiere al humano frente al computador, en los dashboards):
1. Supabase → *Project Settings → Database → Reset database password*. Actualizar la variable correspondiente en `credentials.env`.
2. Supabase → *Account → Access Tokens*: revocar el token `sbp_` expuesto y crear uno nuevo solo si hace falta.
3. Cloudflare → *R2 → Manage API tokens*: crear un token R2 nuevo, actualizar `CF_R2_ACCESS_KEY_ID` y `CF_R2_SECRET_ACCESS_KEY`, y revocar el anterior. Revocar también el token `cfut_` expuesto.
4. Si n8n usa las claves de R2 (WF01 sube videos a R2), actualizarlas en la VM (variables del `docker-compose`) y reiniciar n8n.
5. Borrar de `.claude/settings.local.json` todas las reglas que contengan valores secretos.
6. Verificar acceso con `$VARIABLE` (nunca valores literales): listar buckets de R2 y consultar Supabase.

**Definition of done:**
- [ ] Las credenciales antiguas devuelven error de autenticación
- [ ] `grep -E 'sbp_|PGPASSWORD=|cfut_|AWS_SECRET_ACCESS_KEY="' .claude/settings.local.json` no devuelve nada
- [ ] R2 y Supabase responden con las credenciales nuevas cargadas desde `credentials.env`
- [ ] `docs/MEMORY.md` registra la fecha de rotación

---

## Tarea 2 — T-0009 — [OPERACIÓN]: Respaldo completo antes de tocar la plataforma

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

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
| 2026-10-02 | T-0007 | Diagnóstico y plan de actualización | Sistema caído (SSL vencido), visión de Gemini refutada con pruebas, conflicto de webhooks en Telegram. Plan por fases en `docs/plan-actualizacion.md`. |
| 2026-10-02 | T-0005 | Verificar fix de tema (libros vs. vinilos) | **Descartada:** la causa raíz era que Gemini no veía la imagen; se resuelve en la Fase 3. |
| 2026-10-02 | T-0004 | Validar `secret_token` del webhook de Telegram | **Absorbida** por la Fase 3 (router único de Telegram con `secret_token`). |
| 2026-10-02 | T-0006 | Reorganización del repo para reinicio | Docs en `docs/`, tracking de esfuerzo, rama principal renombrada a `main`, escaneo de secretos en CI. |
| 2026-04-30 | T-0003 | Hotfix calidad contenido IA — iteración 1 | Desplegado, pero basado en ADR-007, que resultó falso. |
| 2026-04-30 | T-0002 | Fix brand + multimodal + deploy | Correcciones de WF01/WF02/WF03 sobre n8n 2.12.3. |
| 2026-04-29 | T-0001 | Inicialización docs + Motor JIT | Creados PRD.md, tech-specs.md, MEMORY.md, TODO.md |

## Backlog (orden del plan)

- **Fase 0:** restablecer HTTPS con renovación automática (decidir Caddy vs. certbot webroot)
- **Fase 0:** verificar en AI Studio que el proyecto de Gemini no tiene facturación y anotar RPM/TPM/RPD de los modelos candidatos
- **Fase 1:** n8n 2.41.x con versión fijada y limpieza de `docker-compose.yml`
- **Fase 2:** tabla `pipeline_steps` y vista de tablero
- **Fase 2:** exportación de Instagram y set dorado (15–20 piezas) + script de evaluación
- **Fase 2:** cálculo de capacidad semanal sin costo (plan §3)
- **Fase 3:** router único de Telegram, subworkflows, visión con `inline_data`, generación en 2 pasos con esquema, validadores
- **Fase 4:** revisión en equipo (grupo, allowlist, objeciones, `review_actions`)
- **Fase 5:** publicación automática en Instagram
- **Fase 6:** video · **Fase 7:** métricas y monitor de cuotas
