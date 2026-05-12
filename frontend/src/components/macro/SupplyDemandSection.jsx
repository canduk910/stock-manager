/**
 * 매크로 페이지 — 시장(KOSPI/KOSDAQ) 일별 수급 + 누적 추세.
 * REQ-SUPPLY-UI-01.
 *
 * 자문 근거:
 *   - MacroSentinel: 억원, 20일 기본(10~60), Graham 보조지표
 *   - 색상 표준: 개인 #EF4444 / 외국인 #3B82F6 / 기관 #10B981 (응답 color_map)
 *   - 부분 실패 격리: KIS 키 미설정/외부 API 실패 시 카드 내부 안내, 다른 매크로 섹션 정상
 *   - 매매 액션 키 없음 (V1은 표시만, OrderAdvisor 자문)
 */
import { useEffect, useState, useMemo } from 'react'
import {
  ResponsiveContainer, ComposedChart,
  Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ReferenceLine,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import { useSupplyDemand } from '../../hooks/useMacro'

const MARKETS = [
  { id: 'kospi', label: '코스피' },
  { id: 'kosdaq', label: '코스닥' },
]

function formatAmount(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  return `${sign}${abs.toLocaleString()}억`
}

function ToggleButton({ id, active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={() => onClick(id)}
      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
        active
          ? 'bg-gray-900 text-white'
          : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
      }`}
    >
      {children}
    </button>
  )
}

function SummaryChip({ data, colorMap }) {
  if (!data) return null
  const personal = data.personal_today
  const foreign = data.foreign_today
  const inst = data.institution_today

  const colorOf = (v, key) => (v === 0 ? '#6b7280' : colorMap?.[key] || '#374151')

  return (
    <div className="text-sm text-gray-700 flex flex-wrap gap-3">
      <span style={{ color: colorOf(foreign, 'foreign') }}>
        외국인 {formatAmount(foreign)}
      </span>
      <span className="text-gray-300">/</span>
      <span style={{ color: colorOf(inst, 'institution') }}>
        기관 {formatAmount(inst)}
      </span>
      <span className="text-gray-300">/</span>
      <span style={{ color: colorOf(personal, 'personal') }}>
        개인 {formatAmount(personal)}
      </span>
    </div>
  )
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

export default function SupplyDemandSection() {
  const [market, setMarket] = useState('kospi')
  const [days, setDays] = useState(20)
  const { data, loading, error, load } = useSupplyDemand()

  // 부분 실패 격리: 자기 카드 안에서만 fetch + 안내
  useEffect(() => {
    load(market, days)
  }, [market, days, load])

  const chartData = useMemo(() => {
    if (!data?.daily) return []
    return data.daily.map((d, i) => {
      const c = data.cumulative?.[i] || {}
      // x축은 MM-DD(끝 5자), 툴팁용 원본 date도 함께
      return {
        date: (d.date || '').slice(5),
        fullDate: d.date,
        personal_net: d.personal_net,
        foreign_net: d.foreign_net,
        institution_net: d.institution_net,
        personal_cum: c.personal_cum,
        foreign_cum: c.foreign_cum,
        institution_cum: c.institution_cum,
      }
    })
  }, [data])

  // KIS 키 미설정 / 외부 API 실패 안내
  const isKisMissing = error?.status === 503
  const isExternalFail = error?.status === 502
  const isOtherError = error && !isKisMissing && !isExternalFail

  const cm = data?.color_map || {
    personal: '#EF4444', foreign: '#3B82F6', institution: '#10B981',
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="text-lg font-semibold text-gray-900">
          개인/외국인/기관 수급
          <span className="ml-2 text-xs text-gray-500 font-normal">
            (일별 막대 + 누적 추세, 단위: 억원)
          </span>
        </h2>

        <div className="flex items-center gap-3">
          {/* 시장 토글 */}
          <div className="inline-flex gap-1">
            {MARKETS.map((m) => (
              <ToggleButton
                key={m.id}
                id={m.id}
                active={market === m.id}
                onClick={setMarket}
              >
                {m.label}
              </ToggleButton>
            ))}
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

      {/* 당일 요약 칩 */}
      {data?.summary && (
        <div className="mb-3 px-3 py-2 bg-gray-50 rounded text-sm">
          <span className="text-gray-500 mr-2">{data.as_of} 당일:</span>
          <SummaryChip data={data.summary} colorMap={cm} />
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

              {/* 일별 막대 */}
              <Bar yAxisId="left" dataKey="personal_net" name="개인(일별)" fill={cm.personal} opacity={0.55} />
              <Bar yAxisId="left" dataKey="foreign_net" name="외국인(일별)" fill={cm.foreign} opacity={0.55} />
              <Bar yAxisId="left" dataKey="institution_net" name="기관(일별)" fill={cm.institution} opacity={0.55} />

              {/* 누적 라인 */}
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
    </div>
  )
}
