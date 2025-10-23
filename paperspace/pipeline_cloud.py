#!/usr/bin/env python3
"""
Cloud-compatible pipeline for Paperspace Workflows.
- No ngrok (uses Paperspace's built-in networking)
- No terminal spawning
- Structured logging to stdout
- Persistent storage in /outputs
- Designed to run as Paperspace Workflow jobs
"""

import os
import sys
import time
import re
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Add parent directory to path
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import cloud utilities
from paperspace.utils.cloud_logging import create_logger
from paperspace.utils.cloud_storage import CloudStorage

# Optional Google Drive API for final report upload
try:
    from google.oauth2.service_account import Credentials as GCredentials
    from googleapiclient.discovery import build as gbuild
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except Exception as _ga_err:
    GOOGLE_API_AVAILABLE = False
    GOOGLE_API_IMPORT_ERROR = str(_ga_err)

# Destination for final reports
GDRIVE_FINAL_REPORT_FOLDER = os.environ.get(
    "GDRIVE_FINAL_REPORT_FOLDER",
    "https://drive.google.com/drive/folders/17mklV-Pz7Jqv1ZQiDNvYOvNA6qXzROXF",
)


class CloudPipeline:
    """Cloud-compatible AI pipeline runner."""
    
    def __init__(self, company_name: str, company_info: str = "", 
                 model_set: str = "gpt5", use_cases_count: int = 7):
        self.company_name = company_name
        self.company_info = company_info
        self.model_set = model_set
        self.use_cases_count = use_cases_count
        
        # Initialize logging and storage
        self.logger = create_logger("pipeline", company_name)
        self.storage = CloudStorage(company_name)
        
        # Parse company info into attributes
        self.parse_company_info()
        
        # Set environment variables
        self.setup_environment()
        
        self.logger.success(f"Initialized pipeline for {company_name}")
        self.logger.metric("use_cases_count", use_cases_count)
    
    def parse_company_info(self):
        """Parse company info string into structured data."""
        self.company_description = ""
        self.readiness_score = "50"
        self.readiness_category = "Explorer"
        self.report_expectations = ""
        
        if not self.company_info:
            return
        
        # Parse from formatted string
        patterns = {
            "description": r'\{Company description\}:\s*(.+?)(?=\n\{|\n$)',
            "score": r'\{Overall Readiness score\}:\s*(.+?)(?=\n\{|\n$)',
            "category": r'\{Agent-readiness category\}:\s*(.+?)(?=\n\{|\n$)',
            "expectations": r'\{Report Expectations\}:\s*(.+?)(?=\n\{|\n$)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, self.company_info, re.DOTALL)
            if match:
                value = match.group(1).strip()
                if key == "description":
                    self.company_description = value
                elif key == "score":
                    self.readiness_score = value
                elif key == "category":
                    self.readiness_category = value
                elif key == "expectations":
                    self.report_expectations = value
    
    def setup_environment(self):
        """Set up environment variables for the pipeline."""
        os.environ["MODEL_SET"] = self.model_set
        os.environ["COMPANY_NAME"] = self.company_name
        os.environ["NON_INTERACTIVE"] = "1"
        os.environ["USE_CASES_COUNT"] = str(self.use_cases_count)
        os.environ["COMPANY_DESCRIPTION"] = self.company_description
        os.environ["READINESS_SCORE"] = self.readiness_score
        os.environ["READINESS_CATEGORY"] = self.readiness_category
        os.environ["REPORT_EXPECTATIONS"] = self.report_expectations
        
        # Storage paths
        os.environ["COMPANY_SLUG"] = self.storage.company_slug
        os.environ["OUTPUT_DIR"] = str(self.storage.outputs_root)
        os.environ["DATA_DIR"] = str(self.storage.data_dir)
        
        # Disable features not available in cloud
        os.environ["DISABLE_CAFFEINATE"] = "1"
        os.environ["DISABLE_TERMINAL_SPAWN"] = "1"
        
        self.logger.info("Environment variables configured")
    
    def run_command(self, cmd: str, cwd: Optional[str] = None, 
                   timeout: int = 3600) -> tuple[int, str]:
        """Run a command and return exit code and output."""
        self.logger.info(f"Executing: {cmd}")
        
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ,
            )
            
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                line = line.rstrip()
                if line:
                    # Log to console (captured by Paperspace)
                    print(line, flush=True)
                    output_lines.append(line)
            
            process.stdout.close()
            exit_code = process.wait(timeout=timeout)
            
            full_output = '\n'.join(output_lines)
            return exit_code, full_output
            
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error(f"Command timed out after {timeout} seconds")
            return 1, "TIMEOUT"
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return 1, str(e)
    
    def preprocess_company_folder(self) -> bool:
        """Preprocess company folder (e.g., convert CSV to JSON)."""
        self.logger.step(1, 10, "Preprocessing company data")
        
        company_dir = self.storage.get_company_data_dir()
        
        # Convert CSV files to JSON
        csv_files = list(company_dir.glob('*.csv'))
        for csv_path in csv_files:
            json_path = csv_path.with_suffix('.json')
            self.logger.info(f"Converting CSV: {csv_path.name}")
            
            try:
                import pandas as pd
                df = pd.read_csv(csv_path)
                df.to_json(json_path, orient='records', indent=2)
                csv_path.unlink()
                self.logger.success(f"Converted {csv_path.name} to JSON")
            except Exception as e:
                self.logger.error(f"Failed to convert {csv_path.name}: {e}")
        
        return True
    
    def upload_to_vector_store(self) -> Optional[str]:
        """Upload company data to OpenAI vector store."""
        self.logger.step(2, 10, "Uploading to vector store")
        
        company_folder = str(self.storage.get_company_data_dir())
        
        exit_code, output = self.run_command(
            f"python3 helper_vectorstoreupload.py \"{company_folder}\""
        )
        
        if exit_code != 0:
            self.logger.error("Vector store upload failed")
            return None
        
        # Get the vector store ID
        vector_store_id = self.storage.get_latest_vector_store_id()
        if not vector_store_id:
            # Try to extract from output
            match = re.search(r'vs_[a-zA-Z0-9]+', output)
            if match:
                vector_store_id = match.group(0)
                self.storage.save_vector_store_id(vector_store_id)
        
        if vector_store_id:
            self.logger.success(f"Vector store created: {vector_store_id}")
            return vector_store_id
        
        self.logger.error("Could not determine vector store ID")
        return None
    
    def start_mcp_server(self, vector_store_id: Optional[str] = None) -> bool:
        """Start MCP server in background (no ngrok needed in cloud)."""
        self.logger.step(3, 10, "Starting MCP server")
        
        # In cloud environment, MCP server gets a stable URL from Paperspace
        # No need for ngrok - Paperspace handles routing
        
        port = int(os.environ.get("MCP_PORT", "8001"))
        vector_arg = f" --vector-store-id {vector_store_id}" if vector_store_id else ""
        
        cmd = f"python3 minimal_mcp.py --port {port}{vector_arg} &"
        
        try:
            subprocess.Popen(cmd, shell=True, env=os.environ)
            time.sleep(5)  # Give server time to start
            self.logger.success(f"MCP server started on port {port}")
            
            # In Paperspace, the MCP URL would be provided by the platform
            # For now, use localhost (within the same container/pod)
            mcp_url = f"http://localhost:{port}/sse"
            os.environ["VECTOR_STORE_MCP_URL"] = mcp_url
            self.logger.info(f"MCP URL: {mcp_url}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            return False
    
    def run_quotes_extraction(self) -> bool:
        """Run quotes extraction and clustering."""
        self.logger.step(4, 10, "Extracting and clustering quotes")
        
        collection_name = f"{self.company_name}_quotes"
        os.environ["QDRANT_COLLECTION"] = collection_name
        
        exit_code, output = self.run_command(
            f"python3 pre-prep/step1.py --force --company-name \"{self.company_name}\""
        )
        
        if exit_code != 0:
            self.logger.error("Quotes extraction failed")
            return False
        
        self.logger.success(f"Quotes extracted. Collection: {collection_name}")
        return True
    
    def run_part_a(self, vector_store_id: Optional[str], collection_name: str) -> bool:
        """Run Part A analysis."""
        self.logger.step(5, 10, "Running Part A analysis")
        
        # Update config if needed
        # For cloud, configs are typically env vars or mounted files
        
        exit_code, output = self.run_command(
            "python3 part_a/minimal_dr_part_a.py",
            timeout=7200  # 2 hours
        )
        
        if exit_code != 0:
            self.logger.error("Part A analysis failed")
            return False
        
        # Verify draft was created
        draft_path = self.storage.get_latest_part_a_draft()
        if draft_path and draft_path.exists():
            content = draft_path.read_text(encoding='utf-8')
            self.logger.metric("part_a_length", len(content), "chars")
            self.logger.success("Part A analysis complete")
            return True
        
        self.logger.error("Part A draft not found")
        return False
    
    def run_part_b(self) -> bool:
        """Run Part B analysis with retry logic."""
        self.logger.step(6, 10, "Running Part B analysis")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.warning(f"Retry {attempt}/{max_retries}")
                time.sleep(180)  # Wait 3 minutes
            
            exit_code, output = self.run_command(
                "python3 part_b/minimal_dr_part_b.py",
                timeout=7200
            )
            
            # Check for server errors
            server_error = "Error code: 500" in output and "server_error" in output
            
            if exit_code == 0:
                self.logger.success("Part B minimal draft complete")
                break
            elif server_error and attempt < max_retries:
                self.logger.warning("OpenAI server error, retrying...")
                continue
            else:
                if attempt == max_retries:
                    self.logger.error(f"Part B failed after {max_retries + 1} attempts")
                    return False
        
        # Run use cases processing
        self.logger.step(6.5, 10, "Processing use cases")
        exit_code, output = self.run_command("python3 -u part_b/usecases_apicalls.py")
        
        if exit_code != 0:
            self.logger.error("Use cases processing failed")
            return False
        
        # Run Part B enhancement
        self.logger.step(6.7, 10, "Enhancing Part B report")
        
        # Find latest use cases report
        use_cased_dir = self.storage.part_b_dir
        candidates = list(use_cased_dir.glob(f"report_with_processed_use_cases_*.md"))
        if candidates:
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            input_report = candidates[0]
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_report = self.storage.part_b_dir / f"report_{self.storage.company_slug}_{timestamp}_enhanced.md"
            
            exit_code, output = self.run_command(
                f"python3 -u part_b/main2_refactored.py --input {input_report} --output {output_report}"
            )
            
            if exit_code != 0:
                self.logger.error("Part B enhancement failed")
                return False
        
        self.logger.success("Part B analysis complete")
        return True
    
    async def run_consolidation(self) -> bool:
        """Run final consolidation."""
        self.logger.step(7, 10, "Running final consolidation")
        
        exit_code, output = self.run_command(
            "python3 -u final_consolidation/main.py dual-model --content-model gpt-5 --style-model gpt-5-nano",
            timeout=7200
        )
        
        if exit_code != 0:
            self.logger.error("Consolidation failed")
            return False
        
        self.logger.success("Consolidation complete")
        return True
    
    def upload_final_report_to_gdrive(self, report_path: Path) -> bool:
        """Upload final report to Google Drive."""
        self.logger.step(8, 10, "Uploading final report to Google Drive")
        
        try:
            if not GOOGLE_API_AVAILABLE:
                self.logger.warning(f"Google API not available: {GOOGLE_API_IMPORT_ERROR}")
                return False
            
            creds_path = Path(os.environ.get("GDRIVE_CREDENTIALS_PATH", "google_drive_credentials.json"))
            if not creds_path.exists():
                self.logger.warning(f"Credentials not found: {creds_path}")
                return False
            
            scopes = ["https://www.googleapis.com/auth/drive"]
            creds = GCredentials.from_service_account_file(str(creds_path), scopes=scopes)
            service = gbuild("drive", "v3", credentials=creds)
            
            # Extract folder ID
            folder_id_match = re.search(r"/folders/([a-zA-Z0-9_-]+)", GDRIVE_FINAL_REPORT_FOLDER)
            folder_id = folder_id_match.group(1) if folder_id_match else GDRIVE_FINAL_REPORT_FOLDER
            
            # Upload file
            media = MediaFileUpload(str(report_path), resumable=True)
            body = {"name": report_path.name, "parents": [folder_id]}
            
            request = service.files().create(
                body=body,
                media_body=media,
                fields="id, name",
                supportsAllDrives=True,
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.logger.metric("upload_progress", int(status.progress() * 100), "%")
            
            if response and response.get("id"):
                self.logger.success(f"Uploaded to Drive: {response.get('name')}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Drive upload failed: {e}")
            return False
    
    def finalize_report(self) -> Optional[Path]:
        """Finalize and save the final report."""
        self.logger.step(9, 10, "Finalizing report")
        
        # Find the latest final report
        final_candidates = []
        final_candidates.extend(self.storage.final_dir.glob("final_dual_model_report_*.md"))
        final_candidates.extend(self.storage.final_dir.glob("final_responses_patched_report_*.md"))
        final_candidates.extend(self.storage.final_dir.glob("final_consolidated_report_*.md"))
        
        if not final_candidates:
            self.logger.error("No final report found")
            return None
        
        final_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_report = final_candidates[0]
        
        # Copy to final location
        content = latest_report.read_text(encoding='utf-8')
        final_path = self.storage.save_final_report(content)
        
        self.logger.metric("final_report_size", len(content), "chars")
        self.logger.success(f"Final report saved: {final_path.name}")
        
        # Upload to Google Drive
        self.upload_final_report_to_gdrive(final_path)
        
        return final_path
    
    async def run(self) -> bool:
        """Run the complete pipeline."""
        try:
            self.logger.info("="*60)
            self.logger.info(f"Starting pipeline for {self.company_name}")
            self.logger.info("="*60)
            
            start_time = time.time()
            
            # Step 1: Preprocess
            if not self.preprocess_company_folder():
                return False
            
            # Step 2: Upload to vector store
            vector_store_id = self.upload_to_vector_store()
            if not vector_store_id:
                self.logger.warning("Continuing without vector store ID")
            
            # Step 3: Start MCP server
            if not self.start_mcp_server(vector_store_id):
                return False
            
            # Step 4: Quotes extraction
            collection_name = f"{self.company_name}_quotes"
            if not self.run_quotes_extraction():
                return False
            
            # Step 5: Part A
            if not self.run_part_a(vector_store_id, collection_name):
                return False
            
            # Step 6: Part B
            if not self.run_part_b():
                return False
            
            # Step 7: Consolidation
            if not await self.run_consolidation():
                return False
            
            # Step 8: Finalize
            final_report = self.finalize_report()
            if not final_report:
                return False
            
            # Success!
            elapsed = time.time() - start_time
            self.logger.metric("pipeline_duration", int(elapsed), "seconds")
            self.logger.success("="*60)
            self.logger.success(f"PIPELINE COMPLETE: {self.company_name}")
            self.logger.success(f"Final report: {final_report}")
            self.logger.success("="*60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run cloud pipeline")
    parser.add_argument("company_name", help="Name of the company")
    parser.add_argument("--company-info", help="Company information", default="")
    parser.add_argument("--model-set", choices=["cheap", "better", "gpt5"], default="gpt5")
    parser.add_argument("--use-cases-count", type=int, default=7)
    
    args = parser.parse_args()
    
    pipeline = CloudPipeline(
        company_name=args.company_name,
        company_info=args.company_info,
        model_set=args.model_set,
        use_cases_count=args.use_cases_count
    )
    
    success = await pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

