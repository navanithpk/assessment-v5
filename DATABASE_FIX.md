# Database Connection Fix for Railway

## Problem

Your Django app is trying to connect to PostgreSQL using the **internal Railway network** (`postgres.railway.internal`), but the services aren't properly linked. This causes connection refused errors.

## Solution

You have TWO services in Railway:
1. **Postgres** - Your database
2. **assessment-v3** (or similar name) - Your Django app

Currently, you're in the Postgres service context. You need to switch to your Django service and set the correct database URL.

---

## Fix Steps

### Step 1: List All Services

```bash
railway service
```

This shows all services in your project. You should see:
- `Postgres` (database)
- `web` or `assessment-v3` (your Django app)

### Step 2: Switch to Your Django Service

If your Django service is called "web":
```bash
railway link
```

Then select your **Django app service** (NOT Postgres).

Or if you see the service name in the list:
```bash
railway service web
```

(Replace `web` with whatever your Django service is called)

### Step 3: Set the Correct Database URL

Once you're in your Django service, set the DATABASE_URL to use the **public URL**:

```bash
railway variables --set DATABASE_URL="postgresql://postgres:LangkYvjiHKTEbBcFjhtxxNAOAfrWQVb@mainline.proxy.rlwy.net:51490/railway"
```

This is the `DATABASE_PUBLIC_URL` from the Postgres service.

### Step 4: Verify Variables

Check that your Django service has the correct variables:

```bash
railway variables
```

Should show:
- `DATABASE_URL` - The public PostgreSQL URL
- `SECRET_KEY` - Your Django secret
- `DEBUG` - False

### Step 5: Redeploy

```bash
railway up --detach
```

---

## Alternative: Use Railway Dashboard

### Option 1: Set Variable in Dashboard

1. Open Railway dashboard:
```bash
railway open
```

2. Click on your **Django service** (not Postgres)

3. Go to **Variables** tab

4. Add/update `DATABASE_URL`:
```
postgresql://postgres:LangkYvjiHKTEbBcFjhtxxNAOAfrWQVb@mainline.proxy.rlwy.net:51490/railway
```

5. Click **Redeploy** button

### Option 2: Link Services Properly

In the Railway dashboard:

1. Click on your **Django service**
2. Go to **Settings** tab
3. Scroll to **Service Variables**
4. Click **+ New Variable**
5. Select **Reference** → Choose **Postgres** → Choose `DATABASE_PUBLIC_URL`
6. Name it `DATABASE_URL`
7. Redeploy

This automatically uses the public database URL.

---

## Verify Fix

After redeploying:

### 1. Check Logs

```bash
railway service web  # or your Django service name
railway logs
```

Look for:
```
✓ No database connection errors
✓ Starting gunicorn
✓ Deployment successful
```

### 2. Run Migrations

```bash
railway run python manage.py migrate
```

Should succeed without connection errors.

### 3. Get Your App URL

```bash
railway status
```

Then visit the URL in your browser.

---

## Understanding Railway Services

Railway projects can have multiple services:

```
Lumen Analytics (Project)
├── Postgres (Database Service)
│   └── DATABASE_PUBLIC_URL = public connection
│   └── DATABASE_URL = internal connection (for linked services)
│
└── web/assessment-v3 (Django Service)
    └── Needs DATABASE_URL set to Postgres public URL
```

**Key Point**: When services are in the same project but not properly linked, you must use the **public database URL** for connections.

---

## Quick Command Reference

```bash
# List all services
railway service

# Link to a specific service
railway link

# Switch to Django service
railway service <your-django-service-name>

# Set database URL (in Django service)
railway variables --set DATABASE_URL="<public-postgres-url>"

# Check current service context
railway status

# Check variables for current service
railway variables

# Redeploy
railway up --detach

# View logs
railway logs
```

---

## Expected Result

After fixing, you should see in logs:
```
✓ Installing dependencies
✓ Starting gunicorn
✓ Listening at: http://0.0.0.0:PORT
✓ No database errors
```

Then you can:
- Run migrations
- Create superuser
- Access your app

---

## Database URL Format

**Internal URL** (doesn't work from Django service):
```
postgresql://postgres:PASSWORD@postgres.railway.internal:5432/railway
```

**Public URL** (works from anywhere):
```
postgresql://postgres:PASSWORD@mainline.proxy.rlwy.net:51490/railway
```

Use the **public URL** for your Django service.

---

## Need More Help?

If this doesn't work:

1. **Take a screenshot** of Railway dashboard showing both services
2. **Run these commands** and share output:
```bash
railway service
railway status
railway variables
```

3. **Check deployment logs**:
```bash
railway logs
```
