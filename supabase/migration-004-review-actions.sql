-- Migration 004: registro de quién hizo qué en la revisión (T-0035, plan-actualizacion §4 Fase 4)
-- Una fila por cada botón pulsado o respuesta de edición, también las que se ignoraron por estado viejo.
-- La escribe WF31 con la service_role key (que ignora RLS); anon y authenticated no tienen acceso.
-- Aplicar con la herramienta apply_migration (nombre: review_actions).

create table public.review_actions (
  id                bigint generated always as identity primary key,
  content_item_id   uuid not null references public.content_items (id) on delete cascade,
  -- approve, discard, regenerate, edit (botón que pide el texto) y editreply (el texto nuevo)
  action            text not null check (action in ('approve', 'discard', 'regenerate', 'edit', 'editreply')),
  -- applied = cambió algo (o pidió el texto, en edit); ignored = estado viejo o acción sin efecto
  outcome           text not null check (outcome in ('applied', 'ignored')),
  -- Telegram: from.id (entero de hasta 52 bits) y nombre para mostrar
  actor_telegram_id bigint,
  actor_name        text check (char_length(actor_name) <= 200),
  -- editreply: el texto nuevo; ignored: el motivo
  detail            text check (char_length(detail) <= 2000),
  created_at        timestamptz not null default now()
);

comment on table public.review_actions is
  'Un botón o una respuesta de edición del aprobador por fila. Base de las vistas review_*.';

create index review_actions_item_idx on public.review_actions (content_item_id, created_at);
create index review_actions_created_idx on public.review_actions (created_at desc);

-- Seguridad: RLS sin políticas = denegado para anon/authenticated; service_role la ignora.
alter table public.review_actions enable row level security;
revoke all on table public.review_actions from anon, authenticated;
revoke all on sequence public.review_actions_id_seq from anon, authenticated;

-- Indicadores por pieza. Solo cuentan las acciones aplicadas.
-- «Sin edición» = aprobada y sin ninguna respuesta de edición aplicada.
create view public.review_item_stats with (security_invoker = true) as
select
  content_item_id,
  count(*) filter (where action = 'editreply'  and outcome = 'applied')  as edits,
  count(*) filter (where action = 'regenerate' and outcome = 'applied')  as regenerations,
  count(*) filter (where action = 'approve'    and outcome = 'applied') > 0 as approved,
  count(*) filter (where action = 'discard'    and outcome = 'applied') > 0 as discarded,
  count(*) filter (where outcome = 'ignored')                            as ignored,
  count(*) filter (where action = 'approve'    and outcome = 'applied') > 0
    and count(*) filter (where action = 'editreply' and outcome = 'applied') = 0 as approved_without_edit,
  min(created_at)                                                        as first_action_at,
  max(created_at)                                                        as last_action_at
from public.review_actions
group by content_item_id;

-- Resumen de la fase: piezas con decisión, % aprobado sin edición y promedios de ediciones y regeneraciones.
create view public.review_summary with (security_invoker = true) as
select
  count(*)                                                     as pieces_reviewed,
  count(*) filter (where approved)                             as approved,
  count(*) filter (where discarded)                            as discarded,
  count(*) filter (where approved_without_edit)                as approved_without_edit,
  round(count(*) filter (where approved_without_edit)::numeric
    / nullif(count(*) filter (where approved), 0), 4)          as approved_without_edit_rate,
  round(avg(edits), 2)                                         as edits_per_piece,
  round(avg(regenerations), 2)                                 as regenerations_per_piece
from public.review_item_stats;

revoke all on public.review_item_stats, public.review_summary from anon, authenticated;
