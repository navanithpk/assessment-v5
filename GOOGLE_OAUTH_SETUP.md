# Google OAuth Setup Guide

## Error: "OAuth client was not found" (Error 401: invalid_client)

This error occurs because the Google OAuth credentials need to be properly configured in Google Cloud Console.

## Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a Project" → "New Project"
3. Name: "Lumen Assessment Platform"
4. Click "Create"

### 2. Enable Google+ API

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for "Google+ API"
3. Click on it and press **Enable**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (for testing with any Google account)
3. Click **Create**

**Fill in the form:**
- **App name:** Lumen
- **User support email:** Your email
- **App logo:** (Optional)
- **Authorized domains:** Leave blank for localhost testing
- **Developer contact email:** Your email
- Click **Save and Continue**

**Scopes:**
- Click **Add or Remove Scopes**
- Search and add:
  - `userinfo.email`
  - `userinfo.profile`
- Click **Save and Continue**

**Test users:** (For testing)
- Click **Add Users**
- Add your Gmail address
- Add any other test accounts
- Click **Save and Continue**

### 4. Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Web application**

**Fill in:**
- **Name:** Lumen Web Client
- **Authorized JavaScript origins:**
  - `http://localhost:8000`
  - `http://127.0.0.1:8000`
- **Authorized redirect URIs:**
  - `http://localhost:8000/accounts/google/callback/`
  - `http://127.0.0.1:8000/accounts/google/callback/`

4. Click **Create**
5. **Copy the Client ID and Client Secret** that appear

### 5. Update Django Settings

Update `assessment_v3/settings.py` with your new credentials:

```python
# Replace these values with your actual credentials from step 4
GOOGLE_OAUTH_CLIENT_ID = 'YOUR_CLIENT_ID_HERE'
GOOGLE_OAUTH_CLIENT_SECRET = 'YOUR_CLIENT_SECRET_HERE'
GOOGLE_OAUTH_REDIRECT_URI = 'http://127.0.0.1:8000/accounts/google/callback/'
```

### 6. Test the Setup

1. Restart Django server
2. Go to http://127.0.0.1:8000/accounts/login/
3. Click "Continue with Google"
4. Should redirect to Google login
5. Select account and authorize
6. Should redirect back and log you in

## For Production Deployment

When deploying to production (e.g., ngrok, Heroku, custom domain):

1. Add production domain to **Authorized JavaScript origins**
2. Add production callback URL to **Authorized redirect URIs**
3. Update `GOOGLE_OAUTH_REDIRECT_URI` in settings
4. Publish OAuth consent screen (move from Testing to Production)

**Example for production:**
```python
GOOGLE_OAUTH_REDIRECT_URI = 'https://yourdomain.com/accounts/google/callback/'
```

## Troubleshooting

### Error: "Access blocked: This app's request is invalid"
- Check that redirect URI exactly matches what's in Google Console
- Make sure there are no trailing slashes mismatches

### Error: "OAuth client was not found"
- Verify Client ID is correct
- Check that OAuth consent screen is configured
- Ensure Google+ API is enabled

### Error: "redirect_uri_mismatch"
- Check spelling and protocol (http vs https)
- Verify no trailing slash differences
- Add both localhost and 127.0.0.1 variants

## Alternative: Disable Google OAuth (Quick Fix)

If you want to disable Google OAuth temporarily:

1. Comment out the Google login button in `core/templates/registration/login.html`:
```html
<!--
<a href="{% url 'google_login' %}" style="display: block; text-decoration: none;">
  ...
</a>
-->
```

2. Or remove the routes from `core/urls.py`:
```python
# path("accounts/google/login/", google_oauth.get_google_auth_url, name="google_login"),
# path("accounts/google/callback/", google_oauth.google_auth_callback, name="google_callback"),
```

## Current Settings (Default - Will Not Work)

The current client ID in the code is a placeholder:
```
GOOGLE_OAUTH_CLIENT_ID = '952684622878-jsl3sbg0jfg1tvcfkm4ij3qj8ilmg79s.apps.googleusercontent.com'
GOOGLE_OAUTH_CLIENT_SECRET = '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'
```

**You MUST replace these with your own credentials from Google Cloud Console.**
