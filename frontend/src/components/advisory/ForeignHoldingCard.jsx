/**
 * 종목 외국인 보유 추이 + 매수여력 카드 (REQ-FH-UI-01 / REQ-FH-EXT-UI-01).
 *
 * V1.5 → V1.6 확장:
 *  - 슬라이더 5단계 stepper (30/60/90/120/180일), 기본 120일 (MacroSentinel 권장).
 *  - x축 자동 포맷: 60일 이하 = MM-DD / 90일 이상 = YYYY-MM(격주 솎기).
 *  - 보조 텍스트: "{days}일 변화: {first}% → {last}% (±{delta}%p)".
 *  - 누적 안내: 응답 daily_history_total_days < days 시 "데이터 누적 중 N/M일".
 *  - change_alert.breached === true 시 노란 강조 텍스트 + 차트 라인 색 변경.
 *
 * 부서장 결정 안 (A): 좌(도넛 게이지 스냅샷) + 우(보유율 추이 라인) 2컬럼.
 * 도메인 자문 합의:
 *  - MacroSentinel: 4단계 임계값 색상 (50/80/95) + 5단계 stepper + ±3.0%p 알림
 *  - MarginAnalyst: 한도 미설정/한도 초과 처리, 양면성 advisory_note, 누적 250일 cap
 *  - OrderAdvisor: 음수 보호(잔여여력 max 0 — 서비스에서 처리), 한도 초과 배지, 매매 액션 키 부재
 *
 * 색상 표준:
 *  - 외국인 라인 = #3B82F6 기본 / #F97316 강조(change_alert.breached)
 *  - 한도 라인 = #9CA3AF 회색 점선
 *  - 4단계 = #9CA3AF/#FBBF24/#F97316/#EF4444 (회색/노랑/주황/빨강)
 *
 * advisory_note 중복 표시 금지 — V1 SupplyDemandPanel이 이미 통일된 문구로 노출.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine, Legend,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import { useForeignHolding } from '../../hooks/useAdvisory'

const STATUS_COLORS = {
  safe: '#9CA3AF',
  caution: '#FBBF24',
  warning: '#F97316',
  saturated: '#EF4444',
  unlimited: '#9CA3AF',
  exceeded: '#EF4444',
}

const STATUS_LABELS = {
  safe: '안전 (<50%)',
  caution: '주의 (50~80%)',
  warning: '경계 (80~95%)',
  saturated: '포화 (≥95%)',
  unlimited: '한도 미설정',
  exceeded: '한도 초과 보유',
}

const STATUS_BG = {
  safe: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  caution: 'bg-amber-50 text-amber-800 border-amber-200',
  warning: 'bg-orange-50 text-orange-800 border-orange-200',
  saturated: 'bg-rose-50 text-rose-800 border-rose-200',
  unlimited: 'bg-gray-50 text-gray-700 border-gray-200',
  exceeded: 'bg-rose-50 text-rose-800 border-rose-200',
}

// REQ-FH-EXT-UI-01: 5단계 stepper. 기본 120 (사용자 요구 "반년").
const DAYS_STEPS = [30, 60, 90, 120, 180]
const DAYS_DEFAULT = 120

function formatMan(v) {
  if (v == null) return '-'
  return `${Number(v).toLocaleString()}만주`
}

function formatPct(v, digits = 2) {
  if (v == null) return '-'
  return `${Number(v).toFixed(digits)}%`
}

/** SVG 도넛 게이지. percent 0~100. status에 따라 색상. */
function DonutGauge({ percent, status }) {
  const isDisabled = status === 'unlimited'
  const value = isDisabled ? 0 : Math.max(0, Math.min(100, percent ?? 0))
  const color = STATUS_COLORS[status] || '#9CA3AF'

  const size = 180
  const stroke = 18
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - value / 100)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={stroke}
          strokeDasharray={isDisabled ? '4 6' : undefined}
        />
        {!isDisabled && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {isDisabled ? (
          <span className="text-sm text-gray-500">한도 미설정</span>
        ) : (
          <>
            <span className="text-2xl font-bold tabular-nums" style={{ color }}>
              {formatPct(percent)}
            </span>
            <span className="text-xs text-gray-500 mt-0.5">소진율</span>
          </>
        )}
      </div>
    </div>
  )
}

