# TODO.md — Motor JIT SGCD Le Tiende

> Siempre exactamente **2 tareas atómicas**. Al completar una, eliminarla, moverla al historial y calcular la siguiente prioritaria comparando `PRD.md` vs `MEMORY.md`.

---

## Tarea 1 — [FIX]: Corregir nombre de marca, añadir visión multimodal y temas (WF01 + WF02)

**Origen:** Prueba de flujo 2026-04-29 reveló dos problemas:
1. El caption generado no corresponde al contenido real porque Gemini no ve la imagen
2. El system prompt dice "Le Tiende.co" en lugar de "Le Tiende" y describe una marca de moda en lugar de un centro cultural

**Archivos:**
- `n8n-workflows/02-generacion.json` (system prompt, fallbacks, nodo descarga imagen, conexiones)
- `n8n-workflows/01-ingesta.json` (topic_hint desde caption, confirmación)
- `lambda/video-processor/package.json` (descripción)

**Qué hacer:**
1. Corregir system prompt: "Le Tiende.co, marca de tendencias" → "Le Tiende, centro cultural colombiano (librería, café, bar, teatro, vinilos)" con 11 temas explícitos
2. Añadir nodo HTTP Request para descargar la imagen de Cloudinary y pasarla como inlineData a Gemini
3. Incluir los 11 temas en el system prompt (libros, vinilos, teatro, fiestas, conciertos, conversatorios, proyecciones, presentaciones, café, comida, licores)
4. Añadir `topic_hint` en WF01: leer caption del mensaje de Telegram para detectar el tema
5. Pasar `topic_hint` por el webhook de WF01 a WF02
6. Corregir fallbacks en "Parsear respuesta Gemini"
7. Actualizar mensaje de confirmación en WF01 para mostrar el tema detectado

**Definition of done:**
- [ ] WF02 incluye nodo de descarga de imagen y pasa inlineData a Gemini
- [ ] System prompt describe correctamente a Le Tiende como centro cultural con los 11 temas
- [ ] No hay referencias a "Le Tiende.co" en los workflows locales
- [ ] WF01 extrae topic_hint del caption y lo pasa a WF02
- [ ] Cambios desplegados en n8n y probados con una imagen real

---

## Tarea 2 — [TEST]: Desplegar cambios en n8n y ejecutar prueba end-to-end

**Origen:** Los JSONs locales de WF01 y WF02 fueron modificados. Hay que subirlos a n8n y probar el flujo completo con una imagen real.

**Archivos:**
- `n8n-workflows/01-ingesta.json` (modificado)
- `n8n-workflows/02-generacion.json` (modificado)

**Qué hacer:**
1. Importar los workflows modificados a n8n vía API (reemplazando los existentes)
2. Activar ambos workflows
3. Enviar una imagen al bot de Telegram con un caption que indique el tema (ej: "libros")
4. Verificar que el caption generado corresponde al contenido de la imagen y al tema correcto
5. Verificar que el nombre "Le Tiende" aparece correctamente (sin ".co")
6. Verificar que el mensaje de confirmación muestra el tema detectado

**Definition of done:**
- [ ] WF01 y WF02 actualizados en n8n y activos
- [ ] Una imagen de prueba genera caption relevante al contenido visual y al tema correcto
- [ ] El caption NO menciona moda a menos que la imagen sea de moda
- [ ] "Le Tiende" aparece en negrita, sin ".co"

---

## Historial de tareas completadas

| Fecha | Tarea | Resultado |
|---|---|---|
| *(pendiente)* | — | — |

## Backlog (próximas tareas)

- [SEGURIDAD] Validar `secret_token` en webhook de Telegram (OWASP A01)
- [FEATURE] Workflow 05 — Métricas y reporte semanal (PRD §6)
- [FIX] Corregir "Le Tiende.co" en WF05 (prompts en n8n)
