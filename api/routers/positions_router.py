"""
Positions router — Step 4: Open Position Cards.

GET /api/positions          All open positions with enriched metrics
GET /api/positions/{ticket} Single position by MT5 ticket number
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import get_current_user
from api.schemas import PositionData
from api.state import bot_state

router = APIRouter(prefix="/api/positions", tags=["positions"])


def _parse_position(raw: dict) -> PositionData:
    """Convert a raw position dict from state into a validated PositionData."""
    from datetime import datetime
    open_time = raw.get("open_time")
    if isinstance(open_time, str):
        open_time = datetime.fromisoformat(open_time)
    return PositionData(
        ticket=raw["ticket"],
        symbol=raw["symbol"],
        direction=raw["direction"],
        volume=raw["volume"],
        open_price=raw["open_price"],
        current_price=raw["current_price"],
        sl=raw["sl"],
        tp=raw["tp"],
        floating_pnl=raw["floating_pnl"],
        r_multiple=raw["r_multiple"],
        sl_distance=raw["sl_distance"],
        atr_at_entry=raw["atr_at_entry"],
        tp_progress_pct=raw["tp_progress_pct"],
        hold_duration_seconds=raw["hold_duration_seconds"],
        signal_type=raw.get("signal_type"),
        open_time=open_time,
    )


@router.get("", response_model=list[PositionData])
async def get_positions(_: str = Depends(get_current_user)) -> list[PositionData]:
    """Return all currently open positions with live P&L and progress metrics."""
    s = bot_state.snapshot()
    return [_parse_position(p) for p in s.positions]


@router.get("/{ticket}", response_model=PositionData)
async def get_position(
    ticket: int,
    _: str = Depends(get_current_user),
) -> PositionData:
    """Return a single open position by its MT5 ticket number."""
    s = bot_state.snapshot()
    for p in s.positions:
        if p["ticket"] == ticket:
            return _parse_position(p)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No open position with ticket {ticket}",
    )
