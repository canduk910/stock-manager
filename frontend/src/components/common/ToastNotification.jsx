/**
 * 화면 우상단 토스트 알림 컨테이너.
 * useNotification 훅의 toasts / removeToast를 받아 렌더링한다.
 */
const TYPE_STYLES = {
  success: 'bg-green-600 text-white',
  error:   'bg-red-600 text-white',
  warning: 'bg-yellow-500 text-white',
  info:    'bg-gray-800 text-white',
}

const TYPE_ICONS = {
  success: '✓',
  error:   '✗',
  warning: '!',
  info:    'ℹ',
}

export default function ToastNotification({ toasts, removeToast }) {
  if (!toasts || toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium
            animate-in slide-in-from-right-5 fade-in duration-200
            ${TYPE_STYLES[toast.type] || TYPE_STYLES.info}`}
        >
          <span className="font-bold text-base leading-none mt-0.5">
            {TYPE_ICONS[toast.type] || TYPE_ICONS.info}
          </span>
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="opacity-70 hover:opacity-100 text-lg leading-none ml-1"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
