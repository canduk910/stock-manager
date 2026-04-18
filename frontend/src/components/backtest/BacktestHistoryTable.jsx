/**
 * 백테스트 이력 테이블.
 * 과거 실행 결과 목록 + "보기" 버튼으로 결과 로드.
 */

const STATUS_BADGE = {
  completed: 'bg-green-100 text-green-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
}

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatPct(val) {
  if (val == null) return '-'
  const n = Number(val)
  return isNaN(n) ? '-' : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

export default function BacktestHistoryTable({ history, onSelect, loading }) {
  if (loading) {
    return <div className="text-sm text-gray-500 py-4 text-center">이력 로딩 중...</div>
  }

  if (!history || history.length === 0) {
    return <div className="text-sm text-gray-400 py-4 text-center">백테스트 이력이 없습니다</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500 text-xs">
            <th className="py-2 px-2 text-left font-medium">일시</th>
            <th className="py-2 px-2 text-left font-medium">종목</th>
            <th className="py-2 px-2 text-left font-medium">전략</th>
            <th className="py-2 px-2 text-right font-medium">수익률</th>
            <th className="py-2 px-2 text-right font-medium">샤프</th>
            <th className="py-2 px-2 text-right font-medium">낙폭</th>
            <th className="py-2 px-2 text-center font-medium">상태</th>
            <th className="py-2 px-2 text-center font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {history.map((job) => {
            const isStale = job.status === 'submitted' &&
              new Date() - new Date(job.submitted_at) > 10 * 60 * 1000
            const displayStatus = isStale ? 'failed' : job.status

            return (
              <tr key={job.job_id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 px-2 text-gray-600 whitespace-nowrap">
                  {formatDate(job.submitted_at || job.completed_at)}
                </td>
                <td className="py-2 px-2 font-mono">{job.symbol}</td>
                <td className="py-2 px-2">{job.strategy_name}</td>
                <td className="py-2 px-2 text-right font-mono">
                  <span className={job.total_return_pct > 0 ? 'text-red-600' : job.total_return_pct < 0 ? 'text-blue-600' : ''}>
                    {formatPct(job.total_return_pct)}
                  </span>
                </td>
                <td className="py-2 px-2 text-right font-mono">
                  {job.sharpe_ratio != null ? Number(job.sharpe_ratio).toFixed(2) : '-'}
                </td>
                <td className="py-2 px-2 text-right font-mono text-blue-600">
                  {job.max_drawdown != null ? `-${Number(job.max_drawdown).toFixed(1)}%` : '-'}
                </td>
                <td className="py-2 px-2 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[displayStatus] || 'bg-gray-100 text-gray-600'}`}>
                    {isStale ? '시간초과' : displayStatus === 'completed' ? '완료' : displayStatus === 'submitted' ? '실행중' : '실패'}
                  </span>
                </td>
                <td className="py-2 px-2 text-center">
                  {job.status === 'completed' && (
                    <button
                      onClick={() => onSelect(job)}
                      className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      보기
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
