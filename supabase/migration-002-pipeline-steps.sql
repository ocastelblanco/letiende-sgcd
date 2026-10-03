-- Migration 002: instrumentación del flujo (T-0017, plan-actualizacion §4 Fase 2)
-- Una fila por intento de cada paso del flujo: duración, resultado, modelo, tokens y costo.
-- La escribe n8n con la service_role key (que ignora RLS); anon y authenticated no tienen acceso.
-- Aplicar con: Supabase SQL Editor, o la herramienta apply_migration (nombre: pipeline_steps).

create table public.pipeline_steps (
  id               bigint generated always as identity primary key,
  content_item_id  uuid not null references public.content_items (id) on delete cascade,
  -- Nombre del paso en snake_case (p. ej. extract_visual, write_captions, validate, review_send)
  step             text not null check (step ~ '^[a-z][a-z0-9_]*$'),
  -- Reintentos del mismo paso: 1 = primer intento
  attempt          smallint not null default 1 check (attempt >= 1),
  status           text not null default 'started'
                   check (status in ('started', 'succeeded', 'failed', 'skipped', 'waiting_quota')),
  started_at       timestamptz not null default now(),
  finished_at      timestamptz,
  error_type       text,
  error_message    text,
  -- Solo pasos que llaman a un modelo
  model            text,
  tokens_input     integer check (tokens_input >= 0),
  tokens_output    integer check (tokens_output >= 0),
  cost_usd         numeric(12, 6) check (cost_usd >= 0),
  -- Para ir de la fila a la ejecución en n8n
  n8n_execution_id text,
  created_at       timestamptz not null default now(),

  -- Idempotencia: n8n inserta 'started' y luego actualiza la misma fila
  unique (content_item_id, step, attempt),
  check (finished_at is null or finished_at >= started_at),
  -- Un paso está abierto si y solo si está en 'started'
  check ((status = 'started') = (finished_at is null))
);

comment on table public.pipeline_steps is
  'Un intento de un paso del flujo por fila. Base de las vistas pipeline_* del tablero.';

-- La restricción unique ya indexa content_item_id (columna inicial), que cubre la clave foránea.
-- Tablero: ventanas de tiempo por paso
create index pipeline_steps_step_started_idx on public.pipeline_steps (step, started_at desc);
-- Items atascados: solo las filas abiertas (muy pocas)
create index pipeline_steps_open_idx on public.pipeline_steps (started_at) where status = 'started';

-- Seguridad: RLS sin políticas = denegado para anon/authenticated; service_role la ignora.
alter table public.pipeline_steps enable row level security;
revoke all on table public.pipeline_steps from anon, authenticated;
revoke all on sequence public.pipeline_steps_id_seq from anon, authenticated;

-- Vistas con los permisos de quien consulta (no del dueño), para que RLS siga aplicando.

-- Duración (p50 y p95) y tasa de fallo por paso, últimos 7 días.
-- Las duraciones cuentan solo intentos terminados con resultado real (no 'skipped' ni 'waiting_quota').
create view public.pipeline_step_stats with (security_invoker = true) as
select
  step,
  count(*) filter (where status <> 'skipped')                          as runs,
  count(*) filter (where status = 'failed')                            as failed,
  count(*) filter (where status = 'waiting_quota')                     as waiting_quota,
  round(
    count(*) filter (where status = 'failed')::numeric
    / nullif(count(*) filter (where status <> 'skipped'), 0), 4)       as failure_rate,
  round((percentile_cont(0.5) within group
    (order by extract(epoch from finished_at - started_at))
    filter (where status in ('succeeded', 'failed')))::numeric, 2)     as p50_s,
  round((percentile_cont(0.95) within group
    (order by extract(epoch from finished_at - started_at))
    filter (where status in ('succeeded', 'failed')))::numeric, 2)     as p95_s
from public.pipeline_steps
where started_at >= now() - interval '7 days'
  and status <> 'started'
group by step;

-- Pasos abiertos hace más de 30 minutos: el flujo se cayó o quedó colgado en ese item.
create view public.pipeline_stuck_steps with (security_invoker = true) as
select
  s.content_item_id,
  s.step,
  s.attempt,
  s.started_at,
  now() - s.started_at as open_for,
  c.status             as item_status
from public.pipeline_steps s
join public.content_items c on c.id = s.content_item_id
where s.status = 'started'
  and s.started_at < now() - interval '30 minutes';

-- Consumo por día y modelo. El día de cuota de Gemini se reinicia a medianoche del Pacífico,
-- así que se agrupa por fecha en America/Los_Angeles (plan §3).
create view public.pipeline_daily_usage with (security_invoker = true) as
select
  (started_at at time zone 'America/Los_Angeles')::date as quota_day,
  model,
  count(*)                                              as calls,
  count(*) filter (where status = 'failed')             as failed,
  count(*) filter (where status = 'waiting_quota')      as rate_limited,
  sum(tokens_input)                                     as tokens_input,
  sum(tokens_output)                                    as tokens_output,
  sum(cost_usd)                                         as cost_usd
from public.pipeline_steps
where model is not null
group by 1, 2;

revoke all on public.pipeline_step_stats, public.pipeline_stuck_steps, public.pipeline_daily_usage
  from anon, authenticated;
