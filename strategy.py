import pandas as pd
import numpy as np
from datetime import datetime, timezone
from logger import setup_logger

logger = setup_logger()


class TradingStrategy:
    """
    XAUUSD Trading Strategy
    -----------------------
    Trend-following strategy using:
    - EMA crossover (fast/slow) for trend direction
    - RSI for momentum confirmation and filtering
    - ATR for dynamic stop-loss placement

    Entry Rules:
    - BUY:  Fast EMA crosses above Slow EMA + RSI < overbought level
    - SELL: Fast EMA crosses below Slow EMA + RSI > oversold level

    Exit Rules:
    - Stop Loss: Based on ATR (1.5x ATR from entry)
    - Take Profit: Based on risk-to-reward ratio
    """

    def __init__(self, fast_ema, slow_ema, rsi_period, rsi_overbought, rsi_oversold, atr_period):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.atr_period = atr_period
        self.last_signal = "HOLD"

    def is_tradeable_session(self):
        """Return True during London and New York sessions (07:00–22:00 UTC).
        Skips the Asian low-liquidity window where EMA crossovers on Gold produce more noise."""
        hour = datetime.now(timezone.utc).hour
        return 7 <= hour < 22

    def calculate_ema(self, series, period):
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, series, period):
        """Calculate Relative Strength Index."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        # Use exponential smoothing after the first SMA
        for i in range(period, len(series)):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, df, period):
        """Calculate Average True Range."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's smoothing: alpha = 1/period (equivalent to com = period - 1)
        atr = true_range.ewm(com=period - 1, min_periods=period, adjust=False).mean()
        return atr

    def add_indicators(self, df):
        """Add all technical indicators to the dataframe."""
        df = df.copy()
        df["ema_fast"] = self.calculate_ema(df["close"], self.fast_ema)
        df["ema_slow"] = self.calculate_ema(df["close"], self.slow_ema)
        df["rsi"] = self.calculate_rsi(df["close"], self.rsi_period)
        df["atr"] = self.calculate_atr(df, self.atr_period)

        # EMA crossover detection
        df["ema_cross_up"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        df["ema_cross_down"] = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))

        return df

    def check_htf_trend(self, df_h4):
        """
        Determine the H4 trend direction using the same EMA pair.

        Returns "BULLISH", "BEARISH", or "NEUTRAL".
        - BULLISH : fast EMA > slow EMA on H4 — only BUY signals pass the filter.
        - BEARISH : fast EMA < slow EMA on H4 — only SELL signals pass the filter.
        - NEUTRAL : not enough data; filter is bypassed (no signals blocked).
        """
        if df_h4 is None or len(df_h4) < self.slow_ema + 5:
            logger.warning("H4 trend filter: not enough H4 bars — filter bypassed.")
            return "NEUTRAL"

        df = df_h4.copy()
        df["ema_fast"] = self.calculate_ema(df["close"], self.fast_ema)
        df["ema_slow"] = self.calculate_ema(df["close"], self.slow_ema)

        latest_fast = df["ema_fast"].iloc[-1]
        latest_slow = df["ema_slow"].iloc[-1]

        if latest_fast > latest_slow:
            return "BULLISH"
        elif latest_fast < latest_slow:
            return "BEARISH"
        return "NEUTRAL"

    def get_signal(self, df, htf_bias="NEUTRAL"):
        """
        Analyze the latest data and return a trading signal.

        Parameters
        ----------
        df        : DataFrame of M15 (or H1) OHLCV bars
        htf_bias  : "BULLISH", "BEARISH", or "NEUTRAL" from check_htf_trend().
                    When BULLISH, SELL signals are suppressed.
                    When BEARISH, BUY signals are suppressed.

        Returns: ("BUY" | "SELL" | "HOLD", atr_value)
        """
        if not self.is_tradeable_session():
            logger.info("Outside trading session (07:00–22:00 UTC). Signal: HOLD.")
            return "HOLD", 0.0

        df = self.add_indicators(df)

        if len(df) < self.slow_ema + 5:
            logger.warning("Not enough data to generate a signal.")
            return "HOLD", 0.0

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ema_fast = latest["ema_fast"]
        ema_slow = latest["ema_slow"]
        rsi = latest["rsi"]
        atr = latest["atr"]
        ema_cross_up = latest["ema_cross_up"]
        ema_cross_down = latest["ema_cross_down"]

        signal = "HOLD"

        # BUY signal: Fast EMA crosses above Slow EMA + RSI not overbought
        if ema_cross_up and rsi < self.rsi_overbought:
            signal = "BUY"
            logger.info(f"BUY signal | EMA Fast: {ema_fast:.2f} > EMA Slow: {ema_slow:.2f} | RSI: {rsi:.2f} | ATR: {atr:.2f}")

        # SELL signal: Fast EMA crosses below Slow EMA + RSI not oversold
        elif ema_cross_down and rsi > self.rsi_oversold:
            signal = "SELL"
            logger.info(f"SELL signal | EMA Fast: {ema_fast:.2f} < EMA Slow: {ema_slow:.2f} | RSI: {rsi:.2f} | ATR: {atr:.2f}")

        # Additional: Strong trend continuation (pullback entry)
        # Guard with last_signal to prevent firing every tick while conditions persist
        elif ema_fast > ema_slow and prev["ema_fast"] > prev["ema_slow"]:
            # Already in uptrend — check for pullback entry
            if rsi < 40 and rsi > self.rsi_oversold and self.last_signal != "BUY":
                signal = "BUY"
                logger.info(f"BUY signal (pullback) | RSI dipped to {rsi:.2f} in uptrend | ATR: {atr:.2f}")

        elif ema_fast < ema_slow and prev["ema_fast"] < prev["ema_slow"]:
            # Already in downtrend — check for pullback entry
            if rsi > 60 and rsi < self.rsi_overbought and self.last_signal != "SELL":
                signal = "SELL"
                logger.info(f"SELL signal (pullback) | RSI rose to {rsi:.2f} in downtrend | ATR: {atr:.2f}")

        # Apply higher-timeframe trend filter
        if htf_bias == "BULLISH" and signal == "SELL":
            logger.info("SELL signal suppressed — H4 trend is BULLISH (counter-trend trade blocked).")
            signal = "HOLD"
        elif htf_bias == "BEARISH" and signal == "BUY":
            logger.info("BUY signal suppressed — H4 trend is BEARISH (counter-trend trade blocked).")
            signal = "HOLD"

        self.last_signal = signal
        return signal, atr

    def calculate_sl_tp(self, order_type, entry_price, atr, rr_ratio, spread=0.0):
        """
        Calculate Stop Loss and Take Profit based on ATR.
        SL = 1.5 x ATR from entry (plus spread, which works against the position)
        TP = RR ratio x SL distance from entry
        """
        sl_distance = 1.5 * atr + spread  # spread widens the effective loss distance

        if order_type == "BUY":
            sl = round(entry_price - sl_distance, 2)
            tp = round(entry_price + (sl_distance * rr_ratio), 2)
        elif order_type == "SELL":
            sl = round(entry_price + sl_distance, 2)
            tp = round(entry_price - (sl_distance * rr_ratio), 2)
        else:
            sl = 0.0
            tp = 0.0

        return sl, tp

    def calculate_position_size(self, balance, risk_percent, sl_distance, symbol_info):
        """
        Calculate lot size based on risk percentage and SL distance.
        Formula: Lot Size = (Balance * Risk%) / (SL in price * Contract Size)
        """
        if sl_distance <= 0:
            return symbol_info["volume_min"]

        contract_size = symbol_info["trade_contract_size"]
        risk_amount = balance * (risk_percent / 100.0)
        lot_size = risk_amount / (sl_distance * contract_size)

        # Round to volume step
        volume_step = symbol_info["volume_step"]
        lot_size = max(symbol_info["volume_min"], round(lot_size / volume_step) * volume_step)
        lot_size = min(lot_size, symbol_info["volume_max"])

        return round(lot_size, 2)
