# especificaciones-tecnicas.md — Especificación técnica SGCD Le Tiende.co

## 1. Arquitectura general

```
Telegram Bot (entrada humana)
       │
       ▼
   n8n (Oracle Cloud VM — n8n.letiende.co)
   ├── Workflow 1: Ingesta
   ├── Workflow 2: Generación IA
   ├── Workflow 3: Revisión HITL
   ├── Workflow 4: Publicación
   └── Workflow 5: Métricas
       │
       ├── Cloudinary (imágenes) ←→ Instagram Graph API
       ├── Cloudflare R2 (videos) ←→ YouTube Data API v3
       ├── Canva Connect API (plantillas)    ←→ TikTok API
       ├── Gemini Flash API (texto)
       ├── Gemini Imagen 3 API (imágenes IA)
       ├── AWS Lambda + FFmpeg (procesamiento video)
       └── Supabase (base de datos)
```

---

## 2. Infraestructura

### 2.1 docker-compose.yml (Oracle Cloud VM)

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_DB: n8n
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - internal

  n8n:
    image: n8nio/n8n:latest
    restart: always
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=n8n.letiende.co
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.letiende.co
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=336
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - postgres
    networks:
      - internal
      - external

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
    depends_on:
      - n8n
    networks:
      - external

volumes:
  postgres_data:
  n8n_data:

networks:
  internal:
    driver: bridge
  external:
    driver: bridge
```

### 2.2 nginx.conf

```nginx
events { worker_connections 1024; }

http {
  upstream n8n {
    server n8n:5678;
  }

  server {
    listen 80;
    server_name n8n.letiende.co;
    return 301 https://$host$request_uri;
  }

  server {
    listen 443 ssl http2;
    server_name n8n.letiende.co;

    ssl_certificate     /etc/letsencrypt/live/n8n.letiende.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.letiende.co/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 200M;

    location / {
      proxy_pass http://n8n;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_read_timeout 300s;
      proxy_connect_timeout 75s;
    }
  }
}
```

---

## 3. Schema de base de datos (Supabase)

```sql
-- supabase/schema.sql

-- Tabla principal de contenidos
CREATE TABLE content_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Activo original
  asset_type      TEXT NOT NULL CHECK (asset_type IN ('image', 'video', 'ai_image', 'ai_carousel')),
  raw_asset_url   TEXT,           -- URL en Cloudinary (imágenes) o R2 (videos)
  processed_urls  JSONB,          -- { instagram: "...", youtube: "...", tiktok: "..." }

  -- Contenido generado por IA
  caption_instagram  TEXT,
  hashtags_instagram TEXT[],
  caption_youtube    TEXT,
  title_youtube      TEXT,
  tags_youtube       TEXT[],
  caption_tiktok     TEXT,
  hashtags_tiktok    TEXT[],

  -- Metadatos Canva
  canva_template_id  TEXT,
  canva_design_id    TEXT,

  -- Programación
  scheduled_at    TIMESTAMPTZ,
  suggested_at    TIMESTAMPTZ,    -- horario sugerido por la IA

  -- Estado
  status          TEXT NOT NULL DEFAULT 'ingested'
                  CHECK (status IN (
                    'ingested',
                    'processing',
                    'ready_for_review',
                    'approved',
                    'stalled',
                    'discarded',
                    'publishing',
                    'published',
                    'error'
                  )),

  -- Publicación
  published_at    TIMESTAMPTZ,
  instagram_post_id TEXT,
  youtube_video_id  TEXT,
  tiktok_post_id    TEXT,

  -- Auditoría
  approved_by     TEXT,
  notes           TEXT           -- notas del aprobador
);

-- Registro de publicaciones (log detallado por plataforma)
CREATE TABLE publish_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_item_id UUID REFERENCES content_items(id),
  platform        TEXT NOT NULL CHECK (platform IN ('instagram', 'youtube', 'tiktok')),
  attempted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  success         BOOLEAN NOT NULL,
  response_code   INTEGER,
  response_body   TEXT,
  error_message   TEXT
);

