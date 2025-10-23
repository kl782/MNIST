#!/usr/bin/env python3
"""
Download files from Google Drive using service account.
"""

import argparse
import io
import os
import re
from pathlib import Path


def extract_google_id(url: str) -> str:
    """Extract Google Drive file/folder ID."""
    if not url:
        return ""
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return ""


def download_gdrive(url: str, output_dir: Path):
    """Download from Google Drive."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        print("ERROR: Google API libraries not installed")
        print("Install with: pip install google-api-python-client google-auth")
        return False
    
    creds_path = Path(os.environ.get("GDRIVE_CREDENTIALS_PATH", "google_drive_credentials.json"))
    if not creds_path.exists():
        print(f"ERROR: Credentials not found: {creds_path}")
        return False
    
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    service = build("drive", "v3", credentials=creds)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    drive_id = extract_google_id(url)
    if not drive_id:
        print(f"ERROR: Could not parse Drive ID from URL: {url}")
        return False
    
    print(f"Downloading from Google Drive: {drive_id}")
    
    downloaded_count = 0
    
    def download_file(file_id: str, file_name: str, out_dir: Path) -> bool:
        nonlocal downloaded_count
        try:
            request = service.files().get_media(fileId=file_id)
            out_path = out_dir / file_name
            fh = io.FileIO(str(out_path), mode="wb")
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            print(f"✓ Downloaded: {file_name}")
            downloaded_count += 1
            return True
        except Exception as e:
            print(f"✗ Failed to download {file_name}: {e}")
            return False
    
    def download_folder(folder_id: str, out_dir: Path):
        nonlocal downloaded_count
        out_dir.mkdir(parents=True, exist_ok=True)
        page_token = None
        
        while True:
            try:
                resp = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                ).execute()
            except Exception as e:
                print(f"✗ Failed to list folder: {e}")
                break
            
            for item in resp.get("files", []):
                item_id = item.get("id")
                name = item.get("name") or item_id
                mime = item.get("mimeType") or ""
                
                if mime == "application/vnd.google-apps.folder":
                    download_folder(item_id, out_dir / name)
                elif mime.startswith("application/vnd.google-apps"):
                    print(f"⊘ Skipping Google Docs type: {name}")
                else:
                    download_file(item_id, name, out_dir)
            
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    
    # Get metadata
    try:
        meta = service.files().get(fileId=drive_id, fields="id, name, mimeType").execute()
    except Exception as e:
        print(f"ERROR: Failed to get metadata: {e}")
        return False
    
    mime = meta.get("mimeType", "")
    if mime == "application/vnd.google-apps.folder":
        print(f"Folder: {meta.get('name')}")
        download_folder(drive_id, output_dir)
    else:
        fname = meta.get("name") or f"download_{drive_id}"
        download_file(drive_id, fname, output_dir)
    
    print(f"\nDownload complete: {downloaded_count} file(s)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Download from Google Drive")
    parser.add_argument("--url", required=True, help="Google Drive URL")
    parser.add_argument("--output", required=True, help="Output directory")
    
    args = parser.parse_args()
    success = download_gdrive(args.url, Path(args.output))
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()

