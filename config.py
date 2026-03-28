# ============================================================
# XAUUSD Trading Bot - Configuration
# ============================================================

# --- MT5 Account Details (Exness) ---
# Replace these with your actual Exness MT5 credentials
MT5_LOGIN = 000000000            # Your MT5 account number
MT5_PASSWORD = "your_password"  # Your MT5 account password
MT5_SERVER = "Your Exness server name (check your Exness Personal Area)"   # Your Exness server name (check your Exness Personal Area)
MT5_PATH = r"Path to your MT5 terminal"  # Path to your MT5 terminal

# --- Telegram Configuration ---
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "your_token_here"
TELEGRAM_CHAT_ID = "your_id_here"

# --- Trading Parameters ---
SYMBOL = "XAUUSD"
TIMEFRAME = "M15"       # Options: M1, M5, M15, M30, H1, H4, D1
MAGIC_NUMBER = 234000   # Unique ID for this bot's trades

# --- Strategy Parameters ---
FAST_EMA_PERIOD = 9
SLOW_EMA_PERIOD = 21
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
ATR_PERIOD = 14

# --- Risk Management ---
RISK_PERCENT_PER_TRADE = 1.0    # % of account balance risked per trade
TAKE_PROFIT_RR = 2.0            # Risk-to-reward ratio (TP = RR x SL distance)
MAX_OPEN_TRADES = 5             # Max simultaneous trades
MAX_DAILY_DRAWDOWN_PERCENT = 5.0  # Stop trading if daily loss exceeds this %

# --- Logging ---
LOG_FILE = "trade_log.txt"

# --- Bot Loop ---
CHECK_INTERVAL_SECONDS = 60     # How often the bot checks for signals (in seconds)
