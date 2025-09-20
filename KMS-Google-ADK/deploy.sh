#!/bin/bash

# KMS-Google-ADK Deployment Script for Google Cloud Platform
# This script deploys the application to Cloud Run with Cloud Storage integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="nice-stack-472707-e4"
REGION="us-central1"
SERVICE_NAME="kms-google-adk"
BUCKET_NAME="kms-adk-bucket-$(date +%s)"
DB_INSTANCE_NAME="kms-db-instance"

echo -e "${BLUE}🚀 Starting KMS-Google-ADK Deployment to GCP${NC}"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  Not authenticated with gcloud. Please run: gcloud auth login${NC}"
    exit 1
fi

# Get project ID if not set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project)
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}❌ No project ID set. Please run: gcloud config set project YOUR_PROJECT_ID${NC}"
        exit 1
    fi
fi

# Generate bucket name if not set
if [ -z "$BUCKET_NAME" ]; then
    BUCKET_NAME="kms-documents-${PROJECT_ID}-$(date +%s)"
fi

echo -e "${GREEN}✅ Using Project: ${PROJECT_ID}${NC}"
echo -e "${GREEN}✅ Using Region: ${REGION}${NC}"
echo -e "${GREEN}✅ Using Bucket: ${BUCKET_NAME}${NC}"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${BLUE}📋 Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    storage.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com

# Create Cloud Storage bucket
echo -e "${BLUE}🪣 Creating Cloud Storage bucket...${NC}"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME || echo "Bucket might already exist"

# Create Cloud SQL instance (if it doesn't exist)
echo -e "${BLUE}🗄️  Setting up Cloud SQL instance...${NC}"
gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=kms-password-123 \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup \
    --enable-bin-log \
    --quiet || echo "Instance might already exist"

# Create database
echo -e "${BLUE}📊 Creating database...${NC}"
gcloud sql databases create kms_db --instance=$DB_INSTANCE_NAME --quiet || echo "Database might already exist"

# Build and push Docker image
echo -e "${BLUE}🐳 Building and pushing Docker image...${NC}"
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Deploy to Cloud Run
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,DB_INSTANCE=$DB_INSTANCE_NAME" \
    --add-cloudsql-instances $PROJECT_ID:$REGION:$DB_INSTANCE_NAME

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "=================================================="
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}🪣 Storage Bucket: gs://${BUCKET_NAME}${NC}"
echo -e "${GREEN}🗄️  Database Instance: ${DB_INSTANCE_NAME}${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Upload sample documents to the bucket:"
echo "   gsutil -m cp sample_notes/*.md gs://$BUCKET_NAME/notes/"
echo ""
echo "2. Test the API:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "3. Access the web interface:"
echo "   Open $SERVICE_URL in your browser"
