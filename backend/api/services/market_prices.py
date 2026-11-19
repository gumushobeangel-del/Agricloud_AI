import csv
import hashlib
import io
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


SOURCE_TITLE = "WFP Uganda Food Prices (HDX)"
SOURCE_URL = "https://data.humdata.org/dataset/wfp-food-prices-for-uganda"
CACHE_KEY = "market-intelligence:wfp-uganda:v1"
REQUIRED_COLUMNS = {
    "date", "admin1", "admin2", "market", "market_id", "commodity", "unit",
    "pricetype", "currency", "price",
}

# Only agricultural food commodities — crops, staples, and direct farm produce.
# Excludes non-food hardware, household items, and fuel from the WFP feed.
AGRICULTURAL_COMMODITIES = {
    "beans",
    "cassava (fresh)",
    "cassava flour",
    "fish (dry)",
    "groundnuts",
    "leafy vegetables",
    "maize (white)",
    "maize flour",
    "milk (fresh)",
    "millet",
    "millet flour",
    "oil (vegetable)",
    "rice",
    "salt",
    "sorghum",
    "sorghum flour",
    "sugar",
    "sweet potatoes",
    "tomatoes",
    "wheat flour",
}


class MarketDataError(Exception):
    pass


def fetch_wfp_prices():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        response = requests.get(settings.MARKET_DATA_CSV_URL, timeout=settings.MARKET_DATA_TIMEOUT)
        response.raise_for_status()
        text = response.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise MarketDataError("The WFP market-price feed returned an unexpected data format.")
        today = timezone.localdate()
        window_start = today - timedelta(days=365)
        prices = []
        for row in reader:
            try:
                observed_at = date.fromisoformat(row.get("date", ""))
                price = Decimal((row.get("price") or "").strip())
            except (InvalidOperation, TypeError, ValueError):
                continue
            commodity = (row.get("commodity") or "").strip()
            market = (row.get("market") or "").strip()
            district = (row.get("admin2") or row.get("admin1") or "Uganda").strip()
            unit = (row.get("unit") or "").strip()
            currency = (row.get("currency") or "").strip().upper()
            price_type = (row.get("pricetype") or "Unspecified").strip().title()
            if (
                not price.is_finite()
                or price <= 0
                or observed_at < window_start
                or observed_at > today
                or not commodity
                or commodity.casefold() not in AGRICULTURAL_COMMODITIES
                or not market
                or not unit
                or not currency
            ):
                continue
            identity = "|".join((
                row.get("market_id", ""),
                observed_at.isoformat(),
                commodity.casefold(),
                price_type.casefold(),
                format(price, "f"),
                unit.casefold(),
                currency,
            ))
            prices.append({
                "id": "wfp-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
                "commodity": commodity,
                "market": market,
                "district": district,
                "price": format(price, "f"),
                "unit": unit,
                "currency": currency,
                "observed_at": observed_at.isoformat(),
                "price_type": price_type,
                "source_title": SOURCE_TITLE,
                "source_url": SOURCE_URL,
            })
    except MarketDataError:
        raise
    except (requests.RequestException, UnicodeError, csv.Error, ValueError) as exc:
        raise MarketDataError("The WFP Uganda market-price feed is temporarily unavailable.") from exc

    prices.sort(key=lambda item: (item["observed_at"], item["commodity"], item["market"]), reverse=True)
    cache.set(CACHE_KEY, prices, settings.MARKET_DATA_CACHE_SECONDS)
    return prices
