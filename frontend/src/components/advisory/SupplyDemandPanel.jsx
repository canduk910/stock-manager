/**
 * 종목 상세 — 수급/투자자 서브탭 패널.
 * REQ-SUPPLY-UI-02.
 *
 * 자문 근거:
 *   - OrderAdvisor: V1은 표시만, advisory_note 노란 배너 고지, 단독 시그널 금지(Graham)
 *   - 색상 표준: 개인 #EF4444 / 외국인 #3B82F6 / 기관 #10B981
 *   - 매수/매도 분리 토글: 분리 모드에서는 매수=양수/매도=음수 막대
 *   - 부분 실패 격리: 503/502 시 패널 내부 안내, 다른 서브탭 정상
 *   - 외국인 보유비율 추이는 미포함(V2)
 *   - 매매 액션 키 없음(응답 키도 부재 — 백엔드에서 차단됨)
 */
import { useEffect, useState, useMemo } from 'react'
import {
  ResponsiveContainer, ComposedChart,
  Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ReferenceLine,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import { useStockSupplyDemand } from '../../hooks/useAdvisory'
import ForeignHoldingCard from './ForeignHoldingCard'

function formatAmount(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  return `${sign}${abs.toLocaleString()}억`
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded shadow-lg p-2 text-xs">
      <div className="font-medium text-gray-900 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block w-2 h-2 rounded-sm"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-gray-700">{p.name}</span>
          <span className="ml-auto font-medium tabular-nums">
            {p.value?.toLocaleString()}억
          </span>
        </div>
      ))}
    </div>
  )
}

