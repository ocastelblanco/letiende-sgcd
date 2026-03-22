# Fase 1 — Guía técnica replicable: Infraestructura base SGCD

## Introducción

Esta guía permite desplegar de cero la **Fase 1 del Sistema de Gestión y Contenidos Digitales (SGCD)** para cualquier cliente nuevo. Al completarla, tendrás un sistema funcional con:

- **n8n** (orquestación de flujos) accesible en `https://n8n.{dominio}`
- **Cloudflare R2** con tres buckets para almacenamiento de activos
- **Supabase** con base de datos PostgreSQL configurada
- **DNS** apuntando correctamente con SSL/TLS validado
- **Docker stack** en Oracle Cloud VM ejecutándose sin errores

**Duración estimada:** 2-3 horas (incluida la propagación DNS y provisioning de recursos).

---

## Prerrequisitos

Antes de empezar, necesitas tener acceso a:

### Cuentas en la nube

| Proveedor | Necesario | Rol / Alcance |
|-----------|----------|--------------|
| **Oracle Cloud** | Sí | Crear VM Always Free (`VM.Standard.A1.Flex` o `VM.Standard.E2.1.Micro`) |
| **Cloudflare** | Sí | Crear R2 buckets con API token |
| **Supabase** | Sí | Crear proyecto PostgreSQL e inyectar schema |
| **AWS (Route 53)** | Sí | Crear registro DNS A (ya debe estar configurado) |
| **Google Cloud** | Opcional (Fase 2) | Para Gemini API y YouTube Data API |

### Herramientas locales

Instala estas herramientas en tu máquina antes de empezar:

```bash
# macOS
brew install awscli postgresql curl git

# Ubuntu/Debian
sudo apt install awscli postgresql-client curl git python3 python3-pip

# Python (para el script de R2)
pip3 install boto3
```

Verifica las versiones:
```bash
aws --version          # AWS CLI v2.x
psql --version         # PostgreSQL client 12+
curl --version         # curl 7.x+
python3 --version      # Python 3.8+
```

### Variables de entorno y secretos

Necesitas obtener y guardar estas variables en un archivo `credentials.env` en la raíz del proyecto. No commitear este archivo (está en `.gitignore`).

| Variable | Dónde obtenerla | Ejemplo / Notas |
|----------|-----------------|-----------------|
| `ORACLE_VM_IP` | Asignada al crear VM en Oracle | `150.136.139.189` (pública) |
| `ORACLE_SSH_KEY_PATH` | Tu directorio `~/.ssh/` | `~/.ssh/id_ed25519` |
| `AWS_ROUTE53_HOSTED_ZONE_ID` | AWS Console → Route 53 → Hosted Zones | `Z010633738KAGFIPOZVEW` |
| `ADMIN_EMAIL` | Email tuyo para certificados SSL | `ejemplo@dominio.com` |
| `CF_ACCOUNT_ID` | Cloudflare → Account → Overview | `424b011991022bd9...` |
| `CF_R2_ACCESS_KEY_ID` | Cloudflare → R2 → Manage R2 API Tokens | ~32 caracteres |
| `CF_R2_SECRET_ACCESS_KEY` | Cloudflare → R2 → Manage R2 API Tokens | ~64 caracteres |
| `CF_R2_ENDPOINT` | Cloudflare → R2 → Buckets | `https://{account-id}.r2.cloudflarestorage.com` |
| `SUPABASE_URL` | Supabase Project → Settings → API | `https://proyecto-id.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Project → Settings → API | Prefijo `sb_secret_...` |
| `SUPABASE_DB_HOST` | Connection string | `aws-0-{region}.pooler.supabase.com` o `aws-1-...` |
| `SUPABASE_DB_PORT` | Connection string | `5432` |
| `SUPABASE_DB_USER` | Connection string | `postgres.{project-id}` |
| `SUPABASE_DB_PASSWORD` | Connection string | Generada por Supabase (URL-encoded en la URL) |
| `TELEGRAM_BOT_TOKEN` | BotFather de Telegram | `8708970956:AAFvh...` |
| `TELEGRAM_APPROVER_CHAT_ID` | Telegram (Chat con el bot) | `-5249716260` (grupo) o ID numérico |
| `TELEGRAM_ADMIN_CHAT_ID` | Telegram (Chat con el bot) | `-5249716260` (mismo que approver o diferente) |
| `N8N_BASIC_AUTH_USER` | Define tú | `admin` (usuario para login en n8n) |
| `N8N_BASIC_AUTH_PASSWORD` | Define tú (criptográfico) | Mínimo 12 caracteres, incluir mayúsculas y números |
| `N8N_ENCRYPTION_KEY` | Define tú (generado) | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Define tú (criptográfico) | Mínimo 12 caracteres |

Crea `credentials.env` en la raíz del proyecto con todos estos valores. Usa `credentials.env.example` como plantilla.

### Costos estimados (primer mes)

| Servicio | Plan | Costo |
|----------|------|-------|
| Oracle Cloud VM | Always Free | **$0** (limitado a 4 OCPU + 24 GB RAM) |
| Cloudflare R2 | Pay-as-you-go | ~$0.015 USD por GB almacenado |
| Supabase | Free tier | **$0** (hasta 500 MB base de datos) |
| AWS Route 53 | Pay-per-query | ~$0.40 USD por millón de queries |
| **Total** | | **< $1 USD al mes** |

---

## Paso 1: Inicializar repositorio Git

```bash
# Crear directorio del proyecto
mkdir letiende-sgcd
cd letiende-sgcd

