#!/usr/bin/env bash
set -uo pipefail

project_id=""
principal=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) project_id="${2:-}"; shift 2 ;;
    --principal) principal="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || [[ ! "$principal" =~ ^(user|serviceAccount|group):[^[:space:]]+@[^[:space:]]+$ ]]; then
  echo "Usage: bash scripts/gcp_bootstrap.sh --project YOUR_PROJECT_ID --principal user:PERSON@COMPANY.COM" >&2
  exit 2
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is required. Run this from Google Cloud Shell or a workstation with Google Cloud CLI." >&2
  exit 1
fi

handoff="gcp-admin-request.txt"
cat > "$handoff" <<EOF
RAISE Assistant — Google Cloud administrator handoff

Project: $project_id
Person or workload: $principal

Please verify:
1. Vertex AI API (aiplatform.googleapis.com) is enabled.
2. The principal has roles/aiplatform.user on this project (or an approved custom role with aiplatform.endpoints.predict and serviceusage.services.use as appropriate).
3. The principal has roles/serviceusage.serviceUsageConsumer so local ADC can set this project's quota.
4. Claude partner model access is enabled for the exact model ID and requested region in Vertex AI Model Garden, including any provider terms acceptance.
5. Organization policy constraints/vertexai.allowedModels and service restrictions permit this model and its supporting services.
6. The project has billing and quota available. No service-account key is requested.

If partner-model terms need acceptance, an authorized administrator may need roles/consumerprocurement.entitlementManager temporarily. Do not grant that role to every app user.

After project setup, the app user runs scripts/gcp_local_auth.sh on their own computer and sets GOOGLE_CLOUD_PROJECT in .env.
EOF

echo "Project: $project_id"
echo "Principal: $principal"
echo "Checking active gcloud account…"
active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1)"
if [[ -z "$active_account" ]]; then
  echo "Sign in to gcloud first. Handoff written to $handoff." >&2
  exit 1
fi
echo "Active account: $active_account"

failed=0
echo "Enabling Vertex AI API…"
if gcloud services enable aiplatform.googleapis.com --project "$project_id" --quiet; then
  echo "Vertex AI API enabled."
else
  echo "Could not enable Vertex AI API. An administrator needs serviceusage.services.enable." >&2
  failed=1
fi

echo "Granting the app principal Vertex AI User…"
if gcloud projects add-iam-policy-binding "$project_id" \
    --member="$principal" --role=roles/aiplatform.user --condition=None --quiet >/dev/null; then
  echo "roles/aiplatform.user granted."
else
  echo "Could not grant roles/aiplatform.user. An administrator must grant it." >&2
  failed=1
fi

echo "Granting Service Usage Consumer for the local ADC quota project…"
if gcloud projects add-iam-policy-binding "$project_id" \
    --member="$principal" --role=roles/serviceusage.serviceUsageConsumer --condition=None --quiet >/dev/null; then
  echo "roles/serviceusage.serviceUsageConsumer granted."
else
  echo "Could not grant Service Usage Consumer. An administrator must grant it." >&2
  failed=1
fi

echo "Checking whether the principal can use enabled services…"
echo "Model Garden terms and organization policy must be checked in the Cloud Console by an authorized person."
echo "Exact follow-up: $handoff"

if [[ $failed -ne 0 ]]; then
  echo "Project setup is incomplete; share $handoff with the Google Cloud administrator." >&2
  exit 1
fi

echo "Project-level steps completed. The user must still sign in locally and test the chosen model."

