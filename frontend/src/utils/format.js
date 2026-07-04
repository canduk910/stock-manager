/**
 * 공용 표시 포맷터 — 메뉴 간 중복 정의 통합 (2026-07-04 refactor F-2).
 *
 * 표기 차이는 옵션 인자로 보존한다:
 *   - formatPct: digits(백테스트 이력=1, 그 외=2), signed(외국인 보유율=false)
 *   - formatDate: Intl 옵션 그대로 전달 (연도 포함 여부 등 화면별 유지)
 */

/** 퍼센트. signed=true면 0 이상에 '+' 접두. null/NaN → '-'. */
export function formatPct(val, { digits = 2, signed = true } = {}) {
  if (val == null) return '-'
  const n = Number(val)
  if (Number.isNaN(n)) return '-'
  const sign = signed && n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(digits)}%`
}

/** 억원 단위 순매수 금액. 부호(+/-) + 천단위 콤마 + '억'. null → '-'. */
export function formatAmount(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  return `${sign}${abs.toLocaleString()}억`
}

/** ko-KR 천단위 콤마 숫자. null/NaN → '-'. */
export function formatNumber(val) {
  if (val == null) return '-'
  const n = Number(val)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('ko-KR')
}

const _DATE_DEFAULT_OPTS = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
}

/** ISO → ko-KR 일시. Intl 옵션으로 화면별 표기 유지. 파싱 실패 시 원문 반환. */
export function formatDate(iso, opts = _DATE_DEFAULT_OPTS) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR', opts)
}

/**
 * 수급 투자자 색상 표준 (MacroSentinel/OrderAdvisor 자문) — 응답 color_map 부재 시 fallback.
 * 개인 #EF4444 / 외국인 #3B82F6 / 기관 #10B981.
 */
export const INVESTOR_COLORS = {
  personal: '#EF4444',
  foreign: '#3B82F6',
  institution: '#10B981',
}
