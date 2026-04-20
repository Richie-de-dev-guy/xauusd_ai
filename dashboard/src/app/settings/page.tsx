"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronLeft, Save, AlertCircle, CheckCircle } from "lucide-react"

interface BotSettings {
  risk_percent: number
  london_session_start: number
  london_session_end: number
  newyork_session_start: number
  newyork_session_end: number
  max_daily_drawdown_percent: number
  news_blackout_minutes: number
  min_atr_filter: number
  ema_fast_period: number
  ema_slow_period: number
  rsi_period: number
  atr_period: number
}

export default function SettingsPage() {
  const router = useRouter()
  const [settings, setSettings] = useState<BotSettings | null>(null)
  const [formData, setFormData] = useState<Partial<BotSettings>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    async function loadSettings() {
      const token = localStorage.getItem("sentinel_token")
      if (!token) { router.push("/login"); return }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/settings`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (response.status === 401) { router.push("/login"); return }
        const data = await response.json()
        setSettings(data)
        setFormData(data)
      } finally {
        setLoading(false)
      }
    }
    loadSettings()
  }, [router])

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSuccess(false)

    try {
      const token = localStorage.getItem("sentinel_token")
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/settings`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || "Failed to save settings")
      }

      const updated = await response.json()
      setSettings(updated)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings")
    } finally {
      setSaving(false)
    }
  }

  function handleChange(key: keyof BotSettings, value: number) {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  if (loading || !settings) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-bold text-lg tracking-tight">Bot Settings</span>
        </header>
        <div className="p-6 text-center text-zinc-500">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-bold text-lg tracking-tight">Bot Settings</span>
      </header>

      <main className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
        {/* Risk Management */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Risk Management</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">
                  Risk Per Trade (%)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="0.1"
                    max="5"
                    step="0.1"
                    value={formData.risk_percent ?? settings.risk_percent}
                    onChange={(e) => handleChange("risk_percent", parseFloat(e.target.value))}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  />
                  <span className="text-sm font-semibold text-amber-400 w-12">
                    {(formData.risk_percent ?? settings.risk_percent).toFixed(1)}%
                  </span>
                </div>
                <p className="text-[11px] text-zinc-600 mt-1">Risk amount per trade (default: 1.0%)</p>
              </div>

              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">
                  Max Daily Drawdown (%)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="1"
                    max="20"
                    step="0.1"
                    value={formData.max_daily_drawdown_percent ?? settings.max_daily_drawdown_percent}
                    onChange={(e) => handleChange("max_daily_drawdown_percent", parseFloat(e.target.value))}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  />
                  <span className="text-sm font-semibold text-rose-400 w-12">
                    {(formData.max_daily_drawdown_percent ?? settings.max_daily_drawdown_percent).toFixed(1)}%
                  </span>
                </div>
                <p className="text-[11px] text-zinc-600 mt-1">Stop trading after this daily loss (default: 5%)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trading Sessions */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Trading Sessions (UTC)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-zinc-300">London Session</h3>
                <div className="flex items-center gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Start (Hour)</label>
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={formData.london_session_start ?? settings.london_session_start}
                      onChange={(e) => handleChange("london_session_start", parseInt(e.target.value))}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <span className="text-zinc-500 mt-6">→</span>
                  <div className="flex-1">
                    <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">End (Hour)</label>
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={formData.london_session_end ?? settings.london_session_end}
                      onChange={(e) => handleChange("london_session_end", parseInt(e.target.value))}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-zinc-300">New York Session</h3>
                <div className="flex items-center gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Start (Hour)</label>
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={formData.newyork_session_start ?? settings.newyork_session_start}
                      onChange={(e) => handleChange("newyork_session_start", parseInt(e.target.value))}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <span className="text-zinc-500 mt-6">→</span>
                  <div className="flex-1">
                    <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">End (Hour)</label>
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={formData.newyork_session_end ?? settings.newyork_session_end}
                      onChange={(e) => handleChange("newyork_session_end", parseInt(e.target.value))}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* News Filter */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">News Filter</CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">
                News Blackout Window (Minutes)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min="0"
                  max="120"
                  step="5"
                  value={formData.news_blackout_minutes ?? settings.news_blackout_minutes}
                  onChange={(e) => handleChange("news_blackout_minutes", parseInt(e.target.value))}
                  className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                />
                <span className="text-sm font-semibold text-blue-400 w-20">
                  {(formData.news_blackout_minutes ?? settings.news_blackout_minutes)} min
                </span>
              </div>
              <p className="text-[11px] text-zinc-600 mt-1">Stop trading before high-impact news events</p>
            </div>
          </CardContent>
        </Card>

        {/* Technical Indicators */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Technical Indicators</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { label: "EMA Fast Period", key: "ema_fast_period" as const, min: 5, max: 50 },
                { label: "EMA Slow Period", key: "ema_slow_period" as const, min: 20, max: 200 },
                { label: "RSI Period", key: "rsi_period" as const, min: 5, max: 30 },
                { label: "ATR Period", key: "atr_period" as const, min: 5, max: 30 },
                { label: "Min ATR Filter", key: "min_atr_filter" as const, min: 0.1, max: 10, step: 0.1 },
              ].map(({ label, key, min, max, step = 1 }) => (
                <div key={key}>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-2">{label}</label>
                  <input
                    type="number"
                    min={min}
                    max={max}
                    step={step}
                    value={formData[key] ?? settings[key]}
                    onChange={(e) => handleChange(key, parseFloat(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Messages */}
        {error && (
          <div className="flex gap-2 items-start text-xs text-rose-400 bg-rose-950/40 rounded px-4 py-3">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="flex gap-2 items-start text-xs text-emerald-400 bg-emerald-950/40 rounded px-4 py-3">
            <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
            Settings saved successfully
          </div>
        )}

        {/* Save Button */}
        <Button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-amber-500 hover:bg-amber-400 text-black font-semibold gap-2 py-3"
        >
          <Save className="w-4 h-4" />
          {saving ? "Saving..." : "Save Settings"}
        </Button>

        <div className="bg-amber-950/30 border border-amber-700/30 rounded-lg p-4">
          <p className="text-xs text-amber-400">
            ⚠️ Bot changes take effect on the next strategy cycle (within 5 seconds). Changes are applied in real-time but won't affect active positions.
          </p>
        </div>
      </main>
    </div>
  )
}
