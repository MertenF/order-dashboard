# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Kivy kitchen/counter display for a scouts food event. It polls the orderBilly POS backend (`manager.orderbilly.com`) and shows, per configured product, how many units have been ordered since the current shift started (or since a specific order number). UI text is Dutch.

## Running

There is no build, lint, test suite, or requirements file. Use the local (untracked) virtualenv `.venv` (Python 3.12, Windows). Billy credentials must be set first: copy `.env.example` to `.env` (gitignored) or export `BILLY_USERNAME` / `BILLY_PASSWORD`.

```
.venv\Scripts\python.exe main.py      # the dashboard
.venv\Scripts\python.exe tables.py    # one-off: re-sort Billy tables numerically ("TAFEL n")
.venv\Scripts\python.exe stats.py     # one-off: plot cumulative orders (seaborn/matplotlib)
.venv\Scripts\python.exe billy.py     # quick smoke test of fetch + count
```

Key deps: kivy 2.3, pandas + openpyxl (Excel parsing), requests, bs4. `main-pyside.py` is an unused PySide6 experiment; `sunmi.py` is an unrelated UDP-multicast experiment for a Sunmi device.

## Architecture

- **`billy.py`** — the orderBilly client. orderBilly has no API; the code logs in by POSTing the manager form (`billy_session`) and detects failure by checking the redirect URL contains `dashboard` (login failures still return HTTP 200). `fetch_data` downloads a report as an Excel file from `/reports/report_download`; `order_data` parses the `orders_products` report with `pandas.read_excel(header=1, usecols=...)`. `count_products` sums `Product Amount` grouped by `Product Name`, matching each configured product as a **regex prefix** (`^{product}`), so variants like "Mosselen natuur" roll up under "Mosselen". If an order ID is given, it only counts orders placed after that order and returns the wait time in minutes.
- **`config.py`** — the per-event knobs, edited before each event:
  - `products`: ordered dict of product-name prefix → `{display, font_scale}`; order determines row order on screen. Note prefix overlap (e.g. a product named `Balletjes` would also match `Balletjes vegan`, but not `Vegan Balletjes`).
  - Shift-start lists per event (`vlms24`, `mf25`, `vlms25`, …) and `shift_starts = <current event>`. `main.start_of_shift()` picks the latest start that is in the past.
  - Billy credentials (`username`/`password`) — used by both `main.py` and `tables.py`.
- **`main.py`** — Kivy app. `DashboardApp` auto-loads `dashboard.kv` by naming convention (App class name minus `App`, lowercased), which styles `StatusBar`, `ProductLabel`, `AmountLabel`. Layout is sized for a portrait 1080×1920 screen scaled by `SCALE` (set to 0.3 for desktop dev; raise to 1 on the real display). Data refresh runs in a background thread every 7s (`Clock.schedule_interval`); UI updates go through the `@mainthread`-decorated `update_amounts`. Typing an order number in the status-bar input + Enter sets the module-global `order_id`, recounting only orders after it and showing the wait time. State (`order_id`, `wait_time`, `last_updated`) lives in module globals.
