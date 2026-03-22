# Guía de credenciales — SGCD Le Tiende.co

Este documento explica **cómo obtener** cada credencial del sistema.
Los valores reales viven **únicamente** en `credentials.env` (gitignoreado).

**Instrucciones:**
1. Lee cada sección en orden.
2. Completa los valores en el archivo `credentials.env` a medida que los obtienes.
3. Nunca compartas ni subas `credentials.env` a GitHub (ya está en `.gitignore`).
4. Ejecuta `source credentials.env` antes de correr cualquier script.

---

## credentials.env (estructura completa)

Crea este archivo en la raíz del proyecto y completa cada valor:

```bash
# =============================================================
# ORACLE CLOUD — Servidor principal (n8n.letiende.co)
# =============================================================
ORACLE_VM_IP=150.136.139.189
ORACLE_SSH_KEY_PATH=~/.ssh/id_ed25519_github

# OCIDs generados durante setup
OCI_INSTANCE_ID=ocid1.instance.oc1.iad...
OCI_VCN_ID=ocid1.vcn.oc1.iad...
OCI_SUBNET_ID=ocid1.subnet.oc1.iad...
OCI_IGW_ID=ocid1.internetgateway.oc1.iad...
OCI_USER_ID=ocid1.user.oc1...
OCI_TENANCY_ID=ocid1.tenancy.oc1...
OCI_REGION=us-ashburn-1
OCI_API_KEY_FINGERPRINT=xx:xx:xx:...
OCI_API_KEY_PATH=~/.oci/letiende_api_key.pem

# =============================================================
# AWS — Ya configurado en AWS CLI local
# =============================================================
AWS_ROUTE53_HOSTED_ZONE_ID=COMPLETAR
AWS_REGION=us-east-1

# =============================================================
# n8n — Credenciales de la instancia
# =============================================================
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=COMPLETAR
N8N_ENCRYPTION_KEY=COMPLETAR
N8N_API_KEY=COMPLETAR
POSTGRES_PASSWORD=COMPLETAR
ADMIN_EMAIL=letiende.co@gmail.com

# =============================================================
# TELEGRAM BOT
# =============================================================
TELEGRAM_BOT_TOKEN=COMPLETAR
TELEGRAM_APPROVER_CHAT_ID=COMPLETAR
TELEGRAM_ADMIN_CHAT_ID=COMPLETAR

# =============================================================
# GOOGLE — Gemini IA
# =============================================================
GEMINI_API_KEY=COMPLETAR

# =============================================================
# GOOGLE — YouTube Data API v3
# =============================================================
YOUTUBE_CLIENT_ID=COMPLETAR
YOUTUBE_CLIENT_SECRET=COMPLETAR
YOUTUBE_REFRESH_TOKEN=COMPLETAR

# =============================================================
# CLOUDINARY — Repositorio de imágenes
# =============================================================
CLOUDINARY_CLOUD_NAME=letiende
CLOUDINARY_API_KEY=COMPLETAR
CLOUDINARY_API_SECRET=COMPLETAR

# =============================================================
# CLOUDFLARE R2 — Repositorio de videos
# =============================================================
CF_ACCOUNT_ID=COMPLETAR
CF_R2_ACCESS_KEY_ID=COMPLETAR
CF_R2_SECRET_ACCESS_KEY=COMPLETAR
CF_R2_ENDPOINT=https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com

# =============================================================
# CANVA — Plantillas de marca (en espera de acceso beta)
# =============================================================
CANVA_API_KEY=COMPLETAR
CANVA_BRAND_TEMPLATE_IDS=COMPLETAR

# =============================================================
# SUPABASE — Base de datos
# =============================================================
SUPABASE_URL=https://iljbfgbndwfaqacxthty.supabase.co
SUPABASE_ANON_KEY=COMPLETAR
SUPABASE_SERVICE_ROLE_KEY=COMPLETAR
SUPABASE_ACCESS_TOKEN=COMPLETAR
SUPABASE_DB_HOST=aws-1-us-east-1.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_USER=postgres.iljbfgbndwfaqacxthty
SUPABASE_DB_PASSWORD=COMPLETAR
SUPABASE_DB_URL=COMPLETAR

# =============================================================
# META / INSTAGRAM
# =============================================================
INSTAGRAM_APP_ID=COMPLETAR
INSTAGRAM_APP_SECRET=COMPLETAR
INSTAGRAM_ACCESS_TOKEN=COMPLETAR
INSTAGRAM_USER_ID=COMPLETAR

# =============================================================
# TIKTOK (completar solo si la API fue aprobada)
# =============================================================
TIKTOK_API_APPROVED=false
TIKTOK_CLIENT_KEY=COMPLETAR
TIKTOK_CLIENT_SECRET=COMPLETAR
TIKTOK_ACCESS_TOKEN=COMPLETAR
```

