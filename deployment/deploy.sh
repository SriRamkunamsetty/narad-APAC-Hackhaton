#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NARAD — One-command Cloud Run deployment script
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated: gcloud auth login
#   2. A GCP project with billing enabled
#   3. A free Gemini API key from https://aistudio.google.com/app/apikey
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
  --quiet

echo "📌 Creating Artifact Registry repo (if not exists)..."
gcloud artifacts repositories create "$REPO_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="NARAD container images" \
  --quiet 2>/dev/null || echo "   (repo already exists, continuing)"

echo "📌 Submitting build + deploy via Cloud Build..."
gcloud builds submit \
  --config=deployment/cloudbuild.yaml \
  --substitutions="_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION},_REPO=${REPO_NAME},_GEMINI_API_KEY=${GEMINI_API_KEY},_GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}" \
  .

echo ""
echo "✅ Deployment complete!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
echo "🌐 NARAD is live at: $SERVICE_URL"
echo ""
echo "   Try it now:"
echo "   curl $SERVICE_URL/api/health"
