# Investigation Report: Monitor Service "Bad File Descriptor" Loop

## Issue Description
The application logs repeated errors `[Errno 9] Bad file descriptor` originating from the `[Launcher]` component, specifically inside the `monitor_job`.

```
2026-01-12 20:42:06 - ERROR - [Launcher] - Error getting status from 172.16.253.34: [Errno 9] Bad file descriptor
...
2026-01-12 20:42:11 - INFO - [Launcher] - Running job "Router/AP Monitor..."
...
2026-01-12 20:42:12 - ERROR - [Launcher] - Error getting status from 172.16.253.34: [Errno 9] Bad file descriptor
```

This error loops indefinitely, often multiple times per second, even though the monitor job is scheduled to run every 2 to 5 minutes. This suggests a tight loop or retry mechanism that is failing to recover.

**Additional Observations (Timeout Errors):**
The logs also show timeouts for Routers (e.g., `10.0.5.2`).
```
2026-01-12 20:52:40 - ERROR - [Launcher] - [RouterConnector] Failed to subscribe to 10.0.5.2: timed out
2026-01-12 20:52:40 - WARNING - [Launcher] - [MonitorScheduler] Backoff for 10.0.5.2: 5s (failures: 1)
```
Unlike the AP "Bad file descriptor" loop, the Router monitoring correctly enters a "Backoff" state. This confirms that the Router monitoring infrastructure (`MonitorScheduler` + `ReadOnlyChannel`) is resilient, whereas the AP monitoring infrastructure (`APMonitorScheduler` + `MikrotikWirelessAdapter`) is not.

**Update (2026-01-12):**
User reported that the issue resolved itself after a server restart. This strongly supports the hypothesis that the error state is being retained in memory (Process State) and is cleared when the application process is terminated and restarted.

## Root Cause Analysis

**CONFIRMED by Code Analysis:**

1.  **Helper Loop in Scheduler**: The `APMonitorScheduler` (`app/services/ap_monitor_scheduler.py`) has a `while self._running:` loop that ticks every 1 second.
2.  **Persistent Connection Pool**: The `MikrotikWirelessAdapter` inherits from `MikrotikRouterAdapter`. In `MikrotikRouterAdapter._get_api()`, it creates a **private** connection pool using `force_new=True`:
    ```python
    # app/utils/device_clients/adapters/mikrotik_router.py
    self._pool_ref = mikrotik_connection.get_pool(..., force_new=True)
    ```
    This pool is stored in `self._pool_ref` and NOT in the global registry accessed by standard keys.
3.  **Broken State Retention**: When a network error occurs (socket closed/timeout), the underlying `RouterOsApi` or its socket becomes invalid.
4.  **Failure to Reset (The Bug)**: 
    *   In `MikrotikWirelessAdapter.get_status()` (`app/utils/device_clients/adapters/mikrotik_wireless.py`), the error handler catches the exception:
        ```python
        except Exception as e:
            # ...
            mikrotik_connection.remove_pool(self.host, self.port, username=self.username)
        ```
    *   **CRITICAL FAULT**: `mikrotik_connection.remove_pool` only removes the entry from the *global* cache. It has NO EFFECT on the `MikrotikWirelessAdapter` instance's private `self._pool_ref`.
    *   Consequently, `self._internal_api` and `self._pool_ref` remain populated with the broken connection.
5.  **Infinite Error Loop**:
    *   Scheduler calls `fetch_ap_stats`.
    *   Connector gets existing Adapter instance.
    *   Adapter `_get_api()` sees `self._internal_api` is not None and returns the *same broken object*.
    *   Call fails with `[Errno 9] Bad file descriptor`.
    *   Exception is caught, `remove_pool` (useless) is called.
    *   Loop repeats.

## Proposed Resolution

We need to align the `MikrotikWirelessAdapter` behavior with the robust `ReadOnlyChannel` pattern, but specifically by leveraging the Adapter's own lifecycle methods.

**File**: `app/utils/device_clients/adapters/mikrotik_wireless.py`

**Logic Fix**:
In `get_status`, instead of calling the ineffective `mikrotik_connection.remove_pool`, we must call `self.disconnect()`.

The `MikrotikRouterAdapter.disconnect()` method correctly handles the cleanup of private pools:
```python
# app/utils/device_clients/adapters/mikrotik_router.py
def disconnect(self):
    # ...
    if self._pool_ref:
         self._pool_ref.disconnect()
         self._pool_ref = None
         self._internal_api = None  # <--- This is what we need cleared
```

**Implementation Plan:**

1.  Modify `app/utils/device_clients/adapters/mikrotik_wireless.py`.
2.  Locate `get_status` method.
3.  Inside the `except Exception as e:` block:
    *   Remove: `mikrotik_connection.remove_pool(self.host, self.port, username=self.username)`
    *   Add: `self.disconnect()`
4.  (Optional) Verify if similar logic applies to `test_connection` method.
    *   **Yes**, `test_connection` has the same bug. It also calls `mikrotik_connection.remove_pool`.
    *   **Action**: Apply the same fix to `test_connection`.

```python
    def get_status(self) -> DeviceStatus:
        try:
             # ... existing code ...
        except Exception as e:
            logger.error(f"Error getting status from {self.host}: {e}")
            # FIX: Use internal disconnect to clear PRIVATE pool state
            self.disconnect() 
            return DeviceStatus(...)

    def test_connection(self) -> bool:
        try:
            # ... existing code ...
        except Exception as e:
            logger.error(f"Connection test failed for {self.host}: {e}")
            # FIX: Use internal disconnect to clear PRIVATE pool state
            self.disconnect()
            return False
```

## Verification
1.  Since we cannot easily reproduce the network error on demand without unplugging devices, verification will rely on code review and unit testing patterns (if available) or simply monitoring after deployment.
2.  **Simulation**: We could simulate this by manually calling `adapter.disconnect()` (simulating a broken state) and seeing if it recovers, or better, mocking the API to raise an `OSError` and asserting that `adapter._internal_api` becomes `None` after the catch.
