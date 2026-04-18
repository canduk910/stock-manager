import { useState } from 'react'

const fmtNum = (v, digits = 2) =>
  v != null ? Number(v).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '-'

const fmtKrw = (v) => v != null ? Math.round(v).toLocaleString('ko-KR') : '-'

export default function TaxTransactionsTable({ transactions, onAdd, onDelete, onSync, syncLoading, year }) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [form, setForm] = useState({
    symbol: '', symbol_name: '', side: 'buy', quantity: '',
    price_foreign: '', trade_date: '', currency: 'USD', commission: '0', memo: '',
  })
  const [addLoading, setAddLoading] = useState(false)

  const handleAdd = async (e) => {
    e.preventDefault()
    setAddLoading(true)
    try {
      await onAdd({
        ...form,
        quantity: parseInt(form.quantity),
        price_foreign: parseFloat(form.price_foreign),
        commission: parseFloat(form.commission || '0'),
      })
      setShowAddForm(false)
      setForm({
        symbol: '', symbol_name: '', side: 'buy', quantity: '',
        price_foreign: '', trade_date: '', currency: 'USD', commission: '0', memo: '',
      })
    } catch (err) {
      alert(err.message)
    } finally {
      setAddLoading(false)
    }
  }

  return (
    <div>
      {/* 액션 바 */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={onSync}
          disabled={syncLoading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {syncLoading ? '동기화 중...' : `${year}년 체결내역 동기화`}
        </button>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-gray-600 text-white text-sm rounded-lg hover:bg-gray-700"
        >
          {showAddForm ? '취소' : '수동 추가'}
        </button>
        <span className="text-sm text-gray-500 ml-auto">{transactions?.length || 0}건</span>
      </div>

      {/* 수동 추가 폼 */}
      {showAddForm && (
        <form onSubmit={handleAdd} className="bg-gray-50 rounded-lg border p-4 mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <input
            placeholder="종목코드 (AAPL)"
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            required
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            placeholder="종목명"
            value={form.symbol_name}
            onChange={(e) => setForm({ ...form, symbol_name: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <select
            value={form.side}
            onChange={(e) => setForm({ ...form, side: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          >
            <option value="buy">매수</option>
            <option value="sell">매도</option>
          </select>
          <input
            type="date"
            value={form.trade_date}
            onChange={(e) => setForm({ ...form, trade_date: e.target.value })}
            required
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            type="number"
            placeholder="수량"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            required min="1"
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            type="number"
            step="0.01"
            placeholder="체결가 (외화)"
            value={form.price_foreign}
            onChange={(e) => setForm({ ...form, price_foreign: e.target.value })}
            required
            className="px-3 py-2 border rounded text-sm"
          />
          <input
            type="number"
            step="0.01"
            placeholder="수수료 (외화)"
            value={form.commission}
            onChange={(e) => setForm({ ...form, commission: e.target.value })}
            className="px-3 py-2 border rounded text-sm"
          />
          <button
            type="submit"
            disabled={addLoading}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            {addLoading ? '추가 중...' : '추가'}
          </button>
        </form>
      )}

      {/* 테이블 */}
      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2 text-left">거래일</th>
              <th className="px-3 py-2 text-left">종목</th>
              <th className="px-3 py-2 text-center">구분</th>
              <th className="px-3 py-2 text-right">수량</th>
              <th className="px-3 py-2 text-right">체결가(외화)</th>
              <th className="px-3 py-2 text-right">환율</th>
              <th className="px-3 py-2 text-right">원화단가</th>
              <th className="px-3 py-2 text-right">수수료(원)</th>
              <th className="px-3 py-2 text-center">소스</th>
              <th className="px-3 py-2 text-center">삭제</th>
            </tr>
          </thead>
          <tbody>
            {(!transactions || transactions.length === 0) ? (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-gray-400">매매내역이 없습니다.</td></tr>
            ) : (
              transactions.map((tx) => (
                <tr key={tx.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2 whitespace-nowrap">{tx.trade_date}</td>
                  <td className="px-3 py-2">
                    <span className="font-medium">{tx.symbol}</span>
                    {tx.symbol_name && <span className="text-gray-400 ml-1 text-xs">{tx.symbol_name}</span>}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      tx.side === 'buy' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {tx.side === 'buy' ? '매수' : '매도'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">{tx.quantity}</td>
                  <td className="px-3 py-2 text-right">${fmtNum(tx.price_foreign)}</td>
                  <td className="px-3 py-2 text-right">{tx.exchange_rate ? fmtNum(tx.exchange_rate, 1) : '-'}</td>
                  <td className="px-3 py-2 text-right">{fmtKrw(tx.price_krw)}</td>
                  <td className="px-3 py-2 text-right">{fmtKrw(tx.commission_krw)}</td>
                  <td className="px-3 py-2 text-center">
                    <span className="text-xs text-gray-400">{tx.source}</span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => { if (confirm('삭제하시겠습니까?')) onDelete(tx.id) }}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
