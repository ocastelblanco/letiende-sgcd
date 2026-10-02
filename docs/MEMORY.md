# MEMORY.md — Estado del proyecto SGCD Le Tiende

> Actualizar al cerrar cada sesión de trabajo relevante.

---

## 1. Estado actual

| Campo | Valor |
|---|---|
| Fecha de última sesión | 2026-10-02 |
| Rama principal | `main` (protegida: exige PR) |
| URL n8n | https://n8n.letiende.co |
| URL Supabase | https://iljbfgbndwfaqacxthty.supabase.co |
| IP VM Oracle | 150.136.139.189 |
| Plan vigente | `docs/plan-actualizacion.md` — **Fase 0** (restablecer, respaldar, asegurar) |
| Estado del servicio | ❌ **Caído**: certificado SSL vencido el 2026-06-18 (Telegram no entrega al bot) |
| Flujo end-to-end | ❌ Nunca completó un ciclo: 26 items de prueba, 0 aprobados (8 `ingested`, 7 `processing`, 11 `ready_for_review`) |
| VM | E2.1.Micro — 2 vCPU, 954 MB RAM, swap 2 GB (455 MB en uso) |
| Capacidad semanal sin costo | Pendiente de cálculo (plan §3) |

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
- [x] **Hotfix calidad de contenido IA** (visión por URL, tono bogotano, hashtags precisos, captions completos en 2 mensajes)
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

### ADR-007 — Visión multimodal vía URL pública en prompt de texto
- **Fecha:** 2026-04-30
- **Estado:** ❌ **REFUTADO (2026-10-02)** — reemplazado por ADR-011
- **Prueba de refutación:** con la URL de Cloudinary de *La clase de griego* en el texto, `gemini-3-flash-preview` describió en tres corridas un Listerine, un vino chileno y un portátil Lenovo. La API no descarga URLs escritas en el prompt; el modelo inventa. Con la imagen enviada como `inline_data` la describió correctamente. El texto original se conserva abajo solo como registro histórico.
- **Decisión:** Pasar la URL pública de la imagen (Cloudinary) directamente en el prompt de texto de Gemini, en lugar de usar inlineData o File API.
- **Razón:** n8n 2.12.3 usa `filesystem-v2` para almacenar binarios descargados con `responseFormat: "file"`, haciendo imposible extraer base64 accesible. La File API de Gemini requiere multipart upload que es difícil de construir en n8n 2.12.3. Sin embargo, `gemini-3-flash-preview` puede analizar imágenes desde URLs públicas cuando la URL está incluida en el texto del prompt: `La imagen está disponible en: https://res.cloudinary.com/...`.
- **Consecuencias:** Gemini ahora "ve" la imagen y genera contenido preciso para el tema detectado. No se requiere descarga de binarios ni File API. Las imágenes deben tener URL pública accesible (Cloudinary lo garantiza).

### ADR-008 — HTTP Request nodes con `specifyBody: "json"` + `jsonBody` (no `body`)
- **Fecha:** 2026-04-30
- **Estado:** Activo — regla para todos los nodos HTTP
- **Decisión:** En n8n 2.12.3, todos los nodos HTTP Request que envían JSON deben usar `specifyBody: "json"` + `jsonBody` en lugar de `body` + `contentType: "json"`.
- **Razón:** n8n 2.12.3 auto-añade `bodyParameters: { parameters: [{"name": "", "value": ""}] }` cuando se configura `contentType: "json"` sin `specifyBody`. Esto causa que el campo `body` sea ignorado y se envíe `{"":""}`.
- **Consecuencias:** Todos los nodos HTTP que envían JSON deben seguir este patrón. Ya aplicado en WF01, WF02, WF03.

