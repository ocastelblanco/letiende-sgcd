-- Migration 006: reabrir piezas detenidas (T-0040, plan-actualizacion §4 Fase 4)
-- Una pieza sin decisión a las 48 h pasa a `stalled` (estado ya permitido desde migration-001) y cualquier usuario autorizado
-- puede reabrirla. Esa acción queda en review_actions. Aplicar con apply_migration (nombre: reopen).
alter table public.review_actions drop constraint review_actions_action_check;
alter table public.review_actions add constraint review_actions_action_check
  check (action in ('approve', 'discard', 'regenerate', 'edit', 'editreply', 'object', 'objectreply', 'resolve', 'reopen'));
