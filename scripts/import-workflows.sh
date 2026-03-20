#!/usr/bin/env bash
# import-workflows.sh — Importa los 5 workflows a n8n via API
set -euo pipefail

# Verificar variables requeridas
: "${N8N_API_KEY:?Variable N8N_API_KEY no definida. Ejecuta: source credentials.env}"

# Verificar dependencias
command -v curl >/dev/null 2>&1 || { echo "Error: curl no está instalado"; exit 1; }

N8N_BASE_URL="https://n8n.letiende.co"
WORKFLOWS_DIR="$(dirname "$0")/../n8n-workflows"

echo "=== Importando workflows a n8n ==="
echo "URL: $N8N_BASE_URL"
echo ""

# Verificar que n8n esté activo
echo "--- Verificando conexión con n8n ---"
HEALTH=$(curl -sf "${N8N_BASE_URL}/healthz" 2>&1 || echo "ERROR")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  echo "✓ n8n está activo"
else
  echo "Error: n8n no responde en ${N8N_BASE_URL}/healthz"
  echo "Respuesta: $HEALTH"
  exit 1
fi

# Función para importar un workflow
import_workflow() {
  local file="$1"
  local name="$(basename "$file" .json)"

  if [[ ! -f "$file" ]]; then
    echo "⚠️  Archivo no encontrado: $file (saltando)"
    return 0
  fi

  echo ""
  echo "--- Importando: $name ---"

  RESPONSE=$(curl -sf \
    -X POST \
    "${N8N_BASE_URL}/api/v1/workflows" \
    -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
    -H "Content-Type: application/json" \
    -d @"$file" 2>&1)

  if echo "$RESPONSE" | grep -q '"id"'; then
    WORKFLOW_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id','?'))" 2>/dev/null || echo "?")
    echo "✓ $name importado (ID: $WORKFLOW_ID)"

    # Activar el workflow
    if [[ -n "$WORKFLOW_ID" && "$WORKFLOW_ID" != "?" ]]; then
      curl -sf \
        -X PATCH \
        "${N8N_BASE_URL}/api/v1/workflows/${WORKFLOW_ID}" \
        -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"active": true}' >/dev/null 2>&1 && echo "✓ $name activado"
    fi
  else
    echo "⚠️  Error importando $name:"
    echo "   $RESPONSE"
  fi
}

# Importar los 5 workflows
import_workflow "${WORKFLOWS_DIR}/01-ingesta.json"
import_workflow "${WORKFLOWS_DIR}/02-generacion.json"
import_workflow "${WORKFLOWS_DIR}/03-revision.json"
import_workflow "${WORKFLOWS_DIR}/04-publicacion.json"
import_workflow "${WORKFLOWS_DIR}/05-metricas.json"

# Verificar estado final
echo ""
echo "--- Estado de workflows en n8n ---"
curl -sf \
  "${N8N_BASE_URL}/api/v1/workflows" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
workflows = data.get('data', [])
print(f'Total workflows: {len(workflows)}')
for w in workflows:
    status = '✅ activo' if w.get('active') else '⏸  inactivo'
    print(f'  {status} — {w[\"name\"]}')
" 2>/dev/null || echo "No se pudo obtener el listado de workflows"

echo ""
echo "=== ✅ Importación completada ==="
