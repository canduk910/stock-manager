/**
 * 실시간 호가/체결 WebSocket 훅.
 * - 국내(KR): KIS WS 브릿지 (price + orderbook 메시지)
 * - 해외(US): yfinance 2초 polling (price 메시지만)
 *
 * symbol 변경 시 기존 WS 닫고 재연결 + state 초기화.
 * 비정상 종료 시 지수 백오프 재연결 (500ms → 최대 10초).
 * rAF throttle로 고빈도 리렌더링 방지.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

const EMPTY_STATE = {
  price: null,
  change: null,
  changeRate: null,
  sign: null,
  asks: [],
  bids: [],
  totalAskVolume: null,
  totalBidVolume: null,
  connected: false,
  errorMessage: null,
}

export function useQuote(symbol, market = 'KR', exchange = 'auto') {
  const [state, setState] = useState(EMPTY_STATE)

  // rAF throttle refs
  const pendingRef = useRef(null)
  const rafRef = useRef(null)

  const flushState = useCallback(() => {
    if (!pendingRef.current) return
    const pending = pendingRef.current
    pendingRef.current = null
    rafRef.current = null
    setState(prev => ({ ...prev, ...pending }))
  }, [])

  const scheduleFlush = useCallback((updates) => {
    pendingRef.current = pendingRef.current
      ? { ...pendingRef.current, ...updates }
      : updates
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(flushState)
    }
  }, [flushState])

  // scheduleFlush를 ref로 잡아 onMessage 안정성 보장
  const sfRef = useRef(scheduleFlush)
  sfRef.current = scheduleFlush

  const onMessage = useCallback((msg) => {
    if (msg.type === 'price') {
      sfRef.current({
        price: msg.price,
        change: msg.change,
        changeRate: msg.change_rate,
        sign: msg.sign,
      })
    } else if (msg.type === 'orderbook') {
      sfRef.current({
        asks: msg.asks || [],
        bids: msg.bids || [],
        totalAskVolume: msg.total_ask_volume,
        totalBidVolume: msg.total_bid_volume,
      })
    } else if (msg.type === 'disconnected') {
      setState(prev => ({ ...prev, connected: false }))
    } else if (msg.type === 'error') {
      setState(prev => ({ ...prev, errorMessage: msg.message || '실시간 시세 오류' }))
    }
  }, [])

  // url 빌더는 매 connect 시점마다 lazy 평가되어 갱신된 access_token 반영
  // (stale-token 무한 백오프 방지). symbol/market/exchange 변경 시 함수 인스턴스가
  // 갱신되어 useWebSocket 의 useEffect 가 재연결을 트리거.
  // KR 거래소 셀렉터(2026-05-08): exchange ∈ {'auto','UN','KRX','NXT'}.
  // 'auto' 기본 — 백엔드(KISQuoteManager)가 KST 4구간으로 자동 분기.
  const buildUrl = useCallback(() => {
    if (!symbol) return null
    const base = buildWsUrl(`/ws/quote/${symbol}`)
    const params = []
    if (market === 'FNO') params.push('market=FNO')
    if (market !== 'FNO' && exchange && exchange !== 'auto') {
      params.push(`exchange=${encodeURIComponent(exchange)}`)
    } else if (market !== 'FNO' && exchange === 'auto') {
      params.push('exchange=auto')
    }
    return params.length ? `${base}?${params.join('&')}` : base
  }, [symbol, market, exchange])

  const { connected } = useWebSocket(buildUrl, { onMessage })

  // symbol 변경 시 state 초기화
  useEffect(() => {
    setState(EMPTY_STATE)
    pendingRef.current = null
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [symbol])

  // cleanup rAF on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return { ...state, connected }
}
