# CLAUDE.md — Plan de trabajo: Sistema SGCD de Le Tiende

## Contexto del proyecto

Sistema autónomo de gestión y publicación de contenidos digitales para **letiende.co**.
Orquestado por n8n, con IA (Gemini), almacenamiento distribuido (Cloudinary + Cloudflare R2),
base de datos (Supabase), mensajería (Telegram) y publicación en Instagram, YouTube y TikTok.

El servidor vive en una VM de Oracle Cloud accesible en `n8n.letiende.co`.
AWS CLI está configurado en el equipo local y da acceso a Lambda y Route 53.
Todos los demás servicios se acceden mediante las variables definidas en `.env`.

---

## Lectura obligatoria antes de empezar

1. `docs/MEMORY.md` — estado actual, ADRs y gotchas. **Leer al iniciar cada sesión.**
2. `docs/TODO.md` — las 2 tareas activas (motor JIT) con su `trace_id`.
3. `docs/plan-actualizacion.md` — plan vigente por fases, con criterios de salida.
4. `docs/tech-specs.md` — arquitectura actual, esquema y convenciones. `docs/PRD.md` — objetivos de negocio.

**Workflows de n8n:** construir y validar con el servidor MCP `n8n-mcp` (ver ADR-014 y las skills `n8n-*`), primero contra la instancia de desarrollo (`N8N_MCP_TARGET=dev`). Nunca editar producción directamente con IA.

El plan original de 4 semanas (Fase 1–4 por semana) quedó obsoleto el 2026-10-02 y vive en el historial de git.
La guía para montar la infraestructura desde cero está en `docs/fase1-guia-replicable.md`.

---

## Variables de entorno disponibles

Todas están en `credentials.env` (ignorado por git; plantilla en `credentials.env.example`). Cárgalas antes de cualquier script:

```bash
set -a && source credentials.env && set +a
```

Nunca hardcodear valores de `credentials.env` en el código ni escribirlos en un comando.
Usar siempre `process.env.NOMBRE_VARIABLE` en JavaScript, `$env.NOMBRE_VARIABLE` en n8n o `$NOMBRE_VARIABLE` en bash.

---

## Notas de implementación importantes

### Manejo de errores
- Todos los nodos HTTP en n8n deben tener el toggle "Continue on Fail" desactivado.
- Usar el nodo "Error Trigger" de n8n para capturar fallos y enviar notificación a Telegram.
- Todos los errores se registran en la tabla `error_log` de Supabase.

### Seguridad
- Nunca exponer `credentials.env` fuera del entorno de desarrollo.
- En la VM de Oracle, las variables se inyectan en Docker Compose como variables de entorno del sistema, no como archivo montado.
- El webhook de Telegram debe validar el `secret_token` en cada request.

### Convenciones de código
- JavaScript ES2022 (async/await, optional chaining).
- Nombres de variables: camelCase para JS, SCREAMING_SNAKE_CASE para variables de entorno.
- Comentarios en español, código en inglés.
- Cada función Lambda debe tener un test unitario en `lambda/video-processor/tests/`.

### Rate limiting y delays
- Entre llamadas a Gemini: delay de 3 segundos (nodo Wait en n8n).
- Entre publicaciones en Instagram: delay de 30 segundos.
- Reintentos automáticos: máximo 3 intentos con backoff exponencial (1s, 2s, 4s).

---

## Seguridad (OWASP)

Riesgos OWASP Top 10 (2021) relevantes para esta arquitectura y reglas de código obligatorias.

### A01 — Broken Access Control

**Riesgo:** El webhook de Telegram no valida la autenticidad del origen. Cualquiera que conozca la URL puede enviar peticiones falsas al Workflow 01.

**Regla:** Agregar nodo If al inicio de WF1 que valide el header `x-telegram-bot-api-secret-token` contra `$TELEGRAM_WEBHOOK_SECRET`. Si no coincide → responder 403 y detener.

Configurar el secret_token al registrar el webhook:
```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://n8n.letiende.co/webhook/..." \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

### A02 — Cryptographic Failures

**Riesgo:** Las variables de entorno en Docker pueden verse con `docker inspect` si el host está comprometido.

**Regla:** Nunca montar `credentials.env` como volumen. Inyectar directamente en `docker-compose.yml` bajo `environment:` (ya implementado). Rotar `N8N_ENCRYPTION_KEY` ante cualquier sospecha de compromiso (invalida todas las credenciales guardadas en n8n).

### A03 — Injection

**Riesgo:** El texto libre del aprobador (opción "Editar") y el contenido del activo se incluyen en prompts de Gemini sin sanitizar (prompt injection).

**Regla:**
```javascript
// NUNCA concatenar input del usuario directamente
// MAL: '{"caption": "' + userInput + '"}'
// BIEN:
JSON.stringify({ caption_instagram: userInput });

