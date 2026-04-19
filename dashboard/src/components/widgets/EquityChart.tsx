"use client"
import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { EquityPoint } from "@/lib/types"
import { api } from "@/lib/api"

type Period = "1d" | "7d" | "30d" | "all"

interface Props { initialData?: EquityPoint[] }

export function EquityChart({ initialData = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  const balanceSeriesRef = useRef<{ setData: (d: unknown[]) => void } | null>(null)
  const equitySeriesRef  = useRef<{ setData: (d: unknown[]) => void } | null>(null)
  const [period, setPeriod] = useState<Period>("1d")
  const [data, setData] = useState<EquityPoint[]>(initialData)

  useEffect(() => {
    api.getEquity(period).then((d) => setData(d as EquityPoint[]))
  }, [period])

  useEffect(() => {
    if (!containerRef.current || typeof window === "undefined") return

    let cleanup: (() => void) | undefined

    import("lightweight-charts").then((lc) => {
      if (!containerRef.current) return

      const height = window.innerWidth < 768 ? 250 : 280
      const chart = lc.createChart(containerRef.current, {
        layout: {
          background: { type: lc.ColorType.Solid, color: "transparent" },
          textColor: "#71717a",
        },
        grid: {
          vertLines: { color: "#27272a" },
          horzLines: { color: "#27272a" },
        },
        rightPriceScale: { borderColor: "#27272a" },
        timeScale: { borderColor: "#27272a", timeVisible: true },
        width:  containerRef.current.clientWidth,
        height,
      })

      // v5 API: addSeries(SeriesType, options)
      const balanceSeries = chart.addSeries(lc.LineSeries, {
        color: "#71717a",
        lineWidth: 1,
        lineStyle: lc.LineStyle.Dashed,
        title: "Balance",
        priceLineVisible: false,
      })

      const equitySeries = chart.addSeries(lc.AreaSeries, {
        lineColor: "#10b981",
        topColor: "#10b98130",
        bottomColor: "#10b98105",
        lineWidth: 2,
        title: "Equity",
        priceLineVisible: false,
      })

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      chartRef.current         = chart as any
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      balanceSeriesRef.current = balanceSeries as any
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      equitySeriesRef.current  = equitySeries  as any

      const ro = new ResizeObserver(() => {
        if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
      })
      ro.observe(containerRef.current)

      cleanup = () => { ro.disconnect(); chart.remove() }
    })

    return () => { cleanup?.() }
  }, [])

  // Feed data into chart whenever it changes
  useEffect(() => {
    if (!balanceSeriesRef.current || !equitySeriesRef.current || data.length === 0) return

    const toTime = (ts: string) => Math.floor(new Date(ts).getTime() / 1000)

    balanceSeriesRef.current.setData(
      data.map((d) => ({ time: toTime(d.timestamp), value: d.balance }))
    )
    equitySeriesRef.current.setData(
      data.map((d) => ({ time: toTime(d.timestamp), value: d.equity }))
    )
  }, [data])

  const PERIODS: Period[] = ["1d", "7d", "30d", "all"]

  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white col-span-full">
      <CardHeader className="pb-2 flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
          Equity Curve
        </CardTitle>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <Button
              key={p}
              variant={period === p ? "secondary" : "ghost"}
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => setPeriod(p)}
            >
              {p}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="h-[250px] md:h-[280px] flex items-center justify-center text-zinc-600 text-sm">
            No data yet — snapshots are saved every strategy cycle
          </div>
        ) : (
          <div ref={containerRef} className="w-full" />
        )}
      </CardContent>
    </Card>
  )
}
