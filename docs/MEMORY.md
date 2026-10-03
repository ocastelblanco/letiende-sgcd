# MEMORY.md — Estado del proyecto SGCD Le Tiende

> Actualizar al cerrar cada sesión de trabajo relevante.

---

## 1. Estado actual

| Campo | Valor |
|---|---|
| Fecha de última sesión | 2026-10-03 |
| Rama principal | `main` (protegida: exige PR) |
| URL n8n | https://n8n.letiende.co |
| URL Supabase | https://iljbfgbndwfaqacxthty.supabase.co |
| IP VM Oracle | 150.136.139.189 |
| Plan vigente | `docs/plan-actualizacion.md` — **Fase 0** (restablecer, respaldar, asegurar) |
| Estado del servicio | ✅ HTTPS con Caddy (certificado hasta 2027-01-01, se renueva solo). n8n **2.41.6** en producción desde 2026-10-03 16:30 (hora de Bogotá), 5 workflows activos. Los flujos siguen sin ciclo completo |
| Flujo end-to-end | ❌ Nunca completó un ciclo: 26 items de prueba, 0 aprobados (8 `ingested`, 7 `processing`, 11 `ready_for_review`) |
| VM | E2.1.Micro — 2 vCPU, 954 MB RAM, swap 2 GB. Ubuntu 24.04.4 LTS, kernel 7.0.0-1013-oracle, Docker 29.8.2 (mantenimiento 2026-10-02) |
| Capacidad semanal sin costo | Pendiente de cálculo (plan §3) |

---

## 2. Funcionalidades completadas vs. pendientes

### Fase 1 — Infraestructura base
- [x] Repositorio Git con `.gitignore` y `credentials.env.example`
- [x] DNS Route 53 → registro A `n8n.letiende.co` → 150.136.139.189
- [x] Oracle Cloud VM con Docker + Docker Compose
- [x] ~~Nginx con SSL Let's Encrypt~~ → Caddy con HTTPS automático (T-0013, 2026-10-03)
- [x] Stack Docker: n8n 2.41.6 (fijada) + PostgreSQL 15 + Caddy 2.11.6
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
- **Estado:** ⚠️ **En revisión (2026-10-03):** la cuenta de AI Studio ya se había subido a plan de pago, así que la clave actual **sí tiene facturación**. Ver T-0011.
- **Decisión provisional (2026-10-03, T-0011):** se mantiene el proyecto actual de AI Studio, con facturación **prepago y tope mensual de COP 5.000**, para medir el consumo real. Luego se decide entre continuar con él o crear otro proyecto con otro formato de facturación. Es una decisión de medir primero: el objetivo de «costo cercano a USD 0» queda en evaluación, no cumplido por diseño. Las vistas `pipeline_daily_usage` y `pipeline_step_stats` (T-0017) son el instrumento de medición. Pendiente: tabla de límites (RPM, TPM, RPD) de al menos 5 modelos desde `aistudio.google.com/rate-limit` y confirmar que el tope prepago corta el consumo al agotarse.
- **Decisión original:** el proyecto de Gemini opera sin facturación habilitada. Ante un 429 el item pasa a `waiting_quota` y se reintenta tras el reinicio diario (medianoche del Pacífico).
- **Razón:** el objetivo de costo cercano a USD 0. Sin facturación, exceder la cuota no genera cobro.
- **Consecuencias:** el volumen está acotado por la cuota gratuita; la capacidad semanal se calcula según el plan §3. Google puede usar el contenido de la capa gratuita para mejorar sus productos (aceptado: es contenido que se publica).

