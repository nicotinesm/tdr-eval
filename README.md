# DR Price Evaluation Tool (Thailand Market)

A standalone desktop application for evaluating the indicative price (iNAV) of
Thai-listed **Depositary Receipts (DRs)**. Pick any DR, fetch the live
underlying stock price and FX rate, and instantly see a 21-level pricing grid
(±10 ticks around the current price) with SET tick rounding.

## Features

- Auto-discovery of all Thai DRs from `dr_config.json` (editable, no code changes needed)
- **Built-in DR editor** — register new DRs or edit existing ones from the UI (`Add / Edit` button); saved straight back to `dr_config.json` and the list refreshes instantly
- One-click fetch of live underlying price & FX rate
- **Multi-source fallback chain** — never blocked by a single provider outage:
  - Price: Yahoo Finance → TradingView Scanner
  - FX: Yahoo Finance → open.er-api.com → TradingView Forex
- **Non-blocking background fetch** — UI stays responsive while data loads
- **Race-condition guard** — fast DR switching discards stale fetch results
- 60-second result cache to avoid rate-limiting (manual **Fetch Data** bypasses it for a live refresh)
- Instant recalculation when you edit the underlying price or FX rate (200 ms debounce)
- Proper **half-up rounding** to Stock Exchange of Thailand tick sizes (using `Decimal` arithmetic to avoid float artifacts)
- **Dark theme by default** — light/dark switch remembered via `QSettings`
- **Left/right layout** — DR selector + parameters in a fixed sidebar; the price grid gets the full remaining width
- **Case-insensitive DR search** — type `aapl`, `AAPL` or `AapL` and the autocomplete still matches `AAPL01`
- Export the price grid to CSV
- Keyboard shortcuts: `Ctrl+F` (focus DR search), `Ctrl+R` (fetch), Tab (navigate parameters)
- Rotating log file (`dr_evaluator.log`)

## Data Sources

| Asset | Primary | Fallback 1 | Fallback 2 |
|-------|---------|-----------|------------|
| Equity price (US, HK, JP, CN, SG, FR, DE, DK, TW, VN) | Yahoo Finance | TradingView Scanner | — |
| FX rate (USD/THB, HKD/THB, JPY/THB, …) | Yahoo Finance | open.er-api.com | TradingView Forex |

The app reports which data source was used in the "Last update" status line.

## Requirements

- Python 3.11+ (tested with 3.13)
- A virtual environment is provided at `.venv`

## Setup

