"""
Bot control router — Step 6: Emergency Kill Switch.

GET  /api/bot/status          Current bot status snapshot
POST /api/bot/halt            Emergency stop — halt bot + close all positions
POST /api/bot/halt?close=false  Halt without closing positions
POST /api/bot/resume          Clear halt and resume normal operation
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_user
from api.bot_runner import bot_runner
from api.schemas import BotStatusData
from api.state import bot_state

router = APIRouter(prefix="/api/bot", tags=["bot"])


class HaltResult(BaseModel):
    halted: bool
    closed: list[int]
    errors: list[str]


class ResumeResult(BaseModel):
    resumed: bool


@router.get("/status", response_model=BotStatusData)
async def get_bot_status(_: str = Depends(get_current_user)) -> BotStatusData:
    """Return current bot status, MT5 connection state, and last cycle metadata."""
    s = bot_state.snapshot()
    return BotStatusData(
        status=s.status,
        mt5_connected=s.mt5_connected,
        is_halted=s.is_halted,
        halt_reason=s.halt_reason,
        last_cycle_at=s.last_cycle_at,
        last_cycle_error=s.last_cycle_error,
    )


@router.post("/halt", response_model=HaltResult)
async def halt_bot(
    close: bool = Query(default=True, description="Close all open positions before halting"),
    _: str = Depends(get_current_user),
) -> HaltResult:
    """
    Emergency kill switch.

    Immediately halts the bot and, by default, closes every open position.
    Pass ?close=false to freeze the bot without touching open trades.
    """
    result = await bot_runner.halt(
        reason="Manual kill switch",
        close_positions=close,
    )
    return HaltResult(**result)


@router.post("/resume", response_model=ResumeResult)
async def resume_bot(_: str = Depends(get_current_user)) -> ResumeResult:
    """
    Resume normal operation after a manual halt.
    Has no effect if the bot is paused due to drawdown, news, or session filters —
    those resume automatically when the condition clears.
    """
    result = await bot_runner.resume()
    return ResumeResult(**result)
