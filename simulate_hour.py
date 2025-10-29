import asyncio
import logging
from datetime import datetime, timedelta

from aliexpress_client import AliExpressClient
from bot_core import BotCore
from config import Settings
from db import Database
from logger import setup_logging


async def simulate(n: int = 5) -> None:
	settings = Settings.load()
	setup_logging(settings.log_dir)
	logging.info("Simulating %s posts within one hour...", n)
	db = Database(settings.database_path)
	ali = AliExpressClient(settings.app_key, settings.app_secret, settings.tracking_id)
	core = BotCore(settings, db, ali, send_enabled=False)

	offers = ali.best_scored(limit=max(20, n * 3))
	count = 0
	for offer in offers:
		ok = await core.post_offer(offer)
		if ok:
			count += 1
		if count >= n:
			break

	logging.info("Simulation done. Posted %s offers.", count)
	db.close()


if __name__ == "__main__":
	asyncio.run(simulate())


