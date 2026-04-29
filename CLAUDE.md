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

1. Leer `TECHNICAL_SPEC.md` completo antes de escribir cualquier código.
2. Leer `credentials.env` para conocer las variables disponibles.
3. Consultar `TECHNICAL_SPEC.md > Sección 7 (Convenciones)` ante cualquier duda de estilo.

---

## Estructura de archivos del repositorio

```
letiende-sgcd/
├── CLAUDE.md                  ← este archivo
├── TECHNICAL_SPEC.md          ← especificación técnica completa
├── credentials.env            ← secrets (NO commitear, está en .gitignore)
├── credentials.env.example    ← plantilla sin valores (sí commitear)
├── .gitignore
│
├── infrastructure/
│   ├── docker-compose.yml     ← n8n + PostgreSQL + Nginx en Oracle VM
│   ├── nginx.conf             ← reverse proxy con SSL
│   └── init-db.sql            ← tablas iniciales de PostgreSQL (para n8n)
│
├── supabase/
│   └── schema.sql             ← tablas de negocio: content_items, publish_log, etc.
│
├── lambda/
│   └── video-processor/
│       ├── index.js           ← handler principal
│       ├── package.json
│       └── Dockerfile         ← imagen con FFmpeg layer
│
├── n8n-workflows/
│   ├── 01-ingesta.json        ← Flujo 1: recepción de activos vía Telegram
│   ├── 02-generacion.json     ← Flujo 2: IA genera contenido
│   ├── 03-revision.json       ← Flujo 3: HITL aprobación
│   ├── 04-publicacion.json    ← Flujo 4: publicación en RRSS
│   └── 05-metricas.json       ← Flujo 5: reporte semanal
│
├── scripts/
│   ├── deploy-lambda.sh       ← empaqueta y despliega función Lambda via AWS CLI
│   ├── setup-r2.sh            ← crea buckets en Cloudflare R2 via API
│   ├── setup-supabase.sh      ← aplica schema.sql en Supabase
│   └── import-workflows.sh    ← importa workflows a n8n via API
│
└── docs/
    └── telegram-commands.md   ← comandos disponibles para usuarios del bot
```

---

## Variables de entorno disponibles

Todas están en `credentials.env`. Carga el archivo antes de ejecutar cualquier script:

```bash
source credentials.env
```

Nunca hardcodear valores de `credentials.env` en el código.
Usar siempre `process.env.NOMBRE_VARIABLE` en JavaScript o `$NOMBRE_VARIABLE` en bash.

---

## Fase 1 — Infraestructura base (Semana 1)

### 1.1 Repositorio Git

```bash
mkdir letiende-sgcd && cd letiende-sgcd
git init
echo "credentials.env" >> .gitignore
echo "node_modules/" >> .gitignore
echo ".DS_Store" >> .gitignore
```

Crear `credentials.env.example` copiando `credentials.env` y reemplazando todos los
valores con el placeholder `COMPLETAR`. Commitear solo el `.example`.

---

### 1.2 Route 53 — Subdominio n8n.letiende.co

Usar AWS CLI (ya configurado). El Hosted Zone ID está en `credentials.env` como
`AWS_ROUTE53_HOSTED_ZONE_ID`.

```bash
# Obtener el Hosted Zone ID para verificación
aws route53 list-hosted-zones --query "HostedZones[?Name=='letiende.co.'].Id" --output text

# Crear registro A apuntando a la IP de Oracle VM
aws route53 change-resource-record-sets \
  --hosted-zone-id $AWS_ROUTE53_HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "n8n.letiende.co",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$ORACLE_VM_IP"'"}]
      }
    }]
  }'
```

Verificar propagación (puede tomar hasta 5 minutos):
```bash
dig n8n.letiende.co +short
```

---

### 1.3 Oracle Cloud VM — Docker stack

Conectarse a la VM:
```bash
ssh -i $ORACLE_SSH_KEY_PATH ubuntu@$ORACLE_VM_IP
```

Una vez dentro de la VM, ejecutar en orden:

