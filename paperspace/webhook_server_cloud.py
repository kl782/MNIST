#!/usr/bin/env python3
"""
Cloud-compatible Flask webhook server for Paperspace Workflows.
- No terminal spawning
- Structured JSON logging
- Persistent storage in /outputs
- Triggers Paperspace Workflow jobs instead of local processes
"""

import os
import json
import time
import uuid
import re
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Add parent directory to path for imports
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import cloud utilities
from paperspace.utils.cloud_logging import create_logger
from paperspace.utils.cloud_storage import CloudStorage

# Optional Google Drive API imports
try:
    from google.oauth2.service_account import Credentials as GCredentials
    from googleapiclient.discovery import build as gbuild
    from googleapiclient.http import MediaIoBaseDownload
    import io
    GOOGLE_API_AVAILABLE = True
    GOOGLE_API_IMPORT_ERROR = None
except Exception as _ga_err:
    GOOGLE_API_AVAILABLE = False
    GOOGLE_API_IMPORT_ERROR = str(_ga_err)

# Optional Paperspace SDK for triggering workflows
try:
    import gradient
    from gradient import WorkflowsClient
    GRADIENT_SDK_AVAILABLE = True
except Exception:
    GRADIENT_SDK_AVAILABLE = False

# -----------------------------------------------------------------------------
# App & CORS
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Global logger (will be created per-request with company context)
base_logger = create_logger("webhook_server")

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin"
    return resp

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

OPENAI_WEBHOOK_SECRET = os.environ.get("OPENAI_WEBHOOK_SECRET", "").strip()
GDRIVE_FINAL_REPORT_FOLDER = os.environ.get(
    "GDRIVE_FINAL_REPORT_FOLDER",
    "https://drive.google.com/drive/folders/17mklV-Pz7Jqv1ZQiDNvYOvNA6qXzROXF",
)

# Paperspace configuration
PAPERSPACE_API_KEY = os.environ.get("PAPERSPACE_API_KEY", "").strip()
PAPERSPACE_PROJECT_ID = os.environ.get("PAPERSPACE_PROJECT_ID", "").strip()
PAPERSPACE_WORKFLOW_ID = os.environ.get("PAPERSPACE_WORKFLOW_ID", "").strip()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.md', '.json', '.csv'}

def slugify(name: str) -> str:
    """Simple filesystem-safe slug."""
    name = (name or "").strip()
    if not name:
        return "unknown_company"
    
    safe = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            safe.append(ch)
        elif ch.isspace():
            safe.append("_")
        else:
            safe.append("_")
    
    slug = "".join(safe).strip("_")
    return slug or "unknown_company"

def extract_company_name(request_data: dict, form_data: dict) -> str:
    """Extract company name from multiple possible keys/casings."""
    candidates = [
        "company_name",
        "name",
        "company",
        "companyName",
        "Company Name",
        "Json Data Company Name",
    ]
    for key in candidates:
        if isinstance(request_data, dict) and key in request_data and request_data.get(key):
            return str(request_data.get(key)).strip()
    for key in candidates:
        if key in form_data and form_data.get(key):
            val = form_data.get(key)
            if isinstance(val, list):
                val = val[0]
            return str(val).strip()
    return "unknown_company"

def parse_use_cases_count(request_data: dict) -> int:
    """Resolve number of use cases from several possible fields."""
    candidates = [
        "use_cases",
        "use_cases_count",
        "readiness_score",
        "Number of use cases to generate",
    ]
    for key in candidates:
        if key in request_data and request_data.get(key) not in (None, ""):
            try:
                return int(str(request_data.get(key)).strip())
            except Exception:
                continue
    return 7

def extract_google_id(url: str) -> str:
    """Extract Google Drive file/folder ID from common URL patterns."""
    if not url:
        return ""
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return ""

