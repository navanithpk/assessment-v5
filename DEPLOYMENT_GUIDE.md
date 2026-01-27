# Deployment Guide - Assessment Platform v3

## ⚠️ Important: Firebase + Colab Is NOT Suitable

**Do NOT attempt to host this on Firebase + Google Colab**. Here's why:

### Why Firebase + Colab Won't Work:
- **Google Colab**: Designed for notebooks, not web servers. Sessions timeout, no persistent storage, database gets wiped
- **Firebase Hosting**: Only serves static files (HTML/CSS/JS), cannot run Django backend
- **Firebase Functions**: Doesn't support Django (only Node.js/limited Python)
- **No Database**: Firebase doesn't support SQLite or Django ORM directly

---

## Recommended Hosting Options

### ⭐ Option 1: Railway (Easiest - Recommended)

**Why Railway?**
- One-click Django deployment
- Free tier available ($5/month after)
- PostgreSQL database included
- Automatic HTTPS
- Git-based deployments

**Steps:**

1. **Install Railway CLI**:
```bash
npm i -g @railway/cli
```

2. **Login**:
```bash
railway login
```

3. **Initialize & Deploy**:
```bash
cd C:\Users\uniqu\Documents\ASSESSMENT-PLATFORM\assessment-v3
railway init
railway up
```

4. **Add PostgreSQL**:
```bash
railway add
# Select PostgreSQL from the list
```

5. **Set Environment Variables** (in Railway dashboard):
```
SECRET_KEY=your-random-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://... (auto-set by Railway)
```

6. **Deploy**:
```bash
git add .
git commit -m "Deploy to Railway"
git push
```

Railway will automatically:
- Detect Django
- Install dependencies from `requirements.txt`
- Run migrations
- Start gunicorn server

**Cost**: Free tier available, then ~$5/month

---

### Option 2: PythonAnywhere (Django-Specific)

**Steps:**

1. Sign up at https://www.pythonanywhere.com
2. Upload your project files
3. Create a virtual environment
4. Configure WSGI file
5. Set up static files
6. Reload web app

**Cost**: Free tier (limited), $5/month for full features

---

### Option 3: Render

**Steps:**

1. Sign up at https://render.com
2. Connect GitHub repository
3. Create new Web Service
4. Configure build command: `pip install -r requirements.txt && python manage.py migrate`
5. Configure start command: `gunicorn assessment_v3.wsgi:application`
6. Add PostgreSQL database

**Cost**: Free tier available

---

### Option 4: Google Cloud (If You Need Google Services)

**Use App Engine or Cloud Run, NOT Colab**

#### App Engine Setup:

1. **Install Google Cloud SDK**:
```bash
# Download from: https://cloud.google.com/sdk/docs/install
```

2. **Create `app.yaml`** (already included in project):
```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT assessment_v3.wsgi:application

env_variables:
  SECRET_KEY: "your-secret-key-here"
  DEBUG: "False"

automatic_scaling:
  min_instances: 1
  max_instances: 10
```

3. **Deploy**:
```bash
gcloud init
gcloud app deploy
```

**Cost**: Pay-as-you-go, starts at ~$7/month

---

## Production Configuration Checklist

Before deploying to ANY platform:

### 1. Update `settings.py`:

```python
import os
import dj_database_url

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['your-domain.com', '.railway.app', '.onrender.com']

# Database (for PostgreSQL)
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Middleware (add WhiteNoise for static files)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... rest of middleware
]
```

### 2. Install Production Dependencies:

Already included in `requirements.txt`:
- `gunicorn` - Production WSGI server
- `psycopg2-binary` - PostgreSQL adapter
- `whitenoise` - Static file serving
- `dj-database-url` - Database URL parsing

### 3. Collect Static Files:

```bash
python manage.py collectstatic
```

### 4. Security Settings:

```python
# settings.py additions for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

---

## Quick Start: Railway (5 Minutes)

**The fastest way to deploy:**

1. **Create Railway account**: https://railway.app
2. **Click "Start a New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Connect your repo** (or upload project)
5. **Add PostgreSQL database** from Railway dashboard
6. **Set environment variables**:
   - `SECRET_KEY`: Generate at https://djecrety.ir/
   - `DEBUG`: `False`
7. **Deploy** - Railway automatically detects Django and deploys

Your app will be live at: `https://your-app.railway.app`

---

## Database Migration

### From SQLite to PostgreSQL:

1. **Export data**:
```bash
python manage.py dumpdata > data.json
```

2. **Update settings.py** to use PostgreSQL

3. **Run migrations**:
```bash
python manage.py migrate
```

4. **Import data**:
```bash
python manage.py loaddata data.json
```

---

## Cost Comparison

| Platform | Free Tier | Paid Tier | Database | Best For |
|----------|-----------|-----------|----------|----------|
| **Railway** | Limited | $5/month | ✅ PostgreSQL | Quick deploy |
| **PythonAnywhere** | Yes (limited) | $5/month | ✅ MySQL | Beginners |
| **Render** | Yes | $7/month | ✅ PostgreSQL | Modern stack |
| **Google App Engine** | No | ~$7/month | ☑️ Cloud SQL | Google ecosystem |
| **Firebase + Colab** | ❌ | ❌ | ❌ | **NOT SUITABLE** |

---

## Support

For deployment issues, check:
- Railway docs: https://docs.railway.app/
- Django deployment checklist: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

---

**Recommendation**: Start with **Railway** for easiest deployment. It's designed for Django and handles most configuration automatically.
