/**
 * 주문 발송 폼.
 * 시장/종목은 상위(OrderPage)에서 공유 상태로 관리 — props로 받음.
 * 매매방향/주문유형/가격/수량/메모만 내부 상태 관리.
 */
import { useState, useEffect } from 'react'
import { useBuyable } from '../../hooks/useOrder'

const SIDE_OPTIONS = [
  { value: 'buy', label: '매수' },
  { value: 'sell', label: '매도' },
]

const ORDER_TYPE_OPTIONS = [
  { value: '00', label: '지정가' },
  { value: '01', label: '시장가' },
]

// KR 거래소 셀렉터 (2026-05-08 사용자 결정 SOR/KRX/NXT 3개, SOR 기본).
// 통합(UN)은 시세 전용 코드 → 주문값 X.
// SOR: KIS Smart Order Routing — KRX/NXT 중 가격 유리한 곳 자동 라우팅.
// KRX: KOSPI/KOSDAQ 단독 (15:30~15:40 동시호가/마감 시간대에 강제).
// NXT: 넥스트레이드 단독 (08:00~09:00 / 15:40~20:00 시간외).
const KR_EXCHANGE_OPTIONS = [
  { value: 'SOR', label: 'SOR', desc: '자동 라우팅 (권장)' },
  { value: 'KRX', label: 'KRX', desc: 'KOSPI/KOSDAQ' },
  { value: 'NXT', label: 'NXT', desc: '넥스트레이드' },
]

// FNO: 4가지 주문유형
const FNO_ORDER_TYPE_OPTIONS = [
  { value: 'limit',       label: '지정가' },
  { value: 'market',      label: '시장가' },
  { value: 'conditional', label: '조건부지정가' },
  { value: 'best',        label: '최유리지정가' },
]

// FNO: 호가조건 (조건부지정가는 IOC/FOK 미지원)
const FNO_CONDITION_OPTIONS = [
  { value: 'normal', label: '없음' },
  { value: 'ioc',    label: 'IOC' },
  { value: 'fok',    label: 'FOK' },
]

// FNO 주문유형 → KIS 코드 매핑
function mapFnoOrderCodes(orderType, condition) {
  const nmprMap = { limit: '01', market: '02', conditional: '03', best: '04' }
  const cndtMap = { normal: '0', ioc: '3', fok: '4' }
  const ordDvsnMap = {
    'limit_normal': '01', 'market_normal': '02', 'conditional_normal': '03', 'best_normal': '04',
    'limit_ioc': '10', 'limit_fok': '11', 'market_ioc': '12', 'market_fok': '13',
    'best_ioc': '14', 'best_fok': '15',
  }
  const nmpr = nmprMap[orderType] || '01'
  const cndt = cndtMap[condition] || '0'
  const ordDvsn = ordDvsnMap[`${orderType}_${condition}`] || nmpr
  return { nmpr_type_cd: nmpr, krx_nmpr_cndt_cd: cndt, ord_dvsn_cd: ordDvsn }
}

