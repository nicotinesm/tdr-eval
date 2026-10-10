---
title: TH DR Price Eval Tool
emoji: 📈
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---

# TH DR Price Evaluator (Web)

Streamlit web version of the desktop DR Price Evaluation Tool. Works on Android/iOS browsers.

- Pick a DR from the sidebar (search box filters case-insensitively).
- `Fetch Data` pulls live underlying price + FX (Yahoo → TradingView → open.er-api fallbacks, 60s cache).
- Edit price/FX manually — the 21-level SET-tick grid recalculates instantly.
- `Export CSV` downloads the grid (mobile-friendly, no file dialog).
- `Add / Edit DR` saves for the current session only (Hugging Face / Streamlit Cloud disks are ephemeral).

## Deploy

**Streamlit Community Cloud (free, recommended):** New app → point to
`web/app.py` as the main file; dependencies install from
`web/requirements.txt`. No Dockerfile needed.

**Hugging Face Spaces:** HF deprecated the Streamlit SDK (Apr 2025) and
Gradio/Docker Spaces require a paid plan (PRO/Team/Enterprise) even on
free CPU — only Static Spaces are free, and those are browser-only
(no Python, so this app cannot run there). Use Streamlit Cloud instead.
The included `Dockerfile` is only useful if you have a paid HF plan:
create a Docker-SDK Space and upload this folder unchanged.

## Run locally

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\streamlit.exe run app.py
```

## Mobile UX

Responsive layout for 360–430px phones: full-width fetch button (sidebar is
hidden behind the menu on mobile), 2-column metrics, swipeable grid with a
hint caption, 16px inputs (prevents iOS auto-zoom), 44–48px touch targets.

## Security

CSV export neutralizes formula-injection characters (`= + - @ | %`); the
Add/Edit form enforces strict input charsets; no secrets in the repo; all
HTTP uses TLS with timeouts.
