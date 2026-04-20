"""
Admin router — subscriber management.

All endpoints require a valid JWT (dashboard login).
In a future multi-admin setup, add an is_admin check on the token.

POST   /api/admin/subscribers           Create subscriber + generate API key
GET    /api/admin/subscribers           List all subscribers
GET    /api/admin/subscribers/{id}      Single subscriber detail
PATCH  /api/admin/subscribers/{id}      Update name / plan / active status / etc.
DELETE /api/admin/subscribers/{id}      Hard-delete subscriber and their queue
POST   /api/admin/subscribers/{id}/rotate-key   Regenerate API key (Plan 2)
GET    /api/admin/subscribers/{id}/queue        Pending signal queue for one subscriber
"""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete

from api.auth import get_current_user
from api.database import AsyncSessionLocal
from api.models import Subscriber, SignalQueueItem
from api.schemas import SubscriberCreate, SubscriberUpdate, SubscriberRead, SignalQueueItemRead

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _generate_api_key() -> str:
    return secrets.token_urlsafe(32)


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/subscribers", response_model=SubscriberRead, status_code=status.HTTP_201_CREATED)
async def create_subscriber(
    body: SubscriberCreate,
    _: str = Depends(get_current_user),
) -> SubscriberRead:
    """
    Register a new paying subscriber.
    An API key is generated automatically for Plan 2 (EA) subscribers.
    Plan 1 (Telegram) subscribers need their Telegram chat_id set here.
    """
    plan = body.plan.upper()
    if plan not in ("TELEGRAM", "EA", "BOTH"):
        raise HTTPException(status_code=400, detail="plan must be TELEGRAM, EA, or BOTH")

    api_key = _generate_api_key() if plan in ("EA", "BOTH") else None

    async with AsyncSessionLocal() as session:
        sub = Subscriber(
            name=body.name,
            email=body.email,
            telegram_chat_id=body.telegram_chat_id,
            api_key=api_key,
            plan=plan,
            notes=body.notes,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return SubscriberRead.model_validate(sub)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/subscribers", response_model=list[SubscriberRead])
async def list_subscribers(
    _: str = Depends(get_current_user),
) -> list[SubscriberRead]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscriber).order_by(Subscriber.created_at.desc())
        )
        rows = result.scalars().all()
        return [SubscriberRead.model_validate(r) for r in rows]


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/subscribers/{sub_id}", response_model=SubscriberRead)
async def get_subscriber(
    sub_id: int,
    _: str = Depends(get_current_user),
) -> SubscriberRead:
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscriber, sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        return SubscriberRead.model_validate(sub)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/subscribers/{sub_id}", response_model=SubscriberRead)
async def update_subscriber(
    sub_id: int,
    body: SubscriberUpdate,
    _: str = Depends(get_current_user),
) -> SubscriberRead:
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscriber, sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        for field, value in body.model_dump(exclude_none=True).items():
            setattr(sub, field, value)

        # Auto-generate API key if plan upgraded to EA/BOTH and key doesn't exist
        if body.plan and body.plan.upper() in ("EA", "BOTH") and not sub.api_key:
            sub.api_key = _generate_api_key()

        await session.commit()
        await session.refresh(sub)
        return SubscriberRead.model_validate(sub)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/subscribers/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscriber(
    sub_id: int,
    _: str = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscriber, sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        # Remove pending queue items first (FK constraint)
        await session.execute(
            delete(SignalQueueItem).where(SignalQueueItem.subscriber_id == sub_id)
        )
        await session.delete(sub)
        await session.commit()


# ── Rotate API key ────────────────────────────────────────────────────────────

@router.post("/subscribers/{sub_id}/rotate-key", response_model=SubscriberRead)
async def rotate_api_key(
    sub_id: int,
    _: str = Depends(get_current_user),
) -> SubscriberRead:
    """Generate a fresh API key — the old one stops working immediately."""
    async with AsyncSessionLocal() as session:
        sub = await session.get(Subscriber, sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        sub.api_key = _generate_api_key()
        await session.commit()
        await session.refresh(sub)
        return SubscriberRead.model_validate(sub)


# ── Signal queue for one subscriber ──────────────────────────────────────────

@router.get("/subscribers/{sub_id}/queue", response_model=list[SignalQueueItemRead])
async def get_subscriber_queue(
    sub_id: int,
    _: str = Depends(get_current_user),
) -> list[SignalQueueItemRead]:
    """View pending and acknowledged signals for a specific subscriber."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SignalQueueItem)
            .where(SignalQueueItem.subscriber_id == sub_id)
            .order_by(SignalQueueItem.created_at.desc())
            .limit(50)
        )
        rows = result.scalars().all()
        return [SignalQueueItemRead.model_validate(r) for r in rows]