export default function SupplyDemandPanel({ code, market = 'KR' }) {
  const [days, setDays] = useState(30)
  // 'net' = 순매수 / 'split' = 매수·매도 분리
  const [mode, setMode] = useState('net')
  const { data, loading, error, load } = useStockSupplyDemand()

  // 국내 종목만 지원 — 해외 종목 진입 시 안내
  const isDomesticMarket = (market || 'KR').toUpperCase() === 'KR'

  useEffect(() => {
    if (code && isDomesticMarket) {
      load(code, days)
    }
  }, [code, days, isDomesticMarket, load])

  const isKisMissing = error?.status === 503
  const isExternalFail = error?.status === 502
  const isNotFound = error?.status === 404
  const isClientError = error?.status === 400
  const isOtherError = error && !isKisMissing && !isExternalFail && !isNotFound && !isClientError

  const cm = data?.color_map || {
    personal: '#EF4444', foreign: '#3B82F6', institution: '#10B981',
  }

  const chartData = useMemo(() => {
    if (!data?.daily) return []
    return data.daily.map((d, i) => {
      const c = data.cumulative?.[i] || {}
      // 매수/매도 분리 모드: sell은 음수 처리(차트에서 아래로 표시)
      return {
        date: (d.date || '').slice(5),
        fullDate: d.date,
        // 순매수
        personal_net: d.personal_net,
        foreign_net: d.foreign_net,
        institution_net: d.institution_net,
        // 매수/매도 분리 (매수=양수, 매도=음수)
        personal_buy: d.personal_buy,
        personal_sell: d.personal_sell != null ? -d.personal_sell : null,
        foreign_buy: d.foreign_buy,
        foreign_sell: d.foreign_sell != null ? -d.foreign_sell : null,
        institution_buy: d.institution_buy,
        institution_sell: d.institution_sell != null ? -d.institution_sell : null,
        // 누적
        personal_cum: c.personal_cum,
        foreign_cum: c.foreign_cum,
        institution_cum: c.institution_cum,
      }
    })
  }, [data])

  if (!isDomesticMarket) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded p-4 text-sm text-amber-800">
        수급/투자자 분석은 국내(KR) 종목만 지원합니다.
      </div>
    )
  }

  return (
    <div>
      {/* OrderAdvisor 자문 — 안전 고지 배너 (응답 advisory_note 표시) */}
      {data?.advisory_note && (
        <div className="bg-amber-50 border border-amber-200 rounded p-2.5 mb-3 text-sm text-amber-900">
          <span className="font-semibold mr-1">고지:</span>
          {data.advisory_note}
        </div>
      )}

      {/* 컨트롤 바 */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="text-sm text-gray-600">
          {data?.name ? `${data.name}(${data.code})` : code} · {data?.as_of || '-'} 기준
          <span className="ml-2 text-xs text-gray-500">(단위: 억원)</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* 매수/매도 분리 토글 */}
          <div className="inline-flex gap-1">
            <button
              type="button"
              onClick={() => setMode('net')}
              className={`px-3 py-1.5 rounded text-sm font-medium ${
                mode === 'net'
                  ? 'bg-gray-900 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              순매수
            </button>
            <button
              type="button"
              onClick={() => setMode('split')}
              className={`px-3 py-1.5 rounded text-sm font-medium ${
                mode === 'split'
                  ? 'bg-gray-900 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              매수·매도 분리
            </button>
          </div>

          {/* 기간 슬라이더 */}
          <div className="flex items-center gap-2 text-sm">
            <label className="text-gray-600">기간</label>
            <input
              type="range"
              min={10}
              max={60}
              step={5}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-gray-900 font-medium tabular-nums w-12">
              {days}일
            </span>
          </div>
        </div>
      </div>

      {/* 당일 요약 */}
      {data?.summary && (
        <div className="px-3 py-2 bg-gray-50 rounded text-sm mb-3 flex flex-wrap gap-3">
          <span style={{ color: cm.foreign }}>
            외국인 {formatAmount(data.summary.foreign_today)}
          </span>
          <span className="text-gray-300">/</span>
          <span style={{ color: cm.institution }}>
            기관 {formatAmount(data.summary.institution_today)}
          </span>
          <span className="text-gray-300">/</span>
          <span style={{ color: cm.personal }}>
            개인 {formatAmount(data.summary.personal_today)}
          </span>
          <span className="ml-auto text-gray-500 text-xs">
            누적 외국인 {formatAmount(data.summary.foreign_cum_total)} ·
            기관 {formatAmount(data.summary.institution_cum_total)} ·
            개인 {formatAmount(data.summary.personal_cum_total)}
          </span>
        </div>
      )}

      {/* 부분 실패 안내 */}
      {isKisMissing && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800">
          수급 데이터는 KIS API 키 설정이 필요합니다. /settings/kis 에서 등록하세요.
        </div>
      )}
      {isExternalFail && (
        <div className="bg-rose-50 border border-rose-200 rounded p-3 text-sm text-rose-800">
          KIS API 호출에 실패했습니다. 잠시 후 다시 시도해주세요.
        </div>
      )}
      {isNotFound && (
        <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700">
          해당 종목의 수급 데이터를 찾을 수 없습니다.
        </div>
      )}
      {isClientError && (
        <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700">
          {error?.message || '잘못된 요청입니다.'}
        </div>
      )}
      {isOtherError && (
        <div className="bg-rose-50 border border-rose-200 rounded p-3 text-sm text-rose-800">
          수급 데이터를 불러올 수 없습니다.
        </div>
      )}

      {loading && <LoadingSpinner message="수급 데이터 로딩 중..." />}

      {!loading && !error && chartData.length > 0 && (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => v?.toLocaleString()}
                label={{ value: '일별(억)', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#6b7280' }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => v?.toLocaleString()}
                label={{ value: '누적(억)', angle: 90, position: 'insideRight', fontSize: 11, fill: '#6b7280' }}
              />
              <Tooltip
                content={<ChartTooltip />}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.fullDate || ''}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine yAxisId="left" y={0} stroke="#9ca3af" strokeWidth={1} />

              {mode === 'net' ? (
                <>
                  <Bar yAxisId="left" dataKey="personal_net" name="개인" fill={cm.personal} opacity={0.55} />
                  <Bar yAxisId="left" dataKey="foreign_net" name="외국인" fill={cm.foreign} opacity={0.55} />
                  <Bar yAxisId="left" dataKey="institution_net" name="기관" fill={cm.institution} opacity={0.55} />
                </>
              ) : (
                <>
                  <Bar yAxisId="left" dataKey="personal_buy" name="개인 매수" fill={cm.personal} opacity={0.7} />
                  <Bar yAxisId="left" dataKey="personal_sell" name="개인 매도" fill={cm.personal} opacity={0.35} />
                  <Bar yAxisId="left" dataKey="foreign_buy" name="외국인 매수" fill={cm.foreign} opacity={0.7} />
                  <Bar yAxisId="left" dataKey="foreign_sell" name="외국인 매도" fill={cm.foreign} opacity={0.35} />
                  <Bar yAxisId="left" dataKey="institution_buy" name="기관 매수" fill={cm.institution} opacity={0.7} />
                  <Bar yAxisId="left" dataKey="institution_sell" name="기관 매도" fill={cm.institution} opacity={0.35} />
                </>
              )}

              {/* 누적 라인 (mode와 무관하게 항상 표시) */}
              <Line yAxisId="right" type="monotone" dataKey="personal_cum" name="개인(누적)" stroke={cm.personal} strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="foreign_cum" name="외국인(누적)" stroke={cm.foreign} strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="institution_cum" name="기관(누적)" stroke={cm.institution} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {!loading && !error && chartData.length === 0 && (
        <div className="text-sm text-gray-500 py-6 text-center">
          표시할 수급 데이터가 없습니다.
        </div>
      )}

      {/* REQ-FH-UI-01: 외국인 보유 추이 + 매수여력 카드 (V1 차트 하단) */}
      <ForeignHoldingCard code={code} market={market} />
    </div>
  )
}
