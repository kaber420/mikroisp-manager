"""
BotManager Service - Handles Telegram Bot Lifecycle

Designed for Multi-Worker Environments:
- ALL workers initialize bot instances (to enable sending messages)
- ONLY ONE worker runs the polling loop (determined by fcntl file lock)
"""

import logging
import asyncio
import fcntl
import os
from typing import Optional
from telegram.ext import Application
from telegram.error import Conflict, NetworkError, TimedOut
from app.utils.settings_utils import get_setting_sync
from app.bot.bot_client.bot_client import create_application as create_client_app
from app.bot.bot_tech import create_application as create_tech_app

logger = logging.getLogger(__name__)

# Reduce noise from HTTP and Telegram libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

LOCK_FILE = "/tmp/umanager_bot_polling.lock"


class BotManager:
    _instance = None

    def __init__(self):
        self.client_app: Optional[Application] = None
        self.tech_app: Optional[Application] = None
        self.polling_tasks: list[asyncio.Task] = []
        self._is_running = False
        self._lock_file_handle = None
        self._is_polling_leader = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BotManager()
        return cls._instance

    def _acquire_polling_lock(self) -> bool:
        """Try to acquire exclusive lock for polling. Returns True if this process is the leader."""
        try:
            self._lock_file_handle = open(LOCK_FILE, "w")
            fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_file_handle.write(str(os.getpid()))
            self._lock_file_handle.flush()
            return True
        except (IOError, OSError):
            # Another process holds the lock
            if self._lock_file_handle:
                self._lock_file_handle.close()
                self._lock_file_handle = None
            return False

    def _release_polling_lock(self):
        """Release the polling lock."""
        if self._lock_file_handle:
            try:
                fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                self._lock_file_handle.close()
            except Exception:
                pass
            self._lock_file_handle = None

    async def _polling_wrapper(self, app_name: str, updater):
        """Wraps polling to catch and log errors cleanly."""
        try:
            logger.info(f"🔄 {app_name}: Starting polling loop...")
            await updater.start_polling(allowed_updates=True, drop_pending_updates=True)
        except Conflict:
            logger.error(f"❌ {app_name}: Conflict error! Another instance is polling.")
        except (NetworkError, TimedOut) as e:
            logger.warning(f"⚠️ {app_name}: Network issue: {e}")
        except asyncio.CancelledError:
            logger.info(f"🛑 {app_name}: Polling cancelled.")
            raise
        except Exception as e:
            logger.error(f"❌ {app_name}: Polling error: {e}")

    async def start(self):
        """Initializes bots. ALL workers initialize for sending; only leader polls."""
        if self._is_running:
            return

        logger.info("🤖 BotManager: Initializing bots...")
        self._is_running = True

        # Load settings
        client_token = get_setting_sync("client_bot_token")
        tech_token = get_setting_sync("telegram_bot_token")
        bot_mode = get_setting_sync("bot_execution_mode") or "auto"
        external_url = get_setting_sync("bot_external_url")

        # Determine if webhooks are used
        use_webhook = False
        if bot_mode == "webhook":
            use_webhook = True
        elif bot_mode == "auto" and external_url and external_url.startswith("https"):
            use_webhook = True

        # Try to become the Polling Leader (only relevant if not using webhooks)
        if not use_webhook:
            self._is_polling_leader = self._acquire_polling_lock()
            if self._is_polling_leader:
                logger.info("🏆 This worker is the POLLING LEADER.")
            else:
                logger.info("🔒 Polling handled by another worker. This worker can still send messages.")

        logger.info(f"🤖 BotManager: Mode={bot_mode}, Webhook={use_webhook}, Leader={self._is_polling_leader}")

        # --- Initialize Client Bot ---
        if client_token:
            try:
                self.client_app = create_client_app(client_token)
                await self.client_app.initialize()
                await self.client_app.start()

                if use_webhook and external_url:
                    hook_url = f"{external_url.rstrip('/')}/api/webhooks/client/{client_token}"
                    await self.client_app.bot.set_webhook(hook_url)
                    logger.info(f"✅ Client Bot Webhook set")
                elif self._is_polling_leader:
                    try:
                        await self.client_app.bot.delete_webhook()
                    except Exception:
                        pass
                    task = asyncio.create_task(self._polling_wrapper("ClientBot", self.client_app.updater))
                    self.polling_tasks.append(task)
                    logger.info("✅ Client Bot Polling started")
                else:
                    logger.info("✅ Client Bot initialized (send-only mode)")

            except Exception as e:
                logger.error(f"❌ Failed to start Client Bot: {e}")

        # --- Initialize Tech Bot ---
        if tech_token:
            try:
                self.tech_app = create_tech_app(tech_token)
                await self.tech_app.initialize()
                await self.tech_app.start()

                if use_webhook and external_url:
                    hook_url = f"{external_url.rstrip('/')}/api/webhooks/tech/{tech_token}"
                    await self.tech_app.bot.set_webhook(hook_url)
                    logger.info(f"✅ Tech Bot Webhook set")
                elif self._is_polling_leader:
                    try:
                        await self.tech_app.bot.delete_webhook()
                    except Exception:
                        pass
                    task = asyncio.create_task(self._polling_wrapper("TechBot", self.tech_app.updater))
                    self.polling_tasks.append(task)
                    logger.info("✅ Tech Bot Polling started")
                else:
                    logger.info("✅ Tech Bot initialized (send-only mode)")

            except Exception as e:
                logger.error(f"❌ Failed to start Tech Bot: {e}")

    async def stop(self):
        """Stops all bots and releases resources."""
        if not self._is_running:
            return

        logger.info("🤖 BotManager: Stopping bots...")
        self._is_running = False

        # Cancel polling tasks
        for task in self.polling_tasks:
            task.cancel()
        self.polling_tasks.clear()

        # Shutdown bot applications
        if self.client_app:
            try:
                await self.client_app.stop()
                await self.client_app.shutdown()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping Client Bot: {e}")
            self.client_app = None

        if self.tech_app:
            try:
                await self.tech_app.stop()
                await self.tech_app.shutdown()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping Tech Bot: {e}")
            self.tech_app = None

        # Release lock
        self._release_polling_lock()
        self._is_polling_leader = False

        logger.info("✅ BotManager: Stopped.")

    async def process_update(self, bot_type: str, token: str, update_data: dict):
        """Process incoming webhook update."""
        from telegram import Update

        app = None
        if bot_type == "client" and self.client_app:
            app = self.client_app
        elif bot_type == "tech" and self.tech_app:
            app = self.tech_app

        if app:
            if app.bot.token != token:
                logger.warning(f"⚠️ Webhook token mismatch for {bot_type}")
                return

            update = Update.de_json(update_data, app.bot)
            await app.process_update(update)


bot_manager = BotManager.get_instance()
