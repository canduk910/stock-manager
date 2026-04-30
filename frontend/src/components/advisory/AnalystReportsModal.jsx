/**
 * 증권사별 목표가 + 리포트 모달.
 *
 * Props: { code, market, currentPrice, onClose }
 *
 * KR: 네이버 증권 리서치 (증권사, 제목, 목표가, 의견, 날짜, PDF)
 * US: yfinance 등급 변경 이력 (증권사, 등급, 변경, 날짜)
 */
import { useState, useEffect, useCallback } from 'react'
import { fetchAnalystReports } from '../../api/advisory'

const OPINION_COLORS = {
  Buy:         'text-red-600 bg-red-50',
  'Strong Buy':'text-red-700 bg-red-100',
  매수:        'text-red-600 bg-red-50',
  적극매수:    'text-red-700 bg-red-100',
  Hold:        'text-gray-600 bg-gray-100',
  Neutral:     'text-gray-600 bg-gray-100',
  중립:        'text-gray-600 bg-gray-100',
  보유:        'text-gray-600 bg-gray-100',
  Sell:        'text-blue-600 bg-blue-50',
  매도:        'text-blue-600 bg-blue-50',
  Underperform:'text-blue-600 bg-blue-50',
  'Not Rated': 'text-gray-400 bg-gray-50',
  NR:          'text-gray-400 bg-gray-50',
}

function OpinionBadge({ opinion }) {
  if (!opinion) return <span className="text-gray-400 text-xs">-</span>
  const cls = OPINION_COLORS[opinion] || 'text-gray-600 bg-gray-100'
  return <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${cls}`}>{opinion}</span>
}

const fmtPrice = (v) => v != null ? Math.round(v).toLocaleString() + '원' : '-'

export default function AnalystReportsModal({ code, market = 'KR', currentPrice, onClose }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAnalystReports(code, market)
      setReports(data.reports || [])
    } catch (e) {
      setError(e.message || '데이터를 불러올 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }, [code, market])

  useEffect(() => { load() }, [load])

  // 배경 클릭으로 닫기
  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose()
  }

  const isKR = market === 'KR'

  // KR: 목표가 평균 계산
  const pricesWithTarget = reports.filter(r => r.target_price != null)
  const avgTarget = pricesWithTarget.length > 0
    ? Math.round(pricesWithTarget.reduce((s, r) => s + r.target_price, 0) / pricesWithTarget.length)
    : null
  const gap = avgTarget && currentPrice ? ((avgTarget / currentPrice - 1) * 100).toFixed(1) : null

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={handleBackdrop}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="text-base font-bold text-gray-900">
            {isKR ? '📊 증권사 목표가' : '📊 Analyst Ratings'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {/* 본문 */}
        <div className="overflow-y-auto flex-1 px-5 py-3">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full" />
              <span className="ml-2 text-sm text-gray-500">조회 중...</span>
            </div>
          )}

          {error && <div className="text-sm text-red-500 py-4 text-center">{error}</div>}

          {!loading && !error && reports.length === 0 && (
            <div className="text-sm text-gray-400 py-8 text-center">증권사 리포트가 없습니다.</div>
          )}

          {!loading && !error && reports.length > 0 && isKR && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-gray-600">
                  <th className="px-2 py-2 text-left font-medium">증권사</th>
                  <th className="px-2 py-2 text-right font-medium">목표가</th>
                  <th className="px-2 py-2 text-center font-medium">의견</th>
                  <th className="px-2 py-2 text-left font-medium">리포트</th>
                  <th className="px-2 py-2 text-center font-medium">날짜</th>
                  <th className="px-2 py-2 text-center font-medium w-8"></th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r, i) => (
                  <tr key={i} className="border-b last:border-b-0 hover:bg-gray-50/50">
                    <td className="px-2 py-2 font-medium text-gray-800 whitespace-nowrap">{r.broker}</td>
                    <td className="px-2 py-2 text-right text-gray-800 whitespace-nowrap">{fmtPrice(r.target_price)}</td>
                    <td className="px-2 py-2 text-center"><OpinionBadge opinion={r.opinion} /></td>
                    <td className="px-2 py-2 text-gray-600 truncate max-w-[200px]" title={r.title}>{r.title}</td>
                    <td className="px-2 py-2 text-center text-gray-500 whitespace-nowrap">{r.date}</td>
                    <td className="px-2 py-2 text-center">
                      {r.pdf_url && (
                        <a href={r.pdf_url} target="_blank" rel="noopener noreferrer"
                           className="text-indigo-500 hover:text-indigo-700" title="PDF 리포트">
                          📄
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* 해외 종목: 등급 변경 이력 */}
          {!loading && !error && reports.length > 0 && !isKR && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-gray-600">
                  <th className="px-2 py-2 text-left font-medium">Firm</th>
                  <th className="px-2 py-2 text-center font-medium">Action</th>
                  <th className="px-2 py-2 text-center font-medium">From</th>
                  <th className="px-2 py-2 text-center font-medium">To</th>
                  <th className="px-2 py-2 text-center font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r, i) => (
                  <tr key={i} className="border-b last:border-b-0 hover:bg-gray-50/50">
                    <td className="px-2 py-2 font-medium text-gray-800">{r.broker}</td>
                    <td className="px-2 py-2 text-center">
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        r.action?.toLowerCase().includes('upgrade') ? 'text-red-600 bg-red-50' :
                        r.action?.toLowerCase().includes('downgrade') ? 'text-blue-600 bg-blue-50' :
                        'text-gray-600 bg-gray-100'
                      }`}>{r.action}</span>
                    </td>
                    <td className="px-2 py-2 text-center text-gray-500">{r.from_grade}</td>
                    <td className="px-2 py-2 text-center text-gray-800 font-medium">{r.to_grade}</td>
                    <td className="px-2 py-2 text-center text-gray-500">{r.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 푸터: 평균 목표가 + 현재가 대비 */}
        {isKR && avgTarget && (
          <div className="px-5 py-3 border-t bg-gray-50 flex items-center justify-between text-sm">
            <span className="text-gray-600">
              평균 목표가 <strong className="text-gray-900">{avgTarget.toLocaleString()}원</strong>
              <span className="text-gray-400 ml-1">({pricesWithTarget.length}건)</span>
            </span>
            {gap && (
              <span className={Number(gap) >= 0 ? 'text-red-600 font-medium' : 'text-blue-600 font-medium'}>
                현재가 대비 {Number(gap) >= 0 ? '+' : ''}{gap}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
