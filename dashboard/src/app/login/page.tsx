"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { access_token } = await api.login(username, password)
      localStorage.setItem("sentinel_token", access_token)
      router.push("/")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-full max-w-sm space-y-6 px-4">
        {/* Logo / title */}
        <div className="text-center space-y-1">
          <div className="text-3xl font-bold text-white tracking-tight">
            XAUUSD <span className="text-amber-400">Sentinel</span>
          </div>
          <p className="text-zinc-500 text-sm">Trading Dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-zinc-400 uppercase tracking-wide">Username</label>
            <input
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
              placeholder="admin"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-zinc-400 uppercase tracking-wide">Password</label>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-rose-400 text-xs bg-rose-950/40 rounded-lg px-3 py-2">{error}</p>
          )}

          <Button
            type="submit"
            className="w-full bg-amber-500 hover:bg-amber-400 text-black font-semibold"
            disabled={loading}
          >
            {loading ? "Signing in…" : "Sign In"}
          </Button>
        </form>

        <p className="text-center text-xs text-zinc-700">
          Credentials set via <code className="text-zinc-500">DASHBOARD_USERNAME</code> /
          <code className="text-zinc-500"> DASHBOARD_PASSWORD</code> env vars
        </p>
      </div>
    </div>
  )
}