### ADR-010 — Mensaje de revisión dividido en 2 partes (Telegram)
- **Fecha:** 2026-04-30
- **Estado:** Activo
- **Decisión:** El mensaje de revisión HITL en Telegram se envía en 2 mensajes separados: (1) media + caption de Instagram + botones, (2) texto con captions completos de YouTube y TikTok.
- **Razón:** Telegram limita los captions de media a 1024 caracteres. Un solo mensaje con Instagram + YouTube + TikTok truncaba los captions de YouTube a 150 chars. Dividiendo en 2 mensajes, cada plataforma muestra su texto completo.
- **Consecuencias:** El aprobador recibe 2 notificaciones por contenido. Los botones de acción (aprobar/editar/regenerar/descartar) solo aparecen en el primer mensaje. El segundo mensaje es informativo solo.

### ADR-011 — Visión con la imagen enviada como datos (`inline_data`)
- **Fecha:** 2026-10-02
- **Estado:** Aceptado (se implementa en la Fase 3)
- **Decisión:** la imagen viaja a Gemini como base64 en `inline_data`, obtenida en un Code node con `this.helpers.getBinaryDataBuffer()`.
- **Razón:** prueba directa (ver ADR-007). El bloqueo `filesystem-v2` de n8n se resuelve con ese helper, que lee el binario sin importar dónde está guardado.
- **Consecuencias:** Cloudinary deja de ser necesario para la visión; sigue sirviendo para variantes de tamaño y URLs públicas de publicación.

### ADR-012 — Una sola entrada de Telegram y subworkflows
- **Fecha:** 2026-10-02
- **Estado:** Aceptado (Fase 3)
- **Decisión:** un único workflow con Telegram Trigger (`message` + `callback_query`, con `secret_token`) despacha a subworkflows mediante `Execute Workflow`. Se eliminan las llamadas HTTP entre workflows por la URL pública.
- **Razón:** Telegram admite un solo webhook por bot. WF01 y WF03 se lo quitaban mutuamente y los botones de aprobación no llegaban a ningún flujo.
- **Consecuencias:** se reemplazan los gotchas "webhook se reasigna a WF03" y los triggers HTTP entre flujos.

### ADR-013 — Costo cero garantizado por diseño en Gemini
- **Fecha:** 2026-10-02
- **Estado:** Aceptado
- **Decisión:** el proyecto de Gemini opera sin facturación habilitada. Ante un 429 el item pasa a `waiting_quota` y se reintenta tras el reinicio diario (medianoche del Pacífico).
- **Razón:** el objetivo de costo cercano a USD 0. Sin facturación, exceder la cuota no genera cobro.
- **Consecuencias:** el volumen está acotado por la cuota gratuita; la capacidad semanal se calcula según el plan §3. Google puede usar el contenido de la capa gratuita para mejorar sus productos (aceptado: es contenido que se publica).

### ADR-014 — n8n-mcp local y entorno de desarrollo
- **Fecha:** 2026-10-02
- **Estado:** Aceptado (servidor instalado; la instancia dev llega en la Fase 1)
- **Decisión:** usar el servidor MCP `n8n-mcp` (MIT) en local, versión fijada, lanzado por `scripts/n8n-mcp.sh`, que carga `credentials.env` en tiempo de ejecución y desactiva la telemetría. Registrado en Claude Code con ámbito local: `claude mcp add -s local n8n-mcp -- "$(pwd)/scripts/n8n-mcp.sh"`. Los workflows se construyen en una instancia n8n de desarrollo en Docker local (`N8N_MCP_TARGET=dev`) y no en producción.
- **Razón:** el servicio hosted (`dashboard.n8n-mcp.com`) limita el plan gratuito a 100 llamadas/día, insuficientes para la Fase 3, y exige entregar la API key de n8n a un tercero. El servidor valida contra el esquema real de los nodos, que ataca la causa de los JSON escritos a mano con versiones viejas. El propio proyecto advierte no editar producción con IA.
- **Consecuencias:** las herramientas de gestión no funcionan contra producción hasta restablecer HTTPS (Fase 0). La base de nodos del servidor (n8n 2.41.4) solo coincide con la instancia después de la Fase 1. Actualizar el servidor es un cambio deliberado de `N8N_MCP_VERSION`.

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

