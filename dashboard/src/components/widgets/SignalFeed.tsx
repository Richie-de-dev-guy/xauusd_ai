"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { SignalData } from "@/lib/types"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface Props { data: SignalData | null }

const SIGNAL_STYLES = {
  BUY:  { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: TrendingUp },
  SELL: { color: "bg-rose-500/15 text-rose-400 border-rose-500/30", icon: TrendingDown },
  HOLD: { color: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30", icon: Minus },
}

function fmt(n: number, d = 2) { return n.toFixed(d) }

export function SignalFeed({ data }: Props) {
  if (!data) return <Card className="bg-zinc-900 border-zinc-800 animate-pulse h-56" />

  const style = SIGNAL_STYLES[data.signal]
  const Icon = style.icon

  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          Live Signal
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-1.5 text-2xl font-bold px-3 py-1 rounded-lg border ${style.color}`}>
            <Icon className="w-5 h-5" />
            {data.signal}
          </span>
          {data.signal_type && (
            <span className="text-xs text-zinc-500 italic">{data.signal_type}</span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3 text-center">
          {[
            { label: "EMA Fast", value: fmt(data.ema_fast) },
            { label: "EMA Slow", value: fmt(data.ema_slow) },
            { label: "EMA Gap",  value: fmt(data.ema_gap) },
            { label: "RSI",      value: fmt(data.rsi) },
            { label: "ATR",      value: fmt(data.atr) },
            { label: "Updated",  value: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "—" },
          ].map(({ label, value }) => (
            <div key={label} className="bg-zinc-800/60 rounded-lg p-2">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</p>
              <p className="text-sm font-semibold mt-0.5">{value}</p>
            </div>
          ))}
        </div>

        {data.history.length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wider">Recent signals</p>
            <div className="flex gap-1.5 flex-wrap">
              {data.history.slice(0, 8).map((h, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className={`text-[10px] ${
                    h.signal === "BUY"  ? "border-emerald-700 text-emerald-400" :
                    h.signal === "SELL" ? "border-rose-700 text-rose-400" :
                    "border-zinc-700 text-zinc-500"
                  }`}
                >
                  {h.signal}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
