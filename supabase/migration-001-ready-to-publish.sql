-- Migration 001: Agregar estado ready_to_publish
-- Necesario para Workflow 4 (publicacion sin RRSS integradas)
-- Ejecutar en Supabase SQL Editor: https://iljbfgbndwfaqacxthty.supabase.co

ALTER TABLE content_items
  DROP CONSTRAINT IF EXISTS content_items_status_check;

ALTER TABLE content_items
  ADD CONSTRAINT content_items_status_check
  CHECK (status IN (
    'ingested',
    'processing',
    'ready_for_review',
    'approved',
    'stalled',
    'discarded',
    'publishing',
    'ready_to_publish',
    'published',
    'error'
  ));
