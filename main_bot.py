"""
XAUUSD Trading Bot — Mean Reversion Scalper (M5)
=================================================
Single-strategy bot. Polls every 60s. Trades only during NY-overlap hours.
Targets the snap-back after Gold overextends — see strategy_mean_reversion.py.

Usage: python main_bot.py
"""

import time
import sys
from datetime import date

import config
from mt5_connector import MT5Connector
from strategy_mean_reversion import MeanReversionScalper, PIP_SIZE
from news_filter import NewsFilter
from logger import setup_logger, log_trade

logger = setup_logger(config.LOG_FILE)


def check_closed_positions(connector, tracked_tickets):
    """Detect closes (TP, SL, manual) by comparing tracked tickets to MT5's open list."""
    current = connector.get_open_positions(symbol=config.SYMBOL, magic=config.MAGIC_NUMBER)
    current_tickets = {p["ticket"] for p in current}

    for ticket in [t for t in tracked_tickets if t not in current_tickets]:
        info = tracked_tickets[ticket]
        bid, ask = connector.get_current_price(config.SYMBOL)
        close_price = (bid if info["type"] == "BUY" else ask) or 0.0
        sl, tp = info["sl"], info["tp"]
        reason = "Closed Manually"
        if info["type"] == "BUY":
            if tp > 0 and close_price >= tp: reason = "Take Profit Hit"
            elif sl > 0 and close_price <= sl: reason = "Stop Loss Hit"
        else:
            if tp > 0 and close_price <= tp: reason = "Take Profit Hit"
            elif sl > 0 and close_price >= sl: reason = "Stop Loss Hit"
        logger.info(f"Trade closed | Ticket: {ticket} | {info['type']} | "
                    f"Reason: {reason} | Close: {close_price:.2f}")
        del tracked_tickets[ticket]

    for pos in current:
        if pos["ticket"] not in tracked_tickets:
            tracked_tickets[pos["ticket"]] = {
                "type": pos["type"], "volume": pos["volume"],
                "open_price": pos["open_price"], "sl": pos["sl"], "tp": pos["tp"],
            }
    return tracked_tickets


