/**
 * 백테스트 페이지 (/backtest).
 *
 * KIS AI Extensions MCP 서버(port 3846) 연동으로 전략 백테스트를 실행한다.
 *
 * 구조:
 *   1) MCP 상태 확인 — KIS_MCP_ENABLED=false이면 안내 화면 표시
 *   2) 종목 선택 — SymbolSearchBar 재사용 (주문 페이지와 동일 컴포넌트)
 *   3) 전략 선택 — 프리셋(10개 드롭다운) 또는 커스텀(.kis.yaml 직접 입력)
 *   4) 백테스트 실행 — POST /api/backtest/run/preset 또는 /run/custom
 *   5) 결과 폴링 — GET /api/backtest/result/{job_id} (3초 간격, 최대 3분)
 *   6) 결과 표시 — MetricsCard(4칸) + 수익률 곡선 + 거래 내역
 *   7) 배치 비교 — 4개 프리셋 동시 실행 → 비교 테이블
 *
 * 핵심 훅: useMcpStatus (연결 상태), usePresets (전략 목록), useBacktest (실행+폴링)
 */
import { useState, useEffect, useCallback } from 'react'
import SymbolSearchBar from '../components/order/SymbolSearchBar'
import StrategySelector from '../components/backtest/StrategySelector'
import BacktestResultPanel from '../components/backtest/BacktestResultPanel'
import BatchCompareTable from '../components/backtest/BatchCompareTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import { useMcpStatus, usePresets, useBacktest } from '../hooks/useBacktest'

// 배치 비교 시 사용할 대표 전략 4개:
// - sma_crossover: 추세추종 대표 (골든/데드 크로스)
// - momentum: 모멘텀 대표 (최근 N일 수익률)
// - trend_filter_signal: 복합 전략 (추세 + 시그널)
// - volatility_breakout: 변동성 대표 (축소 후 확장)
const DEFAULT_PRESETS_FOR_BATCH = ['sma_crossover', 'momentum', 'trend_filter_signal', 'volatility_breakout']

export default function BacktestPage() {
  const { available: mcpAvailable, loading: mcpLoading } = useMcpStatus()
  const { presets, load: loadPresets } = usePresets()
  const {
    status, result, error, progress,
    runPreset, runCustom, runBatch, reset,
  } = useBacktest()

  // 종목 선택
  const [market, setMarket] = useState('KR')
  const [symbol, setSymbol] = useState('')
  const [symbolName, setSymbolName] = useState('')

  // 전략 선택
  const [strategyMode, setStrategyMode] = useState('preset') // preset | custom
  const [selectedPreset, setSelectedPreset] = useState('')
  const [yamlContent, setYamlContent] = useState('')

  // 기간/금액
  const today = new Date().toISOString().slice(0, 10)
  const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10)
  const [startDate, setStartDate] = useState(oneYearAgo)
  const [endDate, setEndDate] = useState(today)
  const [initialCash, setInitialCash] = useState(10000000)

  // 결과 모드 (single | batch)
  const [resultMode, setResultMode] = useState(null)

  // MCP 연결 시 프리셋 목록 로드
  useEffect(() => {
    if (mcpAvailable) loadPresets()
  }, [mcpAvailable, loadPresets])

  const handleSymbolSelect = useCallback(({ code, name, market: m }) => {
    setSymbol(code)
    setSymbolName(name)
    if (m) setMarket(m)
  }, [])

  const handleRun = useCallback(() => {
    if (!symbol) return
    reset()
    setResultMode('single')
    if (strategyMode === 'preset' && selectedPreset) {
      runPreset(selectedPreset, symbol, market, startDate, endDate, initialCash)
    } else if (strategyMode === 'custom' && yamlContent.trim()) {
      runCustom(yamlContent, symbol, market, startDate, endDate, initialCash)
    }
  }, [symbol, strategyMode, selectedPreset, yamlContent, market, startDate, endDate, initialCash, runPreset, runCustom, reset])

  const handleBatch = useCallback(() => {
    if (!symbol) return
    reset()
    setResultMode('batch')
    runBatch(DEFAULT_PRESETS_FOR_BATCH, symbol, market, startDate, endDate)
  }, [symbol, market, startDate, endDate, runBatch, reset])

  const isRunning = status === 'submitting' || status === 'running'
  const canRun = symbol && (
    (strategyMode === 'preset' && selectedPreset) ||
    (strategyMode === 'custom' && yamlContent.trim())
  ) && !isRunning

  // MCP 비활성화 시 안내
  if (!mcpLoading && !mcpAvailable) {
    return (
      <div className="max-w-2xl mx-auto mt-12 text-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">KIS MCP 서버 미연결</h2>
          <p className="text-sm text-yellow-700 mb-4">
            백테스트 기능을 사용하려면 KIS AI Extensions MCP 서버가 실행되어야 합니다.
          </p>
          <div className="text-xs text-left bg-yellow-100 rounded p-3 font-mono">
            <p># 환경변수 설정</p>
            <p>KIS_MCP_ENABLED=true</p>
            <p className="mt-2"># MCP 서버 실행</p>
            <p>bash backtester/scripts/start_mcp.sh</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">백테스트</h1>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
          mcpAvailable ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          MCP {mcpAvailable ? '연결됨' : '미연결'}
        </span>
      </div>

      {/* 설정 패널 */}
      <div className="bg-white rounded-lg border p-4 space-y-4">
        {/* 종목 선택 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">종목</label>
          <SymbolSearchBar
            market={market}
            onMarketChange={setMarket}
            symbol={symbol}
            symbolName={symbolName}
            onSymbolSelect={handleSymbolSelect}
          />
        </div>

        {/* 전략 선택 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">전략</label>
          <StrategySelector
            presets={presets}
            selectedPreset={selectedPreset}
            yamlContent={yamlContent}
            mode={strategyMode}
            onModeChange={setStrategyMode}
            onPresetChange={setSelectedPreset}
            onYamlChange={setYamlContent}
          />
        </div>

        {/* 기간 + 금액 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">시작일</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">종료일</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">초기자금</label>
            <input
              type="number"
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              step={1000000}
            />
          </div>
        </div>

        {/* 실행 버튼 */}
        <div className="flex gap-3">
          <button
            onClick={handleRun}
            disabled={!canRun}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? '실행 중...' : '백테스트 실행'}
          </button>
          <button
            onClick={handleBatch}
            disabled={!symbol || isRunning}
            className="px-5 py-2 bg-gray-600 text-white text-sm font-medium rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            전략 비교 (4개)
          </button>
        </div>
      </div>

      {/* 진행 상태 */}
      {isRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
          <LoadingSpinner />
          <div>
            <p className="text-sm font-medium text-blue-800">백테스트 진행 중...</p>
            {progress && (
              <p className="text-xs text-blue-600 mt-1">
                {progress.done}/{progress.total} 완료
              </p>
            )}
          </div>
        </div>
      )}

      {/* 에러 */}
      {error && <ErrorAlert message={error} />}

      {/* 결과 */}
      {status === 'completed' && resultMode === 'single' && (
        <BacktestResultPanel result={result} />
      )}

      {status === 'completed' && resultMode === 'batch' && (
        <BatchCompareTable result={result} />
      )}

      {status === 'timeout' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            백테스트 시간이 초과되었습니다. MCP 서버 상태를 확인해주세요.
          </p>
        </div>
      )}
    </div>
  )
}