# Inicializar Git
git init

# Crear estructura de directorios
mkdir -p infrastructure supabase lambda/video-processor scripts n8n-workflows docs

# Crear .gitignore
cat > .gitignore << 'EOF'
credentials.env
node_modules/
.DS_Store
.env
*.log
.omc/
EOF

# Crear credentials.env.example
cat > credentials.env.example << 'EOF'
# ORACLE CLOUD
ORACLE_VM_IP=COMPLETAR
ORACLE_SSH_KEY_PATH=COMPLETAR

# AWS
AWS_ROUTE53_HOSTED_ZONE_ID=COMPLETAR

# n8n
N8N_BASIC_AUTH_USER=COMPLETAR
N8N_BASIC_AUTH_PASSWORD=COMPLETAR
N8N_ENCRYPTION_KEY=COMPLETAR
POSTGRES_PASSWORD=COMPLETAR
ADMIN_EMAIL=COMPLETAR

# Telegram
TELEGRAM_BOT_TOKEN=COMPLETAR
TELEGRAM_APPROVER_CHAT_ID=COMPLETAR
TELEGRAM_ADMIN_CHAT_ID=COMPLETAR

# Cloudflare R2
CF_ACCOUNT_ID=COMPLETAR
CF_R2_ACCESS_KEY_ID=COMPLETAR
CF_R2_SECRET_ACCESS_KEY=COMPLETAR
CF_R2_ENDPOINT=COMPLETAR

# Supabase
SUPABASE_URL=COMPLETAR
SUPABASE_SERVICE_ROLE_KEY=COMPLETAR
SUPABASE_DB_HOST=COMPLETAR
SUPABASE_DB_PORT=COMPLETAR
SUPABASE_DB_USER=COMPLETAR
SUPABASE_DB_PASSWORD=COMPLETAR
EOF

# Commitear estructura inicial
git add .gitignore credentials.env.example
git commit -m "chore: structure inicial del proyecto SGCD"
```

---

## Paso 2: Configurar DNS en AWS Route 53

Usa **AWS CLI** (ya debe estar configurado localmente con credentials) para crear el registro DNS que apunte n8n a la IP de la VM.

### 2.1 Obtener el Hosted Zone ID

Primero, lista los hosted zones para encontrar el de tu dominio:

```bash
aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='letiende.co.'].Id" \
  --output text
```

Reemplaza `letiende.co` por el dominio de tu cliente. Si el resultado está vacío, el hosted zone no existe aún.

Guarda el ID en tu `credentials.env` como `AWS_ROUTE53_HOSTED_ZONE_ID`.

### 2.2 Crear el registro A para n8n.{dominio}

```bash
source credentials.env

aws route53 change-resource-record-sets \
  --hosted-zone-id "$AWS_ROUTE53_HOSTED_ZONE_ID" \
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

Reemplaza `n8n.letiende.co` con el subdominio que uses para tu cliente.

### 2.3 Verificar propagación DNS

La propagación puede tardar entre 30 segundos y 5 minutos:

