import { useState, useEffect } from 'react'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (n) => (n ?? 0).toLocaleString('ko-KR')

export default function TaxSimulationPanel({ holdings, result, loadHoldings, simulate, year }) {
  const [inputs, setInputs] = useState({})

  useEffect(() => { loadHoldings() }, [])

  const handleQtyChange = (symbol, value) => {
    setInputs((prev) => ({
      ...prev,
      [symbol]: { ...prev[symbol], quantity: Number(value) || 0 },
    }))
  }

  const handlePriceChange = (symbol, value) => {
    setInputs((prev) => ({
      ...prev,
      [symbol]: { ...prev[symbol], price_foreign: Number(value) || 0 },
    }))
  }

  const handleSimulate = () => {
    const items = (holdings.data || [])
      .filter((h) => {
        const inp = inputs[h.symbol]
        return inp && inp.quantity > 0 && inp.price_foreign > 0
      })
      .map((h) => ({
        symbol: h.symbol,
        quantity: inputs[h.symbol].quantity,
        price_foreign: inputs[h.symbol].price_foreign,
        currency: h.currency,
      }))

    if (items.length === 0) {
      alert('매도할 종목의 수량과 가격을 입력해주세요.')
      return
    }
    simulate(year, items)
  }

  const handleFillAll = () => {
    const filled = {}
    for (const h of holdings.data || []) {
      filled[h.symbol] = {
        quantity: h.quantity,
        price_foreign: h.current_price,
      }
    }
    setInputs(filled)
  }

  const r = result.data

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
        보유 종목을 가상으로 매도했을 때의 예상 양도세를 계산합니다. 실제 주문은 발생하지 않습니다.
      </div>

      {holdings.loading && <LoadingSpinner />}
      {holdings.error && <ErrorAlert message={holdings.error} />}

      {holdings.data?.length > 0 && (
        <>
          <div className="flex justify-end">
            <button
              onClick={handleFillAll}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              전량 현재가 채우기
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 px-2">종목</th>
                  <th className="py-2 px-2 text-right">보유</th>
                  <th className="py-2 px-2 text-right">매입가</th>
                  <th className="py-2 px-2 text-right">현재가</th>
                  <th className="py-2 px-2 text-right">통화</th>
                  <th className="py-2 px-2">매도 수량</th>
                  <th className="py-2 px-2">매도 가격</th>
                </tr>
              </thead>
              <tbody>
                {holdings.data.map((h) => {
                  const inp = inputs[h.symbol] || {}
                  return (
                    <tr key={h.symbol} className="border-b hover:bg-gray-50">
                      <td className="py-2 px-2 font-medium">
                        {h.symbol}
                        {h.name && <span className="text-gray-400 ml-1 text-xs">{h.name}</span>}
                      </td>
                      <td className="py-2 px-2 text-right">{h.quantity}</td>
                      <td className="py-2 px-2 text-right">{h.avg_price?.toFixed(2)}</td>
                      <td className="py-2 px-2 text-right">{h.current_price?.toFixed(2)}</td>
                      <td className="py-2 px-2 text-right text-gray-500">{h.currency}</td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          min="0"
                          max={h.quantity}
                          value={inp.quantity || ''}
                          onChange={(e) => handleQtyChange(h.symbol, e.target.value)}
                          className="w-20 px-2 py-1 border rounded text-right text-sm"
                          placeholder="0"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={inp.price_foreign || ''}
                          onChange={(e) => handlePriceChange(h.symbol, e.target.value)}
                          className="w-24 px-2 py-1 border rounded text-right text-sm"
                          placeholder="0.00"
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleSimulate}
              disabled={result.loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {result.loading ? '계산 중...' : '시뮬레이션 실행'}
            </button>
          </div>
        </>
      )}

      {holdings.data?.length === 0 && !holdings.loading && (
        <div className="text-center text-gray-500 py-8">
          KIS API 키가 설정되지 않았거나 보유 해외주식이 없습니다.
        </div>
      )}

      {result.error && <ErrorAlert message={result.error} />}

      {r && (
        <div className="space-y-4 mt-6">
          <h3 className="font-semibold text-gray-900">시뮬레이션 결과</h3>

          <div className="grid grid-cols-2 gap-4">
            {/* 실제 양도세 */}
            <div className="bg-white border rounded-lg p-4">
              <div className="text-sm text-gray-500 mb-1">현재 양도세 (실제 매도 분)</div>
              <div className="text-lg font-bold">{fmt(r.real_summary?.estimated_tax)}원</div>
              <div className="text-xs text-gray-400 mt-1">
                순양도차익 {fmt(r.real_summary?.net_gain)}원
              </div>
            </div>

            {/* 합산 양도세 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="text-sm text-blue-700 mb-1">시뮬레이션 후 양도세 (합산)</div>
              <div className="text-lg font-bold text-blue-900">{fmt(r.combined_summary?.estimated_tax)}원</div>
              <div className="text-xs text-blue-600 mt-1">
                순양도차익 {fmt(r.combined_summary?.net_gain)}원
              </div>
            </div>
          </div>

          {/* 추가 세액 */}
          <div className={`text-center py-3 rounded-lg text-sm font-medium ${
            r.additional_tax > 0
              ? 'bg-red-50 text-red-700 border border-red-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}>
            가상 매도로 인한 추가 세액: {r.additional_tax > 0 ? '+' : ''}{fmt(r.additional_tax)}원
          </div>

          {/* 가상 매도 상세 */}
          {r.simulated_details?.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">가상 매도 건별 상세</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-2 px-2">종목</th>
                      <th className="py-2 px-2 text-right">수량</th>
                      <th className="py-2 px-2 text-right">매도가(원화)</th>
                      <th className="py-2 px-2 text-right">취득가(원화)</th>
                      <th className="py-2 px-2 text-right">양도차익</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.simulated_details.map((d, i) => (
                      <tr key={i} className="border-b">
                        <td className="py-2 px-2 font-medium">{d.symbol}</td>
                        <td className="py-2 px-2 text-right">{d.sell_quantity}</td>
                        <td className="py-2 px-2 text-right">{fmt(d.sell_price_krw)}</td>
                        <td className="py-2 px-2 text-right">{fmt(d.acquisition_cost_krw)}</td>
                        <td className={`py-2 px-2 text-right font-medium ${
                          d.gain_loss_krw >= 0 ? 'text-red-600' : 'text-blue-600'
                        }`}>
                          {fmt(d.gain_loss_krw)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="text-xs text-gray-400 text-center">
            {r.disclaimer}
          </div>
        </div>
      )}
    </div>
  )
}