-- Métricas de rendimiento
CREATE TABLE metrics (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_item_id UUID REFERENCES content_items(id),
  platform        TEXT NOT NULL,
  recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  likes           INTEGER DEFAULT 0,
  comments        INTEGER DEFAULT 0,
  shares          INTEGER DEFAULT 0,
  views           INTEGER DEFAULT 0,
  reach           INTEGER DEFAULT 0,
  impressions     INTEGER DEFAULT 0,
  saves           INTEGER DEFAULT 0,
  raw_data        JSONB
);

-- Seguimiento de cuotas de API
CREATE TABLE quota_tracker (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service         TEXT NOT NULL,  -- 'youtube', 'cloudinary', 'gemini'
  date            DATE NOT NULL DEFAULT CURRENT_DATE,
  units_used      INTEGER NOT NULL DEFAULT 0,
  units_limit     INTEGER NOT NULL,
  UNIQUE(service, date)
);

-- Insertar límites base
INSERT INTO quota_tracker (service, units_used, units_limit) VALUES
  ('youtube', 0, 10000),
  ('cloudinary', 0, 25),
  ('gemini_flash', 0, 1500),
  ('gemini_imagen', 0, 1000);

-- Log de errores del sistema
CREATE TABLE error_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  workflow        TEXT,
  content_item_id UUID REFERENCES content_items(id),
  error_type      TEXT,
  error_message   TEXT,
  stack_trace     TEXT,
  resolved        BOOLEAN DEFAULT false
);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER content_items_updated_at
  BEFORE UPDATE ON content_items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## 4. Especificación de workflows n8n

### 4.1 Workflow 1 — Ingesta de activos

**Trigger:** Telegram Message node, polling cada 1 segundo.
Solo procesa mensajes que contengan un archivo adjunto (`message.document` o `message.photo`).

**Lógica:**

```
[Telegram Trigger]
    │
    ├─ ¿Tiene archivo adjunto?
    │     NO → Responder: "Hola. Para ingresar un activo, envía una imagen o video."
    │
    ├─ Obtener info del archivo (getFile Telegram API)
    │
    ├─ Validar MIME type
    │     No es image/* ni video/* → Responder con error y lista de formatos válidos
    │
    ├─ Validar tamaño
    │     Imagen > 20 MB → Error con instrucción de comprimir
    │     Video > 200 MB → Error con instrucción de comprimir
    │
    ├─ Descargar archivo temporalmente
    │
    ├─ Router por tipo:
    │   ├─ image/* → Upload a Cloudinary carpeta `raw/`
    │   └─ video/* → Upload a Cloudflare R2 bucket `letiende-raw-assets`
    │
    ├─ Crear registro en Supabase `content_items`:
    │     { asset_type, raw_asset_url, status: 'ingested' }
    │
    ├─ Responder al usuario: "✅ Recibido. Procesando tu [imagen/video]..."
    │
    └─ Trigger Workflow 2 con { content_item_id }
```

**Manejo de errores:** Cualquier fallo → insertar en `error_log` + mensaje Telegram al usuario.

---

### 4.2 Workflow 2 — Generación con IA

**Trigger:** Webhook interno desde Workflow 1.
Input: `{ content_item_id: "uuid" }`

**Lógica:**

```
[Webhook Trigger]
    │
    ├─ Obtener content_item de Supabase
    ├─ Actualizar status: 'processing'
    │
    ├─ Llamar Gemini Flash para generar texto (ver prompts abajo)
    │   [delay 3s]
    │
    ├─ Router por asset_type:
    │   ├─ image / video:
    │   │   ├─ Cloudinary: generar URLs de variantes (sin nueva llamada de API)
    │   │   └─ Si tiene canva_template_id → Canva Autofill API
    │   │
    │   └─ ai_image / ai_carousel:
    │       └─ Gemini Imagen 3: generar imagen(es)
    │           [delay 3s]
    │           └─ Upload resultado a Cloudinary carpeta `ai-generated/`
    │
    ├─ Calcular horario sugerido (próximo lunes/miércoles/viernes a las 10am o 6pm)
    │
    ├─ Actualizar content_item en Supabase con todos los campos generados
    │   status: 'ready_for_review'
    │
    └─ Trigger Workflow 3 con { content_item_id }
```

