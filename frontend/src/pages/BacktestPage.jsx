/**
 * 백테스트 페이지 (/backtest).
 *
 * KIS AI Extensions MCP 서버 연동으로 전략 백테스트를 실행한다.
 * 히스토리 테이블로 과거 실행 결과를 조회할 수 있다.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import SymbolSearchBar from '../components/order/SymbolSearchBar'
import StrategySelector from '../components/backtest/StrategySelector'
import BacktestResultPanel from '../components/backtest/BacktestResultPanel'
import BatchCompareTable from '../components/backtest/BatchCompareTable'
import BacktestHistoryTable from '../components/backtest/BacktestHistoryTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import { useMcpStatus, usePresets, useBacktest, useBacktestHistory } from '../hooks/useBacktest'
import { fetchBacktestResult, deleteBacktestJob } from '../api/backtest'

const DEFAULT_PRESETS_FOR_BATCH = ['sma_crossover', 'momentum', 'trend_filter_signal', 'volatility_breakout']

export default function BacktestPage() {
  const { available: mcpAvailable, loading: mcpLoading } = useMcpStatus()
  const { presets, load: loadPresets } = usePresets()
  const {
    status, result, error, progress,
    runPreset, runCustom, runBatch, reset,
  } = useBacktest()
  const { history, loading: historyLoading, load: loadHistory } = useBacktestHistory()

  const [market, setMarket] = useState('KR')
  const [symbol, setSymbol] = useState('')
  const [symbolName, setSymbolName] = useState('')
  const [strategyMode, setStrategyMode] = useState('preset')
  const [selectedPreset, setSelectedPreset] = useState('')
  const [yamlContent, setYamlContent] = useState('')
  const [customParams, setCustomParams] = useState({})

  const today = new Date().toISOString().slice(0, 10)
  const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10)
  const [startDate, setStartDate] = useState(oneYearAgo)
  const [endDate, setEndDate] = useState(today)
  const [initialCash, setInitialCash] = useState(10000000)
  const [commissionRate, setCommissionRate] = useState(0.015)
  const [taxRate, setTaxRate] = useState(0.23)
  const [slippage, setSlippage] = useState(0.05)
  const [resultMode, setResultMode] = useState(null)
  const [viewResult, setViewResult] = useState(null) // 히스토리에서 선택한 결과
  const [builderYamlState, setBuilderYamlState] = useState(null) // 빌더에서 YAML 생성 시 빌더 상태

  // 경과 시간 카운터
  const [elapsed, setElapsed] = useState(0)
  const elapsedRef = useRef(null)

  const isRunning = status === 'submitting' || status === 'running'

  // 실행 시작/종료 시 경과 시간 타이머 관리
  useEffect(() => {
    if (isRunning) {
      setElapsed(0)
      elapsedRef.current = setInterval(() => setElapsed((v) => v + 1), 1000)
    } else {
      if (elapsedRef.current) {
        clearInterval(elapsedRef.current)
        elapsedRef.current = null
      }
    }
    return () => {
      if (elapsedRef.current) clearInterval(elapsedRef.current)
    }
  }, [isRunning])

  useEffect(() => {
    if (mcpAvailable) loadPresets()
  }, [mcpAvailable, loadPresets])

  // 마운트 시 + 백테스트 완료 시 히스토리 로드
  useEffect(() => { loadHistory() }, [loadHistory])
  useEffect(() => {
    if (status === 'completed') loadHistory()
  }, [status, loadHistory])

  const handleSymbolSelect = useCallback(({ code, name, market: m }) => {
    setSymbol(code)
    setSymbolName(name)
    if (m) setMarket(m)
  }, [])

  const handlePresetChange = useCallback((preset) => {
    setSelectedPreset(preset)
    setCustomParams({})
  }, [])

  const handleRun = useCallback(() => {
    if (!symbol) return
    reset()
    setViewResult(null)
    setResultMode('single')
    if (strategyMode === 'preset' && selectedPreset) {
      const presetObj = (presets || []).find((p) => (typeof p === 'object' ? (p.id || p.strategy_id) : p) === selectedPreset)
      const presetName = typeof presetObj === 'object' ? presetObj.name : selectedPreset
      // 프리셋 기본값 + 사용자 수정값 병합 (전체 파라미터 저장)
      const fullParams = {}
      const specParams = typeof presetObj === 'object' ? (presetObj.params || presetObj.parameters) : null
      if (specParams) {
        for (const [key, spec] of Object.entries(specParams)) {
          fullParams[key] = customParams[key] ?? (typeof spec === 'object' ? spec.default : spec) ?? spec
        }
      }
      Object.assign(fullParams, customParams)
      const costParams = { commission_rate: commissionRate / 100, tax_rate: taxRate / 100, slippage: slippage / 100 }
      runPreset(selectedPreset, symbol, market, startDate, endDate, initialCash, fullParams, presetName, costParams)
    } else if (strategyMode === 'custom' && yamlContent.trim()) {
      const costParams = { commission_rate: commissionRate / 100, tax_rate: taxRate / 100, slippage: slippage / 100 }
      runCustom(yamlContent, symbol, market, startDate, endDate, initialCash, costParams, undefined, builderYamlState)
    }
  }, [symbol, strategyMode, selectedPreset, yamlContent, market, startDate, endDate, initialCash, commissionRate, taxRate, slippage, customParams, presets, runPreset, runCustom, reset, builderYamlState])

  const handleBatch = useCallback(() => {
    if (!symbol) return
    reset()
    setViewResult(null)
    setResultMode('batch')
    runBatch(DEFAULT_PRESETS_FOR_BATCH, symbol, market, startDate, endDate)
  }, [symbol, market, startDate, endDate, runBatch, reset])

  const handleDelete = useCallback(async (jobId) => {
    try {
      await deleteBacktestJob(jobId)
      loadHistory()
    } catch {
      // 삭제 실패 무시
    }
  }, [loadHistory])

  // 히스토리에서 결과 선택
  const handleHistorySelect = useCallback(async (job) => {
    try {
      const data = await fetchBacktestResult(job.job_id)
      setViewResult(data)
      setResultMode('single')
      reset()
    } catch {
      // 이미 job 자체에 메트릭이 있으면 그대로 표시
      setViewResult(job)
      setResultMode('single')
      reset()
    }
  }, [reset])

  const canRun = symbol && (
    (strategyMode === 'preset' && selectedPreset) ||
    (strategyMode === 'custom' && yamlContent.trim()) ||
    (strategyMode === 'builder')
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
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">종목</label>
          <SymbolSearchBar
            market={market}
            onMarketChange={setMarket}
            symbol={symbol}
            symbolName={symbolName}
            onSymbolSelect={handleSymbolSelect}
            markets={['KR']}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">전략</label>
          <StrategySelector
            presets={presets}
            selectedPreset={selectedPreset}
            yamlContent={yamlContent}
            mode={strategyMode}
            onModeChange={setStrategyMode}
            onPresetChange={handlePresetChange}
            onYamlChange={(yaml) => { setYamlContent(yaml); setBuilderYamlState(null) }}
            customParams={customParams}
            onParamsChange={setCustomParams}
            onBuilderYaml={(yaml, builderState) => {
              setYamlContent(yaml)
              setBuilderYamlState(builderState || null)
              setStrategyMode('custom')
            }}
            onRunSavedStrategy={(strategy) => {
              if (strategy.yaml_content) {
                setYamlContent(strategy.yaml_content)
                setBuilderYamlState(strategy.builder_state_json || null)
                setStrategyMode('custom')
              }
            }}
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">시작일</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">종료일</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">초기자금</label>
            <input type="number" value={initialCash} onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" step={1000000} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">수수료 (%)</label>
            <input type="number" value={commissionRate} onChange={(e) => setCommissionRate(Number(e.target.value))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" step={0.001} min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">세금 (%)</label>
            <input type="number" value={taxRate} onChange={(e) => setTaxRate(Number(e.target.value))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" step={0.01} min={0} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">슬리피지 (%)</label>
            <input type="number" value={slippage} onChange={(e) => setSlippage(Number(e.target.value))}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm" step={0.01} min={0} />
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={handleRun} disabled={!canRun}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            {isRunning ? '실행 중...' : '백테스트 실행'}
          </button>
          <button onClick={handleBatch} disabled={!symbol || isRunning}
            className="px-5 py-2 bg-gray-600 text-white text-sm font-medium rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            전략 비교 (4개)
          </button>
        </div>
      </div>

      {/* 진행 상태 */}
      {isRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-3">
            <LoadingSpinner />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-800">
                {status === 'submitting' ? '전략 제출 중...' : '백테스트 실행 중'}
              </p>
              <p className="text-xs text-blue-600 mt-0.5">
                {status === 'submitting' && 'MCP 서버에 전략을 전송하고 있습니다'}
                {status === 'running' && 'KIS 시세 데이터 수집 + 시뮬레이션 엔진 실행'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-mono text-blue-700">{elapsed}초</p>
              <p className="text-xs text-blue-400">최대 5분</p>
            </div>
          </div>

          {/* 프로그레스 바 (배치 시) */}
          {progress && (
            <div>
              <div className="flex justify-between text-xs text-blue-600 mb-1">
                <span>진행률</span>
                <span>{progress.done}/{progress.total} 전략 완료</span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((progress.done / progress.total) * 100)}%` }} />
              </div>
            </div>
          )}

          {/* 백그라운드 안내 */}
          <div className="bg-green-50 border border-green-200 rounded px-3 py-2 text-xs text-green-700 flex items-start gap-2">
            <span className="mt-0.5">&#x1f4a1;</span>
            <div>
              <p className="font-medium">다른 페이지로 이동해도 괜찮습니다</p>
              <p className="mt-0.5 text-green-600">
                백테스트는 서버에서 실행됩니다. 돌아오면 아래 이력에서 결과를 확인할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {error && <ErrorAlert message={error} />}

      {/* 현재 실행 결과 */}
      {status === 'completed' && resultMode === 'single' && (
        <BacktestResultPanel result={result} symbol={symbol} market={market} />
      )}

      {status === 'completed' && resultMode === 'batch' && (
        <BatchCompareTable result={result} />
      )}

      {/* 히스토리에서 선택한 결과 */}
      {viewResult && status !== 'completed' && (
        <BacktestResultPanel result={viewResult} symbol={viewResult.symbol} market={viewResult.market} />
      )}

      {status === 'timeout' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            백테스트 시간이 초과되었습니다. 아래 이력에서 나중에 결과를 확인하세요.
          </p>
        </div>
      )}

      {/* 이력 */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">백테스트 이력</h2>
        <BacktestHistoryTable
          history={history}
          onSelect={handleHistorySelect}
          onDelete={handleDelete}
          loading={historyLoading}
        />
      </div>
    </div>
  )
}
