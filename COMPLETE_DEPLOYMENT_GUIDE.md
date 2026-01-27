# Complete Railway Deployment - Final Steps

## Current Status

✅ **Django app deployed successfully**
✅ **All dependencies installed**
⚠️ **Need to complete setup**

---

## The Situation

When you ran `railway up`, it created a NEW service for your Django app. But your CLI is still linked to the **Postgres** service, so you can't run management commands on the Django app.

You need to:
1. Link to your Django service
2. Set the correct DATABASE_URL
3. Run migrations
4. Create superuser

---

## Complete Fix - Use Railway Dashboard (Recommended)

### Step 1: Open Railway Dashboard

```bash
railway open
```

### Step 2: Find Your Django Service

You should now see **TWO services**:
- **Postgres** (database)
- **assessment-v3-production** or **web** (your Django app)

Click on your **Django service** (NOT Postgres).

### Step 3: Add Database Variable

In your Django service:

1. Click **"Variables"** tab
2. Click **"+ New Variable"**
3. Click **"Add Reference"**
4. Select:
   - Service: **Postgres**
   - Variable: **DATABASE_PUBLIC_URL**
5. Name it: `DATABASE_URL`
6. Click **Add**

### Step 4: Verify Other Variables

Make sure these exist in your Django service:
- `SECRET_KEY` - Should already be there
- `DEBUG` - Should be `False`
- `DATABASE_URL` - Just added above

If SECRET_KEY or DEBUG are missing, add them:
- SECRET_KEY: `pqnnh0sknl6tc8!h*m1^x7)46t6q@qh=4=z8w!dne0`
- DEBUG: `False`

### Step 5: Redeploy (if needed)

If you added/changed variables, click **"Deploy"** in top right.

Wait for deployment to complete (~2 minutes).

### Step 6: Generate a Domain

Still in your Django service:

1. Click **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**

This creates your public URL like: `https://assessment-v3-production.up.railway.app`

### Step 7: Run Migrations via Dashboard

Option A - Use Railway CLI with correct service:

First, find your service ID:
- In dashboard, your Django service URL will show the service ID
- Or note the exact service name

Then in terminal:
```bash
railway link
# Select your Django service (assessment-v3-production or whatever it's called)

railway run python manage.py migrate
```

Option B - Use Railway Web Terminal:

1. In your Django service dashboard
2. Look for **"..." menu** or **"Actions"**
3. Select **"Open Terminal"** or **"Shell"**
4. Run:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## Alternative: CLI Method (If You Know Service Name)

### Find Service Name

In Railway dashboard, look at the exact name of your Django service.

### Link to Django Service

```bash
cd C:\Users\uniqu\Documents\ASSESSMENT-PLATFORM\assessment-v3
railway link
```

When prompted, select your **Django service** (NOT Postgres).

### Verify You're in the Right Service

```bash
railway status
```

Should show:
```
Service: assessment-v3-production  (or your Django service name)
```

NOT "Service: Postgres"

### Set Environment Variables

```bash
railway variables --set DATABASE_URL="postgresql://postgres:LangkYvjiHKTEbBcFjhtxxNAOAfrWQVb@mainline.proxy.rlwy.net:51490/railway"
```

### Run Migrations

```bash
railway run python manage.py migrate --run-syncdb
```

### Collect Static Files

```bash
railway run python manage.py collectstatic --noinput
```

### Create Superuser

```bash
railway run python manage.py createsuperuser
```

Follow prompts to create admin account.

---

## Get Your App URL

### Method 1: Dashboard

In Railway dashboard → Your Django service → Settings → Networking → Domain

### Method 2: CLI

```bash
railway status
```

Look for the deployment URL.

---

## Test Your App

1. Visit your Railway URL (e.g., `https://assessment-v3-production.up.railway.app`)
2. You should see the login page
3. Login with your superuser credentials
4. Go to `/admin/` to access Django admin
5. Create a school
6. Test all features

---

## Troubleshooting

### "Service not found"

You're linked to the wrong service. Run:
```bash
railway link
```

Select your Django service.

### "Could not translate host name postgres.railway.internal"

Your Django service doesn't have the correct DATABASE_URL.

Fix:
1. Go to Railway dashboard
2. Click your Django service
3. Variables tab
4. Update DATABASE_URL to use `mainline.proxy.rlwy.net` (public URL)

### "No module named 'dj_database_url'" (local error)

This is a local error, not Railway. Install locally:
```bash
pip install dj-database-url psycopg2-binary
```

Then try again.

### App shows 500 error

Check logs:
```bash
# Make sure you're linked to Django service first
railway logs
```

Look for Python errors.

Common fixes:
- Run migrations
- Collect static files
- Check DATABASE_URL is correct

---

## Summary of What You Need

### In Railway Dashboard (Your Django Service):

**Variables:**
- `DATABASE_URL` = Reference to Postgres → DATABASE_PUBLIC_URL
- `SECRET_KEY` = Your secret key
- `DEBUG` = False

**Settings:**
- Domain generated (for public access)
- Service deployed and running

**Migrations:**
- Run via dashboard terminal or CLI
- `python manage.py migrate`
- `python manage.py collectstatic --noinput`
- `python manage.py createsuperuser`

---

## Quick Commands (After Linking to Django Service)

```bash
# Link to Django service
railway link
# → Select your Django service

# Verify
railway status

# Run migrations
railway run python manage.py migrate

# Collect static
railway run python manage.py collectstatic --noinput

# Create admin
railway run python manage.py createsuperuser

# View logs
railway logs

# Get URL
railway status
```

---

## Next Steps After Setup

1. Visit your app URL
2. Login as superuser
3. Create a school in Django admin
4. Add teacher and student accounts
5. Test features
6. Enjoy your deployed app!

---

**Cost:** $5/month after free trial

**Your app is ready - just complete the migrations and setup!**