#### Prompts de Gemini Flash

**System prompt (aplicar en todas las llamadas):**
```
Eres el redactor de contenidos digitales de Le Tiende.co, una marca colombiana de tendencias.
Escribe siempre en español colombiano. Tono: cercano, moderno, aspiracional pero auténtico.
Nunca uses frases genéricas como "¡No te lo pierdas!" o "Haz clic aquí".
Usa emojis con moderación (máximo 3 por texto).
```

**Prompt para generación de captions:**
```
Activo recibido: [imagen/video] de tipo [descripción breve del asset_type].

Genera el siguiente JSON (solo JSON, sin markdown, sin explicaciones):
{
  "caption_instagram": "texto para Instagram, máximo 2000 caracteres, incluir llamada a la acción natural",
  "hashtags_instagram": ["array", "de", "10", "a", "15", "hashtags", "sin", "el", "símbolo", "#"],
  "caption_tiktok": "texto para TikTok, máximo 150 caracteres, muy directo",
  "hashtags_tiktok": ["array", "de", "5", "a", "7", "hashtags"],
  "title_youtube": "título para YouTube, máximo 80 caracteres, incluir keyword principal al inicio",
  "caption_youtube": "descripción para YouTube: primer párrafo (150 chars) para el snippet de búsqueda, luego descripción completa, luego timestamps sugeridos si el video tiene más de 3 minutos",
  "tags_youtube": ["array", "de", "hasta", "15", "tags", "sin", "el", "símbolo", "#"],
  "suggested_time_note": "breve nota sobre el mejor horario para publicar este tipo de contenido"
}
```

**Prompt para resumen semanal (Workflow 5):**
```
A continuación están las métricas de las publicaciones de Le Tiende.co de los últimos 7 días:

[METRICS_JSON]

Redacta un resumen ejecutivo en español colombiano con:
1. Las 3 publicaciones con mejor rendimiento (explicar brevemente por qué funcionaron)
2. El tipo de contenido que tuvo mejor engagement en promedio
3. Una recomendación concreta para la semana siguiente
4. El alcance total combinado de todas las plataformas

Máximo 300 palabras. Tono directo, sin tecnicismos.
```

---

### 4.3 Workflow 3 — Revisión HITL

**Trigger:** Webhook interno desde Workflow 2.

**Formato del mensaje de Telegram al aprobador:**

```
📋 *Nuevo contenido para revisar*

📸 [miniatura del activo como foto adjunta]

*Instagram:*
[caption_instagram]
#hashtag1 #hashtag2 ...

*YouTube:*
🎬 [title_youtube]
[primeras 150 chars de caption_youtube]...

*TikTok:*
[caption_tiktok]

📅 Publicación sugerida: [suggested_at formateado]

[botones inline]
```

**Botones inline (callback_data):**
- `approve_{content_item_id}` → status: 'approved', trigger Workflow 4
- `edit_{content_item_id}` → solicitar texto nuevo por Telegram
- `regenerate_{content_item_id}` → trigger Workflow 2 nuevamente
- `discard_{content_item_id}` → status: 'discarded', confirmación

**Manejo del callback "Editar":**
1. Bot responde: "Escribe el caption para Instagram (o escribe /saltar para mantener el actual):"
2. Esperar respuesta del aprobador (nodo Telegram Trigger con filtro por chat_id)
3. Actualizar `caption_instagram` en Supabase con el texto recibido
4. Confirmar y proceder como si fuera aprobación

**Sistema de timeout:**
- Cron n8n cada 6 horas:
  ```sql
  SELECT id FROM content_items
  WHERE status = 'ready_for_review'
  AND updated_at < now() - interval '24 hours'
  ```
- 24h: reenviar vista previa con nota "⏰ Recordatorio: este contenido lleva 24h esperando aprobación"
- 48h: status → 'stalled', notificar al canal del equipo

---

### 4.4 Workflow 4 — Publicación

**Trigger:** Cron cada 15 minutos.

