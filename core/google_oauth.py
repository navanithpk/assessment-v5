"""
Google OAuth Authentication Views
"""
import json
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
import os

# Configure OAuth flow
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for development

def get_google_auth_url(request):
    """Generate Google OAuth authorization URL"""
    # Build redirect URI dynamically based on request
    redirect_uri = build_redirect_uri(request)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=[
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
    )

    flow.redirect_uri = redirect_uri

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account'
    )

    # Store state and redirect URI in session for CSRF protection
    request.session['google_auth_state'] = state
    request.session['google_redirect_uri'] = redirect_uri

    return redirect(authorization_url)


def build_redirect_uri(request):
    """Build the redirect URI based on the current request"""
    # Get the host from the request
    host = request.get_host()

    # Determine protocol (http or https)
    if request.is_secure() or 'ngrok' in host:
        protocol = 'https'
    else:
        protocol = 'http'

    # Build the full redirect URI
    redirect_uri = f'{protocol}://{host}/accounts/google/callback/'

    return redirect_uri


def google_auth_callback(request):
    """Handle Google OAuth callback"""
    try:
        # Verify state for CSRF protection
        state = request.session.get('google_auth_state')
        redirect_uri = request.session.get('google_redirect_uri')

        if not state or not redirect_uri:
            return HttpResponseBadRequest('State or redirect URI verification failed')

        # Get authorization code
        code = request.GET.get('code')
        if not code:
            return HttpResponseBadRequest('No authorization code received')

        # Exchange code for tokens using the stored redirect URI
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            state=state
        )

        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)

        # Get user info from ID token
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )

        # Extract user information
        email = id_info.get('email')
        given_name = id_info.get('given_name', '')
        family_name = id_info.get('family_name', '')

        if not email:
            return HttpResponseBadRequest('No email in OAuth response')

        # Try to find existing user by email
        user = User.objects.filter(email=email).first()

        if not user:
            # Create new user
            username = email.split('@')[0]

            # Ensure username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=given_name,
                last_name=family_name
            )

            # Create UserProfile (will be updated later by user)
            from .models import UserProfile
            UserProfile.objects.create(
                user=user,
                role='student',  # Default role, can be changed later
                school=None  # Will need to be set by admin
            )

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Redirect based on user role
        from .views import redirect_after_login
        return redirect_after_login(user)

    except Exception as e:
        return HttpResponseBadRequest(f'Authentication failed: {str(e)}')
