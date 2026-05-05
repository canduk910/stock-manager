import { useEffect, useRef, useState } from 'react'
import { chatAboutAdvisory, chatAboutPortfolio } from '../../api/chatbot'

const ADVISORY_SUGGESTIONS = [
  '이 보고서의 등급과 그 근거를 요약해줘',
  '주요 리스크 요인은 무엇이야?',
  '진입가/손절가는 어떻게 책정됐어?',
]

const PORTFOLIO_SUGGESTIONS = [
  '진단 핵심 결론을 한 줄로 요약해줘',
  '리밸런싱 우선순위가 가장 높은 종목은?',
  '시장 코멘트의 요지는 무엇이야?',
]

function MessageBubble({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser ? 'bg-indigo-100 text-gray-900' : 'bg-gray-100 text-gray-800'
        }`}
      >
        {content}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 rounded-2xl px-3 py-2 text-sm text-gray-500">
        <span className="inline-block animate-pulse">●</span>
        <span className="inline-block animate-pulse delay-150 ml-1">●</span>
        <span className="inline-block animate-pulse delay-300 ml-1">●</span>
      </div>
    </div>
  )
}

export default function ReportChatBubble({
  kind, // 'advisory' | 'portfolio'
  contextId,
  contextLabel,
  market,
  code,
  disabled = false,
}) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)
  const abortRef = useRef(null)

  // contextId 변경 시 대화 초기화
  useEffect(() => {
    setMessages([])
    setInput('')
    setError(null)
  }, [contextId, kind])

  // 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, pending])

  // unmount 시 진행중 요청 취소
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const isReady = !!contextId && !disabled

  const send = async (text) => {
    const trimmed = (text ?? input).trim()
    if (!trimmed || pending || !isReady) return
    const next = [...messages, { role: 'user', content: trimmed }]
    setMessages(next)
    setInput('')
    setPending(true)
    setError(null)
    try {
      const apiCall =
        kind === 'advisory'
          ? () => chatAboutAdvisory(code, market || 'KR', contextId, next)
          : () => chatAboutPortfolio(contextId, next)
      const data = await apiCall()
      setMessages((m) => [...m, { role: 'assistant', content: data.reply || '(빈 응답)' }])
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
    } catch (e) {
      setError(e?.message || '응답 생성에 실패했습니다.')
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
    } finally {
      setPending(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const suggestions = kind === 'advisory' ? ADVISORY_SUGGESTIONS : PORTFOLIO_SUGGESTIONS
  const headerLabel = kind === 'advisory'
    ? `${contextLabel || code || '종목'} 자문 챗봇`
    : '포트폴리오 자문 챗봇'

  // 닫힘 — 플로팅 버튼
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={!isReady}
        className={`fixed bottom-6 right-6 z-40 rounded-full p-4 shadow-lg transition ${
          isReady
            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        title={isReady ? '보고서에 대해 질문하기' : '보고서 생성 후 이용 가능합니다'}
        aria-label="보고서 챗봇 열기"
      >
        <span className="text-xl">💬</span>
      </button>
    )
  }

  // 열림 — 챗 패널
  return (
    <div className="fixed bottom-6 right-6 left-4 sm:left-auto sm:w-96 max-h-[70vh] z-40 bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col">
      <div className="bg-indigo-600 text-white px-4 py-3 rounded-t-2xl flex items-center justify-between">
        <div className="text-sm font-semibold truncate">{headerLabel}</div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-white/80 hover:text-white text-lg leading-none"
          aria-label="챗봇 닫기"
        >
          ×
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2 min-h-[160px]">
        {messages.length === 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 leading-relaxed">
              이 보고서 내용에 대해 질문해보세요. 답변은 보고서에 수록된 범위 안에서만 제공됩니다.
            </div>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="text-[11px] px-2 py-1 rounded-full border border-indigo-300 text-indigo-700 hover:bg-indigo-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} />
        ))}
        {pending && <TypingIndicator />}
      </div>

      {error && (
        <div className="px-3 py-2 text-xs text-red-700 bg-red-50 border-t border-red-200">
          {error}
        </div>
      )}

      <div className="border-t border-gray-200 p-2 flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          placeholder="보고서에 대해 질문해보세요..."
          className="flex-1 resize-none border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
          disabled={pending || !isReady}
        />
        <button
          type="button"
          onClick={() => send()}
          disabled={pending || !input.trim() || !isReady}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40"
        >
          전송
        </button>
      </div>
    </div>
  )
}
