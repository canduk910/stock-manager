/**
 * AI자문 탭 — OpenAI GPT-4o 리포트 표시
 */

function GradeBadge({ grade }) {
  const map = {
    '매수': 'bg-red-100 text-red-700 border-red-400',
    '중립': 'bg-gray-100 text-gray-700 border-gray-400',
    '매도': 'bg-blue-100 text-blue-700 border-blue-400',
    '관망': 'bg-yellow-100 text-yellow-700 border-yellow-400',
  }
  const cls = map[grade] || 'bg-gray-100 text-gray-600 border-gray-300'
  return (
    <span className={`inline-block px-3 py-0.5 rounded-full text-sm font-bold border ${cls}`}>
      {grade}
    </span>
  )
}

function Section({ title, icon, children }) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200">
        {icon} {title}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

export default function AIReportPanel({ report, loading, error, onGenerate }) {
  const reportData = report?.report || {}
  const generatedAt = report?.generated_at
  const model = report?.model

  const opinion = reportData['종합투자의견'] || reportData.opinion || {}
  const technical = reportData['기술적시그널'] || reportData.technical_signal || {}
  const risks = reportData['리스크요인'] || reportData.risk_factors || []
  const points = reportData['투자포인트'] || reportData.investment_points || []

  // 원문 fallback
  const rawText = reportData.raw

  return (
    <div className="space-y-4">
      {/* 액션 바 */}
      <div className="flex items-center justify-between gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-xs text-gray-500">
          {generatedAt
            ? `최종 생성: ${generatedAt.slice(0, 16).replace('T', ' ')} · ${model || ''}`
            : '아직 생성된 리포트가 없습니다.'}
        </div>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? '분석 중...' : 'AI 분석 생성'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-10 text-gray-400 text-sm">
          <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-2" />
          <p>GPT-4o가 분석 중입니다... (10~30초 소요)</p>
        </div>
      )}

      {/* 원문 fallback */}
      {!loading && rawText && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded text-xs text-gray-700 whitespace-pre-wrap">
          {rawText}
        </div>
      )}

      {/* 종합 투자 의견 */}
      {!loading && !rawText && opinion.등급 && (
        <Section title="종합 투자 의견" icon="📊">
          <div className="flex items-center gap-3 mb-3">
            <GradeBadge grade={opinion.등급} />
            <p className="text-sm text-gray-700">{opinion.요약}</p>
          </div>
          {Array.isArray(opinion.근거) && opinion.근거.length > 0 && (
            <ul className="space-y-1 text-sm text-gray-600 pl-2">
              {opinion.근거.map((g, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-blue-500 font-bold shrink-0">{i + 1}.</span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {/* 기술적 시그널 */}
      {!loading && !rawText && technical.신호 && (
        <Section title="기술적 시그널" icon="📈">
          <div className="flex items-center gap-3 mb-3">
            <GradeBadge grade={technical.신호} />
            <p className="text-sm text-gray-700">{technical.해석}</p>
          </div>
          {technical.지표별 && (
            <div className="grid grid-cols-3 gap-2 mt-2">
              {Object.entries(technical.지표별).map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded p-2 text-xs">
                  <span className="font-semibold text-gray-600 uppercase">{k}</span>
                  <p className="text-gray-700 mt-0.5">{v}</p>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* 리스크 요인 */}
      {!loading && !rawText && Array.isArray(risks) && risks.length > 0 && (
        <Section title="리스크 요인" icon="⚠️">
          <ul className="space-y-2">
            {risks.map((r, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="shrink-0 w-5 h-5 rounded-full bg-orange-100 text-orange-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <span className="font-semibold text-gray-700">{r.요인 || r.factor}</span>
                  {(r.설명 || r.description) && (
                    <p className="text-gray-500 text-xs mt-0.5">{r.설명 || r.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 투자 포인트 */}
      {!loading && !rawText && Array.isArray(points) && points.length > 0 && (
        <Section title="투자 포인트" icon="💡">
          <ul className="space-y-2">
            {points.map((p, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="shrink-0 w-5 h-5 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <span className="font-semibold text-gray-700">{p.포인트 || p.point}</span>
                  {(p.설명 || p.description) && (
                    <p className="text-gray-500 text-xs mt-0.5">{p.설명 || p.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 리포트 없음 안내 */}
      {!loading && !rawText && !opinion.등급 && !error && (
        <div className="text-center py-8 text-gray-400 text-sm">
          <p className="text-2xl mb-2">🤖</p>
          <p>아직 생성된 AI 리포트가 없습니다.</p>
          <p className="text-xs mt-1">데이터를 새로고침한 후 "AI 분석 생성" 버튼을 클릭하세요.</p>
        </div>
      )}
    </div>
  )
}
