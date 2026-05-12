"""
Mean Reversion Scalper (M5)
============================
Premise: Gold often overextends during news/momentum spikes and snaps back
to the mean. We catch the snap-back, not the spike.

Entry rules (close-of-bar):
  SELL : RSI was > overbought_extreme (e.g. 80) within the last N bars
         AND current RSI has crossed back BELOW the neutral upper bound (e.g. 70)
  BUY  : RSI was < oversold_extreme (e.g. 20) within the last N bars
         AND current RSI has crossed back ABOVE the neutral lower bound (e.g. 30)

Exit rules:
  SL : fixed pip distance from entry (e.g. 15 pips = $1.50)
  TP : fixed pip distance from entry (e.g. 25 pips = $2.50)
  → fixed-pip is intentional. Mean reversion either works fast or fails fast;
    ATR scaling rewards waiting, which is the opposite of what we want.

Session / spread guards:
  - Trade only during NY-overlap hours (configurable).
  - Skip if current spread exceeds max_spread_pips (live-only check; backtest
    uses a fixed modelled spread).
"""

import pandas as pd
from datetime import datetime, timezone


PIP_SIZE = 0.10  # 1 pip on XAUUSD = $0.10 (i.e. price units of 0.10)


class MeanReversionScalper:
    def __init__(self,
                 rsi_period=9,
                 overbought_extreme=80, oversold_extreme=20,
                 neutral_upper=70, neutral_lower=30,
                 extreme_lookback=5,
                 sl_pips=15, tp_pips=25,
                 session_start_utc=12.5, session_end_utc=17.0,
                 max_spread_pips=6):
        """
        extreme_lookback : how many recent bars (inclusive of current) to scan
                           for the RSI extreme touch
        session_start_utc / session_end_utc : float hours (e.g. 12.5 = 12:30)
        """
        self.rsi_period = rsi_period
        self.overbought_extreme = overbought_extreme
        self.oversold_extreme = oversold_extreme
        self.neutral_upper = neutral_upper
        self.neutral_lower = neutral_lower
        self.extreme_lookback = extreme_lookback
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.session_start_utc = session_start_utc
        self.session_end_utc = session_end_utc
        self.max_spread_pips = max_spread_pips

    # ------------- session check (live use; backtest derives from bar time) -------------
    def is_tradeable_session_now(self):
        now = datetime.now(timezone.utc)
        h = now.hour + now.minute / 60.0
        return self.session_start_utc <= h < self.session_end_utc

    def is_tradeable_session_at(self, ts):
        """Backtest-friendly variant: check session for a given bar timestamp."""
        if pd.isna(ts):
            return False
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        h = ts.hour + ts.minute / 60.0
        return self.session_start_utc <= h < self.session_end_utc

    # ------------- indicators -------------
    @staticmethod
    def _rsi(series, period):
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def add_indicators(self, df):
        df = df.copy()
        df["rsi"] = self._rsi(df["close"], self.rsi_period)
        df["was_overbought"] = df["rsi"] > self.overbought_extreme
        df["was_oversold"]   = df["rsi"] < self.oversold_extreme
        # Track if an extreme occurred in the last `extreme_lookback` bars (current bar included)
        df["recent_overbought"] = df["was_overbought"].rolling(self.extreme_lookback, min_periods=1).max().astype(bool)
        df["recent_oversold"]   = df["was_oversold"].rolling(self.extreme_lookback, min_periods=1).max().astype(bool)
        return df

    # ------------- signal -------------
    def signal_at(self, df, i):
        if i < 1:
            return "HOLD"
        bar = df.iloc[i]
        prev = df.iloc[i - 1]
        if pd.isna(bar["rsi"]) or pd.isna(prev["rsi"]):
            return "HOLD"

        # Session gate (use bar timestamp if present, else fall back to "now")
        if "time" in df.columns:
            if not self.is_tradeable_session_at(bar["time"]):
                return "HOLD"

        # SELL: RSI touched >overbought_extreme recently AND crossed back DOWN below neutral_upper
        crossed_down = prev["rsi"] >= self.neutral_upper and bar["rsi"] < self.neutral_upper
        if bar["recent_overbought"] and crossed_down:
            return "SELL"

        # BUY: RSI touched <oversold_extreme recently AND crossed back UP above neutral_lower
        crossed_up = prev["rsi"] <= self.neutral_lower and bar["rsi"] > self.neutral_lower
        if bar["recent_oversold"] and crossed_up:
            return "BUY"

        return "HOLD"

    # ------------- order math -------------
    def calculate_sl_tp(self, order_type, entry_price, spread=0.0):
        """Fixed-pip SL/TP. Spread widens the effective SL distance."""
        sl_dist = self.sl_pips * PIP_SIZE + spread
        tp_dist = self.tp_pips * PIP_SIZE
        if order_type == "BUY":
            sl = round(entry_price - sl_dist, 2)
            tp = round(entry_price + tp_dist, 2)
        else:
            sl = round(entry_price + sl_dist, 2)
            tp = round(entry_price - tp_dist, 2)
        return sl, tp

    @staticmethod
    def calculate_position_size(balance, risk_percent, sl_distance, symbol_info):
        """Same formula as TradingStrategy.calculate_position_size — risk-% based sizing."""
        if sl_distance <= 0:
            return symbol_info["volume_min"]
        contract_size = symbol_info["trade_contract_size"]
        risk_amount = balance * (risk_percent / 100.0)
        lot_size = risk_amount / (sl_distance * contract_size)
        step = symbol_info["volume_step"]
        lot_size = max(symbol_info["volume_min"], round(lot_size / step) * step)
        lot_size = min(lot_size, symbol_info["volume_max"])
        return round(lot_size, 2)

    def spread_ok(self, bid, ask):
        """Live-only check — skip trade if current spread exceeds configured max."""
        spread_pips = (ask - bid) / PIP_SIZE
        return spread_pips <= self.max_spread_pips
