"""Data fetcher for underlying prices and foreign-exchange rates.

Provides a multi-source fallback chain (all endpoints verified working):
1. Price: Yahoo Finance (primary) -> TradingView Scanner (fallback)
2. FX:    Yahoo Finance (primary)  -> open.er-api.com (fallback) -> TradingView Forex (fallback)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import requests
from cachetools import TTLCache

from utils.logger import get_logger, safe

logger = get_logger("data_fetcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}

# TradingView scanner market slug + candidate exchange prefixes per DR market.
# Multiple prefixes are probed in one scanner request (e.g. NASDAQ vs NYSE).
MARKET_TV = {
    "US": ("america", ["NASDAQ:", "NYSE:", "AMEX:"]),
    "HK": ("hongkong", ["HKEX:"]),
    "JP": ("asia", ["TSE:"]),
    "CN": ("asia", ["SSE:", "SZSE:"]),
    "SG": ("asia", ["SGX:"]),
    "FR": ("europe", ["EURONEXT:"]),
    "DE": ("europe", ["XETR:", "EURONEXT:"]),
    "DK": ("europe", ["CPH:"]),
    "TW": ("taiwan", ["TWSE:"]),
    "VN": ("vietnam", ["HOSE:", "HNX:"]),
}

_EXCHANGE_SUFFIXES = (".HK", ".T", ".SS", ".SZ", ".SI", ".PA", ".DE", ".CO", ".TW", ".VN")


@dataclass
class FetchResult:
    price: Optional[float]
    fx_rate: Optional[float]
    timestamp: datetime
    error: Optional[str] = None
    price_source: str = "Unknown"
    fx_source: str = "Unknown"


class YahooFinanceFetcher:
    def __init__(self, cache_ttl: int = 60):
        self.cache: TTLCache = TTLCache(maxsize=64, ttl=cache_ttl)
        self.cache_ttl = cache_ttl

    def fetch(self, dr_config: dict) -> FetchResult:
        underlying = dr_config["underlying_ticker"]
        currency_pair = dr_config["currency_pair"]
        market = dr_config.get("market", "US")
        cache_key = (underlying, currency_pair)
        now = datetime.now()

        cached = self.cache.get(cache_key)
        if cached is not None:
            price, fx_rate, fetched_at, p_src, fx_src = cached
            return FetchResult(
                price=price,
                fx_rate=fx_rate,
                timestamp=fetched_at,
                price_source=p_src + " (cached)",
                fx_source=fx_src + " (cached)",
            )

        # 1. Fetch price via fallback chain
        price, price_src = self._fetch_price_with_fallbacks(underlying, market)

        # 2. Fetch FX via fallback chain
        fx_rate, fx_src = self._fetch_fx_with_fallbacks(currency_pair)

        if price is None or fx_rate is None:
            missing = []
            if price is None:
                missing.append(f"underlying price ({underlying})")
            if fx_rate is None:
                missing.append(f"FX rate ({currency_pair})")
            msg = f"Failed to fetch {', '.join(missing)} from all data sources."
            logger.warning("Fetch incomplete for %s: price=%s, fx=%s", safe(underlying), price, fx_rate)
            return FetchResult(None, None, now, error=msg)

        self.cache[cache_key] = (price, fx_rate, now, price_src, fx_src)
        logger.info(
            "Fetched %s: price=%.4f (%s), fx=%.4f (%s)",
            safe(underlying),
            price,
            price_src,
            fx_rate,
            fx_src,
        )
        return FetchResult(
            price=price,
            fx_rate=fx_rate,
            timestamp=now,
            price_source=price_src,
            fx_source=fx_src,
        )

    # ------------------------------------------------ Price Fallback Chain
    def _fetch_price_with_fallbacks(
        self, underlying: str, market: str
    ) -> Tuple[Optional[float], str]:
        # Provider 1: Yahoo Finance
        price = self._fetch_price_yahoo(underlying)
        if price is not None and price > 0:
            return price, "Yahoo Finance"

        logger.info("Yahoo Finance price missing for %s, trying TradingView...", safe(underlying))
        # Provider 2: TradingView
        price = self._fetch_price_tradingview(underlying, market)
        if price is not None and price > 0:
            return price, "TradingView"

        logger.info("TradingView price missing for %s, no more price fallbacks", safe(underlying))
        return None, "None"

    @staticmethod
    def _fetch_price_yahoo(underlying: str) -> Optional[float]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(underlying)
            hist = ticker.history(period="1d", interval="1m", prepost=True, auto_adjust=False)
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            fast = ticker.fast_info
            if hasattr(fast, "last_price") and fast.last_price is not None:
                return float(fast.last_price)
        except Exception as exc:
            logger.debug("_fetch_price_yahoo error for %s: %s", underlying, exc)
        return None

    @staticmethod
    def _strip_exchange_suffix(ticker: str) -> str:
        t = ticker.strip().upper()
        for suffix in _EXCHANGE_SUFFIXES:
            if t.endswith(suffix):
                return ticker.strip()[: -len(suffix)]
        return ticker.strip()

    @classmethod
    def _tv_candidates(cls, market: str, ticker: str) -> Tuple[str, list]:
        """Map a DR market to a scanner slug and candidate TradingView tickers.

        Returns (market_slug, [ticker candidates]); the scanner request probes
        every candidate and the first non-null close wins.
        """
        slug, prefixes = MARKET_TV.get(market, ("hongkong", ["HKEX:"]))
        base = cls._strip_exchange_suffix(ticker)
        return slug, [prefix + base for prefix in prefixes]

    @staticmethod
    def _fetch_price_tradingview(underlying: str, market: str) -> Optional[float]:
        try:
            slug, tickers = YahooFinanceFetcher._tv_candidates(market, underlying)
            url = f"https://scanner.tradingview.com/{slug}/scan"
            payload = {"symbols": {"tickers": tickers}, "columns": ["close"]}
            r = requests.post(url, json=payload, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for item in data:
                    if "d" in item and item["d"][0] is not None:
                        return float(item["d"][0])
        except Exception as exc:
            logger.debug("_fetch_price_tradingview error for %s: %s", underlying, exc)
        return None

    # -------------------------------------------------- FX Fallback Chain
    def _fetch_fx_with_fallbacks(
        self, currency_pair: str
    ) -> Tuple[Optional[float], str]:
        # Provider 1: Yahoo Finance
        fx = self._fetch_fx_yahoo(currency_pair)
        if fx is not None and fx > 0:
            return fx, "Yahoo Finance"

        logger.info("Yahoo Finance FX missing for %s, trying open.er-api.com...", safe(currency_pair))
        # Provider 2: open.er-api.com
        fx = self._fetch_fx_open_er_api(currency_pair)
        if fx is not None and fx > 0:
            return fx, "open.er-api"

        logger.info("open.er-api missing for %s, trying TradingView Forex...", safe(currency_pair))
        # Provider 3: TradingView Forex
        fx = self._fetch_fx_tradingview(currency_pair)
        if fx is not None and fx > 0:
            return fx, "TradingView"

        return None, "None"

    @staticmethod
    def _fetch_fx_yahoo(currency_pair: str) -> Optional[float]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(currency_pair)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            fast = ticker.fast_info
            if hasattr(fast, "last_price") and fast.last_price is not None:
                return float(fast.last_price)
        except Exception as exc:
            logger.debug("_fetch_fx_yahoo error for %s: %s", currency_pair, exc)
        return None

    @staticmethod
    def _fetch_fx_open_er_api(currency_pair: str) -> Optional[float]:
        try:
            # Pair e.g. "THB=X" -> USD/THB, "HKDTHB=X" -> HKD/THB
            clean = currency_pair.replace("=X", "")
            base_curr = "USD"
            if clean.endswith("THB") and len(clean) > 3:
                base_curr = clean[:-3]

            url = f"https://open.er-api.com/v6/latest/{base_curr}"
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                j = r.json()
                if j.get("result") == "success":
                    rates = j.get("rates", {})
                    if "THB" in rates:
                        return float(rates["THB"])
        except Exception as exc:
            logger.debug("_fetch_fx_open_er_api error for %s: %s", currency_pair, exc)
        return None

    @staticmethod
    def _fetch_fx_tradingview(currency_pair: str) -> Optional[float]:
        try:
            clean = currency_pair.replace("=X", "")
            pair_code = "USDTHB" if clean == "THB" else clean
            url = "https://scanner.tradingview.com/forex/scan"
            payload = {
                "symbols": {"tickers": [f"FX_IDC:{pair_code}", f"FX:{pair_code}", pair_code]},
                "columns": ["close"],
            }
            r = requests.post(url, json=payload, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for item in data:
                    if "d" in item and item["d"][0] is not None:
                        return float(item["d"][0])
        except Exception as exc:
            logger.debug("_fetch_fx_tradingview error for %s: %s", currency_pair, exc)
        return None

    def invalidate(self, underlying: str, currency_pair: str):
        key = (underlying, currency_pair)
        if key in self.cache:
            del self.cache[key]
