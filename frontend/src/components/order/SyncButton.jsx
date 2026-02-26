/**
 * KIS 대사/동기화 버튼.
 */
export default function SyncButton({ onSync, loading, result }) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onSync}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white text-sm rounded hover:bg-gray-800 disabled:opacity-50"
      >
        <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {loading ? 'KIS 대사 중...' : 'KIS 대사/동기화'}
      </button>
      {result && !loading && (
        <span className="text-sm text-gray-600">
          {result.synced > 0
            ? <span className="text-green-600 font-medium">{result.synced}건 상태 갱신됨</span>
            : <span className="text-gray-500">{result.message || '변경 없음'}</span>}
        </span>
      )}
    </div>
  )
}
