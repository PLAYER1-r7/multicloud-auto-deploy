#!/usr/bin/env bash
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-PLAYER1-r7/multicloud-auto-deploy}"
INCLUDE_FRONTEND="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --include-frontend)
      INCLUDE_FRONTEND="true"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--repo <owner/repo>] [--include-frontend]" >&2
      exit 1
      ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required" >&2
  exit 1
fi

core_required=(
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  GCP_CREDENTIALS
)

azure_sp_required=(
  AZURE_CLIENT_ID
  AZURE_TENANT_ID
  AZURE_SUBSCRIPTION_ID
)

frontend_required=(
  AZURE_CREDENTIALS
  AZURE_API_ENDPOINT
  AZURE_AD_CLIENT_ID
  GCP_PROJECT_ID
  GCP_API_ENDPOINT
  FIREBASE_API_KEY
  FIREBASE_AUTH_DOMAIN
  FIREBASE_APP_ID
  PULUMI_ACCESS_TOKEN
)

required=("${core_required[@]}")
if [[ "$INCLUDE_FRONTEND" == "true" ]]; then
  required+=("${frontend_required[@]}")
fi

environments=(staging production)

echo "Repository: ${REPO}"
echo "Include frontend secrets: ${INCLUDE_FRONTEND}"
echo

for env in "${environments[@]}"; do
  echo "=== Environment: ${env} ==="

  env_secret_names="$(gh secret list --repo "$REPO" --env "$env" --json name --jq '.[].name' 2>/dev/null || true)"
  repo_secret_names="$(gh secret list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null || true)"

  missing=()
  for key in "${required[@]}"; do
    if grep -qx "$key" <<<"$env_secret_names"; then
      continue
    fi
    if grep -qx "$key" <<<"$repo_secret_names"; then
      continue
    fi
    missing+=("$key")
  done

  has_secret() {
    local name="$1"
    grep -qx "$name" <<<"$env_secret_names" && return 0
    grep -qx "$name" <<<"$repo_secret_names" && return 0
    return 1
  }

  azure_sp_complete=true
  for key in "${azure_sp_required[@]}"; do
    if ! has_secret "$key"; then
      azure_sp_complete=false
      break
    fi
  done

  azure_creds_available=false
  if has_secret "AZURE_CREDENTIALS"; then
    azure_creds_available=true
  fi

  if [[ "$azure_sp_complete" != "true" && "$azure_creds_available" != "true" ]]; then
    missing+=("AZURE_CLIENT_ID")
    missing+=("AZURE_TENANT_ID")
    missing+=("AZURE_SUBSCRIPTION_ID")
    missing+=("AZURE_CREDENTIALS")
  fi

  if [[ ${#missing[@]} -eq 0 ]]; then
    echo "✅ Required secrets are available (env or repo level)."
  else
    echo "❌ Missing secrets (${#missing[@]}):"
    for key in "${missing[@]}"; do
      echo "  - $key"
    done
  fi
  echo
done

echo "Done."
