"""Data fetcher for web version (same fallback chain as desktop).

Price: Yahoo Finance -> TradingView Scanner
FX:    Yahoo Finance -> open.er-api.com -> TradingView Forex
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import requests

logger = logging.getLogger("dr_evaluator.data_fetcher")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
}

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


def fetch_quote(dr_config: dict) -> FetchResult:
    """Stateless fetch (no in-memory cache). Cache in Streamlit layer instead."""
    underlying = dr_config["underlying_ticker"]
    currency_pair = dr_config["currency_pair"]
    market = dr_config.get("market", "US")
    now = datetime.now()

    price, price_src = _fetch_price_with_fallbacks(underlying, market)
    fx_rate, fx_src = _fetch_fx_with_fallbacks(currency_pair)

    if price is None or fx_rate is None:
        missing = []
        if price is None:
            missing.append(f"underlying price ({underlying})")
        if fx_rate is None:
            missing.append(f"FX rate ({currency_pair})")
        msg = f"Failed to fetch {', '.join(missing)} from all data sources."
        logger.warning("Fetch incomplete for %s: price=%s, fx=%s", underlying, price, fx_rate)
        return FetchResult(None, None, now, error=msg)
    logger.info("Fetched %s: price=%.4f (%s), fx=%.4f (%s)", underlying, price, price_src, fx_rate, fx_src)
    return FetchResult(price=price, fx_rate=fx_rate, timestamp=now, price_source=price_src, fx_source=fx_src)


def _fetch_price_with_fallbacks(underlying: str, market: str) -> Tuple[Optional[float], str]:
    price = _fetch_price_yahoo(underlying)
    if price is not None and price > 0:
        return price, "Yahoo Finance"
    logger.info("Yahoo price missing for %s, trying TradingView...", underlying)
    price = _fetch_price_tradingview(underlying, market)
    if price is not None and price > 0:
        return price, "TradingView"
    return None, "None"


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


def _strip_exchange_suffix(ticker: str) -> str:
    t = ticker.strip().upper()
    for suffix in _EXCHANGE_SUFFIXES:
        if t.endswith(suffix):
            return ticker.strip()[: -len(suffix)]
    return ticker.strip()


def _tv_candidates(market: str, ticker: str) -> Tuple[str, list]:
    slug, prefixes = MARKET_TV.get(market, ("hongkong", ["HKEX:"]))
    base = _strip_exchange_suffix(ticker)
    return slug, [prefix + base for prefix in prefixes]


def _fetch_price_tradingview(underlying: str, market: str) -> Optional[float]:
    try:
        slug, tickers = _tv_candidates(market, underlying)
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


def _fetch_fx_with_fallbacks(currency_pair: str) -> Tuple[Optional[float], str]:
    fx = _fetch_fx_yahoo(currency_pair)
    if fx is not None and fx > 0:
        return fx, "Yahoo Finance"
    fx = _fetch_fx_open_er_api(currency_pair)
    if fx is not None and fx > 0:
        return fx, "open.er-api"
    fx = _fetch_fx_tradingview(currency_pair)
    if fx is not None and fx > 0:
        return fx, "TradingView"
    return None, "None"


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


def _fetch_fx_open_er_api(currency_pair: str) -> Optional[float]:
    try:
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
