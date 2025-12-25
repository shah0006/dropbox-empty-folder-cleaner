#!/usr/bin/env python3
"""
Dropbox OAuth Authorization Helper
===================================
Run this script once to authorize the app and save a refresh token.
The refresh token will be used to automatically get new access tokens.

Usage:
    python3 dropbox_auth.py
"""

import os
import webbrowser
from dotenv import load_dotenv, set_key

try:
    import dropbox
    from dropbox import DropboxOAuth2FlowNoRedirect
except ImportError:
    print("Error: dropbox package not installed.")
    print("Run: pip3 install dropbox python-dotenv")
    exit(1)


def main():
    load_dotenv()
    
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    
    if not app_key or not app_secret:
        print("Error: DROPBOX_APP_KEY and DROPBOX_APP_SECRET must be set in .env")
        exit(1)
    
    print("\n" + "=" * 60)
    print("  DROPBOX AUTHORIZATION SETUP")
    print("=" * 60)
    print("""
This will authorize the app to access your Dropbox account.
You'll get a refresh token that works long-term (no more expiring tokens!).
""")
    
    # Start OAuth2 flow
    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type='offline'  # This gives us a refresh token
    )
    
    authorize_url = auth_flow.start()
    
    print("1. Opening your browser to authorize the app...")
    print(f"\n   If the browser doesn't open, visit this URL:\n   {authorize_url}\n")
    
    # Try to open browser
    try:
        webbrowser.open(authorize_url)
    except:
        pass
    
    print("2. Click 'Allow' to grant access")
    print("3. Copy the authorization code and paste it below\n")
    
    auth_code = input("Enter the authorization code: ").strip()
    
    if not auth_code:
        print("Error: No authorization code provided")
        exit(1)
    
    try:
        oauth_result = auth_flow.finish(auth_code)
    except Exception as e:
        print(f"\nError: Could not complete authorization - {e}")
        exit(1)
    
    # Save the refresh token to .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Update .env with refresh token
    set_key(env_path, "DROPBOX_REFRESH_TOKEN", oauth_result.refresh_token)
    set_key(env_path, "DROPBOX_ACCESS_TOKEN", oauth_result.access_token)
    
    print("\n" + "=" * 60)
    print("  ✅ AUTHORIZATION SUCCESSFUL!")
    print("=" * 60)
    print(f"""
Your refresh token has been saved to .env

You can now run the empty folder cleaner:
    python3 dropbox_empty_folder_cleaner.py --dry-run

The app will automatically refresh tokens as needed.
""")
    
    # Verify it works
    try:
        dbx = dropbox.Dropbox(
            oauth2_access_token=oauth_result.access_token,
            oauth2_refresh_token=oauth_result.refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        account = dbx.users_get_current_account()
        print(f"Connected as: {account.name.display_name} ({account.email})")
    except Exception as e:
        print(f"Warning: Could not verify connection - {e}")


if __name__ == "__main__":
    main()