**Query Supabase:**
```sql
SELECT * FROM content_items
WHERE status = 'approved'
AND scheduled_at <= now()
AND published_at IS NULL
ORDER BY scheduled_at ASC
LIMIT 5
```

#### Instagram — publicación de imagen

```javascript
// 1. Crear media container
POST https://graph.facebook.com/v19.0/{ig_user_id}/media
{
  "image_url": "{cloudinary_url_procesado}",
  "caption": "{caption_instagram}\n\n{hashtags_formateados}",
  "access_token": "{INSTAGRAM_ACCESS_TOKEN}"
}
// → { id: "container_id" }

// 2. Publicar
POST https://graph.facebook.com/v19.0/{ig_user_id}/media_publish
{
  "creation_id": "{container_id}",
  "access_token": "{INSTAGRAM_ACCESS_TOKEN}"
}
// → { id: "post_id" }
```

**Nota Cloudinary:** La URL para Instagram debe ser pública. Usar el formato:
`https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/w_1080,h_1080,c_fill,f_jpg,q_auto/{public_id}`

#### Instagram — Reel (video)

```javascript
// 1. Crear container de video
POST https://graph.facebook.com/v19.0/{ig_user_id}/media
{
  "media_type": "REELS",
  "video_url": "{r2_public_url}",
  "caption": "{caption_instagram}\n\n{hashtags_formateados}",
  "access_token": "{INSTAGRAM_ACCESS_TOKEN}"
}
// Polling cada 5s hasta que container.status_code = 'FINISHED' (máx 5 minutos)

// 2. Publicar
POST https://graph.facebook.com/v19.0/{ig_user_id}/media_publish
{ "creation_id": "...", "access_token": "..." }
```

#### YouTube — subida de video

```javascript
// 1. Verificar cuota antes de intentar
// Si youtube_units_used + 1600 > 10000 → posponer y notificar

// 2. Iniciar upload resumable
POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
Authorization: Bearer {YOUTUBE_ACCESS_TOKEN}
{
  "snippet": {
    "title": "{title_youtube}",
    "description": "{caption_youtube}",
    "tags": ["{tags_youtube}"],
    "categoryId": "22"
  },
  "status": { "privacyStatus": "public" }
}
// → Location header con upload URL

// 3. Upload del archivo (desde R2)
PUT {upload_url}
Content-Type: video/*
[binary video data]
// → { id: "video_id" }

// 4. Subir miniatura
POST https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}
Authorization: Bearer {YOUTUBE_ACCESS_TOKEN}
[binary thumbnail data]

// 5. Actualizar quota_tracker
UPDATE quota_tracker SET units_used = units_used + 1650
WHERE service = 'youtube' AND date = CURRENT_DATE
```

#### TikTok — Plan A (API aprobada)

```javascript
POST https://open.tiktokapis.com/v2/post/publish/video/init/
Authorization: Bearer {TIKTOK_ACCESS_TOKEN}
{
  "post_info": {
    "title": "{caption_tiktok} {hashtags_formateados}",
    "privacy_level": "PUBLIC_TO_EVERYONE"
  },
  "source_info": {
    "source": "PULL_FROM_URL",
    "video_url": "{r2_public_url}"
  }
}
```

#### TikTok — Plan B (sin API)

```javascript
// Enviar por Telegram al aprobador:
// "📱 *TikTok — publicación manual*
//  El video está listo. Puedes descargarlo aquí: [r2_presigned_url]
//  Caption sugerido (copia y pega):
//  [caption_tiktok]
//  [hashtags_tiktok]"
```

---

### 4.5 Workflow 5 — Métricas

**Trigger:** Cron, domingos a las 23:00 UTC (18:00 Colombia).

**Instagram Insights (por publicación):**
```javascript
GET https://graph.facebook.com/v19.0/{post_id}/insights
  ?metric=impressions,reach,likes,comments,shares,saved
  &access_token={INSTAGRAM_ACCESS_TOKEN}
```

