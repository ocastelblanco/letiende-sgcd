-- Migration 003: seguridad de las 5 tablas originales (T-0018, OWASP A01)
-- Corrige los avisos del asesor de Supabase: rls_disabled_in_public (ERROR),
-- function_search_path_mutable (WARN) y unindexed_foreign_keys (INFO).
-- n8n accede con la service_role key, que ignora RLS: no se pierde acceso.
-- Sin políticas a propósito: anon y authenticated quedan denegados.
-- Aplicar con la herramienta apply_migration (nombre: rls_tablas_existentes).

-- 1. RLS activado sin políticas
alter table public.content_items enable row level security;
alter table public.publish_log   enable row level security;
alter table public.metrics       enable row level security;
alter table public.quota_tracker enable row level security;
alter table public.error_log     enable row level security;

-- 2. Sin privilegios para los roles de la API pública (defensa en profundidad)
revoke all on table
  public.content_items,
  public.publish_log,
  public.metrics,
  public.quota_tracker,
  public.error_log
from anon, authenticated;

-- 3. search_path fijo: la función solo usa now(), que vive en pg_catalog
alter function public.update_updated_at() set search_path = '';

-- 4. Índices en las claves foráneas hacia content_items
create index if not exists error_log_content_item_id_idx   on public.error_log   (content_item_id);
create index if not exists metrics_content_item_id_idx     on public.metrics     (content_item_id);
create index if not exists publish_log_content_item_id_idx on public.publish_log (content_item_id);
