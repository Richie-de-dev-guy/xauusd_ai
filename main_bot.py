"""
XAUUSD Trading Bot - Main Entry Point
======================================
Connects to Exness MT5, monitors XAUUSD, and executes trades
based on EMA crossover + RSI + ATR strategy.
Sends Telegram alerts for all trade activity including
TP hits, SL hits, and manual closes.

Usage: python main_bot.py
"""

import time
import sys
from datetime import datetime, date

import config
from mt5_connector import MT5Connector
from strategy import TradingStrategy
from logger import setup_logger, log_trade
from telegram_notifier import TelegramNotifier

logger = setup_logger(config.LOG_FILE)


def check_closed_positions(connector, tracked_tickets, telegram):
    """
    Compare currently open positions against tracked tickets.
    If a tracked ticket is no longer open, it was closed (by TP, SL, or manually).
    Send a Telegram notification for each closed trade.
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

            # Estimate profit based on direction
            if trade_info["type"] == "BUY":
                profit_points = close_price - trade_info["open_price"]
            else:
                profit_points = trade_info["open_price"] - close_price

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

            if telegram:
                emoji = "🎯" if close_reason == "Take Profit Hit" else "🛑" if close_reason == "Stop Loss Hit" else "✋"
                msg = (
                    f"{emoji} <b>Trade Closed — {close_reason}</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"Type: {trade_info['type']}\n"
                    f"Symbol: {config.SYMBOL}\n"
                    f"Volume: {trade_info['volume']}\n"
                    f"Open Price: {trade_info['open_price']:.2f}\n"
                    f"Close Price: {close_price:.2f}\n"
                    f"SL: {sl:.2f} | TP: {tp:.2f}\n"
                    f"Ticket: <code>{ticket}</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                )
                telegram.send_message(msg)

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

    # Initialize Telegram notifier
    telegram = None
    if config.TELEGRAM_ENABLED:
        telegram = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        logger.info("Telegram notifications enabled.")

    # Initialize MT5 connection
    connector = MT5Connector(
        login=config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
        mt5_path=config.MT5_PATH,
    )

    if not connector.connect():
        logger.error("Failed to connect to MT5. Exiting.")
        if telegram:
            telegram.notify_error("Failed to connect to MT5. Bot exiting.")
        sys.exit(1)

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
        if telegram:
            telegram.notify_error(f"Cannot get symbol info for {config.SYMBOL}. Bot exiting.")
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

    # Send Telegram startup notification
    account_info = connector.get_account_info()
    if telegram and account_info:
        telegram.notify_bot_started(
            account=config.MT5_LOGIN,
            server=config.MT5_SERVER,
            balance=account_info["balance"],
            symbol=config.SYMBOL,
            strategy_info=strategy_info,
        )

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
                        if telegram:
                            telegram.notify_drawdown_limit(daily_loss_pct)
                        time.sleep(config.CHECK_INTERVAL_SECONDS)
                        continue

                # ---- CHECK FOR CLOSED POSITIONS (TP, SL, MANUAL) ----
                tracked_tickets = check_closed_positions(connector, tracked_tickets, telegram)

                # Get historical data
                df = connector.get_rates(config.SYMBOL, config.TIMEFRAME, num_bars=100)
                if df is None or len(df) < 60:
                    logger.warning("Not enough data. Waiting for next cycle...")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

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

                # Get trading signal
                signal, atr = strategy.get_signal(df)

                if signal == "HOLD":
                    logger.info("Signal: HOLD — No trade opportunity.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                if atr <= 0:
                    logger.warning("ATR is zero or negative. Skipping.")
                    time.sleep(config.CHECK_INTERVAL_SECONDS)
                    continue

                # Determine entry price
                if signal == "BUY":
                    entry_price = ask
                else:
                    entry_price = bid

                # Calculate SL and TP
                sl, tp = strategy.calculate_sl_tp(signal, entry_price, atr, config.TAKE_PROFIT_RR)

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

                    # Send Telegram alert
                    if telegram:
                        telegram.notify_trade_opened(
                            order_type=signal,
                            symbol=config.SYMBOL,
                            volume=volume,
                            entry_price=entry_price,
                            sl=sl,
                            tp=tp,
                            ticket=result.order,
                        )
                else:
                    logger.error("Trade execution failed.")
                    if telegram:
                        telegram.notify_error(f"Trade execution failed for {signal} {config.SYMBOL}")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                if telegram:
                    telegram.notify_error(f"Bot error: {e}")

            # Wait before next check
            time.sleep(config.CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C).")
    finally:
        if telegram:
            telegram.notify_bot_stopped()
        connector.disconnect()
        logger.info("Bot shut down complete.")


if __name__ == "__main__":
    main()
