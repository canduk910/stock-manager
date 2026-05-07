/**
 * UserCommentInput — AI 분석 전 사용자 가설/의견 입력 (2026-05-07).
 *
 * Props:
 *   value: string             — 컨트롤드 값
 *   onChange: (text) => void  — 값 변경 콜백 (raw 문자열)
 *   disabled?: boolean        — 입력 비활성화 (분석 중)
 *   compact?: boolean         — 간략 레이아웃 (포트폴리오 자문용)
 *   placeholder?: string      — 커스텀 플레이스홀더
 *
 * 1000자 상한:
 *   - UX: 글자 수 카운터(0/1000) 표시 + 1000자 도달 시 빨강
 *   - 입력 자체는 막지 않음(브라우저 paste 등 허용) — 백엔드에서 최종 검증(400)
 */

const MAX_LEN = 1000

const DEFAULT_PLACEHOLDER =
  '이 종목/포트폴리오에 대한 의견을 입력하면 GPT가 동의/반박 양면 평가를 추가합니다.\n예) "AI 사이클 수혜로 향후 12개월 강세 예상"'

export default function UserCommentInput({
  value = '',
  onChange,
  disabled = false,
  compact = false,
  placeholder = DEFAULT_PLACEHOLDER,
}) {
  const len = (value || '').length
  const over = len > MAX_LEN
  const near = !over && len >= MAX_LEN * 0.9

  const counterColor = over
    ? 'text-red-600'
    : near
    ? 'text-amber-600'
    : 'text-gray-400'

  const rows = compact ? 2 : 3

  return (
    <div className="space-y-1">
      <textarea
        value={value}
        onChange={(e) => onChange && onChange(e.target.value)}
        disabled={disabled}
        rows={rows}
        placeholder={placeholder}
        className={`w-full text-sm border rounded-md px-3 py-2 resize-y bg-white
          disabled:bg-gray-100 disabled:cursor-not-allowed
          focus:outline-none focus:ring-2
          ${
            over
              ? 'border-red-400 focus:ring-red-300'
              : 'border-gray-300 focus:ring-blue-300'
          }`}
      />
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-400">
          {compact
            ? '의견 입력 시 GPT가 동의/반박 양면 평가를 추가합니다.'
            : '비워두면 일반 분석만 수행됩니다.'}
        </span>
        <span className={`font-mono ${counterColor}`}>
          {len.toLocaleString()}/{MAX_LEN.toLocaleString()}
        </span>
      </div>
    </div>
  )
}
