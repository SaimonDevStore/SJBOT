import asyncio
import logging

from aiogram import Dispatcher

from aliexpress_client import AliExpressClient
from bot_core import BotCore
from config import Settings
from db import Database
from logger import setup_logging
from scheduler import PostingScheduler


async def main() -> None:
    settings = Settings.load()
    setup_logging(settings.log_dir)
    logging.getLogger(__name__).info("Starting bot...")

    db = Database(settings.database_path)
    ali = AliExpressClient(settings.app_key, settings.app_secret, settings.tracking_id)
    core = BotCore(settings, db, ali)
    sched = PostingScheduler(settings, db, ali, core)
    sched.start()

    try:
        await core.dp.start_polling(core.bot)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())


