# Implementation Plan: Unified MikroTik Provisioning (Enhanced)

**Goal**: Create a shared provisioning service that works for all MikroTik devices (Routers, APs, Switches) since they all run RouterOS with the same user/certificate management system.

---

## User Review Required

> [!IMPORTANT]
> **Key Decision**: The AP model currently has no `is_provisioned` or `api_ssl_port` fields. This plan adds them via DB migration. Existing APs will default to `is_provisioned=False`.

> [!NOTE]
> **Scope**: This only applies to MikroTik devices (`vendor="mikrotik"`). Ubiquiti APs will not show provisioning options.

> [!WARNING]
> **Post-Provisioning Behavior**: After provisioning an AP, the system will automatically attempt to reconnect using the new SSL credentials. If the AP's API-SSL service takes time to restart, the first connection attempt may fail. Consider adding a retry mechanism with exponential backoff.

---

## Architecture

### Current State
```
provisioning_service.py  →  Only used by Routers
```

### Proposed State
```
app/services/provisioning/
├── __init__.py
├── mikrotik_provisioning.py   # Core logic (SSH + API methods)
└── models.py                  # Shared request/response models

API Endpoints:
├── /api/routers/{host}/provision  →  Uses shared service
├── /api/aps/{host}/provision      →  Uses shared service (NEW)
└── /api/switches/{host}/provision →  Uses shared service (FUTURE)
```

---

## Proposed Changes

### Phase 1: Create Shared Provisioning Module

---

#### [NEW] `app/services/provisioning/__init__.py`

```python
from .mikrotik_provisioning import MikrotikProvisioningService
from .models import ProvisionRequest, ProvisionResponse
```

---

#### [NEW] `app/services/provisioning/models.py`
Shared Pydantic models for provisioning requests/responses.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
import re