### ADR-014 — n8n-mcp local y entorno de desarrollo
- **Fecha:** 2026-10-02
- **Estado:** Aceptado (servidor instalado; la instancia dev llega en la Fase 1)
- **Decisión:** usar el servidor MCP `n8n-mcp` (MIT) en local, versión fijada, lanzado por `scripts/n8n-mcp.sh`, que carga `credentials.env` en tiempo de ejecución y desactiva la telemetría. Registrado en Claude Code con ámbito local: `claude mcp add -s local n8n-mcp -- "$(pwd)/scripts/n8n-mcp.sh"`. Los workflows se construyen en una instancia n8n de desarrollo en Docker local (`N8N_MCP_TARGET=dev`) y no en producción.
- **Razón:** el servicio hosted (`dashboard.n8n-mcp.com`) limita el plan gratuito a 100 llamadas/día, insuficientes para la Fase 3, y exige entregar la API key de n8n a un tercero. El servidor valida contra el esquema real de los nodos, que ataca la causa de los JSON escritos a mano con versiones viejas. El propio proyecto advierte no editar producción con IA.
- **Consecuencias:** las herramientas de gestión no funcionan contra producción hasta restablecer HTTPS (Fase 0). La base de nodos del servidor (n8n 2.41.4) solo coincide con la instancia después de la Fase 1. Actualizar el servidor es un cambio deliberado de `N8N_MCP_VERSION`.

### ADR-015 — Caddy en lugar de nginx + certbot
- **Fecha:** 2026-10-03
- **Estado:** Aceptado e implementado (T-0013)
- **Decisión:** Caddy 2.11.6 reemplaza a nginx como reverse proxy. Certificado de Let's Encrypt emitido y renovado por Caddy; certificado y cuenta ACME en el volumen `caddy_data`. Se deshabilitó `certbot.timer` en la VM.
- **Razón:** el certificado venció en junio porque certbot corría en el host con el plugin de nginx mientras nginx estaba en Docker: la renovación nunca funcionó, sin avisos. Con Caddy no hay un segundo componente que coordinar.
- **Consecuencias:** `nginx.conf` eliminado. El certificado actual vence el 2027-01-01; Caddy renueva ~30 días antes. Si el DNS deja de apuntar a la VM o se cierra el puerto 80, la renovación falla: la alerta de la Fase 7 debe vigilar la fecha de vencimiento.

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
| n8n | 2.41.6 (fijada; antes 2.12.3 con `latest`) | 2.41.6 | Docker VM y dev | `infrastructure/docker-compose.yml`, `infrastructure/docker-compose.dev.yml` |
| postgres | 15-alpine | 18-alpine | Docker VM | `infrastructure/docker-compose.yml` |
| Caddy | 2.11.6-alpine (reemplazó a nginx) | — | Docker VM | `infrastructure/docker-compose.yml`, `infrastructure/Caddyfile` |
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
| **SSL vencido sin aviso** | Certbot instalado en el host con plugin nginx, pero nginx corre en Docker: la renovación nunca funcionó | Resuelto con Caddy (ADR-015). Vigilar la fecha de vencimiento en el monitor de la Fase 7. |
| **Gemini "ve" una URL escrita en el texto** | Falso: la API no descarga URLs del prompt y el modelo inventa con total seguridad | Enviar la imagen como `inline_data` (ADR-011). |
| **`error_log` rechaza el INSERT** | Los manejadores de error envían `created_at`, que no existe en la tabla | Alinear el payload con el esquema real; probar el manejador de errores forzando un fallo. |
| **n8n-mcp: "SSRF protection: Localhost access is blocked"** | n8n-mcp bloquea localhost por defecto | Solo para la instancia dev: `WEBHOOK_SECURITY_MODE=moderate` (ya en `scripts/n8n-mcp.sh` con `N8N_MCP_TARGET=dev`). |
| **n8n arranca despacio y `/healthz` miente** | En la VM de 1 vCPU, `/healthz` responde 200 mientras n8n aún migra la base; la API devuelve 404 durante ~2 min más y los workflows no han activado | Esperar a `/healthz/readiness` y a que la API de workflows responda (lo hace `scripts/deploy-n8n.sh`) |
| **`sh script.sh` rompe con `syntax error near unexpected token '<'`** | En macOS `sh` es bash en modo POSIX: no admite `< <(...)` | Los scripts llevan un guard que se relanza con bash; evitar sustitución de procesos |
| **zsh: `$VAR:texto` se interpreta como modificador** | `$ORACLE_VM_IP:letiende-sgcd` aplica `:l` (minúsculas) y rompe el destino de `scp` | Siempre `"${VAR}:ruta"` con llaves |
| **El clasificador del modo automático bloquea acciones sobre producción** | `scp`/`ssh` que escriben en la VM y `docker compose up` se tratan como despliegue | Operaciones acotadas en un script revisado y una regla de permiso exacta (`Bash(bash scripts/deploy-n8n.sh --apply:*)` en `.claude/settings.local.json`, ignorado por git) |
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

