import { useState } from 'react'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}분 전`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}시간 전`
    const days = Math.floor(hrs / 24)
    return `${days}일 전`
  } catch {
    return dateStr
  }
}

function NewsItem({ title, link, source, published, subtitle }) {
  return (
    <li className="py-2 border-b border-gray-100 last:border-0">
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-gray-800 hover:text-blue-600 hover:underline leading-snug block"
      >
        {title}
      </a>
      {subtitle && (
        <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">{subtitle}</div>
      )}
      <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
        {source && <span>{source}</span>}
        {published && <span>{timeAgo(published)}</span>}
      </div>
    </li>
  )
}

function TranslatedNewsItem({ item }) {
  const [showOriginal, setShowOriginal] = useState(false)
  return (
    <li className="py-2 border-b border-gray-100 last:border-0">
      <a
        href={item.link}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-gray-800 hover:text-blue-600 hover:underline leading-snug block"
      >
        {item.title_ko || item.title_original}
      </a>
      {item.summary_ko && (
        <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{item.summary_ko}</div>
      )}
      <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
        <span>{item.source}</span>
        {item.published && <span>{timeAgo(item.published)}</span>}
        {item.translated && item.title_original && (
          <button
            onClick={() => setShowOriginal(!showOriginal)}
            className="text-blue-500 hover:underline"
          >
            {showOriginal ? '번역 보기' : '원문 보기'}
          </button>
        )}
      </div>
      {showOriginal && (
        <div className="text-xs text-gray-400 mt-1 italic">{item.title_original}</div>
      )}
    </li>
  )
}

export default function NewsSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="뉴스 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  const { korean = [], international = [] } = data

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">주요 뉴스</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 한국 뉴스 */}
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            한국 경제
          </h3>
          {korean.length === 0 ? (
            <div className="text-sm text-gray-400 py-4 text-center">뉴스를 불러올 수 없습니다</div>
          ) : (
            <ul className="divide-y-0">{korean.map((n, i) => (
              <NewsItem key={i} title={n.title} link={n.link} source={n.source} published={n.published} />
            ))}</ul>
          )}
        </div>

        {/* 국제 뉴스 */}
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
            국제 (NYT)
          </h3>
          {international.length === 0 ? (
            <div className="text-sm text-gray-400 py-4 text-center">뉴스를 불러올 수 없습니다</div>
          ) : (
            <ul className="divide-y-0">{international.map((n, i) => (
              <TranslatedNewsItem key={i} item={n} />
            ))}</ul>
          )}
        </div>
      </div>
    </section>
  )
}
