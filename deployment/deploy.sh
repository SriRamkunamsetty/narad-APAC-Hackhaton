#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NARAD — One-command Cloud Run deployment script
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated: gcloud auth login
#   2. A GCP project with billing enabled
#   3. A free Gemini API key from https://aistudio.google.com/app/apikey
#
# Secrets (Gemini key, Maps key, admin API key) are stored in Secret Manager,
# not passed as plain Cloud Build substitutions — substitutions can appear in
# Cloud Build logs/history, which is not appropriate for real credentials.
#
# Usage:
#   chmod +x deployment/deploy.sh
#   ./deployment/deploy.sh YOUR_PROJECT_ID YOUR_GEMINI_API_KEY [REGION] [GOOGLE_MAPS_API_KEY]
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> <GEMINI_API_KEY> [REGION] [GOOGLE_MAPS_API_KEY]}"
GEMINI_API_KEY="${2:?Usage: ./deploy.sh <PROJECT_ID> <GEMINI_API_KEY> [REGION] [GOOGLE_MAPS_API_KEY]}"
REGION="${3:-us-central1}"
GOOGLE_MAPS_API_KEY="${4:-}"
SERVICE_NAME="narad-city-ai"
REPO_NAME="narad-repo"

echo "🚀 NARAD Deployment Starting"
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"
echo ""

echo "📌 Setting active project..."
gcloud config set project "$PROJECT_ID"

echo "📌 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "📌 Granting BigQuery permissions to the Cloud Run compute service account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/bigquery.dataEditor" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/bigquery.jobUser" --quiet

echo "📌 Storing secrets in Secret Manager (not passed as plain build args)..."
create_or_update_secret() {
  local name=$1
  local value=$2
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --quiet
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic --quiet
  fi
}

create_or_update_secret "narad-gemini-key" "$GEMINI_API_KEY"
create_or_update_secret "narad-maps-key" "${GOOGLE_MAPS_API_KEY:-unset-no-live-traffic}"

# Generate a random admin API key if one doesn't already exist as a secret —
# this is the credential hospital staff / operators will use to submit data
# and trigger parliament sessions. It is NEVER baked into the frontend build.
if gcloud secrets describe "narad-admin-key" >/dev/null 2>&1; then
  echo "   (narad-admin-key already exists — leaving it unchanged; rotate manually if needed)"
else
  ADMIN_KEY=$(openssl rand -hex 24)
  create_or_update_secret "narad-admin-key" "$ADMIN_KEY"
  echo ""
  echo "   🔑 Generated admin access key (SAVE THIS SECURELY — shown only once):"
  echo "   ${ADMIN_KEY}"
  echo "   Distribute this to authorized operators/hospital staff through a"
  echo "   secure channel. It's entered into the dashboard per-session, never"
  echo "   stored in the app's code."
  echo ""
fi

echo "📌 Granting Secret Manager access to the Cloud Run compute service account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/secretmanager.secretAccessor" --quiet

echo "📌 Creating Artifact Registry repo (if not exists)..."
gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="NARAD container images" \
  --quiet 2>/dev/null || echo "   (repo already exists, continuing)"

echo "📌 Submitting build + deploy via Cloud Build..."
gcloud builds submit \
  --config=deployment/cloudbuild.yaml \
  --substitutions="_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION},_REPO=${REPO_NAME}" \
  .

echo ""
echo "✅ Deployment complete!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
echo "🌐 NARAD is live at: $SERVICE_URL"
echo ""
echo "   Try it now:"
echo "   curl $SERVICE_URL/api/health"
echo "   curl $SERVICE_URL/api/diagnostics/bigquery"
echo ""
echo "   ⚠️  IMPORTANT: update ALLOWED_ORIGINS to include $SERVICE_URL for"
echo "   stricter CORS if you plan to call the API from any other origin:"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION \\"
echo "     --update-env-vars=ALLOWED_ORIGINS=$SERVICE_URL"