---

## 1. Oracle Cloud — VM Always Free

### ✅ Instancia creada y operativa

| Campo | Valor |
|---|---|
| Instancia | `letiende-n8n` |
| IP Pública | `150.136.139.189` |
| Shape | VM.Standard.E2.1.Micro (AMD, 1 OCPU, 1 GB RAM + 2 GB swap) |
| OS | Ubuntu 24.04 LTS |
| SSH Key | `~/.ssh/id_ed25519_github` |
| Region | us-ashburn-1 (AD-2) |
| VCN | `vcn-letiende-n8n` |
| Subnet | `public-subnet-letiendeco-n8n` |
| SSL | Let's Encrypt — válido hasta 2026-06-18 |

> **Nota:** Se está reintentando obtener una VM.Standard.A1.Flex (ARM, 4 OCPU / 24 GB) en background. Cuando esté disponible se migrará el stack.

Las contraseñas generadas (n8n, PostgreSQL, encryption key) están en `credentials.env`.

---

## 2. AWS Route 53 — Hosted Zone ID

### Cómo obtenerlo

El dominio `letiende.co` ya está registrado en AWS. Solo necesitas el ID de la Hosted Zone.

1. Abre la consola de AWS → busca **Route 53**
2. Ve a **Hosted zones**
3. Haz clic en `letiende.co`
4. En la parte superior encontrarás el **Hosted zone ID** — tiene formato `Z0123456789ABC`

### Variables a completar

```bash
AWS_ROUTE53_HOSTED_ZONE_ID=   # Ejemplo: Z0123456789ABCDEF1234
```

> **Nota:** AWS CLI ya está configurado en tu equipo. No se necesitan keys adicionales de AWS para Lambda ni Route 53.

---

## 3. n8n — Credenciales internas

### ✅ Instancia desplegada y operativa

| Campo | Estado |
|---|---|
| URL | https://n8n.letiende.co |
| Usuario | `admin` |
| Contraseña | `ver credentials.env` |
| N8N_ENCRYPTION_KEY | `ver credentials.env` |
| POSTGRES_PASSWORD | `ver credentials.env` |
| ADMIN_EMAIL | `letiende.co@gmail.com` |

### N8N_API_KEY — obtener desde el panel

1. Entra a `https://n8n.letiende.co`
2. Ve a **Settings → API → Create API Key**
3. Copia la key y agrégala a `credentials.env`

```bash
N8N_API_KEY=   # Obtener desde https://n8n.letiende.co/settings/api
```

---

## 4. Telegram Bot

### Crear el bot

1. Abre Telegram y busca **@BotFather**
2. Envía el comando `/newbot`
3. Nombre del bot: `Le Tiende Contenidos`
4. Username: debe terminar en `bot` — ej: `letiende_contenidos_bot`
5. BotFather te dará el **token** — formato: `1234567890:ABCdef...`

### Obtener los Chat IDs

Para `TELEGRAM_APPROVER_CHAT_ID`:
1. El aprobador envía cualquier mensaje al bot
2. Abre: `https://api.telegram.org/bot{TU_TOKEN}/getUpdates`
3. En la respuesta JSON, busca `message.chat.id`

Para grupos: agregar el bot al grupo y repetir el proceso.

### Variables a completar

```bash
TELEGRAM_BOT_TOKEN=          # Ejemplo: 1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
TELEGRAM_APPROVER_CHAT_ID=   # Ejemplo: -987654321 (negativo si es grupo)
TELEGRAM_ADMIN_CHAT_ID=      # Puede ser el mismo que APPROVER al inicio
```

---

## 5. Google Gemini — IA de generación de contenido

### Obtener API Key

1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Inicia sesión con la cuenta de Google de la empresa
3. Haz clic en **Get API key → Create API key**
4. Selecciona **Create API key in new project**
5. Copia la key generada

