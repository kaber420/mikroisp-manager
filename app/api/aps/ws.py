# app/api/aps/ws.py
"""WebSocket endpoints for real-time AP monitoring."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...db.engine import async_session_maker
from ...models.ap import AP as APModel
from ...services.ap_monitor_scheduler import ap_monitor_scheduler
from ...utils.cache import cache_manager
from ...utils.security import decrypt_data

router = APIRouter()


@router.websocket("/ws/aps/{host}/resources")
async def ap_resources_stream(websocket: WebSocket, host: str):
    """
    Canal de streaming para datos en vivo del AP.

    ARQUITECTURA V2 (Scheduler + Cache compartido):
    - NO crea conexión directa al AP.
    - Se suscribe al APMonitorScheduler.
    - Lee del CacheManager local (compartido entre usuarios).
    """
    await websocket.accept()

    try:
        # 1. Get AP from DB and prepare credentials
        async with async_session_maker() as session:
            ap = await session.get(APModel, host)
            if not ap:
                await websocket.send_json(
                    {"type": "error", "data": {"message": f"AP {host} no encontrado"}}
                )
                await websocket.close()
                return

            # Copy needed data before session closes
            vendor = ap.vendor or "mikrotik"
            username = ap.username
            password = decrypt_data(ap.password)
            port = ap.api_port or (443 if vendor == "ubiquiti" else 8729)
            ap_monitor_interval = ap.monitor_interval or 2

            # Prepare credentials for scheduler
            creds = {"username": username, "password": password, "vendor": vendor, "port": port}

        # 2. Subscribe to scheduler (starts shared polling if first subscriber)
        await ap_monitor_scheduler.subscribe(host, creds, interval=ap_monitor_interval)
        print(f"✅ WS AP: Subscribed to scheduler for {host}")

        # 3. Loop reading from cache
        stats_cache = cache_manager.get_store("ap_stats")

        while True:
            # Determine interval
            if ap_monitor_interval and ap_monitor_interval >= 1:
                interval = ap_monitor_interval
            else:
                try:
                    async with async_session_maker() as session:
                        from ...services.settings_service import SettingsService
                        svc = SettingsService(session)
                        val = await svc.get_setting_value("dashboard_refresh_interval")
                        interval_setting = val
                    
                    interval = int(interval_setting) if interval_setting else 2
                    if interval < 1:
                        interval = 1
                except ValueError:
                    interval = 2

            # Read from cache
            data = stats_cache.get(host)

            if data:
                if "error" in data:
                    # Error in polling - notify but don't close
                    await websocket.send_json({"type": "error", "data": {"message": data["error"]}})
                else:
                    # Transform data for frontend compatibility
                    clients_list = []
                    for client in data.get("clients", []):
                        clients_list.append(
                            {
                                "cpe_mac": client.get("mac"),
                                "cpe_hostname": client.get("hostname"),
                                "ip_address": client.get("ip_address"),
                                "signal": client.get("signal"),
                                "signal_chain0": client.get("signal_chain0"),
                                "signal_chain1": client.get("signal_chain1"),
                                "noisefloor": client.get("noisefloor"),
                                "dl_capacity": client.get("extra", {}).get("dl_capacity")
                                if client.get("extra")
                                else None,
                                "ul_capacity": client.get("extra", {}).get("ul_capacity")
                                if client.get("extra")
                                else None,
                                "throughput_rx_kbps": client.get("rx_throughput_kbps"),
                                "throughput_tx_kbps": client.get("tx_throughput_kbps"),
                                "total_rx_bytes": client.get("rx_bytes"),
                                "total_tx_bytes": client.get("tx_bytes"),
                                "ccq": client.get("ccq"),
                                "tx_rate": client.get("tx_rate"),
                                "rx_rate": client.get("rx_rate"),
                            }
                        )

                    # Calculate memory usage
                    memory_usage = 0
                    extra = data.get("extra", {})
                    free_mem = extra.get("free_memory")
                    total_mem = extra.get("total_memory")

                    if free_mem and total_mem:
                        try:
                            free = int(free_mem)
                            total = int(total_mem)
                            if total > 0:
                                used = total - free
                                memory_usage = int(round((used / total) * 100, 1))
                        except (ValueError, TypeError):
                            pass

                    payload = {
                        "type": "resources",
                        "data": {
                            "host": host,
                            "hostname": data.get("hostname"),
                            "model": data.get("model"),
                            "mac": data.get("mac"),
                            "firmware": data.get("firmware"),
                            "vendor": data.get("vendor", vendor),
                            "client_count": data.get("client_count", 0),
                            "noise_floor": data.get("noise_floor"),
                            "chanbw": data.get("chanbw"),
                            "frequency": data.get("frequency"),
                            "essid": data.get("essid"),
                            "total_tx_bytes": data.get("total_tx_bytes"),
                            "total_rx_bytes": data.get("total_rx_bytes"),
                            "total_throughput_tx": data.get("total_throughput_tx"),
                            "total_throughput_rx": data.get("total_throughput_rx"),
                            "airtime_total_usage": data.get("airtime_total_usage"),
                            "airtime_tx_usage": data.get("airtime_tx_usage"),
                            "airtime_rx_usage": data.get("airtime_rx_usage"),
                            "clients": clients_list,
                            "extra": {
                                "cpu_load": extra.get("cpu_load", 0),
                                "free_memory": free_mem,
                                "total_memory": total_mem,
                                "memory_usage": memory_usage,
                                "uptime": extra.get("uptime", "--"),
                                "platform": extra.get("platform"),
                                "wireless_type": extra.get("wireless_type"),
                            },
                        },
                    }
                    await websocket.send_json(payload)
            else:
                # Data not yet available (loading...)
                await websocket.send_json({"type": "loading", "data": {}})

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        print(f"✅ WS AP: Cliente desconectado del stream {host}")
    except Exception as e:
        import traceback

        print(f"❌ WS AP Error crítico en {host}: {e}")
        traceback.print_exc()
    finally:
        # 4. Unsubscribe (important - cleanup when last user disconnects)
        await ap_monitor_scheduler.unsubscribe(host)
        try:
            await websocket.close()
        except:
            pass