| Paquete | Versión en uso | Disponible (2026-10-02) | Entorno | Archivo |
|---|---|---|---|---|
| n8n | 2.12.3 (imagen `latest` sin fijar) | 2.41.6 | Docker VM | `infrastructure/docker-compose.yml` |
| postgres | 15-alpine | 18-alpine | Docker VM | `infrastructure/docker-compose.yml` |
| nginx | alpine | — (se evalúa Caddy) | Docker VM | `infrastructure/docker-compose.yml` |
| Gemini | `gemini-3-flash-preview` | 3.8/3.5 Flash, 3.5/3.1 Flash-Lite, Gemma 4 | API | `n8n-workflows/02-generacion.json` |
| Lambda runtime | Node 20 (sin soporte desde 2026-04) — nunca desplegada | Node 24 LTS | Lambda | `lambda/video-processor/Dockerfile` |
| @aws-sdk/client-s3 | ^3.0.0 | 3.1145.0 | Lambda | `lambda/video-processor/package.json` |
| jest | ^29 | 30.5.2 | Lambda (dev) | `lambda/video-processor/package.json` |
| FFmpeg | Sistema (dnf install) | — | Lambda Docker | `lambda/video-processor/Dockerfile` |

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
| **n8n: binarios como `filesystem-v2`** | `responseFormat: "file"` guarda referencia `"filesystem-v2"`, no datos accesibles como base64 | No usar inlineData para Gemini. Solución adoptada: pasar URL pública de Cloudinary en el prompt de texto. Gemini 3 Flash Preview analiza la imagen desde la URL. |
| **n8n: `$()` no resuelve en body de HTTP Request** | `$('NodeName')` en expresiones de body (`"={{ ... }}"`) no resuelve correctamente | Usar Code node para preparar el payload, luego HTTP Request con `$json`. |
| **Gemini: 1.5 Flash deprecado** | Modelo `gemini-1.5-flash` ya no existe | Usar `gemini-3-flash-preview` con `maxOutputTokens: 8192`. |
| **Gemini: respuesta JSON truncada** | `maxOutputTokens: 2048` insuficiente para JSON con caption + hashtags + todas las plataformas | Subir a `8192`. Verificar `finishReason` en la respuesta. |
| **Telegram: webhook se reasigna a WF03** | Telegram admite un solo webhook por bot; WF01 y WF03 tienen cada uno su Telegram Trigger | ~~Re-ejecutar `setWebhook` a WF01~~ (dejaba sin destino los botones). Solución: router único (ADR-012). |
| **SSL vencido sin aviso** | Certbot instalado en el host con plugin nginx, pero nginx corre en Docker: la renovación nunca funcionó | Fase 0: Caddy (HTTPS automático) o certbot webroot + recarga del contenedor, con verificación de renovación. |
| **Gemini "ve" una URL escrita en el texto** | Falso: la API no descarga URLs del prompt y el modelo inventa con total seguridad | Enviar la imagen como `inline_data` (ADR-011). |
| **`error_log` rechaza el INSERT** | Los manejadores de error envían `created_at`, que no existe en la tabla | Alinear el payload con el esquema real; probar el manejador de errores forzando un fallo. |
| **Contraseñas en `credentials.env`** | El archivo se carga con `source` de bash: los caracteres especiales (`$ & ! # \` espacios) exigen comillas simples | Usar contraseñas alfanuméricas generadas: no necesitan comillas. Si tiene especiales, comillas simples y codificar en `SUPABASE_DB_URL` (`&`→`%26`, `$`→`%24`, `!`→`%21`). |
| **R2: `ListBuckets` da AccessDenied** | El token de R2 está acotado a los buckets del proyecto, no a la cuenta | Normal: verificar con `list-objects-v2 --bucket letiende-raw-assets`. |
| **`N8N_BASIC_AUTH_*` sin efecto** | Desde n8n 1.x la autenticación es la cuenta owner; esas variables se ignoran | Quitar del compose (Fase 1); proteger con owner + 2FA. |
| **Supabase: respuesta como objeto, no array** | Con `return=representation`, Supabase devuelve un objeto único (no `[{...}]`) | Usar `Array.isArray(data) ? data[0] : data` en Code nodes. |
| **Supabase: columnas desconocidas dan 400** | PostgREST rechaza columnas que no existen en la tabla | Verificar el schema de Supabase antes de enviar campos en el body. `asset_provider`, `file_name`, `mime_type`, `file_size`, `telegram_chat_id`, `suggested_time_note` NO existen en `content_items`. |
| **Cloudinary: upload_preset requerido** | Tras redeploy, Cloudinary trata el upload como "unsigned" y exige preset | Crear preset `letiende_sgcd` (unsigned, folder=raw) y añadir `upload_preset` + `api_key` al form. |

---

## 8. Documentos de referencia

| Documento | Ruta | Contenido |
|---|---|---|
| CLAUDE.md | `./CLAUDE.md` | Instrucciones de trabajo para agentes IA, plan de fases |
| PRD.md | `docs/PRD.md` | Requisitos de producto, roadmap, casos de uso |
| tech-specs.md | `docs/tech-specs.md` | Arquitectura, stack, endpoints, contratos de API |
| MEMORY.md | `docs/MEMORY.md` | Este archivo — estado, ADRs, gotchas |
| TODO.md | `docs/TODO.md` | Motor JIT — exactamente 2 tareas atómicas activas |
| Guía de infraestructura | `docs/fase1-guia-replicable.md` | Setup completo desde cero (Fase 1) |
| Setup de n8n | `docs/fase2-setup-n8n.md` | Credenciales y configuración de n8n antes de importar workflows |
| Spec técnica legacy | `docs/especificaciones-tecnicas.md` | Referencia histórica de diseño original |
| Credenciales | `docs/credenciales.md` | Dónde y cómo obtener cada credencial |
| Comandos Telegram | `docs/telegram-commands.md` | Referencia de usuario final del bot |

---

## 9. Contexto de la sesión actual

**2026-10-02 — Reinicio del proyecto (T-0006, T-0007):**
- Repo reorganizado: documentos en `docs/`, tracking de esfuerzo en `metrics/`, rama `master` → `main` protegida, escaneo de secretos (gitleaks y push protection).
- Diagnóstico completo (ver `docs/plan-actualizacion.md` §1): servicio caído por SSL vencido; flujo sin un solo ciclo completo; ADR-007 refutado con pruebas; conflicto de webhooks en Telegram; manejador de errores roto.
- Decisiones del usuario: el equipo es de 3 personas (5 pronto) y todos revisan en un grupo de Telegram con opción de objetar; el paquete manual basta por ahora y la siguiente fase es la publicación automática en Instagram (cuenta Creator vinculada); se acepta la capa gratuita de Gemini; todos los datos de prueba se pueden borrar; el set dorado se arma con publicaciones reales de Instagram.
- **Credenciales rotadas (T-0008, 2026-10-02):** contraseña de la base de Supabase, token de gestión de Supabase y claves de R2 (token acotado a los 3 buckets `letiende-*`). Las viejas fueron rechazadas; las nuevas verificadas (REST, base de datos, API de gestión, lectura/escritura en los 3 buckets) y n8n en la VM recreado con las claves de R2 nuevas. **El token de gestión de Supabase vence ~2026-12-31** (90 días): renovarlo antes de esa fecha.

**Próxima sesión:** T-0009 (respaldo) y T-0011 (límites de Gemini en AI Studio). Después: actualizar y reiniciar la VM (63 paquetes pendientes, kernel nuevo desde hace semanas, 27 semanas sin reiniciar) y restablecer HTTPS.

<details>
<summary>Sesión 2026-04-30 (histórico)</summary>

Se corrigieron 11 problemas de WF01/WF02/WF03 sobre n8n 2.12.3, se reforzó el system prompt (tuteo bogotano, dirección exacta en Teusaquillo, regla de especificidad) y se dividió el mensaje de revisión en dos. Las pruebas de captions fallaban de forma intermitente; hoy se sabe por qué: Gemini nunca recibió la imagen (ADR-007 refutado).
</details>
