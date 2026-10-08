#!/usr/bin/env bash
# Despliega a producción los workflows de n8n-workflows/ (PUT por la API + reactivación).
# Solo toca workflows que ya existen: nunca crea ni borra.
#
# Uso:
#   bash scripts/deploy-workflows.sh            simulación: compara y valida, no modifica nada
#   bash scripts/deploy-workflows.sh --apply    despliega
#
# Condiciones (si alguna falla, aborta antes de tocar nada):
#   - hay un respaldo de menos de 1 hora, con sumas SHA-256 correctas (bash scripts/backup.sh --verify)
#   - cada JSON es válido y trae name, nodes, connections y settings
#   - ningún JSON lleva campos de solo lectura (active, tags, staticData, meta, pinData...)
# WF03 se despliega al final: al activarse, su Telegram Trigger se queda con el webhook del bot
# (hoy apunta a WF03; ADR-012 lo resolverá con un router único). El script avisa si la URL cambia.
# No revierte solo: el retroceso es restaurar el respaldo o reimportar los JSON anteriores.
# Los secretos se leen de credentials.env; nunca se pasan como argumento.
# Con `sh script.sh` (en macOS, bash en modo POSIX) fallan construcciones de bash: relanzar con bash
if [ -z "${BASH_VERSION:-}" ] || shopt -oq posix; then exec /usr/bin/env bash "$0" "$@"; fi
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source credentials.env
set +a

MODE="dry-run"
case "${1:-}" in
  "") ;;
  --apply) MODE="apply" ;;
  *) echo "uso: $0 [--apply]" >&2; exit 1 ;;
esac

API="https://n8n.letiende.co/api/v1"
BACKUP_MAX_AGE_S=3600
# archivo:id de producción (inmutables, ver CLAUDE.md). WF03 va al final a propósito.
WORKFLOWS="01-ingesta:ZE5IjN2YzTX15Qm4 02-generacion:lF8QngxsBPpgta2G 04-publicacion:4z8wU9qrV4rw5NC2 05-metricas:RxayCUeh3qCY2JIY 03-revision:unOTijMfyurxMcB1"
READONLY="active tags staticData meta pinData versionId activeVersionId triggerCount shared isArchived description id"

fail() { echo "✗ $*" >&2; exit 1; }
api() { curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" "$@"; }
webhook_url() {
  curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"].get("url",""))'
}
# nodos y estado activo de un workflow vivo: "N activo|inactivo"
live_state() {
  api "$API/workflows/$1" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d["nodes"]), "activo" if d["active"] else "inactivo")'
}

echo "→ [1/4] Condiciones previas"
LAST_BACKUP="$(find backups -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
[ -n "$LAST_BACKUP" ] || fail "no hay respaldos: ejecuta bash scripts/backup.sh --verify"
BACKUP_AGE=$(( $(date +%s) - $(stat -f %m "$LAST_BACKUP/SHA256SUMS" 2>/dev/null || stat -c %Y "$LAST_BACKUP/SHA256SUMS") ))
[ "$BACKUP_AGE" -le "$BACKUP_MAX_AGE_S" ] || fail "el último respaldo ($LAST_BACKUP) tiene $((BACKUP_AGE / 60)) min; el máximo es $((BACKUP_MAX_AGE_S / 60))"
( cd "$LAST_BACKUP" && shasum -a 256 -c SHA256SUMS --quiet ) || fail "sumas de verificación del respaldo incorrectas"
echo "   respaldo: $LAST_BACKUP ($((BACKUP_AGE / 60)) min, sumas OK)"
for pair in $WORKFLOWS; do
  f="n8n-workflows/${pair%%:*}.json"
  python3 - "$f" "$READONLY" <<'PY' || fail "$f no es un workflow desplegable"
import json, sys
w = json.load(open(sys.argv[1]))
missing = [k for k in ("name", "nodes", "connections", "settings") if k not in w]
bad = [k for k in sys.argv[2].split() if k in w]
if missing or bad:
    sys.exit(f"faltan {missing}, sobran {bad}")
PY
done
echo "   5 JSON válidos y sin campos de solo lectura"

echo "→ [2/4] Estado actual en producción"
HOOK_BEFORE="$(webhook_url)"
echo "   webhook de Telegram: ${HOOK_BEFORE##*/webhook/}"
for pair in $WORKFLOWS; do
  f="${pair%%:*}"; id="${pair##*:}"
  nodes_file="$(python3 -c "import json; print(len(json.load(open('n8n-workflows/$f.json'))['nodes']))")"
  echo "   $f: vivo $(live_state "$id") | archivo $nodes_file nodos"
done

if [ "$MODE" = "dry-run" ]; then
  echo "✓ Simulación completa. Nada se modificó."
  echo "  Para desplegar: bash scripts/deploy-workflows.sh --apply"
  exit 0
fi

echo "→ [3/4] Desplegar"
for pair in $WORKFLOWS; do
  f="${pair%%:*}"; id="${pair##*:}"
  api -X PUT "$API/workflows/$id" -d @"n8n-workflows/$f.json" -o /dev/null || fail "PUT de $f falló (los siguientes no se tocaron)"
  api -X POST "$API/workflows/$id/activate" -o /dev/null || fail "no se pudo activar $f"
  echo "   $f ✓"
done

echo "→ [4/4] Comprobaciones posteriores"
PROBLEMS=0
for pair in $WORKFLOWS; do
  f="${pair%%:*}"; id="${pair##*:}"
  want="$(python3 -c "import json; print(len(json.load(open('n8n-workflows/$f.json'))['nodes']))") activo"
  got="$(live_state "$id")"
  [ "$got" = "$want" ] && echo "   $f: $got" || { echo "   ⚠ $f: esperaba '$want', hay '$got'" >&2; PROBLEMS=1; }
done
HOOK_AFTER="$(webhook_url)"
[ "$HOOK_AFTER" = "$HOOK_BEFORE" ] && echo "   webhook de Telegram sin cambios" || { echo "   ⚠ el webhook de Telegram cambió: $HOOK_BEFORE → $HOOK_AFTER" >&2; PROBLEMS=1; }
echo "   healthz público: $(curl -s -o /dev/null -w '%{http_code}' https://n8n.letiende.co/healthz)"
[ "$PROBLEMS" -eq 0 ] || { echo "✗ Desplegado con advertencias: revisa arriba." >&2; exit 1; }
echo "✓ 5 workflows desplegados y activos"
