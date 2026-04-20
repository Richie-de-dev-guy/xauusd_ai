export interface SignalData {
  signal: "BUY" | "SELL" | "HOLD"
  signal_type: string | null
  ema_fast: number
  ema_slow: number
  ema_gap: number
  rsi: number
  atr: number
  htf_bias: "BULLISH" | "BEARISH" | "NEUTRAL"
  timestamp: string | null
  history: SignalHistoryItem[]
}

export interface SignalHistoryItem {
  signal: "BUY" | "SELL" | "HOLD"
  signal_type: string | null
  timestamp: string
}

export interface HTFBiasData {
  bias: "BULLISH" | "BEARISH" | "NEUTRAL"
  ema_fast: number
  ema_slow: number
  ema_gap: number
  last_updated: string | null
}

export interface NewsEventData {
  title: string | null
  scheduled_utc: string | null
  countdown_seconds: number | null
  impact: string
  currency: string
  is_blackout_active: boolean
  resumes_at: string | null
}

export interface PositionData {
  ticket: number
  symbol: string
  direction: "BUY" | "SELL"
  volume: number
  open_price: number
  current_price: number
  sl: number
  tp: number
  floating_pnl: number
  r_multiple: number
  sl_distance: number
  atr_at_entry: number
  tp_progress_pct: number
  hold_duration_seconds: number
  signal_type: string | null
  open_time: string
}

export interface AccountData {
  balance: number
  equity: number
  margin: number
  free_margin: number
  leverage: number
  daily_start_balance: number
  daily_drawdown_pct: number
  max_daily_risk_usd: number
}

export interface BotStatusData {
  status: string
  mt5_connected: boolean
  is_halted: boolean
  halt_reason: string | null
  last_cycle_at: string | null
  last_cycle_error: string | null
}

export interface EquityPoint {
  timestamp: string
  balance: number
  equity: number
  daily_drawdown_pct: number
}

export interface LotCalcData {
  balance: number
  risk_pct: number
  risk_amount: number
  atr: number
  spread: number
  sl_distance: number
  contract_size: number
  calculated_lot: number
  rounded_lot: number
}

export interface WSMessage {
  type: "price_update" | "signal_update" | "position_update" | "trade_opened" | "trade_closed" | "bot_status"
  data: Record<string, unknown>
  timestamp: string
}
