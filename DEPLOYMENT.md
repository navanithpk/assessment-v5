# Deployment Guide - Google Cloud Run

This guide walks you through deploying the Assessment Platform to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: Sign up at https://cloud.google.com
2. **Google Cloud SDK**: Install from https://cloud.google.com/sdk/docs/install
3. **Docker**: Install from https://docs.docker.com/get-docker/

## Step 1: Set Up Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create assessment-platform-prod --name="Assessment Platform"

# Set as active project
gcloud config set project assessment-platform-prod

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

## Step 2: Create Cloud SQL Database

```bash
# Create PostgreSQL instance (this takes ~10 minutes)
gcloud sql instances create assessment-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create assessment_prod \
  --instance=assessment-db

# Create database user
gcloud sql users create django_user \
  --instance=assessment-db \
  --password=YOUR_SECURE_DB_PASSWORD
```

## Step 3: Set Up Secrets

```bash
# Generate Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Store secrets in Secret Manager
echo -n "your-generated-secret-key" | gcloud secrets create django-secret-key --data-file=-
echo -n "your-google-oauth-client-id" | gcloud secrets create google-oauth-client-id --data-file=-
echo -n "your-google-oauth-client-secret" | gcloud secrets create google-oauth-client-secret --data-file=-

# Create DATABASE_URL secret
# Format: postgresql://USER:PASSWORD@//cloudsql/PROJECT:REGION:INSTANCE/DATABASE
echo -n "postgresql://django_user:YOUR_SECURE_DB_PASSWORD@//cloudsql/assessment-platform-prod:us-central1:assessment-db/assessment_prod" | \
  gcloud secrets create database-url --data-file=-
```

## Step 4: Test Docker Build Locally

```bash
# Build the Docker image
docker build -t assessment-platform .

# Test locally (using SQLite)
docker run -p 8080:8080 \
  -e SECRET_KEY="test-secret-key" \
  -e DEBUG="True" \
  assessment-platform

# Visit http://localhost:8080 to verify
```

## Step 5: Deploy to Cloud Run

### Option A: Using Cloud Build (Automated)

```bash
# Update cloudbuild.yaml with your Cloud SQL instance connection
# Replace $_CLOUDSQL_INSTANCE value: PROJECT_ID:REGION:INSTANCE_NAME

# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

# The service will be available at:
# https://assessment-platform-HASH-uc.a.run.app
```

### Option B: Manual Deployment

```bash
# Build and push image
gcloud builds submit --tag gcr.io/assessment-platform-prod/assessment-platform

# Deploy to Cloud Run
gcloud run deploy assessment-platform \
  --image gcr.io/assessment-platform-prod/assessment-platform \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --add-cloudsql-instances assessment-platform-prod:us-central1:assessment-db \
  --set-secrets=SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest
```

## Step 6: Update Environment Variables

```bash
# Get your Cloud Run service URL
gcloud run services describe assessment-platform \
  --region us-central1 \
  --format 'value(status.url)'

# Update allowed hosts (add your .run.app domain)
gcloud run services update assessment-platform \
  --region us-central1 \
  --update-env-vars CLOUD_RUN_SERVICE_NAME=assessment-platform
```

## Step 7: Run Database Migrations

```bash
# Get Cloud SQL proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Start proxy in background
./cloud_sql_proxy -instances=assessment-platform-prod:us-central1:assessment-db=tcp:5432 &

# Run migrations locally through proxy
export DATABASE_URL="postgresql://django_user:YOUR_SECURE_DB_PASSWORD@127.0.0.1:5432/assessment_prod"
python manage.py migrate

# Or run migrations via Cloud Run job
gcloud run jobs create assessment-migrate \
  --image gcr.io/assessment-platform-prod/assessment-platform \
  --region us-central1 \
  --add-cloudsql-instances assessment-platform-prod:us-central1:assessment-db \
  --set-secrets=DATABASE_URL=database-url:latest,SECRET_KEY=django-secret-key:latest \
  --command python,manage.py,migrate

gcloud run jobs execute assessment-migrate --region us-central1
```

## Step 8: Create Superuser

