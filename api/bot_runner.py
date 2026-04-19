"""
Async bot runner — wraps the existing trading engine as two background tasks:

  1. price_poller   — polls MT5 every 5 s for bid/ask/spread
                      emits price_update WebSocket events
  2. cycle_runner   — runs the full strategy loop every CHECK_INTERVAL_SECONDS
                      mirrors main_bot.py logic but writes to SharedBotState
                      emits signal_update, trade_opened, trade_closed, bot_status

MT5's Python library is synchronous and Windows-only.
All blocking calls are wrapped with asyncio.to_thread() so they
do not block the FastAPI event loop.

If MT5 is unavailable (non-Windows dev machine), the runner enters
DISCONNECTED state and keeps retrying every 30 s so the API still
serves — useful for building/testing the frontend with mocked data.
"""

from __future__ import annotations

import asyncio
import sys
import os
from datetime import datetime, date, timezone, timedelta
from typing import Optional

# ── Allow importing bot modules from parent directory ─────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.state import bot_state
from api.ws_manager import ws_manager
from api.database import AsyncSessionLocal
from api.models import EquitySnapshot
from api.broadcaster import broadcast_signal

MT5_AVAILABLE = False
try:
    import config
    from mt5_connector import MT5Connector
    from strategy import TradingStrategy
    from news_filter import NewsFilter
    MT5_AVAILABLE = True
except ImportError:
    pass  # Running outside Windows — bot enters DISCONNECTED mode

PRICE_POLL_INTERVAL = 5        # seconds
RECONNECT_INTERVAL  = 30       # seconds between MT5 reconnect attempts


