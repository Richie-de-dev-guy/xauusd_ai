"""
EA router — Plan 2 signal polling for the MT5 Expert Advisor.

Authentication is via API key (query param), not JWT.
Each subscriber's EA gets a unique key from the admin panel.

GET  /api/ea/signal?api_key=xxx        Oldest unacknowledged signal for this key
POST /api/ea/signal/{id}/ack?api_key=xxx  Mark signal as executed
GET  /api/ea/ping?api_key=xxx          Heartbeat / connection test
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import Subscriber, SignalQueueItem
from api.schemas import SignalQueueItemRead

router = APIRouter(prefix="/api/ea", tags=["ea"])


async def _get_subscriber_by_key(api_key: str) -> Subscriber:
    """Dependency — resolve API key to an active subscriber or raise 401."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscriber).where(
                Subscriber.api_key == api_key,
                Subscriber.is_active == True,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key",
            )
        return sub


@router.get("/ping")
async def ea_ping(api_key: str = Query(...)):
    """Heartbeat endpoint — EA can call this on startup to verify the key works."""
    sub = await _get_subscriber_by_key(api_key)
    return {
        "status": "ok",
        "subscriber": sub.name,
        "plan": sub.plan,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/signal", response_model=SignalQueueItemRead | None)
async def get_pending_signal(api_key: str = Query(...)):
    """
    Return the oldest unacknowledged signal for this subscriber.
    Returns null (HTTP 200) when no pending signal exists — the EA
    should sleep and poll again on the next interval.
    """
    sub = await _get_subscriber_by_key(api_key)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SignalQueueItem)
            .where(
                SignalQueueItem.subscriber_id == sub.id,
                SignalQueueItem.acknowledged_at == None,  # noqa: E711
            )
            .order_by(SignalQueueItem.created_at.asc())
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if not item:
            return None
        return SignalQueueItemRead.model_validate(item)


@router.post("/signal/{item_id}/ack", response_model=SignalQueueItemRead)
async def acknowledge_signal(
    item_id: int,
    api_key: str = Query(...),
):
    """
    Mark a signal as executed so it won't be returned again.
    The EA calls this immediately after placing the trade.
    """
    sub = await _get_subscriber_by_key(api_key)

    async with AsyncSessionLocal() as session:
        item = await session.get(SignalQueueItem, item_id)
        if not item or item.subscriber_id != sub.id:
            raise HTTPException(status_code=404, detail="Signal not found")
        if item.acknowledged_at:
            raise HTTPException(status_code=409, detail="Signal already acknowledged")

        item.acknowledged_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(item)
        return SignalQueueItemRead.model_validate(item)
