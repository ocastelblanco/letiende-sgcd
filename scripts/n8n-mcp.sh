#!/usr/bin/env bash
# Lanza el servidor MCP n8n-mcp (stdio) para Claude Code.
# Los secretos se cargan de credentials.env en tiempo de ejecución: nunca se escriben
# en la configuración de Claude Code (~/.claude.json).
#
# Registro (una vez, ámbito local, no versionado):
#   claude mcp add -s local n8n-mcp -- "$(pwd)/scripts/n8n-mcp.sh"
# Instancia objetivo: N8N_MCP_TARGET=prod (por defecto) | dev (n8n local en Docker)
set -euo pipefail

# Versión fijada del servidor; actualizar a propósito, no con @latest
N8N_MCP_VERSION="2.91.0"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# stdout es el canal del protocolo MCP: nada más puede escribir en él
set -a
# shellcheck disable=SC1091
source "$ROOT/credentials.env" >/dev/null
set +a

case "${N8N_MCP_TARGET:-prod}" in
  prod) export N8N_API_URL="https://n8n.letiende.co" ;;
  dev)
    export N8N_API_URL="http://localhost:5678"
    export N8N_API_KEY="${N8N_DEV_API_KEY:-}"
    # n8n-mcp bloquea localhost por defecto (protección SSRF); solo se relaja para la instancia dev
    export WEBHOOK_SECURITY_MODE=moderate
    ;;
  *) echo "N8N_MCP_TARGET inválido: ${N8N_MCP_TARGET}" >&2; exit 1 ;;
esac

export MCP_MODE=stdio
export LOG_LEVEL=error
export DISABLE_CONSOLE_OUTPUT=true
export N8N_MCP_TELEMETRY_DISABLED=true

exec npx -y "n8n-mcp@${N8N_MCP_VERSION}"
