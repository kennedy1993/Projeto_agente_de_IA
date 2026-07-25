#!/usr/bin/env bash
# Builda a imagem do agente e envia para o Amazon ECR.
# Uso:
#   AWS_REGION=us-east-1 ./deploy/push_to_ecr.sh
#
# Pré-requisitos: AWS CLI instalado e configurado (`aws configure`) com uma
# credencial que tenha permissão de ECR (AmazonEC2ContainerRegistryFullAccess
# ou equivalente).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_NAME="${ECR_REPO_NAME:-bimbambuy-agente}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "Conta AWS: ${ACCOUNT_ID}"
echo "Região:    ${AWS_REGION}"
echo "Repositório ECR: ${ECR_URI}"

echo "==> Garantindo que o repositório ECR existe..."
aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null

echo "==> Autenticando o Docker no ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Buildando a imagem..."
docker build -t "$ECR_REPO_NAME:$IMAGE_TAG" "$PROJECT_DIR"

echo "==> Marcando e enviando para o ECR..."
docker tag "$ECR_REPO_NAME:$IMAGE_TAG" "$ECR_URI:$IMAGE_TAG"
docker push "$ECR_URI:$IMAGE_TAG"

echo ""
echo "Imagem publicada em:"
echo "  $ECR_URI:$IMAGE_TAG"
echo ""
echo "Use essa URI ao criar (ou atualizar) o serviço no AWS App Runner."
