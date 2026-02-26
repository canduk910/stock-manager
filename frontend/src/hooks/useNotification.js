import { useState, useCallback, useRef } from 'react'

let _toastIdCounter = 0

/** 토스트 알림 + 브라우저 Notification API 관리 훅 */
export function useNotification() {
  const [toasts, setToasts] = useState([])
  const timerRefs = useRef({})

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = ++_toastIdCounter
    setToasts((prev) => [...prev, { id, message, type }])

    if (duration > 0) {
      timerRefs.current[id] = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
        delete timerRefs.current[id]
      }, duration)
    }
    return id
  }, [])

  const removeToast = useCallback((id) => {
    if (timerRefs.current[id]) {
      clearTimeout(timerRefs.current[id])
      delete timerRefs.current[id]
    }
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const notify = useCallback(
    (message, type = 'info', duration = 5000) => {
      addToast(message, type, duration)
      // 브라우저 알림 (탭 비활성 시)
      if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
        new Notification('DK STOCK', { body: message })
      }
    },
    [addToast],
  )

  const requestPermission = useCallback(async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission()
    }
  }, [])

  return { toasts, notify, removeToast, requestPermission }
}
