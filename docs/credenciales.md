# Guía de credenciales — SGCD Le Tiende.co

Este documento te guía paso a paso para obtener cada credencial que necesita el sistema.
Al final de cada sección encontrarás el bloque que debes completar en `credentials.env`.

**Instrucciones:**
1. Lee cada sección en orden.
2. Completa los valores en el archivo `credentials.env` a medida que los obtienes.
3. Nunca compartas ni subas `credentials.env` a GitHub (ya está en `.gitignore`).
4. Una vez completado, Claude Code leerá las variables ejecutando `source credentials.env`.

---

## credentials.env (plantilla completa)

Crea este archivo en la raíz del proyecto y completa cada valor:

```bash
# =============================================================
# ORACLE CLOUD — Servidor principal (n8n.letiende.co)
# =============================================================
ORACLE_VM_IP=COMPLETAR
ORACLE_SSH_KEY_PATH=COMPLETAR

# =============================================================
# AWS — Ya configurado en AWS CLI local
# Solo se necesita el Hosted Zone ID de Route 53
# =============================================================
AWS_ROUTE53_HOSTED_ZONE_ID=COMPLETAR
AWS_REGION=us-east-1
# Lambda y Route 53 se acceden via AWS CLI — no se necesitan keys aquí

# =============================================================
# n8n — Credenciales de la instancia
# =============================================================
N8N_BASIC_AUTH_USER=COMPLETAR
N8N_BASIC_AUTH_PASSWORD=COMPLETAR
N8N_ENCRYPTION_KEY=COMPLETAR
N8N_API_KEY=COMPLETAR
POSTGRES_PASSWORD=COMPLETAR
ADMIN_EMAIL=COMPLETAR

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
CLOUDINARY_CLOUD_NAME=COMPLETAR
CLOUDINARY_API_KEY=COMPLETAR
CLOUDINARY_API_SECRET=COMPLETAR

# =============================================================
# CLOUDFLARE R2 — Repositorio de videos
# =============================================================
CF_ACCOUNT_ID=COMPLETAR
CF_R2_ACCESS_KEY_ID=COMPLETAR
CF_R2_SECRET_ACCESS_KEY=COMPLETAR
CF_R2_ENDPOINT=COMPLETAR

# =============================================================
# CANVA — Plantillas de marca
# =============================================================
CANVA_API_KEY=COMPLETAR
CANVA_BRAND_TEMPLATE_IDS=COMPLETAR

# =============================================================
# SUPABASE — Base de datos
# =============================================================
SUPABASE_URL=COMPLETAR
SUPABASE_ANON_KEY=COMPLETAR
SUPABASE_SERVICE_ROLE_KEY=COMPLETAR

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

### Cómo crear la cuenta y la VM

1. Ve a [cloud.oracle.com](https://cloud.oracle.com) → **Start for free**
2. Regístrate con tu email corporativo. Oracle pedirá una tarjeta de crédito para verificación — **no te cobra** mientras uses el Always Free tier.
3. Una vez dentro del panel:
   - Ve a **Compute → Instances → Create Instance**
   - Nombre: `letiende-n8n`
   - Image: **Ubuntu 22.04** (Canonical)
   - Shape: **VM.Standard.E2.1.Micro** (Always Free) — 1 OCPU, 1 GB RAM
   - En "Add SSH keys": sube tu llave pública SSH o genera una nueva. Guarda la llave privada.
   - En "Networking": asegúrate de que tenga IP pública asignada
4. Crea la instancia y espera ~3 minutos a que esté **Running**
5. Anota la **Public IP address** de la instancia

### Variables a completar

```bash
ORACLE_VM_IP=           # IP pública de la VM. Ejemplo: 141.148.32.55
ORACLE_SSH_KEY_PATH=    # Ruta local a tu llave privada SSH. Ejemplo: ~/.ssh/oracle_letiende.pem
```

### Puerto 443 en Oracle (firewall)

Oracle bloquea los puertos por defecto. Después de crear la VM:
- Ve a **Networking → Virtual Cloud Networks → tu VCN → Security Lists**
- Agrega regla de entrada: Protocol TCP, Source 0.0.0.0/0, Destination Port 443
- Agrega regla de entrada: Protocol TCP, Source 0.0.0.0/0, Destination Port 80

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

> **Nota:** AWS CLI ya está configurado en tu equipo. No se necesitan keys adicionales de AWS para Lambda ni Route 53 — se usan las credenciales del CLI.

---

## 3. n8n — Credenciales internas

Estos valores los inventas tú (son contraseñas internas del sistema):

### Variables a completar

```bash
N8N_BASIC_AUTH_USER=      # Usuario para entrar al panel de n8n. Ejemplo: admin
N8N_BASIC_AUTH_PASSWORD=  # Contraseña segura. Mínimo 16 caracteres con símbolos.
N8N_ENCRYPTION_KEY=       # Clave de cifrado para credenciales en n8n.
                          # Genera una con: openssl rand -hex 32
