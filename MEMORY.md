# MEMORY.md — Estado del proyecto SGCD Le Tiende

> Actualizar al cerrar cada sesión de trabajo relevante.

---

## 1. Estado actual

| Campo | Valor |
|---|---|
| Fecha de última sesión | 2026-04-30 |
| Rama activa | `feature/fix-brand-name-and-multimodal-vision` |
| URL n8n | https://n8n.letiende.co |
| URL Supabase | https://iljbfgbndwfaqacxthty.supabase.co |
| IP VM Oracle | 150.136.139.189 |
| Fase activa | Fase 2 completada — Fase 3 (publicación directa) por iniciar |
| Flujo end-to-end | ✅ Funcional — pendiente hotfix de calidad de contenido IA |

---

## 2. Funcionalidades completadas vs. pendientes

### Fase 1 — Infraestructura base
- [x] Repositorio Git con `.gitignore` y `credentials.env.example`
- [x] DNS Route 53 → registro A `n8n.letiende.co` → 150.136.139.189
- [x] Oracle Cloud VM con Docker + Docker Compose
- [x] Nginx con SSL Let's Encrypt (TLSv1.2+)
- [x] Stack Docker: n8n v2.12.3 + PostgreSQL 15 + Nginx
- [x] Cloudflare R2: 3 buckets creados con lifecycle rules (30/90 días)
- [x] Supabase: schema.sql aplicado (5 tablas + triggers)
- [x] Migration-001 aplicada (estado `ready_to_publish`)

### Fase 2 — Workflows de ingesta y generación
- [x] Workflow 01 — Ingesta (Telegram → Cloudinary/R2 → Supabase)
- [x] Workflow 02 — Generación con IA (Gemini 3 Flash Preview → captions → Supabase)
- [x] Workflow 03 — Revisión HITL (Telegram inline buttons + timeouts 24h/48h)
- [x] Workflow 04 — Publicación (empaquetado + entrega manual por Telegram)
- [x] Workflow 05 — Métricas y Reporte Semanal (creado en n8n, exportado localmente)
- [x] Credenciales n8n: Telegram Bot, Supabase, Gemini (httpHeaderAuth), Cloudinary
- [ ] **Hotfix calidad de contenido IA** (visión, tono colombiano, hashtags precisos, captions completos)
- [ ] Lambda video-processor: deploy a AWS pendiente
- [ ] Validación `secret_token` en webhook Telegram (OWASP A01)

### Fase 3 — Publicación directa en RRSS
- [ ] Publicación directa en Instagram Graph API
- [ ] Publicación directa en YouTube Data API v3
- [ ] TikTok (bloqueado por aprobación de API)

### Fase 4 — Métricas y ajustes
- [ ] Monitor diario de cuotas (cron 09:00)
- [ ] Pruebas de carga y escenarios de error

---

## 3. ADRs (Architecture Decision Records)

### ADR-001 — Split de almacenamiento: Cloudinary (imágenes) + R2 (videos)
- **Fecha:** Semana 1 del proyecto
- **Estado:** Activo
- **Decisión:** Cloudinary para imágenes, Cloudflare R2 para videos
- **Razón:** El plan gratuito de Cloudinary permite solo 25 créditos/mes — los videos de gran tamaño los agotarían en días. R2 ofrece almacenamiento muy económico para archivos grandes sin límite práctico.
- **Consecuencias:** Dos sistemas de storage a gestionar; los workflows deben enrutar por tipo de activo.

### ADR-002 — Oracle Cloud Free Tier como infraestructura principal
- **Fecha:** Semana 1 del proyecto
- **Estado:** Activo
- **Decisión:** Usar Oracle Cloud VM gratuita (VM.Standard.A1.Flex ARM o E2.1.Micro) en lugar de n8n Cloud o un VPS de pago.
- **Razón:** Costo cero es un requisito de viabilidad del proyecto en esta etapa.
- **Consecuencias:** La instancia ARM tiene limitaciones (forma A1 no siempre disponible al crear — script `retry-a1-instance.sh`); si Oracle cambia las políticas de Free Tier, migración necesaria.

### ADR-003 — TikTok Plan B: entrega manual vía Telegram
- **Fecha:** Semana 2 del proyecto
- **Estado:** Activo
- **Decisión:** El Workflow 04 entrega el paquete de TikTok por Telegram para publicación manual.
- **Razón:** La API de TikTok Content Posting requiere aprobación que no está garantizada. No se puede asumir acceso.
- **Consecuencias:** `TIKTOK_API_APPROVED=false` por defecto. Cuando (y si) se apruebe, activar con `true` y activar la rama de API en WF4.

