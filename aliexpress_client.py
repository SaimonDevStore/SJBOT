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

        # Placeholder: integrate official API here if available.
        # Since signature/auth specifics vary, keep robust fallback to avoid runtime errors.
        try:
            # TODO: Implement real API request. Using mock for now to ensure stability.
            offers = self._mock_offers(limit)
            return offers
        except Exception as exc:
            logger.exception("AliExpress API error: %s", exc)
            return []

    def generate_affiliate_link(self, offer: Offer) -> str:
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
                    image_url="https://i.imgur.com/Z6X8bQk.png",
                    product_url=f"https://www.aliexpress.com/item/{pid}.html",
                    category=category,
                )
            )
        return offers


