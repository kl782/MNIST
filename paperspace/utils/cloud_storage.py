#!/usr/bin/env python3
"""
Cloud storage utilities for Paperspace Workflows.
Handles persistent storage in /outputs and /inputs directories.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class CloudStorage:
    """Manage persistent storage in cloud environments."""
    
    def __init__(self, company_name: str):
        """
        Initialize cloud storage manager.
        
        In Paperspace Workflows:
        - /inputs: Read-only input data from previous jobs
        - /outputs: Write outputs that persist to next jobs or datasets
        - /tmp: Temporary storage (non-persistent)
        """
        self.company_name = company_name
        self.company_slug = self._slugify(company_name)
        
        # Detect environment
        self.is_cloud = Path("/outputs").exists()
        
        if self.is_cloud:
            self.base_output = Path("/outputs")
            self.base_input = Path("/inputs") if Path("/inputs").exists() else None
            self.temp_dir = Path("/tmp")
        else:
            # Local fallback for testing
            self.base_output = Path("paperspace_outputs")
            self.base_input = Path("paperspace_inputs")
            self.temp_dir = Path("temp")
        
        # Create directory structure
        self.setup_directories()
    
    def _slugify(self, name: str) -> str:
        """Convert name to filesystem-safe slug."""
        import re
        return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    
    def setup_directories(self):
        """Create standard directory structure."""
        # Output directories
        self.outputs_root = self.base_output / self.company_slug
        self.logs_dir = self.base_output / "logs"
        self.debug_dir = self.outputs_root / "debug"
        self.data_dir = self.outputs_root / "data"
        self.reports_dir = self.outputs_root / "reports"
        self.vector_ids_dir = self.outputs_root / "vector_ids"
        self.part_a_dir = self.outputs_root / "part_a"
        self.part_b_dir = self.outputs_root / "part_b"
        self.final_dir = self.outputs_root / "final"
        
        # Create all directories
        for dir_path in [
            self.outputs_root, self.logs_dir, self.debug_dir,
            self.data_dir, self.reports_dir, self.vector_ids_dir,
            self.part_a_dir, self.part_b_dir, self.final_dir,
            self.temp_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def save_submission(self, request_data: Dict[str, Any], 
                       confirmation_code: str) -> Path:
        """Save webhook submission data."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        submission_file = self.debug_dir / f"submission_{timestamp}_{confirmation_code}.json"
        
        with open(submission_file, 'w') as f:
            json.dump({
                "confirmation_code": confirmation_code,
                "timestamp": timestamp,
                "company_name": self.company_name,
                "request_data": request_data,
            }, f, indent=2)
        
        return submission_file
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """Save an uploaded file."""
        file_path = self.data_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        return file_path
    
    def save_gdrive_link(self, link: str) -> Path:
        """Save Google Drive link."""
        link_file = self.data_dir / "gdrive_link.txt"
        with open(link_file, 'w') as f:
            f.write(link.strip() + "\n")
        return link_file
    
    def get_company_data_dir(self) -> Path:
        """Get the directory containing company data files."""
        return self.data_dir
    
    def save_vector_store_id(self, vector_store_id: str) -> Path:
        """Save vector store ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        id_file = self.vector_ids_dir / f"vector_{timestamp}.json"
        
        with open(id_file, 'w') as f:
            json.dump({
                "vector_store_id": vector_store_id,
                "company_name": self.company_name,
                "company_slug": self.company_slug,
                "timestamp": timestamp,
            }, f, indent=2)
        
        return id_file
    
    def get_latest_vector_store_id(self) -> Optional[str]:
        """Get the most recent vector store ID."""
        vector_files = list(self.vector_ids_dir.glob("vector_*.json"))
        if not vector_files:
            return None
        
        vector_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        with open(vector_files[0], 'r') as f:
            data = json.load(f)
        
        return data.get("vector_store_id")
    
    def save_part_a_draft(self, content: str) -> Path:
        """Save Part A draft report."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        draft_file = self.part_a_dir / f"report_draft_{self.company_slug}_{timestamp}.md"
        
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create/update latest symlink
        latest_link = self.part_a_dir / f"report_draft_latest_{self.company_slug}.md"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        try:
            os.symlink(draft_file.name, latest_link)
        except Exception:
            # Fallback: just copy the file
            shutil.copy(draft_file, latest_link)
        
        return draft_file
    
    def get_latest_part_a_draft(self) -> Optional[Path]:
        """Get the latest Part A draft."""
        latest_link = self.part_a_dir / f"report_draft_latest_{self.company_slug}.md"
        
        if latest_link.exists():
            return latest_link
        
        # Fallback to most recent file
        drafts = list(self.part_a_dir.glob(f"report_draft_{self.company_slug}_*.md"))
        if drafts:
            drafts.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return drafts[0]
        
        return None
    
    def save_part_b_report(self, content: str, report_type: str = "enhanced") -> Path:
        """Save Part B report."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = self.part_b_dir / f"report_{report_type}_{self.company_slug}_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_file
    
    def save_final_report(self, content: str) -> Path:
        """Save final consolidated report."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        final_file = self.final_dir / f"FINAL_REPORT_{self.company_slug}_{timestamp}.md"
        
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Create ready signal file
        signal_file = self.final_dir / f"FINAL_REPORT_{self.company_slug}_{timestamp}.ready"
        with open(signal_file, 'w') as f:
            f.write(str(final_file) + "\n")
        
        return final_file
    
    def get_latest_final_report(self) -> Optional[Path]:
        """Get the latest final report."""
        reports = list(self.final_dir.glob(f"FINAL_REPORT_{self.company_slug}_*.md"))
        if reports:
            reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return reports[0]
        return None
    
    def list_files(self, directory: str = "data") -> List[Path]:
        """List files in a directory."""
        dir_map = {
            "data": self.data_dir,
            "reports": self.reports_dir,
            "debug": self.debug_dir,
            "part_a": self.part_a_dir,
            "part_b": self.part_b_dir,
            "final": self.final_dir,
        }
        
        target_dir = dir_map.get(directory, self.data_dir)
        return list(target_dir.iterdir()) if target_dir.exists() else []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        def dir_size(path: Path) -> int:
            total = 0
            try:
                for item in path.rglob('*'):
                    if item.is_file():
                        total += item.stat().st_size
            except Exception:
                pass
            return total
        
        return {
            "company": self.company_name,
            "company_slug": self.company_slug,
            "total_size_bytes": dir_size(self.outputs_root),
            "data_files": len(list(self.data_dir.glob('*'))) if self.data_dir.exists() else 0,
            "part_a_drafts": len(list(self.part_a_dir.glob('*.md'))) if self.part_a_dir.exists() else 0,
            "part_b_reports": len(list(self.part_b_dir.glob('*.md'))) if self.part_b_dir.exists() else 0,
            "final_reports": len(list(self.final_dir.glob('FINAL_*.md'))) if self.final_dir.exists() else 0,
        }


# Example usage
if __name__ == "__main__":
    storage = CloudStorage("Acme Corp")
    print(f"Company data directory: {storage.get_company_data_dir()}")
    print(f"Storage stats: {json.dumps(storage.get_storage_stats(), indent=2)}")

