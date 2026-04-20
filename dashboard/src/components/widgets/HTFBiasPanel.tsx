"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { HTFBiasData } from "@/lib/types"
import { ArrowUp, ArrowDown, Minus } from "lucide-react"

interface Props { data: HTFBiasData | null }

const BIAS_CONFIG = {
  BULLISH: { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", icon: ArrowUp, label: "Bullish" },
  BEARISH: { color: "text-rose-400",    bg: "bg-rose-500/10 border-rose-500/20",       icon: ArrowDown, label: "Bearish" },
  NEUTRAL: { color: "text-zinc-400",   bg: "bg-zinc-800 border-zinc-700",             icon: Minus, label: "Neutral" },
}

export function HTFBiasPanel({ data }: Props) {
  if (!data) return <Card className="bg-zinc-900 border-zinc-800 animate-pulse h-44" />

  const cfg = BIAS_CONFIG[data.bias]
  const Icon = cfg.icon

  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          H4 Trend Bias
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${cfg.bg}`}>
          <Icon className={`w-5 h-5 ${cfg.color}`} />
          <span className={`text-lg font-bold ${cfg.color}`}>{cfg.label}</span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="bg-zinc-800/60 rounded-lg p-2">
            <p className="text-zinc-500 uppercase tracking-wide text-[10px]">EMA Fast</p>
            <p className="font-semibold mt-0.5">{data.ema_fast.toFixed(2)}</p>
          </div>
          <div className="bg-zinc-800/60 rounded-lg p-2">
            <p className="text-zinc-500 uppercase tracking-wide text-[10px]">EMA Slow</p>
            <p className="font-semibold mt-0.5">{data.ema_slow.toFixed(2)}</p>
          </div>
          <div className="bg-zinc-800/60 rounded-lg p-2">
            <p className="text-zinc-500 uppercase tracking-wide text-[10px]">Gap</p>
            <p className={`font-semibold mt-0.5 ${data.ema_gap > 0 ? "text-emerald-400" : data.ema_gap < 0 ? "text-rose-400" : "text-zinc-400"}`}>
              {data.ema_gap > 0 ? "+" : ""}{data.ema_gap.toFixed(2)}
            </p>
          </div>
        </div>

        {data.last_updated && (
          <p className="text-[10px] text-zinc-600 text-right">
            Updated {new Date(data.last_updated).toLocaleTimeString()}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