class ProvisionRequest(BaseModel):
    new_api_user: str = Field(..., min_length=1, max_length=64)
    new_api_password: str = Field(..., min_length=8, max_length=128)
    method: Literal["api", "ssh"] = "api"
    
    @field_validator('new_api_user')
    @classmethod
    def validate_username(cls, v):
        """Validate username format (alphanumeric, underscore, dash)"""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only alphanumeric, underscore or dash')
        return v
    
    @field_validator('new_api_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Ensure password has minimum complexity"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # Optional: Add more complexity rules
        return v

class ProvisionResponse(BaseModel):
    status: str  # "success" | "error"
    message: str
    method_used: Optional[str] = None
    warnings: Optional[list[str]] = None  # New: Collect non-fatal warnings
    
class ProvisionStatus(BaseModel):
    """For checking provisioning status of a device"""
    host: str
    is_provisioned: bool
    vendor: str
    api_port: int
    api_ssl_port: int
    can_provision: bool  # True if vendor == "mikrotik" and not provisioned
```

---

#### [NEW] `app/services/provisioning/mikrotik_provisioning.py`

Move and refactor logic from `provisioning_service.py`.

- `_run_provisioning_ssh_pure()` - Pure SSH method (current implementation)
- `_run_provisioning_api()` - API-based method (current implementation)
- `provision_device()` - Unified entry point

```python
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DeviceCredentials:
    """Generic device credentials for provisioning"""
    host: str
    username: str
    password: str  # Already decrypted
    ssl_port: int = 8729
    ssh_port: int = 22

class MikrotikProvisioningService:
    """
    Unified MikroTik Provisioning Service.
    Works for Routers, APs, and Switches running RouterOS.
    """
    
    # Configuration constants
    DEFAULT_SSL_PORT = 8729
    DEFAULT_SSH_PORT = 22
    API_RESTART_WAIT_SECONDS = 3
    MAX_RETRY_ATTEMPTS = 3
    
    @staticmethod
    async def provision_device(
        host: str,
        current_username: str,
        current_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        method: str = "ssh",  # Changed default to SSH (more secure)
        device_type: str = "router"  # "router", "ap", "switch"
    ) -> Dict[str, Any]:
        """
        Unified provisioning for any MikroTik device.
        
        Args:
            host: Device IP/hostname
            current_username: Existing SSH/API username
            current_password: Existing password (decrypted)
            new_user: New API user to create
            new_password: Password for new user
            ssl_port: Target API-SSL port (default 8729)
            method: "ssh" (recommended) or "api"
            device_type: For logging context
            
        Returns:
            Dict with status, message, and optional warnings
        """
        logger.info(f"[Provisioning] Starting {method.upper()} provisioning for {device_type} {host}")
        
        try:
            if method == "ssh":
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_ssh_provisioning,
                    host, current_username, current_password,
                    new_user, new_password, ssl_port
                )
            else:
                result = await asyncio.to_thread(
                    MikrotikProvisioningService._run_api_provisioning,
                    host, current_username, current_password,
                    new_user, new_password, ssl_port
                )
            
            result["method_used"] = method
            return result
            
        except Exception as e:
            logger.error(f"[Provisioning] Failed for {host}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "method_used": method
            }
    
    @staticmethod
    def _run_ssh_provisioning(
        host: str,
        ssh_username: str,
        ssh_password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access"
    ) -> Dict[str, Any]:
        """
        Pure SSH Provisioning (copied from existing provisioning_service.py)
        """
        # Import here to avoid circular imports
        from ...utils.device_clients.mikrotik.ssh_client import MikrotikSSHClient
        from ...services.pki_service import PKIService
        
        # ... (existing implementation from ProvisioningService._run_provisioning_ssh_pure)
        # This is a copy, see provisioning_service.py lines 112-283
        pass  # Placeholder - copy actual implementation
    
    @staticmethod
    def _run_api_provisioning(
        host: str,
        username: str,
        password: str,
        new_user: str,
        new_password: str,
        ssl_port: int = 8729,
        new_group: str = "api_full_access"
    ) -> Dict[str, Any]:
        """
        API-based Provisioning (copied from existing provisioning_service.py)
        """
        # ... (existing implementation from ProvisioningService._run_provisioning_sync)
        pass  # Placeholder - copy actual implementation
    
    @staticmethod
    async def verify_provisioning(
        host: str,
        username: str,
        password: str,
        ssl_port: int = 8729,
        max_attempts: int = 3,
        wait_seconds: int = 2
    ) -> Tuple[bool, str]:
        """
        NEW: Verify that provisioning was successful by attempting API-SSL connection.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        from ...utils.device_clients.mikrotik.base import MikrotikApiClient
        
        for attempt in range(max_attempts):
            try:
                await asyncio.sleep(wait_seconds * (attempt + 1))  # Exponential backoff
                
                client = MikrotikApiClient(
                    host=host,
                    username=username,
                    password=password,
                    port=ssl_port,
                    use_ssl=True
                )
                
                if client.connect():
                    client.disconnect()
                    return True, "API-SSL connection verified successfully"
                    
            except Exception as e:
                logger.warning(f"[Provisioning] Verification attempt {attempt + 1} failed: {e}")
                continue
        
        return False, f"Could not verify API-SSL after {max_attempts} attempts"
```

---

### Phase 2: Update Models and Database

---

#### [MODIFY] `app/models/ap.py`
Add provisioning fields:

```python
class AP(SQLModel, table=True):
     ...
     api_port: Optional[int] = Field(default=443)
+    api_ssl_port: Optional[int] = Field(default=8729)
+    is_provisioned: bool = Field(default=False)
+    # NEW: Track last provisioning attempt for troubleshooting
+    last_provision_attempt: Optional[datetime] = Field(default=None)
+    last_provision_error: Optional[str] = Field(default=None)
```

---

#### [MODIFY] `app/api/aps/models.py`
Add fields to Pydantic models:

```python
class AP(BaseModel):
     ...
     api_port: Optional[int] = 443
+    api_ssl_port: Optional[int] = 8729
+    is_provisioned: bool = False
+    last_provision_attempt: Optional[datetime] = None

class APCreate(BaseModel):
     ...
+    api_ssl_port: int = 8729  # Allow specifying during creation

class APUpdate(BaseModel):
     ...
+    api_ssl_port: Optional[int] = None
+    is_provisioned: Optional[bool] = None
```

---

#### [MODIFY] `app/db/init_db.py`
Add migration for new columns (add after router migrations ~line 295):

```python
# --- Migration: Add provisioning fields to aps table ---
ap_columns = [
    col[1] for col in cursor.execute("PRAGMA table_info(aps)").fetchall()
]

if "is_provisioned" not in ap_columns:
    print("Migrando aps: Agregando is_provisioned...")
    cursor.execute("ALTER TABLE aps ADD COLUMN is_provisioned BOOLEAN DEFAULT FALSE;")

if "api_ssl_port" not in ap_columns:
    print("Migrando aps: Agregando api_ssl_port...")
    cursor.execute("ALTER TABLE aps ADD COLUMN api_ssl_port INTEGER DEFAULT 8729;")
    
if "last_provision_attempt" not in ap_columns:
    print("Migrando aps: Agregando last_provision_attempt...")
    cursor.execute("ALTER TABLE aps ADD COLUMN last_provision_attempt DATETIME;")

if "last_provision_error" not in ap_columns:
    print("Migrando aps: Agregando last_provision_error...")
    cursor.execute("ALTER TABLE aps ADD COLUMN last_provision_error TEXT;")

# Smart default: Mark MikroTik APs already using SSL port as provisioned
cursor.execute("""
    UPDATE aps SET is_provisioned = TRUE 
    WHERE vendor = 'mikrotik' AND api_port = 8729;