POSTGRES_PASSWORD=        # Contraseña para la base de datos interna de n8n.
                          # Genera una con: openssl rand -hex 24
ADMIN_EMAIL=              # Tu email, para el certificado SSL. Ejemplo: admin@letiende.co
```

Para generar las claves seguras en tu terminal:
```bash
openssl rand -hex 32   # para N8N_ENCRYPTION_KEY
openssl rand -hex 24   # para POSTGRES_PASSWORD
```

**N8N_API_KEY:** Se obtiene después de que n8n esté funcionando:
1. Entra a `https://n8n.letiende.co`
2. Ve a **Settings → API → Create API Key**
3. Copia la key generada

```bash
N8N_API_KEY=   # Se completa después del despliegue en la Semana 1
```

---

## 4. Telegram Bot

### Crear el bot

1. Abre Telegram y busca **@BotFather**
2. Envía el comando `/newbot`
3. Nombre del bot: `Le Tiende Contenidos` (o el nombre que prefieras)
4. Username del bot: debe terminar en `bot`. Ejemplo: `letiende_contenidos_bot`
5. BotFather te dará el **token** — formato: `1234567890:ABCdef...`

### Obtener los Chat IDs

Para `TELEGRAM_APPROVER_CHAT_ID` (la persona que aprueba contenidos):
1. El aprobador debe iniciar una conversación con el bot (enviar cualquier mensaje)
2. Abre en el navegador: `https://api.telegram.org/bot{TU_TOKEN}/getUpdates`
3. En la respuesta JSON, busca `message.chat.id` — ese es el Chat ID del aprobador

Para `TELEGRAM_ADMIN_CHAT_ID` (canal de alertas del equipo técnico):
- Puede ser el mismo Chat ID del aprobador al inicio, o un grupo de Telegram
- Para un grupo: agregar el bot al grupo y repetir el proceso anterior

### Variables a completar

```bash
TELEGRAM_BOT_TOKEN=          # Ejemplo: 1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
TELEGRAM_APPROVER_CHAT_ID=   # Ejemplo: 987654321
TELEGRAM_ADMIN_CHAT_ID=      # Ejemplo: 987654321 (puede ser el mismo al inicio)
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

> **Límites del plan gratuito:** 1.500 solicitudes/día para Gemini Flash, ~1.000 imágenes/día para Imagen 3. Sin costo mientras no superes estos límites.

---

## 6. YouTube Data API v3

Este proceso requiere varios pasos porque YouTube usa OAuth 2.0 para subir videos.

### Paso 1 — Crear proyecto y habilitar la API

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto: **Le Tiende SGCD**
3. Ve a **APIs & Services → Library**
4. Busca y habilita: **YouTube Data API v3** y **YouTube Analytics API**

### Paso 2 — Crear credenciales OAuth 2.0

1. Ve a **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Web application**
3. Name: `letiende-sgcd`
4. Authorized redirect URIs: `https://developers.google.com/oauthplayground`
5. Copia el **Client ID** y el **Client Secret**

### Paso 3 — Obtener el Refresh Token

1. Ve a [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground)
2. Haz clic en el ícono de engranaje (⚙️) → activa **Use your own OAuth credentials**
3. Pega tu Client ID y Client Secret
4. En la lista de APIs (izquierda), busca y selecciona:
   - `YouTube Data API v3 → https://www.googleapis.com/auth/youtube`
   - `YouTube Analytics API → https://www.googleapis.com/auth/yt-analytics.readonly`
5. Haz clic en **Authorize APIs** → inicia sesión con la cuenta de YouTube de la marca
6. Haz clic en **Exchange authorization code for tokens**
7. Copia el **Refresh token** (el campo `refresh_token`)

### Variables a completar

```bash
YOUTUBE_CLIENT_ID=       # Ejemplo: 123456789-abc.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=   # Ejemplo: GOCSPX-abc123DEF456
YOUTUBE_REFRESH_TOKEN=   # Ejemplo: 1//0abc123-DEF456...
```

