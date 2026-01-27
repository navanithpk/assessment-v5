# Railway Deployment - Final Fix Steps

## Current Issues

You have TWO separate errors to fix:

### Error 1: Module Import Error (if this is happening)
```
ModuleNotFoundError: No module named 'dj_database_url'
```

### Error 2: Database Connection Error
```
connection to server at "postgres.railway.internal" failed: Connection refused
```

---

## Quick Fix (Do This Now)

### Step 1: Find Your Django Service Name

Open Railway dashboard:
```bash
railway open
```

Look for TWO services:
- **Postgres** - Your database (you're currently here)
- **assessment-v3** or **web** - Your Django app

Write down the exact name of your Django service.

### Step 2: Link to Your Django Service

Replace `<service-name>` with your actual Django service name:

```bash
cd C:\Users\uniqu\Documents\ASSESSMENT-PLATFORM\assessment-v3
railway link
```

When prompted, select your **Django app service** (NOT Postgres).

### Step 3: Set the Correct Database URL

Use the PUBLIC database URL (from the variables you showed):

```bash
railway variables --set DATABASE_URL="postgresql://postgres:LangkYvjiHKTEbBcFjhtxxNAOAfrWQVb@mainline.proxy.rlwy.net:51490/railway"
```

### Step 4: Redeploy

```bash
railway up --detach
```

### Step 5: Monitor Deployment

```bash
railway logs
```

Wait for successful deployment (3-4 minutes).

---

## Alternative: Use Railway Dashboard (Easier)

### Option A: Manual Variable Setting

1. Run:
```bash
railway open
```

2. Click on your **Django service** (the one that's NOT "Postgres")

3. Click **Variables** tab

4. Look for `DATABASE_URL`:
   - If it exists and says `postgres.railway.internal`, **delete it**
   - Click **+ New Variable**
   - Name: `DATABASE_URL`
   - Value: `postgresql://postgres:LangkYvjiHKTEbBcFjhtxxNAOAfrWQVb@mainline.proxy.rlwy.net:51490/railway`

5. Click **Deploy** button in the top right

### Option B: Reference Variable (Better)

1. In Railway dashboard, click your **Django service**

2. Go to **Variables** tab

3. Click **+ New Variable**

4. Click **Add Reference**

5. Select:
   - Service: **Postgres**
   - Variable: **DATABASE_PUBLIC_URL**

6. Name it: `DATABASE_URL`

7. Click **Deploy**

This automatically uses the public database URL.

---

## After Deployment Succeeds

### 1. Check Logs for Success

```bash
railway logs
```

Look for:
```
✓ Successfully installed all packages
✓ Starting gunicorn
✓ Listening at http://0.0.0.0:PORT
```

NO database errors.

### 2. Run Migrations

```bash
railway run python manage.py migrate
```

Expected output:
```
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying core.0001_initial... OK
  ...
  Applying core.0014_question_parts_config... OK
```

### 3. Collect Static Files

```bash
railway run python manage.py collectstatic --noinput
```

### 4. Create Superuser

```bash
railway run python manage.py createsuperuser
```

### 5. Get Your URL and Test

```bash
railway status
```

Visit: `https://[your-app].up.railway.app`

---

## Verify You're in the Right Service

Before running commands, verify you're in your Django service:

```bash
railway status
```

Should show:
```
Project: Lumen Analytics
Environment: production
Service: <your-django-service-name>  ← NOT "Postgres"
```

If it says "Service: Postgres", you're in the wrong service!

Switch with:
```bash
railway link
# Then select your Django service
```

---

## Understanding the Issue

Railway creates services in isolation:

```
Your Project
├── Postgres Service
│   ├── DATABASE_URL = postgres.railway.internal (internal only)
│   └── DATABASE_PUBLIC_URL = mainline.proxy.rlwy.net (public access)
│
└── Django Service (assessment-v3)
    ├── Can't access internal network by default
    └── Must use DATABASE_PUBLIC_URL from Postgres
```

**Solution**: Set Django's `DATABASE_URL` to use the **public** Postgres URL.

---

## Why This Happens

When you ran `railway add` for PostgreSQL, it created a **separate service**. Then when you ran `railway up`, it deployed your code but Railway didn't know which service you wanted to deploy to.

The fix is to:
1. **Link** your local project to your Django service
2. **Set** DATABASE_URL to use the public Postgres URL
3. **Redeploy**

---

## Troubleshooting

### "Module dj_database_url not found"

This shouldn't happen since it's in requirements.txt, but if it does:

1. Check Railway build logs:
```bash
railway logs
```

2. Look for the pip install section - ensure `dj-database-url` was installed

3. If not, the build might have failed early. Check for other errors first.

### "Connection refused" persists

You're still using the internal URL. Double-check:

```bash
railway variables
```

`DATABASE_URL` should show `mainline.proxy.rlwy.net`, NOT `postgres.railway.internal`.

### Can't find Django service

In Railway dashboard, you should see 2 services. If you only see Postgres:

1. Your Django app might not have deployed as a service
2. You might need to create a new service and deploy to it
3. Run `railway up` again after linking

---

## Quick Commands Summary

```bash
# 1. Link to Django service
railway link

# 2. Verify you're in the right service
railway status

# 3. Set database URL (replace with your actual values)
railway variables --set DATABASE_URL="postgresql://postgres:PASSWORD@mainline.proxy.rlwy.net:PORT/railway"

# 4. Deploy
railway up --detach

# 5. Monitor
railway logs

# 6. Run migrations
railway run python manage.py migrate

# 7. Create superuser
railway run python manage.py createsuperuser

# 8. Get URL
railway status
```

---

## Expected Final Result

After all fixes:

✅ Deployment succeeds without errors
✅ Database connection works
✅ App accessible at Railway URL
✅ Can login and use all features

---

**Start with the Railway Dashboard method (Option B) - it's the easiest and most reliable!**
