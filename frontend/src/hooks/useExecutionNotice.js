import { useEffect, useRef, useCallback } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

/**
 * 체결통보(H0STCNI0) 실시간 수신 훅.
 * @param {function} onNotice - 체결통보 수신 콜백 ({type, order_no, symbol, side, filled_qty, filled_price, ...})
 */
export function useExecutionNotice(onNotice) {
  const cbRef = useRef(onNotice)
  cbRef.current = onNotice

  const onMessage = useCallback((msg) => {
    if (msg.type === 'execution_notice') {
      cbRef.current?.(msg)
    }
  }, [])

  useWebSocket(buildWsUrl('/ws/execution-notice'), { onMessage })
}
