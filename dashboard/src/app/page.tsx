"use client"
import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { useWebSocket } from "@/hooks/useWebSocket"
import type {
  SignalData, HTFBiasData, NewsEventData, PositionData,
  AccountData, BotStatusData, LotCalcData, WSMessage,
} from "@/lib/types"

import { SignalFeed }    from "@/components/widgets/SignalFeed"
import { HTFBiasPanel }  from "@/components/widgets/HTFBiasPanel"
import { NewsCountdown } from "@/components/widgets/NewsCountdown"
import { PositionCards } from "@/components/widgets/PositionCards"
import { DrawdownGauge } from "@/components/widgets/DrawdownGauge"
import { KillSwitch }    from "@/components/widgets/KillSwitch"
import { EquityChart }   from "@/components/widgets/EquityChart"
import { LotCalculator } from "@/components/widgets/LotCalculator"
import { Separator }     from "@/components/ui/separator"
import { Skeleton }      from "@/components/ui/skeleton"
import { LogOut, Users, RefreshCw, Settings } from "lucide-react"

export default function DashboardPage() {
  const router = useRouter()

  const [signal,     setSignal]     = useState<SignalData | null>(null)
  const [htf,        setHtf]        = useState<HTFBiasData | null>(null)
  const [news,       setNews]       = useState<NewsEventData | null>(null)
  const [positions,  setPositions]  = useState<PositionData[]>([])
  const [account,    setAccount]    = useState<AccountData | null>(null)
  const [botStatus,  setBotStatus]  = useState<BotStatusData | null>(null)
  const [lotSize,    setLotSize]    = useState<LotCalcData | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [loading,    setLoading]    = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // Initial REST fetch — also called after halt/resume
  const fetchAll = useCallback(async (isRefresh = false) => {
    const token = localStorage.getItem("sentinel_token")
    if (!token) { router.push("/login"); return }

    if (isRefresh) setRefreshing(true)
    else setLoading(true)

    const settle = <T,>(p: Promise<T>): Promise<T | null> => p.catch(() => null)

    const [sig, h, n, pos, acc, bot, lot] = await Promise.all([
      settle(api.getSignal()),
      settle(api.getHTF()),
      settle(api.getNews()),
      settle(api.getPositions()),
      settle(api.getAccount()),
      settle(api.getBotStatus()),
      settle(api.getLotSize()),
    ])

    if (sig)  setSignal(sig as SignalData)
    if (h)    setHtf(h as HTFBiasData)
    if (n)    setNews(n as NewsEventData)
    if (pos)  setPositions(pos as PositionData[])
    if (acc)  setAccount(acc as AccountData)
    if (bot)  setBotStatus(bot as BotStatusData)
    if (lot)  setLotSize(lot as LotCalcData)

    setLoading(false)
    setRefreshing(false)
  }, [router])

  useEffect(() => { fetchAll() }, [fetchAll])

  // WebSocket live updates
  const handleWS = useCallback((msg: WSMessage) => {
    setWsConnected(true)
    switch (msg.type) {
      case "signal_update":
        setSignal((prev) => ({ ...prev, ...msg.data } as SignalData))
        break
      case "position_update":
        if (Array.isArray((msg.data as { positions?: unknown }).positions)) {
          setPositions((msg.data as { positions: PositionData[] }).positions)
        }
        break
      case "bot_status":
        setBotStatus((prev) => ({ ...prev, ...msg.data } as BotStatusData))
        break
      case "price_update": {
        const d = msg.data as { spread?: number }
        if (d.spread !== undefined) {
          setLotSize((prev) => prev ? { ...prev, spread: d.spread! } : prev)
        }
        break
      }
    }
  }, [])

  useWebSocket(handleWS)

  function handleLogout() {
    localStorage.removeItem("sentinel_token")
    router.push("/login")
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center justify-between sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
        <div className="flex items-center gap-2 md:gap-3 min-w-0">
          <span className="font-bold text-base md:text-lg tracking-tight truncate">
            XAUUSD <span className="text-amber-400">Sentinel</span>
          </span>
          <Separator orientation="vertical" className="h-4 bg-zinc-700 hidden sm:block" />
          <div className="flex items-center gap-1.5 shrink-0">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? "bg-emerald-400 animate-pulse" : "bg-zinc-600"}`} />
            <span className="text-xs text-zinc-500 hidden sm:inline">{wsConnected ? "Live" : "Connecting…"}</span>
          </div>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <button
            onClick={() => fetchAll(true)}
            disabled={refreshing}
            className={`flex items-center gap-1.5 text-zinc-500 hover:text-zinc-300 text-xs transition-colors px-2 py-1 rounded hover:bg-zinc-800/50 ${refreshing ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {/* Quick links dropdown */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 text-zinc-500 hover:text-zinc-300 text-xs transition-colors px-2 py-1 rounded hover:bg-zinc-800/50">
              <span className="hidden sm:inline">Tools</span>
              <span className="sm:hidden">⋮</span>
            </button>
            <div className="absolute right-0 mt-0 w-36 bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all py-1 z-20">
              <button
                onClick={() => router.push("/trades")}
                className="block w-full text-left px-4 py-2 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                Trade History
              </button>
              <button
                onClick={() => router.push("/analytics")}
                className="block w-full text-left px-4 py-2 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                Analytics
              </button>
              <button
                onClick={() => router.push("/settings")}
                className="block w-full text-left px-4 py-2 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                Bot Settings
              </button>
            </div>
          </div>

          <button
            onClick={() => router.push("/admin")}
            className="flex items-center gap-1.5 text-zinc-500 hover:text-zinc-300 text-xs transition-colors px-2 py-1 rounded hover:bg-zinc-800/50"
            title="Manage subscribers"
          >
            <Users className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Subscribers</span>
          </button>
          <button
            onClick={() => router.push("/account")}
            className="flex items-center gap-1.5 text-zinc-500 hover:text-zinc-300 text-xs transition-colors px-2 py-1 rounded hover:bg-zinc-800/50"
            title="Account settings"
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Account</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-zinc-500 hover:text-zinc-300 text-xs transition-colors px-2 py-1 rounded hover:bg-zinc-800/50"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </header>

      {/* Dashboard grid */}
      <main className="p-3 md:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {/* Top row: Core signals */}
        {loading ? (
          <>
            <Skeleton className="h-[224px]" />
            <Skeleton className="h-[224px]" />
            <Skeleton className="h-[224px]" />
          </>
        ) : (
          <>
            <div className="animate-in fade-in duration-300">
              <SignalFeed    data={signal} />
            </div>
            <div className="animate-in fade-in duration-300">
              <HTFBiasPanel  data={htf} />
            </div>
            <div className="animate-in fade-in duration-300">
              <NewsCountdown data={news} />
            </div>
          </>
        )}

        {/* Second row: Risk & Bot control */}
        {loading ? (
          <>
            <Skeleton className="h-[208px]" />
            <Skeleton className="h-[208px]" />
            <Skeleton className="h-[208px]" />
          </>
        ) : (
          <>
            <div className="animate-in fade-in duration-300 delay-75">
              <DrawdownGauge data={account} />
            </div>
            <div className="animate-in fade-in duration-300 delay-100">
              <KillSwitch    data={botStatus} onUpdate={() => fetchAll(true)} />
            </div>
            <div className="animate-in fade-in duration-300 delay-150">
              <LotCalculator live={lotSize} />
            </div>
          </>
        )}

        {/* Third row: Charts */}
        {loading ? (
          <Skeleton className="col-span-full h-[280px] md:h-[320px]" />
        ) : (
          <div className="col-span-full animate-in fade-in duration-300 delay-200">
            <EquityChart />
          </div>
        )}

        {/* Full-width: Positions */}
        <div className="col-span-full">
          {loading ? (
            <Skeleton className="h-64 md:h-[360px]" />
          ) : (
            <div className="animate-in fade-in duration-300 delay-300">
              <PositionCards positions={positions} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
