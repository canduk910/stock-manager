/**
 * 다중 종목 입력기 — 칩(chip) 기반 1~10개 종목 관리.
 *
 * Props:
 *   symbols      - Array<{code, name?}> 현재 선택된 종목 목록
 *   onChange     - (newList) => void
 *   maxItems     - 최대 종목 수 (기본 10)
 *   disabled     - bool
 *
 * 내부 검색은 SymbolSearchBar(KR 자동완성) 재사용.
 */
import { useCallback } from 'react'
import SymbolSearchBar from '../order/SymbolSearchBar'

export default function SymbolMultiInput({
  symbols = [],
  onChange,
  maxItems = 10,
  disabled = false,
}) {
  const handleAdd = useCallback(({ code, name }) => {
    if (!code) return
    if (symbols.length >= maxItems) return
    if (symbols.some((s) => s.code === code)) return
    onChange?.([...symbols, { code, name: name || code }])
  }, [symbols, maxItems, onChange])

  const handleRemove = useCallback((code) => {
    onChange?.(symbols.filter((s) => s.code !== code))
  }, [symbols, onChange])

  const remaining = maxItems - symbols.length

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          KR 종목 코드를 1~{maxItems}개까지 선택 (균등 배분 시뮬레이션).
        </p>
        <span className={`text-xs font-mono ${
          symbols.length >= maxItems ? 'text-orange-600 font-semibold' : 'text-gray-500'
        }`}>
          {symbols.length} / {maxItems}
        </span>
      </div>

      {/* 칩 영역 */}
      {symbols.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {symbols.map((s) => (
            <span
              key={s.code}
              className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-200 text-blue-800 rounded px-2 py-1 text-xs"
            >
              <span className="font-medium">{s.name || s.code}</span>
              <span className="text-blue-400 text-[10px] font-mono">{s.code}</span>
              {!disabled && (
                <button
                  type="button"
                  onClick={() => handleRemove(s.code)}
                  className="ml-1 text-blue-400 hover:text-blue-700 font-bold"
                  aria-label={`${s.name || s.code} 제거`}
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {/* 검색 입력 — 슬롯 가득 찼으면 비활성화 */}
      {!disabled && remaining > 0 ? (
        <SymbolSearchBar
          market="KR"
          markets={['KR']}
          onMarketChange={() => {}}
          symbol=""
          symbolName=""
          onSymbolSelect={handleAdd}
        />
      ) : remaining <= 0 ? (
        <div className="text-xs text-gray-500 bg-gray-50 border border-dashed border-gray-300 rounded px-3 py-2 text-center">
          최대 {maxItems}종목을 모두 선택했습니다. 다른 종목을 추가하려면 ×로 제거하세요.
        </div>
      ) : null}
    </div>
  )
}
