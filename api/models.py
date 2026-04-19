"""
SQLAlchemy ORM models.

Designed multi-tenant from day one — every table carries a user_id.
Phase 1 only creates one user, but the schema never needs migration
when the platform adds more.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Float, Boolean, DateTime, Integer,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="user")
    bot_state: Mapped["BotStateDB"] = relationship(
        "BotStateDB", back_populates="user", uselist=False
    )


# ---------------------------------------------------------------------------
# Trade — full history for the Trade Journal + Session Heatmap
# ---------------------------------------------------------------------------

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    # MT5 identity
    ticket: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # Signal context
    direction: Mapped[str] = mapped_column(String(4), nullable=False)      # BUY / SELL
    signal_type: Mapped[str] = mapped_column(String(32), nullable=True)    # EMA Crossover / Pullback Entry
    h4_bias: Mapped[str] = mapped_column(String(8), nullable=True)         # BULLISH / BEARISH / NEUTRAL
    session: Mapped[str] = mapped_column(String(12), nullable=True)        # London / New York
    news_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Entry
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    sl: Mapped[float] = mapped_column(Float, nullable=False)
    tp: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    atr_at_entry: Mapped[float] = mapped_column(Float, nullable=True)
    open_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Exit (null while trade is open)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    close_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[str] = mapped_column(String(4), nullable=True)         # WIN / LOSS
    pnl_usd: Mapped[float] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=True)        # +2.0 / -1.0
    close_reason: Mapped[str] = mapped_column(String(20), nullable=True)   # Take Profit / Stop Loss / Manual

    user: Mapped["User"] = relationship("User", back_populates="trades")


# ---------------------------------------------------------------------------
# EquitySnapshot — time-series data for the Equity Curve chart
# ---------------------------------------------------------------------------

class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    daily_drawdown_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


# ---------------------------------------------------------------------------
# Subscriber — paying customer on Plan 1 (Telegram) or Plan 2 (EA)
# ---------------------------------------------------------------------------

class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=True)

    # Plan 1 — Telegram signals
    telegram_chat_id: Mapped[str] = mapped_column(String(32), nullable=True)

    # Plan 2 — MT5 EA copy trading (unique API key per subscriber)
    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )

    # Subscription tier: TELEGRAM | EA | BOTH
    plan: Mapped[str] = mapped_column(String(10), nullable=False, default="TELEGRAM")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    signal_queue: Mapped[list["SignalQueueItem"]] = relationship(
        "SignalQueueItem", back_populates="subscriber"
    )


# ---------------------------------------------------------------------------
# SignalQueueItem — one pending signal per Plan 2 subscriber
# Each EA subscriber polls and acknowledges their own row independently.
# ---------------------------------------------------------------------------

class SignalQueueItem(Base):
    __tablename__ = "signal_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscribers.id"), nullable=False, index=True
    )

    # Signal payload — everything the EA needs to place the trade
    signal: Mapped[str] = mapped_column(String(4), nullable=False)      # BUY / SELL
    signal_type: Mapped[str] = mapped_column(String(32), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, default="XAUUSDm")
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    sl: Mapped[float] = mapped_column(Float, nullable=False)
    tp: Mapped[float] = mapped_column(Float, nullable=False)
    atr: Mapped[float] = mapped_column(Float, nullable=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=True)       # advisory — EA recalculates
    htf_bias: Mapped[str] = mapped_column(String(8), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    subscriber: Mapped["Subscriber"] = relationship("Subscriber", back_populates="signal_queue")


# ---------------------------------------------------------------------------
# BotStateDB — persisted bot control flags (survives restarts)
# ---------------------------------------------------------------------------

class BotStateDB(Base):
    __tablename__ = "bot_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Emergency kill switch — persisted so restart doesn't auto-resume
    is_halted: Mapped[bool] = mapped_column(Boolean, default=False)
    halt_reason: Mapped[str] = mapped_column(String(64), nullable=True)
    halted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Daily drawdown baseline
    daily_start_balance: Mapped[float] = mapped_column(Float, nullable=True)
    daily_start_date: Mapped[str] = mapped_column(String(10), nullable=True)  # ISO date string

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="bot_state")
