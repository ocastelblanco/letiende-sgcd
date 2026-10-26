-- Migration 005: objeciones en la revisión (T-0039, plan-actualizacion §4 Fase 4)
-- Una objeción está abierta si la última acción aplicada entre objectreply y resolve de la pieza es objectreply.
-- Sin tabla nueva: se apoya en review_actions. Aplicar con apply_migration (nombre: objeciones).

-- 1. Acciones nuevas: object (botón que pide el texto), objectreply (el texto) y resolve (cierra las objeciones abiertas)
alter table public.review_actions drop constraint review_actions_action_check;
alter table public.review_actions add constraint review_actions_action_check
  check (action in ('approve', 'discard', 'regenerate', 'edit', 'editreply', 'object', 'objectreply', 'resolve'));

-- 2. Búsqueda de la última objeción/resolución de una pieza
create index review_actions_objection_idx on public.review_actions (content_item_id, id desc)
  where outcome = 'applied' and action in ('objectreply', 'resolve');

-- 3. Indicadores: columnas nuevas al final (create or replace no permite reordenar)
create or replace view public.review_item_stats with (security_invoker = true) as
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
  max(created_at)                                                        as last_action_at,
  count(*) filter (where action = 'objectreply' and outcome = 'applied') as objections
from public.review_actions
group by content_item_id;

create or replace view public.review_summary with (security_invoker = true) as
select
  count(*)                                                     as pieces_reviewed,
  count(*) filter (where approved)                             as approved,
  count(*) filter (where discarded)                            as discarded,
  count(*) filter (where approved_without_edit)                as approved_without_edit,
  round(count(*) filter (where approved_without_edit)::numeric
    / nullif(count(*) filter (where approved), 0), 4)          as approved_without_edit_rate,
  round(avg(edits), 2)                                         as edits_per_piece,
  round(avg(regenerations), 2)                                 as regenerations_per_piece,
  round(avg(objections), 2)                                    as objections_per_piece
from public.review_item_stats;

revoke all on public.review_item_stats, public.review_summary from anon, authenticated;
