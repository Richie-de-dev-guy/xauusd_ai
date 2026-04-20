"""
Account router — Step 5: Daily Drawdown Gauge.

GET /api/account   Live account snapshot: balance, equity, margin,
                   daily drawdown %, and the max daily risk in USD.
"""

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import AccountData
from api.state import bot_state

router = APIRouter(prefix="/api/account", tags=["account"])

try:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import config as _config
    _MAX_DD_PCT = _config.MAX_DAILY_DRAWDOWN_PERCENT
    _RISK_PCT   = _config.RISK_PERCENT_PER_TRADE
except Exception:
    _MAX_DD_PCT = 5.0
    _RISK_PCT   = 1.0


@router.get("", response_model=AccountData)
async def get_account(_: str = Depends(get_current_user)) -> AccountData:
    """
    Return current account metrics and daily drawdown gauge data.

    max_daily_risk_usd = balance × MAX_DAILY_DRAWDOWN_PERCENT / 100
    daily_drawdown_pct is negative when in drawdown (equity < daily open balance).
    """
    s = bot_state.snapshot()
    max_daily_risk_usd = round(s.balance * _MAX_DD_PCT / 100, 2)

    return AccountData(
        balance=s.balance,
        equity=s.equity,
        margin=s.margin,
        free_margin=s.free_margin,
        leverage=s.leverage,
        daily_start_balance=s.daily_start_balance,
        daily_drawdown_pct=s.daily_drawdown_pct,
        max_daily_risk_usd=max_daily_risk_usd,
    )
