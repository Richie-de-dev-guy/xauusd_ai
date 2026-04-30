# AurumEdge — Trading Bot & Dashboard

A trend-following automated trading bot for Gold (XAUUSD) on Exness MT5,
paired with a real-time web dashboard (FastAPI backend + Next.js frontend).
Uses EMA crossover + RSI momentum filter + ATR-based risk management,
with an H4 trend filter, news blackout window, and built-in backtesting tools.

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Running the Live Bot](#4-running-the-live-bot)
5. [Running the Dashboard API](#5-running-the-dashboard-api)
6. [Running the Frontend](#6-running-the-frontend)
7. [Admin Dashboard Features](#7-admin-dashboard-features)
8. [Exporting Data from MT5](#8-exporting-data-from-mt5)
9. [Backtesting](#9-backtesting)
10. [EMA Optimization](#10-ema-optimization)
11. [Strategy Overview](#11-strategy-overview)
12. [File Reference](#12-file-reference)
13. [Dashboard Feature Roadmap](#13-dashboard-feature-roadmap)

---

## 1. Requirements

| App | Purpose | Download |
|---|---|---|
| MetaTrader 5 | Trading platform (Exness) | Via Exness Personal Area |
| Python 3.10+ | Runs the bot and dashboard API | python.org/downloads |
| Node.js 18+ | Dashboard frontend (Next.js) | nodejs.org |
| VS Code (optional) | Edit config files | code.visualstudio.com |

> **Note:** The `MetaTrader5` Python library is Windows-only. The dashboard API can run on any OS, but the bot runner requires Windows to connect to MT5.

---

## 2. Installation

### Step 1 — Install MetaTrader 5
- Log in to exness.com and download MT5 from your Personal Area
- Open MT5 and log in with your Exness trading account credentials
- Make sure `XAUUSDm` is visible in the Market Watch panel

### Step 2 — Install Python
- Download Python 3.10, 3.11, or 3.12 from python.org/downloads
- **Important:** check "Add Python to PATH" during installation
- Verify in Command Prompt: `python --version`

### Step 3 — Install Frontend Dependencies

```
cd dashboard
npm install
cd ..
```

### Step 4 — Install Python Dependencies

```
pip install -r requirements.txt
```

This installs everything needed for both the trading bot and the dashboard API
(MetaTrader5, pandas, FastAPI, SQLAlchemy, JWT auth, WebSocket support, etc.).

### Step 5 — Configure Environment

Copy the example env file and fill in your values:

```
cp .env.example .env
```

Key variables to set:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random 64-char hex string for JWT signing |
| `DASHBOARD_USERNAME` | Login username for the web dashboard |
| `DASHBOARD_PASSWORD` | Login password (plain text for dev, bcrypt hash for prod) |
| `CORS_ORIGINS` | Frontend URL allowed to connect (default: `http://localhost:3000`) |
| `DATABASE_URL` | SQLite default: `sqlite+aiosqlite:///./sentinel.db` |

---

## 3. Configuration

Open `config.py` and fill in your credentials and adjust any parameters:

```python
# MT5 account (required)
MT5_LOGIN    = 12345678
MT5_PASSWORD = "your_password"
MT5_SERVER   = "Exness-MT5Trial9"
MT5_PATH     = r"C:\Program Files\MetaTrader 5\terminal64.exe"
```

Key settings you may want to change:

| Setting | Default | Description |
|---|---|---|
| `TIMEFRAME` | `H1` | Entry timeframe. Options: M15, M30, H1, H4 |
| `HTF_TIMEFRAME` | `H4` | Higher timeframe used for trend confirmation |
| `FAST_EMA_PERIOD` | `9` | Fast EMA period (update after running optimizer) |
| `SLOW_EMA_PERIOD` | `21` | Slow EMA period (update after running optimizer) |
| `RISK_PERCENT_PER_TRADE` | `1.0` | % of balance risked per trade |
| `TAKE_PROFIT_RR` | `2.0` | Risk-to-reward ratio |
| `MAX_DAILY_DRAWDOWN_PERCENT` | `5.0` | Bot pauses for the day if this % loss is hit |
| `NEWS_FILTER_ENABLED` | `True` | Block trades around high-impact USD events |
| `NEWS_FILTER_WINDOW_MINUTES` | `30` | Minutes before/after news to block trading |
| `CHECK_INTERVAL_SECONDS` | `300` | How often the bot polls for signals (5 min for H1) |

---

## 4. Running the Live Bot

> **Always test on a demo account first before using real money.**

```
python main_bot.py
```

To stop the bot, press `Ctrl+C` in the terminal.

What the bot does each cycle:
1. Checks the news blackout window — skips if a high-impact USD event is within 30 minutes
2. Fetches H1 bars for signal generation and H4 bars for trend confirmation
3. Evaluates EMA crossover, RSI, and pullback conditions
4. Skips if H4 trend opposes the signal (e.g. H4 bearish blocks BUY)
5. Calculates lot size, SL, and TP — then places the trade via MT5

> The bot can also be run headlessly through the dashboard API (see Section 5).
> When running via the API, the bot runner starts automatically on server startup.

---

## 5. Running the Dashboard API

The dashboard API is a FastAPI server that runs the bot in the background and
exposes real-time data over HTTP + WebSocket to the frontend.

### Start the server

```
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
- Initialise the SQLite database (`sentinel.db`)
- Start the bot runner (connects to MT5, begins price polling + strategy cycles)
- Serve the REST API at `http://localhost:8000`
- Expose interactive API docs at `http://localhost:8000/docs`

### Authentication

All API endpoints (except `/health`) require a JWT. Obtain one via:

```
POST /api/auth/login
{"username": "admin", "password": "changeme"}
```

Returns `{"access_token": "...", "token_type": "bearer"}`.

### WebSocket Live Stream

Connect to receive all real-time events:

```
ws://localhost:8000/ws?token=<your-jwt>
```

Events emitted:

| Event | Trigger |
|---|---|
| `price_update` | Every 5 seconds (bid/ask/spread) |
| `signal_update` | After each strategy cycle |
| `position_update` | When floating P&L changes by more than $1 |
| `trade_opened` | Immediately when a trade is placed |
| `trade_closed` | When a position hits TP, SL, or is closed manually |
| `bot_status` | On any bot status change |

### Health Check

```
GET /health
```

Returns `{"status": "ok", "ws_connections": <n>}`.

---

## 6. Running the Frontend

```
cd dashboard
npm run dev
```

Open `http://localhost:3000` in your browser. Log in with the credentials from your `.env` file.

### Frontend structure

```
dashboard/
├── src/app/
│   ├── page.tsx                Main dashboard (monitoring)
│   ├── login/page.tsx          Login page
│   ├── account/page.tsx        User profile & settings
│   ├── admin/page.tsx          Subscriber management
│   ├── trades/page.tsx         Trade history with filters & stats
│   ├── analytics/page.tsx      Performance analytics & session heatmap
│   └── settings/page.tsx       Bot configuration (remote control)
├── src/components/widgets/
│   ├── SignalFeed.tsx          Live signal + indicator values
│   ├── HTFBiasPanel.tsx        H4 trend direction + EMA values
│   ├── NewsCountdown.tsx       Next news event + countdown
│   ├── PositionCards.tsx       Open trades with TP progress + R-multiple
│   ├── DrawdownGauge.tsx       Daily drawdown gauge + account summary
│   ├── KillSwitch.tsx          Emergency halt/resume + bot status
│   ├── EquityChart.tsx         Equity curve time-series (Lightweight Charts)
│   └── LotCalculator.tsx       Live lot size + what-if calculator
├── src/lib/
│   ├── api.ts                  REST API client (all 18+ endpoints)
│   └── types.ts                TypeScript types mirroring Python schemas
├── src/hooks/
│   └── useWebSocket.ts         Auto-reconnecting WebSocket hook
└── src/components/ui/
    ├── button.tsx, card.tsx, badge.tsx, etc.
    └── skeleton.tsx            Loading state component
```

---

---

## 7. Admin Dashboard Features

### Main Dashboard (`/`)
The real-time monitoring dashboard with 8 widgets:
1. **Signal Feed** — Current signal (BUY/SELL/HOLD) with EMA, RSI, ATR values
2. **H4 Bias Panel** — Higher timeframe trend direction + EMA values
3. **News Countdown** — Next economic event + live blackout timer
4. **Position Cards** — All open trades with TP progress, P&L, R-multiple
5. **Drawdown Gauge** — Daily risk used vs 5% limit
6. **Bot Control** — Emergency halt/resume + bot status
7. **Equity Chart** — Balance vs equity time-series with period selector
8. **Lot Calculator** — Live lot size + what-if risk simulator

**Navigation:** 
- "Tools" dropdown → Trade History, Analytics, Bot Settings
- "Account" → Profile, password change, Telegram setup
- "Subscribers" → Manage customers (Plan 1 & Plan 2)

### Trade History (`/trades`)
Browse all executed trades with advanced filtering:
- **Filters:** Last 7/30/90 days or all-time; wins only / losses only / all results
- **Columns:** Ticket ID, entry/exit prices, P&L, R-multiple, duration, close reason
- **Stats:** Total trades, win count, loss count, total P&L
- **Export:** CSV button (ready for implementation)

### Performance Analytics (`/analytics`)
Comprehensive trading statistics:
- **KPI Cards:** Total trades, win rate %, total P&L, profit factor
- **Monthly Chart:** P&L by month with trade counts
- **Session Heatmap:** Win rate breakdown by trading hour (London, New York, etc.)
- **Trade Averages:** Avg win, avg loss, profit factor interpretation
- **Time Period Selector:** 7/30/90 days or all-time

### Bot Settings (`/settings`)
Remote bot configuration — all changes apply immediately:
- **Risk:** Risk per trade (0.1–5%), max daily drawdown (1–20%)
- **Session Hours:** London & New York UTC times
- **News Filter:** Blackout window in minutes
- **Indicators:** EMA fast/slow periods, RSI period, ATR period, min ATR filter
- **Feedback:** Success/error messages, warning about real-time application

### Subscriber Management (`/admin`)
Manage paying customers for Plans 1 & 2:
- **Create:** Add subscriber with name, email, plan choice
- **For Telegram Plan:** Enter subscriber's Telegram chat ID
- **For EA Plan:** Auto-generate API key, copy and send to client
- **Actions:** Activate/deactivate, rotate API key, delete
- **Stats:** Total subscribers, active count, inactive count
- **View:** All subscriber details in one place

### Account Settings (`/account`)
User profile and preferences:
- **Profile:** View username and join date
- **Security:** Change password (old password must match)
- **Notifications:** Set personal Telegram chat ID for alert messages

---

## 8. Exporting Data from MT5

The backtester and optimizer both require a CSV file of historical OHLCV bars.

### Option A — MQL5 Export Script (recommended)

1. In MT5, open MetaEditor (`F4`) and create a new Script
2. Paste the code below, compile it, then run it on a chart

```mql5
#property script_show_inputs
input int    BarsToExport = 5000;
input string Filename     = "xauusd_h1.csv";

void OnStart() {
    MqlRates rates[];
    int copied = CopyRates("XAUUSDm", PERIOD_H1, 0, BarsToExport, rates);
    int fh = FileOpen(Filename, FILE_WRITE | FILE_CSV | FILE_ANSI, ",");
    FileWrite(fh, "time,open,high,low,close,tick_volume");
    for (int i = copied - 1; i >= 0; i--)
        FileWrite(fh, TimeToString(rates[i].time), rates[i].open,
                  rates[i].high, rates[i].low, rates[i].close, rates[i].tick_volume);
    FileClose(fh);
    Print("Exported ", copied, " bars to ", Filename);
}
```

The CSV is saved to: `<MT5 Data Folder>\MQL5\Files\xauusd_h1.csv`

Find the data folder via: MT5 menu → File → Open Data Folder

### Option B — MT5 History Center

1. In MT5: Tools → History Center
2. Select `XAUUSDm` → `H1`
3. Click Export and save as CSV

---

## 9. Backtesting

The backtester simulates the strategy over historical data and prints a performance report.

### Run

```
python backtest.py xauusd_h1.csv
```

### What It Does

- Loads your CSV and computes all indicators
- Simulates entry at the open of the bar after the signal (no look-ahead bias)
- Tracks SL/TP hits bar by bar; worst-case (SL) assumed when both are touched in one bar
- Applies the same spread adjustment and pullback-gating logic as the live bot

### Example Output

```
====================================================
  BACKTEST RESULTS
====================================================
  Total Trades      : 148
  Winners           : 68  (45.9%)
  Losers            : 80  (54.1%)
  BUY  win/total    : 38/82 (46%)
  SELL win/total    : 30/66 (45%)
  Profit Factor     : 1.47  (>1.3 = viable)
  Net Return        : +38.2%
  Max Drawdown      : 12.4%
  Avg Bars Held     : 6.1
  Final Equity      : $13,820.00  (started $10,000)
====================================================
```

A **Profit Factor above 1.3** indicates a positive expectancy. Below 1.0 means the strategy loses money on that dataset.

---

## 10. EMA Optimization

The optimizer grid-searches all meaningful EMA fast/slow combinations and automatically validates the winner on a held-out 20% test set to check for overfitting.

### Run

```
python optimize.py xauusd_h1.csv
```

### What It Does

1. Splits your data 80% train / 20% test
2. Tests all EMA combinations: fast ∈ {5, 7, 9…19}, slow ∈ {15, 20, 25…60}
3. Ranks results by Profit Factor
4. Re-runs the top combination on the held-out test set
5. Tells you whether the result holds up out-of-sample

### Example Output

```
==========================================================================
  TOP 10 EMA COMBINATIONS  (ranked by Profit Factor)
==========================================================================
  Fast  Slow   Trades   Win%      PF   Return%   MaxDD%
--------------------------------------------------------------------------
     7    25      162  47.5%    1.63    +52.1%    10.2%
     9    21      148  45.9%    1.47    +38.2%    12.4%
    ...
==========================================================================

  Best combination : EMA(7/25)
  To apply: set in config.py →  FAST_EMA_PERIOD = 7  |  SLOW_EMA_PERIOD = 25

  Validating best combo on held-out test set...
  Out-of-sample  →  Trades: 34  PF: 1.41  WR: 47.1%  Return: +11.2%  MaxDD: 8.6%
  ✓  Holds up out-of-sample — safe to update config.py.
```

Once you have the optimal values, update `config.py`:

```python
FAST_EMA_PERIOD = 7   # example — use whatever optimize.py recommends
SLOW_EMA_PERIOD = 25
```

> Recommended workflow: export 2–3 years of H1 data, run the optimizer, validate, then go live.

---

## 11. Strategy Overview

| Component | Detail |
|---|---|
| Entry timeframe | H1 |
| Trend filter timeframe | H4 |
| EMA Crossover | Fast EMA(9) crossing Slow EMA(21) for trend direction |
| RSI Filter | Confirms momentum; blocks overbought/oversold entries |
| Pullback Entries | Additional entries when RSI dips during a trend (single-fire only) |
| ATR Stop Loss | Dynamic SL = 1.5 × ATR(14) + spread |
| Take Profit | RR × SL distance (default 2.0) |
| H4 Trend Filter | Suppresses counter-trend signals (no BUY when H4 is bearish) |
| News Filter | Blocks all trades ±30 min around high-impact USD events |
| Session Filter | Only trades between 07:00–22:00 UTC (London + New York) |
| Risk Per Trade | 1% of account balance |
| Daily Drawdown Limit | Pauses trading for the day if equity drops 5% from open |
| Max Open Trades | 5 simultaneous positions |

---

## 12. File Reference

### Bot Engine

| File | Purpose |
|---|---|
| `main_bot.py` | Standalone bot loop — connects to MT5, coordinates all components |
| `strategy.py` | All signal logic: EMA, RSI, ATR, H4 filter, session filter |
| `mt5_connector.py` | MT5 connection, trade execution, data fetching |
| `news_filter.py` | Fetches ForexFactory calendar and blocks trades near events |
| `backtest.py` | Offline backtesting against a CSV of historical bars |
| `optimize.py` | Grid-search EMA optimizer with train/test split validation |
| `config.py` | All settings — account credentials, strategy params, risk rules |
| `logger.py` | File and console logging, trade log writer |

### Dashboard API (`api/`)

| File | Purpose |
|---|---|
| `api/main.py` | FastAPI app entry point — lifespan, CORS, `/ws` WebSocket endpoint |
| `api/bot_runner.py` | Async bot runner — price poller + strategy cycle, runs on startup |
| `api/state.py` | Thread-safe in-memory state shared between bot runner and API endpoints |
| `api/ws_manager.py` | WebSocket connection manager — broadcasts 6 live event types |
| `api/auth.py` | JWT creation/validation + bcrypt password hashing |
| `api/database.py` | Async SQLAlchemy engine, session factory, `init_db()` |
| `api/models.py` | ORM models: `User`, `Trade`, `BotStateDB` |
| `api/schemas.py` | Pydantic schemas for all API request/response contracts |
| `api/routers/auth_router.py` | `POST /api/auth/login` — returns JWT on valid credentials |
| `api/routers/user_router.py` | `GET /api/user/me` — current user profile; `POST /api/user/change-password` — password change; `PATCH /api/user/telegram` — update telegram ID |
| `api/routers/signal_router.py` | `GET /api/signal` — current signal + indicators; `GET /api/signal/history` — last N signals |
| `api/routers/htf_router.py` | `GET /api/htf` — H4 trend bias (BULLISH/BEARISH/NEUTRAL) + underlying H4 EMA values |
| `api/routers/news_router.py` | `GET /api/news` — next high-impact USD event, countdown seconds, blackout status |
| `api/routers/positions_router.py` | `GET /api/positions` — all open positions; `GET /api/positions/{ticket}` — single position |
| `api/routers/account_router.py` | `GET /api/account` — balance, equity, margin, daily drawdown %, max daily risk USD |
| `api/routers/bot_router.py` | `GET /api/bot/status`; `POST /api/bot/halt` — kill switch; `POST /api/bot/resume` — clear halt |
| `api/routers/equity_router.py` | `GET /api/equity?period=1d\|7d\|30d\|all` — time-series equity snapshots for the chart |
| `api/routers/lotsize_router.py` | `GET /api/lotsize` — live lot size; `POST /api/lotsize/calculate` — interactive what-if calculator |
| `api/routers/trades_router.py` | `GET /api/trades?days=30&outcome=WIN` — trade history with filters; `GET /api/trades/analytics?days=30` — performance stats |
| `api/routers/settings_router.py` | `GET /api/settings` — current bot configuration; `PATCH /api/settings` — update risk, hours, indicators in real-time |
| `api/routers/admin_router.py` | `POST /api/admin/subscribers` — create; `GET /api/admin/subscribers` — list; `PATCH /api/admin/subscribers/{id}` — update; `DELETE /api/admin/subscribers/{id}` — delete; `POST /api/admin/subscribers/{id}/rotate-key` — new API key |
| `api/routers/ea_router.py` | `GET /api/ea/ping?api_key=xxx` — heartbeat; `GET /api/ea/signal?api_key=xxx` — pending signal; `POST /api/ea/signal/{id}/ack?api_key=xxx` — acknowledge |

### Config & Environment

| File | Purpose |
|---|---|
| `.env` | Runtime secrets (not committed) |
| `.env.example` | Template — copy to `.env` and fill in values |
| `requirements.txt` | All Python dependencies (bot + API) |

---

## 13. Dashboard Feature Roadmap

### Phase 1 — Real-Time Monitoring ✅ COMPLETE

| # | Feature | Status |
|---|---|---|
| 0 | FastAPI backend foundation (auth, WebSocket, DB, bot runner) | ✅ Complete |
| 1 | Live Signal Feed widget | ✅ Complete |
| 2 | H4 Trend Bias Panel widget | ✅ Complete |
| 3 | News Countdown Clock widget | ✅ Complete |
| 4 | Open Position Cards widget | ✅ Complete |
| 5 | Daily Drawdown Gauge widget | ✅ Complete |
| 6 | Emergency Kill Switch widget | ✅ Complete |
| 7 | Equity Curve Chart widget | ✅ Complete |
| 8 | Live Lot Size Calculator widget | ✅ Complete |

**Admin Dashboard Features:**
- 8 real-time monitoring widgets
- Live WebSocket updates (6 event types)
- Professional, responsive UI with Tailwind CSS
- Loading states, animations, error handling

### Signal Distribution System ✅ COMPLETE

| Step | Feature | Status |
|---|---|---|
| 1 | Subscriber model + admin CRUD endpoints | ✅ Complete |
| 2 | Telegram broadcaster (Plan 1 — $40–50/mo) | ✅ Complete |
| 3 | EA signal queue + ack endpoints (Plan 2 — $90–120/mo) | ✅ Complete |
| 4 | MQL5 Expert Advisor (`SentinelCopier.mq5`) | ✅ Complete |
| 5 | Admin dashboard page (`/admin`) | ✅ Complete |

**How It Works:**
- **Plan 1 — Telegram Signals**: Subscribers receive formatted messages on every BUY/SELL signal (requires `TELEGRAM_BOT_TOKEN` in `.env`)
- **Plan 2 — EA Copy Trading**: Subscribers run `SentinelCopier.mq5` on their MT5, EA polls signals every 30s, auto-places trades with their own risk
- **Admin Workflow**: Create subscriber → choose plan → auto-generate API key → share with client

### Phase 2 — Analytics & Journal ✅ COMPLETE

| Feature | Page | Status |
|---|---|---|
| Trade History with filters | `/trades` | ✅ Complete |
| Performance Analytics (win rate, profit factor, monthly breakdown) | `/analytics` | ✅ Complete |
| Session Heatmap (London, New York performance) | `/analytics` | ✅ Complete |
| Trade statistics & summary | `/trades` | ✅ Complete |
| Account settings & password change | `/account` | ✅ Complete |
| Telegram notifications setup | `/account` | ✅ Complete |

**New Pages:**
- **`/trades`** — Full trade history table with period/result filters, stats cards (total trades, wins, losses, total P&L)
- **`/analytics`** — Performance dashboard with KPI cards, monthly breakdown, session win rates, trade averages, profit factor
- **`/account`** — User profile, change password, update Telegram chat ID for notifications
- **`/settings`** — Remote bot configuration (risk %, daily drawdown, trading hours, news blackout, technical indicators)

### Phase 3 — Configuration & Control ✅ COMPLETE

| Feature | Page | Status |
|---|---|---|
| Remote bot configuration (live parameter updates) | `/settings` | ✅ Complete |
| Risk management settings | `/settings` | ✅ Complete |
| Trading session hours (UTC) | `/settings` | ✅ Complete |
| News filter & blackout window | `/settings` | ✅ Complete |
| Technical indicator tuning | `/settings` | ✅ Complete |
| Bot emergency control (halt/resume) | `/` (KillSwitch widget) | ✅ Complete |

**Remote Control Features:**
- Change risk % per trade (0.1–5%)
- Adjust daily drawdown limit (1–20%)
- Configure trading hours (London & New York sessions)
- Tune EMA periods, RSI, ATR parameters
- All changes apply in real-time within 5 seconds
- No server restart required
- Active positions unaffected by parameter changes

### Future Enhancements (Phase 4+)
- CSV export from trade history
- Trade notes & manual journaling
- Multi-user support (invite links)
- Dashboard customization (widget layout)
- Mobile app (React Native)
- Advanced backtesting UI
- API webhooks for external integrations

### Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + uvicorn |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy async |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Real-time | WebSocket (FastAPI native) |
| Frontend | Next.js + Tailwind CSS + shadcn/ui |
| Charts | Lightweight Charts (TradingView library) |
