"""
XAUUSD Trading Bot - Main Entry Point
======================================
Connects to Exness MT5, monitors XAUUSD, and executes trades
based on EMA crossover + RSI + ATR strategy.
(Telegram Notifications Disabled)

Usage: python main_bot.py
"""

import time
import sys
from datetime import datetime, date

import config
from mt5_connector import MT5Connector
from strategy import TradingStrategy
from news_filter import NewsFilter
from logger import setup_logger, log_trade

logger = setup_logger(config.LOG_FILE)


def check_closed_positions(connector, tracked_tickets):
    """
    Compare currently open positions against tracked tickets.
    If a tracked ticket is no longer open, it was closed (by TP, SL, or manually).
    """
    current_positions = connector.get_open_positions(
        symbol=config.SYMBOL, magic=config.MAGIC_NUMBER
    )
    current_tickets = {pos["ticket"] for pos in current_positions}

    closed_tickets = []
    for ticket, trade_info in list(tracked_tickets.items()):
        if ticket not in current_tickets:
            # This trade has been closed
            closed_tickets.append(ticket)

            # Get account info to calculate profit
            account = connector.get_account_info()

            # Determine close reason
            bid, ask = connector.get_current_price(config.SYMBOL)
            close_price = bid if trade_info["type"] == "BUY" else ask
            if close_price is None:
                close_price = 0.0

            # Determine if it hit TP, SL, or was closed manually
            sl = trade_info["sl"]
            tp = trade_info["tp"]
            close_reason = "Closed Manually"

            if trade_info["type"] == "BUY":
                if close_price >= tp and tp > 0:
                    close_reason = "Take Profit Hit"
                elif close_price <= sl and sl > 0:
                    close_reason = "Stop Loss Hit"
            elif trade_info["type"] == "SELL":
                if close_price <= tp and tp > 0:
                    close_reason = "Take Profit Hit"
                elif close_price >= sl and sl > 0:
                    close_reason = "Stop Loss Hit"

            logger.info(f"Trade closed | Ticket: {ticket} | {trade_info['type']} | "
                        f"Reason: {close_reason} | Close Price: {close_price:.2f}")

    # Remove closed tickets from tracking
    for ticket in closed_tickets:
        del tracked_tickets[ticket]

    # Add any new positions that appeared (e.g., opened manually)
    for pos in current_positions:
        if pos["ticket"] not in tracked_tickets:
            tracked_tickets[pos["ticket"]] = {
                "type": pos["type"],
                "volume": pos["volume"],
                "open_price": pos["open_price"],
                "sl": pos["sl"],
                "tp": pos["tp"],
            }

    return tracked_tickets


