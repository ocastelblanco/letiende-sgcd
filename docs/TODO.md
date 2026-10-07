# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria según `docs/plan-actualizacion.md` y `docs/MEMORY.md`.
>
> Cada tarea lleva un `trace_id` con formato `T-NNNN` (correlativo, nunca se reutiliza). Es el que referencian los eventos de `metrics/events/`. Último asignado: **T-0019**.

**Fase activa:** Fase 0 — Restablecer, respaldar y asegurar (ver `docs/plan-actualizacion.md` §4).

---

## Tarea 1 — T-0019 — [INFRA]: Cierre de Fase 1 — confirmar 72 h estable de n8n 2.41.6

**Origen:** Plan §4 (criterio de salida de Fase 1) y backlog. Producción corre n8n 2.41.6 desde el 2026-10-03 16:30 (Bogotá); las 72 h se cumplieron el 2026-10-06 16:30.

**Archivos:**
- `docs/MEMORY.md` y `docs/plan-actualizacion.md` (estado de la Fase 1)

**Qué hacer:**
1. Por SSH a la VM: reinicios del contenedor n8n (`docker inspect` → `RestartCount`, `StartedAt`), memoria (`free -m`, `docker stats --no-stream`) y CPU desde el despliegue.
2. Revisar errores en `docker logs` de n8n y Caddy desde el 2026-10-03, y `getWebhookInfo` de Telegram (pendientes y último error).
3. Comprobar que los 5 workflows siguen activos y que `/healthz/readiness` responde.
4. Registrar RAM y CPU en MEMORY.md. Si la memoria disponible es insuficiente, evaluar la VM ARM A1.Flex (ADR-002).

**Definition of done:**
- [ ] 0 reinicios inesperados y sin errores nuevos en 72 h, o causas documentadas
- [ ] RAM y CPU registradas con fecha en `docs/MEMORY.md`
- [ ] Fase 1 marcada como cerrada en el plan, o decisión sobre la VM ARM registrada

---

## Tarea 2 — T-0011 — [DECISIÓN]: Estrategia de costo de Gemini con la cuenta de pago

**Origen:** Plan §3, ADR-013. La cuenta de AI Studio ya es de pago, así que la clave actual cobra desde el primer token y el "costo cero por diseño" ya no se cumple. Hay que decidir cómo cumplir el objetivo de costo cercano a USD 0.

**Archivos:**
- `docs/MEMORY.md` (ADR-013 actualizado)
- `docs/plan-actualizacion.md` (§2 y §3)

**Decisión provisional del usuario (2026-10-03):** mantener el proyecto actual (facturación prepago, tope mensual de COP 5.000) para medir el consumo con las vistas de `pipeline_steps`, y decidir después si seguir o crear otro proyecto. Quedan pendientes la tabla de límites y la verificación del tope; la tarea no se cierra hasta tener datos.

**Opciones a evaluar con el usuario:**
1. **Proyecto separado sin facturación** para el flujo: la capa gratuita se aplica por proyecto y una cuenta de pago puede tener otros proyectos sin facturación. Costo cero garantizado; el volumen queda limitado por la cuota gratuita.
2. **Quedarse en el proyecto de pago** con el modelo más barato que pase el set dorado, tope de presupuesto y alerta. Costo del orden de centavos, con mayor cuota.
3. **Híbrido:** proyecto gratuito por defecto y el de pago solo como respaldo cuando se agote la cuota.

**Qué hacer** (requiere al usuario en AI Studio y en Google Cloud):
1. Elegir la opción y, si es la 1 o la 3, crear el proyecto sin facturación y su clave; anotar RPM, TPM y RPD de los modelos candidatos en `aistudio.google.com/rate-limit`.
2. Si es la 2 o la 3: fijar un presupuesto mensual con alerta en Google Cloud Billing.
3. Actualizar ADR-013 y el cálculo de capacidad semanal.

**Definition of done:**
- [ ] Opción elegida y registrada en el ADR-013
- [ ] Tabla de límites de al menos 5 modelos del proyecto elegido en `docs/MEMORY.md`, con fecha
- [ ] Si hay facturación: presupuesto mensual y alerta configurados; si no: confirmación de que el proyecto no tiene facturación

---

## Historial de tareas

| Fecha | trace_id | Tarea | Resultado |
|---|---|---|---|
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
