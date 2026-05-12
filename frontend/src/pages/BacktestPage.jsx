/**
 * 백테스트 페이지 (/backtest).
 *
 * KIS AI Extensions MCP 서버 연동으로 전략 백테스트를 실행한다.
 * 히스토리 테이블로 과거 실행 결과를 조회할 수 있다.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import SymbolSearchBar from '../components/order/SymbolSearchBar'
import SymbolMultiInput from '../components/backtest/SymbolMultiInput'
import StrategySelector from '../components/backtest/StrategySelector'
import BacktestResultPanel from '../components/backtest/BacktestResultPanel'
import BatchCompareTable from '../components/backtest/BatchCompareTable'
import BacktestHistoryTable from '../components/backtest/BacktestHistoryTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import {
  useMcpStatus, usePresets, useLocalPresets, useBacktest, useBacktestHistory,
} from '../hooks/useBacktest'
import { fetchBacktestResult, deleteBacktestJob } from '../api/backtest'

const DEFAULT_PRESETS_FOR_BATCH = ['sma_crossover', 'momentum', 'trend_filter_signal', 'volatility_breakout']

export default function BacktestPage() {
  const { available: mcpAvailable, loading: mcpLoading } = useMcpStatus()
  const { presets, load: loadPresets } = usePresets()
  const { presets: localPresets, load: loadLocalPresets } = useLocalPresets()
  const {
    status, result, error, progress,
    runPreset, runCustom, runBatch, runLocal, reset,
  } = useBacktest()
  const { history, loading: historyLoading, load: loadHistory } = useBacktestHistory()

  const [market, setMarket] = useState('KR')
  const [symbol, setSymbol] = useState('')
  const [symbolName, setSymbolName] = useState('')
  // 로컬 프리셋(다중 종목) 모드 전용 — 칩 리스트
  const [multiSymbols, setMultiSymbols] = useState([]) // [{code, name}]
  // 단위 토글: 'single'(종목 단위) | 'portfolio'(포트폴리오 단위)
  // - single  → 전략 탭은 builder/preset/custom 노출, local-preset 숨김
  // - portfolio → local-preset 단독 노출, multiSymbols 입력 사용
  const [unitMode, setUnitMode] = useState('single')
  const [strategyMode, setStrategyMode] = useState('builder')
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

  // 로컬 프리셋은 MCP 무관 — 마운트 시 즉시 로드
  useEffect(() => {
    loadLocalPresets()
  }, [loadLocalPresets])

  // 모드 전환 시 선택값 초기화 (mcp/local preset 사이 ID 충돌 방지)
  useEffect(() => {
    setSelectedPreset('')
    setCustomParams({})
  }, [strategyMode])

  // 단위 토글 변경 → 전략 모드 자동 보정
  // - portfolio: local-preset 강제
  // - single   : 현재가 local-preset이면 builder로 폴백 (그 외 유지)
  useEffect(() => {
    if (unitMode === 'portfolio') {
      if (strategyMode !== 'local-preset') setStrategyMode('local-preset')
    } else if (unitMode === 'single') {
      if (strategyMode === 'local-preset') setStrategyMode('builder')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitMode])

  // StrategySelector에 전달할 노출 모드 화이트리스트
  const allowedStrategyModes = unitMode === 'portfolio'
    ? ['local-preset']
    : ['builder', 'preset', 'custom']

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
    // 로컬 프리셋: 다중 종목 분기
    if (strategyMode === 'local-preset') {
      if (!selectedPreset || multiSymbols.length === 0) return
      reset()
      setViewResult(null)
      setResultMode('single')
      const codes = multiSymbols.map((s) => s.code)
      const presetObj = (localPresets || []).find((p) => (p.id || p.strategy_id) === selectedPreset)
      const fullParams = {}
      const specParams = presetObj && (presetObj.params || presetObj.parameters)
      if (specParams) {
        for (const [key, spec] of Object.entries(specParams)) {
          fullParams[key] = customParams[key] ?? (typeof spec === 'object' ? spec.default : spec) ?? spec
        }
      }
      Object.assign(fullParams, customParams)
      runLocal({
        preset: selectedPreset,
        symbols: codes,
        market: 'KR',
        startDate,
        endDate,
        initialCapital: initialCash,
        commissionRate: commissionRate / 100,
        taxRate: taxRate / 100,
        slippage: slippage / 100,
        params: fullParams,
      })
      return
    }
    // MCP 단일 종목 흐름
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
    } else if ((strategyMode === 'custom' || strategyMode === 'builder') && yamlContent.trim()) {
      const costParams = { commission_rate: commissionRate / 100, tax_rate: taxRate / 100, slippage: slippage / 100 }
      runCustom(yamlContent, symbol, market, startDate, endDate, initialCash, costParams, undefined, builderYamlState)
    }
  }, [symbol, strategyMode, selectedPreset, multiSymbols, yamlContent, market, startDate, endDate, initialCash, commissionRate, taxRate, slippage, customParams, presets, localPresets, runPreset, runCustom, runLocal, reset, builderYamlState])

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

  const canRun = (
    (strategyMode === 'local-preset' && selectedPreset && multiSymbols.length > 0) ||
    (
      symbol && (
        (strategyMode === 'preset' && selectedPreset) ||
        (strategyMode === 'custom' && yamlContent.trim()) ||
        (strategyMode === 'builder')
      )
    )
  ) && !isRunning

  // MCP 비활성화 시 안내 (로컬 프리셋은 MCP 무관 → 안내만 띄우되 페이지는 그대로 사용)
  // 기존 풀화면 차단 → 상단 배너로 변경하여 로컬 프리셋 사용 가능하도록 함.
  // (로컬 프리셋 4개는 MCP 없이 stock-manager 내부 엔진으로 실행)

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-gray-900">백테스트</h1>
          {/* 단위 토글 — segment control 스타일 */}
          <div
            role="group"
            aria-label="백테스트 단위 선택"
            className="inline-flex rounded-lg border border-gray-300 bg-gray-50 p-0.5 text-xs"
          >
            <button
              type="button"
              onClick={() => setUnitMode('single')}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                unitMode === 'single'
                  ? 'bg-white text-blue-700 shadow-sm border border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="단일 종목 백테스트 (빌더 / MCP 프리셋 / 커스텀)"
            >
              종목
            </button>
            <button
              type="button"
              onClick={() => setUnitMode('portfolio')}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                unitMode === 'portfolio'
                  ? 'bg-white text-blue-700 shadow-sm border border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title="포트폴리오 백테스트 (로컬 프리셋, 최대 10종목 균등 배분)"
            >
              포트폴리오
            </button>
          </div>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
          mcpAvailable ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          MCP {mcpAvailable ? '연결됨' : '미연결'}
        </span>
      </div>

      {/* MCP 비활성화 시 상단 안내 (로컬 프리셋은 사용 가능) */}
      {!mcpLoading && !mcpAvailable && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-xs text-yellow-800">
          <b>KIS MCP 서버 미연결</b> — 빌더/프리셋(MCP)/커스텀 YAML 모드는 사용할 수 없습니다.
          {' '}<b className="text-emerald-700">로컬 프리셋</b> 탭은 MCP 없이 즉시 실행 가능합니다.
        </div>
      )}

      {/* 설정 패널 */}
      <div className="bg-white rounded-lg border p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {unitMode === 'portfolio' ? '종목 (1~10개, 균등 배분)' : '종목'}
          </label>
          {unitMode === 'portfolio' ? (
            <SymbolMultiInput
              symbols={multiSymbols}
              onChange={setMultiSymbols}
              maxItems={10}
              disabled={isRunning}
            />
          ) : (
            <SymbolSearchBar
              market={market}
              onMarketChange={setMarket}
              symbol={symbol}
              symbolName={symbolName}
              onSymbolSelect={handleSymbolSelect}
              markets={['KR']}
            />
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">전략</label>
          <StrategySelector
            presets={presets}
            localPresets={localPresets}
            selectedPreset={selectedPreset}
            yamlContent={yamlContent}
            mode={strategyMode}
            onModeChange={setStrategyMode}
            allowedModes={allowedStrategyModes}
            onPresetChange={handlePresetChange}
            onYamlChange={(yaml) => { setYamlContent(yaml); setBuilderYamlState(null) }}
            customParams={customParams}
            onParamsChange={setCustomParams}
            onBuilderYaml={(yaml, builderState) => {
              setYamlContent(yaml)
              setBuilderYamlState(builderState || null)
            }}
            onRunSavedStrategy={(strategy) => {
              if (strategy.yaml_content) {
                setYamlContent(strategy.yaml_content)
                setBuilderYamlState(strategy.builder_state_json || null)
                setStrategyMode('custom')
                // 저장 전략 실행 시 단위는 'single'로 자동 전환
                setUnitMode('single')
              }
            }}
          />
        </div>

        {/* 백테스트 가용 기간 가이드 (2026-05-05) — 출처 + 추정값 명시 */}
        <div className="text-[11px] text-gray-600 bg-blue-50 border border-blue-200 rounded px-3 py-2 mb-3">
          <div className="font-semibold text-blue-900 mb-1">📅 백테스트 가용 기간 가이드</div>
          <ul className="space-y-0.5 list-disc pl-4">
            <li>
              <b>US</b>: 일봉 기준 <b>1998-01-02 이후</b> 가용 (QuantConnect Lean 공식 데이터 패키지).
              종목 상장 이전 시점은 자동으로 잘립니다.
            </li>
            <li>
              <b>KR</b>: 일봉 기준 <b>2000-01-04 이후</b> 가용 (KIS API inquire-daily-itemchartprice).
              ETF는 상장일 이후만 의미 있음 — 추후 종목 메타에서 자동 안내 예정.
            </li>
            <li>
              <b>권장 기간</b>: 통계적 의미가 있으려면 최소 <b>1년(252영업일)</b>, 사이클 1회 이상은 <b>5~10년</b> 권장.
              범위가 너무 길면 Lean 백테스트 메모리/실행 시간이 증가합니다.
            </li>
            <li className="text-gray-500">
              ※ 정확한 한계는 운영 환경 Lean Data 폴더에 따릅니다 — 위 추정값은 공식 가용 범위 기준.
              실제로는 이른 시작일을 넣어도 Lean이 자동으로 첫 데이터 시점부터 시작합니다.
            </li>
          </ul>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              시작일
              <span className="ml-1 text-gray-400">
                (US ≥ 1998-01-02 / KR ≥ 2000-01-04 권장)
              </span>
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              min={market === 'US' ? '1998-01-02' : '2000-01-04'}
              max={today}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">종료일</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={startDate}
              max={today}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
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
