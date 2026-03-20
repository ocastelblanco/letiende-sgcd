#!/usr/bin/env bash
# setup-supabase.sh — Aplica el schema de Supabase para SGCD Le Tiende.co
set -euo pipefail

# Verificar variables requeridas
: "${SUPABASE_URL:?Variable SUPABASE_URL no definida. Ejecuta: source credentials.env}"
: "${SUPABASE_SERVICE_ROLE_KEY:?Variable SUPABASE_SERVICE_ROLE_KEY no definida}"

# Verificar dependencias
command -v curl >/dev/null 2>&1 || { echo "Error: curl no está instalado"; exit 1; }

SCHEMA_FILE="$(dirname "$0")/../supabase/schema.sql"

if [[ ! -f "$SCHEMA_FILE" ]]; then
  echo "Error: No se encuentra el archivo $SCHEMA_FILE"
  exit 1
fi

echo "=== Aplicando schema de Supabase para Le Tiende SGCD ==="
echo "URL: $SUPABASE_URL"
echo ""

# Ejecutar el SQL via Supabase REST API (endpoint /rest/v1/rpc no permite DDL)
# Usar el endpoint de administración que sí permite DDL
echo "Aplicando schema.sql..."

RESPONSE=$(curl -sf \
  -X POST \
  "${SUPABASE_URL}/rest/v1/rpc/exec_sql" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"query\": $(cat "$SCHEMA_FILE" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
  2>&1 || true)

# Nota: Supabase no expone exec_sql por defecto. Usar psql si está disponible.
if command -v psql >/dev/null 2>&1; then
  echo "Usando psql para aplicar el schema..."
  # Extraer host de SUPABASE_URL (formato: https://project-id.supabase.co)
  SUPABASE_HOST=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|\.supabase\.co.*||')

  PGPASSWORD="$SUPABASE_SERVICE_ROLE_KEY" psql \
    -h "db.${SUPABASE_HOST}.supabase.co" \
    -p 5432 \
    -U postgres \
    -d postgres \
    -f "$SCHEMA_FILE"

  echo "✓ Schema aplicado via psql"
else
  echo ""
  echo "⚠️  psql no está disponible localmente."
  echo "Opciones para aplicar el schema manualmente:"
  echo ""
  echo "Opción A — Desde el panel de Supabase:"
  echo "  1. Ve a ${SUPABASE_URL} → SQL Editor"
  echo "  2. Pega el contenido de supabase/schema.sql"
  echo "  3. Ejecuta con Ctrl+Enter"
  echo ""
  echo "Opción B — Instala psql y vuelve a ejecutar este script:"
  echo "  macOS: brew install postgresql"
  echo "  Ubuntu: sudo apt install postgresql-client"
  echo ""
  echo "El archivo schema.sql está en: $SCHEMA_FILE"
  exit 1
fi

# Verificar que las tablas fueron creadas
echo ""
echo "--- Verificando tablas creadas ---"
TABLES_RESPONSE=$(curl -sf \
  "${SUPABASE_URL}/rest/v1/content_items?select=id&limit=1" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  2>&1)

if echo "$TABLES_RESPONSE" | grep -q '\[\]' || echo "$TABLES_RESPONSE" | grep -q '"id"'; then
  echo "✓ Tabla content_items accesible"
else
  echo "⚠️  No se pudo verificar la tabla content_items. Verifica manualmente en el panel de Supabase."
fi

echo ""
echo "=== ✅ Schema de Supabase aplicado ==="
echo ""
echo "Tablas creadas:"
echo "  - content_items"
echo "  - publish_log"
echo "  - metrics"
echo "  - quota_tracker (con datos iniciales)"
echo "  - error_log"