```bash
# Verificar hasta que resuelva
while ! dig n8n.letiende.co +short | grep -q "$ORACLE_VM_IP"; do
  echo "Esperando propagación DNS..."
  sleep 10
done
echo "✓ DNS propagado: n8n.letiende.co apunta a $ORACLE_VM_IP"
```

---

## Paso 3: Provisionar VM en Oracle Cloud

### 3.1 Crear la VM

**Importante:** La VM `VM.Standard.A1.Flex` (ARM, Always Free, 4 OCPU, 24 GB) tiene disponibilidad limitada. Si no puedes crearla, usa `VM.Standard.E2.1.Micro` como alternativa temporal.

Pasos en Oracle Cloud Console:

1. **Compute** → **Instances** → **Create Instance**
2. **Image:** Ubuntu 22.04 (Canonical)
3. **Shape:** `VM.Standard.A1.Flex` (Always Free) o `E2.1.Micro`
   - Si es A1.Flex: asignar 4 OCPU, 24 GB RAM
   - Si es E2.1.Micro: asignar el máximo disponible
4. **VCN:** Crear nuevo (se llamará automáticamente)
5. **Subnet:** Crear nueva (public, permite IP pública)
6. **SSH key:** Usar la pública correspondiente a `~/.ssh/id_ed25519_github` (o tu clave SSH)
7. **Assign public IP:** ✓ Activado

Una vez creada, la consola mostrará la **IP pública**. Guárdala como `ORACLE_VM_IP` en `credentials.env`.

### 3.2 Configurar VCN, Internet Gateway y rutas (si es necesario)

**Si la VM tiene IP privada pero no acceso a Internet:**

```bash
# 1. Obtener IDs del VCN e IGW desde Oracle Cloud Console
OCI_VCN_ID="ocid1.vcn.oc1.iad.amaaaaaarxpvyyqaibm2qsdomaiyshurtpmvfc64k74mbxfsjjjfmfsmekha"
OCI_IGW_ID="ocid1.internetgateway.oc1.iad.aaaaaaaaqbwiypl6qxheamdpc2wftwavdjajl7e5dqaak6howmg4374kj3ma"
OCI_ROUTE_TABLE_ID="ocid1.routetable.oc1.iad.aaaaaaaa35fw55cafmkdedlr5cqfdjvwu6s4ogfwqxp5eemgynfiwvuaawuq"
OCI_REGION="us-ashburn-1"

# 2. Crear ruta 0.0.0.0/0 → Internet Gateway
oci network route-table update \
  --rt-id "$OCI_ROUTE_TABLE_ID" \
  --region "$OCI_REGION" \
  --route-rules '[
    {
      "destinationCIDRBlock": "0.0.0.0/0",
      "networkEntityId": "'"$OCI_IGW_ID"'"
    }
  ]'

# 3. Permitir puertos 80/443 en el Security List
# Ir a Oracle Cloud Console → VCN → Security Lists → editar la que está asociada a tu subnet
```

### 3.3 Conectarse a la VM

```bash
source credentials.env
ssh -i "$ORACLE_SSH_KEY_PATH" ubuntu@"$ORACLE_VM_IP"
```

Si no puedes conectar con ed25519, intenta con RSA:

```bash
ssh -i ~/.ssh/id_rsa ubuntu@$ORACLE_VM_IP
```

---

## Paso 4: Setup de la VM (Docker, Certbot, Nginx)

Una vez dentro de la VM (después del `ssh`), ejecuta esto en orden:

```bash
# 1. Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Docker y Docker Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Verificar Docker
docker --version
docker compose --version

# 4. Instalar Nginx y Certbot para SSL
sudo apt install -y nginx certbot python3-certbot-nginx

# 5. Detener Nginx (conflictúa con Docker)
# El Nginx de Docker Compose manejará los puertos 80/443
sudo systemctl stop nginx
sudo systemctl disable nginx

# 6. Crear estructura de directorios
mkdir -p ~/letiende-sgcd/infrastructure

# 7. Salir de la VM (volvemos a la máquina local)
exit
```

---

## Paso 5: Subir archivos de configuración a la VM

Desde tu máquina local, copia los archivos de infraestructura a la VM:

