# ============================================================
# XAUUSD Trading Bot - Configuration
# ============================================================

# --- MT5 Account Details (Exness) ---
# Replace these with your actual Exness MT5 credentials
MT5_LOGIN =  435387461           # Your MT5 account number
MT5_PASSWORD = "Effiom3009$1"  # Your MT5 account password
MT5_SERVER = "Exness-MT5Trial9"   # Your Exness server name (check your Exness Personal Area)
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"  # Path to your MT5 terminal

# # --- Telegram Configuration ---
# TELEGRAM_ENABLED = True
# TELEGRAM_BOT_TOKEN = "your_token_here"
# TELEGRAM_CHAT_ID = "your_id_here"

# --- Trading Parameters ---
SYMBOL       = "XAUUSDm"
TIMEFRAME    = "H1"         # H1 produces fewer false signals than M15 on Gold
MAGIC_NUMBER = 234000       # Unique ID for this bot's trades

# --- Higher Timeframe (trend filter) ---
HTF_TIMEFRAME = "H4"        # Used by strategy.check_htf_trend() to confirm direction
H4_BARS       = 100         # Number of H4 bars to fetch

# --- Data ---
NUM_BARS = 200              # Historical bars fetched per cycle (H1 needs more for warmup)

# --- Strategy Parameters ---
FAST_EMA_PERIOD = 7
SLOW_EMA_PERIOD = 25
RSI_PERIOD      = 14
RSI_OVERBOUGHT  = 70
RSI_OVERSOLD    = 30
ATR_PERIOD      = 14

# --- News Filter ---
NEWS_FILTER_ENABLED        = True
NEWS_FILTER_WINDOW_MINUTES = 30   # Block trading ±30 min around high-impact USD events

# --- Risk Management ---
RISK_PERCENT_PER_TRADE    = 1.0    # % of account balance risked per trade
TAKE_PROFIT_RR            = 2.0    # Risk-to-reward ratio (TP = RR x SL distance)
MAX_OPEN_TRADES           = 5      # Max simultaneous trades
MAX_DAILY_DRAWDOWN_PERCENT = 5.0   # Stop trading if daily loss exceeds this %

# --- Logging ---
LOG_FILE = "trade_log.txt"

# --- Bot Loop ---
CHECK_INTERVAL_SECONDS = 300    # Check every 5 min — no need to poll every 60s on H1
