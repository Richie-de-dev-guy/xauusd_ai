"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { AccountData } from "@/lib/types"

interface Props { data: AccountData | null }

export function DrawdownGauge({ data }: Props) {
  if (!data) return <Card className="bg-zinc-900 border-zinc-800 animate-pulse h-52" />

  const pct = Math.min(100, Math.max(0, data.daily_drawdown_pct))
  const maxPct = 5 // MAX_DAILY_DRAWDOWN_PERCENT
  const fillPct = (pct / maxPct) * 100

  const color =
    pct >= maxPct * 0.9 ? "bg-rose-500" :
    pct >= maxPct * 0.6 ? "bg-amber-500" :
    "bg-emerald-500"

  const textColor =
    pct >= maxPct * 0.9 ? "text-rose-400" :
    pct >= maxPct * 0.6 ? "text-amber-400" :
    "text-emerald-400"

  const floatingPnl = data.equity - data.balance

  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          Daily Drawdown
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Used</p>
            <p className={`text-2xl font-bold ${textColor}`}>{pct.toFixed(2)}%</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Limit</p>
            <p className="text-sm font-semibold text-zinc-400">{maxPct}%</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${color}`}
            style={{ width: `${Math.min(100, fillPct)}%` }}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-zinc-800/60 rounded-lg p-2.5">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Balance</p>
            <p className="font-semibold text-sm mt-0.5">${data.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
          </div>
          <div className="bg-zinc-800/60 rounded-lg p-2.5">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Equity</p>
            <p className="font-semibold text-sm mt-0.5">${data.equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
          </div>
          <div className="bg-zinc-800/60 rounded-lg p-2.5">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Floating P&L</p>
            <p className={`font-semibold text-sm mt-0.5 ${floatingPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {floatingPnl >= 0 ? "+" : ""}${floatingPnl.toFixed(2)}
            </p>
          </div>
          <div className="bg-zinc-800/60 rounded-lg p-2.5">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Max Risk</p>
            <p className="font-semibold text-sm mt-0.5 text-rose-400">${data.max_daily_risk_usd.toFixed(2)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