function LineTooltip({ active, payload, label }) {
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
            {p.value != null ? `${Number(p.value).toFixed(2)}%` : '-'}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * 5단계 stepper. 선택 시 onChange(value) 호출.
 * 모바일/데스크톱 동일 UI.
 */
function DaysStepper({ value, onChange, disabled = false }) {
  return (
    <div className="inline-flex border border-gray-300 rounded overflow-hidden text-sm">
      {DAYS_STEPS.map((d, i) => {
        const active = d === value
        return (
          <button
            key={d}
            type="button"
            disabled={disabled}
            onClick={() => onChange(d)}
            className={
              (active
                ? 'bg-blue-600 text-white font-medium'
                : 'bg-white text-gray-700 hover:bg-gray-50') +
              ' px-2.5 py-1 tabular-nums' +
              (i > 0 ? ' border-l border-gray-300' : '') +
              (disabled ? ' opacity-50 cursor-not-allowed' : '')
            }
          >
            {d}일
          </button>
        )
      })}
    </div>
  )
}

export default function ForeignHoldingCard({ code, market = 'KR' }) {
  const [days, setDays] = useState(DAYS_DEFAULT)
  const { data, loading, error, load } = useForeignHolding()

  const isDomestic = (market || 'KR').toUpperCase() === 'KR'

  useEffect(() => {
    if (code && isDomestic) {
      load(code, days)
    }
  }, [code, days, isDomestic, load])

  const snap = data?.snapshot
  const status = snap?.limit_status || 'safe'

  // 라인 차트 데이터 + x축 포맷 분기
  const { chartData, xTickFormatter, xInterval } = useMemo(() => {
    if (!data?.daily) {
      return { chartData: [], xTickFormatter: (v) => v, xInterval: 'preserveStartEnd' }
    }
    // 60일 이하 = MM-DD 매일 (V1.5 동일)
    // 90일 이상 = YYYY-MM 격자 솎기 (MacroSentinel 권장)
    const longMode = days >= 90
    const fmt = longMode
      ? (d) => (d ? d.slice(0, 7) : '')   // YYYY-MM
      : (d) => (d ? d.slice(5) : '')      // MM-DD
    const interval = longMode
      ? Math.max(1, Math.floor(data.daily.length / 10))
      : Math.max(0, Math.floor(data.daily.length / 12))
    return {
      chartData: data.daily.map((d) => ({
        date: d.date,                 // 풀 YYYY-MM-DD (raw)
        ehrt: d.frgn_ehrt_pct,
      })),
      xTickFormatter: fmt,
      xInterval: interval || 0,
    }
  }, [data, days])

  // change_alert 응답 객체 (없으면 보조 텍스트만)
  const changeAlert = data?.change_alert || null
  const breached = !!(changeAlert && changeAlert.breached)

  // 누적 안내
  const historyTotal = data?.daily_history_total_days ?? null
  const showAccumulating = historyTotal != null && historyTotal < days

  // 라인 색상 — breached 시 강조
  const lineColor = breached ? '#F97316' : (data?.color_map?.foreign || '#3B82F6')

  if (!isDomestic) {
    return null
  }

  const isKisMissing = error?.status === 503
  const isExternalFail = error?.status === 502
  const isNotFound = error?.status === 404
  const isClientError = error?.status === 400
  const isOtherError = error && !isKisMissing && !isExternalFail && !isNotFound && !isClientError

  return (
    <div className="mt-5 border-t pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            외국인 보유 추이 + 매수여력
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {data?.as_of ? `${data.as_of} 기준` : ''} · 단위: 만주, % (소수점 2자리)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">기간</label>
          <DaysStepper value={days} onChange={setDays} disabled={loading} />
        </div>
      </div>

      {/* 부분 실패 격리 */}
      {isKisMissing && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800">
          외국인 보유 데이터는 KIS API 키 설정이 필요합니다. /settings/kis 에서 등록하세요.
        </div>
      )}
      {isExternalFail && (
        <div className="bg-rose-50 border border-rose-200 rounded p-3 text-sm text-rose-800">
          외국인 보유 데이터 일시 미수집. 잠시 후 다시 시도해주세요.
        </div>
      )}
      {isNotFound && (
        <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700">
          외국인 보유 데이터를 제공하지 않는 종목입니다.
        </div>
      )}
      {isClientError && (
        <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700">
          {error?.message || '잘못된 요청입니다.'}
        </div>
      )}
      {isOtherError && (
        <div className="bg-rose-50 border border-rose-200 rounded p-3 text-sm text-rose-800">
          외국인 보유 데이터를 불러올 수 없습니다.
        </div>
      )}

      {loading && <LoadingSpinner message="외국인 보유 데이터 로딩 중..." />}

      {!loading && !error && snap && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* 좌: 스냅샷 + 도넛 게이지 */}
          <div className="border border-gray-200 rounded p-4 bg-white relative">
            <span
              className={`absolute top-3 right-3 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_BG[status] || STATUS_BG.safe}`}
            >
              {STATUS_LABELS[status] || status}
            </span>

            <div className="flex justify-center mb-4">
              <DonutGauge percent={snap.frgn_ehrt_pct} status={status} />
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div>
                <div className="text-xs text-gray-500">보유 수량</div>
                <div className="font-medium tabular-nums">
                  {formatMan(snap.frgn_hldn_man)}
                  {snap.frgn_holding_pct != null && (
                    <span className="text-xs text-gray-500 ml-1">
                      (보유율 {formatPct(snap.frgn_holding_pct)})
                    </span>
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">상장 주수</div>
                <div className="font-medium tabular-nums">
                  {formatMan(snap.lstn_stcn_man)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">한도 수량</div>
                <div className="font-medium tabular-nums">
                  {snap.is_limit_unset ? (
                    <span className="text-gray-500">한도 미설정</span>
                  ) : (
                    formatMan(snap.frgn_limit_man)
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">잔여 매수여력</div>
                <div className="font-medium tabular-nums">
                  {status === 'unlimited' ? (
                    <span className="text-gray-500">-</span>
                  ) : snap.is_exceeded ? (
                    <span className="text-rose-700">0 (한도 초과)</span>
                  ) : (
                    <>
                      {formatMan(snap.frgn_remaining_man)}
                      {snap.frgn_remaining_pct_of_limit != null && (
                        <span className="text-xs text-gray-500 ml-1">
                          (한도 대비 {formatPct(snap.frgn_remaining_pct_of_limit)})
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {status === 'saturated' && (
              <div className="mt-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">
                한도 ≥95%는 외국인 매도 시 단방향 가격 충격 위험이 있습니다(MarginAnalyst).
              </div>
            )}
          </div>

          {/* 우: 라인 차트 (보유율 추이) */}
          <div className="border border-gray-200 rounded p-4 bg-white">
            <div className="flex items-start justify-between mb-2 gap-2">
              <h4 className="text-sm font-semibold text-gray-900">소진율 추이</h4>
              {/* 보조 텍스트: change_alert 우선, 없으면 V1.5 단순 텍스트 */}
              {changeAlert ? (
                <div className="text-right">
                  <div className={`text-xs ${breached ? 'text-amber-700 font-medium' : 'text-gray-600'}`}>
                    {breached ? (
                      <>
                        최근 {days}일 외국인 보유율{' '}
                        <span className="inline-block px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold mx-0.5">
                          {changeAlert.signed_change_pct_point > 0 ? '+' : ''}
                          {Number(changeAlert.signed_change_pct_point).toFixed(2)}%p
                        </span>{' '}
                        {changeAlert.signed_change_pct_point > 0 ? '급증' : '급감'} (정상 범위 ±{changeAlert.threshold_pct_point}%p)
                      </>
                    ) : (
                      <>
                        {days}일 변화: {formatPct(changeAlert.first_ehrt_pct)} → {formatPct(changeAlert.last_ehrt_pct)} (
                        <span className={changeAlert.signed_change_pct_point >= 0 ? 'text-blue-600' : 'text-gray-500'}>
                          {changeAlert.signed_change_pct_point >= 0 ? '+' : ''}
                          {Number(changeAlert.signed_change_pct_point).toFixed(2)}%p
                        </span>
                        )
                      </>
                    )}
                  </div>
                </div>
              ) : null}
            </div>

            {/* 누적 안내 — 데이터 부족 시 */}
            {showAccumulating && (
              <div className="mb-2 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded px-2 py-1">
                데이터 누적 중: {historyTotal} / {days}일. 매일 자동 채워집니다.
              </div>
            )}

            {chartData.length === 0 ? (
              <div className="text-sm text-gray-500 py-6 text-center">
                표시할 시계열 데이터가 없습니다.
              </div>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={chartData}
                    margin={{ top: 8, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickFormatter={xTickFormatter}
                      interval={xInterval}
                      minTickGap={20}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      domain={[
                        (dataMin) => Math.max(0, Math.floor(dataMin - 2)),
                        (dataMax) => Math.min(100, Math.ceil(dataMax + 2)),
                      ]}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip
                      content={<LineTooltip />}
                      labelFormatter={(label) => label || ''}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {/* 4임계 ReferenceLine */}
                    <ReferenceLine y={50} stroke="#FBBF24" strokeDasharray="4 4" />
                    <ReferenceLine y={80} stroke="#F97316" strokeDasharray="4 4" />
                    <ReferenceLine y={95} stroke="#EF4444" strokeDasharray="4 4" />
                    {/* 한도 라인(100%) — unlimited 시 미렌더 */}
                    {!snap.is_limit_unset && (
                      <ReferenceLine
                        y={100}
                        stroke="#9CA3AF"
                        strokeDasharray="5 5"
                        label={{ value: '한도', position: 'right', fontSize: 10, fill: '#6b7280' }}
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="ehrt"
                      name="외국인 소진율"
                      stroke={lineColor}
                      strokeWidth={breached ? 2.5 : 2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
