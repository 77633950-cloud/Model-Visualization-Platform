import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.host}/ws/status`

export function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const callbacksRef = useRef([])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnecting(true)
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setConnecting(false)
      }

      ws.onclose = () => {
        setConnected(false)
        setConnecting(false)
        reconnectTimerRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          callbacksRef.current.forEach(cb => cb(data))
        } catch (e) {
          console.error('WebSocket 解析错误:', e)
        }
      }
    } catch (e) {
      setConnecting(false)
      reconnectTimerRef.current = setTimeout(connect, 3000)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
    setConnecting(false)
  }, [])

  const onData = useCallback((cb) => {
    callbacksRef.current.push(cb)
    return () => {
      callbacksRef.current = callbacksRef.current.filter(c => c !== cb)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return { connected, connecting, onData }
}
