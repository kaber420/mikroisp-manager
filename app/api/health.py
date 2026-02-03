from fastapi import APIRouter
from app.utils.cache.manager import cache_manager
from app.services.bot_manager import bot_manager

router = APIRouter()

@router.get("/health", tags=["System"])
async def get_system_health():
    """
    Returns the system health status including:
    - Cache status (Legacy/Redict)
    - Bot status (Client/Tech)
    """
    # Cache Stats
    cache_stats = cache_manager.get_stats()
    
    # Bot Stats
    bot_stats = bot_manager.get_status_summary()
    
    return {
        "status": "ok",
        "cache": cache_stats,
        "bots": bot_stats
    }
