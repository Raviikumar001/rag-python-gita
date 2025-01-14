# utils/helpers.py
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid
from dotenv import load_dotenv
import json
import os
from .logger import get_logger
load_dotenv()
logger = get_logger(__name__)

def create_metadata(additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    
    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "user": os.getenv("GITHUB_USER", "ravi-hisoka"),
        "request_id": str(uuid.uuid4()),
        "service_version": "1.0.0",
        "environment": os.getenv("ENV", "development")
    }
    
    if additional_data:
        metadata.update(additional_data)
    
    return metadata

def log_request(endpoint: str, data: Dict[str, Any]) -> str:
    
    request_id = str(uuid.uuid4())
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "endpoint": endpoint,
        "request_id": request_id,
        "user": os.getenv("GITHUB_USER", "ravi-hisoka"),
        "data": data
    }
    
    # Log to file
    logger.info(
        f"Incoming request to {endpoint}",
        extra={
            "request_id": request_id,
            "log_type": "request",
            "data": json.dumps(log_data)
        }
    )
    
    return request_id

def log_response(request_id: str, response_data: Dict[str, Any]) -> None:
    
    log_data = {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "request_id": request_id,
        "response": response_data
    }
    
    # Log to file
    logger.info(
        "Outgoing response",
        extra={
            "request_id": request_id,
            "log_type": "response",
            "data": json.dumps(log_data)
        }
    )

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    
    sensitive_fields = ['password', 'token', 'api_key', 'secret']
    sanitized = data.copy()
    
    for key in sensitive_fields:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    
    return sanitized

def get_request_context() -> Dict[str, Any]:
    
    return {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "user": os.getenv("GITHUB_USER", "ravi-hisoka"),
        "environment": os.getenv("ENV", "development"),
        "service": "crustdata-api"
    }