// En prompts de Gemini, delimitar el input del usuario
`Nuevo caption del aprobador:
"""
${userInput}
"""`;
```

### A05 — Security Misconfiguration

**Riesgo:** el editor de n8n está expuesto a internet; los logs de ejecución retienen datos de usuarios hasta 14 días.

**Reglas:**
- El acceso al editor se protege con la cuenta owner de n8n y 2FA. Las variables `N8N_BASIC_AUTH_*` no tienen efecto desde n8n 1.x; se retiran en la Fase 1.
- Fijar la versión de la imagen de n8n; nunca `latest`.
- No modificar `EXECUTIONS_DATA_MAX_AGE` más allá de 336h (14 días).
- No exponer el puerto 5678 directamente — siempre pasar por Caddy (reverse proxy con HTTPS automático).

### A07 — Identification and Authentication Failures

**Riesgo:** Los access tokens de Instagram (expiran en 60 días) y YouTube pueden revocarse. Un token vencido causa fallo silencioso.

**Regla:** Ante cualquier `401` de una API de RRSS → insertar en `error_log` + alertar a `TELEGRAM_ADMIN_CHAT_ID` + actualizar `status = 'error'`. Nunca silenciar el error.

### A10 — SSRF

**Riesgo:** WF1 descarga archivos desde URLs de Telegram generadas dinámicamente. Una URL interna podría acceder al metadata service de Oracle Cloud.

**Regla:**
```javascript
const ALLOWED_HOSTS = ['api.telegram.org', 'cdn.telegram.org'];
const url = new URL(fileUrl);
if (!ALLOWED_HOSTS.includes(url.hostname)) {
  throw new Error(`URL no permitida: ${url.hostname}`);
}
```

### Tabla de prohibiciones absolutas

| Acción prohibida | Riesgo |
|---|---|
| Hardcodear credenciales en workflows JSON | Exposición en el repositorio |
| Escribir el valor de un secreto en un comando (usar siempre `$VARIABLE` tras `source credentials.env`) | Queda guardado en el historial y en `.claude/settings.local.json` |
| Montar `credentials.env` como volumen en Docker | Archivo sensible en filesystem del contenedor |
| Desactivar la cuenta owner o el 2FA de n8n | n8n sin autenticación expuesto a internet |
| `Continue on Fail: ON` en nodos HTTP | Errores de API pasan silenciosamente |
| Concatenar input del usuario en prompts de Gemini | Prompt injection |
| Ignorar respuestas 401 de APIs de RRSS | Tokens vencidos no se detectan |
| Descargar archivos desde URLs no validadas en WF1 | SSRF hacia metadata service de Oracle |
| Habilitar facturación en el proyecto de Gemini | Rompe el objetivo de costo cercano a USD 0 (ADR-013) |
| Pasar a Gemini una imagen como URL dentro del texto | El modelo no la descarga e inventa el contenido (ADR-007 refutado) |

---

## Git Flow para Agentes IA

Reglas **obligatorias** para cualquier agente que opere en este repositorio. No hay excepciones.

### Ramas protegidas

La rama `main` está protegida (GitHub exige PR para fusionar). **Ningún agente puede hacer commits directos a ella.**

### Protocolo antes de cualquier cambio de código

**Paso 1 — Verificar la rama actual:**
```bash
git branch --show-current
```
Si el resultado es `main`, ejecutar el Paso 2. Si ya hay una feature branch activa, ir al Paso 3.

**Paso 2 — Crear feature branch:**
```bash
git checkout main
git pull origin main
git checkout -b feature/descripcion-corta-en-kebab-case
```

Prefijos válidos: `feature/`, `fix/`, `hotfix/`, `docs/`, `refactor/`

**Paso 3 — Cambios y commit:**
```bash
git add [archivos específicos]   # Nunca git add . ni git add -A
git commit -m "tipo(alcance): descripción en español colombiano"
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Paso 4 — Pull Request:**
```bash
git push -u origin HEAD
gh pr create \
  --base main \
  --title "tipo(alcance): descripción breve" \
  --body "$(cat <<'EOF'
## Cambios realizados
- [bullet]

## Cómo probar
- [pasos verificables]

## Checklist
- [ ] Workflows importados y verificados en n8n
- [ ] No hay secretos hardcodeados
- [ ] Seguí las convenciones del proyecto

🤖 Generado con Claude Code
EOF
)"
```