class BotRunner:
    def __init__(self):
        self._connector: Optional[object] = None
        self._strategy: Optional[object] = None
        self._news_filter: Optional[object] = None
        self._symbol_info: Optional[dict] = None
        self._running = False

        # Tracked open tickets for closed-position detection (mirrors main_bot.py)
        self._tracked_tickets: dict = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        self._running = True
        asyncio.create_task(self._price_poller(), name="price_poller")
        asyncio.create_task(self._cycle_runner(), name="cycle_runner")

    async def stop(self):
        self._running = False
        if self._connector and MT5_AVAILABLE:
            await asyncio.to_thread(self._connector.disconnect)
        bot_state.update(status="DISCONNECTED", mt5_connected=False)

    async def halt(self, reason: str = "Manual kill switch", close_positions: bool = True) -> dict:
        """
        Halt the bot and optionally close all open positions immediately.
        Returns a summary: {"halted": True, "closed": [ticket, ...], "errors": [...]}.
        """
        now = datetime.now(timezone.utc)
        bot_state.update(
            is_halted=True,
            halt_reason=reason,
            halted_at=now,
            status="HALTED",
        )
        await ws_manager.broadcast("bot_status", {
            "status": "HALTED",
            "is_halted": True,
            "halt_reason": reason,
            "halted_at": now.isoformat(),
        })

        closed, errors = [], []
        if close_positions and self._connector and MT5_AVAILABLE:
            try:
                positions = await asyncio.to_thread(
                    self._connector.get_open_positions, config.SYMBOL, config.MAGIC_NUMBER
                )
                for pos in positions:
                    result = await asyncio.to_thread(
                        self._connector.close_trade,
                        pos["ticket"], pos["symbol"], pos["volume"], pos["type"],
                    )
                    if result:
                        closed.append(pos["ticket"])
                        self._tracked_tickets.pop(pos["ticket"], None)
                    else:
                        errors.append(pos["ticket"])

                bot_state.update(positions=[])

            except Exception as exc:
                errors.append(str(exc))

        return {"halted": True, "closed": closed, "errors": errors}

    async def resume(self) -> dict:
        """Clear the manual halt so the cycle runner picks up on the next tick."""
        bot_state.update(
            is_halted=False,
            halt_reason=None,
            halted_at=None,
            status="RUNNING",
        )
        await ws_manager.broadcast("bot_status", {
            "status": "RUNNING",
            "is_halted": False,
        })
        return {"resumed": True}

    # ── Initialisation ────────────────────────────────────────────────────────

    async def _connect(self) -> bool:
        if not MT5_AVAILABLE:
            bot_state.update(status="DISCONNECTED", mt5_connected=False)
            return False

        try:
            self._connector = MT5Connector(
                login=config.MT5_LOGIN,
                password=config.MT5_PASSWORD,
                server=config.MT5_SERVER,
                mt5_path=config.MT5_PATH,
            )
            connected = await asyncio.to_thread(self._connector.connect)
            if not connected:
                bot_state.update(status="DISCONNECTED", mt5_connected=False)
                return False

            self._symbol_info = await asyncio.to_thread(
                self._connector.get_symbol_info, config.SYMBOL
            )
            self._strategy = TradingStrategy(
                fast_ema=config.FAST_EMA_PERIOD,
                slow_ema=config.SLOW_EMA_PERIOD,
                rsi_period=config.RSI_PERIOD,
                rsi_overbought=config.RSI_OVERBOUGHT,
                rsi_oversold=config.RSI_OVERSOLD,
                atr_period=config.ATR_PERIOD,
            )
            self._news_filter = (
                NewsFilter(window_minutes=config.NEWS_FILTER_WINDOW_MINUTES)
                if config.NEWS_FILTER_ENABLED else None
            )

            bot_state.update(status="RUNNING", mt5_connected=True)
            await ws_manager.broadcast("bot_status", {"status": "RUNNING", "mt5_connected": True})
            return True

        except Exception as exc:
            bot_state.update(status="DISCONNECTED", mt5_connected=False, last_cycle_error=str(exc))
            return False

    # ── Fast price poller (every 5 s) ─────────────────────────────────────────

    async def _price_poller(self):
        while self._running:
            try:
                if self._connector and bot_state.get("mt5_connected"):
                    bid, ask = await asyncio.to_thread(
                        self._connector.get_current_price, config.SYMBOL
                    )
                    if bid and ask:
                        spread = round(ask - bid, 5)
                        now = datetime.now(timezone.utc)
                        bot_state.update(bid=bid, ask=ask, spread=spread, price_updated_at=now)

                        await ws_manager.broadcast("price_update", {
                            "bid": bid, "ask": ask, "spread": spread,
                            "timestamp": now.isoformat(),
                        })

                        # Update floating P&L on open positions
                        await self._refresh_positions(bid, ask)

            except Exception:
                pass  # Price poll failures are non-fatal

            await asyncio.sleep(PRICE_POLL_INTERVAL)

    # ── Main strategy cycle ───────────────────────────────────────────────────

    async def _cycle_runner(self):
        # Attempt initial connection
        connected = await self._connect()
        if not connected:
            asyncio.create_task(self._reconnect_loop(), name="reconnect_loop")
            return

        while self._running:
            if not bot_state.get("is_halted"):
                await self._run_one_cycle()
            else:
                # Still emit bot_status so the dashboard knows it's halted
                await ws_manager.broadcast("bot_status", bot_state.to_dict())

            await asyncio.sleep(config.CHECK_INTERVAL_SECONDS if MT5_AVAILABLE else 60)

    async def _reconnect_loop(self):
        """Keep retrying MT5 connection until successful."""
        while self._running and not bot_state.get("mt5_connected"):
            await asyncio.sleep(RECONNECT_INTERVAL)
            connected = await self._connect()
            if connected:
                asyncio.create_task(self._cycle_runner(), name="cycle_runner_retry")
                return

    # ── Single strategy cycle ─────────────────────────────────────────────────

    async def _run_one_cycle(self):
        try:
            now = datetime.now(timezone.utc)

            # ── Daily drawdown reset ──────────────────────────────────────────
            today = now.date()
            if bot_state.get("daily_start_date") != today:
                account = await asyncio.to_thread(self._connector.get_account_info)
                if account:
                    bot_state.update(
                        daily_start_balance=account["balance"],
                        daily_start_date=today,
                        balance=account["balance"],
                        equity=account["equity"],
                        margin=account["margin"],
                        free_margin=account["free_margin"],
                        leverage=account.get("leverage", 0),
                    )

            # ── Refresh account ───────────────────────────────────────────────
            account = await asyncio.to_thread(self._connector.get_account_info)
            if not account:
                return

            bot_state.update(
                balance=account["balance"],
                equity=account["equity"],
                margin=account["margin"],
                free_margin=account["free_margin"],
            )

            # ── Daily drawdown check ──────────────────────────────────────────
            daily_start = bot_state.get("daily_start_balance") or account["balance"]
            daily_loss = daily_start - account["equity"]
            daily_dd_pct = (daily_loss / daily_start * 100) if daily_start > 0 else 0.0
            bot_state.update(daily_drawdown_pct=round(daily_dd_pct, 4))

            if daily_dd_pct >= config.MAX_DAILY_DRAWDOWN_PERCENT:
                bot_state.update(status="PAUSED_DRAWDOWN")
                await ws_manager.broadcast("bot_status", {
                    "status": "PAUSED_DRAWDOWN",
                    "daily_drawdown_pct": daily_dd_pct,
                })
                return

            # ── News filter ───────────────────────────────────────────────────
            news_blocked = False
            if self._news_filter:
                event_data = await asyncio.to_thread(self._news_filter.next_event_data)
                news_blocked = bool(event_data and event_data["is_blackout_active"])

                bot_state.update(
                    news_blocked=news_blocked,
                    next_news_title=event_data["title"] if event_data else None,
                    next_news_time=event_data["scheduled_utc"] if event_data else None,
                    news_resumes_at=event_data["resumes_at"] if event_data else None,
                )

            if news_blocked:
                bot_state.update(status="PAUSED_NEWS")
                await ws_manager.broadcast("bot_status", {"status": "PAUSED_NEWS"})
                return

            # ── Session check ─────────────────────────────────────────────────
            in_session = self._strategy.is_tradeable_session()
            bot_state.update(in_trading_session=in_session)
            if not in_session:
                bot_state.update(status="PAUSED_SESSION")
                await ws_manager.broadcast("bot_status", {"status": "PAUSED_SESSION"})
                return

            bot_state.update(status="RUNNING")

            # ── Fetch bars ────────────────────────────────────────────────────
            df = await asyncio.to_thread(
                self._connector.get_rates, config.SYMBOL, config.TIMEFRAME, config.NUM_BARS
            )
            df_h4 = await asyncio.to_thread(
                self._connector.get_rates, config.SYMBOL, config.HTF_TIMEFRAME, config.H4_BARS
            )
            if df is None or len(df) < 60:
                return

            # ── Generate signal ───────────────────────────────────────────────
            htf_bias, h4_ema_fast, h4_ema_slow = self._strategy.check_htf_trend(df_h4)
            signal, atr = self._strategy.get_signal(df, htf_bias=htf_bias)

            # Derive latest indicator values for the dashboard
            df_ind = self._strategy.add_indicators(df)
            latest = df_ind.iloc[-1]

            ema_fast = float(latest["ema_fast"])
            ema_slow = float(latest["ema_slow"])
            rsi      = float(latest["rsi"])
            atr_val  = float(latest["atr"])

            # Determine human-readable signal type
            signal_type = _classify_signal_type(signal, latest, htf_bias, news_blocked, in_session)

            bot_state.update(
                signal=signal,
                signal_type=signal_type,
                signal_time=now,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                ema_gap=round(ema_fast - ema_slow, 2),
                rsi=round(rsi, 2),
                atr=round(atr_val, 2),
                htf_bias=htf_bias,
                h4_ema_fast=round(h4_ema_fast, 2),
                h4_ema_slow=round(h4_ema_slow, 2),
                h4_ema_gap=round(h4_ema_fast - h4_ema_slow, 2),
                last_cycle_at=now,
                last_cycle_error=None,
            )
            bot_state.push_signal_history(signal, signal_type, now)

            # ── Lot size preview (always compute, even on HOLD) ───────────────
            bid, ask = await asyncio.to_thread(self._connector.get_current_price, config.SYMBOL)
            if bid and ask and self._symbol_info:
                spread = ask - bid
                sl_dist = 1.5 * atr_val + spread
                lot = self._strategy.calculate_position_size(
                    balance=account["balance"],
                    risk_percent=config.RISK_PERCENT_PER_TRADE,
                    sl_distance=sl_dist,
                    symbol_info=self._symbol_info,
                )
                bot_state.update(
                    current_lot_size=lot,
                    sl_distance=round(sl_dist, 4),
                    risk_amount=round(account["balance"] * config.RISK_PERCENT_PER_TRADE / 100, 2),
                )

            # ── Emit signal update WebSocket event ────────────────────────────
            await ws_manager.broadcast("signal_update", {
                "signal": signal,
                "signal_type": signal_type,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "ema_gap": round(ema_fast - ema_slow, 2),
                "rsi": round(rsi, 2),
                "atr": round(atr_val, 2),
                "htf_bias": htf_bias,
                "timestamp": now.isoformat(),
            })

            # ── Persist equity snapshot ───────────────────────────────────────
            await self._save_equity_snapshot(account["balance"], account["equity"], daily_dd_pct)

            # ── Check for closed positions ────────────────────────────────────
            await self._check_closed_positions()

            if signal == "HOLD" or atr <= 0:
                return

            # ── Position deduplication ────────────────────────────────────────
            open_positions = await asyncio.to_thread(
                self._connector.get_open_positions,
                config.SYMBOL, config.MAGIC_NUMBER
            )
            if len(open_positions) >= config.MAX_OPEN_TRADES:
                return
            if any(p["type"] == signal for p in open_positions):
                return

            # ── Place trade ───────────────────────────────────────────────────
            entry = ask if signal == "BUY" else bid
            spread_val = ask - bid
            sl, tp = self._strategy.calculate_sl_tp(
                signal, entry, atr_val, config.TAKE_PROFIT_RR, spread_val
            )
            sl_distance = abs(entry - sl)
            volume = self._strategy.calculate_position_size(
                balance=account["balance"],
                risk_percent=config.RISK_PERCENT_PER_TRADE,
                sl_distance=sl_distance,
                symbol_info=self._symbol_info,
            )

            result = await asyncio.to_thread(
                self._connector.open_trade,
                config.SYMBOL, signal, volume, entry, sl, tp,
                config.MAGIC_NUMBER, "Sentinel_Bot",
            )

            if result:
                position_data = {
                    "ticket": result.order,
                    "symbol": config.SYMBOL,
                    "direction": signal,
                    "volume": volume,
                    "open_price": entry,
                    "sl": sl,
                    "tp": tp,
                    "signal_type": signal_type,
                    "atr_at_entry": round(atr_val, 2),
                    "open_time": now.isoformat(),
                }
                self._tracked_tickets[result.order] = {
                    "type": signal, "volume": volume,
                    "open_price": entry, "sl": sl, "tp": tp,
                    "signal_type": signal_type, "atr_at_entry": round(atr_val, 2),
                    "open_time": now,
                }
                await ws_manager.broadcast("trade_opened", position_data)

                # Broadcast signal to Telegram subscribers and EA queue
                await broadcast_signal(
                    signal=signal,
                    signal_type=signal_type,
                    symbol=config.SYMBOL,
                    entry_price=entry,
                    sl=sl,
                    tp=tp,
                    atr=round(atr_val, 2),
                    lot_size=volume,
                    htf_bias=htf_bias,
                )

        except Exception as exc:
            bot_state.update(last_cycle_error=str(exc), last_cycle_at=datetime.now(timezone.utc))

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _refresh_positions(self, bid: float, ask: float):
        """Update floating P&L on tracked positions and emit position_update if needed."""
        if not self._connector:
            return
        try:
            raw = await asyncio.to_thread(
                self._connector.get_open_positions, config.SYMBOL, config.MAGIC_NUMBER
            )
            enriched = []
            for pos in raw:
                current_price = bid if pos["type"] == "BUY" else ask
                pnl = pos["profit"]

                entry = pos["open_price"]
                sl = pos["sl"]
                tp = pos["tp"]
                atr_entry = self._tracked_tickets.get(pos["ticket"], {}).get("atr_at_entry", 0.0)
                sl_dist = abs(entry - sl) if sl else 0.0
                risk_r = sl_dist * (self._symbol_info["trade_contract_size"] if self._symbol_info else 100) * pos["volume"]
                r_multiple = round(pnl / risk_r, 2) if risk_r > 0 else 0.0

                tp_range = abs(tp - entry) if tp and entry else 1
                tp_progress = min(100.0, max(0.0, abs(current_price - entry) / tp_range * 100))

                open_time_raw = self._tracked_tickets.get(pos["ticket"], {}).get("open_time")
                hold_secs = int((datetime.now(timezone.utc) - open_time_raw).total_seconds()) if open_time_raw else 0

                enriched.append({
                    "ticket": pos["ticket"],
                    "symbol": pos["symbol"],
                    "direction": pos["type"],
                    "volume": pos["volume"],
                    "open_price": pos["open_price"],
                    "current_price": current_price,
                    "sl": sl,
                    "tp": tp,
                    "floating_pnl": round(pnl, 2),
                    "r_multiple": r_multiple,
                    "sl_distance": round(sl_dist, 2),
                    "atr_at_entry": atr_entry,
                    "tp_progress_pct": round(tp_progress, 1),
                    "hold_duration_seconds": hold_secs,
                    "signal_type": self._tracked_tickets.get(pos["ticket"], {}).get("signal_type"),
                    "open_time": open_time_raw.isoformat() if open_time_raw else None,
                })

            bot_state.update(positions=enriched)
            if enriched:
                await ws_manager.broadcast("position_update", {"positions": enriched})

        except Exception:
            pass

    async def _save_equity_snapshot(self, balance: float, equity: float, dd_pct: float):
        """Persist one equity data point to the DB for the equity curve chart."""
        try:
            async with AsyncSessionLocal() as session:
                snapshot = EquitySnapshot(
                    recorded_at=datetime.now(timezone.utc),
                    balance=round(balance, 2),
                    equity=round(equity, 2),
                    daily_drawdown_pct=round(dd_pct, 4),
                )
                session.add(snapshot)
                await session.commit()
        except Exception:
            pass  # Non-fatal — chart will just have a gap

    async def _check_closed_positions(self):
        """Detect positions that closed since the last cycle and emit trade_closed events."""
        if not self._connector:
            return
        try:
            current = await asyncio.to_thread(
                self._connector.get_open_positions, config.SYMBOL, config.MAGIC_NUMBER
            )
            current_tickets = {p["ticket"] for p in current}

            for ticket, info in list(self._tracked_tickets.items()):
                if ticket not in current_tickets:
                    bid_now = bot_state.get("bid")
                    ask_now = bot_state.get("ask")
                    close_price = bid_now if info["type"] == "BUY" else ask_now
                    sl, tp = info.get("sl", 0), info.get("tp", 0)

                    if info["type"] == "BUY":
                        outcome = "WIN" if close_price >= tp > 0 else "LOSS"
                    else:
                        outcome = "WIN" if close_price <= tp > 0 else "LOSS"

                    await ws_manager.broadcast("trade_closed", {
                        "ticket": ticket,
                        "outcome": outcome,
                        "close_price": close_price,
                        "pnl": None,  # exact PnL comes from MT5 history
                    })
                    del self._tracked_tickets[ticket]

            # Track any new positions that appeared externally
            for pos in current:
                if pos["ticket"] not in self._tracked_tickets:
                    self._tracked_tickets[pos["ticket"]] = {
                        "type": pos["type"], "volume": pos["volume"],
                        "open_price": pos["open_price"], "sl": pos["sl"], "tp": pos["tp"],
                        "signal_type": None, "atr_at_entry": 0.0,
                        "open_time": datetime.now(timezone.utc),
                    }

        except Exception:
            pass


# ── Signal type classifier ────────────────────────────────────────────────────

def _classify_signal_type(signal, latest_bar, htf_bias, news_blocked, in_session):
    """Return a human-readable label for the signal origin."""
    if news_blocked:
        return "News Blackout"
    if not in_session:
        return "Outside Session"
    if signal == "HOLD":
        return None

    cross_up  = bool(latest_bar.get("ema_cross_up",  False))
    cross_down = bool(latest_bar.get("ema_cross_down", False))

    if cross_up or cross_down:
        if (signal == "BUY" and htf_bias == "BEARISH") or (signal == "SELL" and htf_bias == "BULLISH"):
            return "Filtered by H4 Bias"
        return "EMA Crossover"

    return "Pullback Entry"


# ── Global singleton ──────────────────────────────────────────────────────────
bot_runner = BotRunner()
