# MEMORY.md — Estado del proyecto SGCD Le Tiende

> Actualizar al cerrar cada sesión de trabajo relevante.

---

## 1. Estado actual

| Campo | Valor |
|---|---|
| Fecha de última sesión | 2026-04-29 |
| Rama principal | `master` |
| URL n8n | https://n8n.letiende.co |
| URL Supabase | https://iljbfgbndwfaqacxthty.supabase.co |
| IP VM Oracle | 150.136.139.189 |
| Fase activa | Fase 2 completada parcialmente — Fase 3 (publicación directa) por iniciar |

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
- [x] Workflow 02 — Generación con IA (Gemini Flash → captions JSON → Supabase)
- [x] Workflow 03 — Revisión HITL (Telegram inline buttons + timeouts 24h/48h)
- [x] Workflow 04 — Publicación (empaquetado + entrega manual por Telegram)
- [x] Credenciales n8n creadas: Telegram Bot SGCD, Supabase SGCD, Gemini SGCD, Cloudinary SGCD
- [x] Lambda video-processor: código listo (`lambda/video-processor/`)
- [ ] **Lambda: deploy a AWS pendiente** (`bash scripts/deploy-lambda.sh`)

### Fase 3 — Publicación directa en RRSS
- [ ] Publicación directa en Instagram Graph API
- [ ] Publicación directa en YouTube Data API v3
- [ ] TikTok (bloqueado por aprobación de API)
- [ ] Canva Autofill (bloqueado por acceso beta)

### Fase 4 — Métricas y ajustes
- [ ] Workflow 05 — Métricas y reporte semanal
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

### ADR-005 — Estado `ready_to_publish` como estado intermedio
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

**Qué se hizo hoy (2026-04-29):**
- Inicialización completa de documentación con Motor JIT
- Creados: `PRD.md`, `tech-specs.md`, `MEMORY.md`, `TODO.md`
- Agregadas secciones de seguridad OWASP y git flow a `CLAUDE.md`
- **Prueba de flujo end-to-end:** Se envió una imagen al bot. WF01→WF02→WF03→WF04 ejecutaron correctamente.
- **Problemas detectados en la prueba:**
  1. Gemini generó caption de moda para la portada de un libro — el modelo no veía la imagen
  2. El system prompt decía "Le Tiende" y "marca colombiana de tendencias"
- **Correcciones aplicadas (en rama `feature/fix-brand-name-and-multimodal-vision`):**
  - WF02: system prompt corregido con descripción precisa de Le Tiende como centro cultural + 11 temas
  - WF02: añadido nodo de descarga de imagen + inlineData multimodal a Gemini
  - WF02: fallbacks corregidos (Le Tiende → Le Tiende)
  - WF01: topic_hint desde caption del mensaje de Telegram + confirmación con tema
  - PRD.md: descripción de Le Tiende corregida
  - TODO.md: tareas reordenadas con la corrección actual como prioridad

**Próxima tarea sugerida:** Ver `TODO.md` — Tarea 2: desplegar cambios en n8n y ejecutar prueba end-to-end.