---

## 7. Cloudinary — Repositorio de imágenes

### Obtener credenciales

1. Entra a tu cuenta en [cloudinary.com](https://cloudinary.com) → **Dashboard**
2. En la sección **API Keys** encontrarás los tres valores directamente en la pantalla principal

### Variables a completar

```bash
CLOUDINARY_CLOUD_NAME=   # Ejemplo: letiende (nombre corto de tu cuenta)
CLOUDINARY_API_KEY=      # Ejemplo: 123456789012345
CLOUDINARY_API_SECRET=   # Ejemplo: abcDEF123ghiJKL456mnoPQR
```

---

## 8. Cloudflare R2 — Repositorio de videos

### Crear cuenta y habilitar R2

1. Ve a [cloudflare.com](https://cloudflare.com) → crea cuenta gratuita
2. En el panel izquierdo → **R2 Object Storage**
3. Habilitar R2 (pedirá tarjeta de crédito — no cobra hasta superar 10 GB)

### Obtener el Account ID

- En el panel de Cloudflare → esquina superior derecha → **Account ID** visible en el sidebar

### Crear API Token para R2

1. Ve a **My Profile → API Tokens → Create Token**
2. Usa la plantilla **Edit Cloudflare Workers** o crea uno personalizado con:
   - Permisos: `Workers R2 Storage — Edit`
3. Copia el token generado

### Obtener Access Key para R2 (compatible con S3)

1. En **R2 → Manage R2 API Tokens → Create API Token**
2. Permissions: **Admin Read & Write**
3. Se generarán un **Access Key ID** y un **Secret Access Key** — guárdalos en ese momento, no se vuelven a mostrar

### Variables a completar

```bash
CF_ACCOUNT_ID=            # Ejemplo: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
CF_R2_ACCESS_KEY_ID=      # Ejemplo: abc123DEF456ghi789JKL
CF_R2_SECRET_ACCESS_KEY=  # Ejemplo: xyz987WVU654tsr321QPO
CF_R2_ENDPOINT=           # Formato: https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com
```

---

## 9. Canva Pro — API de plantillas

### Activar Canva Connect

1. Entra a [canva.com](https://canva.com) con la cuenta Pro de Le Tiende
2. Ve a **Settings (⚙️) → Apps & integrations → Canva Connect**
3. Si no aparece, buscar en [developers.canva.com](https://developers.canva.com) → **Get started**
4. Crea una integración: **Le Tiende SGCD**
5. Copia el **API Key** generado

### Obtener los IDs de Brand Templates

1. En Canva, abre cada plantilla de marca que quieras usar en el pipeline
2. La URL de la plantilla tiene el formato: `https://www.canva.com/design/{DESIGN_ID}/edit`
3. Copia el `DESIGN_ID` de cada plantilla

### Variables a completar

```bash
CANVA_API_KEY=             # Ejemplo: eyJhbGciOiJFZERTQSIsImtpZCI6...
CANVA_BRAND_TEMPLATE_IDS=  # IDs separados por coma. Ejemplo: DAFxyz123,DAFabc456,DAFdef789
```

---

## 10. Supabase — Base de datos

### Crear proyecto

1. Ve a [supabase.com](https://supabase.com) → **New project**
2. Organization: crear una nueva o usar la existente
3. Project name: `letiende-sgcd`
4. Database Password: genera una contraseña fuerte y guárdala aparte
5. Region: **South America (São Paulo)** — la más cercana a Colombia
6. Espera ~2 minutos mientras se provisiona

### Obtener las keys

1. Ve a **Project Settings → API**
2. Encontrarás:
   - **Project URL** → es `SUPABASE_URL`
   - **anon public** key → es `SUPABASE_ANON_KEY`
   - **service_role secret** key → es `SUPABASE_SERVICE_ROLE_KEY`

### Variables a completar

```bash
SUPABASE_URL=               # Ejemplo: https://abcdefghijkl.supabase.co
SUPABASE_ANON_KEY=          # Ejemplo: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=  # Ejemplo: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

> ⚠️ `SUPABASE_SERVICE_ROLE_KEY` tiene permisos totales sobre la base de datos. Solo usarla en el servidor (n8n, scripts de setup) — nunca en el frontend.

---

## 11. Meta / Instagram

Este es el proceso más complejo. Requiere una cuenta Business de Instagram conectada a una Página de Facebook.

### Requisitos previos

- Cuenta de Instagram de la marca convertida a **cuenta profesional (Business)**
- Página de Facebook asociada a esa cuenta de Instagram
- Acceso de administrador a esa Página de Facebook

### Paso 1 — Crear App en Meta for Developers

1. Ve a [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App**
2. Type: **Business**
3. App name: `Le Tiende SGCD`
4. Contact email: tu email corporativo
5. En el dashboard de la app, copia el **App ID** y el **App Secret** (Settings → Basic)

### Paso 2 — Agregar el producto Instagram Graph API

1. En tu app → **Add Product → Instagram Graph API**
2. Ve a **Instagram Graph API → Settings**
3. Agrega tu cuenta de Instagram como cuenta de prueba

### Paso 3 — Obtener el Access Token de larga duración

1. Ve a [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)
2. Selecciona tu app en el menú superior
3. Haz clic en **Generate Access Token** — seleccionar permisos:
   - `instagram_basic`
   - `instagram_content_publish`
   - `instagram_manage_insights`
   - `pages_read_engagement`
4. Copia el token generado (es de corta duración — 1 hora)
5. Conviértelo a **token de larga duración** (60 días):
   ```
   https://graph.facebook.com/v19.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={APP_ID}
     &client_secret={APP_SECRET}
     &fb_exchange_token={SHORT_TOKEN}
   ```
   Abre esa URL en el navegador y copia el `access_token` de la respuesta.

> **Nota:** Los tokens de Instagram caducan cada 60 días. El sistema incluirá un cron que los renueva automáticamente antes de que expiren.

### Paso 4 — Obtener el Instagram User ID

```bash
curl "https://graph.facebook.com/v19.0/me/accounts?access_token={TU_ACCESS_TOKEN}"
```
En la respuesta, busca la página conectada a tu Instagram. Luego:
```bash
curl "https://graph.facebook.com/v19.0/{PAGE_ID}?fields=instagram_business_account&access_token={TU_ACCESS_TOKEN}"
```
El campo `instagram_business_account.id` es tu `INSTAGRAM_USER_ID`.

### Variables a completar

```bash
INSTAGRAM_APP_ID=        # Ejemplo: 1234567890123456
INSTAGRAM_APP_SECRET=    # Ejemplo: abc123def456ghi789jkl012mno345pq
INSTAGRAM_ACCESS_TOKEN=  # Token de larga duración (60 días)
INSTAGRAM_USER_ID=       # Ejemplo: 17841400000000000
```

---

## 12. TikTok (completar solo si la API fue aprobada)

### Aplicar a la Content Posting API

1. Ve a [developers.tiktok.com](https://developers.tiktok.com) → **Manage Apps → Create App**
2. En la app creada, solicita el scope: **Content Posting API**
3. Llena el formulario de aprobación — puede tomar 2 a 4 semanas
4. Una vez aprobado, obtén el **Client Key** y **Client Secret** desde el dashboard

### Obtener Access Token

Sigue el flujo OAuth 2.0 de TikTok una vez que tengas la app aprobada.
Documentación: [developers.tiktok.com/doc/login-kit-web](https://developers.tiktok.com/doc/login-kit-web)

### Variables a completar

```bash
TIKTOK_API_APPROVED=true         # Cambiar a true solo cuando la API esté aprobada
TIKTOK_CLIENT_KEY=               # Ejemplo: awxyz1234567890
TIKTOK_CLIENT_SECRET=            # Ejemplo: abc123DEF456ghi789JKL012mno
TIKTOK_ACCESS_TOKEN=             # Token generado después de la autorización OAuth
```

---

## Lista de verificación final

Antes de entregar `credentials.env` a Claude Code, verifica que ningún valor diga `COMPLETAR`:

```bash
grep "COMPLETAR" credentials.env
```

Si el comando no devuelve nada, todas las credenciales están completas.

**Servicios que pueden quedar en `COMPLETAR` temporalmente (tienen plan B):**
- `TIKTOK_*` — El sistema funciona sin TikTok (publica manualmente)
- `N8N_API_KEY` — Se obtiene después del despliegue de la Semana 1

---

## Seguridad

- `credentials.env` ya está en `.gitignore` — nunca se sube a GitHub
- No envíes este archivo por email ni WhatsApp — usa un gestor de contraseñas (1Password, Bitwarden) o compártelo por canal cifrado
- Si alguna credencial es comprometida, revócala inmediatamente desde el panel del servicio correspondiente y genera una nueva