### ADR-004 — PostgreSQL en lugar de SQLite para n8n
- **Fecha:** Semana 1 del proyecto
- **Estado:** Activo
- **Decisión:** n8n usa PostgreSQL como backend de estado.
- **Razón:** SQLite no soporta escrituras concurrentes. Con múltiples workflows activos simultáneamente, SQLite causaría bloqueos.
- **Consecuencias:** Requiere PostgreSQL en el mismo Docker Compose; añade un servicio más al stack.

### ADR-006 — Gemini 3 Flash Preview como modelo de generación
- **Fecha:** 2026-04-30
- **Estado:** Activo
- **Decisión:** Usar `gemini-3-flash-preview` para generación de contenido.
- **Razón:** `gemini-1.5-flash` fue deprecado y `gemini-2.0-flash` dejó de aceptar nuevos usuarios. `gemini-2.5-flash` funciona pero devuelve 503 frecuentemente por alta demanda. `gemini-3-flash-preview` tiene disponibilidad consistente.
- **Consecuencias:** El modelo es preview y puede cambiar. `maxOutputTokens` debe ser al menos 8192 para que la respuesta JSON completa no se trunque.

### ADR-007 — Text-only prompt para Gemini (sin visión multimodal por ahora)
- **Fecha:** 2026-04-30
- **Estado:** Temporal — pendiente de resolver
- **Decisión:** No pasar la imagen a Gemini. El system prompt incluye los 11 temas y Gemini genera contenido basado solo en texto.
- **Razón:** n8n 2.12.3 usa `filesystem-v2` para almacenar binarios descargados con `responseFormat: "file"`. El valor `$input.first().binary.data.data` devuelve la cadena `"filesystem-v2"` en lugar de base64. `this.helpers.getBinaryDataBuffer()` tampoco funcionó. Gemini rechaza `"filesystem-v2"` como base64 válido.
- **Consecuencias:** Gemini genera contenido relevante al centro cultural pero no sabe qué hay exactamente en la imagen. El hotfix actual debe resolver esto (File API, descripción manual, u otra alternativa).

### ADR-008 — HTTP Request nodes con `specifyBody: "json"` + `jsonBody` (no `body`)
- **Fecha:** 2026-04-30
- **Estado:** Activo — regla para todos los nodos HTTP
- **Decisión:** En n8n 2.12.3, todos los nodos HTTP Request que envían JSON deben usar `specifyBody: "json"` + `jsonBody` en lugar de `body` + `contentType: "json"`.
- **Razón:** n8n 2.12.3 auto-añade `bodyParameters: { parameters: [{"name": "", "value": ""}] }` cuando se configura `contentType: "json"` sin `specifyBody`. Esto causa que el campo `body` sea ignorado y se envíe `{"":""}`.
- **Consecuencias:** Todos los nodos HTTP que envían JSON deben seguir este patrón. Ya aplicado en WF01, WF02, WF03.

### ADR-009 — Eliminación de nodos Merge v3
- **Fecha:** 2026-04-30
- **Estado:** Activo
- **Decisión:** Eliminar todos los nodos Merge v3 y conectar las ramas directamente al destino.
- **Razón:** Merge v3 en n8n 2.12.3 crashea consistentemente tras redeploy vía PUT, en todos los modos probados (`passThrough` → "Cannot read properties of undefined (reading 'execute')", `combine` + `multiplex` → requiere items de ambos inputs, `combine` + `mergeByPosition` → requiere "Fields to Match"). Conectar múltiples fuentes al mismo nodo HTTP funciona correctamente.
- **Consecuencias:** Sin Merge, `$json[0].id` ya no funciona (Supabase devuelve objeto único, no array). Referencias entre workflows deben usar `$('NodeName').first().json.id` en Code nodes, o pasar el UUID explícitamente.
- **Fecha:** Post-diseño inicial (migration-001)
- **Estado:** Temporal — se eliminará cuando exista publicación directa
- **Decisión:** Agregar el estado `ready_to_publish` entre `publishing` y `published`.
- **Razón:** El Workflow 04 empaqueta y entrega el contenido por Telegram, pero no publica directamente. Se necesita un estado que indique "paquete entregado, publicación manual pendiente".
- **Consecuencias:** Cuando se implemente publicación directa en RRSS, este estado puede eliminarse del CHECK constraint.

---

## 4. Dependencias instaladas

| Paquete | Versión | Entorno | Archivo |
|---|---|---|---|
| n8n | 2.12.3 (latest en el momento del deploy) | Docker VM | `infrastructure/docker-compose.yml` |
| postgres | 15-alpine | Docker VM | `infrastructure/docker-compose.yml` |
| nginx | alpine | Docker VM | `infrastructure/docker-compose.yml` |
| @aws-sdk/client-s3 | ^3.x | Lambda Node 20 | `lambda/video-processor/package.json` |
| FFmpeg | Sistema (dnf install) | Lambda Docker | `lambda/video-processor/Dockerfile` |

---

## 5. Configuraciones vigentes

