# ============================================================
# XAUUSD Trading Bot - Configuration
# ============================================================

# --- MT5 Account Details (Exness) ---
MT5_LOGIN    = Your MT5 Login
MT5_PASSWORD = "MT5_PASSWORD"
MT5_SERVER   = "Exness-MT5Trial9"
MT5_PATH     = r"C:\Program Files\MetaTrader 5\terminal64.exe"

# # --- Telegram Configuration ---
# TELEGRAM_ENABLED   = True
# TELEGRAM_BOT_TOKEN = "your_token_here"
# TELEGRAM_CHAT_ID   = "your_id_here"

# --- Trading Parameters ---
SYMBOL       = "XAUUSDm"
TIMEFRAME    = "M5"          # Mean reversion scalper runs on M5
MAGIC_NUMBER = 234002        # Single strategy now — keep one magic

# --- Data ---
NUM_BARS = 300               # RSI(9) + lookback warmup needs ~50; extra headroom

# --- Mean Reversion Scalper Parameters ---
SCALPER_RSI_PERIOD          = 9
SCALPER_RSI_OB_EXTREME      = 80    # "RSI must have spiked above this..."
SCALPER_RSI_OS_EXTREME      = 20    # "...or dropped below this..."
SCALPER_RSI_NEUTRAL_UPPER   = 70    # "...then crossed back below this (for SELL)"
SCALPER_RSI_NEUTRAL_LOWER   = 30    # "...or crossed back above this (for BUY)"
SCALPER_EXTREME_LOOKBACK    = 5     # bars to scan for the extreme touch
SCALPER_SL_PIPS             = 15    # fixed-pip SL
SCALPER_TP_PIPS             = 25    # fixed-pip TP (RR ~1:1.67)
SCALPER_SESSION_START_UTC   = 12.5  # 12:30 UTC — NY-London overlap begins
SCALPER_SESSION_END_UTC     = 17.0  # 17:00 UTC — London close, liquidity drops
SCALPER_MAX_SPREAD_PIPS     = 6     # live guard: skip trade if spread wider than this

# --- News Filter ---
# Mean reversion targets the post-spike snap-back, so the news filter is
# intentionally DISABLED for this strategy. If you re-enable it, keep the
# window narrow (5–10 min, not 30).
NEWS_FILTER_ENABLED        = False
NEWS_FILTER_WINDOW_MINUTES = 10

# --- Risk Management ---
RISK_PERCENT_PER_TRADE     = 1.0
MAX_OPEN_TRADES            = 2     # Scalper trades resolve in minutes, cap kept low
MAX_DAILY_DRAWDOWN_PERCENT = 5.0

# --- Legacy values (still referenced by api/bot_runner.py and backtest.py) ---
# The main bot no longer uses these, but the API server reads them at import time.
# Safe to leave in place; only update if you reactivate the legacy strategy via the API.
FAST_EMA_PERIOD = 9
SLOW_EMA_PERIOD = 21
RSI_PERIOD      = 14
RSI_OVERBOUGHT  = 70
RSI_OVERSOLD    = 30
ATR_PERIOD      = 14
TAKE_PROFIT_RR  = 2.0
HTF_TIMEFRAME   = "H4"
H4_BARS         = 100

# --- Logging ---
LOG_FILE = "trade_log.txt"

# --- Bot Loop ---
CHECK_INTERVAL_SECONDS = 60   # M5 bars close every 5 min; 60s polling reacts within 1 min
