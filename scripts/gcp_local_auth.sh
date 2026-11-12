#!/usr/bin/env bash
set -euo pipefail

project_id=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) project_id="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
  echo "Usage: bash scripts/gcp_local_auth.sh --project YOUR_PROJECT_ID" >&2
  exit 2
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Google Cloud CLI is missing. Install it from https://cloud.google.com/sdk/docs/install first." >&2
  exit 1
fi

echo "This signs in the current computer to project: $project_id"
echo "Use this on the computer that will actually run RAISE Assistant."
gcloud auth application-default login

if gcloud auth application-default set-quota-project "$project_id"; then
  echo "Application Default Credentials quota project set."
else
  echo "Quota project could not be set. Ask the project administrator to confirm the user's serviceusage.services.use permission." >&2
fi

if gcloud auth application-default print-access-token >/dev/null; then
  echo "Local Google credentials are working."
else
  echo "Google sign-in did not produce usable Application Default Credentials." >&2
  exit 1
fi

echo "Set GOOGLE_CLOUD_PROJECT=$project_id in the app's .env file, then run ./doctor.sh."
echo "Cloud Shell login does not configure credentials on a different computer."

