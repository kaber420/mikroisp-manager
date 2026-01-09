import sys
import os
import asyncio
from sqlmodel import select

# Add app to path
sys.path.append(os.getcwd())

from app.db.engine import get_session
from app.services.cpe_service import CPEService
from app.db.stats_db import save_device_stats
from app.utils.device_clients.adapters.base import DeviceStatus, ConnectedClient

async def main():
    print("--- Verificando Datos de CPEs (Backend) ---")
    
    # 1. Simulate some data if needed, or just read existing
    # We will just read existing data using the service to see what the API sees
    
    # Mock session for service (we just need the method that uses stats_db)
    # The get_all_cpes_globally method primarily uses raw SQL and stats_db, 
    # but checks cpes table for fallbacks.
    
    service = CPEService(None) # Session not strictly needed for the raw sql part if stats exist
    
    try:
        results = service.get_all_cpes_globally()
        
        print(f"\nTotal CPEs encontrados: {len(results)}")
        
        if not results:
            print("No hay CPEs para mostrar. Necesitamos datos de prueba.")
        
        for cpe in results[:5]: # Show first 5
            print(f"\nMAC: {cpe.get('cpe_mac')}")
            print(f"  Hostname: {cpe.get('cpe_hostname')}")
            print(f"  Status: {cpe.get('status')}  <-- EXPOSED FIELD")
            print(f"  Enabled: {cpe.get('is_enabled')}")
            print(f"  Last Seen: {cpe.get('last_seen')}")
            print(f"  AP: {cpe.get('ap_hostname')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
