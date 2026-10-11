# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

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

- **`billy.py`** — the orderBilly client. orderBilly has no API; the code logs in by POSTing the manager form (`billy_session`) and detects failure by checking the redirect URL contains `dashboard` (login failures still return HTTP 200). `fetch_data` downloads a report as an Excel file from `/reports/report_download`; `order_data` parses the `orders_products` report with `pandas.read_excel(header=1, usecols=...)`. `count_products` sums `Product Amount` grouped by `Product Name`, matching each configured product as a **regex prefix** (`^{product}`), so variants like "Mosselen natuur" roll up under "Mosselen". If an order ID (or a `since` time) is given, it only counts orders placed after that order (or time) and returns the minutes since then. `order_data` reuses one logged-in session and logs in again once when a download fails; all requests use `TIMEOUT`.
- **`config.py`** — the per-event knobs, edited before each event:
  - `products`: ordered dict of product-name prefix → `{display, font_scale}`; order determines row order on screen. Note prefix overlap (e.g. a product named `Balletjes` would also match `Balletjes vegan`, but not `Vegan Balletjes`).
  - Shift-start lists per event (`vlms24`, `mf25`, `vlms25`, …) and `shift_starts = <current event>`. `main.start_of_shift()` picks the latest start that is in the past.
  - Billy credentials, read from env vars `BILLY_USERNAME`/`BILLY_PASSWORD`. A small built-in loader fills them from `.env` next to `config.py` (gitignored; template in `.env.example`, no python-dotenv dependency). Never hardcode them here.
- **`main.py`** — Kivy app. `DashboardApp` auto-loads `dashboard.kv` by naming convention (App class name minus `App`, lowercased), which styles `StatusBar`, `ProductLabel`, `AmountLabel`. Layout is sized for a portrait 1080×1920 screen scaled by `SCALE`, read from env var `DASHBOARD_SCALE` (default 0.3 for a desktop preview; the Pi's service sets 1). Product names too wide for their column get a smaller font (`ProductLabel.max_font_size`); the shift column is drawn at `shift_scale` of the amount font. Data refresh runs in a background thread every 7s (`Clock.schedule_interval`); UI updates go through the `@mainthread`-decorated `update_amounts`. When run as a script, the first download is started before Kivy is imported (`first_download`), because both take seconds on the Pi. The status-bar input filters the "Na order" column: an order number sets `order_id`, a time of up to 4 digits (`1830`, `18:30`; Billy order IDs are 8 digits) sets `since_time` (see `parse_time`), empty input clears it. The "Shift" column is never filtered. The top-right box shows the minutes since that order/time (orange from `WAIT_ORANGE`, red from `WAIT_RED`). State (`order_id`, `since_time`, `wait_time`) lives in module globals. The bottom line shows data freshness, the IP and a drawn `NetworkIcon`; WiFi/cable detection reads `/proc/net/*` and `/sys/class/net` on Linux (the Raspberry Pi), while Windows only gets online/offline.

## Deployment

The dashboard runs on a headless Raspberry Pi 4 (Kivy straight on KMS/DRM, no desktop) as `dashboard-kivy.service`. `docs/raspberry-pi.md` documents the Pi's configuration and a fresh install; `deploy/` holds the service file, Kivy screen config and `setup-pi.sh`. The code needs Kivy ≥ 2.3 (Debian 13 "trixie"); the old Pi still has Debian 12 with Kivy 2.1, whose Labels only accept 2-value `padding`.