### Prohibiciones absolutas

| Acción prohibida | Por qué |
|---|---|
| `git push origin main` | Commit directo a producción |
| `git push --force` en cualquier rama | Destruye historial |
| `git merge` de cualquier PR | Solo humanos aprueban y fusionan |
| `--no-verify` en commits o pushes | Omite hooks de seguridad |
| `git add .` o `git add -A` | Puede incluir `credentials.env` u otros archivos sensibles |
| Commitear `credentials.env`, `*.pem`, `*.key` | Exposición de credenciales |

---

## Estructura de archivos JSON de workflows n8n

> Referencia rápida para editar workflows SGCD sin romperlos. Todo campo no listado aquí debe tratarse como read-only o no modificarse.

### Formato global del archivo JSON

```json
{
  "name": "01 - Ingesta de Activos",
  "nodes": [...],
  "connections": {...},
  "active": false,
  "settings": { "executionOrder": "v1" },
  "tags": []
}
```

| Campo | Obligatorio | Propósito |
|---|---|---|
| `name` | Sí | Nombre visible en n8n |
| `nodes` | Sí | Array de objetos nodo |
| `connections` | Sí | Mapa de conexiones entre nodos |
| `settings` | Sí | Mínimo: `{ "executionOrder": "v1" }` |
| `active` | **Read-only** | Solo se activa vía API (`POST /activate`) |
| `tags` | **Read-only** | Gestionado vía API, no en el JSON |
| `staticData` | **Read-only** | Datos persistentes entre ejecuciones |
| `meta` | **Auto-generado** | Template metadata |
| `pinData` | **Auto-generado** | Datos de pines |
| `versionId` | **Auto-generado** | ID de versión actual |
| `activeVersionId` | **Auto-generado** | ID de versión activa |
| `triggerCount` | **Auto-generado** | Número de triggers |
| `shared` | **Auto-generado** | Permisos de compartición |
| `isArchived` | **Read-only** | Solo en export desde n8n |
| `description` | **Read-only** | Solo en export desde n8n |

### Estructura de un nodo

```json
{
  "id": "uuid-v4-o-id-corto",
  "name": "Nombre descriptivo (único en el workflow)",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4,
  "position": [1100, 300],
  "parameters": { ... },
  "credentials": { ... }
}
```

| Campo | Obligatorio | Notas |
|---|---|---|
| `id` | Sí | UUID v4 o ID corto. Único en el workflow |
| `name` | Sí | Se usa en `$('Nombre')` y en `connections`. Debe ser único |
| `type` | Sí | Prefijo `n8n-nodes-base.` |
| `typeVersion` | Sí | HTTP Request: 4, Code: 2, IF/Switch: 2, Telegram: 1 / 1.2, Merge: 3 |
| `position` | Sí | `[x, y]` en el canvas. X en incrementos de ~250, Y=300 (flujo), Y=600 (error) |
| `parameters` | Sí | Específico por tipo de nodo |
| `credentials` | No | Formato anidado por tipo: `{ "httpHeaderAuth": { "id": "...", "name": "..." } }` |
| `webhookId` | Solo webhooks | UUID v4 generado por n8n al crear el nodo |

### Conexiones (connections)

```json
"connections": {
  "Nombre del nodo origen": {
    "main": [
      [ { "node": "Nombre destino A", "type": "main", "index": 0 } ],
      [ { "node": "Nombre destino B", "type": "main", "index": 0 } ]
    ]
  }
}
```

| Indice | Significado |
|---|---|
| `main[0]` | Salida 0: "true" en IF, "imagen" (o primera regla) en Switch, flujo normal |
| `main[1]` | Salida 1: "false" en IF, "video" (segunda regla) en Switch |
| `main[N]` | Salidas adicionales en Switch con 3+ reglas |

### Tipos de nodo — parámetros clave

#### Code node (`n8n-nodes-base.code`, typeVersion: 2)

```json
{
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "parameters": {
    "jsCode": "const data = $input.first().json;\nreturn [{ json: { result: data } }];"
  }
}
```

**Acceso a datos:**
| Expresión | Devuelve |
|---|---|
| `$input.first().json` | Primer item del nodo anterior (objeto o array) |
| `$input.first().json[0]` | Si el nodo anterior devuelve array, primer elemento |
| `$input.first().binary` | Datos binarios del nodo anterior |
| `$input.first().binary.data` | Binario por defecto (HTTP Request con `responseFormat: "file"`) |
| `$input.first().binary.data.mimeType` | MIME type del binario |
| `$input.first().binary.data.data` | Datos en **base64** (n8n almacena binarios como base64) |
| `$('Nombre del nodo').first().json` | Acceder a otro nodo por nombre |
| `$env.NOMBRE_VARIABLE` | Variable de entorno |
| `$json` | Alias de `$input.first().json` |
| `$now` | Fecha/hora actual |