export default function OrderForm({
  symbol = '',
  symbolName = '',
  market = 'KR',
  defaultValues = {},
  onConfirm,
  externalPrice = null,
  externalSide = null,
  isSimulation = false,
}) {
  const [side, setSide] = useState(defaultValues.side || 'buy')
  const [orderType, setOrderType] = useState('00')
  const [fnoOrderType, setFnoOrderType] = useState('limit')
  const [fnoCondition, setFnoCondition] = useState('normal')
  const [price, setPrice] = useState(defaultValues.price || '')
  const [quantity, setQuantity] = useState(defaultValues.quantity || '')
  const [memo, setMemo] = useState('')
  // KR 거래소 셀렉터 — 모의투자는 KRX 강제(NXT/SOR 미지원)
  const [exchange, setExchange] = useState(isSimulation ? 'KRX' : 'SOR')

  // 모의투자 환경 감지 시 SOR/NXT 선택 차단
  useEffect(() => {
    if (isSimulation && exchange !== 'KRX') setExchange('KRX')
  }, [isSimulation]) // eslint-disable-line

  const { data: buyable, loading: buyableLoading, load: loadBuyable } = useBuyable()

  // 잔고 연계 defaultValues 반영
  useEffect(() => {
    if (defaultValues.side) setSide(defaultValues.side)
    if (defaultValues.price) setPrice(String(defaultValues.price))
    if (defaultValues.quantity) setQuantity(String(defaultValues.quantity))
  }, [defaultValues.side, defaultValues.price, defaultValues.quantity])

  // 호가창 가격 클릭 → 지정가 자동 세팅
  useEffect(() => {
    if (externalPrice != null && orderType !== '01') {
      setPrice(String(externalPrice))
    }
  }, [externalPrice]) // eslint-disable-line

  // 호가창 side 클릭 → 매매방향 자동 세팅
  useEffect(() => {
    if (externalSide != null) setSide(externalSide)
  }, [externalSide])

  const isFNO = market === 'FNO'

  // 조건부지정가는 IOC/FOK 미지원 → normal 자동 리셋
  useEffect(() => {
    if (isFNO && fnoOrderType === 'conditional') {
      setFnoCondition('normal')
    }
  }, [fnoOrderType, isFNO])

  // FNO 시장가/최유리는 가격 불필요
  const isFnoMarketLike = isFNO && (fnoOrderType === 'market' || fnoOrderType === 'best')

  const handleBuyableCheck = () => {
    if (!symbol) return
    if (isFNO) {
      const codes = mapFnoOrderCodes(fnoOrderType, fnoCondition)
      loadBuyable(symbol, market, price || 0, codes.ord_dvsn_cd || '01', side)
    } else {
      loadBuyable(symbol, market, price || 0, orderType, side)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!symbol || !quantity) return
    const body = {
      symbol: symbol.trim().toUpperCase(),
      symbol_name: symbolName.trim(),
      market,
      side,
      order_type: orderType,
      price: (orderType === '01' || isFnoMarketLike) ? 0 : Number(price) || 0,
      quantity: Number(quantity),
      memo,
    }
    // FNO 전용 필드
    if (isFNO) {
      const codes = mapFnoOrderCodes(fnoOrderType, fnoCondition)
      body.nmpr_type_cd = codes.nmpr_type_cd
      body.krx_nmpr_cndt_cd = codes.krx_nmpr_cndt_cd
      body.ord_dvsn_cd = codes.ord_dvsn_cd
    }
    // KR 거래소 셀렉터 (US/FNO 무시 — 백엔드는 KR 외 시장에서 exchange 컬럼을 NULL 보존)
    if (market === 'KR') {
      body.exchange = exchange
    }
    onConfirm(body)
  }

  const isMarketOrder = orderType === '01'
  const isBuy = side === 'buy'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 종목 미선택 안내 */}
      {!symbol && (
        <p className="text-xs text-amber-600 bg-amber-50 rounded px-3 py-2">
          위 검색창에서 종목을 먼저 선택해주세요
        </p>
      )}

      {/* 거래소 셀렉터 (KR 전용, 2026-05-08) */}
      {market === 'KR' && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-medium text-gray-600">거래소</label>
            {isSimulation && (
              <span className="text-[10px] text-amber-600">모의투자: KRX만 가능</span>
            )}
          </div>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            {KR_EXCHANGE_OPTIONS.map((o) => {
              const disabled = isSimulation && o.value !== 'KRX'
              const selected = exchange === o.value
              return (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => !disabled && setExchange(o.value)}
                  disabled={disabled}
                  title={o.desc}
                  className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
                    selected
                      ? 'bg-purple-600 text-white'
                      : disabled
                        ? 'text-gray-300 bg-gray-50 cursor-not-allowed'
                        : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {o.label}
                </button>
              )
            })}
          </div>
          <p className="mt-1 text-[10px] text-gray-400">
            {exchange === 'SOR' && '⚡ KRX/NXT 중 가격 유리한 곳 자동 라우팅'}
            {exchange === 'KRX' && '■ KOSPI/KOSDAQ 단독'}
            {exchange === 'NXT' && '◆ 넥스트레이드 단독 (08~09시 / 15:40~20시)'}
          </p>
        </div>
      )}

      {/* 매매 방향 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">매매 방향</label>
        <div className="flex rounded border border-gray-300 overflow-hidden">
          {SIDE_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setSide(o.value)}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${
                side === o.value
                  ? o.value === 'buy'
                    ? 'bg-red-600 text-white'
                    : 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* 주문 유형 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">주문 유형</label>
        <div className="flex rounded border border-gray-300 overflow-hidden">
          {isFNO
            ? FNO_ORDER_TYPE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setFnoOrderType(o.value)}
                  className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
                    fnoOrderType === o.value
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {o.label}
                </button>
              ))
            : ORDER_TYPE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setOrderType(o.value)}
                  className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
                    orderType === o.value
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {o.label}
                </button>
              ))
          }
        </div>
      </div>

      {/* FNO 호가조건 (없음/IOC/FOK) */}
      {isFNO && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">호가조건</label>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            {FNO_CONDITION_OPTIONS.map((o) => {
              const disabled = fnoOrderType === 'conditional' && o.value !== 'normal'
              return (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => !disabled && setFnoCondition(o.value)}
                  disabled={disabled}
                  className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
                    fnoCondition === o.value
                      ? 'bg-gray-700 text-white'
                      : disabled
                        ? 'text-gray-300 bg-gray-50 cursor-not-allowed'
                        : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {o.label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* 가격 / 수량 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            주문가격 {isMarketOrder && <span className="text-gray-400">(시장가)</span>}
          </label>
          <input
            type="number"
            value={(isMarketOrder || isFnoMarketLike) ? '' : price}
            onChange={(e) => setPrice(e.target.value)}
            disabled={isMarketOrder || isFnoMarketLike}
            placeholder={(isMarketOrder || isFnoMarketLike) ? '자동' : market === 'US' ? 'USD' : isFNO ? '포인트/원' : '원'}
            min="0"
            step={market === 'US' ? '0.01' : isFNO ? '0.01' : '1'}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm disabled:bg-gray-50 disabled:text-gray-400"
            required={!isMarketOrder && !isFnoMarketLike}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">수량</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="주"
            min="1"
            step="1"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            required
          />
        </div>
      </div>

      {/* 매수가능 조회 */}
      {isBuy && (
        <div className="bg-gray-50 rounded p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">매수가능 조회</span>
            <button
              type="button"
              onClick={handleBuyableCheck}
              disabled={buyableLoading || !symbol}
              className="text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
            >
              {buyableLoading ? '조회 중...' : '조회'}
            </button>
          </div>
          {buyable && (
            <div className="text-xs text-gray-700 space-y-0.5">
              {/* REQ-FE-10: US 시장은 USD + KRW + 환율 동시 표시
                  환율 조회 실패(buyable_amount_krw == null) 시 USD만 표시 (graceful degrade) */}
              {market === 'US' && buyable.buyable_amount_krw != null && buyable.usd_krw_rate != null ? (
                <>
                  <div>
                    가능금액: <span className="font-medium">${Number(buyable.buyable_amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    <span className="text-gray-500 ml-1">(₩{Math.floor(Number(buyable.buyable_amount_krw)).toLocaleString()})</span>
                  </div>
                  <div>가능수량: <span className="font-medium">{Number(buyable.buyable_quantity).toLocaleString()}주</span></div>
                  <div className="text-gray-500">환율: <span className="font-medium">₩{Math.floor(Number(buyable.usd_krw_rate)).toLocaleString()}/USD</span></div>
                </>
              ) : (
                <>
                  <div>가능금액: <span className="font-medium">{Number(buyable.buyable_amount).toLocaleString()} {buyable.currency}</span></div>
                  <div>가능수량: <span className="font-medium">{Number(buyable.buyable_quantity).toLocaleString()}주</span></div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* 메모 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">메모 (선택)</label>
        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="주문 메모"
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        />
      </div>

      {/* 주문 버튼 */}
      <button
        type="submit"
        disabled={!symbol}
        className={`w-full py-2.5 rounded font-semibold text-sm text-white transition-colors disabled:opacity-40 ${
          isBuy ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isBuy ? '매수' : '매도'} 주문 확인
      </button>
    </form>
  )
}
