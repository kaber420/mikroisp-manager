# Plan: Enable Rate and Throughput for RouterOS v6

## Problem

RouterOS v6 devices are not showing "Rate" and "Throughput" in the APs module, while RouterOS v7 devices (WifiWave2) do.

- **Rate**: Should show the negotiated physical link speed (e.g., "144Mbps", "300Mbps").
- **Throughput**: Should show the current traffic usage (e.g., "2Mbps").

## Analysis

### 1. Rate

- **Expected Data**: RouterOS v6 registration table usually returns `tx-rate` and `rx-rate` strings (e.g., "300Mbps", "54Mbps").
- **Current Logic**: `mikrotik_parsers.parse_rate()` extracts the first integer `(\d+)`.
- **Potential Issue**:
  - The field might be named differently (e.g., just `rate` in some contexts?)
  - The value might be a formatted string that regex doesn't match well (unlikely for `\d+`).
  - The code might be looking at `stats` print where `tx-rate` is missing?

### 2. Throughput

- **Expected Data**: Real-time traffic usage (bps).
- **Current Logic**: Uses `tx-bits-per-second` which is a RouterOS v7 (WifiWave2) specific field.
- **RouterOS v6 Limitation**: The legacy `/interface wireless registration-table` **does NOT** provide real-time throughput columns (`tx-bits-per-second`) by default.
- **Alternatives**:
  - **Calculated**: Cannot calculate from `bytes` in a single stateless API call (requires `delta_bytes / delta_time`).
  - **P-Throughput**: v6 provides `p-throughput` (Packed Throughput), which is an estimation of the *theoretical limit* (capacity) based on valid frames, NOT actual usage.
  - **Queues/Simple Queues**: If clients have simple queues (e.g. PPPoE), we could fetch throughput from there, but that requires mapping MAC/IP to Queues, which is outside the scope of `ap_connector` (which focuses on L2 wireless registration).

## Proposed Solution

### Step 1: Debug & Validation

Create a script to dump the **raw** registration table data from a v6 device to confirm exactly what fields are available.
`scripts/debug_ros6_wireless.py`

### Step 2: Fix Rate Parsing

If `tx-rate` is present but failing:

- Adjust `parse_rate` to handle decimals (e.g., "144.4Mbps" -> 144).
- Ensure we are checking the correct field keys.

### Step 3: Address Throughput

Since real-time throughput is unavailable in v6 wireless registration table:

1. **Option A (Recommended)**: Map `p-throughput` to a new field `estimated_capacity` and display that, while leaving `throughput` as 0/None.
2. **Option B (Fallback)**: If the user *really* wants "Throughput" to show *something*, we can map `p-throughput` to it, but this is technically incorrect (Capacity != Usage).
3. **Experimental**: Check if `/interface monitor-traffic` works on the `wlan` interface to get *aggregate* throughput, but not per-client.

**Decision for Plan**:

- Fix `tx-rate` / `rx-rate` parsing (ensure it works for v6 strings).
- For `tx-throughput` / `rx-throughput`:
  - **Constraint**: Since `tx-bits-per-second` is unavailable in v6 wireless registration, we will **NOT** use `p-throughput` as a fallback for the main throughput field, as it represents capacity, not usage.
  - **Action**: Return `0` (or `None`) for throughput on v6 devices to avoid misleading data.
  - We will still parse `p-throughput` into `extra` data for potential future use (e.g. "Max Capacity" display), but the main "Throughput" column will remain empty/zero for v6.

## Implementation Steps

1. **Debug Script**: Create and run `scripts/debug_ros6_wireless.py` (User needs to run this or provide output).
2. **Modify `wireless.py`**:
    - Update `get_connected_clients`:
        - Ensure `tx-rate` fallback logic.
        - valid parsing for "144.4Mbps" (currently 144).
        - **New**: If `tx-bits-per-second` is missing, try to estimate or explicitly handle v6.
        - **New**: Map `p-throughput` to `extra` data (already done, verify frontend usage).
3. **Frontend Update (if needed)**:
    - If backend sends `None`, frontend should handle it gracefully.

## Verification

- Run debug script on v6 device.
- Verify "Rate" column is populated.
- Confirm "Throughput" behavior (likely 0/Empty for v6, unless we use p-throughput).