def main():
    logger.info("=" * 60)
    logger.info("XAUUSD Mean Reversion Scalper Starting (M5)...")
    logger.info("=" * 60)

    connector = MT5Connector(
        login=config.MT5_LOGIN, password=config.MT5_PASSWORD,
        server=config.MT5_SERVER, mt5_path=config.MT5_PATH,
    )
    if not connector.connect():
        logger.error("Failed to connect to MT5. Exiting.")
        sys.exit(1)

    news_filter = NewsFilter(window_minutes=config.NEWS_FILTER_WINDOW_MINUTES) \
        if config.NEWS_FILTER_ENABLED else None

    strategy = MeanReversionScalper(
        rsi_period=config.SCALPER_RSI_PERIOD,
        overbought_extreme=config.SCALPER_RSI_OB_EXTREME,
        oversold_extreme=config.SCALPER_RSI_OS_EXTREME,
        neutral_upper=config.SCALPER_RSI_NEUTRAL_UPPER,
        neutral_lower=config.SCALPER_RSI_NEUTRAL_LOWER,
        extreme_lookback=config.SCALPER_EXTREME_LOOKBACK,
        sl_pips=config.SCALPER_SL_PIPS,
        tp_pips=config.SCALPER_TP_PIPS,
        session_start_utc=config.SCALPER_SESSION_START_UTC,
        session_end_utc=config.SCALPER_SESSION_END_UTC,
        max_spread_pips=config.SCALPER_MAX_SPREAD_PIPS,
    )

    symbol_info = connector.get_symbol_info(config.SYMBOL)
    if symbol_info is None:
        logger.error(f"Cannot get symbol info for {config.SYMBOL}. Exiting.")
        connector.disconnect()
        sys.exit(1)

    logger.info(f"Symbol: {config.SYMBOL} | Timeframe: {config.TIMEFRAME}")
    logger.info(f"RSI({strategy.rsi_period}) extremes {strategy.oversold_extreme}/{strategy.overbought_extreme} "
                f"→ neutral {strategy.neutral_lower}/{strategy.neutral_upper}")
    logger.info(f"SL/TP: {strategy.sl_pips}/{strategy.tp_pips} pips  |  "
                f"Session: {strategy.session_start_utc:.1f}–{strategy.session_end_utc:.1f} UTC  |  "
                f"Max spread: {strategy.max_spread_pips} pips")
    logger.info(f"Risk: {config.RISK_PERCENT_PER_TRADE}% per trade  |  "
                f"Max open: {config.MAX_OPEN_TRADES}  |  Poll: {config.CHECK_INTERVAL_SECONDS}s")
    logger.info("-" * 60)

    daily_start_balance = None
    current_date = None
    tracked_tickets = {}

    # Load any pre-existing positions for this magic
    for pos in connector.get_open_positions(symbol=config.SYMBOL, magic=config.MAGIC_NUMBER):
        tracked_tickets[pos["ticket"]] = {
            "type": pos["type"], "volume": pos["volume"],
            "open_price": pos["open_price"], "sl": pos["sl"], "tp": pos["tp"],
        }
    if tracked_tickets:
        logger.info(f"Tracking {len(tracked_tickets)} existing open position(s).")

    try:
        while True:
            try:
                # ---- Daily balance / drawdown ----
                today = date.today()
                if current_date != today:
                    account = connector.get_account_info()
                    if account:
                        daily_start_balance = account["balance"]
                        current_date = today
                        logger.info(f"New day: {today} | Starting balance: {daily_start_balance:.2f}")

                account = connector.get_account_info()
                if account and daily_start_balance:
                    dd_pct = (daily_start_balance - account["equity"]) / daily_start_balance * 100
                    if dd_pct >= config.MAX_DAILY_DRAWDOWN_PERCENT:
                        logger.warning(f"Daily drawdown limit hit: {dd_pct:.2f}%. Pausing.")
                        time.sleep(config.CHECK_INTERVAL_SECONDS)
                        continue

                tracked_tickets = check_closed_positions(connector, tracked_tickets)

                # ---- Session gate (live clock) ----
                if not strategy.is_tradeable_session_now():
                    logger.info("Outside NY-overlap session. Waiting.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- Market data ----
                df = connector.get_rates(config.SYMBOL, config.TIMEFRAME, num_bars=config.NUM_BARS)
                if df is None or len(df) < strategy.rsi_period + strategy.extreme_lookback + 5:
                    logger.warning("Not enough data. Waiting.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                bid, ask = connector.get_current_price(config.SYMBOL)
                if bid is None:
                    logger.warning("No current price. Waiting.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                spread_pips = (ask - bid) / PIP_SIZE
                logger.info(f"XAUUSD | Bid: {bid:.2f} | Ask: {ask:.2f} | "
                            f"Spread: {spread_pips:.1f} pips | "
                            f"Balance: {account['balance']:.2f} | Equity: {account['equity']:.2f}")

                # ---- Capacity check ----
                open_positions = connector.get_open_positions(
                    symbol=config.SYMBOL, magic=config.MAGIC_NUMBER
                )
                if len(open_positions) >= config.MAX_OPEN_TRADES:
                    logger.info(f"Max open trades reached ({len(open_positions)}/{config.MAX_OPEN_TRADES}). Waiting.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- News filter (off by default for this strategy) ----
                if news_filter and news_filter.is_blocked():
                    logger.info("News filter active — skipping cycle.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- Spread guard ----
                if not strategy.spread_ok(bid, ask):
                    logger.info(f"Spread too wide ({spread_pips:.1f} > {strategy.max_spread_pips} pips). Skipping.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- Generate signal ----
                df_ind = strategy.add_indicators(df)
                signal = strategy.signal_at(df_ind, len(df_ind) - 1)
                latest_rsi = df_ind["rsi"].iloc[-1]
                logger.info(f"Latest RSI({strategy.rsi_period}): {latest_rsi:.1f} | Signal: {signal}")

                if signal == "HOLD":
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- Same-direction skip ----
                same_dir = [p for p in open_positions if p["type"] == signal]
                if same_dir:
                    logger.info(f"Skipping {signal} — {len(same_dir)} open {signal} position(s) already exist.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # ---- Place trade ----
                spread = ask - bid
                entry_price = ask if signal == "BUY" else bid
                sl, tp = strategy.calculate_sl_tp(signal, entry_price, spread=spread)
                sl_distance = abs(entry_price - sl)

                volume = strategy.calculate_position_size(
                    balance=account["balance"],
                    risk_percent=config.RISK_PERCENT_PER_TRADE,
                    sl_distance=sl_distance,
                    symbol_info=symbol_info,
                )

                logger.info(f"Placing {signal} | Entry: {entry_price:.2f} | "
                            f"SL: {sl:.2f} | TP: {tp:.2f} | Volume: {volume}")

                result = connector.open_trade(
                    symbol=config.SYMBOL, order_type=signal, volume=volume, price=entry_price,
                    sl=sl, tp=tp, magic=config.MAGIC_NUMBER, comment="XAUUSD_Scalper",
                )

                if result:
                    log_trade(config.LOG_FILE, signal, config.SYMBOL, volume, entry_price, sl, tp,
                              result_comment=f"Ticket: {result.order}")
                    logger.info(f"Trade executed. Ticket: {result.order}")
                    tracked_tickets[result.order] = {
                        "type": signal, "volume": volume, "open_price": entry_price,
                        "sl": sl, "tp": tp,
                    }
                else:
                    logger.error("Trade execution failed.")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            time.sleep(config.CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")
    finally:
        connector.disconnect()
        logger.info("Bot shut down complete.")


if __name__ == "__main__":
    main()
