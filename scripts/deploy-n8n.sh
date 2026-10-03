#!/usr/bin/env bash
# Despliega en la VM de producción el servicio n8n del compose del repo. Solo toca n8n:
# postgres y caddy no se recrean (--no-deps).
#
# Uso:
#   bash scripts/deploy-n8n.sh            simulación: comprueba todo, no modifica la VM
#   bash scripts/deploy-n8n.sh --apply    despliega
#
# Condiciones (si alguna falla, aborta antes de tocar nada):
#   - la imagen de n8n en el compose lleva versión fija (nunca `latest`)
#   - hay un respaldo de menos de 1 hora, con sumas SHA-256 correctas (bash scripts/backup.sh --verify)
#   - el compose es válido en la VM
# Si n8n no responde tras el despliegue, el script NO revierte: la base ya pudo migrar y la
# única vuelta atrás es restaurar el respaldo. Imprime el estado y sale con error.
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

SSH_OPTS=(-i "$ORACLE_SSH_KEY_PATH" -o BatchMode=yes -o ConnectTimeout=20)
VM="ubuntu@${ORACLE_VM_IP}"
REMOTE_DIR="letiende-sgcd/infrastructure"
COMPOSE="infrastructure/docker-compose.yml"
LOCAL_PORT=15679
BACKUP_MAX_AGE_S=3600
HEALTH_WAIT_S=240
TUNNEL_PID=""

cleanup() { [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true; }
trap cleanup EXIT

fail() { echo "✗ $*" >&2; exit 1; }
# shellcheck disable=SC2029  # REMOTE_DIR se expande a propósito en el cliente
remote() { ssh "${SSH_OPTS[@]}" "$VM" "$@"; }

# Cuenta los workflows activos de producción por un túnel (no depende del certificado).
# Reintenta la API: n8n responde /healthz antes de tener listas las rutas de la API.
active_workflows() {
  ssh "${SSH_OPTS[@]}" -N -L "$LOCAL_PORT:localhost:5678" "$VM" &
  TUNNEL_PID=$!
  local out="" rc=1
  for _ in $(seq 1 30); do
    out="$(curl -sf "http://localhost:$LOCAL_PORT/api/v1/workflows?limit=250" -H "X-N8N-API-KEY: $N8N_API_KEY" 2>/dev/null \
      | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(sum(1 for w in d if w["active"]), len(d))' 2>/dev/null)" && { rc=0; break; }
    sleep 4
  done
  kill "$TUNNEL_PID" 2>/dev/null || true
  TUNNEL_PID=""
  [ "$rc" -eq 0 ] || return 1
  echo "$out"
}

echo "→ [1/5] Condiciones previas"
TARGET_IMAGE="$(sed -n 's/^ *image: *\(n8nio\/n8n:[^ ]*\).*/\1/p' "$COMPOSE")"
[ -n "$TARGET_IMAGE" ] || fail "no encuentro la imagen de n8n en $COMPOSE"
[ "${TARGET_IMAGE##*:}" != "latest" ] || fail "la imagen de n8n no puede ser latest"
LAST_BACKUP="$(find backups -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
[ -n "$LAST_BACKUP" ] || fail "no hay respaldos: ejecuta bash scripts/backup.sh --verify"
BACKUP_AGE=$(( $(date +%s) - $(stat -f %m "$LAST_BACKUP/SHA256SUMS" 2>/dev/null || stat -c %Y "$LAST_BACKUP/SHA256SUMS") ))
[ "$BACKUP_AGE" -le "$BACKUP_MAX_AGE_S" ] || fail "el último respaldo ($LAST_BACKUP) tiene $((BACKUP_AGE / 60)) min; el máximo es $((BACKUP_MAX_AGE_S / 60))"
( cd "$LAST_BACKUP" && shasum -a 256 -c SHA256SUMS --quiet ) || fail "sumas de verificación del respaldo incorrectas"
echo "   imagen objetivo: $TARGET_IMAGE"
echo "   respaldo: $LAST_BACKUP ($((BACKUP_AGE / 60)) min, sumas OK)"

echo "→ [2/5] Estado actual de la VM"
CURRENT_IMAGE="$(remote "docker inspect -f '{{.Config.Image}}' infrastructure-n8n-1")"
WF_COUNT="$(active_workflows)"
ACTIVE_BEFORE="${WF_COUNT% *}"; TOTAL_BEFORE="${WF_COUNT#* }"
echo "   imagen en uso: $CURRENT_IMAGE"
echo "   workflows activos: $ACTIVE_BEFORE de $TOTAL_BEFORE"
echo "   memoria: $(remote "free -m | awk '/Mem:/ {print \$7\" MB disponibles\"}'")"

echo "→ [3/5] Validar el compose en la VM"
# Por stdin: no modifica nada en la VM; el .env del directorio resuelve las variables
remote "cd $REMOTE_DIR && docker compose -f - config --quiet" < "$COMPOSE" || fail "compose inválido en la VM"
echo "   compose válido"

if [ "$MODE" = "dry-run" ]; then
  echo "✓ Simulación completa: $CURRENT_IMAGE → $TARGET_IMAGE. Nada se modificó."
  echo "  Para desplegar: bash scripts/deploy-n8n.sh --apply"
  exit 0
fi

echo "→ [4/5] Desplegar solo n8n"
scp "${SSH_OPTS[@]}" -q "$COMPOSE" "$VM:$REMOTE_DIR/docker-compose.yml"
remote "cd $REMOTE_DIR && docker compose pull n8n 2>&1 | tail -2 && docker compose up -d --no-deps n8n 2>&1 | tail -3"

echo "   esperando a /healthz/readiness (máximo ${HEALTH_WAIT_S} s)"
OK=""
for _ in $(seq 1 $((HEALTH_WAIT_S / 6))); do
  CODE="$(remote 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5678/healthz/readiness' || true)"
  [ "$CODE" = "200" ] && { OK=1; break; }
  sleep 6
done
if [ -z "$OK" ]; then
  echo "✗ n8n no respondió en ${HEALTH_WAIT_S} s. No se revierte automáticamente." >&2
  remote 'docker ps --format "{{.Names}} {{.Image}} {{.Status}}"; docker logs --tail 30 infrastructure-n8n-1 2>&1 | cut -c1-200' >&2 || true
  echo "  Retroceso: restaurar $LAST_BACKUP (la base pudo migrar)." >&2
  exit 1
fi

echo "→ [5/5] Comprobaciones posteriores"
PROBLEMS=0
NOW_IMAGE="$(remote "docker inspect -f '{{.Config.Image}}' infrastructure-n8n-1")"
[ "$NOW_IMAGE" = "$TARGET_IMAGE" ] || fail "imagen en uso $NOW_IMAGE; esperaba $TARGET_IMAGE"
BIND="$(remote "ss -ltn | awk '\$4 ~ /:5678\$/ {print \$4}' | sort -u | tr '\n' ' '")"
echo "   imagen: $NOW_IMAGE | puerto 5678 en: $BIND"
case "$BIND" in
  "127.0.0.1:5678 ") ;;
  *) echo "   ⚠ el puerto 5678 no está solo en loopback" >&2; PROBLEMS=1 ;;
