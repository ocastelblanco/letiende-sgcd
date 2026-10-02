#!/usr/bin/env bash
# Respaldo completo del sistema SGCD en backups/<fecha>/.
#   1. Workflows vivos de n8n (API, por túnel SSH: no depende del certificado SSL)
#   2. Base de datos de n8n (pg_dump dentro del contenedor, enviado por SSH)
#   3. Configuración de la VM (docker-compose.yml, nginx.conf y .env)
#   4. Base de datos de negocio en Supabase (esquema public)
#
# Uso:
#   bash scripts/backup.sh                          respalda
#   bash scripts/backup.sh --verify                 respalda y verifica la restauración
#   bash scripts/backup.sh --verify-only <carpeta>  verifica un respaldo existente
# La verificación restaura el dump de n8n en un Postgres local desechable (requiere Docker).
# Los secretos se leen de credentials.env; el respaldo contiene datos sensibles y queda fuera de git.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source credentials.env
set +a

SSH_OPTS=(-i "$ORACLE_SSH_KEY_PATH" -o BatchMode=yes -o ConnectTimeout=20)
VM="ubuntu@$ORACLE_VM_IP"
LOCAL_PORT=15678
PG_DUMP_SUPABASE="${PG_DUMP_SUPABASE:-/opt/homebrew/opt/libpq/bin/pg_dump}"
TUNNEL_PID=""
CONTAINER=""

cleanup() {
  [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
  [ -n "$CONTAINER" ] && docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

backup() {
  DEST="backups/$(date +%Y-%m-%d_%H%M)"
  umask 077
  mkdir -p "$DEST/workflows" "$DEST/vm"

  echo "→ [1/4] Workflows de n8n"
  ssh "${SSH_OPTS[@]}" -N -L "$LOCAL_PORT:localhost:5678" "$VM" &
  TUNNEL_PID=$!
  for _ in $(seq 1 20); do
    curl -s -o /dev/null "http://localhost:$LOCAL_PORT/healthz" && break
    sleep 1
  done
  curl -sf "http://localhost:$LOCAL_PORT/api/v1/workflows?limit=250" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" > "$DEST/workflows/_lista.json"
  python3 - "$DEST/workflows" <<'PY'
import json, os, sys, urllib.request
dest = sys.argv[1]
key = os.environ["N8N_API_KEY"]
lista = json.load(open(f"{dest}/_lista.json"))["data"]
for w in lista:
    req = urllib.request.Request(
        f"http://localhost:15678/api/v1/workflows/{w['id']}",
        headers={"X-N8N-API-KEY": key},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    with open(f"{dest}/{w['id']}.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
print(f"   {len(lista)} workflows exportados")
PY
  kill "$TUNNEL_PID" 2>/dev/null || true
  TUNNEL_PID=""

  echo "→ [2/4] Base de datos de n8n"
  ssh "${SSH_OPTS[@]}" "$VM" \
    'docker exec infrastructure-postgres-1 pg_dump -U n8n -d n8n --no-owner --format=custom' \
    > "$DEST/n8n-db.dump"
  echo "   $(du -h "$DEST/n8n-db.dump" | cut -f1)"

  echo "→ [3/4] Configuración de la VM"
  scp "${SSH_OPTS[@]}" -q \
    "$VM:~/letiende-sgcd/infrastructure/docker-compose.yml" \
    "$VM:~/letiende-sgcd/infrastructure/nginx.conf" \
    "$VM:~/letiende-sgcd/infrastructure/.env" \
    "$DEST/vm/"

  echo "→ [4/4] Supabase (esquema public)"
  "$PG_DUMP_SUPABASE" "$SUPABASE_DB_URL" --schema=public --no-owner --no-privileges \
    --format=custom -f "$DEST/supabase-public.dump"
  echo "   $(du -h "$DEST/supabase-public.dump" | cut -f1)"

  ( cd "$DEST" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256 > SHA256SUMS )
  echo "✓ Respaldo en $DEST"
}

verify() {
  local dir="$1"
  echo "→ Verificación de $dir"
  ( cd "$dir" && shasum -a 256 -c SHA256SUMS --quiet ) && echo "   sumas de verificación OK"
  CONTAINER="sgcd-restore-test-$$"
  docker run -d --rm --name "$CONTAINER" -e POSTGRES_PASSWORD=test -e POSTGRES_DB=n8n \
    postgres:15-alpine >/dev/null
  # El arranque inicial levanta un servidor temporal solo por socket; el definitivo escucha por TCP
  for _ in $(seq 1 60); do
    docker exec "$CONTAINER" pg_isready -h 127.0.0.1 -U postgres -q && break
    sleep 1
  done
  docker exec -i "$CONTAINER" pg_restore -h 127.0.0.1 -U postgres -d n8n --no-owner \
    < "$dir/n8n-db.dump"
  for t in workflow_entity credentials_entity execution_entity; do
    printf '   %-20s %s filas\n' "$t" \
      "$(docker exec "$CONTAINER" psql -h 127.0.0.1 -U postgres -d n8n -tAc "select count(*) from $t")"
  done
  echo "✓ Restauración verificada"
}

case "${1:-}" in
  "")            backup ;;
  --verify)      backup; verify "$DEST" ;;
  --verify-only) verify "${2:?indica la carpeta del respaldo}" ;;
  *) echo "uso: $0 [--verify | --verify-only <carpeta>]" >&2; exit 1 ;;
esac
