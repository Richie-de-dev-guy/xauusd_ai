"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronLeft, Save, AlertCircle, CheckCircle } from "lucide-react"

interface UserInfo {
  username: string
  telegram_chat_id: string | null
  created_at: string
}

export default function AccountPage() {
  const router = useRouter()
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  // Password form
  const [oldPassword, setOldPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState(false)

  // Telegram form
  const [telegramId, setTelegramId] = useState("")
  const [telegramLoading, setTelegramLoading] = useState(false)
  const [telegramError, setTelegramError] = useState<string | null>(null)
  const [telegramSuccess, setTelegramSuccess] = useState(false)

  // Load user info
  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem("sentinel_token")
      if (!token) { router.push("/login"); return }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (response.status === 401) { router.push("/login"); return }
        const data = await response.json()
        setUser(data)
        setTelegramId(data.telegram_chat_id || "")
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [router])

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(false)

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match")
      return
    }

    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters")
      return
    }

    setPasswordLoading(true)
    try {
      const token = localStorage.getItem("sentinel_token")
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || "Failed to change password")
      }

      setPasswordSuccess(true)
      setOldPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setTimeout(() => setPasswordSuccess(false), 3000)
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Failed to change password")
    } finally {
      setPasswordLoading(false)
    }
  }

  async function handleTelegramUpdate(e: React.FormEvent) {
    e.preventDefault()
    setTelegramError(null)
    setTelegramSuccess(false)

    setTelegramLoading(true)
    try {
      const token = localStorage.getItem("sentinel_token")
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/telegram`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          telegram_chat_id: telegramId || null,
        }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || "Failed to update Telegram ID")
      }

      setTelegramSuccess(true)
      if (user) setUser({ ...user, telegram_chat_id: telegramId || null })
      setTimeout(() => setTelegramSuccess(false), 3000)
    } catch (err) {
      setTelegramError(err instanceof Error ? err.message : "Failed to update Telegram ID")
    } finally {
      setTelegramLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <header className="border-b border-zinc-800 px-4 md:px-6 py-3 flex items-center gap-4 sticky top-0 bg-zinc-950/90 backdrop-blur z-10">
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-bold text-lg tracking-tight">Account Settings</span>
        </header>
        <div className="p-6 text-center text-zinc-500">Loading...</div>
      </div>
    )
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
        <span className="font-bold text-lg tracking-tight">Account Settings</span>
      </header>

      <main className="p-4 md:p-6 max-w-2xl mx-auto space-y-6">
        {/* Profile Info */}
        <Card className="bg-zinc-900 border-zinc-800 text-white">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Username</label>
              <div className="px-3 py-2 bg-zinc-800/40 rounded-lg text-sm font-semibold">{user?.username}</div>
            </div>
            <div>
              <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Member Since</label>
              <div className="text-sm text-zinc-400">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Change Password */}
        <Card className="bg-zinc-900 border-zinc-800 text-white">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
              Change Password
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500"
                  required
                />
              </div>

              {passwordError && (
                <div className="flex gap-2 items-start text-xs text-rose-400 bg-rose-950/40 rounded px-3 py-2">
                  <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  {passwordError}
                </div>
              )}

              {passwordSuccess && (
                <div className="flex gap-2 items-start text-xs text-emerald-400 bg-emerald-950/40 rounded px-3 py-2">
                  <CheckCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  Password changed successfully
                </div>
              )}

              <Button
                type="submit"
                disabled={passwordLoading}
                className="w-full bg-amber-500 hover:bg-amber-400 text-black font-semibold gap-2"
              >
                <Save className="w-4 h-4" />
                {passwordLoading ? "Saving..." : "Change Password"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Telegram Chat ID */}
        <Card className="bg-zinc-900 border-zinc-800 text-white">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
              Telegram Notifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleTelegramUpdate} className="space-y-4">
              <div>
                <label className="text-xs text-zinc-500 uppercase tracking-wide block mb-1">Telegram Chat ID</label>
                <input
                  type="text"
                  value={telegramId}
                  onChange={(e) => setTelegramId(e.target.value)}
                  placeholder="Enter your Telegram chat ID"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-zinc-500 placeholder-zinc-600"
                />
                <p className="text-[11px] text-zinc-600 mt-1.5">
                  Send /start to our bot, then copy your chat ID here to receive alerts about your trades.
                </p>
              </div>

              {telegramError && (
                <div className="flex gap-2 items-start text-xs text-rose-400 bg-rose-950/40 rounded px-3 py-2">
                  <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  {telegramError}
                </div>
              )}

              {telegramSuccess && (
                <div className="flex gap-2 items-start text-xs text-emerald-400 bg-emerald-950/40 rounded px-3 py-2">
                  <CheckCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  Telegram chat ID updated successfully
                </div>
              )}

              <Button
                type="submit"
                disabled={telegramLoading}
                className="w-full bg-amber-500 hover:bg-amber-400 text-black font-semibold gap-2"
              >
                <Save className="w-4 h-4" />
                {telegramLoading ? "Saving..." : "Update Telegram ID"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
