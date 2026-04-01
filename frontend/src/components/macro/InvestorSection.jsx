import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const diff = Date.now() - d.getTime()
    const days = Math.floor(diff / 86400000)
    if (days < 1) return '오늘'
    if (days < 7) return `${days}일 전`
    if (days < 30) return `${Math.floor(days / 7)}주 전`
    return `${Math.floor(days / 30)}개월 전`
  } catch {
    return dateStr
  }
}

function InvestorCard({ investor }) {
  const { name_ko: nameKo, name, quotes = [] } = investor

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-bold text-gray-600">
          {nameKo[0]}
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-900">{nameKo}</div>
          <div className="text-xs text-gray-400">{name}</div>
        </div>
      </div>

      {quotes.length === 0 ? (
        <div className="text-sm text-gray-400 py-2">최근 코멘트 없음</div>
      ) : (
        <ul className="space-y-3">
          {quotes.map((q, i) => (
            <li key={i} className="text-sm">
              <p className="text-gray-800 leading-relaxed">{q.text_ko}</p>
              {q.text_original && q.text_original !== q.text_ko && (
                <p className="text-xs text-gray-400 mt-0.5 italic line-clamp-1">{q.text_original}</p>
              )}
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                {q.source && <span>{q.source}</span>}
                {q.date && <span>{timeAgo(q.date)}</span>}
                {q.source_url && (
                  <a
                    href={q.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:underline"
                  >
                    원문
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function InvestorSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="투자자 코멘트 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data?.investors?.length) return null

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">투자 대가 코멘트</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.investors.map((inv) => (
          <InvestorCard key={inv.name} investor={inv} />
        ))}
      </div>
    </section>
  )
}