```bash
# 1. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Docker y Docker Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Instalar Certbot
sudo apt install certbot python3-certbot-nginx nginx -y

# 4. Crear estructura de directorios
mkdir -p ~/letiende-sgcd/infrastructure
```

Copiar los archivos `infrastructure/docker-compose.yml` y `infrastructure/nginx.conf`
a la VM con `scp`:

```bash
scp -i $ORACLE_SSH_KEY_PATH \
  infrastructure/docker-compose.yml \
  infrastructure/nginx.conf \
  ubuntu@$ORACLE_VM_IP:~/letiende-sgcd/infrastructure/
```

En la VM, emitir el certificado SSL (el registro DNS debe estar propagado):
```bash
sudo certbot --nginx -d n8n.letiende.co --non-interactive --agree-tos -m $ADMIN_EMAIL
```

Iniciar el stack:
```bash
cd ~/letiende-sgcd/infrastructure
docker compose up -d
```

Verificar que n8n esté activo:
```bash
docker compose ps
curl -s https://n8n.letiende.co/healthz | grep ok
```

**Resultado esperado:** `https://n8n.letiende.co` responde con la pantalla de login de n8n.

---

### 1.4 Cloudflare R2 — Crear buckets

Usar el script `scripts/setup-r2.sh`. El script usa la API de Cloudflare con las
variables `CF_ACCOUNT_ID`, `CF_R2_ACCESS_KEY_ID` y `CF_R2_SECRET_ACCESS_KEY`.

Buckets a crear:
- `letiende-raw-assets` — activos crudos enviados por el equipo (lifecycle: 30 días)
- `letiende-processed-assets` — activos procesados listos para publicar (lifecycle: 90 días)
- `letiende-templates-backup` — respaldo de plantillas exportadas de Canva

El script `setup-r2.sh` debe:
1. Crear los tres buckets via `PUT /accounts/{id}/r2/buckets`
2. Configurar lifecycle rule en `letiende-raw-assets` (expiración 30 días)
3. Verificar acceso con un objeto de prueba (subir y eliminar un archivo de 1 byte)

---

### 1.5 Supabase — Crear tablas

Aplicar el schema con:
```bash
bash scripts/setup-supabase.sh
```

El script ejecuta `supabase/schema.sql` via la REST API de Supabase usando
`SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY`.

Ver `TECHNICAL_SPEC.md > Sección 3` para el schema completo de tablas.

---

### 1.6 Verificación de Fase 1

Antes de avanzar a la Fase 2, verificar que todos estos endpoints respondan:

| Servicio | Verificación |
|---|---|
| n8n | `curl https://n8n.letiende.co/healthz` → `{"status":"ok"}` |
| R2 raw-assets | El script setup-r2.sh reporta los tres buckets creados |
| Supabase | `curl $SUPABASE_URL/rest/v1/content_items` con header `apikey: $SUPABASE_ANON_KEY` → `[]` |
| SSL | `curl -I https://n8n.letiende.co` → `HTTP/2 200` |

---

## Fase 2 — Flujos de ingesta y generación (Semana 2)

### 2.1 Lambda — Procesador de video

Construir y desplegar la función Lambda con capa FFmpeg:

```bash
bash scripts/deploy-lambda.sh
```

El script debe:
1. Construir la imagen Docker de `lambda/video-processor/`
2. Publicar en ECR (usar `aws ecr` commands)
3. Crear o actualizar la función Lambda `letiende-video-processor`
4. Configurar variables de entorno en Lambda: `CF_R2_ENDPOINT`, `CF_R2_ACCESS_KEY_ID`,
   `CF_R2_SECRET_ACCESS_KEY`, `CF_R2_BUCKET_PROCESSED`
5. Asignar 512 MB de RAM y timeout de 900 segundos (15 minutos)

Ver `TECHNICAL_SPEC.md > Sección 5.1` para el contrato de entrada/salida de la función.

---

### 2.2 Workflow 1 — Ingesta de activos (n8n)

Importar `n8n-workflows/01-ingesta.json` via API de n8n:
```bash
curl -X POST https://n8n.letiende.co/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/01-ingesta.json
```