- **Respaldo (T-0009):** `bash scripts/backup.sh [--verify]` deja en `backups/<fecha>/` (ignorado por git, permisos 700) los workflows vivos, el dump de la base de n8n, la configuración de la VM y el esquema `public` de Supabase, con `SHA256SUMS`. Restauración probada: 5 workflows, 4 credenciales, 1.465 ejecuciones. Los workflows se exportan por túnel SSH a `localhost:5678`, así que funciona con el certificado vencido. **Las credenciales dentro del dump de n8n están cifradas con `N8N_ENCRYPTION_KEY`** (guardada en el `.env` de la VM y en `credentials.env`): sin esa clave el respaldo no las recupera.
- **Hallazgo:** WF04 vivo en n8n tiene 26 nodos y el JSON del repo 25; los demás workflows coinciden en número de nodos. Revisar al reconstruir en la Fase 3: el repo no es la fuente de verdad de WF04.

- **Mantenimiento de la VM (T-0012, 2026-10-02):** `apt upgrade` de 63 paquetes y dos reinicios (el kernel 1013 salió durante la sesión). Kernel 6.17.0-1007 → 7.0.0-1013, Docker 29.3 → 29.8, containerd 2.2 → 2.3. Los 3 contenedores volvieron solos (`restart: always`), `healthz` responde `ok` y la base de n8n conserva sus 5 workflows. n8n se sigue ejecutando en la 2.12.3 (la actualización es la Fase 1). Ubuntu 26.04 no se instala: 24.04 tiene soporte hasta 2029. Memoria libre tras el arranque: ~590 MB disponibles.
- **Log de n8n:** "Failed to start Python task runner… Python 3 is missing". Es esperable: los workflows usan solo Code nodes de JavaScript.