""")
print("  -> MikroTik APs usando puerto 8729 marcados como aprovisionados.")
```

---

### Phase 3: Create AP Provisioning Endpoint

---

#### [MODIFY] `app/api/aps/main.py`

Add provisioning imports and endpoint after the existing endpoints:

```python
# Add to imports section
from ...core.users import require_admin  # NEW: Provisioning requires admin
from ..services.provisioning import MikrotikProvisioningService
from ..services.provisioning.models import ProvisionRequest, ProvisionResponse

# Add new endpoint (after delete_ap, around line 296)
@router.post("/aps/{host}/provision", response_model=ProvisionResponse)
async def provision_ap(
    host: str,
    data: ProvisionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),  # Admin only
):
    """
    Provisions a MikroTik AP with secure API-SSL access.
    
    Creates a dedicated API user and installs SSL certificates.
    Only works for MikroTik APs (vendor='mikrotik').
    """
    from ...utils.security import decrypt_data
    from ...models.ap import AP as APModel
    from ...core.audit import log_action
    from datetime import datetime
    
    # 1. Get AP from database
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")
    
    # 2. Validate vendor
    if ap.vendor != "mikrotik":
        raise HTTPException(
            status_code=400, 
            detail=f"Provisioning only available for MikroTik devices. This AP is: {ap.vendor}"
        )
    
    # 3. Check if already provisioned (optional: allow re-provisioning)
    if ap.is_provisioned:
        raise HTTPException(
            status_code=400,
            detail="AP is already provisioned. Use force=true to re-provision."
        )
    
    # 4. Decrypt current password
    current_password = decrypt_data(ap.password)
    ssl_port = ap.api_ssl_port or 8729
    
    # 5. Record provisioning attempt
    ap.last_provision_attempt = datetime.now()
    ap.last_provision_error = None
    await session.commit()
    
    try:
        # 6. Run provisioning
        result = await MikrotikProvisioningService.provision_device(
            host=host,
            current_username=ap.username,
            current_password=current_password,
            new_user=data.new_api_user,
            new_password=data.new_api_password,
            ssl_port=ssl_port,
            method=data.method,
            device_type="ap"
        )
        
        if result["status"] == "error":
            # Update error tracking
            ap.last_provision_error = result["message"]
            await session.commit()
            raise HTTPException(status_code=500, detail=result["message"])
        
        # 7. Update AP in database
        from ...utils.security import encrypt_data
        ap.username = data.new_api_user
        ap.password = encrypt_data(data.new_api_password)
        ap.api_port = ssl_port  # Now use SSL port for connections
        ap.is_provisioned = True
        await session.commit()
        
        # 8. Audit log
        log_action("PROVISION", "ap", host, user=current_user, request=request)
        
        # 9. Subscribe to monitor scheduler with new credentials
        from ...services.ap_monitor_scheduler import ap_monitor_scheduler
        
        try:
            await asyncio.sleep(2)  # Wait for API-SSL restart
            new_creds = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "vendor": "mikrotik",
                "port": ssl_port
            }
            await ap_monitor_scheduler.subscribe(host, new_creds)
        except Exception as e:
            logger.warning(f"Could not reconnect to scheduler after provisioning {host}: {e}")
            # Don't fail - scheduler will pick it up on next poll
        
        return ProvisionResponse(
            status="success",
            message="AP provisioned successfully with API-SSL",
            method_used=data.method
        )
        
    except HTTPException:
        raise
    except Exception as e:
        ap.last_provision_error = str(e)
        await session.commit()
        logger.error(f"Provisioning failed for AP {host}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aps/{host}/provision-status")
async def get_provision_status(
    host: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_technician),
):
    """
    NEW: Check the provisioning status of an AP.
    Returns whether provisioning is available and current status.
    """
    from ...models.ap import AP as APModel
    
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")
    
    return {
        "host": host,
        "is_provisioned": ap.is_provisioned,
        "vendor": ap.vendor,
        "api_port": ap.api_port,
        "api_ssl_port": ap.api_ssl_port or 8729,
        "can_provision": ap.vendor == "mikrotik" and not ap.is_provisioned,
        "last_provision_attempt": ap.last_provision_attempt,
        "last_provision_error": ap.last_provision_error
    }
```

---

### Phase 4: Update Router Endpoint to Use Shared Service

---

#### [MODIFY] `app/api/routers/main.py`

Replace direct call to `ProvisioningService` with shared module:

```python
# Replace import
- from ...services.provisioning_service import ProvisioningService
+ from ...services.provisioning import MikrotikProvisioningService

# In provision_router_endpoint (around line 237):
- result = await ProvisioningService.provision_router(session, host, router, data)
+ result = await MikrotikProvisioningService.provision_device(
+     host=host,
+     current_username=router.username,
+     current_password=decrypt_data(router.password),
+     new_user=data.new_api_user,
+     new_password=data.new_api_password,
+     ssl_port=router.api_ssl_port,
+     method=data.method,
+     device_type="router"
+ )
```

---

### Phase 5: Update UI

---

#### [MODIFY] `templates/aps.html`

Add provision button and modal (copy pattern from `routers.html`):

- Show "Provision" button for MikroTik APs where `is_provisioned == false`
- Reuse modal structure from routers
- Add vendor badge showing "MikroTik" or "Ubiquiti"

**Key additions:**
```html
<!-- In AP card/row -->
{% if ap.vendor == 'mikrotik' and not ap.is_provisioned %}
<button class="btn btn-warning btn-sm" onclick="showProvisionModal('{{ ap.host }}')">
    <i class="fas fa-shield-alt"></i> Provision
</button>
{% elif ap.vendor == 'mikrotik' and ap.is_provisioned %}
<span class="badge bg-success"><i class="fas fa-lock"></i> Secured</span>
{% endif %}

<!-- Vendor badge -->
<span class="badge {{ 'bg-info' if ap.vendor == 'mikrotik' else 'bg-primary' }}">
    {{ ap.vendor | title }}
</span>
```

---

#### [MODIFY] `static/js/aps.js`

Add provisioning logic similar to `routers.js`:

```javascript
// NEW: AP Provisioning Functions
async function showProvisionModal(host) {
    // Fetch current status first
    const status = await fetch(`/api/aps/${host}/provision-status`).then(r => r.json());
    
    if (!status.can_provision) {
        showToast('error', `Cannot provision: ${status.last_provision_error || 'Already provisioned'}`);
        return;
    }
    
    // Populate modal with suggested values
    document.getElementById('provision-host').value = host;
    document.getElementById('provision-ssl-port').value = status.api_ssl_port;
    document.getElementById('new-api-user').value = 'umanager_api';
    document.getElementById('new-api-password').value = generateSecurePassword();
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('provisionModal'));
    modal.show();
}

async function submitProvision() {
    const host = document.getElementById('provision-host').value;
    const data = {
        new_api_user: document.getElementById('new-api-user').value,
        new_api_password: document.getElementById('new-api-password').value,
        method: document.getElementById('provision-method').value || 'ssh'
    };
    
    // Show loading state
    const btn = document.getElementById('provision-submit-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Provisioning...';
    
    try {
        const response = await fetch(`/api/aps/${host}/provision`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('success', 'AP provisioned successfully!');
            // Close modal and refresh list
            bootstrap.Modal.getInstance(document.getElementById('provisionModal')).hide();
            loadAPs(); // Refresh AP list
        } else {
            showToast('error', result.detail || 'Provisioning failed');
        }
    } catch (e) {
        showToast('error', `Error: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-shield-alt"></i> Provision';
    }
}

function generateSecurePassword(length = 16) {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%';
    let password = '';
    for (let i = 0; i < length; i++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
}
```

---

### Phase 6: Backwards Compatibility Layer (NEW)

---

#### [MODIFY] `app/services/provisioning_service.py`

Keep as wrapper for backwards compatibility:

```python
"""
DEPRECATED: Use app.services.provisioning.MikrotikProvisioningService instead.
This module is kept for backwards compatibility only.
"""
import warnings
from .provisioning import MikrotikProvisioningService

class ProvisioningService:
    """
    Legacy wrapper - delegates to MikrotikProvisioningService.
    Will be removed in a future version.
    """
    
    @staticmethod
    async def provision_router(session, host: str, creds, data):
        warnings.warn(
            "ProvisioningService.provision_router is deprecated. "
            "Use MikrotikProvisioningService.provision_device instead.",
            DeprecationWarning
        )
        from ..utils.security import decrypt_data
        
        result = await MikrotikProvisioningService.provision_device(
            host=host,
            current_username=creds.username,
            current_password=decrypt_data(creds.password),
            new_user=data.new_api_user,
            new_password=data.new_api_password,
            ssl_port=creds.api_ssl_port,
            method=getattr(data, 'method', 'api'),
            device_type="router"
        )
        
        # Handle DB update (moved from original implementation)
        if result["status"] == "success":
            from .router_service import update_router as update_router_service
            from ..utils.security import encrypt_data
            
            update_data = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "api_port": creds.api_ssl_port,
                "is_provisioned": True,
            }
            await update_router_service(session, host, update_data)
        
        return result
    
    # Keep legacy methods for reference
    _run_provisioning_ssh_pure = MikrotikProvisioningService._run_ssh_provisioning
    _run_provisioning_sync = MikrotikProvisioningService._run_api_provisioning
```

---

### Phase 7: Error Handling & Logging Enhancements (NEW)

---

#### [NEW] Add structured logging for provisioning events

```python
# In mikrotik_provisioning.py, add structured logging:

def _log_provision_event(
    host: str, 
    device_type: str, 
    event: str, 
    success: bool, 
    details: str = None
):
    """Log provisioning events for audit trail"""
    from ...db.logs_db import insert_event_log
    
    event_type = "success" if success else "danger"
    message = f"Provisioning {event} for {device_type} {host}"
    if details:
        message += f": {details}"
    
    insert_event_log(
        device_host=host,
        device_type=device_type,
        event_type=event_type,
        message=message
    )
```

---

### Phase 8: Switch Provisioning Placeholder (FUTURE)

---

#### [PLACEHOLDER] `app/api/switches/main.py`

Document for future implementation:

```python
# TODO: Add switch provisioning endpoint when switches module is complete
# The MikrotikProvisioningService is ready to support switches.
# 
# @router.post("/switches/{host}/provision")
# async def provision_switch(host: str, data: ProvisionRequest, ...):
#     result = await MikrotikProvisioningService.provision_device(
#         host=host,
#         ...,
#         device_type="switch"
#     )
```

---

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `app/services/provisioning/__init__.py` | NEW | Package init with exports |
| `app/services/provisioning/models.py` | NEW | Shared Pydantic models with validation |
| `app/services/provisioning/mikrotik_provisioning.py` | NEW | Core provisioning logic with verification |
| `app/services/provisioning_service.py` | MODIFY | Deprecation wrapper for backwards compat |
| `app/models/ap.py` | MODIFY | Add `is_provisioned`, `api_ssl_port`, tracking fields |
| `app/api/aps/models.py` | MODIFY | Add fields to Pydantic models |
| `app/api/aps/main.py` | MODIFY | Add provision endpoint + status endpoint |
| `app/api/routers/main.py` | MODIFY | Use shared service |
| `app/db/init_db.py` | MODIFY | Add migration with smart defaults |
| `templates/aps.html` | MODIFY | Add provision UI with vendor badges |
| `static/js/aps.js` | MODIFY | Add provision logic with password generator |

---

## Verification Plan

### Automated Tests

1. **Syntax validation** of all modified Python files
   ```bash
   python -m py_compile app/services/provisioning/*.py
   python -m py_compile app/api/aps/main.py
   ```

2. **API endpoint reachability tests**
   ```bash
   # Test provision status endpoint
   curl -X GET http://localhost:8000/api/aps/{host}/provision-status -H "Authorization: Bearer $TOKEN"
   
   # Test provision endpoint (dry run with invalid credentials)
   curl -X POST http://localhost:8000/api/aps/{host}/provision \
     -H "Content-Type: application/json" \
     -d '{"new_api_user": "test", "new_api_password": "testtest", "method": "ssh"}'
   ```

3. **Unit tests for validation**
   ```bash
   pytest tests/test_provisioning_models.py -v
   ```

### Manual Verification

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| Router Provisioning | 1. Navigate to router details<br>2. Click Provision<br>3. Complete wizard | Router marked as provisioned, API-SSL active |
| AP Provisioning (MikroTik) | 1. Add MikroTik AP<br>2. Navigate to AP details<br>3. Click Provision<br>4. Select SSH method | AP marked as provisioned, uses API-SSL |
| AP Provisioning (Ubiquiti) | 1. Navigate to Ubiquiti AP | "Provision" button should NOT appear |
| Database Migration | 1. Start app with existing DB<br>2. Check logs | New columns added, smart defaults applied |
| UI Vendor Badge | 1. View AP list | MikroTik = blue badge, Ubiquiti = green badge |
| Error Handling | 1. Attempt provision with wrong SSH password | Error shown, `last_provision_error` updated |

---

## Security Considerations (NEW)

1. **Password Handling**
   - Passwords are encrypted before storage using `encrypt_data()`
   - Never log passwords, even in errors
   - Use secure password generation in frontend

2. **Rate Limiting**
   - Consider adding rate limiting to provision endpoints to prevent brute-force
   - Example: 3 attempts per 5 minutes per device

3. **Audit Trail**
   - All provisioning actions are logged via `log_action()`
   - Events stored in `event_logs` table for troubleshooting

4. **Rollback**
   - If provisioning fails mid-way, old credentials remain valid
   - `last_provision_error` field helps with debugging

---

## Estimation

| Task | Estimated Time |
|------|----------------|
| Create provisioning module | 45 min |
| Modify AP models | 15 min |
| Create AP endpoint + status | 30 min |
| Update router endpoint | 15 min |
| Database migration | 10 min |
| UI updates (HTML + JS) | 45 min |
| Backwards compat wrapper | 15 min |
| Testing | 45 min |
| **Total** | ~3.5-4 hours |

---

## Open Questions

1. **Re-provisioning**: Should we allow re-provisioning an already provisioned device? (Current: No, raise error)

2. **Default method**: SSH is more secure but requires SSH enabled. Should it be the default? (Current: Yes)

3. **Certificate rotation**: Should we implement certificate expiry checking and rotation reminders?
