"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronLeft, Download, TrendingUp, TrendingDown } from "lucide-react"

interface Trade {
  id: number
  ticket: number
  symbol: string
  direction: string
  signal_type: string | null
  h4_bias: string | null
  session: string | null
  news_active: boolean
  entry_price: number
  sl: number
  tp: number
  exit_price: number | null
  volume: number
  atr_at_entry: number | null
  open_time: string
  close_time: string | null
  outcome: string | null
  pnl_usd: number | null
  r_multiple: number | null
  close_reason: string | null
}

export default function TradesPage() {
  const router = useRouter()
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [filterDays, setFilterDays] = useState(30)
  const [filterOutcome, setFilterOutcome] = useState<string | null>(null)

  useEffect(() => {
    async function loadTrades() {
      const token = localStorage.getItem("sentinel_token")
      if (!token) { router.push("/login"); return }

      try {
        const params = new URLSearchParams({
          days: filterDays.toString(),
        })
        if (filterOutcome) params.append("outcome", filterOutcome)

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/trades?${params}`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        if (response.status === 401) { router.push("/login"); return }
        const data = await response.json()
        setTrades(data)
      } finally {
        setLoading(false)
      }
    }
    loadTrades()
  }, [router, filterDays, filterOutcome])

  function formatDate(date: string) {
    return new Date(date).toLocaleString()
  }

  function formatDuration(open: string, close: string | null) {
    if (!close) return "—"
    const ms = new Date(close).getTime() - new Date(open).getTime()
    const h = Math.floor(ms / 3600000)
    const m = Math.floor((ms % 3600000) / 60000)
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
  }

  const stats = {
    total: trades.length,
    wins: trades.filter(t => t.outcome === "WIN").length,
    losses: trades.filter(t => t.outcome === "LOSS").length,
    totalPnl: trades.reduce((sum, t) => sum + (t.pnl_usd || 0), 0),
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
        <button
          onClick={() => router.push("/")}
          className="text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Back to dashboard"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-bold text-lg tracking-tight">Trade History</span>
      </header>

      <main className="p-4 md:p-6 max-w-6xl mx-auto space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Trades", value: stats.total, color: "text-zinc-400" },
            { label: "Wins", value: stats.wins, color: "text-emerald-400" },
            { label: "Losses", value: stats.losses, color: "text-rose-400" },
            { label: "Total P&L", value: `$${stats.totalPnl.toFixed(2)}`, color: stats.totalPnl >= 0 ? "text-emerald-400" : "text-rose-400" },
          ].map(({ label, value, color }) => (
            <Card key={label} className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-4 text-center">
                <p className={`text-xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-zinc-500 uppercase tracking-wide mt-1">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">Period</label>
                <select
                  value={filterDays}
                  onChange={(e) => setFilterDays(Number(e.target.value))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-500"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                  <option value={365}>Last year</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">Result</label>
                <select
                  value={filterOutcome || ""}
                  onChange={(e) => setFilterOutcome(e.target.value || null)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-500"
                >
                  <option value="">All Results</option>
                  <option value="WIN">Wins Only</option>
                  <option value="LOSS">Losses Only</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button variant="outline" className="w-full border-zinc-700 text-zinc-300 hover:bg-zinc-800 gap-2">
                  <Download className="w-4 h-4" />
                  Export CSV
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trades Table */}
        {loading ? (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="p-8 text-center text-zinc-500">Loading trades...</CardContent>
          </Card>
        ) : trades.length === 0 ? (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="p-8 text-center text-zinc-500">No trades found for this period</CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Ticket</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Type</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Entry</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Exit</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Result</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">P&L</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">R</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Duration</th>
                  <th className="text-left py-3 px-4 font-semibold text-zinc-400 uppercase tracking-wide">Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors">
                    <td className="py-3 px-4 font-mono text-xs">{trade.ticket}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1">
                        {trade.direction === "BUY" ? (
                          <TrendingUp className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <TrendingDown className="w-3 h-3 text-rose-400" />
                        )}
                        <span className={trade.direction === "BUY" ? "text-emerald-400" : "text-rose-400"}>
                          {trade.direction}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-xs">
                        <div className="font-semibold">${trade.entry_price.toFixed(2)}</div>
                        <div className="text-zinc-500">{formatDate(trade.open_time)}</div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {trade.exit_price ? (
                        <div>
                          <div className="font-semibold">${trade.exit_price.toFixed(2)}</div>
                          <div className="text-zinc-500">{trade.close_time ? formatDate(trade.close_time) : "—"}</div>
                        </div>
                      ) : (
                        <span className="text-zinc-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {trade.outcome && (
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            trade.outcome === "WIN"
                              ? "border-emerald-700 text-emerald-400"
                              : "border-rose-700 text-rose-400"
                          }`}
                        >
                          {trade.outcome}
                        </Badge>
                      )}
                    </td>
                    <td className={`py-3 px-4 font-semibold ${
                      trade.pnl_usd !== null && trade.pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}>
                      {trade.pnl_usd !== null ? `$${trade.pnl_usd.toFixed(2)}` : "—"}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {trade.r_multiple !== null && (
                        <span className={trade.r_multiple >= 0 ? "text-emerald-400" : "text-rose-400"}>
                          {trade.r_multiple > 0 ? "+" : ""}{trade.r_multiple.toFixed(2)}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs text-zinc-400">
                      {formatDuration(trade.open_time, trade.close_time)}
                    </td>
                    <td className="py-3 px-4 text-xs text-zinc-500">{trade.close_reason || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
