/**
 * 다중심볼 실시간 시세 WebSocket 훅 (/ws/market-board).
 * subscribe(symbols[]) / unsubscribe(symbols[]) 제공.
 * prices 상태: { [symbol]: { price, change_pct, sign } }
 */
import { useState, useEffect, useRef, useCallback } from 'react'

export function useMarketBoardWS() {
  const [prices, setPrices] = useState({})
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const mountedRef = useRef(true)
  const retryRef = useRef(null)
  const pendingRef = useRef(null)
  const rafRef = useRef(null)
  const backoffRef = useRef(500)
  const subscribedRef = useRef(new Set())  // 현재 구독 중인 심볼들

  const flushState = useCallback(() => {
    if (!mountedRef.current || !pendingRef.current) return
    const pending = pendingRef.current
    pendingRef.current = null
    rafRef.current = null
    setPrices(prev => ({ ...prev, ...pending }))
  }, [])

  const scheduleFlush = useCallback((updates) => {
    pendingRef.current = pendingRef.current
      ? { ...pendingRef.current, ...updates }
      : updates
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(flushState)
    }
  }, [flushState])

  const sendToWS = useCallback((msg) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg))
    }
  }, [])

  const subscribe = useCallback((symbols) => {
    if (!symbols || symbols.length === 0) return
    const newSymbols = symbols.filter(s => !subscribedRef.current.has(s))
    if (newSymbols.length === 0) return
    newSymbols.forEach(s => subscribedRef.current.add(s))
    sendToWS({ action: 'subscribe', symbols: newSymbols })
  }, [sendToWS])

  const unsubscribe = useCallback((symbols) => {
    if (!symbols || symbols.length === 0) return
    symbols.forEach(s => subscribedRef.current.delete(s))
    sendToWS({ action: 'unsubscribe', symbols })
  }, [sendToWS])

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close(1000)
      wsRef.current = null
    }
    if (retryRef.current) {
      clearTimeout(retryRef.current)
      retryRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}//${host}/ws/market-board`)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      backoffRef.current = 500
      setConnected(true)
      // 재연결 시 기존 구독 복원
      const syms = Array.from(subscribedRef.current)
      if (syms.length > 0) {
        ws.send(JSON.stringify({ action: 'subscribe', symbols: syms }))
      }
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'prices' && msg.data) {
          scheduleFlush(msg.data)
        }
      } catch (e) {}
    }

    ws.onerror = () => {
      if (!mountedRef.current) return
      setConnected(false)
    }

    ws.onclose = (event) => {
      if (!mountedRef.current) return
      setConnected(false)
      if (event.code !== 1000 && mountedRef.current) {
        const delay = backoffRef.current
        backoffRef.current = Math.min(delay * 2, 10000)
        retryRef.current = setTimeout(() => {
          if (mountedRef.current) connect()
        }, delay)
      }
    }
  }, [scheduleFlush])

  // visibilitychange: 탭 복귀 시 즉시 재연결
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        const ws = wsRef.current
        if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
          backoffRef.current = 500
          connect()
        }
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [connect])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (retryRef.current) clearTimeout(retryRef.current)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close(1000)
        wsRef.current = null
      }
    }
  }, [connect])

  return { prices, connected, subscribe, unsubscribe }
}
