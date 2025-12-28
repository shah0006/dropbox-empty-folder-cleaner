#!/usr/bin/env python3
"""
Delete the 7 duplicate files from the source conflict folder.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import dropbox
from dropbox.exceptions import ApiError

def get_dropbox_client():
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    return dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret
    )

dbx = get_dropbox_client()
print("Connected to Dropbox\n")

# Files to delete (these are duplicates that exist in both source and destination)
source_base = "/Books (view-only conflicts 2025-12-19)"

files_to_delete = [
    "/Internal Medicine/Cardiology/General Cardiology/Cardiac Pharmacology/General Cardiology - Shortcut.lnk",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Cardiology Secrets, 4th Edition (Levine)/Chapter 41.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/009 Drug Therapeutics and Personalized Medicine.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Mayo Cardiology Textbook/12 Appendix.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/042 Risk Markers and the Primary Prevention of Cardiovascular Disease.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/037 Specific Arrhythmias, Diagnosis and Treatment.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/The Washington Manual Cardiology Subspecialty Consult, 3rd Edition (De Far, 2014).pdf",
]

print(f"Deleting {len(files_to_delete)} duplicate files from source folder...")
print("=" * 70)

deleted = 0
errors = 0

for rel_path in files_to_delete:
    full_path = source_base + rel_path
    try:
        dbx.files_delete_v2(full_path)
        print(f"✅ Deleted: {rel_path}")
        deleted += 1
    except ApiError as e:
        print(f"❌ Error deleting {rel_path}: {e}")
        errors += 1

print("\n" + "=" * 70)
print(f"COMPLETE: {deleted} files deleted, {errors} errors")
print("\nRemaining files in source folder are the 3 .lnk files you chose not to move.")


