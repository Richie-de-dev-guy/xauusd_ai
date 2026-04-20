"""
H4 Trend Bias router — Step 2: H4 Trend Bias Panel.

GET /api/htf   Current H4 EMA values and derived trend direction.
"""

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import HTFBiasData
from api.state import bot_state

router = APIRouter(prefix="/api/htf", tags=["htf"])


@router.get("", response_model=HTFBiasData)
async def get_htf_bias(_: str = Depends(get_current_user)) -> HTFBiasData:
    """Return the current H4 trend direction and the underlying EMA values."""
    s = bot_state.snapshot()
    return HTFBiasData(
        bias=s.htf_bias,
        ema_fast=s.h4_ema_fast,
        ema_slow=s.h4_ema_slow,
        ema_gap=s.h4_ema_gap,
        last_updated=s.last_cycle_at,
    )
