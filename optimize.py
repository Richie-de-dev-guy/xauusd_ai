"""
EMA Period Optimizer
====================
Grid-searches combinations of fast/slow EMA periods using the backtest
engine and ranks results by Profit Factor.  Run this BEFORE going live
to find the EMA periods with the strongest historical edge on your data.

Usage
-----
    python optimize.py <data.csv>

Output
------
Prints a ranked table of the top 10 EMA combinations and tells you
which values to paste into config.py.

Notes
-----
- Uses the same single-position simulation as backtest.py.
- Combinations with fewer than MIN_TRADES trades are excluded to avoid
  over-fitting to a tiny sample.
- This is an in-sample optimisation — validate the winner out-of-sample
  (hold out the last 20 % of bars) before changing config.py.
"""

import sys
import pandas as pd
from strategy import TradingStrategy
from backtest import load_data, run_backtest, INITIAL_EQUITY
import config

# ---- Grid search ranges ----
FAST_EMA_RANGE = range(5, 21, 2)     # 5, 7, 9, 11, 13, 15, 17, 19
SLOW_EMA_RANGE = range(15, 61, 5)    # 15, 20, 25, 30, 35, 40, 45, 50, 55, 60
MIN_TRADES     = 20                  # Skip combos with fewer trades (too noisy)
MIN_EMA_GAP    = 5                   # fast + gap must be <= slow to ensure separation


def _run_combo(df, fast, slow):
    """Run one EMA combination and return a result dict, or None if skipped."""
    strategy = TradingStrategy(
        fast_ema=fast,
        slow_ema=slow,
        rsi_period=config.RSI_PERIOD,
        rsi_overbought=config.RSI_OVERBOUGHT,
        rsi_oversold=config.RSI_OVERSOLD,
        atr_period=config.ATR_PERIOD,
    )

    try:
        trades, final_equity, max_dd = run_backtest(
            df.copy(), strategy, rr_ratio=config.TAKE_PROFIT_RR
        )
    except Exception as e:
        return None

    if len(trades) < MIN_TRADES:
        return None

    wins         = sum(1 for t in trades if t["result"] == "WIN")
    win_rate     = wins / len(trades) * 100
    gross_profit = sum(t["pnl_pct"] for t in trades if t["result"] == "WIN")
    gross_loss   = abs(sum(t["pnl_pct"] for t in trades if t["result"] == "LOSS"))
    pf           = gross_profit / gross_loss if gross_loss > 0 else 0.0
    net_return   = (final_equity - INITIAL_EQUITY) / INITIAL_EQUITY * 100

    return {
        "fast":          fast,
        "slow":          slow,
        "trades":        len(trades),
        "win_rate":      round(win_rate, 1),
        "profit_factor": round(pf, 2),
        "net_return":    round(net_return, 1),
        "max_dd":        round(max_dd, 1),
    }


def run_grid_search(df):
    """Iterate over all valid (fast, slow) pairs and collect results."""
    combos = [
        (f, s)
        for f in FAST_EMA_RANGE
        for s in SLOW_EMA_RANGE
        if s >= f + MIN_EMA_GAP
    ]

    total   = len(combos)
    results = []

    print(f"Testing {total} EMA combinations...\n")

    for idx, (fast, slow) in enumerate(combos, start=1):
        result = _run_combo(df, fast, slow)
        status = (
            f"PF: {result['profit_factor']:.2f}  WR: {result['win_rate']:.0f}%  "
            f"Trades: {result['trades']}"
            if result else "skipped (too few trades)"
        )
        print(f"  [{idx:>3}/{total}] EMA({fast:>2}/{slow:>2})  {status}")
        if result:
            results.append(result)

    return sorted(results, key=lambda x: x["profit_factor"], reverse=True)


def print_results(results):
    """Print ranked results table."""
    if not results:
        print("\nNo valid combinations found — try a larger dataset.")
        return

    W = 74
    print()
    print("=" * W)
    print("  TOP 10 EMA COMBINATIONS  (ranked by Profit Factor)")
    print("=" * W)
    header = f"  {'Fast':>4}  {'Slow':>4}  {'Trades':>7}  {'Win%':>6}  {'PF':>6}  {'Return%':>8}  {'MaxDD%':>7}"
    print(header)
    print("-" * W)

    for r in results[:10]:
        print(
            f"  {r['fast']:>4}  {r['slow']:>4}  {r['trades']:>7}  "
            f"{r['win_rate']:>5}%  {r['profit_factor']:>6}  "
            f"{r['net_return']:>+7.1f}%  {r['max_dd']:>6.1f}%"
        )

    print("=" * W)

    best = results[0]
    current_pf = next(
        (r["profit_factor"] for r in results
         if r["fast"] == config.FAST_EMA_PERIOD and r["slow"] == config.SLOW_EMA_PERIOD),
        None
    )

    print(f"\n  Best combination : EMA({best['fast']}/{best['slow']})")
    print(f"  Profit Factor    : {best['profit_factor']}  |  Win Rate: {best['win_rate']}%  |  Net Return: {best['net_return']:+.1f}%")

    if current_pf is not None:
        print(f"\n  Current config EMA({config.FAST_EMA_PERIOD}/{config.SLOW_EMA_PERIOD}) scores PF: {current_pf}")

    print(f"\n  To apply: set in config.py →  FAST_EMA_PERIOD = {best['fast']}  |  SLOW_EMA_PERIOD = {best['slow']}")
    print()
    print("  NOTE: Validate on a held-out period (last 20% of data) before going live.")


# ---------------------------------------------------------------------------
# Out-of-sample split helper
# ---------------------------------------------------------------------------

def split_data(df, train_ratio=0.8):
    """Return (train_df, test_df) split by row count."""
    split = int(len(df) * train_ratio)
    return df.iloc[:split].reset_index(drop=True), df.iloc[split:].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    df = load_data(sys.argv[1])
    print(f"Loaded {len(df)} bars  ({df['time'].iloc[0]}  →  {df['time'].iloc[-1]})")

    # Use only the training portion for optimisation
    train_df, test_df = split_data(df, train_ratio=0.8)
    print(f"Train set : {len(train_df)} bars  |  Test (held-out) : {len(test_df)} bars\n")

    results = run_grid_search(train_df)
    print_results(results)

    # Auto-validate the best combo on the held-out test set
    if results:
        best = results[0]
        print(f"\nValidating best combo EMA({best['fast']}/{best['slow']}) on held-out test set...")
        val_strategy = TradingStrategy(
            fast_ema=best["fast"], slow_ema=best["slow"],
            rsi_period=config.RSI_PERIOD,
            rsi_overbought=config.RSI_OVERBOUGHT,
            rsi_oversold=config.RSI_OVERSOLD,
            atr_period=config.ATR_PERIOD,
        )
        val_trades, val_equity, val_dd = run_backtest(
            test_df.copy(), val_strategy, rr_ratio=config.TAKE_PROFIT_RR
        )
        if val_trades:
            val_wins = sum(1 for t in val_trades if t["result"] == "WIN")
            val_pf_profit = sum(t["pnl_pct"] for t in val_trades if t["result"] == "WIN")
            val_pf_loss   = abs(sum(t["pnl_pct"] for t in val_trades if t["result"] == "LOSS"))
            val_pf        = val_pf_profit / val_pf_loss if val_pf_loss > 0 else 0.0
            val_wr        = val_wins / len(val_trades) * 100
            val_ret       = (val_equity - INITIAL_EQUITY) / INITIAL_EQUITY * 100
            print(f"  Out-of-sample  →  Trades: {len(val_trades)}  PF: {val_pf:.2f}  WR: {val_wr:.1f}%  Return: {val_ret:+.1f}%  MaxDD: {val_dd:.1f}%")
            if val_pf >= 1.2:
                print("  ✓  Holds up out-of-sample — safe to update config.py.")
            else:
                print("  ⚠  Degrades out-of-sample — the optimised params may be overfit.")
        else:
            print("  No trades on test set — dataset may be too short.")
