#!/usr/bin/env python3
"""Quick script to complete OAuth with the authorization code."""

import os
from dotenv import load_dotenv, set_key

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

load_dotenv()

app_key = os.getenv("DROPBOX_APP_KEY")
app_secret = os.getenv("DROPBOX_APP_SECRET")

# The authorization code from the user
auth_code = "QO4W5Xfq-NkAAAAAAAACGxkzoSLypm8-1P1vg31LEiA"

print("Exchanging authorization code for tokens...")

auth_flow = DropboxOAuth2FlowNoRedirect(
    app_key,
    app_secret,
    token_access_type='offline'
)

# We need to call start() to initialize the flow, even though we already have the code
auth_flow.start()

try:
    oauth_result = auth_flow.finish(auth_code)
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    set_key(env_path, "DROPBOX_REFRESH_TOKEN", oauth_result.refresh_token)
    set_key(env_path, "DROPBOX_ACCESS_TOKEN", oauth_result.access_token)
    
    print(f"✅ Success! Tokens saved to .env")
    print(f"   Refresh token: {oauth_result.refresh_token[:20]}...")
    
    # Verify
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=oauth_result.refresh_token,
        app_key=app_key,
        app_secret=app_secret
    )
    account = dbx.users_get_current_account()
    print(f"   Connected as: {account.name.display_name}")
    
except Exception as e:
    print(f"❌ Error: {e}")

