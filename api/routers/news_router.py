"""
News router — Step 3: News Countdown Clock.

GET /api/news   Next high-impact USD event + blackout status + countdown.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import NewsEventData
from api.state import bot_state

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=NewsEventData)
async def get_news(_: str = Depends(get_current_user)) -> NewsEventData:
    """
    Return the next upcoming high-impact USD news event and whether
    trading is currently in a blackout window around it.
    """
    s = bot_state.snapshot()

    countdown: int | None = None
    if s.next_news_time:
        secs = int((s.next_news_time - datetime.now(timezone.utc)).total_seconds())
        countdown = max(0, secs)

    return NewsEventData(
        title=s.next_news_title,
        scheduled_utc=s.next_news_time,
        countdown_seconds=countdown,
        is_blackout_active=s.news_blocked,
        resumes_at=s.news_resumes_at,
    )