```bash
# Using Cloud SQL proxy
export DATABASE_URL="postgresql://django_user:YOUR_SECURE_DB_PASSWORD@127.0.0.1:5432/assessment_prod"
python manage.py createsuperuser

# Or use Cloud Run job
gcloud run jobs create create-superuser \
  --image gcr.io/assessment-platform-prod/assessment-platform \
  --region us-central1 \
  --add-cloudsql-instances assessment-platform-prod:us-central1:assessment-db \
  --set-secrets=DATABASE_URL=database-url:latest,SECRET_KEY=django-secret-key:latest \
  --command python,manage.py,createsuperuser,--noinput,--username=admin,--email=admin@example.com

# You'll need to set password manually via Django shell
```

## Step 9: Configure OAuth Redirect URIs

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Find your OAuth 2.0 Client ID
3. Add authorized redirect URIs:
   ```
   https://YOUR-SERVICE-NAME-HASH-uc.a.run.app/accounts/google/callback/
   ```

## Post-Deployment Checklist

- [ ] Test login functionality
- [ ] Create school admin using management command
- [ ] Test test creation and student assignment
- [ ] Verify PDF export works
- [ ] Test student test-taking flow
- [ ] Check analytics dashboards
- [ ] Set up Cloud Monitoring alerts
- [ ] Configure Cloud Storage for media files (if needed)
- [ ] Set up automated backups for Cloud SQL

## Monitoring and Logs

```bash
# View logs
gcloud run services logs read assessment-platform --region us-central1

# Stream logs
gcloud run services logs tail assessment-platform --region us-central1

# Monitor service health
gcloud run services describe assessment-platform --region us-central1
```

## Updating the Application

```bash
# Make code changes, then redeploy
gcloud builds submit --config cloudbuild.yaml

# Cloud Run will automatically route traffic to new revision
```

## Cost Optimization

**Free Tier Limits:**
- Cloud Run: 2 million requests/month
- Cloud SQL: db-f1-micro instance
- Container Registry: 0.5 GB storage

**Estimated Monthly Cost (minimal usage):**
- Cloud Run: ~$0-5
- Cloud SQL (db-f1-micro): ~$7-10
- Storage: ~$1-2
- **Total: ~$8-17/month**

To reduce costs:
1. Stop Cloud SQL instance when not in use
2. Use Cloud Run minimum instances = 0
3. Enable Cloud SQL automatic backups only if needed

## Troubleshooting

### Database Connection Errors
```bash
# Verify Cloud SQL connection
gcloud sql instances describe assessment-db

# Check Cloud Run has proper IAM permissions
gcloud projects add-iam-policy-binding assessment-platform-prod \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/cloudsql.client
```

### Static Files Not Loading
```bash
# Verify collectstatic ran during build
docker build -t test . --progress=plain 2>&1 | grep collectstatic

# Check STATIC_URL and STATIC_ROOT settings
```

### 502 Bad Gateway
- Check container logs for Python errors
- Verify PORT environment variable is 8080
- Check Cloud Run memory limits (increase if needed)

## Security Recommendations

1. **Enable Cloud Armor** for DDoS protection
2. **Use VPC Connector** for private Cloud SQL access
3. **Enable Cloud Audit Logs** for compliance
4. **Set up Cloud Monitoring alerts** for errors
5. **Use Secret Manager** for all sensitive data (already configured)
6. **Enable HTTPS only** (default on Cloud Run)
7. **Restrict Cloud SQL to Cloud Run only** using private IP

## Support

For issues specific to:
- **Django**: Check `assessment_v3/settings.py`
- **Docker**: Review `Dockerfile`
- **Cloud Run**: Check `cloudbuild.yaml`
- **Database**: Verify Cloud SQL connection string

## Maintenance

### Backup Database
```bash
gcloud sql backups create --instance=assessment-db
```

### Restore Database
```bash
gcloud sql backups restore BACKUP_ID --backup-instance=assessment-db --restore-instance=assessment-db
```

### Scale Cloud Run
```bash
gcloud run services update assessment-platform \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4 \
  --max-instances 10
```
