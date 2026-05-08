import { useEffect, useRef, useCallback } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

// 모듈 스코프 안정 인스턴스. 매 connect 시점마다 lazy 평가되어 최신 access_token 반영.
const buildExecutionNoticeUrl = () => buildWsUrl('/ws/execution-notice')

// H0STCNI0 ORD_EXG_GB 매핑 (KIS docs/kis/09_KR_REALTIME.md:504)
//   1=KRX / 2=NXT / 3=SOR-KRX / 4=SOR-NXT
const ORD_EXG_GB_MAP = {
  '1': 'KRX',
  '2': 'NXT',
  '3': 'SOR-KRX',
  '4': 'SOR-NXT',
}

/** ORD_EXG_GB 코드를 거래소 라벨로 매핑. 누락/미지원 값은 'KRX' 폴백(legacy 보존). */
export function mapOrdExgGb(code) {
  return ORD_EXG_GB_MAP[String(code || '').trim()] || 'KRX'
}

/**
 * 체결통보(H0STCNI0) 실시간 수신 훅.
 * @param {function} onNotice - 체결통보 수신 콜백
 *   ({type, order_no, symbol, side, filled_qty, filled_price, ord_exg_gb, exchange, ...})
 *   - exchange: ord_exg_gb 매핑 결과 (KRX/NXT/SOR-KRX/SOR-NXT). UI 토스트/배지에서 그대로 사용.
 */
export function useExecutionNotice(onNotice) {
  const cbRef = useRef(onNotice)
  cbRef.current = onNotice

  const onMessage = useCallback((msg) => {
    if (msg.type === 'execution_notice') {
      // 백엔드 _parse_notice 가 ord_exg_gb 토큰을 응답에 포함시키면 그대로 매핑.
      // 토큰 미확정 시 백엔드는 ord_exg_gb 미포함 → 'KRX' 폴백.
      const enriched = { ...msg, exchange: mapOrdExgGb(msg.ord_exg_gb) }
      cbRef.current?.(enriched)
    }
  }, [])

  useWebSocket(buildExecutionNoticeUrl, { onMessage })
}
