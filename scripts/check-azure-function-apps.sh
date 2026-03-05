#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${1:-staging}"
if [[ "$ENV_NAME" != "staging" && "$ENV_NAME" != "production" ]]; then
  echo "Usage: $0 [staging|production]" >&2
  exit 1
fi

RG="multicloud-auto-deploy-${ENV_NAME}-rg"
APPS=(
  "multicloud-auto-deploy-${ENV_NAME}-api"
  "multicloud-auto-deploy-${ENV_NAME}-solver"
)

if ! command -v az >/dev/null 2>&1; then
  echo "Error: Azure CLI (az) is required" >&2
  exit 1
fi

echo "Environment: ${ENV_NAME}"
echo "Resource Group: ${RG}"
echo

missing=()
for app in "${APPS[@]}"; do
  if az functionapp show --resource-group "$RG" --name "$app" >/dev/null 2>&1; then
    echo "✅ $app"
  else
    echo "❌ $app (not found)"
    missing+=("$app")
  fi
done

echo
if [[ ${#missing[@]} -eq 0 ]]; then
  echo "All required Azure Function Apps exist."
else
  echo "Missing Function Apps:"
  for app in "${missing[@]}"; do
    echo "  - $app"
  done
  echo
  echo "Run infrastructure update:"
  echo "  cd infrastructure/pulumi/azure && pulumi up"
  exit 2
fi
