"use client"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { BotStatusData } from "@/lib/types"
import { api } from "@/lib/api"
import { Power, Play, Wifi, WifiOff, AlertCircle } from "lucide-react"

interface Props {
  data: BotStatusData | null
  onUpdate: () => void
}

const STATUS_COLOR: Record<string, string> = {
  RUNNING:          "text-emerald-400",
  HALTED:           "text-rose-400",
  PAUSED_DRAWDOWN:  "text-amber-400",
  PAUSED_NEWS:      "text-amber-400",
  PAUSED_SESSION:   "text-zinc-400",
  DISCONNECTED:     "text-zinc-500",
  INITIALIZING:     "text-blue-400",
}

export function KillSwitch({ data, onUpdate }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleHalt() {
    if (!confirm("Close all open positions and halt the bot?")) return
    setLoading(true)
    setError(null)
    try {
      await api.haltBot(true)
      onUpdate()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to halt")
    } finally {
      setLoading(false)
    }
  }

  async function handleResume() {
    setLoading(true)
    setError(null)
    try {
      await api.resumeBot()
      onUpdate()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resume")
    } finally {
      setLoading(false)
    }
  }

  if (!data) return <Card className="bg-zinc-900 border-zinc-800 animate-pulse h-44" />

  const isHalted = data.is_halted
  const statusColor = STATUS_COLOR[data.status] ?? "text-zinc-400"

  return (
    <Card className={`border text-white ${isHalted ? "bg-rose-950/30 border-rose-800/40" : "bg-zinc-900 border-zinc-800"}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          Bot Control
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {data.mt5_connected
              ? <Wifi className="w-4 h-4 text-emerald-400" />
              : <WifiOff className="w-4 h-4 text-zinc-500" />
            }
            <span className={`font-bold text-sm ${statusColor}`}>{data.status.replace("_", " ")}</span>
          </div>
          {data.last_cycle_at && (
            <span className="text-[10px] text-zinc-600">
              {new Date(data.last_cycle_at).toLocaleTimeString()}
            </span>
          )}
        </div>

        {data.halt_reason && (
          <p className="text-xs text-rose-400 bg-rose-950/40 rounded px-2 py-1">
            {data.halt_reason}
          </p>
        )}

        {data.last_cycle_error && (
          <p className="text-xs text-amber-400 bg-amber-950/40 rounded px-2 py-1 flex gap-1 items-start">
            <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
            {data.last_cycle_error}
          </p>
        )}

        {error && <p className="text-xs text-rose-400">{error}</p>}

        <div className="flex gap-2">
          {!isHalted ? (
            <Button
              variant="destructive"
              size="sm"
              className="flex-1 gap-2"
              onClick={handleHalt}
              disabled={loading}
            >
              <Power className="w-4 h-4" />
              Emergency Stop
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-2 border-emerald-700 text-emerald-400 hover:bg-emerald-950"
              onClick={handleResume}
              disabled={loading}
            >
              <Play className="w-4 h-4" />
              Resume Bot
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
