#!/usr/bin/env python3
"""
Structured logging for Paperspace Workflows.
Logs are written to stdout in JSON format for easy parsing and monitoring.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class CloudLogger:
    """Structured logger for cloud environments."""
    
    def __init__(self, service_name: str, company_name: str = ""):
        self.service_name = service_name
        self.company_name = company_name
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging to write JSON to stdout and plain text to file."""
        # Console handler - JSON format for cloud platforms
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(JsonFormatter(
            service=self.service_name,
            company=self.company_name
        ))
        
        # File handler - traditional format for debugging
        log_dir = Path("/outputs/logs") if Path("/outputs").exists() else Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{self.service_name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        self.logger = logger
        self.log_file = log_file
    
    def log(self, level: str, message: str, **kwargs):
        """Log a structured message."""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log("debug", message, **kwargs)
    
    def step(self, step_num: int, total_steps: int, message: str, **kwargs):
        """Log a pipeline step."""
        self.info(
            f"[STEP {step_num}/{total_steps}] {message}",
            step=step_num,
            total_steps=total_steps,
            **kwargs
        )
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self.info(f"✓ {message}", status="success", **kwargs)
    
    def metric(self, name: str, value: Any, unit: str = "", **kwargs):
        """Log a metric."""
        self.info(
            f"Metric: {name}={value}{unit}",
            metric_name=name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def __init__(self, service: str = "", company: str = ""):
        super().__init__()
        self.service = service
        self.company = company
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service,
            "message": record.getMessage(),
        }
        
        if self.company:
            log_data["company"] = self.company
        
        # Add extra fields from record
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info"
                ]:
                    log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def create_logger(service_name: str, company_name: str = "") -> CloudLogger:
    """Factory function to create a cloud logger."""
    return CloudLogger(service_name, company_name)


# Example usage
if __name__ == "__main__":
    logger = create_logger("test_service", "acme_corp")
    logger.info("Service started")
    logger.step(1, 5, "Uploading data")
    logger.metric("upload_size", 1024, "KB")
    logger.success("Upload complete")
    logger.error("Connection failed", error_code="CONN_TIMEOUT")

