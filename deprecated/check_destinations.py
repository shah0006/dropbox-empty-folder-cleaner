#!/usr/bin/env python3
"""
Check if specific files exist in the destination Books folder.
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

# Files to check (relative paths from source)
source_files = [
    "/Anesthesia/Videos (D) - Shortcut.lnk",
    "/Deleted/Miscellaneous/Downloads - Shortcut.lnk",
    "/Internal Medicine/Cardiology/General Cardiology/Cardiac Pharmacology/General Cardiology - Shortcut.lnk",
    "/Anatomy and Physiology/Netter/Netter's Illustrated Human Pathology, Updated Edition (Buja, 2014).pdf - Shortcut.lnk",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Cardiology Secrets, 4th Edition (Levine)/Chapter 41.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/009 Drug Therapeutics and Personalized Medicine.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Mayo Cardiology Textbook/12 Appendix.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/042 Risk Markers and the Primary Prevention of Cardiovascular Disease.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/Braunwald/Braunwald's Heart Disease, 10th Edition/037 Specific Arrhythmias, Diagnosis and Treatment.pdf",
    "/Internal Medicine/Cardiology/General Cardiology/General Textbooks/The Washington Manual Cardiology Subspecialty Consult, 3rd Edition (De Far, 2014).pdf",
]

source_base = "/Books (view-only conflicts 2025-12-19)"
dest_base = "/Books"

print("Checking if files exist in destination...")
print("=" * 80)

missing_files = []
existing_files = []

for rel_path in source_files:
    src_path = source_base + rel_path
    dst_path = dest_base + rel_path
    
    try:
        # Try to get metadata for the destination file
        metadata = dbx.files_get_metadata(dst_path)
        existing_files.append({
            'rel_path': rel_path,
            'src_path': src_path,
            'dst_path': dst_path,
            'dst_size': metadata.size
        })
        print(f"✅ EXISTS: {rel_path}")
        print(f"   Dest size: {metadata.size:,} bytes\n")
    except ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            missing_files.append({
                'rel_path': rel_path,
                'src_path': src_path,
                'dst_path': dst_path
            })
            print(f"❌ MISSING: {rel_path}")
            print(f"   Would move to: {dst_path}\n")
        else:
            print(f"⚠️ ERROR checking {rel_path}: {e}\n")

print("=" * 80)
print(f"\nSUMMARY:")
print(f"  ✅ Files that exist in destination: {len(existing_files)}")
print(f"  ❌ Files MISSING from destination: {len(missing_files)}")

if missing_files:
    print(f"\n{'='*80}")
    print("FILES THAT NEED TO BE MOVED:")
    print("="*80)
    for f in missing_files:
        print(f"\n  FROM: {f['src_path']}")
        print(f"  TO:   {f['dst_path']}")


