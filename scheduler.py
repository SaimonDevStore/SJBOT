from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from aliexpress_client import AliExpressClient
from bot_core import BotCore
from config import Settings
from db import Database


logger = logging.getLogger(__name__)


class PostingScheduler:
    def __init__(self, settings: Settings, db: Database, ali: AliExpressClient, core: BotCore) -> None:
        self.settings = settings
        self.db = db
        self.ali = ali
        self.core = core
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self.consecutive_failures = 0

    def start(self) -> None:
        self.scheduler.start()
        # schedule hourly at minute 0
        self.scheduler.add_job(self._plan_next_hour, "cron", minute=0)
        # plan immediately for current partial hour
        self.scheduler.add_job(self._plan_next_hour, next_run_time=datetime.now(self.settings.timezone))

    def _in_window(self, now: datetime) -> bool:
        return 8 <= now.hour < 22

    def _get_hourly_bounds(self) -> (int, int):
        mn = int(self.db.get_state("min_per_hour", str(self.settings.min_per_hour_default)))
        mx = int(self.db.get_state("max_per_hour", str(self.settings.max_per_hour_default)))
        if mx < mn:
            mx = mn
        return mn, mx

    def _random_times_within_hour(self, now: datetime, n: int) -> List[datetime]:
        start = now.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        seconds = sorted(random.sample(range(0, 3600), k=min(n, 3600)))
        return [start + timedelta(seconds=s) for s in seconds if now <= start + timedelta(seconds=s) < end]

    def _plan_next_hour(self) -> None:
        now = datetime.now(self.settings.timezone)
        if self.db.get_state("paused", "0") == "1":
            logger.info("Bot paused; skipping schedule plan")
            return
        if not self._in_window(now):
            logger.info("Outside posting window; skipping hour plan")
            return

        mn, mx = self._get_hourly_bounds()
        n = random.randint(mn, mx)
        logger.info("Planning %s posts this hour", n)
        for when in self._random_times_within_hour(now, n):
            self.scheduler.add_job(self._post_one, trigger=DateTrigger(run_date=when))

    async def _post_one(self) -> None:
        if self.db.get_state("paused", "0") == "1":
            return
        # fetch best current offers
        offers = self.ali.best_scored(limit=20)
        posted = False
        for offer in offers:
            if not self.ali._available(offer):
                continue
            if await self.core.post_offer(offer):
                posted = True
                break
        if not posted:
            self.consecutive_failures += 1
            logger.warning("No offer posted in this attempt. Failure count=%s", self.consecutive_failures)
            if self.consecutive_failures >= 5:
                self.db.set_state("paused", "1")
                await self.core.notify_admins("Bot pausado automaticamente após 5 falhas consecutivas de postagem.")
        else:
            self.consecutive_failures = 0


