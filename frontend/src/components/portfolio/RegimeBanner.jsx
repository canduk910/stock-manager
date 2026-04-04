const REGIMES = [
  { max: 25, label: '공포 (방어적)', desc: '현금 비중 확대, 신규 매수 자제', bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', badge: 'bg-red-100' },
  { max: 45, label: '신중 (선별적)', desc: '저평가 우량주 선별 매수', bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', badge: 'bg-amber-100' },
  { max: 60, label: '중립 (적극적)', desc: '정상 포트폴리오 운용', bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-700', badge: 'bg-green-100' },
  { max: 100, label: '탐욕 (축적)', desc: '이익 실현 고려, 현금 확보', bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700', badge: 'bg-blue-100' },
]

function getRegime(fearGreed) {
  if (fearGreed == null) return null
  return REGIMES.find(r => fearGreed <= r.max) || REGIMES[REGIMES.length - 1]
}

export default function RegimeBanner({ sentiment }) {
  if (!sentiment) return null

  const fg = sentiment.fear_greed
  const fgValue = fg?.score ?? fg?.value
  const regime = getRegime(fgValue)
  if (!regime) return null

  const vix = sentiment.vix
  const buffett = sentiment.buffett_indicator

  return (
    <div className={`rounded-xl border ${regime.border} ${regime.bg} px-5 py-3 flex items-center justify-between`}>
      <div className="flex items-center gap-3">
        <span className={`px-3 py-1 rounded-full text-xs font-bold ${regime.badge} ${regime.text}`}>
          {regime.label}
        </span>
        <span className={`text-sm ${regime.text}`}>{regime.desc}</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-500">
        {fgValue != null && (
          <span>공포탐욕 <strong className={regime.text}>{fgValue}</strong></span>
        )}
        {vix?.value != null && (
          <span>VIX <strong>{Number(vix.value).toFixed(1)}</strong></span>
        )}
        {buffett?.ratio != null && (
          <span>버핏 <strong>{Number(buffett.ratio).toFixed(0)}%</strong></span>
        )}
      </div>
    </div>
  )
}
