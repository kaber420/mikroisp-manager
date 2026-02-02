
import asyncio
import sys
import os
from datetime import datetime

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.engine import get_session, create_db_and_tables
from app.models.stats import APStats
from sqlmodel import select

async def main():
    print("Starting DB Smoke Test...")
    
    # 1. Ensure tables exist
    print("Creating tables...")
    await create_db_and_tables()
    
    # 2. Insert Test Data
    print("Inserting test APStats...")
    async for session in get_session():
        test_stats = APStats(
            ap_host="1.2.3.4",
            vendor="mikrotik",
            timestamp=datetime.utcnow(),
            client_count=10,
            airtime_total_usage=50,
        )
        session.add(test_stats)
        await session.commit()
        await session.refresh(test_stats)
        print(f"Inserted Stats ID: {test_stats.id}")
        
        # 3. Query Data
        print("Querying data...")
        stmt = select(APStats).where(APStats.ap_host == "1.2.3.4")
        result = await session.exec(stmt)
        stats = result.first()
        
        if stats:
            print(f"Found Stats: Host={stats.ap_host}, Clients={stats.client_count}")
        else:
            print("ERROR: Stats not found!")
            sys.exit(1)
            
        # 4. Cleanup
        print("Cleaning up...")
        await session.delete(stats)
        await session.commit()
        
        print("Smoke Test PASSED!")
        return

if __name__ == "__main__":
    asyncio.run(main())
