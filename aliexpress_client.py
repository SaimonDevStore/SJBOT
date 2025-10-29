from __future__ import annotations

import hashlib
import hmac
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


ACCEPTED_CATEGORIES = {
	"electronics",
	"pc gamer",
	"acessórios gamer",
	"acessorios gamer",
	"gabinetes",
	"processadores",
	"placas de vídeo",
	"placas de video",
	"componentes de pc",
	"quarto",
	"decoração",
	"decoracao",
	"funko",
}


@dataclass
class Offer:
	product_id: str
	title: str
	old_price: float
	price: float
	discount_pct: float
	coupon: Optional[str]
	free_shipping: bool
	sales_count: int
	rating: float
	image_url: str
	product_url: str
	category: str


class AliExpressClient:
	def __init__(self, app_key: str, app_secret: str, tracking_id: str) -> None:
		self.app_key = app_key
		self.app_secret = app_secret
		self.tracking_id = tracking_id
		self.base_url = "https://api-sg.aliexpress.com/sync"  # Union Open Platform (SG endpoint)

	def _score(self, offer: Offer) -> float:
		score = 0.0
		score += offer.discount_pct * 2.0
		if offer.coupon:
			score += 20.0
		if offer.free_shipping:
			score += 10.0
		score += min(offer.sales_count / 50.0, 20.0)
		score += offer.rating
		return score

	def _passes_category(self, offer: Offer) -> bool:
		name = f"{offer.title} {offer.category}".lower()
		return any(cat in name for cat in ACCEPTED_CATEGORIES)

	def _affiliate(self, url: str) -> str:
		sep = "&" if "?" in url else "?"
		return f"{url}{sep}utm_source=telegram&utm_medium=bot&utm_campaign={self.tracking_id}"

	def _shorten(self, url: str) -> str:
		# simple deterministic shortener
		h = hashlib.sha256(url.encode()).hexdigest()[:8]
		return f"https://sjp.li/{h}"

	def _available(self, offer: Offer) -> bool:
		# lightweight availability check placeholder
		return True

	def fetch_top_offers(self, limit: int = 50) -> List[Offer]:
		if not (self.app_key and self.app_secret):
			# Fallback mock data to keep bot functional during setup
			return self._mock_offers(limit)

		# Try real API; on any error, fallback to mock
		try:
			items = self._api_product_query(limit=max(50, limit * 2))
			offers: List[Offer] = []
			for it in items:
				try:
					product_id = str(it.get("product_id") or it.get("item_id") or it.get("app_sale_price_id") or "")
					title = it.get("product_title") or it.get("title") or "Produto AliExpress"
					image_url = (it.get("product_main_image_url") or it.get("image_url") or "").replace("_640x640.jpg", "_Q90.jpg")
					# Only accept AliExpress CDN images; otherwise, leave empty to post text-only
					if image_url and not ("alicdn.com" in image_url or "aliexpress" in image_url):
						image_url = ""
					# Prices
					price_str = str(it.get("target_sale_price") or it.get("sale_price") or it.get("app_sale_price") or "0").replace(",", ".")
					old_str = str(it.get("target_original_price") or it.get("original_price") or it.get("app_original_price") or price_str).replace(",", ".")
					price = float(price_str) if price_str else 0.0
					old_price = float(old_str) if old_str else price
					discount_pct = max(0.0, round((1 - (price / old_price)) * 100, 2) if old_price else 0.0)
					# Metadata
					coupon = it.get("coupon_activity_id") or it.get("coupon_amount")
					free_shipping = bool(it.get("free_shipping", False))
					sales_count = int(it.get("product_sale_quantity") or it.get("sale_count") or 0)
					rating = float(it.get("evaluate_rate") or it.get("product_average_star") or 4.5)
					category = str(it.get("first_level_category_name") or it.get("category_name") or "eletronicos")
					url = it.get("product_detail_url") or it.get("promotion_link") or it.get("url") or ""
					if not url:
						# generate affiliate link later via generate_affiliate_link
						url = f"https://www.aliexpress.com/item/{product_id}.html"
					offers.append(
						Offer(
							product_id=product_id,
							title=title,
							old_price=old_price,
							price=price,
							discount_pct=discount_pct,
							coupon=(str(coupon) if coupon else None),
							free_shipping=free_shipping,
							sales_count=sales_count,
							rating=rating,
							image_url=image_url or "",
							product_url=url,
							category=category,
						)
					)
				except Exception as exc:
					logger.warning("AliExpress API parse error: %s", exc)
			if not offers:
				return self._mock_offers(limit)
			return offers[:limit]
		except Exception as exc:
			logger.exception("AliExpress API error: %s", exc)
			return self._mock_offers(limit)

	def generate_affiliate_link(self, offer: Offer) -> str:
		# If API already returned a promotional/affiliated URL, use it directly
		if any(x in (offer.product_url or "") for x in ["aff_", "affid", "aff_fcid", "aff_fsk", "aff_fcid", "aff_short_key", "affd", "ali_trackid", "pdp_npi"]):
			return offer.product_url
		try:
			link = self._api_link_generate(offer.product_url)
			if link:
				return link
		except Exception:
			logger.exception("Failed to generate affiliate link via API; using fallback short link")
		return self._shorten(self._affiliate(offer.product_url))

	def best_scored(self, limit: int = 25) -> List[Offer]:
		offers = [o for o in self.fetch_top_offers(limit * 3) if self._passes_category(o)]
		offers.sort(key=self._score, reverse=True)
		return offers[:limit]

	# ---- Mock data generator ----
	def _mock_offers(self, limit: int) -> List[Offer]:
		base_products = [
			("Placa de Vídeo RTX 4060 8GB", "placas de video"),
			("Processador Ryzen 5 5600G", "processadores"),
			("Gabinete ATX com RGB", "gabinetes"),
			("Teclado Mecânico Gamer", "acessorios gamer"),
			("Funko Pop Colecionável", "funko"),
			("Luminária LED de Mesa", "decoracao"),
		]
		offers: List[Offer] = []
		for i in range(limit):
			title, category = random.choice(base_products)
			old_price = round(random.uniform(150.0, 1500.0), 2)
			discount_pct = random.choice([10, 20, 30, 40, 50])
			price = round(old_price * (1 - discount_pct / 100.0), 2)
			coupon = random.choice([None, "R$20 OFF", "R$50 OFF", None])
			free_shipping = random.choice([True, False])
			sales = random.randint(5, 500)
			rating = round(random.uniform(3.5, 4.9), 1)
			pid = f"mock-{int(time.time())}-{i}-{random.randint(100,999)}"
			offers.append(
				Offer(
					product_id=pid,
					title=title,
					old_price=old_price,
					price=price,
					discount_pct=discount_pct,
					coupon=coupon,
					free_shipping=free_shipping,
					sales_count=sales,
					rating=rating,
					image_url="",
					product_url=f"https://www.aliexpress.com/item/{pid}.html",
					category=category,
				)
			)
		return offers

	# ---- Real API helpers ----
	def _top_sign(self, params: Dict[str, str]) -> str:
		# TOP-style HMAC-MD5 signature: sign = MD5(secret + concat(kv) + secret)
		joined = "".join(f"{k}{params[k]}" for k in sorted(params.keys()))
		data = (self.app_secret + joined + self.app_secret).encode()
		return hashlib.md5(data).hexdigest().upper()

	def _api_call(self, method: str, biz_params: Dict[str, object]) -> Dict[str, object]:
		common = {
			"app_key": self.app_key,
			"method": method,
			"sign_method": "md5",
			"timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
			"format": "json",
			"v": "2.0",
		}
		payload = {**common, "param": json.dumps(biz_params, ensure_ascii=False)}
		payload["sign"] = self._top_sign(payload)
		logger.info("AliExpress API call %s with params=%s", method, biz_params)
		resp = requests.post(self.base_url, data=payload, timeout=15)
		resp.raise_for_status()
		data = resp.json()
		logger.info("AliExpress API response %s: %s", method, str(data)[:800])
		return data

	def _api_product_query(self, limit: int) -> List[Dict[str, object]]:
		# Query by keywords and categories; use BR target
		keywords = [
			"RTX", "Ryzen", "Gabinete", "Teclado Mecânico", "Funko", "LED"
		]
		result_items: List[Dict[str, object]] = []
		for kw in keywords:
			try:
				res = self._api_call(
					"aliexpress.affiliate.product.query",
					{
						"keywords": kw,
						"target_language": "pt_BR",
						"target_currency": "BRL",
						"page_size": 20,
						"sort": "SALE_PRICE_ASC",
					},
				)
				# Response shape can vary; try common paths
				data = (
					res.get("aliexpress_affiliate_product_query_response")
					or res.get("resp")
					or res
				)
				items = (
					(data or {}).get("result")
					or (data or {}).get("products")
					or {}
				)
				products = items.get("products") if isinstance(items, dict) else items
				if isinstance(products, list):
					result_items.extend(products)
			except Exception:
				logger.warning("Product query failed for '%s'", kw)
		# De-dup by product_id
		seen = set()
		unique: List[Dict[str, object]] = []
		for it in result_items:
			pid = str(it.get("product_id") or it.get("item_id") or "")
			if pid and pid not in seen:
				unique.append(it)
				seen.add(pid)
		return unique[:limit]

	def _api_link_generate(self, url: str) -> Optional[str]:
		res = self._api_call(
			"aliexpress.affiliate.link.generate",
			{
				"promotion_link_type": "SHORT_LINK",
				"source_values": [url],
				"tracking_id": self.tracking_id,
			},
		)
		data = res.get("aliexpress_affiliate_link_generate_response") or res.get("resp") or res
		links = (data or {}).get("resp_result") or (data or {}).get("promotion_links") or {}
		if isinstance(links, dict):
			arr = links.get("promotion_links") or links.get("links") or []
		else:
			arr = links
		if isinstance(arr, list) and arr:
			link = arr[0].get("promotion_link") or arr[0].get("short_link_url") or arr[0].get("url")
			return link
		return None