esac
if WF_COUNT="$(active_workflows)"; then
  ACTIVE_AFTER="${WF_COUNT% *}"; TOTAL_AFTER="${WF_COUNT#* }"
else
  ACTIVE_AFTER="?"; TOTAL_AFTER="?"; echo "   ⚠ la API de n8n no respondió" >&2; PROBLEMS=1
fi
echo "   workflows activos: $ACTIVE_AFTER de $TOTAL_AFTER (antes: $ACTIVE_BEFORE de $TOTAL_BEFORE)"
[ "$ACTIVE_AFTER" = "$ACTIVE_BEFORE" ] && [ "$TOTAL_AFTER" = "$TOTAL_BEFORE" ] || { echo "   ⚠ cambió el número de workflows" >&2; PROBLEMS=1; }
echo "   healthz público: $(curl -s -o /dev/null -w '%{http_code}' https://n8n.letiende.co/healthz)"
echo "   memoria: $(remote "free -m | awk '/Mem:/ {print \$7\" MB disponibles\"}'")"
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print("   webhook Telegram: pendientes", r.get("pending_update_count"), "| último error:", r.get("last_error_message", "ninguno"))'
[ "$PROBLEMS" -eq 0 ] || { echo "✗ Desplegado ($CURRENT_IMAGE → $NOW_IMAGE) pero con advertencias: revisa arriba." >&2; exit 1; }
echo "✓ Desplegado: $CURRENT_IMAGE → $NOW_IMAGE"
