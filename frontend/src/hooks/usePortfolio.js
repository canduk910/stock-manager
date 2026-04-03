import { useState, useEffect, useCallback, useMemo } from 'react'
import { fetchBalance } from '../api/balance'
import { fetchMacroSentiment } from '../api/macro'

function calcGraham(stock) {
  const price = Number(stock.current_price)
  const per = stock.per
  const pbr = stock.pbr
  if (!price || !per || !pbr || per <= 0 || pbr <= 0) {
    return { grade: null, grahamNumber: null, discountRate: null }
  }
  const eps = price / per
  const bps = price / pbr
  if (eps <= 0 || bps <= 0) {
    return { grade: null, grahamNumber: null, discountRate: null }
  }
  const gn = Math.sqrt(22.5 * eps * bps)
  const dr = ((gn - price) / price) * 100

  let grade = 'D'
  if (dr >= 30) grade = 'A'
  else if (dr >= 10) grade = 'B+'
  else if (dr >= 0) grade = 'B'
  else if (dr >= -20) grade = 'C'

  return {
    grade,
    grahamNumber: Math.round(gn),
    discountRate: Math.round(dr * 10) / 10,
  }
}

export function usePortfolio() {
  const [balance, setBalance] = useState(null)
  const [sentiment, setSentiment] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [bal, sent] = await Promise.allSettled([
        fetchBalance(),
        fetchMacroSentiment(),
      ])
      if (bal.status === 'fulfilled') setBalance(bal.value)
      else setError(bal.reason?.message || '잔고 조회 실패')
      if (sent.status === 'fulfilled') setSentiment(sent.value)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // 자산 배분 (국내/해외/현금)
  const allocation = useMemo(() => {
    if (!balance) return []
    const kr = Number(balance.stock_eval_domestic) || 0
    const us = Number(balance.stock_eval_overseas_krw) || 0
    const cash = Number(balance.deposit) || 0
    const total = kr + us + cash
    if (total === 0) return []
    return [
      { name: '국내주식', value: kr, pct: Math.round(kr / total * 1000) / 10, color: '#3b82f6' },
      { name: '해외주식', value: us, pct: Math.round(us / total * 1000) / 10, color: '#8b5cf6' },
      { name: '현금', value: cash, pct: Math.round(cash / total * 1000) / 10, color: '#6b7280' },
    ].filter(a => a.value > 0)
  }, [balance])

  // 보유종목 통합 + 안전마진 등급
  const holdings = useMemo(() => {
    if (!balance) return []
    const totalEval = Number(balance.total_evaluation) || 1

    const kr = (balance.stock_list || []).map(s => {
      const evalAmt = Number(s.eval_amount) || 0
      return {
        ...s,
        market: 'KR',
        currency: 'KRW',
        evalKrw: evalAmt,
        weight: Math.round(evalAmt / totalEval * 1000) / 10,
        profitRate: Number(s.profit_rate) || 0,
        ...calcGraham(s),
      }
    })

    const us = (balance.overseas_list || []).map(s => {
      const evalKrw = Number(s.eval_amount_krw) || 0
      return {
        ...s,
        market: 'US',
        currency: s.currency || 'USD',
        evalKrw,
        weight: Math.round(evalKrw / totalEval * 1000) / 10,
        profitRate: Number(s.profit_rate) || 0,
        ...calcGraham(s),
      }
    })

    return [...kr, ...us].sort((a, b) => b.evalKrw - a.evalKrw)
  }, [balance])

  // 총 수익률
  const totalReturn = useMemo(() => {
    if (!balance) return null
    const stockEval = Number(balance.stock_eval) || 0
    const totalEval = Number(balance.total_evaluation) || 0
    const deposit = Number(balance.deposit) || 0
    const invested = totalEval - deposit
    if (invested <= 0) return null
    // 총 평가손익 계산
    const totalPL = holdings.reduce((sum, h) => sum + (Number(h.profit_loss) || 0), 0)
    const totalCost = invested - totalPL
    if (totalCost <= 0) return null
    return Math.round(totalPL / totalCost * 1000) / 10
  }, [balance, holdings])

  const cashRatio = useMemo(() => {
    if (!balance) return 0
    const total = Number(balance.total_evaluation) || 1
    const cash = Number(balance.deposit) || 0
    return Math.round(cash / total * 1000) / 10
  }, [balance])

  return {
    balance,
    sentiment,
    loading,
    error,
    load,
    allocation,
    holdings,
    totalReturn,
    cashRatio,
  }
}
