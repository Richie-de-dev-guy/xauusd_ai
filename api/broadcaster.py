"""
Signal broadcaster — distributes signals to all active subscribers.

Called by bot_runner after every actionable BUY/SELL signal.

Plan 1 (TELEGRAM):  sends a formatted Telegram message to each subscriber's chat_id.
Plan 2 (EA):        inserts a SignalQueueItem row that the subscriber's MT5 EA polls.
Plan BOTH:          does both.

Telegram bot token is read from TELEGRAM_BOT_TOKEN env var.
If the token is missing, Telegram delivery is skipped silently.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import Subscriber, SignalQueueItem

TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _signal_emoji(signal: str) -> str:
    return "🟢" if signal == "BUY" else "🔴"


def _format_signal_message(
    signal: str,
    signal_type: Optional[str],
    symbol: str,
    entry: float,
    sl: float,
    tp: float,
    atr: float,
    htf_bias: str,
    rr: float,
) -> str:
    emoji = _signal_emoji(signal)
    sl_dist = abs(entry - sl)
    return (
        f"{emoji} <b>XAUUSD Sentinel Signal — {signal}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Symbol:      <code>{symbol}</code>\n"
        f"🎯 Direction:   <b>{signal}</b>\n"
        f"💡 Type:        {signal_type or 'EMA Crossover'}\n"
        f"📈 H4 Bias:     {htf_bias}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Entry:       <code>{entry:.2f}</code>\n"
        f"🛑 Stop Loss:   <code>{sl:.2f}</code>  ({sl_dist:.2f} pts)\n"
        f"✅ Take Profit: <code>{tp:.2f}</code>\n"
        f"📊 R:R Ratio:   1 : {rr:.1f}\n"
        f"📉 ATR:         {atr:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"<i>Not financial advice. Trade at your own risk.</i>"
    )


async def _send_telegram(chat_id: str, text: str) -> bool:
    """Send one Telegram message. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            })
            return resp.status_code == 200
    except Exception:
        return False


async def broadcast_signal(
    signal: str,
    signal_type: Optional[str],
    symbol: str,
    entry_price: float,
    sl: float,
    tp: float,
    atr: float,
    lot_size: float,
    htf_bias: str,
) -> dict:
    """
    Distribute a BUY or SELL signal to all active subscribers.

    Returns a summary dict:
        {"telegram_sent": N, "telegram_failed": N, "queue_inserted": N}
    """
    if signal not in ("BUY", "SELL"):
        return {"telegram_sent": 0, "telegram_failed": 0, "queue_inserted": 0}

    sl_dist = abs(entry_price - sl)
    tp_dist = abs(tp - entry_price)
    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 2.0

    message = _format_signal_message(
        signal, signal_type, symbol,
        entry_price, sl, tp, atr, htf_bias, rr,
    )

    telegram_sent = 0
    telegram_failed = 0
    queue_inserted = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.is_active == True)
        )
        subscribers = result.scalars().all()

        telegram_tasks = []
        for sub in subscribers:
            plan = sub.plan.upper()

            # Plan 1 — Telegram
            if plan in ("TELEGRAM", "BOTH") and sub.telegram_chat_id:
                telegram_tasks.append((sub.telegram_chat_id, message))

            # Plan 2 — EA signal queue
            if plan in ("EA", "BOTH"):
                item = SignalQueueItem(
                    subscriber_id=sub.id,
                    signal=signal,
                    signal_type=signal_type,
                    symbol=symbol,
                    entry_price=entry_price,
                    sl=sl,
                    tp=tp,
                    atr=atr,
                    lot_size=lot_size,
                    htf_bias=htf_bias,
                )
                session.add(item)
                queue_inserted += 1

        await session.commit()

    # Send Telegram messages concurrently (outside DB session)
    if telegram_tasks:
        results = await asyncio.gather(
            *[_send_telegram(chat_id, msg) for chat_id, msg in telegram_tasks],
            return_exceptions=True,
        )
        for r in results:
            if r is True:
                telegram_sent += 1
            else:
                telegram_failed += 1

    return {
        "telegram_sent": telegram_sent,
        "telegram_failed": telegram_failed,
        "queue_inserted": queue_inserted,
    }
