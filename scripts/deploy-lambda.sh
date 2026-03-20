#!/usr/bin/env bash
# deploy-lambda.sh — Construye y despliega la función Lambda de procesamiento de video
set -euo pipefail

# Verificar variables requeridas
: "${AWS_REGION:?Variable AWS_REGION no definida. Ejecuta: source credentials.env}"
: "${CF_R2_ENDPOINT:?Variable CF_R2_ENDPOINT no definida}"
: "${CF_R2_ACCESS_KEY_ID:?Variable CF_R2_ACCESS_KEY_ID no definida}"
: "${CF_R2_SECRET_ACCESS_KEY:?Variable CF_R2_SECRET_ACCESS_KEY no definida}"

# Verificar dependencias
command -v aws >/dev/null 2>&1 || { echo "Error: AWS CLI no está instalado"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: Docker no está instalado"; exit 1; }

FUNCTION_NAME="letiende-video-processor"
LAMBDA_DIR="$(dirname "$0")/../lambda/video-processor"

echo "=== Desplegando Lambda: $FUNCTION_NAME ==="

# Obtener Account ID de AWS
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FUNCTION_NAME}"

echo "Account ID: $AWS_ACCOUNT_ID"
echo "ECR Repo: $ECR_REPO"
echo ""

# 1. Crear repositorio ECR si no existe
echo "--- Paso 1: Crear repositorio ECR ---"
aws ecr describe-repositories --repository-names "$FUNCTION_NAME" \
  --region "$AWS_REGION" 2>/dev/null || \
aws ecr create-repository \
  --repository-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --image-scanning-configuration scanOnPush=true
echo "✓ Repositorio ECR listo"

# 2. Autenticar Docker con ECR
echo ""
echo "--- Paso 2: Autenticar Docker con ECR ---"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
echo "✓ Docker autenticado con ECR"

# 3. Construir imagen Docker
echo ""
echo "--- Paso 3: Construir imagen Docker ---"
IMAGE_TAG="$(date +%Y%m%d%H%M%S)"
docker build -t "${FUNCTION_NAME}:${IMAGE_TAG}" "$LAMBDA_DIR"
docker tag "${FUNCTION_NAME}:${IMAGE_TAG}" "${ECR_REPO}:${IMAGE_TAG}"
docker tag "${FUNCTION_NAME}:${IMAGE_TAG}" "${ECR_REPO}:latest"
echo "✓ Imagen construida: ${IMAGE_TAG}"

# 4. Push a ECR
echo ""
echo "--- Paso 4: Push imagen a ECR ---"
docker push "${ECR_REPO}:${IMAGE_TAG}"
docker push "${ECR_REPO}:latest"
echo "✓ Imagen publicada en ECR"

# 5. Crear o actualizar función Lambda
echo ""
echo "--- Paso 5: Crear o actualizar función Lambda ---"

ENV_VARS="Variables={CF_R2_ENDPOINT=${CF_R2_ENDPOINT},CF_R2_ACCESS_KEY_ID=${CF_R2_ACCESS_KEY_ID},CF_R2_SECRET_ACCESS_KEY=${CF_R2_SECRET_ACCESS_KEY},CF_R2_BUCKET_PROCESSED=letiende-processed-assets}"

if aws lambda get-function --function-name "$FUNCTION_NAME" \
   --region "$AWS_REGION" 2>/dev/null; then
  # Actualizar función existente
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --image-uri "${ECR_REPO}:${IMAGE_TAG}" \
    --region "$AWS_REGION"

  # Esperar a que el update esté completo
  aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"

  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --memory-size 512 \
    --timeout 900 \
    --environment "$ENV_VARS" \
    --region "$AWS_REGION"

  echo "✓ Función Lambda actualizada"
else
  # Crear función nueva
  # Crear rol de ejecución si no existe
  ROLE_NAME="letiende-lambda-execution-role"
  ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" \
    --query 'Role.Arn' --output text 2>/dev/null || \
    aws iam create-role \
      --role-name "$ROLE_NAME" \
      --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Principal": {"Service": "lambda.amazonaws.com"},
          "Action": "sts:AssumeRole"
        }]
      }' \
      --query 'Role.Arn' --output text)

  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
    2>/dev/null || true

  # Esperar a que el rol esté disponible
  sleep 10

  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --package-type Image \
    --code "ImageUri=${ECR_REPO}:${IMAGE_TAG}" \
    --role "$ROLE_ARN" \
    --memory-size 512 \
    --timeout 900 \
    --environment "$ENV_VARS" \
    --region "$AWS_REGION"

  echo "✓ Función Lambda creada"
fi

echo ""
echo "=== ✅ Lambda desplegado correctamente ==="
echo ""
echo "Función: $FUNCTION_NAME"
echo "Región: $AWS_REGION"
echo "Memoria: 512 MB"
echo "Timeout: 900 segundos (15 minutos)"
echo "Imagen: ${ECR_REPO}:${IMAGE_TAG}"
