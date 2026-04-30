# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria comparando `PRD.md` vs `MEMORY.md`.

---

## Tarea 1 — [HOTFIX]: Corregir tono, hashtags precisos y visión de imagen en WF02

**Origen:** Prueba de flujo 2026-04-30 confirmó que el pipeline funciona end-to-end, pero la calidad del contenido generado por Gemini tiene 4 problemas:

1. **Gemini no ve la imagen** — el intento de pasar inlineData (base64) falló porque n8n 2.12.3 almacena binarios como referencia `filesystem-v2`, no como datos accesibles desde Code nodes. Gemini genera contenido "a ciegas" basándose solo en el system prompt con los 11 temas, sin saber qué hay realmente en la foto.

2. **Tono incorrecto** — Gemini a veces usa voseo ("Descubrí") en lugar de tuteo bogotano ("Descubre"). Debe usar **siempre** español de Colombia, especialmente de Bogotá: solo "tú", nunca "vos".

3. **Hashtags imprecisos** — Gemini mezcla hashtags de temas que no corresponden al contenido (ej: genera `#VinilosColombia` para una imagen de libros). Los hashtags deben ser precisos para el tema detectado o genéricos de Le Tiende.

4. **Captions de YouTube y TikTok truncados** en el mensaje de revisión de Telegram. El mensaje de WF03 muestra solo 150 caracteres del caption de YouTube y corta el de TikTok. Debe mostrar el texto completo para que el aprobador pueda decidir.

**Archivos:**
- `n8n-workflows/02-generacion.json` (system prompt, tono, hashtags, modelo Gemini)
- `n8n-workflows/03-revision.json` (mensaje de revisión con captions completos)

**Qué hacer:**
1. Evaluar y resolver visión multimodal:
   - Opción A: investigar si `this.helpers.getBinaryDataBuffer()` o alternativas pueden extraer base64 real del binario en n8n
   - Opción B: usar la File API de Gemini para subir la imagen y referenciarla por URI
   - Opción C: añadir un campo `description` al enviar la imagen desde Telegram, para que el operador describa el contenido
2. Actualizar system prompt en "Preparar prompt Gemini" (WF02):
   - Instrucción explícita: "Nunca uses voseo. Siempre usa tuteo bogotano (tú, no vos). Ejemplo correcto: 'Descubre', no 'Descubrí'."
   - Instrucción sobre hashtags: "Los hashtags deben ser precisos para el tema detectado. No mezcles hashtags de otros temas."
   - Lista de hashtags genéricos permitidos: `#LeTiende`, `#CulturaBogota`, `#CafeCultural`, `#PuntoDeEncuentro`, `#AgendaCultural`, `#BarCultural`, `#BogotaCultura`, `#DondeIrEnBogota`
3. En "Preparar mensaje Telegram" (WF03):
   - Mostrar caption de YouTube completo (no truncado a 150 chars)
   - Mostrar caption de TikTok completo (no truncado)
   - Mantener el límite de 900 chars en el mensaje total de Telegram

**Definition of done:**
- [ ] Gemini recibe contexto visual de la imagen (descripción, inlineData, o File API)
- [ ] Los captions generados usan tuteo bogotano, sin voseo
- [ ] Los hashtags corresponden al tema del contenido, sin mezclar temas
- [ ] El mensaje de revisión en Telegram muestra captions completos de YouTube y TikTok
- [ ] Prueba con imagen de libro genera hashtags de libros, no de vinilos

---

## Tarea 2 — [SEGURIDAD]: Validar secret_token en Webhook de Telegram (Workflow 01)

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

## Historial de tareas completadas

| Fecha | Tarea | Resultado |
|---|---|---|
| 2026-04-30 | Fix brand + multimodal + deploy | Flujo end-to-end funcional. Gemini 3 Flash Preview genera contenido. 11 bugs de n8n 2.12.3 corregidos. |
| 2026-04-29 | Inicialización docs + Motor JIT | Creados PRD.md, tech-specs.md, MEMORY.md, TODO.md |

## Backlog (próximas tareas)

- [FEATURE] Workflow 05 — Métricas y reporte semanal (PRD §6)
- [FIX] Corregir "Le Tiende.co" en prompts de WF05 en n8n
- [FEATURE] Publicación directa en Instagram Graph API
- [FEATURE] Publicación directa en YouTube Data API v3
- [FEATURE] Monitor diario de cuotas y alertas (cron 09:00)