| Servicio | Configuración | Valor |
|---|---|---|
| Oracle VM | IP pública | 150.136.139.189 |
| n8n | Dominio | n8n.letiende.co |
| Supabase | Project ref | iljbfgbndwfaqacxthty |
| Cloudinary | Cloud name | letiende |
| R2 | Endpoint | https://424b011991022bd9f953ebc622e59f4f.r2.cloudflarestorage.com |
| Telegram | Approver chat ID | -5249716260 |
| Telegram | Admin chat ID | -5249716260 |
| AWS | Region | us-east-1 |
| n8n | Executions data max age | 336 horas (14 días) |

---

## 6. Patrones de código establecidos

### Llamada a Supabase desde n8n (HTTP node)

```javascript
// GET con filtro
URL: {{ $env.SUPABASE_URL }}/rest/v1/content_items?id=eq.{{ $json.content_item_id }}&select=*
Headers: { "apikey": "{{ $env.SUPABASE_SERVICE_ROLE_KEY }}", "Authorization": "Bearer {{ $env.SUPABASE_SERVICE_ROLE_KEY }}" }

// PATCH (actualizar)
Method: PATCH
URL: {{ $env.SUPABASE_URL }}/rest/v1/content_items?id=eq.{{ $json.content_item_id }}
Headers: + "Content-Type": "application/json", "Prefer": "return=representation"
Body: { "status": "processing", "updated_at": "{{ $now.toISO() }}" }
```

### Llamada a Gemini Flash desde n8n

```javascript
Method: POST
URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
Headers: { "x-goog-api-key": "{{ $env.GEMINI_API_KEY }}", "Content-Type": "application/json" }
Body: {
  "system_instruction": { "parts": [{ "text": "SYSTEM_PROMPT" }] },
  "contents": [{ "parts": [{ "text": "USER_PROMPT" }] }],
  "generationConfig": { "temperature": 0.7, "maxOutputTokens": 2048 }
}
```

### Notificación de error a Telegram

```javascript
// Siempre incluir en el nodo Error Trigger de cada workflow
Method: POST
URL: https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage
Body: {
  "chat_id": "{{ $env.TELEGRAM_ADMIN_CHAT_ID }}",
  "text": "❌ Error en {{ $workflow.name }}: {{ $json.error.message }}"
}
```

---

## 7. Gotchas conocidos

| Situación | Causa | Solución |
|---|---|---|
| R2 con AWS CLI da error de "chunked encoding" | La API de R2 no acepta chunked transfer encoding | Usar Python boto3 con `payload_signing_enabled=False` (ver `setup-r2.sh`) |
| "Environment Variables" en n8n es Enterprise | La UI de n8n Enterprise tiene una sección dedicada; en free tier no existe | Inyectar todas las variables en `docker-compose.yml` bajo `n8n.environment` |
| `exec_sql` en Supabase REST no funciona | Supabase no expone RPC de SQL genérico por defecto | Usar `psql` directo o el SQL Editor en `https://iljbfgbndwfaqacxthty.supabase.co` |
| IDs de credenciales hardcodeados en workflows JSON | n8n referencia credenciales por ID interno | Crear las credenciales ANTES de importar los workflows, con los nombres exactos (ver `docs/fase2-setup-n8n.md`) |
| Workflow 04 no publica en RRSS | Diseño actual: entrega manual por Telegram | El estado `ready_to_publish` indica que el paquete fue enviado al aprobador; la publicación directa está en el roadmap |
| Shape A1 de Oracle no siempre disponible al crear | Disponibilidad limitada de instancias ARM gratuitas | Usar `scripts/retry-a1-instance.sh` que reintenta hasta encontrar disponibilidad |
| n8n webhook URL cambia si se recrea el contenedor | n8n genera el webhook ID al crear el nodo | Al importar un workflow nuevo, verificar y actualizar el webhook en @BotFather si cambió |
| **n8n: Merge v3 crashea tras redeploy** | n8n 2.12.3: Merge v3 en `passThrough` crashea con "Cannot read properties of undefined (reading 'execute')" después de PUT | Eliminar Merge v3. Conectar múltiples fuentes directo al nodo destino. n8n acepta múltiples conexiones entrantes a un HTTP Request. |
| **n8n: `body` ignorado en HTTP Request** | n8n 2.12.3 auto-añade `bodyParameters` vacíos cuando `contentType: "json"` sin `specifyBody` | Usar `specifyBody: "json"` + `jsonBody` en todos los nodos HTTP con JSON. |
| **n8n: `httpHeaderAuth` no envía `apikey`** | Tras redeploy, la credencial `httpHeaderAuth` de Supabase no incluye el header `apikey` | Añadir header `apikey` explícito con `={{ $env.SUPABASE_SERVICE_ROLE_KEY }}` en cada nodo Supabase. |
| **n8n: binarios como `filesystem-v2`** | `responseFormat: "file"` guarda referencia `"filesystem-v2"`, no datos accesibles como base64 | No usar inlineData para Gemini. Alternativas: File API de Gemini, descripción manual, o investigar `getBinaryDataBuffer()`. |
| **n8n: `$()` no resuelve en body de HTTP Request** | `$('NodeName')` en expresiones de body (`"={{ ... }}"`) no resuelve correctamente | Usar Code node para preparar el payload, luego HTTP Request con `$json`. |
| **Gemini: 1.5 Flash deprecado** | Modelo `gemini-1.5-flash` ya no existe | Usar `gemini-3-flash-preview` con `maxOutputTokens: 8192`. |
| **Gemini: respuesta JSON truncada** | `maxOutputTokens: 2048` insuficiente para JSON con caption + hashtags + todas las plataformas | Subir a `8192`. Verificar `finishReason` en la respuesta. |
| **Telegram: webhook se reasigna a WF03** | WF03 tiene su propio TelegramTrigger que sobreescribe el webhook al activarse | Después de cada deploy de WF03, re-ejecutar `setWebhook` apuntando a WF01. |
| **Supabase: respuesta como objeto, no array** | Con `return=representation`, Supabase devuelve un objeto único (no `[{...}]`) | Usar `Array.isArray(data) ? data[0] : data` en Code nodes. |
| **Supabase: columnas desconocidas dan 400** | PostgREST rechaza columnas que no existen en la tabla | Verificar el schema de Supabase antes de enviar campos en el body. `asset_provider`, `file_name`, `mime_type`, `file_size`, `telegram_chat_id`, `suggested_time_note` NO existen en `content_items`. |
| **Cloudinary: upload_preset requerido** | Tras redeploy, Cloudinary trata el upload como "unsigned" y exige preset | Crear preset `letiende_sgcd` (unsigned, folder=raw) y añadir `upload_preset` + `api_key` al form. |