def main():
    logger.info("=" * 60)
    logger.info("XAUUSD Trading Bot Starting...")
    logger.info("=" * 60)

    # Initialize MT5 connection
    connector = MT5Connector(
        login=config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
        mt5_path=config.MT5_PATH,
    )

    if not connector.connect():
        logger.error("Failed to connect to MT5. Exiting.")
        sys.exit(1)

    # Initialize news filter
    news_filter = NewsFilter(window_minutes=config.NEWS_FILTER_WINDOW_MINUTES) if config.NEWS_FILTER_ENABLED else None

    # Initialize strategy
    strategy = TradingStrategy(
        fast_ema=config.FAST_EMA_PERIOD,
        slow_ema=config.SLOW_EMA_PERIOD,
        rsi_period=config.RSI_PERIOD,
        rsi_overbought=config.RSI_OVERBOUGHT,
        rsi_oversold=config.RSI_OVERSOLD,
        atr_period=config.ATR_PERIOD,
    )

    # Get symbol info
    symbol_info = connector.get_symbol_info(config.SYMBOL)
    if symbol_info is None:
        logger.error(f"Cannot get symbol info for {config.SYMBOL}. Exiting.")
        connector.disconnect()
        sys.exit(1)

    strategy_info = (f"EMA({config.FAST_EMA_PERIOD}/{config.SLOW_EMA_PERIOD}) + "
                     f"RSI({config.RSI_PERIOD}) + ATR({config.ATR_PERIOD})")

    logger.info(f"Symbol: {config.SYMBOL} | Point: {symbol_info['point']} | "
                f"Min Lot: {symbol_info['volume_min']} | Max Lot: {symbol_info['volume_max']}")
    logger.info(f"Strategy: {strategy_info}")
    logger.info(f"Risk: {config.RISK_PERCENT_PER_TRADE}% per trade | RR: 1:{config.TAKE_PROFIT_RR}")
    logger.info(f"Checking every {config.CHECK_INTERVAL_SECONDS} seconds...")
    logger.info("-" * 60)

    # Track daily starting balance for drawdown check
    daily_start_balance = None
    current_date = None

    # Track open positions for close detection (TP, SL, manual)
    tracked_tickets = {}
    # Load any already-open positions at startup
    existing_positions = connector.get_open_positions(
        symbol=config.SYMBOL, magic=config.MAGIC_NUMBER
    )
    for pos in existing_positions:
        tracked_tickets[pos["ticket"]] = {
            "type": pos["type"],
            "volume": pos["volume"],
            "open_price": pos["open_price"],
            "sl": pos["sl"],
            "tp": pos["tp"],
        }
    if tracked_tickets:
        logger.info(f"Tracking {len(tracked_tickets)} existing open position(s).")

    try:
        while True:
            try:
                # Reset daily balance tracker at the start of each new day
                today = date.today()
                if current_date != today:
                    account = connector.get_account_info()
                    if account:
                        daily_start_balance = account["balance"]
                        current_date = today
                        logger.info(f"New day: {today} | Starting balance: {daily_start_balance:.2f}")

                # Check daily drawdown
                account = connector.get_account_info()
                if account and daily_start_balance:
                    daily_loss = daily_start_balance - account["equity"]
                    daily_loss_pct = (daily_loss / daily_start_balance) * 100
                    if daily_loss_pct >= config.MAX_DAILY_DRAWDOWN_PERCENT:
                        logger.warning(f"Daily drawdown limit reached: {daily_loss_pct:.2f}%. "
                                       f"Pausing trading for today.")
                        time.sleep(config.CHECK_INTERVAL_SECONDS)
                        continue

                # ---- CHECK FOR CLOSED POSITIONS (TP, SL, MANUAL) ----
                tracked_tickets = check_closed_positions(connector, tracked_tickets)

                # Get historical data (entry timeframe + H4 for trend filter)
                df = connector.get_rates(config.SYMBOL, config.TIMEFRAME, num_bars=config.NUM_BARS)
                if df is None or len(df) < 60:
                    logger.warning("Not enough data. Waiting for next cycle...")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                df_h4 = connector.get_rates(config.SYMBOL, config.HTF_TIMEFRAME, num_bars=config.H4_BARS)

                # Get current price
                bid, ask = connector.get_current_price(config.SYMBOL)
                if bid is None:
                    logger.warning("Cannot get current price. Waiting...")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                logger.info(f"XAUUSD | Bid: {bid:.2f} | Ask: {ask:.2f} | "
                            f"Balance: {account['balance']:.2f} | Equity: {account['equity']:.2f}")

                # Check existing positions
                open_positions = connector.get_open_positions(
                    symbol=config.SYMBOL, magic=config.MAGIC_NUMBER
                )

                if len(open_positions) >= config.MAX_OPEN_TRADES:
                    logger.info(f"Max open trades reached ({len(open_positions)}/{config.MAX_OPEN_TRADES}). "
                                f"Waiting...")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # Check news blackout window before generating any signal
                if news_filter and news_filter.is_blocked():
                    logger.info("News filter active — skipping this cycle.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # Get H4 trend bias, then generate entry-timeframe signal
                htf_bias = strategy.check_htf_trend(df_h4)
                logger.info(f"H4 trend bias: {htf_bias}")
                signal, atr = strategy.get_signal(df, htf_bias=htf_bias)

                if signal == "HOLD":
                    logger.info("Signal: HOLD — No trade opportunity.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # Skip if a position in the same direction is already open
                same_dir = [p for p in open_positions if p["type"] == signal]
                if same_dir:
                    logger.info(f"Skipping {signal} — {len(same_dir)} open {signal} position(s) already exist.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                if atr <= 0:
                    logger.warning("ATR is zero or negative. Skipping.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # Determine entry price and spread
                spread = ask - bid
                if signal == "BUY":
                    entry_price = ask
                else:
                    entry_price = bid

                # Calculate SL and TP (spread widens effective SL distance)
                sl, tp = strategy.calculate_sl_tp(signal, entry_price, atr, config.TAKE_PROFIT_RR, spread)

                # Calculate position size
                sl_distance = abs(entry_price - sl)
                volume = strategy.calculate_position_size(
                    balance=account["balance"],
                    risk_percent=config.RISK_PERCENT_PER_TRADE,
                    sl_distance=sl_distance,
                    symbol_info=symbol_info,
                )

                logger.info(f"Placing {signal} order | Entry: {entry_price:.2f} | "
                            f"SL: {sl:.2f} | TP: {tp:.2f} | Volume: {volume}")

                # Place the trade
                result = connector.open_trade(
                    symbol=config.SYMBOL,
                    order_type=signal,
                    volume=volume,
                    price=entry_price,
                    sl=sl,
                    tp=tp,
                    magic=config.MAGIC_NUMBER,
                    comment="XAUUSD_Bot",
                )

                if result:
                    log_trade(
                        config.LOG_FILE, signal, config.SYMBOL,
                        volume, entry_price, sl, tp,
                        result_comment=f"Ticket: {result.order}"
                    )
                    logger.info(f"Trade executed successfully! Ticket: {result.order}")

                    # Track the new trade for close detection
                    tracked_tickets[result.order] = {
                        "type": signal,
                        "volume": volume,
                        "open_price": entry_price,
                        "sl": sl,
                        "tp": tp,
                    }
                else:
                    logger.error("Trade execution failed.")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            # Wait before next check
            time.sleep(config.CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")
    finally:
        connector.disconnect()
        logger.info("Bot shut down complete.")


if __name__ == "__main__":
    main()