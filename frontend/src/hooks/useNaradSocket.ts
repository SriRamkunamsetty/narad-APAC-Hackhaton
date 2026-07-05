import { useEffect, useRef, useState, useCallback } from 'react'
import type { WSMessage, CityPulse, ParliamentDecision } from '../types'

const WS_URL = (import.meta.env.VITE_WS_URL as string) ||
  (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws'

interface UseNaradSocket {
  connected: boolean
  cityPulse: CityPulse | null
  decision: ParliamentDecision | null
  alerts: string[]
  parliamentRunning: boolean
  triggerParliament: (reason: string) => void
}

export function useNaradSocket(): UseNaradSocket {
  const [connected, setConnected] = useState(false)
  const [cityPulse, setCityPulse] = useState<CityPulse | null>(null)
  const [decision, setDecision] = useState<ParliamentDecision | null>(null)
  const [alerts, setAlerts] = useState<string[]>([])
  const [parliamentRunning, setParliamentRunning] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      retryRef.current = 0
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
        else clearInterval(ping)
      }, 25000)
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        switch (msg.type) {
          case 'city_pulse':
            setCityPulse(msg.payload)
            break
          case 'parliament_start':
            setParliamentRunning(true)
            break
          case 'parliament_end':
            setDecision(msg.payload)
            setParliamentRunning(false)
            break
          case 'alert':
            setAlerts(prev => [msg.payload.message, ...prev].slice(0, 20))
            break
        }
      } catch (e) {
        // ignore pong / malformed
      }
    }

    ws.onclose = () => {
      setConnected(false)
      const delay = Math.min(1000 * 2 ** retryRef.current, 15000)
      retryRef.current += 1
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  const triggerParliament = useCallback((reason: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'trigger_parliament', reason }))
    }
  }, [])

  return { connected, cityPulse, decision, alerts, parliamentRunning, triggerParliament }
}
