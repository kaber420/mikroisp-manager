# app/api/aps/provisioning.py
"""Provisioning and repair endpoints for MikroTik APs."""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.audit import log_action
from ...core.users import require_admin, require_technician
from ...db.engine import get_session
from ...models.ap import AP as APModel
from ...models.user import User
from ...services.ap_monitor_scheduler import ap_monitor_scheduler
from ...services.provisioning import MikrotikProvisioningService
from ...services.provisioning.models import ProvisionRequest, ProvisionResponse, ProvisionStatus
from ...utils.security import decrypt_data, encrypt_data

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/aps/{host}/provision")
async def provision_ap(
    host: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),  # Admin only
):
    """
    Provisions a MikroTik AP with secure API-SSL access.

    Creates a dedicated API user and installs SSL certificates.
    Only works for MikroTik APs (vendor='mikrotik').
    """
    # Parse request body
    try:
        body = await request.json()
        data = ProvisionRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    # 1. Get AP from database
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")

    # 2. Validate vendor
    if ap.vendor != "mikrotik":
        raise HTTPException(
            status_code=400,
            detail=f"Provisioning only available for MikroTik devices. This AP is: {ap.vendor}",
        )

    # 3. Check if already provisioned
    if ap.is_provisioned:
        raise HTTPException(
            status_code=400,
            detail="AP is already provisioned. Contact administrator to re-provision.",
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
            device_type="ap",
        )

        if result["status"] == "error":
            # Update error tracking
            ap.last_provision_error = result["message"]
            await session.commit()
            raise HTTPException(status_code=500, detail=result["message"])

        # 7. Update AP in database
        ap.username = data.new_api_user
        ap.password = encrypt_data(data.new_api_password)
        ap.api_port = ssl_port  # Now use SSL port for connections
        ap.is_provisioned = True
        await session.commit()

        # 8. Audit log
        log_action("PROVISION", "ap", host, user=current_user, request=request)

        # 9. Reconnect to monitor scheduler with new credentials
        try:
            await asyncio.sleep(2)  # Wait for API-SSL restart on device
            new_creds = {
                "username": data.new_api_user,
                "password": data.new_api_password,
                "vendor": "mikrotik",
                "port": ssl_port,
            }
            await ap_monitor_scheduler.subscribe(host, new_creds)
        except Exception as e:
            logger.warning(f"Could not reconnect to scheduler after provisioning {host}: {e}")
            # Don't fail - scheduler will pick it up on next poll

        return ProvisionResponse(
            status="success",
            message="AP provisioned successfully with API-SSL",
            method_used=data.method,
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
    Check the provisioning status of an AP.
    Returns whether provisioning is available and current status.
    """
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP not found")

    return ProvisionStatus(
        host=host,
        is_provisioned=ap.is_provisioned,
        vendor=ap.vendor or "unknown",
        api_port=ap.api_port or 443,
        api_ssl_port=ap.api_ssl_port or 8729,
        can_provision=(ap.vendor == "mikrotik" and not ap.is_provisioned),
        last_provision_attempt=ap.last_provision_attempt,
        last_provision_error=ap.last_provision_error,
    )


class APRepairRequest(BaseModel):
    """Request body for AP repair endpoint."""
    action: str = "unprovision"  # 'renew' or 'unprovision'


@router.post("/aps/{host}/repair", status_code=status.HTTP_200_OK)
async def repair_ap_connection(
    host: str,
    body: APRepairRequest | None = None,
    reset_provision: bool = False,  # Keep for backward compatibility
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Repairs or recovers a MikroTik AP in an error state.

    Actions:
    - `unprovision`: Marks the AP as not provisioned (DB only). Default.
    - `renew`: Renews SSL certificates without full re-provisioning.
    """
    ap = await session.get(APModel, host)
    if not ap:
        raise HTTPException(status_code=404, detail="AP no encontrado")

    if ap.vendor != "mikrotik":
        raise HTTPException(
            status_code=400,
            detail=f"Esta operación solo aplica para MikroTik. Este AP es: {ap.vendor}",
        )

    # Handle backward compatibility
    action = "unprovision"
    if body:
        action = body.action
    elif reset_provision:
        action = "unprovision"

    if action == "renew":
        current_password = decrypt_data(ap.password)
        ssl_port = ap.api_ssl_port or 8729

        result = await MikrotikProvisioningService.renew_ssl(
            host=host,
            username=ap.username,
            password=current_password,
            ssl_port=ssl_port,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "SSL renewal failed"))

        log_action("RENEW_SSL", "ap", host, user=current_user)

        return {
            "status": "success",
            "message": "Certificados SSL renovados exitosamente.",
            "action": "renew",
        }

    elif action == "unprovision":
        # Reset connection state in scheduler
        try:
            if hasattr(ap_monitor_scheduler, "reset_connection"):
                ap_monitor_scheduler.reset_connection(host)
        except Exception as e:
            logger.warning(f"Error resetting scheduler for {host}: {e}")

        # Mark as not provisioned
        ap.is_provisioned = False
        ap.last_provision_error = None
        await session.commit()

        log_action("UNPROVISION", "ap", host, user=current_user)

        return {
            "status": "success",
            "message": "AP desvinculado. Listo para re-aprovisionar.",
            "action": "unprovision",
        }
    else:
        raise HTTPException(status_code=400, detail=f"Acción desconocida: {action}")

