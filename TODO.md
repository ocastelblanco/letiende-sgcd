# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria comparando `PRD.md` vs `MEMORY.md`.

---

## Tarea 1 — [SEGURIDAD]: Validar secret_token en Webhook de Telegram (Workflow 01)

**Origen:** Riesgo OWASP A01 — el webhook de Telegram no valida la autenticidad del origen. Cualquiera que conozca la URL del webhook puede enviar peticiones falsas al sistema.

**Archivos:**
- `n8n-workflows/01-ingesta.json` (agregar nodo de validación al inicio)

**Qué hacer:**
1. Agregar un nodo **If** inmediatamente después del Telegram Trigger en WF01
2. Condición: validar header `x-telegram-bot-api-secret-token` contra `$env.TELEGRAM_WEBHOOK_SECRET`
3. Si `false`: responder HTTP 403 y detener
4. Si `true`: continuar con el flujo normal
5. Agregar `TELEGRAM_WEBHOOK_SECRET` a `credentials.env.example` y al `docker-compose.yml`
6. Configurar `secret_token` en el webhook de Telegram via `setWebhook`

**Definition of done:**
- [ ] Nodo If de validación existe al inicio de WF01 en n8n
- [ ] Petición sin header correcto retorna 403 y no crea registros
- [ ] `TELEGRAM_WEBHOOK_SECRET` está en `credentials.env.example`
- [ ] Webhook de Telegram configurado con `secret_token`

---

## Tarea 2 — [FIX]: Verificar que el fix de tema (libros vs vinilos) funciona en producción

**Origen:** Prueba con foto de "La clase de griego" de Han Kang generó captions de vinilos. Se aplicó fix en WF01 (guardar topic en `notes`) y WF02 (prioridad absoluta al tema indicado).

**Archivos:**
- `n8n-workflows/01-ingesta.json`
- `n8n-workflows/02-generacion.json`

**Definition of done:**
- [ ] Subir foto de libro con caption "Libros" genera captions de libros, no vinilos
- [ ] Subir foto de vinilo con caption "Vinilos" genera captions de vinilos
- [ ] Hashtags corresponden al tema indicado

---

## Historial de tareas completadas

| Fecha | Tarea | Resultado |
|---|---|---|
| 2026-04-30 | Hotfix calidad contenido IA — iteración 1 (Tarea 1 original) | Gemini analiza imágenes vía URL pública. System prompt con tuteo bogotano y reglas de hashtags. WF03 divide mensaje en 2 partes. Deploy exitoso. |
| 2026-04-30 | Fix brand + multimodal + deploy | Flujo end-to-end funcional. Gemini 3 Flash Preview genera contenido. 11 bugs de n8n 2.12.3 corregidos. |
| 2026-04-29 | Inicialización docs + Motor JIT | Creados PRD.md, tech-specs.md, MEMORY.md, TODO.md |

## Backlog (próximas tareas)

- [FEATURE] Workflow 05 — Métricas y reporte semanal (PRD §6)
- [FIX] Corregir "Le Tiende.co" en prompts de WF05 en n8n
- [FEATURE] Publicación directa en Instagram Graph API
- [FEATURE] Publicación directa en YouTube Data API v3
- [FEATURE] Monitor diario de cuotas y alertas (cron 09:00)
