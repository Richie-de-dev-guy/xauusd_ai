"use client"
import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { NewsEventData } from "@/lib/types"
import { AlertTriangle, Clock, ShieldCheck } from "lucide-react"

interface Props { data: NewsEventData | null }

function formatCountdown(secs: number): string {
  if (secs <= 0) return "NOW"
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s.toString().padStart(2, "0")}s`
  return `${s}s`
}

export function NewsCountdown({ data }: Props) {
  const [countdown, setCountdown] = useState(data?.countdown_seconds ?? null)

  useEffect(() => {
    setCountdown(data?.countdown_seconds ?? null)
  }, [data?.countdown_seconds])

  useEffect(() => {
    if (countdown === null || countdown <= 0) return
    const id = setInterval(() => setCountdown((c) => (c !== null && c > 0 ? c - 1 : c)), 1000)
    return () => clearInterval(id)
  }, [countdown])

  if (!data) return <Card className="bg-zinc-900 border-zinc-800 animate-pulse h-44" />

  const isBlackout = data.is_blackout_active
  const hasEvent = !!data.title

  return (
    <Card className={`border text-white ${isBlackout ? "bg-rose-950/40 border-rose-700/40" : "bg-zinc-900 border-zinc-800"}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Clock className="w-3.5 h-3.5" />
          News Filter
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isBlackout ? (
          <div className="flex items-center gap-2 text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-semibold">Blackout Active</span>
          </div>
        ) : hasEvent ? (
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">Upcoming Event</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
            <span className="font-semibold">All Clear</span>
          </div>
        )}

        {hasEvent && (
          <>
            <div>
              <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Event</p>
              <p className="font-semibold text-sm mt-0.5">{data.title}</p>
            </div>

            {data.scheduled_utc && (
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Scheduled</p>
                <p className="text-sm mt-0.5">
                  {new Date(data.scheduled_utc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC
                </p>
              </div>
            )}

            {countdown !== null && !isBlackout && (
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Countdown</p>
                <p className="text-xl font-bold tabular-nums text-amber-400 mt-0.5">
                  {formatCountdown(countdown)}
                </p>
              </div>
            )}

            {isBlackout && data.resumes_at && (
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Resumes at</p>
                <p className="text-sm mt-0.5">
                  {new Date(data.resumes_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC
                </p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