El workflow debe implementar la lógica descrita en `TECHNICAL_SPEC.md > Sección 4.1`.

Puntos críticos a implementar:
- Telegram Trigger node configurado con `$TELEGRAM_BOT_TOKEN`
- Validación de MIME type: solo `image/*` y `video/*`
- Router: imagen → nodo upload Cloudinary, video → nodo upload R2
- Nodo HTTP Request a Supabase para crear registro en `content_items`
- Respuesta de confirmación al usuario por Telegram
- Manejo de errores con notificación al usuario

---

### 2.3 Workflow 2 — Generación con IA (n8n)

Importar `n8n-workflows/02-generacion.json`.

El workflow recibe el `content_item_id` del Workflow 1 y debe:
1. Consultar el activo en Supabase
2. Llamar a Gemini Flash para generar caption, hashtags y metadatos por plataforma
3. Si el activo es imagen → llamar a Cloudinary para generar variantes de tamaño
4. Si el activo tiene plantilla → llamar a Canva Autofill API
5. Si el tipo es `ai_generated_image` → llamar a Gemini Imagen 3
6. Actualizar `content_items` con todos los textos generados y URLs de assets
7. Trigger automático al Workflow 3

Ver `TECHNICAL_SPEC.md > Sección 4.2` para los prompts de Gemini y los parámetros
de cada API call.

---

### 2.4 Prueba de Fase 2

Enviar una foto de prueba al bot de Telegram y verificar:
1. El bot confirma recepción
2. La imagen aparece en Cloudinary carpeta `instagram/`
3. En Supabase, el registro en `content_items` tiene `status = 'ready_for_review'`
4. Los campos `caption_instagram`, `hashtags_instagram`, `caption_youtube` están llenos

---

## Fase 3 — Revisión, aprobación y publicación (Semana 3)

### 3.1 Workflow 3 — Revisión HITL (n8n)

Importar `n8n-workflows/03-revision.json`.

El workflow envía al chat de Telegram del aprobador:
- Miniatura del activo (imagen o frame del video)
- Caption generado para cada plataforma
- Fecha y hora sugerida de publicación
- Teclado inline con botones: `✅ Aprobar` · `✏️ Editar` · `🔄 Regenerar` · `❌ Descartar`

Implementar el árbol de decisión completo (ver `TECHNICAL_SPEC.md > Sección 4.3`).
Implementar el sistema de timeout:
- Cron cada 6 horas busca items `ready_for_review` con `updated_at < now() - interval '24 hours'`
- Primer recordatorio a las 24 h
- Estado `stalled` a las 48 h

---

### 3.2 Workflow 4 — Publicación automática (n8n)

Importar `n8n-workflows/04-publicacion.json`.

Cron cada 15 minutos. Busca en Supabase items con:
```sql
status = 'approved' AND scheduled_at <= now() AND published_at IS NULL
```

Implementar publicación para cada plataforma (ver `TECHNICAL_SPEC.md > Sección 4.4`):

**Instagram:**
- Imagen: `POST /v1/{ig-user-id}/media` → `POST /v1/{ig-user-id}/media_publish`
- Reel: upload container → publish
- Carrusel: crear N containers de imagen → crear container CAROUSEL → publish

**YouTube:**
- Verificar cuota disponible en tabla `quota_tracker` antes de cada subida
- Si `youtube_units_used + 1600 > 10000` → posponer 24h y notificar por Telegram
- Upload resumable via `videos.insert`
- Subir miniatura via `thumbnails.set` (50 unidades)

**TikTok:**
- Si `TIKTOK_API_APPROVED = true` → usar Content Posting API
- Si `TIKTOK_API_APPROVED = false` → enviar video + caption al aprobador por Telegram con instrucción de publicación manual

---

### 3.3 Prueba de Fase 3

Probar el flujo completo:
1. Enviar activo → recibir confirmación
2. Recibir vista previa en Telegram como aprobador
3. Presionar "Aprobar"
4. Verificar publicación en Instagram (usar cuenta de prueba)
5. Verificar que `content_items.status = 'published'` y `published_at` tiene fecha

