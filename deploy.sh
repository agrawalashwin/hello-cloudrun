#!/bin/bash
set -e

REGION=us-central1
PROJECT_ID=$(gcloud config get-value project)
REPO=hello-app-repo
IMAGE_NAME=hello-app
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}"

echo "🔧 Building image and pushing to Artifact Registry..."
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --quiet || true

gcloud builds submit --tag $IMAGE

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $IMAGE_NAME \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated

