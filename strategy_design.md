# XAUUSD Trading Bot Strategy Design

## 1. Strategy Overview

This trading strategy for XAUUSD (Gold vs. US Dollar) will primarily focus on a **trend-following approach combined with key support and resistance levels**. The Dollar Index (DXY) will be used as a **confluence factor** to confirm potential trade directions. The bot will operate on a medium-term timeframe (e.g., 1-hour or 4-hour charts for trend identification, with finer timeframes for entry/exit) to avoid the high-frequency demands and risks of scalping, while still capturing significant moves.

## 2. Core Components

### 2.1 Trend Identification

*   **Moving Averages (MAs):** We will use a combination of Exponential Moving Averages (EMAs) to identify the prevailing trend. For instance, a faster EMA (e.g., 20-period) crossing a slower EMA (e.g., 50-period or 100-period) can signal a trend change or continuation. The relative position of price to these MAs will also indicate trend strength.
*   **Price Action:** Observing higher highs and higher lows for an uptrend, and lower highs and lower lows for a downtrend, will reinforce MA signals.

### 2.2 Support and Resistance (S&R) Levels

*   **Key Levels:** The bot will identify significant historical support and resistance levels on higher timeframes (e.g., daily, weekly) as potential areas for price reversal or continuation after a breakout.
*   **Dynamic S&R:** Moving Averages can also act as dynamic support and resistance. Price bouncing off or breaking through these MAs will be considered.

### 2.3 Confluence Factor: Dollar Index (DXY)

*   **Inverse Correlation:** XAUUSD often has an inverse correlation with the US Dollar Index (DXY). A strong DXY downtrend can support an XAUUSD uptrend, and vice-versa.
*   **Confirmation:** DXY will be used as a confirming indicator. For example, if XAUUSD shows an uptrend signal, a simultaneous downtrend or weakness in DXY would strengthen the XAUUSD long signal.

### 2.4 Entry Triggers

*   **Trend Following Entries:**
    *   **Buy Signal:** Price is above the EMAs, faster EMA is above slower EMA, and price pulls back to test an EMA or a key support level and shows rejection (e.g., candlestick patterns like hammer, bullish engulfing).
    *   **Sell Signal:** Price is below the EMAs, faster EMA is below slower EMA, and price pulls back to test an EMA or a key resistance level and shows rejection (e.g., shooting star, bearish engulfing).
*   **Breakout Entries:**
    *   **Buy Signal:** Price breaks above a significant resistance level with strong momentum, especially if confirmed by DXY weakness.
    *   **Sell Signal:** Price breaks below a significant support level with strong momentum, especially if confirmed by DXY strength.

### 2.5 Exit Strategy

*   **Take Profit (TP):** Set at the next significant resistance level for long positions or support level for short positions, or based on a fixed risk-to-reward ratio (e.g., 1:2 or 1:3).
*   **Stop Loss (SL):** Placed strategically below the recent swing low for long positions or above the recent swing high for short positions, or below/above the broken S&R level. This will be a hard stop loss.
*   **Trailing Stop Loss:** Optionally, a trailing stop loss can be implemented to protect profits as the trade moves in a favorable direction.

## 3. Risk Management

*   **Position Sizing:** Position size will be calculated based on a fixed percentage of the account balance per trade (e.g., 1-2%). This will be dynamically adjusted based on the stop loss distance to ensure consistent risk per trade.
    *   `Position Size = (Account Balance * Risk Percentage) / (Stop Loss in Pips * Pip Value)`
*   **Maximum Drawdown:** The bot will have a maximum daily/weekly drawdown limit. If reached, trading will be paused.
*   **Maximum Open Trades:** Limit the number of concurrent open trades to manage overall exposure.

## 4. Trade Logging

All trades (entry, exit, profit/loss, reason for trade, risk metrics) will be logged to a file for performance analysis and auditing.

## 5. Configurability

Key parameters such as EMA periods, risk percentage, maximum drawdown, and maximum open trades will be configurable via a separate configuration file.
