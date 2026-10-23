#!/usr/bin/env bash
# Escribe en el .env de la VM (~/letiende-sgcd/infrastructure/.env) una variable de credentials.env.
# El valor viaja por stdin: nunca aparece en un argumento, en el historial ni en la salida.
# Solo escribe el .env: para que n8n la lea hay que reiniciarlo con bash scripts/deploy-n8n.sh --apply.
#
# Uso:
#   bash scripts/set-vm-env.sh NOMBRE            simulación: dice si la variable existe en la VM y si cambiaría
#   bash scripts/set-vm-env.sh NOMBRE --apply    escribe (deja copia .env.bak-<fecha> en la VM)
# Con `sh script.sh` (en macOS, bash en modo POSIX) fallan construcciones de bash: relanzar con bash
if [ -z "${BASH_VERSION:-}" ] || shopt -oq posix; then exec /usr/bin/env bash "$0" "$@"; fi
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
NAME="${1:-}"; MODE="dry-run"
[[ "$NAME" =~ ^[A-Z][A-Z0-9_]*$ ]] || { echo "uso: $0 NOMBRE_VARIABLE [--apply]" >&2; exit 1; }
[ "${2:-}" = "--apply" ] && MODE="apply"
set -a
# shellcheck disable=SC1091
source credentials.env
set +a
VALUE="${!NAME:-}"
[ -n "$VALUE" ] || { echo "✗ $NAME está vacía en credentials.env" >&2; exit 1; }
# Evita que un valor con saltos de línea rompa el .env
case "$VALUE" in *$'\n'*|*"'"*) echo "✗ el valor no puede tener saltos de línea ni comillas simples" >&2; exit 1 ;; esac

SSH_OPTS=(-i "$ORACLE_SSH_KEY_PATH" -o BatchMode=yes -o ConnectTimeout=20)
VM="ubuntu@${ORACLE_VM_IP}"
ENV_FILE="letiende-sgcd/infrastructure/.env"

# El script remoto viaja como argumento de bash -c y el valor por stdin (un heredoc ocuparía el stdin).
# El nombre sí viaja como argumento (no es secreto)
read -r -d '' REMOTE_SCRIPT <<'REMOTE' || true
set -euo pipefail
name="$1"; mode="$2"; file="$3"
IFS= read -r value || true  # sin salto de línea final read devuelve 1
actual="$(grep -E "^${name}=" "$file" | head -n1 | cut -d= -f2- || true)"
if [ -z "$actual" ]; then estado="no existe"
elif [ "$actual" = "$value" ]; then estado="existe y es igual"
else estado="existe y es distinta"; fi
echo "   $name en la VM: $estado"
[ "$mode" = "apply" ] || { echo "✓ Simulación completa. Nada se modificó."; exit 0; }
[ "$estado" != "existe y es igual" ] || { echo "✓ Sin cambios."; exit 0; }
cp -p "$file" "$file.bak-$(date +%Y%m%d%H%M%S)"
if [ -z "$actual" ]; then
  printf '%s=%s\n' "$name" "$value" >> "$file"
else
  tmp="$(mktemp)"; grep -vE "^${name}=" "$file" > "$tmp"; printf '%s=%s\n' "$name" "$value" >> "$tmp"
  cat "$tmp" > "$file"; rm -f "$tmp"
fi
chmod 600 "$file"
echo "✓ $name escrita en $file (copia previa .bak-*)"
REMOTE
printf '%s' "$VALUE" | ssh "${SSH_OPTS[@]}" "$VM" "bash -c $(printf '%q' "$REMOTE_SCRIPT") remoto $(printf '%q ' "$NAME" "$MODE" "$ENV_FILE")"
