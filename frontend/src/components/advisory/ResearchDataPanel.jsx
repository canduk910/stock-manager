import { useState } from 'react'

/**
 * AI분석 입력 데이터 통합 미리보기 패널.
 * GPT 프롬프트에 들어가는 모든 데이터를 보여준다.
 *
 * A. 기존 분석 데이터 (새로고침): 손익/BS/CF, 계량지표, 기술지표, 전략, 매크로
 * B. 리서치 데이터 (입력정보 획득): 6카테고리
 *
 * @param {object} data - research_data (6카테고리)
 * @param {object} advData - advisory cache (fundamental, technical, strategy_signals)
 * @param {string} market - 'KR' | 'US'
 */
export default function ResearchDataPanel({ data, advData, market = 'KR' }) {
  const hasAdv = !!advData
  const hasResearch = data && data.categories_ok > 0

  if (!hasAdv && !hasResearch) return null

  // ── A. 기존 분석 데이터 카테고리 ──
  const fundamental = advData?.fundamental || {}
  const technical = advData?.technical || {}
  const strategySignals = advData?.strategy_signals

  const advCategories = [
    { key: 'income', label: '손익계산서 (3년)', render: () => renderIncomeStmt(fundamental, market), hasData: (fundamental.income_stmt || []).length > 0 },
    { key: 'bs', label: '대차대조표 (3년)', render: () => renderBalanceSheet(fundamental, market), hasData: (fundamental.balance_sheet || []).length > 0 },
    { key: 'cf', label: '현금흐름표 (3년)', render: () => renderCashflow(fundamental, market), hasData: (fundamental.cashflow || []).length > 0 },
    { key: 'metrics', label: '계량지표 (PER/PBR/ROE 등)', render: () => renderMetrics(fundamental), hasData: !!fundamental.metrics },
    { key: 'quarterly', label: '분기 실적 (최근 4분기)', render: () => renderQuarterly(fundamental, market), hasData: (fundamental.quarterly || []).length > 0 },
    { key: 'valstats', label: 'PER/PBR 5년 통계', render: () => renderValStats(fundamental), hasData: !!fundamental.valuation_stats },
    { key: 'forward', label: '포워드 추정 (애널리스트)', render: () => renderForward(fundamental), hasData: !!fundamental.forward_estimates },
    { key: 'segments', label: '사업 개요/부문', render: () => renderSegments(fundamental), hasData: !!fundamental.business_description || (fundamental.segments || []).length > 0 },
    { key: 'tech', label: '기술적 시그널 (15분봉)', render: () => renderTechnical(technical), hasData: !!technical.indicators },
    { key: 'strategy', label: 'KIS 퀀트 신호', render: () => renderStrategy(strategySignals), hasData: !!strategySignals },
  ]

  // ── B. 리서치 데이터 카테고리 ──
  const researchCategories = [
    { key: 'basic_macro', label: '거시 경제 지표', render: () => renderBasicMacro(data?.basic_macro), hasData: !!data?.basic_macro?.macro },
    { key: 'valuation_band', label: '10년 밸류에이션 밴드 + 실적일', render: () => renderValuationBand(data?.valuation_band), hasData: !!data?.valuation_band?.valuation_stats || (data?.valuation_band?.earnings_dates || []).length > 0 },
    { key: 'management', label: '경영진 및 거버넌스', render: () => renderManagement(data?.management), hasData: (data?.management?.officers || []).length > 0 || (data?.management?.major_holders?.institutional || []).length > 0 },
    { key: 'capital_actions', label: '자본 변동 및 공시', render: () => renderCapitalActions(data?.capital_actions), hasData: (data?.capital_actions?.filings || []).length > 0 },
    { key: 'industry_peers', label: '업황 뉴스 및 경쟁 그룹', render: () => renderIndustryPeers(data?.industry_peers), hasData: (data?.industry_peers?.news || []).length > 0 },
  ]

  const advOkCount = advCategories.filter(c => c.hasData).length
  const researchOkCount = researchCategories.filter(c => c.hasData).length
  const totalOk = advOkCount + researchOkCount
  const totalCats = advCategories.length + researchCategories.length

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">AI분석 입력 데이터 (프롬프트 전체)</h3>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          {totalOk}/{totalCats} 항목 수집
        </span>
      </div>

      {/* A. 기존 분석 데이터 */}
      {hasAdv && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">기본 분석 데이터</span>
            <span className="text-[10px] text-gray-400">(새로고침으로 수집)</span>
            <span className="text-[10px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">{advOkCount}/{advCategories.length}</span>
          </div>
          <div className="space-y-1">
            {advCategories.map(cat => (
              <CategoryAccordion key={cat.key} label={cat.label} hasData={cat.hasData} render={cat.render} />
            ))}
          </div>
        </div>
      )}

      {/* B. 리서치 데이터 */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wide">심화 리서치 데이터</span>
          <span className="text-[10px] text-gray-400">(입력정보 획득으로 수집)</span>
          {hasResearch && <span className="text-[10px] bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded">{researchOkCount}/{researchCategories.length}</span>}
        </div>
        {!hasResearch ? (
          <p className="text-xs text-gray-400 italic pl-2">[입력정보 획득] 버튼을 눌러 심화 데이터를 수집하세요 (v3 분석에 사용됨)</p>
        ) : (
          <div className="space-y-1">
            {researchCategories.map(cat => (
              <CategoryAccordion key={cat.key} label={cat.label} hasData={cat.hasData} render={cat.render} />
            ))}
          </div>
        )}
      </div>

      {/* 수집 시각 */}
      <div className="mt-3 flex gap-4 text-[10px] text-gray-400">
        {advData?.updated_at && <span>기본분석: {advData.updated_at}</span>}
        {data?.collected_at && <span>리서치: {data.collected_at}</span>}
      </div>
    </div>
  )
}


