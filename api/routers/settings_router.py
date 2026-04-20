"""
Settings router — bot configuration and parameters.

GET /api/settings     — get current bot settings
PATCH /api/settings   — update bot settings
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_async_session
from api.auth import get_current_user
from api.state import shared_state
from api.schemas import BotSettingsResponse, BotSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=BotSettingsResponse)
async def get_settings(
    current_user: str = Depends(get_current_user),
) -> BotSettingsResponse:
    """Get current bot settings."""
    with shared_state.lock:
        return BotSettingsResponse(
            risk_percent=shared_state.state.risk_percent,
            london_session_start=shared_state.state.london_session_start,
            london_session_end=shared_state.state.london_session_end,
            newyork_session_start=shared_state.state.newyork_session_start,
            newyork_session_end=shared_state.state.newyork_session_end,
            max_daily_drawdown_percent=shared_state.state.max_daily_drawdown_percent,
            news_blackout_minutes=shared_state.state.news_blackout_minutes,
            min_atr_filter=shared_state.state.min_atr_filter,
            ema_fast_period=shared_state.state.ema_fast_period,
            ema_slow_period=shared_state.state.ema_slow_period,
            rsi_period=shared_state.state.rsi_period,
            atr_period=shared_state.state.atr_period,
        )


@router.patch("", response_model=BotSettingsResponse)
async def update_settings(
    body: BotSettingsUpdate,
    current_user: str = Depends(get_current_user),
) -> BotSettingsResponse:
    """Update bot settings."""
    with shared_state.lock:
        # Update only provided fields
        if body.risk_percent is not None:
            shared_state.state.risk_percent = body.risk_percent
        if body.london_session_start is not None:
            shared_state.state.london_session_start = body.london_session_start
        if body.london_session_end is not None:
            shared_state.state.london_session_end = body.london_session_end
        if body.newyork_session_start is not None:
            shared_state.state.newyork_session_start = body.newyork_session_start
        if body.newyork_session_end is not None:
            shared_state.state.newyork_session_end = body.newyork_session_end
        if body.max_daily_drawdown_percent is not None:
            shared_state.state.max_daily_drawdown_percent = body.max_daily_drawdown_percent
        if body.news_blackout_minutes is not None:
            shared_state.state.news_blackout_minutes = body.news_blackout_minutes
        if body.min_atr_filter is not None:
            shared_state.state.min_atr_filter = body.min_atr_filter
        if body.ema_fast_period is not None:
            shared_state.state.ema_fast_period = body.ema_fast_period
        if body.ema_slow_period is not None:
            shared_state.state.ema_slow_period = body.ema_slow_period
        if body.rsi_period is not None:
            shared_state.state.rsi_period = body.rsi_period
        if body.atr_period is not None:
            shared_state.state.atr_period = body.atr_period

        return BotSettingsResponse(
            risk_percent=shared_state.state.risk_percent,
            london_session_start=shared_state.state.london_session_start,
            london_session_end=shared_state.state.london_session_end,
            newyork_session_start=shared_state.state.newyork_session_start,
            newyork_session_end=shared_state.state.newyork_session_end,
            max_daily_drawdown_percent=shared_state.state.max_daily_drawdown_percent,
            news_blackout_minutes=shared_state.state.news_blackout_minutes,
            min_atr_filter=shared_state.state.min_atr_filter,
            ema_fast_period=shared_state.state.ema_fast_period,
            ema_slow_period=shared_state.state.ema_slow_period,
            rsi_period=shared_state.state.rsi_period,
            atr_period=shared_state.state.atr_period,
        )
