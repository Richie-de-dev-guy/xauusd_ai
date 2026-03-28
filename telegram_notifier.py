"""
Telegram Notifier
=================
Sends trade alerts and bot status updates to Telegram.
"""

import requests
from logger import setup_logger

logger = setup_logger()


class TelegramNotifier:
    """Send messages to a Telegram bot."""

    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text):
        """Send a text message to the configured Telegram chat."""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully.")
            else:
                logger.warning(f"Telegram send failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Telegram notification error: {e}")

    def notify_bot_started(self, account, server, balance, symbol, strategy_info):
        """Send a notification when the bot starts."""
        msg = (
            "<b>XAUUSD Trading Bot Started</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Account: <code>{account}</code>\n"
            f"Server: {server}\n"
            f"Balance: ${balance:,.2f}\n"
            f"Symbol: {symbol}\n"
            f"Strategy: {strategy_info}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Bot is now monitoring the market."
        )
        self.send_message(msg)

    def notify_trade_opened(self, order_type, symbol, volume, entry_price, sl, tp, ticket):
        """Send a notification when a trade is opened."""
        emoji = "🟢" if order_type == "BUY" else "🔴"
        msg = (
            f"{emoji} <b>Trade Opened — {order_type}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Symbol: {symbol}\n"
            f"Volume: {volume}\n"
            f"Entry: {entry_price:.2f}\n"
            f"Stop Loss: {sl:.2f}\n"
            f"Take Profit: {tp:.2f}\n"
            f"Ticket: <code>{ticket}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_message(msg)

    def notify_trade_closed(self, order_type, symbol, volume, close_price, profit, ticket):
        """Send a notification when a trade is closed."""
        emoji = "💰" if profit >= 0 else "📉"
        profit_text = f"+${profit:,.2f}" if profit >= 0 else f"-${abs(profit):,.2f}"
        msg = (
            f"{emoji} <b>Trade Closed — {order_type}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Symbol: {symbol}\n"
            f"Volume: {volume}\n"
            f"Close Price: {close_price:.2f}\n"
            f"Profit: {profit_text}\n"
            f"Ticket: <code>{ticket}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_message(msg)

    def notify_signal(self, signal, bid, ask, balance, equity):
        """Send a notification about the current signal check."""
        msg = (
            f"<b>Signal: {signal}</b>\n"
            f"XAUUSD Bid: {bid:.2f} | Ask: {ask:.2f}\n"
            f"Balance: ${balance:,.2f} | Equity: ${equity:,.2f}"
        )
        self.send_message(msg)

    def notify_drawdown_limit(self, daily_loss_pct):
        """Send a warning when daily drawdown limit is reached."""
        msg = (
            "⚠️ <b>DAILY DRAWDOWN LIMIT REACHED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Daily Loss: {daily_loss_pct:.2f}%\n"
            "Trading paused for today.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_message(msg)

    def notify_error(self, error_msg):
        """Send an error notification."""
        msg = (
            "❌ <b>Bot Error</b>\n"
            f"{error_msg}"
        )
        self.send_message(msg)

    def notify_bot_stopped(self):
        """Send a notification when the bot stops."""
        msg = (
            "🛑 <b>XAUUSD Trading Bot Stopped</b>\n"
            "The bot has been shut down."
        )
        self.send_message(msg)
