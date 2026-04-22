"""
Shared in-memory bot state.

This is the single source of truth that the bot runner writes to
and every API endpoint reads from. It is fast (pure memory reads)
so no MT5 call is needed on every HTTP request.

Thread-safety: the bot runner runs in asyncio tasks but calls MT5
via run_in_executor (threads). SharedBotState uses a threading.Lock
so both async and threaded writers are safe.
"""

from __future__ import annotations
import threading
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any


@dataclass
class _State:
    # ── Connection ────────────────────────────────────────────────────────────
    mt5_connected: bool = False

    # ── Bot status ────────────────────────────────────────────────────────────
    # INITIALIZING / RUNNING / HALTED / PAUSED_DRAWDOWN / PAUSED_NEWS / PAUSED_SESSION / DISCONNECTED
    status: str = "INITIALIZING"
    is_halted: bool = False
    halt_reason: Optional[str] = None
    halted_at: Optional[datetime] = None

    # ── Signal ────────────────────────────────────────────────────────────────
    signal: str = "HOLD"
    signal_type: Optional[str] = None  # EMA Crossover / Pullback Entry / Filtered by H4 Bias
    signal_time: Optional[datetime] = None
    signal_history: List[Dict] = field(default_factory=list)  # last 10, newest first

    # ── Indicators (H1 / entry timeframe) ────────────────────────────────────
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    ema_gap: float = 0.0
    rsi: float = 0.0
    atr: float = 0.0

    # ── H4 trend filter ───────────────────────────────────────────────────────
    htf_bias: str = "NEUTRAL"
    h4_ema_fast: float = 0.0
    h4_ema_slow: float = 0.0
    h4_ema_gap: float = 0.0

    # ── Live price ────────────────────────────────────────────────────────────
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    price_updated_at: Optional[datetime] = None

    # ── Account ───────────────────────────────────────────────────────────────
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    leverage: int = 0

    # ── Daily drawdown ────────────────────────────────────────────────────────
    daily_start_balance: float = 0.0
    daily_start_date: Optional[date] = None
    daily_drawdown_pct: float = 0.0

    # ── Open positions ────────────────────────────────────────────────────────
    # Each item is a dict matching PositionData schema
    positions: List[Dict] = field(default_factory=list)

    # ── Lot sizing ────────────────────────────────────────────────────────────
    current_lot_size: float = 0.0
    sl_distance: float = 0.0
    risk_amount: float = 0.0

    # ── News filter ───────────────────────────────────────────────────────────
    news_blocked: bool = False
    next_news_title: Optional[str] = None
    next_news_time: Optional[datetime] = None
    news_resumes_at: Optional[datetime] = None

    # ── Session ───────────────────────────────────────────────────────────────
    in_trading_session: bool = False

    # ── Cycle metadata ────────────────────────────────────────────────────────
    last_cycle_at: Optional[datetime] = None
    last_cycle_error: Optional[str] = None


class SharedBotState:
    """Thread-safe wrapper — single global instance shared by bot runner and API."""

    def __init__(self):
        self._data = _State()
        self._lock = threading.Lock()

    # ── Read ──────────────────────────────────────────────────────────────────

    def snapshot(self) -> _State:
        """Return a shallow copy of current state (safe to read without holding the lock)."""
        with self._lock:
            import copy
            return copy.copy(self._data)

    def get(self, key: str, default=None):
        with self._lock:
            return getattr(self._data, key, default)

    # ── Write ─────────────────────────────────────────────────────────────────

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._data, key):
                    setattr(self._data, key, value)

    def push_signal_history(self, signal: str, signal_type: Optional[str], ts: datetime):
        """Prepend a new signal to history; keep the last 10."""
        with self._lock:
            entry = {"signal": signal, "signal_type": signal_type, "timestamp": ts.isoformat()}
            self._data.signal_history = [entry] + self._data.signal_history[:9]

    # ── Serialise ─────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe dictionary for WebSocket broadcasting."""
        with self._lock:
            d: Dict[str, Any] = {}
            for key, value in self._data.__dict__.items():
                if isinstance(value, datetime):
                    d[key] = value.isoformat()
                elif isinstance(value, date):
                    d[key] = value.isoformat()
                else:
                    d[key] = value
            return d


# ── Global singleton ──────────────────────────────────────────────────────────
bot_state = SharedBotState()

# Alias to match the name expected by the API routers
shared_state = bot_state