def try_download_gdrive_service_account(url: str, dest_dir: Path, logger) -> bool:
    """Download Google Drive folder/file using service account."""
    logger.info(f"Starting service-account Google Drive download: {url}")
    
    try:
        if not GOOGLE_API_AVAILABLE:
            logger.warning(f"Google API libraries unavailable: {GOOGLE_API_IMPORT_ERROR}")
            return False

        creds_path = Path(os.environ.get("GDRIVE_CREDENTIALS_PATH", "google_drive_credentials.json"))
        if not creds_path.exists():
            logger.warning(f"Service account credentials not found at {creds_path}")
            return False

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = GCredentials.from_service_account_file(str(creds_path), scopes=scopes)
        
        try:
            sa_email = getattr(creds, "service_account_email", None)
            if sa_email:
                logger.info(f"Authenticated as service account: {sa_email}")
        except Exception:
            pass

        service = gbuild("drive", "v3", credentials=creds)
        dest_dir.mkdir(parents=True, exist_ok=True)

        drive_id = extract_google_id(url)
        if not drive_id:
            logger.warning("Could not parse Drive ID from URL")
            return False

        downloaded_count = 0

        def download_file(file_id: str, file_name: str, out_dir: Path) -> bool:
            nonlocal downloaded_count
            try:
                request_media = service.files().get_media(fileId=file_id)
                out_path = out_dir / file_name
                fh = io.FileIO(str(out_path), mode="wb")
                downloader = MediaIoBaseDownload(fh, request_media, chunksize=1024 * 1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                logger.info(f"Downloaded file: {out_path}")
                downloaded_count += 1
                return True
            except Exception as e:
                logger.error(f"Failed downloading {file_name}: {e}")
                return False

        def download_folder(folder_id: str, out_dir: Path) -> int:
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
                    logger.error(f"List files failed for folder {folder_id}: {e}")
                    break

                for item in resp.get("files", []):
                    item_id = item.get("id")
                    name = item.get("name") or item_id
                    mime = item.get("mimeType") or ""
                    if mime == "application/vnd.google-apps.folder":
                        download_folder(item_id, out_dir / name)
                    elif mime.startswith("application/vnd.google-apps"):
                        logger.info(f"Skip Google Docs type: {name}")
                    else:
                        download_file(item_id, name, out_dir)

                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return downloaded_count

        # Fetch metadata
        try:
            meta = service.files().get(fileId=drive_id, fields="id, name, mimeType").execute()
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {drive_id}: {e}")
            return False

        mime_top = meta.get("mimeType", "")
        if mime_top == "application/vnd.google-apps.folder":
            logger.info(f"Identified folder: {meta.get('name')}")
            download_folder(drive_id, dest_dir)
        elif mime_top.startswith("application/vnd.google-apps"):
            logger.info(f"Top-level item is Google Doc type; export not implemented")
        else:
            fname = meta.get("name") or f"download_{drive_id}"
            download_file(drive_id, fname, dest_dir)

        logger.success(f"Service-account download finished with {downloaded_count} file(s)")
        return downloaded_count > 0
        
    except Exception as e:
        logger.error(f"Service-account download crashed: {e}")
        return False

def trigger_paperspace_workflow(company_name: str, request_data: dict, storage: CloudStorage, logger):
    """Trigger a Paperspace Workflow to run the pipeline."""
    try:
        if not GRADIENT_SDK_AVAILABLE:
            logger.warning("Gradient SDK not available. Cannot trigger workflow.")
            logger.info("Install with: pip install gradient")
            return False
        
        if not PAPERSPACE_API_KEY or not PAPERSPACE_PROJECT_ID:
            logger.warning("PAPERSPACE_API_KEY or PAPERSPACE_PROJECT_ID not configured")
            return False
        
        # Create workflow client
        client = WorkflowsClient(api_key=PAPERSPACE_API_KEY)
        
        # Prepare workflow parameters
        use_cases_count = parse_use_cases_count(request_data)
        
        params = {
            "company_name": company_name,
            "company_slug": storage.company_slug,
            "use_cases_count": str(use_cases_count),
            "company_description": request_data.get("company_description", ""),
            "readiness_score": str(request_data.get("overall_readiness_score", 50)),
            "readiness_category": request_data.get("readiness_category", "Explorer"),
            "report_expectations": request_data.get("report_expectations", ""),
            "google_drive_link": request_data.get("google_drive_link", ""),
        }
        
        logger.info(f"Triggering Paperspace Workflow for {company_name}")
        logger.info(f"Workflow ID: {PAPERSPACE_WORKFLOW_ID}")
        logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        # Trigger the workflow
        run = client.run_workflow(
            workflow_id=PAPERSPACE_WORKFLOW_ID,
            inputs=params
        )
        
        logger.success(f"Workflow triggered successfully. Run ID: {run.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger Paperspace Workflow: {e}")
        return False

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "webhook_server_cloud",
        "environment": "cloud" if Path("/outputs").exists() else "local",
        "gradient_sdk": GRADIENT_SDK_AVAILABLE,
        "google_api": GOOGLE_API_AVAILABLE,
    }), 200

@app.route("/test", methods=["GET", "POST", "OPTIONS"])
def test():
    """Test endpoint."""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    
    base_logger.info(f"/test accessed via {request.method}")
    return jsonify({"status": "test_success", "method": request.method}), 200

