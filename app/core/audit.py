# app/core/audit.py
"""
Centralized Audit Logging for OWASP Security Compliance.
Logs all critical/destructive actions (DELETE, sensitive modifications) to a 
structured JSON file for forensic analysis and compliance.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request

from app.models.user import User


# --- Configuration ---
LOG_DIR = "logs"
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure dedicated audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # Don't duplicate to root logger

# File handler with JSON-like format
if not audit_logger.handlers:
    file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(file_handler)


def log_action(
    action: str,
    resource_type: str,
    resource_id: str,
    user: Optional[User] = None,
    request: Optional[Request] = None,
    details: Optional[dict] = None,
    status: str = "success"
) -> None:
    """
    Log a security-relevant action to the audit log.
    
    Args:
        action: The action performed (e.g., "DELETE", "UPDATE", "CREATE")
        resource_type: Type of resource affected (e.g., "router", "client", "backup")
        resource_id: Identifier of the affected resource
        user: The User object who performed the action (optional)
        request: FastAPI Request object to extract IP (optional)
        details: Additional context dictionary (optional)
        status: "success" or "failure"
    """
    # Extract client IP
    client_ip = "unknown"
    if request:
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action.upper(),
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "user": user.username if user else "anonymous",
        "user_role": user.role if user else "unknown",
        "ip_address": client_ip,
        "status": status,
    }
    
    if details:
        log_entry["details"] = details
    
    # Write as JSON line
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    # Also print to console for visibility during development
    emoji = "✅" if status == "success" else "❌"
    print(f"📝 [AUDIT] {emoji} {action.upper()} {resource_type}/{resource_id} by {log_entry['user']} from {client_ip}")
