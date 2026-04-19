"use client"
import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import type { LotCalcData } from "@/lib/types"
import { api } from "@/lib/api"
import { Calculator } from "lucide-react"

interface Props { live: LotCalcData | null }

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-zinc-800 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-xs font-semibold tabular-nums ${highlight ? "text-emerald-400 text-sm" : ""}`}>{value}</span>
    </div>
  )
}

export function LotCalculator({ live }: Props) {
  const [riskPct, setRiskPct] = useState<string>("")
  const [result, setResult] = useState<LotCalcData | null>(null)
  const [loading, setLoading] = useState(false)

  const d = result ?? live

  async function handleCalculate() {
    setLoading(true)
    try {
      const res = await api.calculateLot({
        risk_pct: riskPct ? parseFloat(riskPct) : null,
      }) as LotCalcData
      setResult(res)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  return (
    <Card className="bg-zinc-900 border-zinc-800 text-white">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Calculator className="w-3.5 h-3.5" />
          Lot Size Calculator
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* What-if input */}
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-[10px] text-zinc-500 uppercase tracking-wide block mb-1">Risk %</label>
            <input
              type="number"
              min="0.1"
              max="10"
              step="0.1"
              placeholder={live ? String(live.risk_pct) : "1.0"}
              value={riskPct}
              onChange={(e) => { setRiskPct(e.target.value); setResult(null) }}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-zinc-500 text-white placeholder-zinc-600"
            />
          </div>
          <div className="flex items-end">
            <Button
              size="sm"
              variant="outline"
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              onClick={handleCalculate}
              disabled={loading}
            >
              Calc
            </Button>
          </div>
        </div>

        {d ? (
          <div>
            <Row label="Balance"       value={`$${d.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
            <Row label="Risk Amount"   value={`$${d.risk_amount.toFixed(2)}`} />
            <Row label="ATR"           value={d.atr.toFixed(2)} />
            <Row label="Spread"        value={d.spread.toFixed(5)} />
            <Row label="SL Distance"   value={d.sl_distance.toFixed(2)} />
            <Row label="Contract Size" value={`${d.contract_size}`} />
            <Row label="Raw Lot"       value={d.calculated_lot.toFixed(4)} />
            <Row label="Rounded Lot"   value={`${d.rounded_lot}`} highlight />
          </div>
        ) : (
          <p className="text-zinc-600 text-xs text-center py-4">Waiting for first bot cycle…</p>
        )}
      </CardContent>
    </Card>
  )
}
