# tech-specs.md — Especificaciones Técnicas SGCD Le Tiende

> Ver PRD §2 para el contexto de negocio. Este documento es la referencia técnica para retomar el proyecto sin contexto previo.

---

## 1. Diagrama de arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│  ENTRADA                                                          │
│  Telegram Bot (@le_tiende_contenidos_bot)                         │
│  Operador envía imagen o video                                    │
└─────────────────────────┬────────────────────────────────────────┘
                          │ webhook HTTPS
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  ORQUESTACIÓN — Oracle Cloud VM (150.136.139.189)                │
│  https://n8n.letiende.co                                          │
│                                                                   │
│  n8n v2.12.3  ←→  PostgreSQL 15  ←  Nginx (SSL Let's Encrypt)   │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────┐  ┌────────┐ │
│  │WF1       │──►│WF2           │──►│WF3           │─►│WF4     │ │
│  │Ingesta   │   │Generación IA │   │Revisión HITL │  │Publ.   │ │
│  └────┬─────┘   └──────┬───────┘   └──────┬───────┘  └───┬────┘ │
└───────┼────────────────┼──────────────────┼──────────────┼──────┘
        │                │                  │              │
        ▼                ▼                  ▼              ▼
   Cloudinary       Google Gemini      Telegram        Telegram
   (imágenes)       Flash 1.5          (aprobador)     (paquete
   Cloudflare R2    (captions)                          entrega)
   (videos)
        │
        ▼
   AWS Lambda
   + FFmpeg
   (procesamiento
    de video)
        │
   ┌────▼────────────────────────────────────────────┐
   │  SUPABASE (iljbfgbndwfaqacxthty.supabase.co)   │
   │  content_items  publish_log  metrics            │
   │  quota_tracker  error_log                       │
   └─────────────────────────────────────────────────┘

  [FUTURO]
   ├──► Instagram Graph API (publicación directa)
   ├──► YouTube Data API v3 (publicación directa)
   └──► TikTok Content Posting API (si se aprueba)
```

---

## 2. Stack tecnológico

| Tecnología | Versión | Propósito | Docs |
|---|---|---|---|
| n8n | 2.12.3+ | Motor de orquestación de workflows | https://docs.n8n.io |
| PostgreSQL | 15-alpine | Base de datos interna de n8n | https://www.postgresql.org/docs/15/ |
| Nginx | alpine | Reverse proxy con SSL (Let's Encrypt) | https://nginx.org/en/docs/ |
| Node.js (Lambda) | 20 | Runtime de la función AWS Lambda | https://nodejs.org/en/docs |
| Docker / Docker Compose | latest | Contenerización en Oracle VM | https://docs.docker.com |
| Supabase | Free tier | Base de datos de negocio (PostgreSQL managed) | https://supabase.com/docs |
| Cloudflare R2 | — | Almacenamiento de videos (API S3-compatible) | https://developers.cloudflare.com/r2/ |
| Cloudinary | Free (25 créditos/mes) | Almacenamiento y transformación de imágenes | https://cloudinary.com/documentation |
| AWS Lambda | — | Procesamiento de video con FFmpeg | https://docs.aws.amazon.com/lambda/ |
| Google Gemini Flash | 1.5 | Generación de captions y metadata | https://ai.google.dev/api |
| FFmpeg | Sistema | Transcodificación y resize de videos | https://ffmpeg.org/documentation.html |
| Let's Encrypt / Certbot | — | Certificado SSL gratuito para n8n.letiende.co | https://certbot.eff.org |

---

## 3. Estructura del repositorio

```
letiende-sgcd/
├── CLAUDE.md                      ← Instrucciones para agentes IA (este repo)
├── PRD.md                         ← Requisitos de producto (ver PRD §2–10)
├── tech-specs.md                  ← Este archivo
├── MEMORY.md                      ← Estado de sesiones + ADRs + gotchas
├── TODO.md                        ← Motor JIT (exactamente 2 tareas atómicas)
├── credentials.env                ← Secrets (en .gitignore, NUNCA commitear)
├── credentials.env.example        ← Plantilla sin valores (sí commitear)
│
├── infrastructure/
│   ├── docker-compose.yml         ← Stack: n8n + PostgreSQL + Nginx
│   ├── nginx.conf                 ← SSL TLSv1.2+, proxy a puerto 5678, max 200M upload
│   └── init-db.sql                ← Init de PostgreSQL (placeholder vacío)
│
├── supabase/
│   ├── schema.sql                 ← 5 tablas + trigger updated_at (aplicar en setup inicial)
│   ├── migration-001-ready-to-publish.sql ← Agrega estado ready_to_publish al CHECK
│   └── migrations/                ← Gestionado por Supabase CLI (en .gitignore)
│
├── lambda/
│   └── video-processor/
│       ├── index.js               ← Handler: descarga R2 → FFmpeg (paralelo) → sube R2
│       ├── package.json           ← @aws-sdk/client-s3, Node 20 ESM
│       ├── Dockerfile             ← public.ecr.aws/lambda/nodejs:20 + dnf install ffmpeg
│       └── tests/
│           └── index.test.js      ← Tests unitarios (Jest)
│
├── n8n-workflows/
│   ├── 01-ingesta.json            ← Telegram → validación → Cloudinary/R2 → Supabase
│   ├── 02-generacion.json         ← Gemini Flash → captions JSON → Supabase → trigger WF3
│   ├── 03-revision.json           ← Telegram inline buttons + cron timeouts
│   ├── 04-publicacion.json        ← Empaqueta y entrega por Telegram (manual hoy)
│   └── 05-metricas.json           ← [PENDIENTE] Cron domingos 23:00 UTC, reporte semanal
│
├── scripts/
│   ├── deploy-lambda.sh           ← Build Docker → ECR → crear/actualizar Lambda function
│   ├── setup-r2.sh                ← Crear 3 buckets R2 con lifecycle via boto3
│   ├── setup-supabase.sh          ← Aplicar schema.sql (psql o instrucción manual)
│   ├── import-workflows.sh        ← POST + PATCH active:true para cada workflow via n8n API
│   └── retry-a1-instance.sh       ← Reintento de VM Oracle A1 (shape ARM spot)
│
└── docs/
    ├── telegram-commands.md        ← Referencia para usuarios del bot
    ├── fase1-guia-replicable.md   ← Setup de infraestructura paso a paso desde cero
    ├── fase2-setup-n8n.md         ← Crear credenciales en n8n antes de importar workflows
    ├── especificaciones-tecnicas.md ← Spec técnica legacy (referencia de contexto histórico)
    └── credenciales.md            ← Guía de obtención de cada credencial
```

---

## 4. Infraestructura

### 4.1 Oracle Cloud VM

| Parámetro | Valor |
|---|---|
| IP pública | 150.136.139.189 |
| Dominio | n8n.letiende.co |
| Shape | VM.Standard.A1.Flex (ARM) o E2.1.Micro |
| OS | Ubuntu Server |
| Acceso SSH | `ssh -i $ORACLE_SSH_KEY_PATH ubuntu@$ORACLE_VM_IP` |
| Costo | $0 (Oracle Always Free Tier) |
| Path del proyecto en VM | `~/letiende-sgcd/infrastructure/` |

**Servicios Docker en VM:**

| Servicio | Imagen | Puerto | Red |
|---|---|---|---|
| postgres | postgres:15-alpine | Interno | internal |
| n8n | n8nio/n8n:latest | 5678 (interno) | internal + external |
| nginx | nginx:alpine | 80, 443 | external |

### 4.2 Nginx

- SSL con Let's Encrypt — certificado en `/etc/letsencrypt/live/n8n.letiende.co/`
- Protocolos: TLSv1.2, TLSv1.3 únicamente
- `client_max_body_size 200M` — para uploads de video
- WebSocket upgrade (`Upgrade`, `Connection: upgrade`) — requerido por el editor de n8n
- `proxy_read_timeout 300s` — para workflows de larga duración

### 4.3 Multi-entorno

| Entorno | URL | Descripción |
|---|---|---|
| Producción | https://n8n.letiende.co | VM Oracle Cloud, Docker stack |
| Desarrollo local | http://localhost:5678 | Docker local (misma imagen) |

---

## 5. Base de datos (Supabase)

**URL:** `https://iljbfgbndwfaqacxthty.supabase.co`

### 5.1 Tablas

| Tabla | Propósito |
|---|---|
| `content_items` | Registro central de cada activo — fuente de verdad del sistema |
| `publish_log` | Log detallado de cada intento de publicación por plataforma |
| `metrics` | Snapshots diarios de engagement por plataforma |
| `quota_tracker` | Uso diario de cuotas de APIs externas |
| `error_log` | Errores del sistema con stack trace y estado de resolución |

### 5.2 Máquina de estados de content_item

```
ingested ──► processing ──► ready_for_review
                                 │         │
                            ┌────┘         └────┐
                            ▼                   ▼
                          stalled           discarded
                            │
                         approved ──► publishing ──► ready_to_publish ──► published
                                             │
                                         [error] (cualquier estado puede transicionar a error)
```

**Nota sobre `ready_to_publish`:** Estado intermedio añadido en migration-001. Representa "paquete listo para publicar manualmente" antes de que exista integración directa con las APIs de RRSS. Cuando se implemente publicación directa, este estado quedará obsoleto.

### 5.3 Cuotas en quota_tracker

| Servicio | Límite | Costo por operación | Alerta al |
|---|---|---|---|
| youtube | 10,000 unidades/día | upload: 1,600 + thumbnail: 50 = 1,650 total | 80% = 8,000 unidades |
| cloudinary | 25 créditos/mes | Variable por transformación | 80% = 20 créditos |
| gemini_flash | 1,500 llamadas/día | 1 por generación de captions | 80% = 1,200 |
| gemini_imagen | 1,000 generaciones/día | 1 por imagen | 80% = 800 |

---

## 6. Endpoints internos de n8n

| Path | Workflow | Método | Caller | Descripción |
|---|---|---|---|---|
| `/webhook/[telegram-id]` | WF1 | POST | Telegram API | Recibe mensajes y archivos del bot |
| `/webhook/sgcd-generacion` | WF2 | POST | WF1 (HTTP node) | Dispara generación con `{ content_item_id }` |
| `/webhook/sgcd-revision` | WF3 | POST | WF2 (HTTP node) | Dispara revisión con `{ content_item_id }` |
| `/webhook/sgcd-publicacion` | WF4 | POST | WF3 (callback Telegram) | Dispara publicación con `{ content_item_id }` |
| `/api/v1/workflows` | — | GET/POST | Scripts locales | API de gestión de n8n |
| `/healthz` | — | GET | Monitoreo | Estado del servidor |

---

## 7. Servicios externos

| Servicio | Estado | Uso actual | Variables requeridas |
|---|---|---|---|
| Telegram Bot API | ✅ Activo | Ingesta + revisión + entrega de paquetes | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_APPROVER_CHAT_ID`, `TELEGRAM_ADMIN_CHAT_ID` |
| Google Gemini Flash 1.5 | ✅ Activo | Generación de captions (WF2) | `GEMINI_API_KEY` |
| Cloudinary | ✅ Activo | Storage + transformación de imágenes (cloud: `letiende`) | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| Cloudflare R2 | ✅ Activo | Storage de videos (3 buckets con lifecycle) | `CF_ACCOUNT_ID`, `CF_R2_ACCESS_KEY_ID`, `CF_R2_SECRET_ACCESS_KEY`, `CF_R2_ENDPOINT` |
| Supabase | ✅ Activo | Base de datos de negocio | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| AWS Lambda | ⚠️ Código listo, sin deploy | Procesamiento de video con FFmpeg | `AWS_REGION` (AWS CLI configurado localmente) |
| Instagram Graph API | ❌ Futuro | Publicación directa de imágenes y reels | `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` |
| YouTube Data API v3 | ❌ Futuro | Subida de videos y thumbnails | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` |
| TikTok Content Posting API | ⏳ Esperando aprobación | Publicación directa (Plan B: Telegram manual) | `TIKTOK_API_APPROVED=false`, `TIKTOK_ACCESS_TOKEN` |
| Canva Connect API | ⏳ Esperando acceso beta | Autofill de plantillas de marca | `CANVA_API_KEY`, `CANVA_BRAND_TEMPLATE_IDS` |
| Google Gemini Imagen 3 | ❌ Futuro | Generación de imágenes por IA | `GEMINI_API_KEY` (misma key) |
| AWS Route 53 | ✅ Configurado | DNS de letiende.co | AWS CLI local configurado |

---

## 8. AWS Lambda — Procesador de video

### 8.1 Contrato de entrada/salida

**Input (event de Lambda):**
```json
{
  "content_item_id": "uuid",
  "r2_key": "letiende-raw-assets/raw/uuid.mp4",
  "operations": ["resize_9_16", "compress_youtube"],
  "target_bucket": "letiende-processed-assets"
}
```

**Output:**
```json
{
  "success": true,
  "outputs": {
    "instagram_reel": "letiende-processed-assets/processed/uuid/instagram_reel.mp4",
    "youtube": "letiende-processed-assets/processed/uuid/youtube.mp4"
  },
  "duration_seconds": 45,
  "error": null
}
```

### 8.2 Operaciones FFmpeg disponibles

| Operación | Plataforma | Resolución | Duración máx | Codec |
|---|---|---|---|---|
| `resize_9_16` | Instagram Reel / TikTok | 1080×1920 | 60 seg | libx264 fast crf23, aac 128k |
| `compress_youtube` | YouTube | 1920×1080 | Sin límite | libx264 medium crf20, aac 192k |
| `resize_1_1` | Instagram Feed video | 1080×1080 | 60 seg | libx264 fast crf23, aac 128k |

### 8.3 Configuración de la función

| Parámetro | Valor |
|---|---|
| Nombre | `letiende-video-processor` |
| RAM | 512 MB |
| Timeout | 900 segundos (15 minutos) |
| Package type | Image (Docker en ECR) |
| Runtime base | `public.ecr.aws/lambda/nodejs:20` |
| Variables de entorno Lambda | `CF_R2_ENDPOINT`, `CF_R2_ACCESS_KEY_ID`, `CF_R2_SECRET_ACCESS_KEY`, `CF_R2_BUCKET_PROCESSED` |

**Para desplegar:**
```bash
source credentials.env
bash scripts/deploy-lambda.sh
```

---

## 9. Cloudflare R2 — Buckets

| Bucket | Uso | Lifecycle |
|---|---|---|
| `letiende-raw-assets` | Videos crudos enviados por Telegram | Eliminar después de 30 días |
| `letiende-processed-assets` | Videos procesados por Lambda (Reel, YouTube, TikTok) | Eliminar después de 90 días |
| `letiende-templates-backup` | Respaldo de plantillas de Canva | Sin expiración |

**Endpoint R2:** `https://424b011991022bd9f953ebc622e59f4f.r2.cloudflarestorage.com`

**Estructura de keys:**
- Crudos: `letiende-raw-assets/raw/{uuid}.{ext}`
- Procesados: `letiende-processed-assets/processed/{uuid}/{platform}.{ext}`

---

## 10. Cloudinary — Convenciones de URL

Un activo subido una vez genera todas las variantes por transformación de URL (sin subir múltiples veces):

| Destino | Transformación URL |
|---|---|
| Instagram feed (1:1) | `upload/w_1080,h_1080,c_fill,f_jpg,q_auto/{public_id}` |
| Instagram Story / Reel (9:16) | `upload/w_1080,h_1920,c_fill,f_jpg,q_auto/{public_id}` |
| YouTube thumbnail (16:9) | `upload/w_1280,h_720,c_fill,f_jpg,q_90/{public_id}` |
| Preview Telegram | `upload/w_400,h_300,c_fill,f_jpg,q_70/{public_id}` |

**Estructura de folders:**
- Imágenes crudas: `raw/{uuid}`
- Imágenes por plataforma: `{platform}/{uuid}` (ej: `instagram/{uuid}`)
- Imágenes generadas por IA: `ai-generated/{uuid}`

---

## 11. Credenciales en n8n

Las credenciales deben existir en la instancia n8n **antes** de importar los workflows. Los JSON de workflows referencian los IDs internos de las credenciales — si se migra la instancia, deben recrearse con los mismos nombres.

| Nombre de credencial | Tipo n8n | Campo | Valor |
|---|---|---|---|
| `Telegram Bot SGCD` | Telegram API | Access Token | `$TELEGRAM_BOT_TOKEN` |
| `Supabase SGCD` | Header Auth | Name: `apikey` / Value: key | `$SUPABASE_SERVICE_ROLE_KEY` |
| `Gemini SGCD` | Header Auth | Name: `x-goog-api-key` / Value: key | `$GEMINI_API_KEY` |
| `Cloudinary SGCD` | HTTP Basic Auth | User: api_key / Password: api_secret | `$CLOUDINARY_API_KEY` / `$CLOUDINARY_API_SECRET` |

**Para crear:** `https://n8n.letiende.co/home/credentials` → "Add credential" → hacer clic en el **título** para editar el nombre (no en la pestaña Details).

---

## 12. Gestión de secretos

| Variable | Propósito | Cómo se usa |
|---|---|---|
| `ORACLE_VM_IP` | IP pública VM (150.136.139.189) | Scripts locales de deploy |
| `ORACLE_SSH_KEY_PATH` | Ruta a llave SSH | Scripts locales de SSH/SCP |
| `AWS_ROUTE53_HOSTED_ZONE_ID` | Zona DNS de letiende.co | Scripts de setup de DNS |
| `N8N_BASIC_AUTH_USER/PASSWORD` | Acceso al panel n8n | Docker Compose en VM |
| `N8N_ENCRYPTION_KEY` | Cifrado de credenciales n8n | Docker Compose en VM |
| `N8N_API_KEY` | API programática de n8n | Scripts de import de workflows |
| `POSTGRES_PASSWORD` | Base de datos interna n8n | Docker Compose en VM |
| `TELEGRAM_BOT_TOKEN` | Autenticar el bot | Docker Compose + n8n |
| `TELEGRAM_APPROVER_CHAT_ID` | Chat del aprobador (-5249716260) | Docker Compose + n8n |
| `TELEGRAM_ADMIN_CHAT_ID` | Canal del equipo (-5249716260) | Docker Compose + n8n |
| `GEMINI_API_KEY` | Google AI Studio | Docker Compose + n8n |
| `SUPABASE_URL` | https://iljbfgbndwfaqacxthty.supabase.co | Docker Compose + scripts |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin de Supabase (bypass RLS) | Docker Compose + n8n |
| `CLOUDINARY_CLOUD_NAME` | `letiende` | Docker Compose + n8n |
| `CF_R2_ENDPOINT` | https://424b011991022bd9f953ebc622e59f4f.r2.cloudflarestorage.com | Docker Compose + n8n |
| `INSTAGRAM_ACCESS_TOKEN` | Publicar en Instagram (futuro) | Docker Compose (cuando se implemente) |
| `YOUTUBE_REFRESH_TOKEN` | Publicar en YouTube (futuro) | Docker Compose (cuando se implemente) |
| `TIKTOK_API_APPROVED` | Habilitar API TikTok | `false` por defecto |

**Regla:** Nunca hardcodear valores de `credentials.env` en el código. Siempre `process.env.NOMBRE_VARIABLE` en JS o `$NOMBRE_VARIABLE` en bash.

---

## 13. Convenciones de código

### JavaScript (Lambda + Code nodes n8n)
- ES2022: `async/await`, optional chaining (`?.`), nullish coalescing (`??`)
- Variables: `camelCase` en código, `SCREAMING_SNAKE_CASE` en env vars
- Comentarios en español; código en inglés
- Imports ESM (`import/export`), no CommonJS en Lambda

### SQL (Supabase)
- Nombres de tablas: `snake_case` plural
- Siempre incluir: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Foreign keys: `{tabla_singular}_id` (ej: `content_item_id`)

### n8n
- Nombres de workflows: prefijo numérico `01-ingesta`, `02-generacion`, etc.
- Todos los workflows incluyen un nodo **Error Trigger** para captura global de errores
- HTTP nodes: "Continue on Fail" **DESACTIVADO** (los errores deben detenerse, no silenciarse)
- Ante cualquier error: insertar en `error_log` + notificar `TELEGRAM_ADMIN_CHAT_ID` + actualizar `content_items.status = 'error'`
- Delays entre llamadas a Gemini: 3 segundos (nodo Wait)
- Reintentos: máximo 3, con backoff exponencial (1s, 2s, 4s)

---

## 14. Prompts de Gemini

### System prompt (todas las llamadas de WF2)
```
Eres el redactor de contenidos digitales de Le Tiende, un centro cultural colombiano que reúne librería, café, bar y teatro.
Escribe siempre en español colombiano. Tono: cercano, moderno, aspiracional pero auténtico.
Nunca uses frases genéricas como "¡No te lo pierdas!" o "Haz clic aquí".
Usa emojis con moderación (máximo 3 por texto).
```

### Prompt de generación (WF2)
Retorna JSON estricto (sin markdown) con: `caption_instagram`, `hashtags_instagram`, `caption_tiktok`, `hashtags_tiktok`, `title_youtube`, `caption_youtube`, `tags_youtube`, `suggested_time_note`.

Config de Gemini: `temperature: 0.7`, `maxOutputTokens: 2048`.

### Prompt de resumen semanal (WF5 — futuro)
Análisis de los últimos 7 días: top 3 publicaciones, tipo de contenido con mejor engagement, recomendación para la siguiente semana, alcance total combinado. Máximo 300 palabras, en español colombiano.

---

## 15. Roadmap técnico

| Feature | Archivos a crear/modificar | Dependencias |
|---|---|---|
| Deploy Lambda | Ejecutar `scripts/deploy-lambda.sh` | AWS CLI configurado, ECR disponible |
| Workflow 5 métricas | `n8n-workflows/05-metricas.json` | Workflows 1-4 activos, `quota_tracker` con datos |
| Publicación directa Instagram | `n8n-workflows/04-publicacion.json` | Instagram App en producción, access token de larga duración |
| Publicación directa YouTube | `n8n-workflows/04-publicacion.json` | YouTube OAuth con refresh token válido |
| Monitor de cuotas diario | Nuevo workflow en n8n (cron 09:00) | `quota_tracker` activo |
| Canva Autofill | `n8n-workflows/02-generacion.json` | Acceso beta Canva API |
| Carruseles Instagram | `n8n-workflows/04-publicacion.json` | Instagram Graph API v19+ |