```bash
source credentials.env

# Copiar docker-compose.yml y nginx.conf
scp -i "$ORACLE_SSH_KEY_PATH" \
  infrastructure/docker-compose.yml \
  infrastructure/nginx.conf \
  ubuntu@"$ORACLE_VM_IP":~/letiende-sgcd/infrastructure/

# Crear un archivo .env temporal en la VM con todas las credenciales
# (No lo commitees al repo, solo existirá en la VM)
```

Conectarse de nuevo a la VM:

```bash
ssh -i "$ORACLE_SSH_KEY_PATH" ubuntu@"$ORACLE_VM_IP"
```

Dentro de la VM, crear el archivo `.env`:

```bash
cd ~/letiende-sgcd/infrastructure

# Pegar cada línea manualmente o usar heredoc:
cat > .env << 'EOF'
POSTGRES_PASSWORD=<tu-postgres-password-aqui>
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<tu-n8n-password-aqui>
N8N_ENCRYPTION_KEY=<resultado-de-openssl-rand-hex-32>
TELEGRAM_BOT_TOKEN=<tu-token-telegram>
TELEGRAM_APPROVER_CHAT_ID=<tu-chat-id>
TELEGRAM_ADMIN_CHAT_ID=<tu-chat-id>
GEMINI_API_KEY=<completar-en-fase-2>
YOUTUBE_CLIENT_ID=<completar-en-fase-2>
YOUTUBE_CLIENT_SECRET=<completar-en-fase-2>
YOUTUBE_REFRESH_TOKEN=<completar-en-fase-2>
CLOUDINARY_CLOUD_NAME=<completar-en-fase-2>
CLOUDINARY_API_KEY=<completar-en-fase-2>
CLOUDINARY_API_SECRET=<completar-en-fase-2>
CF_ACCOUNT_ID=<tu-cf-account-id>
CF_R2_ACCESS_KEY_ID=<tu-cf-r2-access-key>
CF_R2_SECRET_ACCESS_KEY=<tu-cf-r2-secret>
CF_R2_ENDPOINT=https://<tu-account-id>.r2.cloudflarestorage.com
CANVA_API_KEY=<completar-en-fase-2>
CANVA_BRAND_TEMPLATE_IDS=<completar-en-fase-2>
SUPABASE_URL=<tu-supabase-url>
SUPABASE_ANON_KEY=<tu-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<tu-service-role-key>
INSTAGRAM_APP_ID=<completar-en-fase-2>
INSTAGRAM_APP_SECRET=<completar-en-fase-2>
INSTAGRAM_ACCESS_TOKEN=<completar-en-fase-2>
INSTAGRAM_USER_ID=<completar-en-fase-2>
TIKTOK_API_APPROVED=false
TIKTOK_CLIENT_KEY=<completar-en-fase-2>
TIKTOK_CLIENT_SECRET=<completar-en-fase-2>
TIKTOK_ACCESS_TOKEN=<completar-en-fase-2>
EOF

# Proteger el archivo (solo lectura)
chmod 600 .env
```

---

## Paso 6: Emitir certificado SSL con Certbot

**Asegúrate de que el DNS está propagado antes de esto** (ver Paso 2.3).

Dentro de la VM:

```bash
source ~/letiende-sgcd/infrastructure/.env

# Generar certificado SSL
sudo certbot certonly --standalone \
  -d n8n.letiende.co \
  --non-interactive \
  --agree-tos \
  -m "$ADMIN_EMAIL"
```

Reemplaza `n8n.letiende.co` y `$ADMIN_EMAIL` según corresponda.

**Resultado esperado:** El certificado se guardará en `/etc/letsencrypt/live/n8n.letiende.co/`.

---

## Paso 7: Iniciar Docker stack

Dentro de la VM:

```bash
cd ~/letiende-sgcd/infrastructure

# Iniciar los servicios (postgres, n8n, nginx)
docker compose up -d

# Verificar que están corriendo
docker compose ps
```

Verifica el estado de cada contenedor. Todos deben estar en `Up`:

```
NAME              STATUS
postgres          Up 2 minutes
n8n               Up 1 minute
nginx             Up 30 seconds
```

### Troubleshooting Docker

| Error | Solución |
|-------|----------|
| `docker: command not found` | Reinicia la terminal o ejecuta `newgrp docker` |
| `Bind for 0.0.0.0:80 failed` | El puerto 80 está en uso; detener nginx con `sudo systemctl stop nginx` |
| `Connection refused` (n8n no responde) | Esperar 30 segundos, el contenedor está iniciando PostgreSQL |
| `env-file: no such file or directory` | Asegurar que el archivo `.env` existe en `infrastructure/` |

