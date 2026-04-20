const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("sentinel_token")
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json()
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getSignal: () => request("/api/signal"),
  getHTF: () => request("/api/htf"),
  getNews: () => request("/api/news"),
  getPositions: () => request("/api/positions"),
  getAccount: () => request("/api/account"),
  getBotStatus: () => request("/api/bot/status"),
  getEquity: (period = "1d") => request(`/api/equity?period=${period}`),
  getLotSize: () => request("/api/lotsize"),

  haltBot: (close = true) =>
    request(`/api/bot/halt?close=${close}`, { method: "POST" }),
  resumeBot: () => request("/api/bot/resume", { method: "POST" }),

  calculateLot: (body: Record<string, number | null>) =>
    request("/api/lotsize/calculate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getTrades: (days = 30, outcome?: string) => {
    const params = new URLSearchParams({ days: days.toString() })
    if (outcome) params.append("outcome", outcome)
    return request(`/api/trades?${params}`)
  },

  getAnalytics: (days = 30) => request(`/api/trades/analytics?days=${days}`),

  getSettings: () => request("/api/settings"),
  updateSettings: (body: Record<string, number>) =>
    request("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
}
