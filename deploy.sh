#!/bin/bash
set -e

REGION=us-central1
PROJECT_ID=$(gcloud config get-value project)
REPO=hello-app-repo
SERVICE=hello-app
TAG=latest

# Full image path in Artifact Registry
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${TAG}"

echo "🔧 Ensuring Artifact Registry repo exists..."
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --quiet || true

echo "🔐 Configuring Docker credentials for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

echo "🐳 Building Docker image (uses local layer cache)..."
docker build \
  --tag $IMAGE \
  .

echo "📤 Pushing image to Artifact Registry..."
docker push $IMAGE

echo "🚀 Deploying to Cloud Run ($SERVICE) from prebuilt image..."
gcloud run deploy $SERVICE \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated
