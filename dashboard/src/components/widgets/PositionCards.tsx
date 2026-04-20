"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { PositionData } from "@/lib/types"
import { TrendingUp, TrendingDown } from "lucide-react"

interface Props { positions: PositionData[] }

function formatDuration(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function PositionCard({ pos }: { pos: PositionData }) {
  const isBuy = pos.direction === "BUY"
  const pnlColor = pos.floating_pnl >= 0 ? "text-emerald-400" : "text-rose-400"
  const dirColor = isBuy ? "border-emerald-700 text-emerald-400" : "border-rose-700 text-rose-400"

  return (
    <Card className="bg-zinc-800/50 border-zinc-700 text-white">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isBuy
              ? <TrendingUp className="w-4 h-4 text-emerald-400" />
              : <TrendingDown className="w-4 h-4 text-rose-400" />
            }
            <span className="font-semibold text-sm">{pos.symbol}</span>
            <Badge variant="outline" className={`text-[10px] ${dirColor}`}>{pos.direction}</Badge>
          </div>
          <span className={`font-bold text-sm ${pnlColor}`}>
            {pos.floating_pnl >= 0 ? "+" : ""}${pos.floating_pnl.toFixed(2)}
          </span>
        </div>

        {/* TP progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-zinc-500">
            <span>TP Progress</span>
            <span>{pos.tp_progress_pct.toFixed(1)}%</span>
          </div>
          <div className="h-1.5 bg-zinc-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${isBuy ? "bg-emerald-500" : "bg-rose-500"}`}
              style={{ width: `${Math.min(100, pos.tp_progress_pct)}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="bg-zinc-900/50 rounded p-1.5">
            <p className="text-zinc-500 text-[10px]">Entry</p>
            <p className="font-medium">{pos.open_price.toFixed(2)}</p>
          </div>
          <div className="bg-zinc-900/50 rounded p-1.5">
            <p className="text-zinc-500 text-[10px]">SL</p>
            <p className="font-medium text-rose-400">{pos.sl.toFixed(2)}</p>
          </div>
          <div className="bg-zinc-900/50 rounded p-1.5">
            <p className="text-zinc-500 text-[10px]">TP</p>
            <p className="font-medium text-emerald-400">{pos.tp.toFixed(2)}</p>
          </div>
        </div>

        <div className="flex justify-between text-[10px] text-zinc-500">
          <span>{pos.volume} lot{pos.volume !== 1 ? "s" : ""}</span>
          <span className={pos.r_multiple >= 0 ? "text-emerald-400" : "text-rose-400"}>
            {pos.r_multiple >= 0 ? "+" : ""}{pos.r_multiple.toFixed(2)}R
          </span>
          <span>{formatDuration(pos.hold_duration_seconds)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export function PositionCards({ positions }: Props) {
  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider flex justify-between items-center">
          <span>Open Positions</span>
          <span className="text-zinc-600 text-xs font-normal">{positions.length} {positions.length === 1 ? "position" : "positions"}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className={`space-y-3 ${positions.length > 4 ? "max-h-[600px] overflow-y-auto pr-2" : ""}`}>
        {positions.length === 0 ? (
          <p className="text-zinc-600 text-sm text-center py-8">No open positions</p>
        ) : (
          positions.map((p) => <PositionCard key={p.ticket} pos={p} />)
        )}
      </CardContent>
    </Card>
  )
}
