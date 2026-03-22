# Fase 2 — Setup de n8n antes de importar los workflows

Antes de ejecutar `import-workflows.sh`, configura estas 3 cosas en n8n.

---

## 1. Variables de entorno en n8n

**Ruta:** Settings → Environment Variables (menú lateral izquierdo en n8n)

Agrega estas variables una por una:

| Variable | Valor (de credentials.env) |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `8708970956:AAFvh-...` |
| `TELEGRAM_APPROVER_CHAT_ID` | `-5249716260` |
| `TELEGRAM_ADMIN_CHAT_ID` | `-5249716260` |
| `SUPABASE_URL` | `https://iljbfgbndwfaqacxthty.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_W4GKG874...` |
| `CF_R2_ENDPOINT` | `https://424b011991022bd9f953ebc622e59f4f.r2.cloudflarestorage.com` |
| `CF_R2_ACCESS_KEY_ID` | `a8af46d9cbd06f8ff70b6ef6e2cfd421` |
| `CF_R2_SECRET_ACCESS_KEY` | `ce1ed6b8ce6d71...` |
| `GEMINI_API_KEY` | `AIzaSyBbAJ3k3e9...` |
| `CLOUDINARY_CLOUD_NAME` | `letiende` |
| `CLOUDINARY_API_KEY` | `754879372588642` |
| `CLOUDINARY_API_SECRET` | `oYin7v60AHO1Fe-...` |

---

## 2. Credenciales en n8n

**Ruta:** Credentials → Add Credential (esquina superior derecha)

### 2.1 Telegram Bot SGCD

- Tipo: **Telegram API**
- Access Token: `{TELEGRAM_BOT_TOKEN}`

### 2.2 Supabase SGCD

- Tipo: **Header Auth**
- Name: `apikey`
- Value: `{SUPABASE_SERVICE_ROLE_KEY}`

### 2.3 Gemini SGCD

- Tipo: **Header Auth**
- Name: `x-goog-api-key`
- Value: `{GEMINI_API_KEY}`

### 2.4 Cloudinary SGCD

- Tipo: **HTTP Basic Auth**
- User: `{CLOUDINARY_API_KEY}`
- Password: `{CLOUDINARY_API_SECRET}`

> Los valores entre `{}` los encuentras en `credentials.env`.

---

## 3. Migración de Supabase

El Workflow 4 usa el estado `ready_to_publish`. Si ya aplicaste el schema original, ejecuta esta migración en el **SQL Editor de Supabase** (`https://iljbfgbndwfaqacxthty.supabase.co` → SQL Editor):

```sql
-- Archivo: supabase/migration-001-ready-to-publish.sql
ALTER TABLE content_items
  DROP CONSTRAINT IF EXISTS content_items_status_check;

ALTER TABLE content_items
  ADD CONSTRAINT content_items_status_check
  CHECK (status IN (
    'ingested', 'processing', 'ready_for_review', 'approved',
    'stalled', 'discarded', 'publishing', 'ready_to_publish',
    'published', 'error'
  ));
```

> Si el schema **nunca se aplicó**, ejecuta `supabase/schema.sql` completo (ya incluye `ready_to_publish`).

---

## 4. API Key de n8n

1. Ve a `https://n8n.letiende.co/settings/api`
2. Clic en **Create an API key**
3. Copia el valor y agrégalo a `credentials.env`:
   ```bash
   N8N_API_KEY=tu_api_key_aqui
   ```

---

## 5. Importar los workflows

```bash
cd /ruta/al/proyecto
source credentials.env
bash scripts/import-workflows.sh
```

Resultado esperado:
```
✓ 01-ingesta importado (ID: xxx) — ✓ activado
✓ 02-generacion importado (ID: xxx) — ✓ activado
✓ 03-revision importado (ID: xxx) — ✓ activado
✓ 04-publicacion importado (ID: xxx) — ✓ activado
```

---

## 6. Prueba de extremo a extremo

1. Abre Telegram y envía una foto al bot
2. Verifica en Supabase → Table Editor → `content_items` que aparece un registro con `status = 'ready_for_review'`
3. En el chat del aprobador llega el preview con los 4 botones
4. Presiona **✅ Aprobar**
5. Llega el paquete completo con captions por plataforma
6. Verifica en Supabase que `status = 'ready_to_publish'`