- **HTTPS (T-0013, 2026-10-03):** Caddy emitió el certificado (Let's Encrypt, válido hasta 2027-01-01) y responde `HTTP/2 200` en `/healthz` sin `-k`. Persiste al reiniciar el contenedor. El editor, la API (5 workflows activos) y la redirección HTTP→HTTPS funcionan. El webhook de Telegram mostraba `Connection refused` de las horas de corte; `pending_update_count` en 0.
- **Lección del despliegue:** el primer `compose up` falló porque el puerto 80 aún lo tenía nginx; el contenedor de Caddy quedó creado con el `resolv.conf` del host (`127.0.0.53`) y no resolvía DNS. Se arregló con `docker compose up -d --force-recreate caddy`. Si un contenedor falla al crearse, recrearlo, no solo reiniciarlo.

- **Instancia de desarrollo (T-0014, 2026-10-03):** n8n **2.41.6** (la etiqueta `stable` de Docker Hub, fijada) + PostgreSQL 15 en Docker, solo en `127.0.0.1:5678`. Arranque: `set -a && source credentials.env && set +a && docker compose -f infrastructure/docker-compose.dev.yml up -d` (Docker Desktop con el disco `Auxiliar` montado). Owner `dev@letiende.local`; contraseña, clave de cifrado y contraseña de la base son propias de desarrollo y viven en `credentials.env` (`N8N_DEV_*`). API key de desarrollo (`N8N_DEV_API_KEY`, 106 scopes, sin vencimiento: solo vale para esa instancia). n8n-mcp con `N8N_MCP_TARGET=dev` lista 0 workflows; el script activa `WEBHOOK_SECURITY_MODE=moderate` solo para dev, porque n8n-mcp bloquea localhost por defecto. Contra producción (`prod`, por defecto) lista los 5 workflows ya con HTTPS.
- **Gemini con facturación (2026-10-03):** el usuario indicó que la cuenta de AI Studio ya es de pago. Esto contradice ADR-013; la tarea T-0011 pasa a ser decidir la estrategia de costo.

- **Compatibilidad con n8n 2.41.6 (T-0015, 2026-10-03):** los 5 workflows del respaldo `2026-10-02_1859` (los vivos, no los del repo) se importaron a dev por la API REST, inactivos. n8n 2.41.6 los aceptó y los guardó **idénticos** (mismos nodos, `typeVersion`, parámetros y conexiones): ningún nodo rechazado ni modificado. Validación con `n8n_validate_workflow` (perfil `runtime`, n8n-mcp 2.91.0, `N8N_MCP_TARGET=dev`). IDs en dev: 01 `MqmV7oZTABtzTDD2`, 02 `u2UijuWG2PAGFblR`, 03 `4rH10xcsEIKuw2YD`, 04 `hS0gSKQVT2We6d4J`, 05 `C3vBtqFbBskFnMxH`.

  | Workflow | Nodos | Errores | Advertencias | `typeVersion` obsoleta | Causa de los errores |
  |---|---|---|---|---|---|
  | 01 Ingesta | 22 | 1 | 2 | 14 | Texto con expresión sin prefijo `=` (Telegram de error); 2 nodos de video inalcanzables |
  | 02 Generación | 20 | 1 | 0 | 10 | Texto con expresión sin prefijo `=` (Telegram de error) |
  | 03 Revisión HITL | 32 | 9 | 2 | 27 | 2 Switch con conexiones a salidas inexistentes; 7 nodos con `credentials` dentro de `parameters` |
  | 04 Publicación | 26 | 3 | 3 | 21 | 3 Switch con conexiones a salidas inexistentes |
  | 05 Métricas | 27 | 5 | 1 | 12 | URL con expresión sin `=`; 4 nodos con `credentials` dentro de `parameters`; 1 nodo inalcanzable |

  Versiones obsoletas (vigente en 2.41.6): `httpRequest` 4 → 4.5 (52 nodos), `switch` 3 → 3.4, `if` 2 → 2.3, `telegram` 1/1.2 → 1.2, `webhook` 2 → 2.1, `scheduleTrigger` 1.1/1.2 → 1.4, `telegramTrigger` 1 → 1.5, `respondToWebhook` 1 → 1.5, `wait` 1 → 1.1, `merge` 3 → 3.2. `code` 2 y `splitInBatches` 3 están al día. Las versiones antiguas siguen siendo ejecutables.
  - **Los errores son defectos previos de los JSON, no efecto de la versión.** Los Switch de WF03/WF04 tienen una sola regla y conectan a la salida 1, que solo existe con `options.fallbackOutput: "extra"`: la rama «imagen»/«no» probablemente nunca ejecuta. Es una hipótesis sin probar, pero encaja con que el flujo nunca completó un ciclo. WF03 y WF05 llevan `credentials` en `parameters`, donde n8n las ignora.
  - **Límite de la medición:** solo cubre importación y validación estática. No se ejecutó ningún flujo en 2.41.6 (los nodos Telegram/Supabase/Gemini no se probaron con tráfico).
  - **Decisión: sí actualizar producción a 2.41.x antes de la Fase 3.** (1) Ningún workflow se rompe al importar, y el riesgo de runtime es bajo porque las versiones viejas de los nodos se conservan. (2) La Fase 3 se construye con n8n-mcp, cuya base de nodos es 2.41.4: producción en 2.12.3 impediría validar contra lo que realmente corre. (3) Quedarse en 2.12.3 mantiene una imagen `latest` sin fijar y los gotchas de Merge v3 y `body`. Mitigación: respaldo fresco con `scripts/backup.sh` justo antes, imagen fijada, y comprobar la memoria de la VM (954 MB) tras el arranque. Cuidado con el orden: las migraciones de la base de n8n no se revierten, así que el respaldo es el único retroceso.

- **Producción en n8n 2.41.6 (T-0016, 2026-10-03):** `bash scripts/deploy-n8n.sh --apply` (nuevo) recreó solo el servicio n8n con la imagen fijada. Compose limpio: sin `version` ni `N8N_BASIC_AUTH_*`, puerto 5678 en `127.0.0.1` (Caddy llega por la red interna; el respaldo usa túnel SSH; desde internet el 5678 no responde). Todas las migraciones terminaron; 5 de 5 workflows activos; `healthz` público 200; webhook de Telegram sin pendientes ni errores. **Memoria disponible: 441 MB antes → ~380 MB después** (954 MB de VM): cabe, pero con menos margen. El script exige un respaldo de menos de 1 hora, no revierte solo (las migraciones no se deshacen: la vuelta atrás es restaurar el respaldo) y por defecto solo simula.
  - **Lección:** la primera ejecución dio ✓ aunque la comprobación de workflows falló (n8n seguía arrancando y el script tapaba el error). Corregido: reintenta la API, espera a `/healthz/readiness` y sale con error si alguna comprobación falla.
  - **Pendiente de la Fase 1:** la salida exige 72 h estable con la memoria registrada. Revisar a partir del 2026-10-06 16:30: reinicios del contenedor, memoria y errores (ver backlog).
  - **Avisos de n8n 2.41.6 por atender en la Fase 3:** `WEBHOOK_URL` → `N8N_WEBHOOK_URL`; el modo de runners interno está obsoleto; fijar explícitamente `N8N_RUNNERS_TASK_TIMEOUT` y los límites del nodo Compression.

- **`pipeline_steps` (T-0017, 2026-10-03):** `supabase/migration-002-pipeline-steps.sql` crea la tabla y 3 vistas (`pipeline_step_stats`, `pipeline_stuck_steps`, `pipeline_daily_usage`). Probada en un Postgres 15 desechable con roles tipo Supabase: p50 = 6,00 s y p95 = 20,00 s sobre datos de prueba calculados a mano, 8 restricciones rechazan lo debido, `anon` y `authenticated` no acceden a la tabla, las vistas ni la secuencia, `service_role` inserta y actualiza, la cascada borra los pasos y las consultas usan los dos índices. **La migración aún NO está aplicada en producción**: el clasificador del modo automático bloqueó `apply_migration` (recurso compartido) y se dejó para decisión del usuario.
- **⚠️ Hallazgo de seguridad (asesor de Supabase, 2026-10-03):** las 5 tablas de `public` (`content_items`, `publish_log`, `metrics`, `quota_tracker`, `error_log`) tienen **RLS desactivado**: cualquiera con la `anon` key puede leer y modificar todas las filas. n8n no se vería afectado al activarlo, porque usa la service_role key, que ignora RLS. Además `public.update_updated_at` tiene `search_path` mutable. La corrección (activar RLS sin políticas y revocar privilegios a `anon`/`authenticated`, fijar `search_path`) es un cambio aparte y requiere aprobación del usuario antes de aplicarse.

**Próxima sesión:** aplicar `migration-002` en producción, decidir sobre el hallazgo de RLS y continuar con T-0011 (tabla de límites de Gemini) y la siguiente tarea de la Fase 2.

<details>
<summary>Sesión 2026-04-30 (histórico)</summary>

Se corrigieron 11 problemas de WF01/WF02/WF03 sobre n8n 2.12.3, se reforzó el system prompt (tuteo bogotano, dirección exacta en Teusaquillo, regla de especificidad) y se dividió el mensaje de revisión en dos. Las pruebas de captions fallaban de forma intermitente; hoy se sabe por qué: Gemini nunca recibió la imagen (ADR-007 refutado).
</details>