// ── 아코디언 ──────────────────────────────────────────────────────────────

function CategoryAccordion({ label, hasData, render }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${hasData ? 'bg-green-400' : 'bg-gray-300'}`} />
          <span className="font-medium text-gray-700">{label}</span>
        </div>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs text-gray-600">
          {hasData ? render() : <p className="text-gray-400 italic">데이터 없음</p>}
        </div>
      )}
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════════
// A. 기존 분석 데이터 렌더러
// ══════════════════════════════════════════════════════════════════════════

function renderIncomeStmt(fundamental, market) {
  const income = fundamental.income_stmt || []
  const rows = income.slice(-3)
  if (!rows.length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b border-gray-200 text-gray-500">
          <th className="py-1 text-left">연도</th><th className="py-1 text-right">매출</th>
          <th className="py-1 text-right">영업이익</th><th className="py-1 text-right">순이익</th>
          <th className="py-1 text-right">영업이익률</th><th className="py-1 text-right">순이익률</th>
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-gray-50">
            <td className="py-1">{r.year}</td>
            <td className="py-1 text-right">{fmtShort(r.revenue)}</td>
            <td className="py-1 text-right">{fmtShort(r.operating_income)}</td>
            <td className="py-1 text-right">{fmtShort(r.net_income)}</td>
            <td className="py-1 text-right">{r.oi_margin != null ? `${r.oi_margin}%` : '-'}</td>
            <td className="py-1 text-right">{r.net_margin != null ? `${r.net_margin}%` : '-'}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function renderBalanceSheet(fundamental, market) {
  const bs = fundamental.balance_sheet || []
  const rows = bs.slice(-3)
  if (!rows.length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b border-gray-200 text-gray-500">
          <th className="py-1 text-left">연도</th><th className="py-1 text-right">총자산</th>
          <th className="py-1 text-right">총자본</th><th className="py-1 text-right">부채비율</th>
          <th className="py-1 text-right">유동비율</th>
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-gray-50">
            <td className="py-1">{r.year}</td>
            <td className="py-1 text-right">{fmtShort(r.total_assets)}</td>
            <td className="py-1 text-right">{fmtShort(r.total_equity)}</td>
            <td className="py-1 text-right">{r.debt_ratio != null ? `${r.debt_ratio}%` : '-'}</td>
            <td className="py-1 text-right">{r.current_ratio != null ? `${r.current_ratio}%` : '-'}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function renderCashflow(fundamental, market) {
  const cf = fundamental.cashflow || []
  const rows = cf.slice(-3)
  if (!rows.length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b border-gray-200 text-gray-500">
          <th className="py-1 text-left">연도</th><th className="py-1 text-right">영업CF</th>
          <th className="py-1 text-right">투자CF</th><th className="py-1 text-right">재무CF</th>
          <th className="py-1 text-right">FCF</th>
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-gray-50">
            <td className="py-1">{r.year}</td>
            <td className="py-1 text-right">{fmtShort(r.operating_cf)}</td>
            <td className="py-1 text-right">{fmtShort(r.investing_cf)}</td>
            <td className="py-1 text-right">{fmtShort(r.financing_cf)}</td>
            <td className={`py-1 text-right font-medium ${(r.free_cf || 0) >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
              {fmtShort(r.free_cf)}
            </td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function renderMetrics(fundamental) {
  const m = fundamental.metrics || {}
  if (!Object.keys(m).length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
      <MiniStat label="PER" value={m.per != null ? Number(m.per).toFixed(1) : null} />
      <MiniStat label="PBR" value={m.pbr != null ? Number(m.pbr).toFixed(2) : null} />
      <MiniStat label="ROE" value={m.roe != null ? `${Number(m.roe).toFixed(1)}%` : null} />
      <MiniStat label="PSR" value={m.psr != null ? Number(m.psr).toFixed(2) : null} />
      <MiniStat label="EV/EBITDA" value={m.ev_ebitda != null ? Number(m.ev_ebitda).toFixed(1) : null} />
      <MiniStat label="부채비율" value={m.debt_to_equity != null ? `${Number(m.debt_to_equity).toFixed(0)}%` : null} />
      <MiniStat label="유동비율" value={m.current_ratio != null ? `${Number(m.current_ratio).toFixed(0)}%` : null} />
      <MiniStat label="EPS" value={m.eps != null ? fmtNum(m.eps) : null} />
      <MiniStat label="Graham Number" value={m.graham_number != null ? fmtNum(m.graham_number) : null} />
      <MiniStat label="배당수익률" value={m.dividend_yield != null ? `${Number(m.dividend_yield).toFixed(2)}%` : null} />
    </div>
  )
}

function renderQuarterly(fundamental, market) {
  const q = fundamental.quarterly || []
  const rows = q.slice(-4)
  if (!rows.length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b border-gray-200 text-gray-500">
          <th className="py-1 text-left">분기</th><th className="py-1 text-right">매출</th>
          <th className="py-1 text-right">영업이익</th><th className="py-1 text-right">순이익</th>
          <th className="py-1 text-right">영업이익률</th>
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-gray-50">
            <td className="py-1">{r.year}Q{r.quarter}</td>
            <td className="py-1 text-right">{fmtShort(r.revenue)}</td>
            <td className="py-1 text-right">{fmtShort(r.operating_income)}</td>
            <td className="py-1 text-right">{fmtShort(r.net_income)}</td>
            <td className="py-1 text-right">{r.oi_margin != null ? `${r.oi_margin}%` : '-'}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function renderValStats(fundamental) {
  const vs = fundamental.valuation_stats || {}
  if (!vs.per_avg_5y && !vs.pbr_avg_5y) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
      <MiniStat label="PER 5Y 평균" value={vs.per_avg_5y?.toFixed(1)} />
      <MiniStat label="PER 최고" value={vs.per_max_5y?.toFixed(1)} />
      <MiniStat label="PER 최저" value={vs.per_min_5y?.toFixed(1)} />
      <MiniStat label="PER 현재" value={vs.per_current?.toFixed(1)} />
      <MiniStat label="PER 편차" value={vs.per_deviation_pct != null ? `${vs.per_deviation_pct.toFixed(0)}%` : null} />
      <MiniStat label="PBR 5Y 평균" value={vs.pbr_avg_5y?.toFixed(2)} />
      <MiniStat label="PBR 최고" value={vs.pbr_max_5y?.toFixed(2)} />
      <MiniStat label="PBR 최저" value={vs.pbr_min_5y?.toFixed(2)} />
      <MiniStat label="PBR 현재" value={vs.pbr_current?.toFixed(2)} />
      <MiniStat label="PBR 편차" value={vs.pbr_deviation_pct != null ? `${vs.pbr_deviation_pct.toFixed(0)}%` : null} />
    </div>
  )
}

function renderForward(fundamental) {
  const fwd = fundamental.forward_estimates || {}
  if (!Object.keys(fwd).length) return <p className="text-gray-400">데이터 없음 (해외 종목만 제공)</p>
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      <MiniStat label="Forward PE" value={fwd.forward_pe?.toFixed(1)} />
      <MiniStat label="Forward EPS" value={fwd.eps_forward?.toFixed(2)} />
      <MiniStat label="목표주가" value={fwd.target_mean_price ? fmtNum(fwd.target_mean_price) : null} />
      <MiniStat label="컨센서스" value={fwd.recommendation} />
      <MiniStat label="분석가 수" value={fwd.num_analysts} />
      <MiniStat label="현재 EPS" value={fwd.eps_current_year?.toFixed(2)} />
    </div>
  )
}

function renderSegments(fundamental) {
  const desc = fundamental.business_description
  const keywords = fundamental.business_keywords || []
  const segments = fundamental.segments || []
  if (!desc && !segments.length) return <p className="text-gray-400">데이터 없음</p>
  return (
    <div className="space-y-2">
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {keywords.map((k, i) => <span key={i} className="bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded text-[10px]">#{k}</span>)}
        </div>
      )}
      {desc && <p className="text-gray-700 text-xs leading-relaxed">{desc}</p>}
      {segments.length > 0 && (
        <div>
          {segments.map((s, i) => (
            <div key={i} className="flex justify-between py-0.5">
              <span>{s.name || s}</span>
              {s.ratio != null && <span className="text-gray-500">{s.ratio}%</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function renderTechnical(technical) {
  const ind = technical.indicators || {}
  const sig = ind.current_signals || {}
  if (!Object.keys(sig).length) return <p className="text-gray-400">데이터 없음</p>

  const macdLabel = { golden: '골든크로스', dead: '데드크로스', none: '크로스 없음' }[sig.macd_cross] || sig.macd_cross
  const rsiLabel = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[sig.rsi_signal] || sig.rsi_signal

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MiniStat label="MACD" value={macdLabel} />
        <MiniStat label="RSI (14)" value={sig.rsi_value != null ? `${Number(sig.rsi_value).toFixed(1)} (${rsiLabel})` : null} />
        <MiniStat label="Stochastic %K" value={sig.stoch_k != null ? Number(sig.stoch_k).toFixed(1) : null} />
        <MiniStat label="MA 배열" value={sig.ma_alignment || '혼합'} />
        <MiniStat label="현재가" value={sig.current_price != null ? fmtNum(sig.current_price) : null} />
        <MiniStat label="MA20" value={sig.ma20 != null ? fmtNum(sig.ma20) : null} />
        <MiniStat label="ATR" value={sig.atr != null ? Number(sig.atr).toFixed(1) : null} />
        <MiniStat label="BB 위치" value={sig.bb_position != null ? `${Number(sig.bb_position).toFixed(0)}%` : null} />
      </div>
      {/* 변동성 돌파 목표가 */}
      {(sig.volatility_target_k03 || sig.volatility_target_k05 || sig.volatility_target_k07) && (
        <div>
          <p className="text-gray-500 text-[10px] mb-1 mt-1">변동성 돌파 목표가</p>
          <div className="grid grid-cols-3 gap-2">
            <MiniStat label="K=0.3 (보수)" value={sig.volatility_target_k03 != null ? fmtNum(sig.volatility_target_k03) : null} />
            <MiniStat label="K=0.5 (표준)" value={sig.volatility_target_k05 != null ? fmtNum(sig.volatility_target_k05) : null} />
            <MiniStat label="K=0.7 (공격)" value={sig.volatility_target_k07 != null ? fmtNum(sig.volatility_target_k07) : null} />
          </div>
        </div>
      )}
      {/* 거래량 */}
      {sig.volume_signal && (
        <div className="grid grid-cols-3 gap-2">
          <MiniStat label="거래량 신호" value={typeof sig.volume_signal === 'object' ? JSON.stringify(sig.volume_signal) : sig.volume_signal} />
        </div>
      )}
    </div>
  )
}

function renderStrategy(strategySignals) {
  if (!strategySignals) return <p className="text-gray-400">MCP 비활성화 또는 미수집</p>
  const signals = strategySignals.signals || []
  const consensus = strategySignals.consensus
  return (
    <div className="space-y-2">
      {consensus && (
        <div className="flex items-center gap-2 mb-1">
          <span className="text-gray-500">합의:</span>
          <SignalBadge signal={consensus.signal} />
          <span className="text-gray-500 text-[10px]">강도: {consensus.strength?.toFixed(2)}</span>
        </div>
      )}
      {signals.map((s, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <span className="text-gray-700 text-xs w-32">{s.strategy || s.name}</span>
          <SignalBadge signal={s.signal} />
          <span className="text-gray-500 text-[10px]">강도: {s.strength?.toFixed(2)}</span>
        </div>
      ))}
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════════
// B. 리서치 데이터 렌더러 (기존 6카테고리)
// ══════════════════════════════════════════════════════════════════════════

function renderBasicMacro(data) {
  if (!data) return <p className="text-gray-400">데이터 없음</p>
  const macro = data.macro || {}
  return (
    <div className="space-y-2">
      {data.name && (
        <div className="flex gap-4 flex-wrap">
          <span>종목: <b>{data.name}</b> ({data.code})</span>
          {data.current_price != null && <span>현재가: <b>{fmtNum(data.current_price)}</b></span>}
          {data.market_cap != null && <span>시가총액: <b>{fmtCap(data.market_cap, data.market)}</b></span>}
        </div>
      )}
      <table className="w-full text-xs">
        <tbody>
          {macro.us_10y_yield != null && <Tr label="미국 10Y 국채" value={`${macro.us_10y_yield?.toFixed(2)}%`} />}
          {macro.gold != null && <Tr label="금(Gold)" value={`$${fmtNum(macro.gold)}/oz`} />}
          {macro.oil_wti != null && <Tr label="WTI 원유" value={`$${macro.oil_wti?.toFixed(2)}/bbl`} />}
          {macro.usd_krw != null && <Tr label="원/달러" value={`${fmtNum(macro.usd_krw)}원`} />}
          {macro.dollar_index != null && <Tr label="달러인덱스" value={macro.dollar_index?.toFixed(2)} />}
          {macro.vix != null && <Tr label="VIX" value={macro.vix?.toFixed(2)} />}
        </tbody>
      </table>
    </div>
  )
}

function renderValuationBand(data) {
  if (!data) return <p className="text-gray-400">데이터 없음</p>
  const vs = data.valuation_stats || {}
  const ed = data.earnings_dates || []
  return (
    <div className="space-y-3">
      {vs.per_avg_5y != null && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <MiniStat label="PER 평균" value={vs.per_avg_5y?.toFixed(1)} />
          <MiniStat label="PER 현재" value={vs.per_current?.toFixed(1)} />
          <MiniStat label="PBR 평균" value={vs.pbr_avg_5y?.toFixed(2)} />
          <MiniStat label="PBR 현재" value={vs.pbr_current?.toFixed(2)} />
        </div>
      )}
      {ed.length > 0 && (
        <div>
          <p className="font-medium text-gray-700 mb-1">최근 실적 발표</p>
          {ed.slice(0, 6).map((e, i) => (
            <div key={i} className="flex gap-3 py-0.5">
              <span className="text-gray-500">{e.date}</span>
              <span>예상: {e.eps_estimate ?? '-'}</span>
              <span>실제: {e.eps_actual ?? '-'}</span>
              {e.surprise_pct != null && (
                <span className={e.surprise_pct >= 0 ? 'text-red-500' : 'text-blue-500'}>
                  {e.surprise_pct > 0 ? '+' : ''}{e.surprise_pct}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function renderManagement(data) {
  if (!data) return <p className="text-gray-400">데이터 없음</p>
  const officers = data.officers || []
  const inst = (data.major_holders || {}).institutional || []
  if (!officers.length && !inst.length) return <p className="text-gray-400 italic">경영진/주주 정보 없음 (국내 종목은 제한적)</p>
  return (
    <div className="space-y-3">
      {officers.length > 0 && (
        <div>{officers.slice(0, 5).map((o, i) => (
          <div key={i} className="py-0.5">
            <span className="font-medium">{o.name}</span>
            <span className="text-gray-500 ml-2">{o.title}</span>
          </div>
        ))}</div>
      )}
      {inst.length > 0 && (
        <div>
          <p className="font-medium text-gray-700 mb-1">주요 기관</p>
          {inst.slice(0, 5).map((h, i) => (
            <div key={i} className="flex justify-between py-0.5">
              <span>{h.holder}</span>
              <span className="text-gray-500">{h.pct_held != null ? `${(h.pct_held * 100).toFixed(1)}%` : '-'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function renderCapitalActions(data) {
  if (!data) return <p className="text-gray-400">데이터 없음</p>
  const filings = data.filings || []
  if (!filings.length) return <p className="text-gray-400">최근 1년 공시 없음</p>
  return (
    <div className="space-y-1">
      {filings.slice(0, 10).map((f, i) => (
        <div key={i} className="flex gap-3 py-0.5">
          <span className="text-gray-500 shrink-0">{f.rcept_dt}</span>
          <span className="truncate">{f.report_name || f.report_type || '-'}</span>
        </div>
      ))}
    </div>
  )
}

function renderIndustryPeers(data) {
  if (!data) return <p className="text-gray-400">데이터 없음</p>
  const news = data.news || []
  const sector = data.sector || ''
  const industry = data.industry || ''
  return (
    <div className="space-y-3">
      {(sector || industry) && (
        <div className="flex gap-3">
          {sector && <span className="bg-gray-100 px-2 py-0.5 rounded">{sector}</span>}
          {industry && <span className="bg-gray-100 px-2 py-0.5 rounded">{industry}</span>}
        </div>
      )}
      {news.length > 0 && (
        <div>
          {news.slice(0, 8).map((n, i) => (
            <div key={i} className="py-0.5">
              {n.link ? (
                <a href={n.link} target="_blank" rel="noopener noreferrer" className="hover:text-blue-600">
                  {n.source && <span className="text-gray-400 mr-1">[{n.source}]</span>}
                  {n.title}
                </a>
              ) : <span>{n.title}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════════
// 공통 유틸 컴포넌트
// ══════════════════════════════════════════════════════════════════════════

function Tr({ label, value }) {
  return (
    <tr className="border-b border-gray-50">
      <td className="py-1 text-gray-500 pr-4">{label}</td>
      <td className="py-1 text-right font-medium">{value}</td>
    </tr>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="bg-gray-50 rounded p-1.5">
      <div className="text-gray-500 text-[10px]">{label}</div>
      <div className="font-medium">{value ?? '-'}</div>
    </div>
  )
}

function SignalBadge({ signal }) {
  const colors = {
    BUY: 'bg-red-100 text-red-700',
    SELL: 'bg-blue-100 text-blue-700',
    HOLD: 'bg-gray-100 text-gray-700',
  }
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${colors[signal] || 'bg-gray-100 text-gray-600'}`}>
      {signal || '-'}
    </span>
  )
}

function fmtNum(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('ko-KR', { maximumFractionDigits: 0 })
}

function fmtCap(v, market) {
  if (v == null) return '-'
  if (market === 'KR') {
    const eok = v / 1e8
    if (eok >= 10000) return `${(eok / 10000).toFixed(1)}조`
    return `${Math.floor(eok).toLocaleString()}억`
  }
  const m = v / 1e6
  if (m >= 1000) return `$${(m / 1000).toFixed(1)}B`
  return `$${Math.floor(m).toLocaleString()}M`
}

function fmtShort(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  if (abs >= 1e12) return `${(v / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`
  if (abs >= 1e8) return `${(v / 1e8).toFixed(0)}억`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(0)}M`
  return v.toLocaleString()
}
