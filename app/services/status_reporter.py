import asyncio
import json
import os
import aiofiles
from app.utils.cache.manager import cache_manager
from app.services.bot_manager import bot_manager

STATUS_FILE = "/tmp/umanager_status.json"

async def status_reporter_loop():
    """
    Periodically writes the application status to a JSON file.
    This allows the TUI to read status without making HTTP requests.
    """
    while True:
        try:
            # Gather Stats
            cache_stats = cache_manager.get_stats()
            bot_stats = bot_manager.get_status_summary()
            
            data = {
                "cache": cache_stats,
                "bots": bot_stats,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Write to temp file atomically-ish
            async with aiofiles.open(STATUS_FILE, "w") as f:
                await f.write(json.dumps(data))
                
        except Exception as e:
            print(f"⚠️ [StatusReporter] Error writing status: {e}")
            
        await asyncio.sleep(2)
