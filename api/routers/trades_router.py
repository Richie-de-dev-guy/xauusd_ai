"""
Trades router — trade history, analytics, and exports.

GET /api/trades          — list trades with filters
GET /api/trades/analytics — performance stats
GET /api/trades/export   — CSV export
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
from io import StringIO

from api.database import get_async_session
from api.auth import get_current_user
from api.models import Trade
from api.schemas import TradeRead, AnalyticsResponse

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=List[TradeRead])
async def list_trades(
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),  # BUY or SELL
    outcome: Optional[str] = Query(None),    # WIN or LOSS
    days: int = Query(30, ge=1, le=365),
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[TradeRead]:
    """List trades with optional filters."""
    query = select(Trade).where(Trade.user_id == current_user)

    # Filter by date
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = query.where(Trade.open_time >= cutoff)

    if symbol:
        query = query.where(Trade.symbol == symbol)
    if direction:
        query = query.where(Trade.direction == direction)
    if outcome:
        query = query.where(Trade.outcome == outcome)

    # Order by recent first
    query = query.order_by(Trade.open_time.desc())

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AnalyticsResponse:
    """Get performance analytics."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all closed trades
    query = select(Trade).where(
        Trade.user_id == current_user,
        Trade.open_time >= cutoff,
        Trade.outcome.isnot(None),  # Only closed trades
    )
    result = await session.execute(query)
    trades = result.scalars().all()

    if not trades:
        return AnalyticsResponse(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            monthly_data=[],
            session_stats={},
        )

    # Calculate stats
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.outcome == "WIN")
    losing_trades = total_trades - winning_trades
    total_pnl = sum(t.pnl_usd or 0 for t in trades)

    winning_pnls = [t.pnl_usd for t in trades if t.outcome == "WIN" and t.pnl_usd]
    losing_pnls = [t.pnl_usd for t in trades if t.outcome == "LOSS" and t.pnl_usd]

    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
    avg_loss = abs(sum(losing_pnls) / len(losing_pnls)) if losing_pnls else 0.0

    profit_factor = avg_win / avg_loss if avg_loss > 0 else (avg_win if avg_win > 0 else 0)

    # Monthly breakdown
    monthly_data = []
    for i in range(days // 30 + 1):
        month_start = datetime.utcnow() - timedelta(days=days - (i * 30))
        month_end = month_start + timedelta(days=30)
        month_trades = [t for t in trades if month_start <= t.open_time <= month_end]
        if month_trades:
            month_pnl = sum(t.pnl_usd or 0 for t in month_trades)
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "trades": len(month_trades),
                "pnl": round(month_pnl, 2),
            })

    # Session stats (by trading hour)
    session_stats = {}
    for trade in trades:
        if trade.session:
            if trade.session not in session_stats:
                session_stats[trade.session] = {"wins": 0, "losses": 0, "pnl": 0.0}
            if trade.outcome == "WIN":
                session_stats[trade.session]["wins"] += 1
            else:
                session_stats[trade.session]["losses"] += 1
            session_stats[trade.session]["pnl"] += trade.pnl_usd or 0

    return AnalyticsResponse(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=(winning_trades / total_trades * 100) if total_trades > 0 else 0.0,
        total_pnl=round(total_pnl, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2),
        monthly_data=monthly_data,
        session_stats=session_stats,
    )
