/**
 * ExchangeBadge — 거래소 배지 공용 컴포넌트.
 *
 * KIS H0STCNI0.ORD_EXG_GB 매핑:
 *   1=KRX / 2=NXT / 3=SOR-KRX / 4=SOR-NXT
 * + Pre-trade 사용자 입력값:
 *   SOR (PENDING/PLACED 시점, KIS 라우팅 결과 도착 전)
 *
 * 사용처: OpenOrdersTable, ExecutionsTable, OrderHistoryTable, 토스트.
 *
 * 누락/legacy(NULL) 값은 'KRX' 폴백 — orders.exchange=NULL 인 기존 데이터 호환.
 */
const VARIANTS = {
  KRX: {
    icon: '■',
    label: 'KRX',
    cls: 'bg-blue-100 text-blue-700 border-blue-200',
  },
  NXT: {
    icon: '◆',
    label: 'NXT',
    cls: 'bg-green-100 text-green-700 border-green-200',
  },
  SOR: {
    icon: '⚡',
    label: 'SOR',
    cls: 'bg-purple-100 text-purple-700 border-purple-200',
  },
  'SOR-KRX': {
    icon: '⚡',
    label: 'SOR→KRX',
    cls: 'bg-purple-100 text-purple-700 border-purple-200',
  },
  'SOR-NXT': {
    icon: '⚡',
    label: 'SOR→NXT',
    cls: 'bg-purple-100 text-purple-700 border-purple-200',
  },
}

export default function ExchangeBadge({ exchange, size = 'sm' }) {
  const v = VARIANTS[exchange] || { icon: '■', label: 'KRX', cls: 'bg-blue-100 text-blue-700 border-blue-200' }
  const padding = size === 'xs' ? 'px-1.5 py-0' : 'px-2 py-0.5'
  const text = size === 'xs' ? 'text-[10px]' : 'text-xs'
  return (
    <span className={`inline-flex items-center gap-0.5 ${padding} ${text} rounded-full border font-medium ${v.cls}`}>
      <span aria-hidden>{v.icon}</span>
      <span>{v.label}</span>
    </span>
  )
}
