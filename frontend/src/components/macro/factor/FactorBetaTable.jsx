/**
 * 종목 거시 베타 테이블 — 5 beta 칩 + R² 가로막대 + 1-R²(고유 스토리) 부각.
 *
 * "내 종목의 거시 민감도" — in_portfolio 강조. 고유스토리(1-R²)가 높을수록
 * 거시보다 개별 스토리에 좌우됨을 시각화. 매매 액션 문구 미표시(안전 규칙).
 */
const BETA_COLORS = ['#7c3aed', '#2563eb', '#059669', '#d97706', '#dc2626']

function betaChipColor(v) {
  // 절대값 클수록 진하게, 부호로 빨강(+)/파랑(-)
  const a = Math.min(1, Math.abs(v) / 1.0)
  if (v >= 0) return { color: '#b91c1c', opacity: 0.25 + a * 0.5 }
  return { color: '#1d4ed8', opacity: 0.25 + a * 0.5 }
}

export default function FactorBetaTable({ stockBetas, pcLabels }) {
  const rows = stockBetas || []
  if (rows.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-6">
        종목 베타 데이터 없음 — 관심종목·자문종목 등록 후 익일 갱신됩니다.
      </div>
    )
  }

  const pcLabelList = pcLabels
    ? Object.keys(pcLabels).map((k) => pcLabels[k])
    : ['PC0', 'PC1', 'PC2', 'PC3', 'PC4']

  // in_portfolio 우선 + R² 내림차순 정렬
  const sorted = [...rows].sort((a, b) => {
    if (!!b.in_portfolio !== !!a.in_portfolio) return b.in_portfolio ? 1 : -1
    return (b.r2 || 0) - (a.r2 || 0)
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500">
            <th className="text-left py-1.5 px-1">종목</th>
            {pcLabelList.map((lbl, i) => (
              <th key={i} className="text-center py-1.5 px-1" title={lbl}>
                <span style={{ color: BETA_COLORS[i % BETA_COLORS.length] }}>β{i}</span>
              </th>
            ))}
            <th className="text-left py-1.5 px-2 w-28">설명력 R²</th>
            <th className="text-right py-1.5 px-1">고유스토리</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => {
            const betas = s.betas || []
            const r2 = s.r2 || 0
            const idio = s.idiosyncratic != null ? s.idiosyncratic : 1 - r2
            return (
              <tr
                key={`${s.code}:${s.market}`}
                className={`border-b border-gray-100 ${
                  s.in_portfolio ? 'bg-violet-50/50' : ''
                }`}
              >
                <td className="py-1.5 px-1">
                  <div className="flex items-center gap-1">
                    {s.in_portfolio && <span className="text-violet-600" title="내 포트폴리오">★</span>}
                    <span className="font-medium text-gray-800 truncate max-w-[7rem]" title={s.name}>
                      {s.name}
                    </span>
                    {s.market === 'US' && (
                      <span className="text-[10px] text-gray-400">US</span>
                    )}
                  </div>
                </td>
                {betas.map((b, i) => {
                  const st = betaChipColor(b)
                  return (
                    <td key={i} className="text-center py-1.5 px-1">
                      <span
                        className="inline-block px-1 rounded text-[11px] font-medium"
                        style={{ backgroundColor: st.color, opacity: st.opacity, color: '#fff' }}
                      >
                        {b >= 0 ? '+' : ''}{b.toFixed(2)}
                      </span>
                    </td>
                  )
                })}
                <td className="py-1.5 px-2">
                  <div className="flex items-center gap-1.5">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500"
                        style={{ width: `${Math.round(r2 * 100)}%` }}
                      />
                    </div>
                    <span className="text-gray-600 w-8 text-right">{(r2 * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td className="text-right py-1.5 px-1 text-amber-700 font-medium">
                  {(idio * 100).toFixed(0)}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-[11px] text-gray-400 mt-2">
        ※ βi = 주성분 i 1σ 변동 시 일별 수익률 민감도. R²=거시 설명력, 고유스토리=1-R²(개별 요인).
        ★=내 관심·자문 종목.
      </p>
    </div>
  )
}
