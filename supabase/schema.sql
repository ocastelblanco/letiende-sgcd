-- supabase/schema.sql
-- Schema de negocio para SGCD Le Tiende.co

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