---

## Paso 8: Verificar n8n y SSL

Desde tu máquina local:

```bash
# Verificar que HTTPS responde (esperar a que Nginx esté listo, ~30 segundos)
curl -I https://n8n.letiende.co/

# Resultado esperado: HTTP/2 200 o 401 (sin certificado inválido)
```

Abre en el navegador: `https://n8n.letiende.co`

Deberías ver la pantalla de login de n8n. Usa el usuario y contraseña de `N8N_BASIC_AUTH_USER` y `N8N_BASIC_AUTH_PASSWORD`.

---

## Paso 9: Configurar Cloudflare R2

### 9.1 Crear token de R2 en Cloudflare

1. Ir a Cloudflare Dashboard
2. **R2** → **Manage R2 API Tokens** (en el lateral derecho)
3. **Create API Token**
4. Nombre: `letiende-sgcd-admin`
5. Permisos: **Admin (All permissions)**
6. Copiar `Access Key ID` y `Secret Access Key`

Guardar en `credentials.env`:

```bash
CF_ACCOUNT_ID=424b011991022bd9f953ebc622e59f4f
CF_R2_ACCESS_KEY_ID=a8af46d9cbd06f8ff70b6ef6e2cfd421
CF_R2_SECRET_ACCESS_KEY=ce1ed6b8ce6d71d250170f82019aa2fdea2d671cb101c5d967e946f1f76662fa
CF_R2_ENDPOINT=https://424b011991022bd9f953ebc622e59f4f.r2.cloudflarestorage.com
```

### 9.2 Ejecutar script de setup de R2

Desde tu máquina local (donde está `setup-r2.sh`):

```bash
source credentials.env
bash scripts/setup-r2.sh
```

**Resultado esperado:**

```
=== Configurando Cloudflare R2 para Le Tiende SGCD ===
--- Creando bucket: letiende-raw-assets ---
✓ Bucket letiende-raw-assets creado
--- Creando bucket: letiende-processed-assets ---
✓ Bucket letiende-processed-assets creado
--- Creando bucket: letiende-templates-backup ---
✓ Bucket letiende-templates-backup creado
--- Configurando lifecycle en letiende-raw-assets (30 días) ---
✓ Lifecycle configurado: raw-assets expiran en 30 días
--- Configurando lifecycle en letiende-processed-assets (90 días) ---
✓ Lifecycle configurado: processed-assets expiran en 90 días
--- Verificando acceso con objeto de prueba ---
✓ Objeto de prueba subido
✓ Objeto de prueba eliminado
=== ✅ Cloudflare R2 configurado correctamente ===
```

---

## Paso 10: Configurar Supabase

### 10.1 Crear proyecto en Supabase

1. Ir a https://supabase.com
2. **New Project**
3. **Database Password:** Genera una segura (min 12 caracteres, incluir mayúsculas, números, símbolos)
4. **Region:** Elige la más cercana geográficamente
5. Confirmar creación (tarda ~5 minutos)

Una vez creado, ir a **Project Settings** → **API**:

- Copiar `Project URL` → `SUPABASE_URL`
- Copiar `Service Role Secret` → `SUPABASE_SERVICE_ROLE_KEY`
- Copiar `Anon Public` → `SUPABASE_ANON_KEY`

Guardar en `credentials.env`.

### 10.2 Obtener conexión a la base de datos

En Supabase, ir a **Database** → **Connection Pooler**:

- Modo: **Session** (predeterminado)
- Copiar la connection string y extraer:
  - `Host` → `SUPABASE_DB_HOST`
  - `Port` → `SUPABASE_DB_PORT`
  - `User` → `SUPABASE_DB_USER`
  - `Password` → `SUPABASE_DB_PASSWORD` (URL-encoded)

**Nota importante sobre caracteres especiales en contraseñas:**

Si tu contraseña contiene caracteres como `&`, `$`, `!`, debes URL-encodearlos:

- `&` → `%26`
- `$` → `%24`
- `!` → `%21`

Ejemplo: `Y8&nTiRbB6HZt$!q` → `Y8%26nTiRbB6HZt%24%21q`

