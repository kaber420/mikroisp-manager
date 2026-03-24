# app/bot/core/middleware.py
"""
Rate limiting middleware for Telegram Bot handlers.
Provides a decorator to prevent spam and DoS attacks.
"""

import time
import logging
from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# In-memory store for rate limiting
# Format: {user_id: [list of timestamps]}
_user_timestamps: dict[str, list[float]] = {}

# Config
DEFAULT_LIMIT = 5  # requests
DEFAULT_WINDOW = 10  # seconds


def rate_limit(limit: int = DEFAULT_LIMIT, window: int = DEFAULT_WINDOW, silent: bool = False):
    """
    Decorator to rate limit handler functions.
    
    Args:
        limit: Max number of requests allowed in the time window.
        window: Time window in seconds.
        silent: If True, silently drop requests. If False, send a warning message.
    
    Usage:
        @rate_limit(limit=3, window=5)
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)
            
            user_id = str(user.id)
            now = time.time()
            
            # Get or create timestamp list for this user
            if user_id not in _user_timestamps:
                _user_timestamps[user_id] = []
            
            # Clean old timestamps outside the window
            _user_timestamps[user_id] = [
                ts for ts in _user_timestamps[user_id] if now - ts < window
            ]
            
            # Check if over limit
            if len(_user_timestamps[user_id]) >= limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if not silent:
                    try:
                        if update.message:
                            await update.message.reply_text(
                                "⏳ Por favor, espera unos segundos antes de enviar más comandos."
                            )
                        elif update.callback_query:
                            await update.callback_query.answer(
                                "⏳ Por favor, espera unos segundos.",
                                show_alert=True
                            )
                    except Exception as e:
                        logger.debug(f"Could not send rate limit warning: {e}")
                return None  # Block the request
            
            # Record this request
            _user_timestamps[user_id].append(now)
            
            # Proceed with the original handler
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def cleanup_rate_limit_cache(max_age: int = 300):
    """
    Utility function to clean up stale entries from the rate limit cache.
    Call this periodically (e.g., every few minutes) to prevent memory bloat.
    
    Args:
        max_age: Remove entries older than this many seconds.
    """
    now = time.time()
    stale_users = []
    for user_id, timestamps in _user_timestamps.items():
        # Remove old timestamps
        _user_timestamps[user_id] = [ts for ts in timestamps if now - ts < max_age]
        # Mark user for removal if no recent activity
        if not _user_timestamps[user_id]:
            stale_users.append(user_id)
    
    for user_id in stale_users:
        del _user_timestamps[user_id]
    
    if stale_users:
        logger.debug(f"Rate limit cache cleaned: {len(stale_users)} stale entries removed.")
