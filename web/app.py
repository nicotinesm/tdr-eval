"""TH DR Price Evaluator — Streamlit web version.

Deploy targets:
- Hugging Face Spaces (SDK: streamlit, app_file: app.py)
- Streamlit Community Cloud (main file: web/app.py)

Desktop parity: DR search, live fetch with fallbacks, 60s cache,
21-level SET-tick grid, manual price/FX edit, CSV download, Add/Edit DR
(session-scoped on cloud — filesystem is ephemeral).
"""

import csv
import io
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from data_fetcher import fetch_quote
from engine import CalculationEngine

# Strict charsets: values surface in logs, captions and the CSV file name.
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,19}$")
TICKER_RE = re.compile(r"^[A-Z0-9.:-]{1,20}$")
PAIR_RE = re.compile(r"^[A-Z]{3,7}=X$")
MARKET_RE = re.compile(r"^[A-Z]{1,10}$")

# OWASP CSV Injection: cells starting with these chars run as formulas in Excel.
_CSV_UNSAFE_LEADING = ("=", "+", "-", "@", "|", "%")


def _csv_cell(value) -> str:
    text = str(value)
    return "'" + text if text.startswith(_CSV_UNSAFE_LEADING) else text

st.set_page_config(
    page_title="DR Price Evaluator – Thailand",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

ENGINE = CalculationEngine()
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dr_config.json")

# Responsive CSS (static string, no user data): comfortable touch targets and
# readable type on phones. Inputs stay at 16px so iOS Safari does not auto-zoom.
st.markdown(
    """<style>
.stButton > button { min-height: 44px; }
@media (max-width: 640px) {
  html, body, [data-testid="stAppViewContainer"] { font-size: 17px; }
  [data-testid="stMetricValue"] > div { font-size: 1.6rem; }
  .stButton > button { min-height: 48px; width: 100%; font-size: 1rem; }
  input, textarea, select { font-size: 16px !important; }
  [data-testid="stDataFrame"] { font-size: 0.85rem; }
}
</style>""",
    unsafe_allow_html=True,
)

REQUIRED_KEYS = ("underlying_ticker", "currency_pair", "ratio")


@st.cache_data(ttl=300)
def load_registry() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def registry() -> dict:
    base = dict(load_registry())
    base.update(st.session_state.get("custom_drs", {}))
    return base


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cached(underlying: str, currency_pair: str, market: str, _force: int = 0):
    return fetch_quote(
        {"underlying_ticker": underlying, "currency_pair": currency_pair, "market": market}
    )


def fmt(v, dec=4):
    try:
        return f"{float(v):,.{dec}f}"
    except (TypeError, ValueError):
        return "-"


# ---------------- Sidebar: DR selection + parameters ----------------
with st.sidebar:
    st.header("Select DR")
    reg = registry()
    names = sorted(reg.keys())

    query = st.text_input("Search DR (e.g. aapl)", value=st.session_state.get("dr_query", "")).strip().upper()
    st.session_state["dr_query"] = query
    filtered = [n for n in names if query in n] if query else names
    if not filtered:
        st.warning(f"No DR matches '{query}'. Showing all.")
        filtered = names

    default_dr = st.session_state.get("dr_symbol", "AAPL01" if "AAPL01" in filtered else filtered[0])
    if default_dr not in filtered:
        default_dr = filtered[0]
    dr_symbol = st.selectbox("DR symbol", filtered, index=filtered.index(default_dr), label_visibility="collapsed")
    st.session_state["dr_symbol"] = dr_symbol
    cfg = reg[dr_symbol]

    st.caption(
        f"{cfg.get('name', '')} · {cfg.get('market', 'US')} · "
        f"Underlying `{cfg['underlying_ticker']}` · FX `{cfg['currency_pair']}` · Ratio `{cfg['ratio']}`"
    )

    col_f, col_r = st.columns(2)
    with col_f:
        do_fetch = st.button("🔄 Fetch Data", use_container_width=True)
    with col_r:
        if st.button("🧹 Clear cache", use_container_width=True):
            fetch_cached.clear()
            do_fetch = True

    if do_fetch:
        st.session_state["force_nonce"] = st.session_state.get("force_nonce", 0) + 1

    prev_dr = st.session_state.get("_prev_dr")
    if prev_dr != dr_symbol and "force_nonce" not in st.session_state:
        pass  # first auto-fetch below handles it
    st.session_state["_prev_dr"] = dr_symbol

    st.divider()
    st.header("Parameters")
    # Fetch (cached 60s, force via nonce)
    with st.spinner("Fetching live price & FX..."):
        result = fetch_cached(
            cfg["underlying_ticker"], cfg["currency_pair"], cfg.get("market", "US"),
            _force=st.session_state.get("force_nonce", 0),
        )

    if result.error:
        st.error(result.error)
    # seed editable fields from fetch on DR change / fetch success
    if result.price and result.fx_rate:
        if st.session_state.get("_seed_dr") != dr_symbol or do_fetch:
            st.session_state["ul_price"] = float(result.price)
            st.session_state["fx_rate"] = float(result.fx_rate)
            st.session_state["_seed_dr"] = dr_symbol

    ul = st.number_input("Underlying Price", min_value=0.0, value=float(st.session_state.get("ul_price", 0.0)), format="%.4f")
    fx = st.number_input("Exchange Rate (to THB)", min_value=0.0, value=float(st.session_state.get("fx_rate", 0.0)), format="%.4f")
    st.session_state["ul_price"] = ul
    st.session_state["fx_rate"] = fx
    st.number_input("Ratio (locked)", value=float(cfg["ratio"]), disabled=True)

    with st.expander("➕ Add / Edit DR"):
        with st.form("dr_editor"):
            symbol = st.text_input("DR Symbol *", value=dr_symbol)
            ticker = st.text_input("Underlying Ticker *", value=cfg["underlying_ticker"])
            pair = st.text_input("Currency Pair *", value=cfg["currency_pair"])
            ratio = st.number_input("Ratio *", min_value=0.0, value=float(cfg["ratio"]), format="%.4f")
            market = st.text_input("Market", value=cfg.get("market", "US"))
            name = st.text_input("Name", value=cfg.get("name", ""))
            submitted = st.form_submit_button("Save (this session)")
        if submitted:
            sym = symbol.strip().upper()
            tick = ticker.strip().upper()
            pr = pair.strip().upper()
            mkt = market.strip().upper()
            if not sym or not SYMBOL_RE.match(sym):
                st.error("DR Symbol must be 1-20 chars: A-Z, 0-9, . _ -")
            elif not tick or not TICKER_RE.match(tick):
                st.error("Underlying Ticker must be 1-20 chars: A-Z, 0-9, . : -")
            elif not pr or not PAIR_RE.match(pr):
                st.error("Currency Pair must look like THB=X or HKDTHB=X.")
            elif mkt and not MARKET_RE.match(mkt):
                st.error("Market must be 1-10 letters (e.g. US, HK, JP).")
            elif ratio <= 0:
                st.error("Ratio must be a positive number.")
            else:
                new_cfg = {"underlying_ticker": tick,
                           "currency_pair": pr, "ratio": float(ratio)}
                if mkt:
                    new_cfg["market"] = mkt
                if name.strip():
                    new_cfg["name"] = name.strip()[:60]
                customs = st.session_state.get("custom_drs", {})
                customs[sym] = new_cfg
                st.session_state["custom_drs"] = customs
                st.session_state["dr_symbol"] = sym
                st.session_state.pop("_seed_dr", None)
                st.success(f"Saved {sym} for this session. (Cloud disk is ephemeral — export config to keep it.)")
                st.rerun()

# ---------------- Main: iNAV + grid ----------------
st.title("DR Price Evaluator — Thailand")
st.caption("Indicative DR price (iNAV) = (Underlying × FX) / Ratio · 21 levels ±10 SET ticks")

# Primary fetch lives in the main view too: on phones the sidebar is hidden
# behind the hamburger menu, so mobile users get a full-width button here.
if st.button("🔄 Fetch live data", type="primary", use_container_width=True):
    st.session_state["force_nonce"] = st.session_state.get("force_nonce", 0) + 1
    st.rerun()

ratio = float(cfg["ratio"])
if ul <= 0 or fx <= 0:
    st.warning("Enter a positive underlying price and FX rate (or press Fetch Data).")
    st.stop()

try:
    levels = ENGINE.generate_price_table(ul, fx, ratio)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

center = next(l for l in levels if l.level == 0)
# Two metric columns (not three): a third column squeezes unreadably on
# 360-430px phone screens. The status line goes full-width underneath.
m1, m2 = st.columns(2)
m1.metric("iNAV (THB)", f"{center.dr_price:,.2f}")
m2.metric("Underlying (implied)", f"{center.underlying_price:,.4f}")
src = f"Price: {result.price_source} | FX: {result.fx_source}" if result and not result.error else "manual input"
ts = result.timestamp.strftime("%Y-%m-%d %H:%M:%S") if result and result.timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.info(f"Last update: {ts} [{src}] · {dr_symbol} ({cfg.get('name','')})")

rows = [
    {"Level": f"{l.level:+d}" if l.level else "0",
     "Underlying Price": round(l.underlying_price, 4),
     "FX": round(l.fx_rate, 4),
     "Raw DR (THB)": round(l.raw_dr, 4),
     "SET DR (Rounded)": round(l.dr_price, 2),
     "_center": l.level == 0}
    for l in levels
]

try:
    import pandas as pd

    df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    styled = df.style.apply(
        lambda _: ["background-color: #16a34a; color: white; font-weight: bold"
                   if c else "" for c in [r["_center"] for r in rows]], axis=0
    )
    st.caption("📱 On phones, swipe the table sideways to see all columns.")
    st.dataframe(
        styled,
        use_container_width=True,
        height=500,
        hide_index=True,
        column_config={
            "Level": st.column_config.TextColumn("Level", width="small"),
            "Underlying Price": st.column_config.NumberColumn("Underlying", format="%.4f"),
            "FX": st.column_config.NumberColumn("FX", format="%.4f", width="small"),
            "Raw DR (THB)": st.column_config.NumberColumn("Raw DR", format="%.4f"),
            "SET DR (Rounded)": st.column_config.NumberColumn("SET DR", format="%.2f"),
        },
    )
except ImportError:
    st.table([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])

buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["Level", "Underlying Price", "FX", "Raw DR (THB)", "SET DR (Rounded)"])
for r in rows:
    w.writerow([_csv_cell(r["Level"]), r["Underlying Price"], r["FX"], r["Raw DR (THB)"], r["SET DR (Rounded)"]])
st.download_button("⬇️ Export CSV", buf.getvalue().encode("utf-8-sig"),
                    file_name=f"DR_{dr_symbol}_price_grid.csv", mime="text/csv", use_container_width=False)

with st.expander("ℹ️ How it works / SET ticks"):
    st.markdown(
        "**iNAV (THB)** = (Underlying × FX) / Ratio. Center row = iNAV rounded half-up to the SET tick; "
        "±10 steps each advance by the tick of the current level.\n\n"
        "| DR Price (THB) | Tick |\n|---|---|\n"
        "| < 2 | 0.01 |\n| 2–<5 | 0.02 |\n| 5–<10 | 0.05 |\n"
        "| 10–<25 | 0.10 |\n| 25–<100 | 0.25 |\n| 100–<200 | 0.50 |\n"
        "| 200–<400 | 1.00 |\n| ≥ 400 | 2.00 |"
    )