### 10.3 Aplicar schema

Desde tu máquina local (donde tienes `setup-supabase.sh`):

```bash
source credentials.env
bash scripts/setup-supabase.sh
```

El script intenta usar `psql` si está disponible. Si no lo tienes, instala PostgreSQL:

```bash
# macOS
brew install postgresql

# Ubuntu
sudo apt install postgresql-client
```

Luego ejecuta el script de nuevo.

**Resultado esperado:**

```
=== Aplicando schema de Supabase para Le Tiende SGCD ===
Usando psql para aplicar el schema...
✓ Schema aplicado via psql

--- Verificando tablas creadas ---
✓ Tabla content_items accesible

=== ✅ Schema de Supabase aplicado ===

Tablas creadas:
  - content_items
  - publish_log
  - metrics
  - quota_tracker (con datos iniciales)
  - error_log
```

---

## Paso 11: Verificación final de Fase 1

Ejecuta este checklist para confirmar que todo está funcionando:

### 11.1 Verificar n8n

```bash
curl -I https://n8n.letiende.co/healthz
# Resultado esperado: HTTP/2 200
```

Accede a `https://n8n.letiende.co` con el navegador y confirma que puedes loguear.

### 11.2 Verificar R2 buckets

```bash
aws s3 ls --endpoint-url "$CF_R2_ENDPOINT"
# Resultado esperado:
# 2024-03-20 10:30:00     letiende-raw-assets
# 2024-03-20 10:30:00     letiende-processed-assets
# 2024-03-20 10:30:00     letiende-templates-backup
```

### 11.3 Verificar Supabase

```bash
curl -s "$SUPABASE_URL/rest/v1/content_items?limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY" | head -c 100
# Resultado esperado: [] o error 401 (que significa que está activo)
```

Accede a `$SUPABASE_URL` y verifica que puedes ver la tabla `content_items` en SQL Editor.

### 11.4 Verificar SSL

```bash
openssl s_client -connect n8n.letiende.co:443 -servername n8n.letiende.co < /dev/null | grep -A2 "Certificate"
# Resultado esperado: Subject emitido por Let's Encrypt
```

### 11.5 Checklist final

- [ ] `curl https://n8n.letiende.co/healthz` responde con `{"status":"ok"}`
- [ ] Puedo loguear en n8n con usuario/contraseña
- [ ] Los 3 buckets de R2 existen: `letiende-raw-assets`, `letiende-processed-assets`, `letiende-templates-backup`
- [ ] Supabase responde a queries (tabla `content_items` accesible)
- [ ] El certificado SSL es válido (sin advertencias de navegador)
- [ ] `docker compose ps` en la VM muestra todos los contenedores en `Up`

Si todos los puntos están ✓, **la Fase 1 está completa**.

---

## Troubleshooting

### DNS no propaga

**Síntoma:** `dig n8n.letiende.co +short` devuelve vacío o IP incorrecta

**Solución:**

1. Verificar que el registro fue creado:
   ```bash
   aws route53 list-resource-record-sets \
     --hosted-zone-id "$AWS_ROUTE53_HOSTED_ZONE_ID" \
     --query "ResourceRecordSets[?Name=='n8n.letiende.co.']"
   ```

2. Si no existe, crear nuevamente con el comando del Paso 2.2

3. Esperar 5 minutos y reintentar

4. Si sigue sin funcionar, verificar que `$ORACLE_VM_IP` es la IP pública correcta

### n8n no responde (timeout o 502)

**Síntoma:** `curl https://n8n.letiende.co/` cuelga o devuelve error 502

**Solución:**

1. Dentro de la VM, verificar estado de contenedores:
   ```bash
   docker compose ps
   docker compose logs n8n | tail -50
   ```

2. Si n8n dice `waiting for postgres`, significa que PostgreSQL está lento. Esperar 1-2 minutos.

3. Si el contenedor está crashed:
   ```bash
   docker compose restart n8n
   ```

4. Verificar que las variables de entorno están correctas en `.env`:
   ```bash
   cat ~/letiende-sgcd/infrastructure/.env | grep N8N
   ```

### Certificado SSL inválido

**Síntoma:** Navegador muestra "Esta conexión no es segura" o error HSTS

**Solución:**

1. Verificar que el DNS está propagado (Paso 2.3)

