"""
XAUUSD Strategy Backtester
===========================
Simulates the EMA+RSI+ATR strategy over historical OHLCV data and
reports win rate, profit factor, net return, and max drawdown.

Usage
-----
    python backtest.py <data.csv>

How to export XAUUSD data from MT5
-----------------------------------
1. In MT5: File > Open Data Folder > history > <server_name>
   Copy the relevant .hst file and convert with MT5 Script, OR:
2. In MT5 terminal, open the "Strategy Tester" panel, run a simple
   EA on XAUUSD H1 and export the ticks/bars from the Data tab, OR:
3. Easiest: paste the script below into MT5's MetaEditor and run it:

   // MQL5 export script
   // Exports OHLCV to <MT5 Data Folder>\\MQL5\\Files\\xauusd_h1.csv
   #property script_show_inputs
   input int Bars = 5000;
   void OnStart() {
       int fh = FileOpen("xauusd_h1.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
       FileWrite(fh, "time,open,high,low,close,tick_volume");
       MqlRates rates[];
       int copied = CopyRates("XAUUSDm", PERIOD_H1, 0, Bars, rates);
       for (int i = copied-1; i >= 0; i--)
           FileWrite(fh, TimeToString(rates[i].time), rates[i].open,
                     rates[i].high, rates[i].low, rates[i].close, rates[i].tick_volume);
       FileClose(fh);
       Print("Exported ", copied, " bars.");
   }

Expected CSV columns: time, open, high, low, close  (tick_volume optional)
"""

import sys
import pandas as pd
from strategy import TradingStrategy
import config

