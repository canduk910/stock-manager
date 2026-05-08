/**
 * 공통 WebSocket 훅.
 * - 지수 백오프 재연결 (500ms → 최대 10초)
 * - visibilitychange 탭 복귀 시 즉시 재연결
 * - 정상 종료(1000) 시 재연결 안 함
 *
 * @param {string|null|(() => string|null)} url - WebSocket URL 또는 매 connect 시
 *   lazy 평가될 함수. 함수형은 401/1008 close 후 백오프 재시도 시점에 최신 token이
 *   박힌 URL을 다시 만들어 stale token으로 무한 재시도되는 문제를 자기치유한다.
 *   호출자는 함수 인스턴스를 안정화(모듈 const 또는 useCallback)해야 매번 재연결되지 않는다.
 * @param {object} options
 * @param {(msg: any) => void} options.onMessage - 파싱된 JSON 메시지 핸들러
 * @param {(ws: WebSocket) => void} [options.onOpen] - 연결 성공 콜백
 */
import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(url, { onMessage, onOpen } = {}) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const mountedRef = useRef(true)
  const retryRef = useRef(null)
  const backoffRef = useRef(500)

  // stable refs for callbacks
  const onMessageRef = useRef(onMessage)
  const onOpenRef = useRef(onOpen)
  useEffect(() => { onMessageRef.current = onMessage }, [onMessage])
  useEffect(() => { onOpenRef.current = onOpen }, [onOpen])

  const sendMessage = useCallback((msg) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
  }, [])

  const connect = useCallback(() => {
    if (!url) return
    // url 이 함수면 매 connect 시도마다 lazy 평가 → localStorage 의 최신 access_token 반영.
    const currentUrl = typeof url === 'function' ? url() : url
    if (!currentUrl) return

    // 이전 WS 정리
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close(1000)
      wsRef.current = null
    }
    if (retryRef.current) {
      clearTimeout(retryRef.current)
      retryRef.current = null
    }

    const ws = new WebSocket(currentUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      backoffRef.current = 500
      setConnected(true)
      if (onOpenRef.current) onOpenRef.current(ws)
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(event.data)
        if (onMessageRef.current) onMessageRef.current(msg)
      } catch {}
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
  }, [url])

  // visibilitychange: 탭 복귀 시 즉시 재연결
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState !== 'visible' || !url) return
      const ws = wsRef.current
      if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
        backoffRef.current = 500
        connect()
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [url, connect])

  // 연결/해제 라이프사이클
  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (retryRef.current) clearTimeout(retryRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close(1000)
        wsRef.current = null
      }
    }
  }, [connect])

  return { connected, sendMessage }
}

/** WebSocket URL 생성 헬퍼 */
export function buildWsUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = localStorage.getItem('access_token')
  const sep = path.includes('?') ? '&' : '?'
  const tokenParam = token ? `${sep}token=${encodeURIComponent(token)}` : ''
  return `${protocol}//${window.location.host}${path}${tokenParam}`
}
