"""
Equity router — Step 7: Equity Curve Chart.

GET /api/equity?period=1d|7d|30d|all

Returns a list of equity snapshots (balance + equity + drawdown %)
ordered by time ascending. The frontend plots these as a time-series chart.

Snapshots are written to the DB once per strategy cycle (~5 min on H1).
Long periods are downsampled to ≤500 points to keep payloads small.
"""

from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func

from api.auth import get_current_user
from api.database import AsyncSessionLocal
from api.models import EquitySnapshot
from api.schemas import EquityPoint

router = APIRouter(prefix="/api/equity", tags=["equity"])

_PERIOD_MAP = {
    "1d":  timedelta(days=1),
    "7d":  timedelta(days=7),
    "30d": timedelta(days=30),
}
MAX_POINTS = 500   # downsample threshold


@router.get("", response_model=list[EquityPoint])
async def get_equity_curve(
    period: Literal["1d", "7d", "30d", "all"] = Query(
        default="1d",
        description="Time window: 1d (24 h), 7d, 30d, or all history",
    ),
    _: str = Depends(get_current_user),
) -> list[EquityPoint]:
    """
    Return equity snapshots for the requested period.
    Results are ordered oldest-first so the chart can be plotted directly.
    For periods with more than 500 raw points, every Nth row is returned
    to keep the payload under control.
    """
    async with AsyncSessionLocal() as session:
        # Build the base query with an optional time filter
        stmt = select(EquitySnapshot).order_by(EquitySnapshot.recorded_at.asc())
        if period != "all":
            cutoff = datetime.now(timezone.utc) - _PERIOD_MAP[period]
            stmt = stmt.where(EquitySnapshot.recorded_at >= cutoff)

        result = await session.execute(stmt)
        rows = result.scalars().all()

    if not rows:
        return []

    # Downsample if needed — pick every Nth row to stay under MAX_POINTS
    n = max(1, len(rows) // MAX_POINTS)
    sampled = rows[::n]

    return [
        EquityPoint(
            timestamp=row.recorded_at,
            balance=row.balance,
            equity=row.equity,
            daily_drawdown_pct=row.daily_drawdown_pct,
        )
        for row in sampled
    ]
