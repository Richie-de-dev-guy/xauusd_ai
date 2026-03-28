# XAUUSD Trading Bot v2 — Setup Guide

## What You Need to Install

| App | Purpose | Download |
|---|---|---|
| MetaTrader 5 | Trading platform (Exness) | Via Exness Personal Area |
| Python 3.10+ | Runs the bot | python.org/downloads |
| 7-Zip | Extract the bot archive | 7-zip.org |
| VS Code (optional) | Edit config files | code.visualstudio.com |

**No MTsocketAPI or .ex5 files needed.** This version uses the official free MetaTrader5 Python library.

---

## Step-by-Step Setup

### 1. Install MetaTrader 5
- Go to exness.com, log in, and download MT5 from your Personal Area
- Install and log in with your Exness trading account credentials
- Make sure XAUUSD is visible in Market Watch

### 2. Install Python
- Download from python.org/downloads (get Python 3.10, 3.11, or 3.12)
- IMPORTANT: Check "Add Python to PATH" during installation
- Verify: open Command Prompt and type `python --version`

### 3. Install Dependencies
Open Command Prompt and run:
```
pip install MetaTrader5 pandas numpy
```

### 4. Configure the Bot
Open `config.py` and fill in your Exness MT5 credentials:
- `MT5_LOGIN` — Your MT5 account number
- `MT5_PASSWORD` — Your MT5 password
- `MT5_SERVER` — Your Exness server (e.g., "Exness-MT5Real")
- `MT5_PATH` — Path to your MT5 terminal (e.g., r"C:\Program Files\MetaTrader 5\terminal64.exe")

### 5. Run the Bot
```
cd C:\xauusd_bot_v2
python main_bot.py
```

### 6. Stop the Bot
Press Ctrl+C in the terminal.

---

## Files

| File | Purpose |
|---|---|
| main_bot.py | Main execution loop |
| strategy.py | EMA + RSI + ATR trading strategy |
| mt5_connector.py | MT5 connection and trade execution |
| config.py | All settings (account, risk, strategy) |
| logger.py | Trade logging |

---

## Strategy Overview

- **EMA Crossover**: Fast EMA (9) crossing Slow EMA (21) for trend direction
- **RSI Filter**: Confirms momentum, avoids overbought/oversold entries
- **ATR Stop Loss**: Dynamic SL based on market volatility (1.5x ATR)
- **Risk-to-Reward**: Default 1:2 (TP is 2x the SL distance)
- **Risk Per Trade**: 1% of account balance
- **Daily Drawdown Limit**: Stops trading if daily loss exceeds 5%

---

## Important Notes

- **Test on a demo account first** before going live
- Keep MT5 running while the bot is active
- For 24/7 operation, use a VPS (Exness offers free VPS for qualifying accounts)