### Variables a completar

```bash
GEMINI_API_KEY=   # Ejemplo: AIzaSyABC123def456GHI789jkl
```

> **Límites del plan gratuito:** 1.500 solicitudes/día para Gemini Flash, ~1.000 imágenes/día para Imagen 3.

---

## 6. YouTube Data API v3

### Paso 1 — Crear proyecto y habilitar la API

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto: **Le Tiende SGCD**
3. Ve a **APIs & Services → Library**
4. Habilita: **YouTube Data API v3** y **YouTube Analytics API**

### Paso 2 — Crear credenciales OAuth 2.0

1. Ve a **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Web application**
3. Name: `letiende-sgcd`
4. Authorized redirect URIs: `https://developers.google.com/oauthplayground`
5. Copia el **Client ID** y el **Client Secret**

### Paso 3 — Obtener el Refresh Token

1. Ve a [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground)
2. Ícono de engranaje (⚙️) → activa **Use your own OAuth credentials**
3. Pega tu Client ID y Client Secret
4. Selecciona los scopes:
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/yt-analytics.readonly`
5. **Authorize APIs** → iniciar sesión con la cuenta de YouTube de la marca
6. **Exchange authorization code for tokens**
7. Copia el `refresh_token`

### Variables a completar

```bash
YOUTUBE_CLIENT_ID=       # Ejemplo: 123456789-abc.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=   # Ejemplo: GOCSPX-abc123DEF456
YOUTUBE_REFRESH_TOKEN=   # Ejemplo: 1//0abc123-DEF456...
```

---

## 7. Cloudinary — Repositorio de imágenes

### ✅ Configurado

Cloud name: `letiende`. API Key y Secret en `credentials.env`.

### Cómo obtener las credenciales (para replicar en otro cliente)

1. Entra a [cloudinary.com](https://cloudinary.com) → **Dashboard**
2. En la sección **API Keys** encontrarás los tres valores en la pantalla principal

### Variables a completar

```bash
CLOUDINARY_CLOUD_NAME=   # Ejemplo: mi-empresa
CLOUDINARY_API_KEY=      # Ejemplo: 123456789012345
CLOUDINARY_API_SECRET=   # Ejemplo: abcDEF123ghiJKL456mnoPQR
```

---

## 8. Cloudflare R2 — Repositorio de videos

### ✅ Buckets creados y verificados

| Bucket | Lifecycle | Estado |
|---|---|---|
| `letiende-raw-assets` | 30 días | ✅ |
| `letiende-processed-assets` | 90 días | ✅ |
| `letiende-templates-backup` | Sin expiración | ✅ |

> **Nota técnica:** AWS CLI v2 usa `chunked encoding + CRC64NVME` incompatible con R2. Los scripts usan `boto3` con `payload_signing_enabled=False` para PutObject/DeleteObject.

### Cómo obtener las credenciales R2

1. Panel de Cloudflare → **R2 Object Storage → Manage R2 API Tokens**
2. **Create API Token** con permisos de lectura/escritura
3. El **Access Key ID** tiene ~32 caracteres
4. El **Secret Access Key** tiene ~64 caracteres
5. El **Account ID** lo encuentras en la esquina superior derecha del panel

Las credenciales actuales están en `credentials.env`.

---

## 9. Canva Pro — API de plantillas

### Estado actual

La API de Canva Connect (Autofill) está en **acceso restringido beta**.
Se requiere aprobación explícita de Canva para usarla.

> **Decisión de diseño:** Los workflows actuales omiten la integración con Canva.
> Cloudinary cubre la generación de variantes de imagen por plataforma.
> Cuando Canva otorgue acceso, se agrega como nodo opcional al Workflow 2.

### Cómo activarla cuando esté disponible

1. Ir a [developers.canva.com](https://developers.canva.com)
2. Solicitar acceso al programa beta de Autofill API
3. Una vez aprobado: **Create Integration → Le Tiende SGCD**
4. Copiar el API Key generado

```bash
CANVA_API_KEY=             # Pendiente de aprobación beta
CANVA_BRAND_TEMPLATE_IDS=  # IDs separados por coma: DAFxyz123,DAFabc456
```

---

## 10. Supabase — Base de datos

### ✅ Configurado

Proyecto: `iljbfgbndwfaqacxthty` — Región: us-east-1.
Todas las credenciales en `credentials.env`.

### Cómo obtener las keys (nuevo panel Supabase 2024+)

| Lo que ves en el panel | Variable en credentials.env |
|---|---|
| **Project ID** | Se usa para construir la URL |
| **Publishable key** | `SUPABASE_ANON_KEY` |
| **Secret key** | `SUPABASE_SERVICE_ROLE_KEY` |

Ruta: **Project Settings → API** (o **Data API**)

### Conexión directa (pooler)

Los proyectos nuevos de Supabase usan pooler, no host directo:
- Host: `aws-0-{region}.pooler.supabase.com` o `aws-1-{region}.pooler.supabase.com`
- User: `postgres.{project-ref}` (no solo `postgres`)
- Contraseña: URL-encoded (`&` → `%26`, `$` → `%24`, `!` → `%21`)

### Variables a completar (nuevo cliente)

```bash
SUPABASE_URL=               # https://{PROJECT_ID}.supabase.co
SUPABASE_ANON_KEY=          # La "Publishable key"
SUPABASE_SERVICE_ROLE_KEY=  # La "Secret key" — solo en servidor, nunca en frontend
SUPABASE_DB_HOST=           # aws-0-{region}.pooler.supabase.com
SUPABASE_DB_USER=           # postgres.{project-ref}
SUPABASE_DB_PASSWORD=       # Generada al crear el proyecto
```

---

## 11. Meta / Instagram

*(Integración diferida — se conecta en una fase posterior)*

### Requisitos previos

- Cuenta de Instagram de la marca convertida a **cuenta profesional (Business)**
- Página de Facebook asociada a esa cuenta de Instagram

### Paso 1 — Crear App en Meta for Developers

1. [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App**
2. Type: **Business** → Name: `Le Tiende SGCD`
3. Copia el **App ID** y **App Secret** (Settings → Basic)

### Paso 2 — Obtener Access Token de larga duración

1. [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)
2. Selecciona tu app → **Generate Access Token** con permisos:
   - `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_read_engagement`
3. Convierte a token de 60 días:
   ```
   https://graph.facebook.com/v19.0/oauth/access_token
     ?grant_type=fb_exchange_token&client_id={APP_ID}
     &client_secret={APP_SECRET}&fb_exchange_token={SHORT_TOKEN}
   ```

### Paso 3 — Obtener Instagram User ID

```bash
curl "https://graph.facebook.com/v19.0/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN}"
```

```bash
INSTAGRAM_APP_ID=        # Ejemplo: 1234567890123456
INSTAGRAM_APP_SECRET=    # Ejemplo: abc123def456ghi789
INSTAGRAM_ACCESS_TOKEN=  # Token de larga duración (60 días)
INSTAGRAM_USER_ID=       # Ejemplo: 17841400000000000
```

> Los tokens de Instagram caducan cada 60 días. El sistema incluirá un cron de renovación automática.

---

## 12. TikTok (completar solo si la API fue aprobada)

1. [developers.tiktok.com](https://developers.tiktok.com) → **Manage Apps → Create App**
2. Solicita el scope: **Content Posting API** (aprobación: 2-4 semanas)
3. Una vez aprobado: obtén **Client Key** y **Client Secret**

```bash
TIKTOK_API_APPROVED=true   # Cambiar a true solo cuando esté aprobada
TIKTOK_CLIENT_KEY=         # Ejemplo: awxyz1234567890
TIKTOK_CLIENT_SECRET=      # Ejemplo: abc123DEF456ghi789
TIKTOK_ACCESS_TOKEN=       # Generado via OAuth 2.0 de TikTok
```

---

## Lista de verificación final

```bash
grep "COMPLETAR" credentials.env
```

Si el comando no devuelve nada, todas las credenciales están completas.

**Pueden quedar en `COMPLETAR` temporalmente:**
- `TIKTOK_*` — El sistema funciona sin TikTok (publica manualmente via Telegram)
- `CANVA_*` — Pendiente de aprobación beta
- `INSTAGRAM_*` — Integración diferida a fase posterior

---

## Seguridad

- `credentials.env` está en `.gitignore` — nunca se sube a GitHub
- No envíes este archivo por email ni WhatsApp — usa 1Password o Bitwarden
- Si alguna credencial es comprometida, revócala inmediatamente desde el panel del servicio
