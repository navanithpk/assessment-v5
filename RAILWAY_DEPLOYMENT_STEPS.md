# Railway Deployment - Manual Steps

## ✅ Completed Automatically:
1. ✅ Railway CLI installed
2. ✅ settings.py updated for production
3. ✅ requirements.txt updated with dependencies
4. ✅ .gitignore created
5. ✅ Git repository committed

---

## 🟡 Next Steps - DO THESE MANUALLY:

### Step 6: Login to Railway

Open your **Command Prompt** or **PowerShell** in the project directory and run:

```bash
cd C:\Users\uniqu\Documents\ASSESSMENT-PLATFORM\assessment-v3
railway login
```

This will:
- Open your browser
- Ask you to sign up/login with GitHub (recommended) or email
- Authorize the CLI

**Result**: You'll see "Logged in as [your-name]"

---

### Step 7: Create Railway Project

After logging in, run:

```bash
railway init
```

You'll be asked:
- **"What would you like to name your project?"** → Type: `assessment-platform-v3` (or your preferred name)
- **"Would you like to link to an existing project?"** → Select: **Create new project**

**Result**: You'll see "Created project assessment-platform-v3"

---

### Step 8: Add PostgreSQL Database

Run:

```bash
railway add
```

- Select: **PostgreSQL** from the list
- Wait for provisioning (30 seconds)

**Result**: PostgreSQL database is now linked to your project

---

### Step 9: Set Environment Variables

Railway automatically sets `DATABASE_URL` for PostgreSQL. Now set the SECRET_KEY:

```bash
railway variables --set SECRET_KEY="your-random-secret-key-here"
railway variables --set DEBUG="False"
```

**Generate a secure SECRET_KEY** by running this Python command:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and use it in the command above.

**Example**:
```bash
railway variables --set SECRET_KEY="django-insecure-abc123xyz789randomkey"
railway variables --set DEBUG="False"
```

---

### Step 10: Deploy to Railway

Deploy your application:

```bash
railway up
```

This will:
- Upload your code
- Install dependencies from requirements.txt
- Start gunicorn server

**Wait**: This takes 2-3 minutes. You'll see build logs.

**Result**: "Deployment successful" with a URL like `https://assessment-platform-v3.railway.app`

---

### Step 11: Run Database Migrations

Once deployed, run migrations on the Railway server:

```bash
railway run python manage.py migrate
```

**Result**: You'll see:
```
Running migrations:
  Applying core.0011_pdfimportsession... OK
  Applying core.0012_processedpdf... OK
  Applying core.0013_answerspace... OK
  Applying core.0014_question_parts_config... OK
```

---

### Step 12: Collect Static Files

```bash
railway run python manage.py collectstatic --noinput
```

**Result**: Static files copied to staticfiles/ directory

---

### Step 13: Create Superuser

Create your admin account:

```bash
railway run python manage.py createsuperuser
```

You'll be prompted for:
- Username: (your choice)
- Email: (your email)
- Password: (secure password)

---

### Step 14: Get Your Application URL

```bash
railway status
```

Or open the Railway dashboard:

```bash
railway open
```

This opens your project in the Railway web dashboard where you can see:
- Your app URL (e.g., `https://assessment-platform-v3.railway.app`)
- Deployment logs
- Database details
- Environment variables

---

## 🎉 Your App is Live!

Visit your URL: `https://[your-app].railway.app`

**Login** with the superuser credentials you created in Step 13.

---

## Troubleshooting

### If deployment fails:

1. **Check logs**:
```bash
railway logs
```

2. **Verify environment variables**:
```bash
railway variables
```

Should show:
- `SECRET_KEY`
- `DEBUG=False`
- `DATABASE_URL` (automatically set)

3. **Redeploy**:
```bash
railway up --detach
```

### If migrations fail:

```bash
railway run python manage.py migrate --run-syncdb
```

### If static files don't load:

```bash
railway run python manage.py collectstatic --noinput --clear
```

---

## Managing Your App

### View logs:
```bash
railway logs
```

### Open Railway dashboard:
```bash
railway open
```

### SSH into your container:
```bash
railway run bash
```

### Update code:
```bash
git add .
git commit -m "Update message"
railway up
```

---

## Cost Information

Railway costs:
- **$5/month** for the Hobby plan (includes $5 credit)
- **Free trial**: $5 credit to start
- PostgreSQL included in the price

Your app usage:
- Small Django app: ~$0.50-$2/month
- PostgreSQL: Included
- Bandwidth: Usually free tier

**Total expected cost**: ~$5/month (first month free with trial credit)

---

## Next Steps After Deployment

1. **Import data**: Use Django admin to create schools, subjects, grades
2. **Create users**: Add teachers and students
3. **Test features**: Create tests, import PDFs
4. **Custom domain** (optional): Add your own domain in Railway dashboard

---

## Need Help?

- Railway docs: https://docs.railway.app/
- Railway Discord: https://discord.gg/railway
- Your deployment: `railway open` → View logs