@app.route("/", methods=["POST", "OPTIONS"])
def handle_submission():
    """Main webhook endpoint."""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        base_logger.info(f"Received {request.method} from {request.remote_addr}")
        
        # Extract company name and request data
        company_name = "unknown_company"
        request_data = {}
        
        if "json_data" in request.form:
            try:
                raw_json = request.form["json_data"]
                request_data = json.loads(raw_json)
                company_name = extract_company_name(request_data, dict(request.form))
            except json.JSONDecodeError as e:
                base_logger.error(f"JSON decode error: {e}")
                request_data = {"json_decode_error": str(e)}
        elif request.is_json:
            request_data = request.get_json(silent=True) or {}
            company_name = extract_company_name(request_data, dict(request.form))
        else:
            request_data = dict(request.form)
            company_name = extract_company_name(request_data, request_data)

        # Create company-specific logger and storage
        logger = create_logger("webhook_handler", company_name)
        storage = CloudStorage(company_name)
        
        logger.info(f"Processing submission for company: {company_name}")
        
        # Generate confirmation code
        confirmation_code = f"CONF_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Save submission data
        submission_file = storage.save_submission(request_data, confirmation_code)
        logger.success(f"Saved submission to {submission_file}")
        
        # Handle file uploads
        files_saved = 0
        for key, file in request.files.items():
            if not file or not file.filename:
                continue
            
            fname = secure_filename(file.filename)
            if not fname:
                fname = f"upload_{int(time.time()*1000)}"
            
            file_content = file.read()
            file_path = storage.save_uploaded_file(file_content, fname)
            files_saved += 1
            logger.success(f"Saved file: {fname} ({len(file_content)} bytes)")
        
        # Save Google Drive link if provided
        gdrive_link = (
            request_data.get("google_drive_link")
            or request_data.get("Google Drive Link")
            or request_data.get("googleDriveLink")
        )
        if gdrive_link:
            storage.save_gdrive_link(gdrive_link)
            logger.info(f"Saved Google Drive link")
            
            # Attempt to download files from Google Drive
            try:
                gdrive_dir = storage.temp_dir / "drive_download"
                if try_download_gdrive_service_account(str(gdrive_link), gdrive_dir, logger):
                    # Move downloaded files to data directory
                    for item in gdrive_dir.rglob('*'):
                        if item.is_file():
                            dest = storage.data_dir / item.name
                            item.rename(dest)
                            logger.info(f"Moved downloaded file: {item.name}")
            except Exception as e:
                logger.error(f"Google Drive download failed: {e}")
        
        # Log storage stats
        stats = storage.get_storage_stats()
        logger.metric("data_files", stats["data_files"])
        logger.metric("total_size_bytes", stats["total_size_bytes"])
        
        # Trigger Paperspace Workflow (instead of local pipeline)
        workflow_triggered = trigger_paperspace_workflow(
            company_name, request_data, storage, logger
        )
        
        # Return success response
        response = {
            "status": "success",
            "message": "Submission received and saved successfully",
            "confirmation_code": confirmation_code,
            "company_name": company_name,
            "files_saved": files_saved,
            "workflow_triggered": workflow_triggered,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
        
        logger.success(f"Webhook processing complete. Confirmation: {confirmation_code}")
        return jsonify(response), 200
        
    except Exception as e:
        base_logger.error(f"Error in handle_submission: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/storage/<company_slug>", methods=["GET"])
def get_storage_stats(company_slug: str):
    """Get storage statistics for a company."""
    try:
        # Reverse slugify to approximate company name
        company_name = company_slug.replace("_", " ").title()
        storage = CloudStorage(company_name)
        stats = storage.get_storage_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
def main():
    """Main entry point."""
    port = int(os.environ.get("PORT", "8080"))
    
    base_logger.info("="*60)
    base_logger.info("Starting Cloud Webhook Server")
    base_logger.info(f"Port: {port}")
    base_logger.info(f"Environment: {'cloud' if Path('/outputs').exists() else 'local'}")
    base_logger.info(f"Gradient SDK: {'available' if GRADIENT_SDK_AVAILABLE else 'NOT available'}")
    base_logger.info(f"Google API: {'available' if GOOGLE_API_AVAILABLE else 'NOT available'}")
    base_logger.info("="*60)
    
    # Use production WSGI server in cloud, development server locally
    if Path("/outputs").exists():
        # Cloud environment - use gunicorn or waitress
        try:
            from waitress import serve
            base_logger.info("Using Waitress WSGI server")
            serve(app, host="0.0.0.0", port=port, threads=4)
        except ImportError:
            base_logger.warning("Waitress not available, using Flask dev server")
            app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    else:
        # Local development
        base_logger.info("Using Flask development server")
        app.run(host="0.0.0.0", port=port, debug=True, threaded=True)

if __name__ == "__main__":
    main()

