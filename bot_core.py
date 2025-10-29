from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, URLInputFile
from aiogram.client.default import DefaultBotProperties

from aliexpress_client import AliExpressClient
from config import Settings
from db import Database
from formatting import format_offer_message


logger = logging.getLogger(__name__)


class BotCore:
	def __init__(self, settings: Settings, db: Database, ali: AliExpressClient, send_enabled: bool = True) -> None:
		self.settings = settings
		self.db = db
		self.ali = ali
		self.send_enabled = send_enabled
		self.bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
		self.dp = Dispatcher()
		self._register_handlers()

	# ---- Handlers ----
	def _register_handlers(self) -> None:
		@self.dp.message(Command("status"))
		async def status_handler(message: Message) -> None:
			if not self._is_admin(message.from_user.id if message.from_user else 0):
				return
			paused = self.db.get_state("paused", "0") == "1"
			min_h = self.db.get_state("min_per_hour") or str(self.settings.min_per_hour_default)
			max_h = self.db.get_state("max_per_hour") or str(self.settings.max_per_hour_default)
			recent = self.db.get_recent_posts(5)
			lines = [
				f"Bot: {'PAUSADO' if paused else 'ATIVO'}",
				f"Janela: 06:00-22:00 {self.settings.timezone.key}",
				f"Frequência: {min_h}-{max_h} por hora",
				"Últimos posts:",
			]
			for pid, ts, price in recent:
				lines.append(f"• {pid} @ {ts} (R$ {price or 0:.2f})")
			await message.answer("\n".join(lines))

		@self.dp.message(Command("pausar"))
		async def pause_handler(message: Message) -> None:
			if not self._is_admin(message.from_user.id if message.from_user else 0):
				return
			self.db.set_state("paused", "1")
			await message.answer("Postagens automáticas pausadas.")

		@self.dp.message(Command("retomar"))
		async def resume_handler(message: Message) -> None:
			if not self._is_admin(message.from_user.id if message.from_user else 0):
				return
			self.db.set_state("paused", "0")
			await message.answer("Postagens automáticas retomadas.")

		@self.dp.message(Command("freq"))
		async def freq_handler(message: Message) -> None:
			if not self._is_admin(message.from_user.id if message.from_user else 0):
				return
			try:
				parts = message.text.split()
				if len(parts) != 3:
					await message.answer("Uso: /freq min max")
					return
				mn = int(parts[1])
				mx = int(parts[2])
				if mn <= 0 or mx < mn:
					await message.answer("Valores inválidos.")
					return
				self.db.set_state("min_per_hour", str(mn))
				self.db.set_state("max_per_hour", str(mx))
				await message.answer(f"Frequência atualizada para {mn}-{mx}/h.")
			except Exception:
				await message.answer("Erro ao processar. Uso: /freq 15 20")

		@self.dp.message(Command("postnow"))
		async def postnow_handler(message: Message) -> None:
			if not self._is_admin(message.from_user.id if message.from_user else 0):
				return
			offers = self.ali.best_scored(limit=20)
			for offer in offers:
				ok = await self.post_offer(offer)
				if ok:
					await message.answer("Post enviado.")
					return
			await message.answer("Nenhuma oferta publicada agora (sem estoque/duplicada/erro).")

	def _is_admin(self, user_id: int) -> bool:
		return user_id in self.settings.admin_ids

	# ---- Posting ----
	async def post_offer(self, offer) -> bool:
		now = datetime.now(self.settings.timezone)
		# No repost within 48h unless significant change; simplified check here.
		since = now - timedelta(hours=48)
		if self.db.posted_within(offer.product_id, since):
			return False

		caption = format_offer_message(offer, self.ali.generate_affiliate_link(offer))
		try:
			if self.send_enabled:
				await self.bot.send_photo(
					chat_id=self.settings.channel_id,
					photo=offer.image_url,
					caption=caption,
				)
			else:
				logger.info("[DRY-RUN] Would post: %s", offer.product_id)
		except Exception as exc:
			logger.exception("Failed to post photo for %s, falling back to text: %s", offer.product_id, exc)
			if self.send_enabled:
				try:
					await self.bot.send_message(chat_id=self.settings.channel_id, text=caption)
				except Exception as exc2:
					logger.exception("Text fallback also failed for %s: %s", offer.product_id, exc2)
					return False
		# record as posted if either path worked
		self.db.record_post(offer.product_id, now, offer.price, offer.coupon)
		return True

	async def notify_admins(self, text: str) -> None:
		for admin_id in self.settings.admin_ids:
			try:
				await self.bot.send_message(chat_id=admin_id, text=text)
			except Exception:
				logger.warning("Could not notify admin %s", admin_id)