**Retorno:** siempre `return [{ json: { ... } }]`.

#### HTTP Request (`n8n-nodes-base.httpRequest`, typeVersion: 4)

```json
{
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4,
  "parameters": {
    "method": "POST",
    "url": "=https://api.example.com/{{ $json.id }}",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "httpHeaderAuth",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        { "name": "Authorization", "value": "=Bearer {{ $env.SUPABASE_SERVICE_ROLE_KEY }}" },
        { "name": "Prefer", "value": "return=representation" },
        { "name": "Content-Type", "value": "application/json" }
      ]
    },
    "sendBody": true,
    "contentType": "json",
    "body": "={{ JSON.stringify({ status: 'ready_for_review', ... }) }}"
  }
}
```

**Notas:**
- `url`: Prefijo `=` activa modo expresión. Sin `=`, es string literal
- `authentication`: `"none"`, `"genericCredentialType"` o `"predefinedCredentialType"`
- `nodeCredentialType`: `"httpHeaderAuth"`, `"httpBasicAuth"`, `"supabaseApi"`
- `options.response.response.responseFormat: "file"` → devuelve binario
- `options.response.response.neverError: true` → no para el workflow en 4xx/5xx
- `sendQuery: true` → añade `queryParameters.parameters`
- `contentType: "multipart-form-data"` → usa `bodyParameters.parameters`

**Credenciales en nodos HTTP:**
```json
"credentials": {
  "httpHeaderAuth": { "id": "RmsV9T5laWF4HUXc", "name": "Supabase SGCD" }
}
```

#### IF node (`n8n-nodes-base.if`, typeVersion: 2)

Salidas: `main[0]` = true, `main[1]` = false.

**Operadores comunes:**

| `type` | `operation` | Ejemplo `leftValue` | Ejemplo `rightValue` |
|---|---|---|---|
| `boolean` | `equals` | `"={{ $json.valid }}"` | `true` |
| `number` | `gt` (greater than) | `"={{ $json.length }}"` | `0` |
| `string` | `equals` | `"={{ $json.asset_type }}"` | `"image"` |
| `string` | `notEmpty` | `"={{ $json.field }}"` | `""` |
| `string` | `isEmpty` | `"={{ $json.field }}"` | `""` |

#### Switch / Router (`n8n-nodes-base.switch`, typeVersion: 3)

```json
{
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3,
  "parameters": {
    "mode": "rules",
    "rules": {
      "values": [
        {
          "conditions": { "conditions": [{ "leftValue": "={{ $json.asset_type }}", "rightValue": "image", "operator": { "type": "string", "operation": "equals" } }] },
          "renameOutput": true,
          "outputKey": "imagen"
        }
      ]
    }
  }
}
```
Salidas: `main[0]` = primera regla, `main[1]` = segunda, etc.

#### Telegram (`n8n-nodes-base.telegram`, typeVersion: 1 / 1.2)

```json
{
  "type": "n8n-nodes-base.telegram",
  "typeVersion": 1.2,
  "parameters": {
    "operation": "sendMessage",
    "chatId": "={{ $json.chat_id }}",
    "text": "={{ texto }}",
    "additionalFields": { "parse_mode": "Markdown" }
  },
  "credentials": {
    "telegramApi": { "id": "OCCZrTCUmwHqePhr", "name": "Telegram Bot SGCD" }
  }
}
```

#### Telegram Trigger (`n8n-nodes-base.telegramTrigger`, typeVersion: 1)

```json
{
  "type": "n8n-nodes-base.telegramTrigger",
  "typeVersion": 1,
  "webhookId": "uuid-v4",
  "parameters": { "updates": ["message", "callback_query"], "additionalFields": {} }
}
```
Datos del mensaje en `$json.message`. Para callback queries: `$json.callback_query`.

#### Webhook (`n8n-nodes-base.webhook`, typeVersion: 2)

```json
{
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2,
  "webhookId": "uuid-v4",
  "parameters": {
    "httpMethod": "POST",
    "path": "sgcd-generacion",
    "responseMode": "responseNode"
  }
}
```
URL: `https://n8n.letiende.co/webhook/{path}`. Body recibido en `$json.body`.

#### Merge (`n8n-nodes-base.merge`, typeVersion: 3)

