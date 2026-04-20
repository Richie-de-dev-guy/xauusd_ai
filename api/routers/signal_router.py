"""
Signal router — Step 1: Live Signal Feed.

GET  /api/signal        Current signal + indicators + last-10 history
GET  /api/signal/history  Signal history only (last N, default 10, max 50)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import get_current_user
from api.schemas import SignalData, SignalHistoryItem
from api.state import bot_state

router = APIRouter(prefix="/api/signal", tags=["signal"])


@router.get("", response_model=SignalData)
async def get_signal(_: str = Depends(get_current_user)) -> SignalData:
    """Return the most recent signal and all indicator values."""
    s = bot_state.snapshot()

    history = [
        SignalHistoryItem(
            signal=item["signal"],
            signal_type=item.get("signal_type"),
            timestamp=datetime.fromisoformat(item["timestamp"]),
        )
        for item in s.signal_history
    ]

    return SignalData(
        signal=s.signal,
        signal_type=s.signal_type,
        ema_fast=s.ema_fast,
        ema_slow=s.ema_slow,
        ema_gap=s.ema_gap,
        rsi=s.rsi,
        atr=s.atr,
        htf_bias=s.htf_bias,
        timestamp=s.signal_time,
        history=history,
    )


@router.get("/history", response_model=list[SignalHistoryItem])
async def get_signal_history(
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(get_current_user),
) -> list[SignalHistoryItem]:
    """Return the last N signals (newest first)."""
    s = bot_state.snapshot()
    items = s.signal_history[:limit]
    return [
        SignalHistoryItem(
            signal=item["signal"],
            signal_type=item.get("signal_type"),
            timestamp=datetime.fromisoformat(item["timestamp"]),
        )
        for item in items
    ]
