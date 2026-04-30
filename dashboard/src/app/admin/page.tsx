"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, RotateCcw, Users, ChevronLeft, Copy, Check } from "lucide-react"

interface Subscriber {
  id: number
  name: string
  email: string | null
  telegram_chat_id: string | null
  api_key: string | null
  plan: string
  is_active: boolean
  created_at: string
  notes: string | null
}

const PLAN_COLORS: Record<string, string> = {
  TELEGRAM: "border-blue-700 text-blue-400",
  EA:       "border-amber-700 text-amber-400",
  BOTH:     "border-purple-700 text-purple-400",
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="ml-1 text-zinc-500 hover:text-zinc-300 transition-colors">
      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
    </button>
  )
}

function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", email: "", telegram_chat_id: "", plan: "TELEGRAM", notes: "" })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/subscribers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("sentinel_token")}`,
        },
        body: JSON.stringify(form),
      }).then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail)
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create")
    } finally {
      setLoading(false)
    }
  }

  const inputCls = "w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">New Subscriber</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Name *</label>
            <input required className={inputCls} value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Email</label>
            <input type="email" className={inputCls} value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Plan *</label>
            <select className={inputCls} value={form.plan}
              onChange={e => setForm(f => ({ ...f, plan: e.target.value }))}>
              <option value="TELEGRAM">Telegram — $40-50/mo</option>
              <option value="EA">EA Copy Trading — $90-120/mo</option>
              <option value="BOTH">Both Plans</option>
            </select>
          </div>
          {(form.plan === "TELEGRAM" || form.plan === "BOTH") && (
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Telegram Chat ID</label>
              <input className={inputCls} placeholder="e.g. 123456789" value={form.telegram_chat_id}
                onChange={e => setForm(f => ({ ...f, telegram_chat_id: e.target.value }))} />
              <p className="text-[10px] text-zinc-600 mt-1">
                Subscriber sends /start to your bot, then share their chat ID here
              </p>
            </div>
          )}
          <div>
            <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Notes</label>
            <input className={inputCls} value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </div>
          {error && <p className="text-rose-400 text-xs">{error}</p>}
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="ghost" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-semibold" disabled={loading}>
              {loading ? "Creating…" : "Create Subscriber"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const router = useRouter()
  const [subscribers, setSubscribers] = useState<Subscriber[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  async function load() {
    const token = localStorage.getItem("sentinel_token")
    if (!token) { router.push("/login"); return }
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/subscribers`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 401) { router.push("/login"); return }
      setSubscribers(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  async function toggleActive(sub: Subscriber) {
    const token = localStorage.getItem("sentinel_token")
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/subscribers/${sub.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ is_active: !sub.is_active }),
    })
    load()
  }

  async function rotateKey(id: number) {
    if (!confirm("Rotate API key? The old key will stop working immediately.")) return
    const token = localStorage.getItem("sentinel_token")
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/subscribers/${id}/rotate-key`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  async function deleteSub(id: number) {
    if (!confirm("Delete this subscriber permanently?")) return
    const token = localStorage.getItem("sentinel_token")
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/subscribers/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  const active = subscribers.filter(s => s.is_active).length

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
        <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="font-bold text-lg tracking-tight">
          AurumEdge
          <span className="text-zinc-500 font-normal text-base ml-2">/ Subscribers</span>
        </span>
      </header>

      <main className="p-4 md:p-6 space-y-4 max-w-4xl mx-auto">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Total",    value: subscribers.length },
            { label: "Active",   value: active },
            { label: "Inactive", value: subscribers.length - active },
          ].map(({ label, value }) => (
            <Card key={label} className="bg-zinc-900 border-zinc-800 text-white">
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-zinc-500 uppercase tracking-wide mt-0.5">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Header + add button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-400">
            <Users className="w-4 h-4" />
            <span className="text-sm font-medium">Subscribers</span>
          </div>
          <Button
            size="sm"
            className="gap-1.5 bg-amber-500 hover:bg-amber-400 text-black font-semibold"
            onClick={() => setShowCreate(true)}
          >
            <Plus className="w-4 h-4" /> Add Subscriber
          </Button>
        </div>

        {/* Subscriber cards */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <Card key={i} className="bg-zinc-900 border-zinc-800 animate-pulse h-28" />
            ))}
          </div>
        ) : subscribers.length === 0 ? (
          <Card className="bg-zinc-900 border-zinc-800 text-white">
            <CardContent className="p-8 text-center text-zinc-500">
              No subscribers yet. Click &ldquo;Add Subscriber&rdquo; to onboard your first paying customer.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {subscribers.map(sub => (
              <Card key={sub.id} className={`border text-white transition-colors ${sub.is_active ? "bg-zinc-900 border-zinc-800" : "bg-zinc-900/50 border-zinc-800/50 opacity-60"}`}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold">{sub.name}</span>
                        <Badge variant="outline" className={`text-[10px] ${PLAN_COLORS[sub.plan] ?? "border-zinc-700 text-zinc-400"}`}>
                          {sub.plan}
                        </Badge>
                        {!sub.is_active && (
                          <Badge variant="outline" className="text-[10px] border-zinc-700 text-zinc-500">Inactive</Badge>
                        )}
                      </div>

                      {sub.email && (
                        <p className="text-xs text-zinc-500">{sub.email}</p>
                      )}

                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                        {sub.telegram_chat_id && (
                          <span>Telegram: <code className="text-zinc-400">{sub.telegram_chat_id}</code></span>
                        )}
                        {sub.api_key && (
                          <span className="flex items-center">
                            API Key: <code className="text-zinc-400 ml-1">{sub.api_key.slice(0, 12)}…</code>
                            <CopyButton text={sub.api_key} />
                          </span>
                        )}
                      </div>

                      {sub.notes && (
                        <p className="text-[11px] text-zinc-600 italic">{sub.notes}</p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-1.5 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-[11px] border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                        onClick={() => toggleActive(sub)}
                      >
                        {sub.is_active ? "Deactivate" : "Activate"}
                      </Button>
                      {sub.api_key && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2 text-[11px] border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                          onClick={() => rotateKey(sub.id)}
                        >
                          <RotateCcw className="w-3 h-3 mr-1" />
                          New Key
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-[11px] border-rose-900 text-rose-400 hover:bg-rose-950"
                        onClick={() => deleteSub(sub.id)}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onCreated={load} />
      )}
    </div>
  )
}