INITIAL_EQUITY = 10_000.0   # Simulated starting balance in USD
FIXED_SPREAD   = 3.0        # Approximate XAUUSD spread in price units ($3 typical on Exness ECN)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(filepath: str) -> pd.DataFrame:
    """Load and normalise a CSV into a standard OHLCV DataFrame."""
    df = pd.read_csv(filepath)
    df.columns = [c.lower().strip() for c in df.columns]

    # Accept 'date' as an alias for 'time'
    if "date" in df.columns and "time" not in df.columns:
        df.rename(columns={"date": "time"}, inplace=True)

    if "time" not in df.columns:
        raise ValueError("CSV must contain a 'time' (or 'date') column.")

    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"CSV is missing required column: '{col}'")

    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def run_backtest(
    df: pd.DataFrame,
    strategy: TradingStrategy,
    rr_ratio: float = 2.0,
    risk_pct: float = 1.0,
    spread: float = FIXED_SPREAD,
) -> tuple[list, float, float]:
    """
    Simulate strategy trades over the full dataset.

    Rules
    -----
    - One position at a time (single-position model, cleanest for validation).
    - Signal generated on bar N close → entry at bar N+1 open.
    - Each bar checks whether SL or TP was breached (uses high/low).
    - If both SL and TP are touched on the same bar, worst-case is assumed (SL hit).
    - Pullback entries are gated by last_signal to match live bot behaviour.

    Returns
    -------
    trades        : list of trade dicts
    final_equity  : float
    max_drawdown  : float (percent)
    """
    df = strategy.add_indicators(df.copy())
    min_bars = strategy.slow_ema + 5

    trades = []
    position = None          # dict when a trade is open, else None
    last_signal = "HOLD"
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_drawdown = 0.0

    for i in range(min_bars, len(df) - 1):
        bar  = df.iloc[i]
        prev = df.iloc[i - 1]

        # ---- Update drawdown tracker ----
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity * 100.0
        if dd > max_drawdown:
            max_drawdown = dd

        # ---- Check open position for SL/TP hits ----
        if position is not None:
            hi = bar["high"]
            lo = bar["low"]

            if position["type"] == "BUY":
                sl_hit = lo <= position["sl"]
                tp_hit = hi >= position["tp"]
            else:  # SELL
                sl_hit = hi >= position["sl"]
                tp_hit = lo <= position["tp"]

            if sl_hit:
                pnl = -risk_pct
                equity *= 1 + pnl / 100.0
                trades.append({
                    "type": position["type"], "result": "LOSS",
                    "pnl_pct": pnl, "bars_held": i - position["entry_bar"],
                    "entry": position["entry"], "sl": position["sl"], "tp": position["tp"],
                })
                position = None
                last_signal = "HOLD"
                continue

            if tp_hit:
                pnl = risk_pct * rr_ratio
                equity *= 1 + pnl / 100.0
                trades.append({
                    "type": position["type"], "result": "WIN",
                    "pnl_pct": pnl, "bars_held": i - position["entry_bar"],
                    "entry": position["entry"], "sl": position["sl"], "tp": position["tp"],
                })
                position = None
                last_signal = "HOLD"
                continue

            continue  # still in position, no new entry

        # ---- Generate signal (mirrors strategy.get_signal logic) ----
        atr           = bar["atr"]
        rsi           = bar["rsi"]
        ema_fast      = bar["ema_fast"]
        ema_slow      = bar["ema_slow"]
        ema_cross_up  = bar["ema_cross_up"]
        ema_cross_down = bar["ema_cross_down"]

        if pd.isna(atr) or atr <= 0:
            continue

        signal = "HOLD"

        if ema_cross_up and rsi < config.RSI_OVERBOUGHT:
            signal = "BUY"
        elif ema_cross_down and rsi > config.RSI_OVERSOLD:
            signal = "SELL"
        elif ema_fast > ema_slow and prev["ema_fast"] > prev["ema_slow"]:
            if rsi < 40 and rsi > config.RSI_OVERSOLD and last_signal != "BUY":
                signal = "BUY"
        elif ema_fast < ema_slow and prev["ema_fast"] < prev["ema_slow"]:
            if rsi > 60 and rsi < config.RSI_OVERBOUGHT and last_signal != "SELL":
                signal = "SELL"

        if signal != "HOLD":
            last_signal = signal

        if signal == "HOLD":
            continue

        # ---- Enter at next bar open ----
        next_open = df.iloc[i + 1]["open"]

        if signal == "BUY":
            entry    = next_open + spread
            sl_dist  = 1.5 * atr + spread
            sl       = round(entry - sl_dist, 2)
            tp       = round(entry + sl_dist * rr_ratio, 2)
        else:
            entry    = next_open - spread
            sl_dist  = 1.5 * atr + spread
            sl       = round(entry + sl_dist, 2)
            tp       = round(entry - sl_dist * rr_ratio, 2)

        position = {
            "type": signal, "entry": entry,
            "sl": sl, "tp": tp, "entry_bar": i + 1,
        }

    return trades, equity, max_drawdown


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(trades: list, final_equity: float, max_drawdown: float):
    """Print a formatted performance summary to stdout."""
    if not trades:
        print("\nNo trades were generated — check your data or indicator periods.")
        return

    wins   = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]

    win_rate      = len(wins) / len(trades) * 100
    gross_profit  = sum(t["pnl_pct"] for t in wins)
    gross_loss    = abs(sum(t["pnl_pct"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    net_return    = (final_equity - INITIAL_EQUITY) / INITIAL_EQUITY * 100
    avg_bars_held = sum(t["bars_held"] for t in trades) / len(trades)

    buy_trades  = [t for t in trades if t["type"] == "BUY"]
    sell_trades = [t for t in trades if t["type"] == "SELL"]

    def side_wr(side):
        w = sum(1 for t in side if t["result"] == "WIN")
        return f"{w}/{len(side)} ({w/len(side)*100:.0f}%)" if side else "—"

    print()
    print("=" * 54)
    print("  BACKTEST RESULTS")
    print("=" * 54)
    print(f"  Total Trades      : {len(trades)}")
    print(f"  Winners           : {len(wins)}  ({win_rate:.1f}%)")
    print(f"  Losers            : {len(losses)}  ({100 - win_rate:.1f}%)")
    print(f"  BUY  win/total    : {side_wr(buy_trades)}")
    print(f"  SELL win/total    : {side_wr(sell_trades)}")
    print(f"  Profit Factor     : {profit_factor:.2f}  (>1.3 = viable)")
    print(f"  Net Return        : {net_return:+.1f}%")
    print(f"  Max Drawdown      : {max_drawdown:.1f}%")
    print(f"  Avg Bars Held     : {avg_bars_held:.1f}")
    print(f"  Final Equity      : ${final_equity:,.2f}  (started ${INITIAL_EQUITY:,.0f})")
    print("=" * 54)

    if profit_factor < 1.0:
        print("\n  ⚠  Profit factor below 1.0 — strategy loses money on this data.")
    elif profit_factor < 1.3:
        print("\n  ⚠  Marginal edge. Consider optimizing parameters (run optimize.py).")
    else:
        print("\n  ✓  Profit factor above 1.3 — strategy shows positive expectancy.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"Loading: {filepath}")

    df = load_data(filepath)
    print(f"Bars loaded : {len(df)}")
    print(f"Date range  : {df['time'].iloc[0]}  →  {df['time'].iloc[-1]}")

    strategy = TradingStrategy(
        fast_ema=config.FAST_EMA_PERIOD,
        slow_ema=config.SLOW_EMA_PERIOD,
        rsi_period=config.RSI_PERIOD,
        rsi_overbought=config.RSI_OVERBOUGHT,
        rsi_oversold=config.RSI_OVERSOLD,
        atr_period=config.ATR_PERIOD,
    )

    print("\nRunning simulation (this may take a moment for large datasets)...")
    trades, final_equity, max_dd = run_backtest(
        df, strategy, rr_ratio=config.TAKE_PROFIT_RR
    )
    print_report(trades, final_equity, max_dd)
