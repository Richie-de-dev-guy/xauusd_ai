"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronLeft } from "lucide-react"

interface AnalyticsData {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  monthly_data: Array<{ month: string; trades: number; pnl: number }>
  session_stats: Record<string, { wins: number; losses: number; pnl: number }>
}

export default function AnalyticsPage() {
  const router = useRouter()
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState(30)

  useEffect(() => {
    async function loadAnalytics() {
      const token = localStorage.getItem("sentinel_token")
      if (!token) { router.push("/login"); return }

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/trades/analytics?days=${period}`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        if (response.status === 401) { router.push("/login"); return }
        const data = await response.json()
        setAnalytics(data)
      } finally {
        setLoading(false)
      }
    }
    loadAnalytics()
  }, [router, period])

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-bold text-lg tracking-tight">Performance Analytics</span>
        </header>
        <div className="p-6 text-center text-zinc-500">Loading analytics...</div>
      </div>
    )
  }

  if (!analytics || analytics.total_trades === 0) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-bold text-lg tracking-tight">Performance Analytics</span>
        </header>
        <div className="p-6 text-center text-zinc-500">No trades data available for this period</div>
      </div>
    )
  }

  const sessions = Object.entries(analytics.session_stats).map(([name, stats]) => ({
    name,
    wins: stats.wins,
    losses: stats.losses,
    total: stats.wins + stats.losses,
    winRate: (stats.wins / (stats.wins + stats.losses) * 100).toFixed(1),
    pnl: stats.pnl,
  }))

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-bold text-lg tracking-tight">Performance Analytics</span>
        <div className="ml-auto">
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-zinc-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </header>

      <main className="p-4 md:p-6 max-w-6xl mx-auto space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              label: "Total Trades",
              value: analytics.total_trades,
              subtitle: `${analytics.winning_trades} wins / ${analytics.losing_trades} losses`,
              color: "text-zinc-400",
            },
            {
              label: "Win Rate",
              value: `${analytics.win_rate.toFixed(1)}%`,
              subtitle: `${analytics.winning_trades}/${analytics.total_trades} profitable`,
              color: analytics.win_rate >= 50 ? "text-emerald-400" : "text-rose-400",
            },
            {
              label: "Total P&L",
              value: `$${analytics.total_pnl.toFixed(2)}`,
              subtitle: analytics.total_pnl >= 0 ? "Profitable" : "Loss",
              color: analytics.total_pnl >= 0 ? "text-emerald-400" : "text-rose-400",
            },
            {
              label: "Profit Factor",
              value: analytics.profit_factor.toFixed(2),
              subtitle: `${analytics.avg_win.toFixed(2)} avg win / ${analytics.avg_loss.toFixed(2)} avg loss`,
              color: analytics.profit_factor > 1 ? "text-emerald-400" : "text-rose-400",
            },
          ].map(({ label, value, subtitle, color }) => (
            <Card key={label} className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-4">
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-zinc-500 uppercase tracking-wide mt-1">{label}</p>
                <p className="text-[11px] text-zinc-600 mt-1">{subtitle}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Monthly Performance */}
        {analytics.monthly_data.length > 0 && (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Monthly Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {analytics.monthly_data.map((month) => (
                  <div key={month.month} className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-semibold">{month.month}</span>
                      <span className={`text-sm font-bold ${month.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        ${month.pnl.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full ${month.pnl >= 0 ? "bg-emerald-500" : "bg-rose-500"}`}
                          style={{ width: `${Math.min(100, Math.abs(month.pnl) / 50)}%` }}
                        />
                      </div>
                      <span className="text-xs text-zinc-500 w-12 text-right">{month.trades} trades</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Session Performance */}
        {sessions.length > 0 && (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Trading Session Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sessions.map((session) => (
                  <div key={session.name} className="bg-zinc-800/50 rounded-lg p-4 space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold text-sm">{session.name}</p>
                        <p className="text-xs text-zinc-500">{session.total} trades</p>
                      </div>
                      <p className={`text-lg font-bold ${session.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        ${session.pnl.toFixed(2)}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-500 w-16">Win Rate</span>
                        <div className="flex-1 bg-zinc-700 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="h-full bg-emerald-500"
                            style={{ width: `${session.winRate}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold w-12 text-right">{session.winRate}%</span>
                      </div>
                      <div className="text-xs text-zinc-500">
                        <span className="text-emerald-400">{session.wins}W</span>
                        <span className="mx-2">•</span>
                        <span className="text-rose-400">{session.losses}L</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Averages */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Trade Averages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-1">
                <p className="text-xs text-zinc-500 uppercase tracking-wide">Average Win</p>
                <p className="text-2xl font-bold text-emerald-400">${analytics.avg_win.toFixed(2)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-zinc-500 uppercase tracking-wide">Average Loss</p>
                <p className="text-2xl font-bold text-rose-400">${analytics.avg_loss.toFixed(2)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-zinc-500 uppercase tracking-wide">Profit Factor</p>
                <p className={`text-2xl font-bold ${analytics.profit_factor > 1 ? "text-emerald-400" : "text-rose-400"}`}>
                  {analytics.profit_factor.toFixed(2)}
                </p>
                <p className="text-xs text-zinc-600 mt-1">
                  {analytics.profit_factor > 1 ? "Profitable system" : "Below break-even"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
