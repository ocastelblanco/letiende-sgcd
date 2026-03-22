#!/usr/bin/env bash
# setup-r2.sh — Crea los buckets de Cloudflare R2 para SGCD Le Tiende.co
set -euo pipefail

# Verificar variables requeridas
: "${CF_ACCOUNT_ID:?Variable CF_ACCOUNT_ID no definida. Ejecuta: source credentials.env}"
: "${CF_R2_ACCESS_KEY_ID:?Variable CF_R2_ACCESS_KEY_ID no definida}"
: "${CF_R2_SECRET_ACCESS_KEY:?Variable CF_R2_SECRET_ACCESS_KEY no definida}"
: "${CF_R2_ENDPOINT:?Variable CF_R2_ENDPOINT no definida}"

# Verificar dependencias
command -v curl >/dev/null 2>&1 || { echo "Error: curl no está instalado"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "Error: AWS CLI no está instalado (se usa para interactuar con R2 via S3 API)"; exit 1; }

echo "=== Configurando Cloudflare R2 para Le Tiende SGCD ==="
echo "Account ID: ${CF_ACCOUNT_ID:0:8}..."

# Configurar AWS CLI para apuntar a R2 (compatible con S3 API)
export AWS_ACCESS_KEY_ID="$CF_R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$CF_R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="auto"

R2_ENDPOINT="$CF_R2_ENDPOINT"

# Función para crear bucket
create_bucket() {
  local bucket_name="$1"
  echo ""
  echo "--- Creando bucket: $bucket_name ---"

  if aws s3api head-bucket --bucket "$bucket_name" --endpoint-url "$R2_ENDPOINT" 2>/dev/null; then
    echo "✓ Bucket $bucket_name ya existe"
  else
    aws s3api create-bucket \
      --bucket "$bucket_name" \
      --endpoint-url "$R2_ENDPOINT"
    echo "✓ Bucket $bucket_name creado"
  fi
}

# Crear los tres buckets
create_bucket "letiende-raw-assets"
create_bucket "letiende-processed-assets"
create_bucket "letiende-templates-backup"

# Configurar lifecycle rule en letiende-raw-assets (expiración 30 días)
echo ""
echo "--- Configurando lifecycle en letiende-raw-assets (30 días) ---"
aws s3api put-bucket-lifecycle-configuration \
  --bucket "letiende-raw-assets" \
  --endpoint-url "$R2_ENDPOINT" \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-raw-assets-30d",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Expiration": { "Days": 30 }
    }]
  }'
echo "✓ Lifecycle configurado: raw-assets expiran en 30 días"

# Configurar lifecycle en letiende-processed-assets (expiración 90 días)
echo ""
echo "--- Configurando lifecycle en letiende-processed-assets (90 días) ---"
aws s3api put-bucket-lifecycle-configuration \
  --bucket "letiende-processed-assets" \
  --endpoint-url "$R2_ENDPOINT" \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-processed-assets-90d",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Expiration": { "Days": 90 }
    }]
  }'
echo "✓ Lifecycle configurado: processed-assets expiran en 90 días"

# Verificar acceso con objeto de prueba
# Nota: AWS CLI v2 usa chunked encoding + CRC64NVME que R2 no soporta.
# Se usa boto3 con payload_signing_enabled=False para PutObject/DeleteObject.
echo ""
echo "--- Verificando acceso con objeto de prueba ---"
python3 - << PYEOF
import boto3, sys
from botocore.config import Config

config = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path', 'payload_signing_enabled': False}
)
client = boto3.client(
    's3',
    endpoint_url='$CF_R2_ENDPOINT',
    aws_access_key_id='$CF_R2_ACCESS_KEY_ID',
    aws_secret_access_key='$CF_R2_SECRET_ACCESS_KEY',
    region_name='auto',
    config=config
)
try:
    client.put_object(Bucket='letiende-raw-assets', Key='test/access-check.txt', Body=b'1')
    print('✓ Objeto de prueba subido')
    client.delete_object(Bucket='letiende-raw-assets', Key='test/access-check.txt')
    print('✓ Objeto de prueba eliminado')
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
PYEOF

echo ""
echo "=== ✅ Cloudflare R2 configurado correctamente ==="
echo ""
echo "Buckets creados:"
echo "  - letiende-raw-assets      (lifecycle: 30 días)"
echo "  - letiende-processed-assets (lifecycle: 90 días)"
echo "  - letiende-templates-backup (sin lifecycle)"
