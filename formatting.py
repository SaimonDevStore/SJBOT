from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aliexpress_client import Offer


def format_offer_message(offer: Offer, affiliate_link: str) -> str:
	highlight_parts = []
	if offer.coupon:
		highlight_parts.append(f"Cupom: {offer.coupon}")
	if offer.free_shipping:
		highlight_parts.append("Frete Grátis")
	highlight = " | ".join(highlight_parts) if highlight_parts else "Oferta"

	old_str = f"R$ {offer.old_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
	new_str = f"R$ {offer.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

	# Using HTML parse mode (Telegram)
	text = (
		f"🔥 <b>{escape_html(offer.title)}</b>\n"
		f"{escape_html(highlight)}\n\n"
		f"💵 De: {old_str} ➜ <b>{new_str}</b>\n"
		f"🎯 Desconto: <b>{int(offer.discount_pct)}%</b>"
	)
	if offer.coupon:
		text += f" • Cupom: <b>{escape_html(offer.coupon)}</b>"
	text += "\n"
	text += f"🚚 {'Frete Grátis' if offer.free_shipping else 'Consulte frete'}\n\n"
	text += f"🔗 <b>Link do produto:</b>\n{escape_html(affiliate_link)}\n\n"
	text += hashtags_line(offer)
	return text


def escape_html(s: str) -> str:
	return (
		s.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
	)


def hashtags_line(offer: Offer) -> str:
	base = ["#Promo", "#Desconto", "#AliExpress", "#Ofertas"]
	cats = []
	name = f"{offer.title} {offer.category}".lower()
	for tag in [
		("placa", "#PCGamer"),
		("ryzen", "#Processadores"),
		("gabinete", "#Gabinetes"),
		("gamer", "#Gamer"),
		("funko", "#FunkoPop"),
		("led", "#DecoTech"),
	]:
		if tag[0] in name:
			cats.append(tag[1])
	return " ".join(base + cats)