---

## Fase 4 — Métricas, pruebas y ajustes (Semana 4)

### 4.1 Workflow 5 — Métricas y reporte semanal (n8n)

Importar `n8n-workflows/05-metricas.json`.

Cron: domingos a las 18:00 hora Colombia (UTC-5 = 23:00 UTC).

El workflow debe:
1. Consultar todos los `content_items` publicados en los últimos 7 días
2. Para cada uno, obtener métricas de Instagram Insights y YouTube Analytics API
3. Insertar snapshot diario en tabla `metrics`
4. Llamar a Gemini Flash con los datos para generar el resumen semanal en español
5. Enviar el resumen por Telegram al canal del equipo

Ver `TECHNICAL_SPEC.md > Sección 4.5` para el prompt del resumen y el formato esperado.

---

### 4.2 Pruebas de carga y error

Ejecutar los siguientes escenarios de prueba:

| Escenario | Comportamiento esperado |
|---|---|
| Archivo > 100 MB enviado a Telegram | Bot responde con error claro y límite |
| Video enviado (< 200 MB) | Va a R2, no a Cloudinary |
| Imagen enviada (< 20 MB) | Va a Cloudinary, no a R2 |
| Aprobador no responde en 24h | Llega recordatorio automático |
| YouTube cuota agotada | Publicación pospuesta 24h, notificación enviada |
| API de Instagram devuelve error 400 | Registro en `publish_log` con error, notificación al equipo |
| Cloudinary: más de 20 créditos usados | Alerta enviada al canal de Telegram del equipo |

---

### 4.3 Script de monitoreo de créditos

Crear un cron en n8n que corra diariamente a las 09:00 y verifique:
- Créditos usados en Cloudinary (via `GET https://api.cloudinary.com/v1_1/{cloud}/usage`)
- Unidades de cuota YouTube usadas hoy (tabla `quota_tracker`)
- Espacio usado en R2 (via Cloudflare API)

Si algún servicio supera el 80% de su límite gratuito → notificación al canal del equipo.

---

### 4.4 Importación de workflows y verificación final

```bash
bash scripts/import-workflows.sh
```

Verificar que los 5 workflows estén activos en n8n:
```bash
curl -s https://n8n.letiende.co/api/v1/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | python3 -m json.tool | grep -E '"name"|"active"'
```

**Los 5 workflows deben aparecer con `"active": true`.**

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

**Riesgo:** n8n con autenticación básica expuesto a internet; logs de ejecución retienen datos de usuarios hasta 14 días.

**Reglas:**
- No deshabilitar `N8N_BASIC_AUTH_ACTIVE` nunca.
- No modificar `EXECUTIONS_DATA_MAX_AGE` más allá de 336h (14 días).
- No exponer el puerto 5678 directamente — siempre pasar por Nginx.

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
| Montar `credentials.env` como volumen en Docker | Archivo sensible en filesystem del contenedor |
| Deshabilitar `N8N_BASIC_AUTH_ACTIVE` | n8n sin autenticación expuesto a internet |
| `Continue on Fail: ON` en nodos HTTP | Errores de API pasan silenciosamente |
| Concatenar input del usuario en prompts de Gemini | Prompt injection |
| Ignorar respuestas 401 de APIs de RRSS | Tokens vencidos no se detectan |
| Descargar archivos desde URLs no validadas en WF1 | SSRF hacia metadata service de Oracle |

---

## Git Flow para Agentes IA

Reglas **obligatorias** para cualquier agente que opere en este repositorio. No hay excepciones.

### Ramas protegidas

La rama `master` está protegida. **Ningún agente puede hacer commits directos a ella.**

### Protocolo antes de cualquier cambio de código

**Paso 1 — Verificar la rama actual:**
```bash
git branch --show-current
```
Si el resultado es `master`, ejecutar el Paso 2. Si ya hay una feature branch activa, ir al Paso 3.

**Paso 2 — Crear feature branch:**
```bash
git checkout master
git pull origin master
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
  --base master \
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
| `git push origin master` | Commit directo a producción |
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
