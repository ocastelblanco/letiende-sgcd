# Comandos del Bot de Telegram — SGCD Le Tiende.co

Este documento lista todos los comandos disponibles para los usuarios del bot.

## Comandos de ingesta

| Comando / Acción | Descripción |
|---|---|
| Enviar foto | Ingresa una imagen al pipeline (máx. 20 MB) |
| Enviar video | Ingesta un video al pipeline (máx. 200 MB) |
| Enviar documento de imagen | Imagen sin compresión de Telegram |

## Botones de revisión (aparecen automáticamente)

| Botón | Acción |
|---|---|
| ✅ Aprobar | Aprueba el contenido y lo programa para publicación |
| ✏️ Editar | Permite editar el caption antes de aprobar |
| 🔄 Regenerar | Vuelve a generar el contenido con IA |
| ❌ Descartar | Descarta el contenido permanentemente |

## Flujo de edición

Cuando presionas **✏️ Editar**, el bot solicita el nuevo texto en este orden:
1. Caption para Instagram (o `/saltar` para mantener el actual)
2. Confirmación antes de guardar

## Formatos soportados

**Imágenes:** JPG, PNG, WebP, GIF (máx. 20 MB)
**Videos:** MP4, MOV, AVI (máx. 200 MB)

## Recordatorios automáticos

El sistema envía recordatorios cuando un contenido lleva tiempo pendiente:
- **24 horas:** Primer recordatorio
- **48 horas:** El contenido pasa a estado "bloqueado" y se notifica al equipo
