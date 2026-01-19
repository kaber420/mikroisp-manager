# Switch SSL and Provisioning Implementation Plan

## Goal Description

Implement standard SSL status checking and auto-provisioning for Switches, aligning them with the Zero Trust security model currently used for Routers and APs.
This resolves the `AttributeError: 'SwitchService' object has no attribute 'get_ssl_status'` error and ensures switches communicate over secure channels (API-SSL).

## User Review Required
>
> [!WARNING]
> This change involves a database schema migration (adding `is_provisioned` column to `switches` table). The application handles this migration automatically on startup in `init_db.py`, but it's worth noting.

## Proposed Changes

### Database Layer

#### [MODIFY] [init_db.py](file:///home/kaber420/Documentos/python/umanager6/app/db/init_db.py)

- Update `switches` table definition to include `is_provisioned BOOLEAN DEFAULT FALSE`.
- Add a migration block to add this column to existing databases.
- Add a smart default update: If `api_port == api_ssl_port` (or strict SSL is already used), mark as provisioned.

#### [MODIFY] [switches_db.py](file:///home/kaber420/Documentos/python/umanager6/app/db/switches_db.py)

- Update `create_switch_in_db` to accept/init `is_provisioned`.
- Update `_SWITCH_ALLOWED_COLUMNS` to include `is_provisioned` so it can be updated via API.
- Update fetching logic to include this field where necessary.

### Service Layer

#### [MODIFY] [switch_service.py](file:///home/kaber420/Documentos/python/umanager6/app/services/switch_service.py)

- Implement `get_ssl_status()` method (delegating to `adapter.get_ssl_status()`).
- Implement `ensure_ssl_provisioned()` method (cloned from `RouterService`), which:
    1. Checks current SSL status via adapter.
    2. If insecure, uses `PKIService` to generate certificates.
    3. Uses `adapter.import_certificate()` to apply them.
    4. Returns status.

### Provisioning Support

- The existing `MikrotikProvisioningService` is generic and supports `device_type="switch"`. No changes needed there, but we must ensure `SwitchService` calls it or uses the equivalent logic in `ensure_ssl_provisioned`.

## Verification Plan

### Automated Tests

- None existing for this specific flow.

### Manual Verification

1. **Restart Application**: Ensure DB migration runs without error.
2. **Check Logs**: Observe `Launcher` logs.
    - Expect to see: `[Launcher] - Error getting SSL status...` DISAPPEAR.
    - Expect to see: `Switch ... SSL is INSECURE... Auto-provisioning...` or `SSL is ALREADY SECURE`.
3. **API Test**:
    - URL: `GET /api/switches/{host}/ssl/status`
    - Expected Result: JSON with SSL status (enabled, trusted, valid) instead of 500 Error.
4. **Functional Test**:
    - Verify that the switch monitoring dashboard updates correctly and connection shows as "Secure".