```powershell
# from the project root
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running

```powershell
.venv\Scripts\python.exe main.py
```

Or double-click `run.bat`.

## Running Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## How it works

The current indicative DR price (iNAV) is:

```
iNAV (THB) = (Underlying_Price x FX_Rate) / Ratio
```

The center row (level `0`) is the iNAV rounded **half-up** to the SET tick for
its price band (using `Decimal` arithmetic — no float artifacts). The grid
covers 21 DR-price levels (`-10` … `0` … `+10`). Each step advances by the SET
tick applicable to the *current* level's price, so every quoted price is a
valid SET price even when the range crosses a tick band (e.g. `…1.99 → 2.00 →
2.02 → 2.04…`). For each level the implied underlying price is derived back
from the DR price:

```
Implied_Underlying = (DR_Price x Ratio) / FX_Rate
```

Columns: **Level** (tick offset), **Underlying Price** (implied), **FX**,
**Raw DR (THB)** (unrounded iNAV at that level — because the grid steps in SET
ticks it equals the tick-aligned value), **SET DR (Rounded)** (the tick-aligned
DR price). The tick size for each price band:

| DR Price Range (THB) | Tick (THB) |
|----------------------|-----------|
| < 2                  | 0.01      |
| 2 – < 5              | 0.02      |
| 5 – < 10             | 0.05      |
| 10 – < 25            | 0.10      |
| 25 – < 100           | 0.25      |
| 100 – < 200          | 0.50      |
| 200 – < 400          | 1.00      |
| ≥ 400                | 2.00      |

## Adding a new DR

Two ways:

**From the UI (recommended):** click **Add / Edit** in the sidebar, fill in the
DR symbol, underlying ticker, currency pair, ratio (and optionally market,
name, tick size), then **Save**. The entry is written to `dr_config.json` and
the list refreshes immediately. Editing an existing DR: select it first, then
**Add / Edit** opens the form pre-filled.

**Manually:** open `dr_config.json` and append an entry:

```json
"TSLA80": {
    "underlying_ticker": "TSLA",
    "currency_pair": "THB=X",
    "ratio": 5,
    "market": "US",
    "underlying_tick_size": 0.01,
    "name": "Tesla DR"
}
```

Restart the application — no code changes required.

Only `underlying_ticker`, `currency_pair` and `ratio` are required; `market`,
`name` and `underlying_tick_size` are optional metadata. The grid uses the SET
tick derived from the DR's iNAV — `underlying_tick_size` is informational and
not used by the calculation.

### FX ticker format
- US stocks → `THB=X` (USD/THB)
- Hong Kong stocks → `HKDTHB=X` (HKD/THB)
- Other currencies → `<ISO3>THB=X` (e.g. `SGDTHB=X`)

## Packaging as a Windows .exe

```powershell
.venv\Scripts\python.exe -m PyInstaller build.spec --noconfirm
```

The bundle is created in `dist\DRPriceEvaluator\`. Keep `dr_config.json` next
to the executable (the app looks for it in its own directory first).

## Web version (mobile-friendly)

A Streamlit port lives in `web/` — self-contained (own copies of the engine,
fetcher and registry), verified with headless tests, with a responsive layout
for Android/iOS browsers: full-width fetch button, 2-column metrics, swipeable
price grid, 16px inputs (no iOS auto-zoom) and 48px touch targets.

## Deploying the web version (free)

Push to GitHub, then deploy via **Streamlit Community Cloud**: New app →
select the repo → main file `web/app.py`. Dependencies install from
`web/requirements.txt`. The site rebuilds automatically on every push to the
linked branch (`main`).

Note: Hugging Face Spaces is not free for this app — the Streamlit SDK was
deprecated (Apr 2025) and Docker/Gradio Spaces require a paid plan. Only
Static Spaces are free, and those cannot run Python.

## Security notes

- CSV export sanitizes `= + - @ | %` leading characters (formula-injection safe).
- The DR editor enforces strict input charsets; error labels render as plain text.
- Log lines neutralize CR/LF injection from user-controlled values.
- `dr_config.json` is written atomically (temp file + replace).
- All HTTP uses TLS with timeouts; no secrets or credentials in the repo.

## Project layout

```
├── main.py               Entry point
├── app_controller.py     Controller / signal wiring (+ async fetch)
├── config.py             DRConfig (reads dr_config.json)
├── data_fetcher.py       Multi-provider data fetcher with fallback chain
├── engine.py             iNAV grid generation (21 levels)
├── dr_config.json        DR registry
├── ui/
│   ├── main_window.py    MainWindow (left/right layout, themes, DR editor trigger)
│   ├── dr_search.py      Autocomplete DR selector
│   ├── param_panel.py    Editable parameter inputs
│   ├── price_table.py    Price grid table + CSV export
│   ├── dr_editor.py      Register/edit DR dialog
│   ├── fetch_worker.py   QThread for non-blocking background fetch
│   └── styles/           QSS themes (light/dark)
├── utils/
│   ├── set_tick.py       SET tick rounding (Decimal half-up)
│   ├── debounce.py       Input debounce utility
│   └── logger.py         Rotating file logger
├── tests/
│   ├── test_engine.py    Unit tests for calculation engine
│   └── test_set_tick.py  Unit tests for SET tick logic
├── web/                  Streamlit web version (mobile-friendly)
│   ├── app.py            Web app (search, live fetch, 21-level grid, CSV export)
│   ├── engine.py / set_tick.py / data_fetcher.py  Self-contained core logic
│   ├── dr_config.json    DR registry copy
│   ├── requirements.txt  Web dependencies
│   ├── Dockerfile        Optional HF Docker-SDK deploy (paid plan required)
│   └── .streamlit/config.toml  Dark theme
├── build.spec            PyInstaller spec
├── requirements.txt
└── .gitignore
```
