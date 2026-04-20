"""
Pydantic schemas — API request/response contracts.

All feature-specific schemas (signal, positions, account, etc.)
are defined here and imported by the routers added in Steps 1–8.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Price
# ---------------------------------------------------------------------------

class PriceData(BaseModel):
    bid: float
    ask: float
    spread: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Signal  (Step 1)
# ---------------------------------------------------------------------------

class SignalData(BaseModel):
    signal: str                         # BUY / SELL / HOLD
    signal_type: Optional[str]          # EMA Crossover / Pullback Entry / Filtered by H4 Bias / News Blackout / Outside Session
    ema_fast: float
    ema_slow: float
    ema_gap: float
    rsi: float
    atr: float
    htf_bias: str                       # BULLISH / BEARISH / NEUTRAL
    timestamp: Optional[datetime]
    history: List[SignalHistoryItem] = []


class SignalHistoryItem(BaseModel):
    signal: str
    signal_type: Optional[str]
    timestamp: datetime


# ---------------------------------------------------------------------------
# Positions  (Step 4)
# ---------------------------------------------------------------------------

class PositionData(BaseModel):
    ticket: int
    symbol: str
    direction: str                      # BUY / SELL
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    floating_pnl: float
    r_multiple: float
    sl_distance: float
    atr_at_entry: float
    tp_progress_pct: float              # 0–100 % of the way from entry to TP
    hold_duration_seconds: int
    signal_type: Optional[str]
    open_time: datetime


# ---------------------------------------------------------------------------
# Account  (Step 1, also used by Drawdown Gauge)
# ---------------------------------------------------------------------------

class AccountData(BaseModel):
    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: int
    daily_start_balance: float
    daily_drawdown_pct: float
    max_daily_risk_usd: float


# ---------------------------------------------------------------------------
# News  (Step 3)
# ---------------------------------------------------------------------------

class NewsEventData(BaseModel):
    title: Optional[str]
    scheduled_utc: Optional[datetime]
    countdown_seconds: Optional[int]
    impact: str = "High"
    currency: str = "USD"
    is_blackout_active: bool
    resumes_at: Optional[datetime]      # blackout end = event_time + window_minutes


# ---------------------------------------------------------------------------
# Lot Size Calculator  (Step 8)
# ---------------------------------------------------------------------------

class LotCalcData(BaseModel):
    balance: float
    risk_pct: float
    risk_amount: float
    atr: float
    spread: float
    sl_distance: float
    contract_size: float
    calculated_lot: float
    rounded_lot: float


class LotCalcRequest(BaseModel):
    balance: Optional[float] = None     # defaults to live account balance if omitted
    risk_pct: Optional[float] = None    # defaults to config value if omitted
    atr: Optional[float] = None         # defaults to latest ATR from state if omitted
    spread: Optional[float] = None      # defaults to live spread if omitted
    atr_multiplier: float = 1.5         # SL = atr_multiplier × ATR + spread


# ---------------------------------------------------------------------------
# Equity Curve  (Step 7)
# ---------------------------------------------------------------------------

class EquityPoint(BaseModel):
    timestamp: datetime
    balance: float
    equity: float
    daily_drawdown_pct: float

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# H4 Trend Bias  (Step 2)
# ---------------------------------------------------------------------------

class HTFBiasData(BaseModel):
    bias: str                            # BULLISH / BEARISH / NEUTRAL
    ema_fast: float                      # H4 fast EMA value at last cycle
    ema_slow: float                      # H4 slow EMA value at last cycle
    ema_gap: float                       # fast − slow (positive = bullish)
    last_updated: Optional[datetime]     # timestamp of the last completed cycle


# ---------------------------------------------------------------------------
# Bot Status
# ---------------------------------------------------------------------------

class BotStatusData(BaseModel):
    status: str                         # RUNNING / HALTED / PAUSED_DRAWDOWN / PAUSED_NEWS / PAUSED_SESSION / DISCONNECTED
    mt5_connected: bool
    is_halted: bool
    halt_reason: Optional[str]
    last_cycle_at: Optional[datetime]
    last_cycle_error: Optional[str]


# ---------------------------------------------------------------------------
# Subscribers + Signal Queue  (Step 1 of signal distribution build)
# ---------------------------------------------------------------------------

class SubscriberCreate(BaseModel):
    name: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    plan: str = "TELEGRAM"                  # TELEGRAM | EA | BOTH
    notes: Optional[str] = None


class SubscriberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SubscriberRead(BaseModel):
    id: int
    name: str
    email: Optional[str]
    telegram_chat_id: Optional[str]
    api_key: Optional[str]
    plan: str
    is_active: bool
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class SignalQueueItemRead(BaseModel):
    id: int
    subscriber_id: int
    signal: str
    signal_type: Optional[str]
    symbol: str
    entry_price: float
    sl: float
    tp: float
    atr: Optional[float]
    lot_size: Optional[float]
    htf_bias: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# WebSocket envelope  — all WS messages share this shape
# ---------------------------------------------------------------------------

class WSMessage(BaseModel):
    type: str                           # price_update / signal_update / position_update / trade_opened / trade_closed / bot_status
    data: Any
    timestamp: datetime


# ---------------------------------------------------------------------------
# Trade Journal  (Step 7 / Phase 2 — schema defined now so DB is correct)
# ---------------------------------------------------------------------------

class TradeRecord(BaseModel):
    id: int
    ticket: int
    direction: str
    signal_type: Optional[str]
    h4_bias: Optional[str]
    session: Optional[str]
    news_active: bool
    entry_price: float
    sl: float
    tp: float
    exit_price: Optional[float]
    volume: float
    atr_at_entry: Optional[float]
    open_time: datetime
    close_time: Optional[datetime]
    outcome: Optional[str]
    pnl_usd: Optional[float]
    r_multiple: Optional[float]
    close_reason: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# User / Account
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    username: str
    telegram_chat_id: Optional[str] = None
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Trades & Analytics
# ---------------------------------------------------------------------------

class TradeRead(BaseModel):
    id: int
    ticket: int
    symbol: str
    direction: str
    signal_type: Optional[str]
    h4_bias: Optional[str]
    session: Optional[str]
    news_active: bool
    entry_price: float
    sl: float
    tp: float
    exit_price: Optional[float]
    volume: float
    atr_at_entry: Optional[float]
    open_time: datetime
    close_time: Optional[datetime]
    outcome: Optional[str]
    pnl_usd: Optional[float]
    r_multiple: Optional[float]
    close_reason: Optional[str]

    class Config:
        from_attributes = True


class MonthlyDataItem(BaseModel):
    month: str
    trades: int
    pnl: float


class AnalyticsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    monthly_data: List[MonthlyDataItem]
    session_stats: dict


# ---------------------------------------------------------------------------
# Bot Settings
# ---------------------------------------------------------------------------

class BotSettingsResponse(BaseModel):
    risk_percent: float
    london_session_start: int
    london_session_end: int
    newyork_session_start: int
    newyork_session_end: int
    max_daily_drawdown_percent: float
    news_blackout_minutes: int
    min_atr_filter: float
    ema_fast_period: int
    ema_slow_period: int
    rsi_period: int
    atr_period: int


class BotSettingsUpdate(BaseModel):
    risk_percent: Optional[float] = None
    london_session_start: Optional[int] = None
    london_session_end: Optional[int] = None
    newyork_session_start: Optional[int] = None
    newyork_session_end: Optional[int] = None
    max_daily_drawdown_percent: Optional[float] = None
    news_blackout_minutes: Optional[int] = None
    min_atr_filter: Optional[float] = None
    ema_fast_period: Optional[int] = None
    ema_slow_period: Optional[int] = None
    rsi_period: Optional[int] = None
    atr_period: Optional[int] = None


class UpdateTelegramRequest(BaseModel):
    telegram_chat_id: Optional[str] = None
