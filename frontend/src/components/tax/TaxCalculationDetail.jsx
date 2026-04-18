const fmtKrw = (v) => v != null ? Math.round(v).toLocaleString('ko-KR') : '-'

export default function TaxCalculationDetail({ calculations }) {
  if (!calculations || calculations.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center text-gray-400">
        계산 결과가 없습니다. '요약' 탭에서 조회하면 자동 계산됩니다.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-3 py-2 text-left">매도일</th>
            <th className="px-3 py-2 text-left">종목</th>
            <th className="px-3 py-2 text-right">매도수량</th>
            <th className="px-3 py-2 text-right">매도금액(원)</th>
            <th className="px-3 py-2 text-right">취득원가(원)</th>
            <th className="px-3 py-2 text-right">수수료(원)</th>
            <th className="px-3 py-2 text-right">양도차익(원)</th>
            <th className="px-3 py-2 text-left">FIFO 상세</th>
          </tr>
        </thead>
        <tbody>
          {calculations.map((calc) => {
            const gl = calc.gain_loss_krw || 0
            let detail = null
            try {
              detail = calc.detail_json ? JSON.parse(calc.detail_json) : null
            } catch {}

            return (
              <tr key={calc.id} className="border-b hover:bg-gray-50">
                <td className="px-3 py-2 whitespace-nowrap">{calc.trade_date}</td>
                <td className="px-3 py-2 font-medium">{calc.symbol}</td>
                <td className="px-3 py-2 text-right">{calc.sell_quantity}</td>
                <td className="px-3 py-2 text-right">{fmtKrw(calc.sell_price_krw)}</td>
                <td className="px-3 py-2 text-right">{fmtKrw(calc.acquisition_cost_krw)}</td>
                <td className="px-3 py-2 text-right">{fmtKrw(calc.commission_total_krw)}</td>
                <td className={`px-3 py-2 text-right font-medium ${gl >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                  {fmtKrw(gl)}
                </td>
                <td className="px-3 py-2">
                  {Array.isArray(detail) ? (
                    <div className="space-y-0.5">
                      {detail.map((d, i) => (
                        <div key={i} className="text-xs text-gray-500">
                          {d.warning ? (
                            <span className="text-amber-600 font-medium">{d.warning} ({d.quantity}주)</span>
                          ) : (
                            <span>{d.trade_date} · {d.quantity}주 · {fmtKrw(d.cost_krw)}원</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : detail?.method ? (
                    <span className="text-xs text-gray-400">{detail.method}</span>
                  ) : null}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
