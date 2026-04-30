"use client"
import { useEffect, useRef } from "react"
import type { WSMessage } from "@/lib/types"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"
const RECONNECT_DELAY = 3000

type Handler = (msg: WSMessage) => void

export function useWebSocket(onMessage: Handler) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)
  const handlerRef = useRef(onMessage)

  useEffect(() => {
    handlerRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    mountedRef.current = true
    const token = localStorage.getItem("sentinel_token")
    if (!token || !mountedRef.current) return

    function connect() {
      if (!mountedRef.current) return

      const ws = new WebSocket(`${WS_BASE}/ws?token=${token}`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as WSMessage
          handlerRef.current(msg)
        } catch { /* ignore malformed frames */ }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])
}
