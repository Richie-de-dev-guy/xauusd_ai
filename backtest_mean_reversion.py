"""
Backtester for the Mean Reversion Scalper.

Models a wider spread (4 pips by default) than the trend backtester because
scalper fills on Gold are typically worse than backtest assumes during the
news/momentum spikes the strategy targets.

Usage:
    python backtest_mean_reversion.py xauusd_m5.csv
"""

import sys
import pandas as pd

import config
from backtest import load_data, INITIAL_EQUITY, print_report
from strategy_mean_reversion import MeanReversionScalper, PIP_SIZE


SCALPER_SPREAD_PIPS = 4.0   # wider than the 3-pip default in backtest.py
SCALPER_SPREAD      = SCALPER_SPREAD_PIPS * PIP_SIZE


def run(df, strategy, risk_pct=1.0, spread=SCALPER_SPREAD):
    df = strategy.add_indicators(df.copy())
    min_bars = strategy.rsi_period + strategy.extreme_lookback + 2

    trades = []
    position = None
    equity = INITIAL_EQUITY
    peak = INITIAL_EQUITY
    max_dd = 0.0

    # Compute the per-trade win/loss in equity-curve terms.
    # SL = sl_pips, TP = tp_pips → RR = tp/sl
    rr = strategy.tp_pips / strategy.sl_pips
    win_pct  = risk_pct * rr
    loss_pct = -risk_pct

    for i in range(min_bars, len(df) - 1):
        bar = df.iloc[i]

        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd: max_dd = dd

        if position is not None:
            hi, lo = bar["high"], bar["low"]
            if position["type"] == "BUY":
                sl_hit = lo <= position["sl"]
                tp_hit = hi >= position["tp"]
            else:
                sl_hit = hi >= position["sl"]
                tp_hit = lo <= position["tp"]

            # Conservative: if both touched in same bar, assume SL hit (worst case)
            if sl_hit:
                equity *= 1 + loss_pct / 100
                trades.append({"type": position["type"], "result": "LOSS",
                               "pnl_pct": loss_pct,
                               "bars_held": i - position["entry_bar"],
                               "entry": position["entry"], "sl": position["sl"], "tp": position["tp"]})
                position = None
                continue
            if tp_hit:
                equity *= 1 + win_pct / 100
                trades.append({"type": position["type"], "result": "WIN",
                               "pnl_pct": win_pct,
                               "bars_held": i - position["entry_bar"],
                               "entry": position["entry"], "sl": position["sl"], "tp": position["tp"]})
                position = None
                continue
            continue  # still in trade

        signal = strategy.signal_at(df, i)
        if signal == "HOLD":
            continue

        next_open = df.iloc[i + 1]["open"]
        entry = next_open + spread if signal == "BUY" else next_open - spread
        sl, tp = strategy.calculate_sl_tp(signal, entry, spread=spread)
        position = {"type": signal, "entry": entry, "sl": sl, "tp": tp, "entry_bar": i + 1}

    return trades, equity, max_dd


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    df = load_data(sys.argv[1])
    print(f"Loaded {len(df)} bars  ({df['time'].iloc[0]}  →  {df['time'].iloc[-1]})\n")

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
    print(f"Strategy: Mean Reversion Scalper  "
          f"(RSI {strategy.rsi_period}, extremes {strategy.oversold_extreme}/{strategy.overbought_extreme} → "
          f"neutral {strategy.neutral_lower}/{strategy.neutral_upper})")
    print(f"SL/TP: {strategy.sl_pips}/{strategy.tp_pips} pips  |  "
          f"Session: {strategy.session_start_utc:.1f}–{strategy.session_end_utc:.1f} UTC  |  "
          f"Spread modelled: {SCALPER_SPREAD_PIPS} pips\n")

    trades, equity, max_dd = run(df, strategy)
    print_report(trades, equity, max_dd)