Modos: `"passThrough"` (deja pasar input1), `"combine"` + `"combinationMode": "multiplex"`.

#### Wait (`n8n-nodes-base.wait`, typeVersion: 1)

```json
{ "unit": "seconds", "amount": 3 }
```

#### Cron (`n8n-nodes-base.scheduleTrigger`, typeVersion: 1.2)

```json
{ "rule": { "interval": [{ "field": "cronExpression", "expression": "0 23 * * 0" }] } }
```

### Deploy de JSON a n8n — procedimiento exacto

```bash
source credentials.env

# 1. Limpiar campos read-only del JSON
python3 -c "
import json
with open('n8n-workflows/XX-nombre.json') as f:
    wf = json.load(f)
for key in ['active', 'tags', 'staticData', 'meta', 'pinData']:
    wf.pop(key, None)
print(json.dumps(wf))
" > /tmp/wf-clean.json

# 2. PUT al workflow existente
curl -s -X PUT "https://n8n.letiende.co/api/v1/workflows/$WORKFLOW_ID" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/wf-clean.json

# 3. Activar
curl -s -X POST "https://n8n.letiende.co/api/v1/workflows/$WORKFLOW_ID/activate" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

### IDs y credenciales del proyecto

**IDs de workflows en n8n (inmutables):**

| Workflow | ID |
|---|---|
| 01 - Ingesta de Activos | `ZE5IjN2YzTX15Qm4` |
| 02 - Generación con IA | `lF8QngxsBPpgta2G` |
| 03 - Revisión y aprobación HITL | `unOTijMfyurxMcB1` |
| 04 - Publicación (entrega por Telegram) | `4z8wU9qrV4rw5NC2` |
| 05 - Métricas y Reporte Semanal | `RxayCUeh3qCY2JIY` |

**Credenciales internas de n8n (referenciadas en los nodos):**

| Nombre | Tipo de nodo | ID interno |
|---|---|---|
| Telegram Bot SGCD | `telegramApi` | `OCCZrTCUmwHqePhr` |
| Supabase SGCD | `httpHeaderAuth` | `RmsV9T5laWF4HUXc` |
| Gemini SGCD | `httpHeaderAuth` | `BtiKAfnEOG65ddqG` |
| Cloudinary SGCD | `httpBasicAuth` | `pkyzhNuiwQQC3qzs` |

### Convención de posiciones en el canvas

| Columna X | Contenido típico |
|---|---|
| 100 | Triggers (Telegram, Webhook, Cron) |
| 350 | Code: extracción inicial / GET Supabase |
| 600 | IF: primera validación |
| 850 | HTTP: operaciones, descargas |
| 950 | Descargas de assets |
| 1100 | Code: preparación de payloads |
| 1350 | HTTP: APIs externas (Gemini, Cloudinary) |
| 1600 | Esperas / Code intermedio |
| 1850–2100 | Parseo / Router |
| 2350–2600 | URLs procesadas / Merge |
| 2850–3100 | Cálculos finales / PATCH Supabase |
| 3350+ | Triggers al siguiente workflow / Response |

| Fila Y | Significado |
|---|---|
| `300` | Flujo principal (happy path) |
| `600` | Error handling (Error Trigger + log + notificación) |

---

## Registro de esfuerzo

Este proyecto lleva un registro de esfuerzo y costo en `metrics/events/`,
un archivo JSONL por sesión, versionado en git. Configuración en `metrics/config.json`.

**Al cerrar cualquier unidad de trabajo**, invoca `/ai-effort-tracking capture`.

Reglas no negociables:
- Nunca escribas tokens, costo, duraciones ni nivel de esfuerzo de memoria.
  Ejecuta siempre el adaptador de la superficie activa.
- Si un dato no se puede medir, escribe `null` y baja `capture_level`. No lo estimes.
- Los precios salen de `metrics/pricing.json`, jamás de tu conocimiento previo.
  Si el proveedor está `unverified`, deja `cost.usd` en `null`.
- `input_uncached` y `cache_read` son disjuntos; `thinking` va dentro de `output`.
- El registro es append-only y cada sesión escribe solo su archivo.
  Para corregir, emite un evento nuevo con `corrects`.
- Referencia siempre el `trace_id` de la tarea de `docs/TODO.md` (formato `T-NNNN`).

## Documentación del proyecto

Los documentos de la skill `project-docs-bootstrap` viven en `docs/`:
`PRD.md`, `tech-specs.md`, `MEMORY.md` (leer al iniciar sesión), `TODO.md` (motor JIT, 2 tareas)
y `plan-actualizacion.md` (plan vigente por fases).