---

## 8. Documentos de referencia

| Documento | Ruta | Contenido |
|---|---|---|
| CLAUDE.md | `./CLAUDE.md` | Instrucciones de trabajo para agentes IA, plan de fases |
| PRD.md | `./PRD.md` | Requisitos de producto, roadmap, casos de uso |
| tech-specs.md | `./tech-specs.md` | Arquitectura, stack, endpoints, contratos de API |
| MEMORY.md | `./MEMORY.md` | Este archivo — estado, ADRs, gotchas |
| TODO.md | `./TODO.md` | Motor JIT — exactamente 2 tareas atómicas activas |
| Guía de infraestructura | `docs/fase1-guia-replicable.md` | Setup completo desde cero (Fase 1) |
| Setup de n8n | `docs/fase2-setup-n8n.md` | Credenciales y configuración de n8n antes de importar workflows |
| Spec técnica legacy | `docs/especificaciones-tecnicas.md` | Referencia histórica de diseño original |
| Credenciales | `docs/credenciales.md` | Dónde y cómo obtener cada credencial |
| Comandos Telegram | `docs/telegram-commands.md` | Referencia de usuario final del bot |

---

## 9. Contexto de la sesión actual

**Qué se hizo (2026-04-30):**

- **Prueba de flujo end-to-end:** Se probó el pipeline completo con una imagen real.
- **11 bugs de n8n 2.12.3 corregidos** (ver sección 7 — Gotchas).
- **Correcciones aplicadas en rama `feature/fix-brand-name-and-multimodal-vision`:**
  - WF01: upload_preset Cloudinary, apikey header Supabase, jsonBody, sin Merge, Code node para Trigger WF2
  - WF02: Gemini 3 Flash Preview, system prompt corregido (Le Tiende centro cultural + 11 temas), sin Merge, sin inlineData, maxOutputTokens 8192
  - WF03: httpHeaderAuth en vez de supabaseApi, apikey headers, jsonBody, caption truncado a 900 chars
  - WF05: exportado localmente, modelo Gemini actualizado
  - PRD.md: corregida descripción de Le Tiende, añadidos requisitos de calidad de contenido
  - TODO.md: hotfix priorizado como Tarea 1
  - CLAUDE.md: añadida referencia completa de estructura JSON de workflows n8n
  - Documentación: eliminado "Le Tiende.co" de todos los archivos
- **Documentación generada:** estructura JSON de workflows n8n documentada en CLAUDE.md, 6 ADRs nuevos, 12 gotchas nuevos en MEMORY.md

**Problemas pendientes (Hotfix Tarea 1 en TODO.md):**
1. Gemini no ve la imagen — evaluar File API, descripción manual, o extracción de base64
2. Tono: forzar tuteo bogotano, prohibir voseo
3. Hashtags: precisos por tema, no mezclar entre temas
4. Captions completos de YouTube y TikTok en mensaje de revisión