2. Dentro de la VM, forzar renovación del certificado:
   ```bash
   sudo certbot renew --force-renewal -d n8n.letiende.co
   ```

3. Recargar Nginx:
   ```bash
   docker compose exec nginx nginx -s reload
   ```

### R2 bucket creation falla

**Síntoma:** `setup-r2.sh` devuelve `error: An error occurred (InvalidAccessKeyId.NotFound)`

**Solución:**

1. Verificar que el token de R2 es válido y tiene permisos `Admin`

2. Verificar que `CF_R2_ENDPOINT` es correcta (debe ser `https://{account-id}.r2.cloudflarestorage.com`)

3. Intentar crear manualmente desde Cloudflare Console:
   - Ir a **R2** → **Create Bucket**
   - Nombre: `letiende-raw-assets`
   - Confirmar

4. Reintenta el script

### Supabase: psql connection refused

**Síntoma:** `psql: error: could not translate host name "aws-0-us-east-1.pooler.supabase.com" to address`

**Solución:**

1. Verificar que `SUPABASE_DB_HOST` es correcto (no todos los proyectos usan `aws-0`, algunos usan `aws-1`)

2. Probar la conexión manualmente:
   ```bash
   psql -h "$SUPABASE_DB_HOST" -U "$SUPABASE_DB_USER" -d postgres -c "SELECT 1"
   ```

3. Si pide contraseña, ingresar `SUPABASE_DB_PASSWORD`

4. Si sigue fallando, ir a Supabase Console → **Database** → **Connection Pooler** y copiar la URL exacta

### Supabase: password not matching

**Síntoma:** `psql: error: FATAL: password authentication failed for user "postgres.xyz"`

**Solución:**

1. La contraseña en la connection string está URL-encoded. Decodificar caracteres especiales en tu editor de texto.

2. Ir a Supabase → **Database** → **Database Password** → **Reset Password**

3. Guardar la nueva contraseña y repetir la conexión

### Docker: port 80/443 already in use

**Síntoma:** `docker compose up -d` falla con "Bind for 0.0.0.0:80 failed: port is already allocated"

**Solución:**

1. Dentro de la VM, detener el Nginx del sistema:
   ```bash
   sudo systemctl stop nginx
   sudo systemctl disable nginx
   ```

2. Matar procesos en puerto 80/443:
   ```bash
   sudo lsof -i :80 | grep -v PID | awk '{print $2}' | xargs kill -9
   sudo lsof -i :443 | grep -v PID | awk '{print $2}' | xargs kill -9
   ```

3. Reintentar `docker compose up -d`

---

## Próximos pasos — Fase 2

Una vez que la Fase 1 esté verificada, pasas a la Fase 2, que incluye:

1. **Lambda Function** — Procesador de videos con FFmpeg
2. **Workflow 1 (Ingesta)** — Recibir activos vía Telegram
3. **Workflow 2 (Generación)** — IA genera captions y hashtags con Gemini

Antes de Fase 2, necesitas completar credenciales adicionales:

- `GEMINI_API_KEY` (Google Cloud)
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`

Ver documento separado de Fase 2 para las instrucciones.

---

## Notas de mantenimiento

### Renovación automática de certificados SSL

Certbot renueva automáticamente cada 60 días. Para verificar que está activo:

```bash
# En la VM
sudo systemctl status certbot.timer
```

Si necesita renovación manual:

```bash
sudo certbot renew --dry-run
```

### Backup de datos n8n

Los datos de n8n (workflows, credenciales) se guardan en PostgreSQL. Para hacer backup:

```bash
# En la VM
docker compose exec postgres pg_dump -U n8n n8n > backup-n8n-$(date +%Y%m%d).sql
```

### Limpieza de espacios en R2

R2 cobra por almacenamiento. Para ver cuánto espacio usas:

```bash
aws s3 ls s3://letiende-raw-assets/ --recursive --summarize --endpoint-url "$CF_R2_ENDPOINT"
```

---

## Contacto y soporte

Si encuentras errores no documentados aquí, crea un issue en el repositorio con:

- El error exacto (salida de comando)
- Los pasos que realizaste
- Tu entorno (SO, versión AWS CLI, etc.)

---

**Última actualización:** Marzo 20, 2026
**Autores:** Le Tiende.co Infrastructure Team
