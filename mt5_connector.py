import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from logger import setup_logger

logger = setup_logger()

# Timeframe mapping
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Connector:
    """Handles all communication with MetaTrader 5 using the official Python library."""

    def __init__(self, login, password, server, mt5_path=None):
        self.login = login
        self.password = password
        self.server = server
        self.mt5_path = mt5_path
        self.connected = False

    def connect(self):
        """Initialize MT5 and log in to the trading account."""
        if self.mt5_path:
            initialized = mt5.initialize(self.mt5_path)
        else:
            initialized = mt5.initialize()

        if not initialized:
            logger.error(f"MT5 initialize() failed. Error: {mt5.last_error()}")
            return False

        authorized = mt5.login(self.login, password=self.password, server=self.server)
        if not authorized:
            logger.error(f"MT5 login failed. Error: {mt5.last_error()}")
            mt5.shutdown()
            return False

        account_info = mt5.account_info()
        logger.info(f"Connected to MT5 | Account: {account_info.login} | "
                     f"Server: {account_info.server} | Balance: {account_info.balance}")
        self.connected = True
        return True

    def disconnect(self):
        """Shut down the MT5 connection."""
        mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5.")

    def get_account_info(self):
        """Return account balance, equity, and margin info."""
        info = mt5.account_info()
        if info is None:
            logger.error(f"Failed to get account info. Error: {mt5.last_error()}")
            return None
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "leverage": info.leverage,
        }

    def get_rates(self, symbol, timeframe_str, num_bars=100):
        """Fetch historical OHLCV data as a pandas DataFrame."""
        timeframe = TIMEFRAME_MAP.get(timeframe_str)
        if timeframe is None:
            logger.error(f"Invalid timeframe: {timeframe_str}")
            return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get rates for {symbol}. Error: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_current_price(self, symbol):
        """Get the current bid/ask price for a symbol."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Failed to get tick for {symbol}. Error: {mt5.last_error()}")
            return None, None
        return tick.bid, tick.ask

    def get_symbol_info(self, symbol):
        """Get symbol specifications (point, digits, volume constraints, etc.)."""
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"Failed to get symbol info for {symbol}. Error: {mt5.last_error()}")
            return None

        # Make sure the symbol is visible in Market Watch
        if not info.visible:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)

        return {
            "point": info.point,
            "digits": info.digits,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "trade_contract_size": info.trade_contract_size,
        }

    def _try_filling_modes(self, request, label="Order"):
        """
        Try all three filling modes in sequence until one succeeds.
        Exness and some brokers do not reliably report supported modes
        via symbol_info.filling_mode, so we brute-force all options.
        Returns the result on success, or None if all modes fail.
        """
        filling_modes = [
            (mt5.ORDER_FILLING_RETURN, "RETURN"),
            (mt5.ORDER_FILLING_IOC,    "IOC"),
            (mt5.ORDER_FILLING_FOK,    "FOK"),
        ]

        for filling, name in filling_modes:
            request["type_filling"] = filling
            result = mt5.order_send(request)

            if result is None:
                logger.warning(f"{label} | Filling {name} → order_send() returned None")
                continue

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"{label} succeeded with filling mode: {name}")
                return result

            if result.retcode == 10030:  # Unsupported filling mode — try next
                logger.warning(f"{label} | Filling {name} not supported (10030), trying next...")
                continue

            # Any other error is a real failure — stop retrying
            logger.error(f"{label} failed | Retcode: {result.retcode} | Comment: {result.comment}")
            return None

        logger.error(f"{label} failed — no supported filling mode found for this broker/symbol.")
        return None

    def open_trade(self, symbol, order_type, volume, price, sl, tp, magic, comment="XAUUSD_Bot"):
        """Send a market order to open a trade."""
        if order_type == "BUY":
            mt5_order_type = mt5.ORDER_TYPE_BUY
        elif order_type == "SELL":
            mt5_order_type = mt5.ORDER_TYPE_SELL
        else:
            logger.error(f"Invalid order type: {order_type}")
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,  # Will be overridden by _try_filling_modes
        }

        result = self._try_filling_modes(request, label=f"{order_type} {volume} {symbol}")
        if result is None:
            return None

        logger.info(f"Order placed | {order_type} {volume} {symbol} @ {price} | "
                     f"SL: {sl} | TP: {tp} | Ticket: {result.order}")
        return result

    def get_open_positions(self, symbol=None, magic=None):
        """Get all open positions, optionally filtered by symbol and magic number."""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        positions_list = []
        for pos in positions:
            if magic is not None and pos.magic != magic:
                continue
            positions_list.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "open_price": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "magic": pos.magic,
                "comment": pos.comment,
            })
        return positions_list

    def close_trade(self, ticket, symbol, volume, order_type):
        """Close an open position by ticket."""
        if order_type == "BUY":
            close_type = mt5.ORDER_TYPE_SELL
            bid, ask = self.get_current_price(symbol)
            price = bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            bid, ask = self.get_current_price(symbol)
            price = ask

        if price is None:
            logger.error("Cannot close trade — failed to get current price.")
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "magic": 0,
            "comment": "XAUUSD_Bot_Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,  # Will be overridden by _try_filling_modes
        }

        result = self._try_filling_modes(request, label=f"Close ticket {ticket}")
        if result is None:
            return None

        logger.info(f"Position closed | Ticket: {ticket} | {order_type} {volume} {symbol} @ {price}")
        return result