**YouTube Analytics (por video):**
```javascript
GET https://youtubeanalytics.googleapis.com/v2/reports
  ?ids=channel==MINE
  &metrics=views,likes,comments,estimatedMinutesWatched
  &dimensions=video
  &filters=video=={video_id}
  &startDate={7_days_ago}
  &endDate={today}
  Authorization: Bearer {YOUTUBE_ACCESS_TOKEN}
```

---

## 5. Lambda — Procesador de video

### 5.1 Contrato de entrada/salida

**Input (event de Lambda):**
```json
{
  "content_item_id": "uuid",
  "r2_key": "letiende-raw-assets/video_uuid.mp4",
  "operations": ["resize_9_16", "compress_youtube"],
  "target_bucket": "letiende-processed-assets"
}
```

**Output:**
```json
{
  "success": true,
  "outputs": {
    "instagram_reel": "letiende-processed-assets/uuid_reel.mp4",
    "youtube": "letiende-processed-assets/uuid_youtube.mp4",
    "tiktok": "letiende-processed-assets/uuid_tiktok.mp4"
  },
  "duration_seconds": 45,
  "error": null
}
```

### 5.2 Operaciones FFmpeg disponibles

```javascript
const OPERATIONS = {
  // Reel / TikTok: 9:16, 1080x1920, máx 60s, 50 MB
  resize_9_16: '-vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -t 60',

  // YouTube: 16:9, 1920x1080, máx 15min, sin recorte
  compress_youtube: '-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k',

  // Instagram Feed: 1:1, 1080x1080, máx 60s
  resize_1_1: '-vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -t 60',
};
```

### 5.3 Dockerfile de Lambda

```dockerfile
FROM public.ecr.aws/lambda/nodejs:20

# Instalar FFmpeg
RUN dnf install -y ffmpeg && dnf clean all

COPY package.json ./
RUN npm install --omit=dev

COPY index.js ./

CMD ["index.handler"]
```

---

## 6. Cloudinary — Convenciones de URL

Usar transformaciones de URL para no duplicar assets. Una sola imagen subida genera
todas las variantes necesarias cambiando la URL:

| Destino | Transformación | Ejemplo |
|---|---|---|
| Instagram feed cuadrado | `w_1080,h_1080,c_fill,f_jpg,q_auto` | `upload/w_1080,h_1080,c_fill,f_jpg,q_auto/{public_id}` |
| Instagram Story / Reel | `w_1080,h_1920,c_fill,f_jpg,q_auto` | `upload/w_1080,h_1920,c_fill,f_jpg,q_auto/{public_id}` |
| YouTube thumbnail | `w_1280,h_720,c_fill,f_jpg,q_90` | `upload/w_1280,h_720,c_fill,f_jpg,q_90/{public_id}` |
| Miniatura preview Telegram | `w_400,h_300,c_fill,f_jpg,q_70` | `upload/w_400,h_300,c_fill,f_jpg,q_70/{public_id}` |

Las transformaciones se cachean en Cloudinary — solo se generan una vez.

---

## 7. Convenciones del proyecto

### Nombres de workflows n8n
- Prefijo numérico: `01-ingesta`, `02-generacion`, etc.
- Siempre incluir nodo "Error Trigger" al inicio para captura global de errores

### Tablas Supabase
- Nombres en `snake_case` plural
- Siempre incluir `id UUID`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`
- Foreign keys con nombre `{tabla_referenciada_singular}_id`

### Keys en Cloudinary
- Imágenes crudas: `raw/{uuid}`
- Imágenes procesadas: `{platform}/{uuid}`
- Imágenes generadas por IA: `ai-generated/{uuid}`

### Keys en R2
- Videos crudos: `{bucket}/raw/{uuid}.{ext}`
- Videos procesados: `{bucket}/processed/{uuid}/{platform}.{ext}`

### Logs de error
Todo error no recuperable debe:
1. Insertar en `error_log` de Supabase
2. Enviar mensaje a Telegram al canal `$TELEGRAM_ADMIN_CHAT_ID`
3. Actualizar `content_items.status = 'error'` si aplica

### Variables de entorno requeridas por n8n en Docker
Inyectar en `docker-compose.yml` bajo `n8n.environment` — NO usar archivos `.env` montados.
