import asyncio
import logging

from aiogram.enums import ParseMode

from aliexpress_client import AliExpressClient
from bot_core import BotCore
from config import Settings
from db import Database
from logger import setup_logging
from formatting import format_offer_message


async def post_one() -> None:
    settings = Settings.load()
    setup_logging(settings.log_dir)
    db = Database(settings.database_path)
    ali = AliExpressClient(settings.app_key, settings.app_secret, settings.tracking_id)
    core = BotCore(settings, db, ali, send_enabled=True)

    offers = ali.best_scored(limit=10)
    if not offers:
        print("No offers available")
        return
    # Try photo; on failure, send text-only
    for offer in offers:
        ok = await core.post_offer(offer)
        if ok:
            break

    db.close()


if __name__ == "__main__":
    asyncio.run(post_one())


