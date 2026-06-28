/**
 * 종합리포트 PDF 문서 — off-screen 숨김 렌더 + 자동 캡처 컴포넌트.
 *
 * DetailPage가 `exporting` 상태일 때만 조건부 마운트한다. 화면 밖
 * (position:fixed; left:-10000px) 고정 폭 컨테이너에 표지/기본적분석/AI자문
 * 3블록을 렌더하고, Recharts 애니메이션 정착을 기다린 뒤 html2canvas-pro로
 * 캡처해 단일 PDF로 저장한 후 onDone()을 호출한다.
 *
 * 숨김 방식 주의: display:none 금지 — none이면 ResponsiveContainer 크기가
 *   0으로 계산돼 차트가 비어 캡처된다. off-screen + 명시 폭(760px)으로 처리.
 *
 * 데이터: 이미 로드된 advData/report 재사용(추가 API 호출 0). report 부재 시
 *   표지 + 기본적분석만 출력하고 AI자문은 "미생성" 안내 박스로 대체.
 */
import { useEffect, useRef } from 'react'
import FundamentalPanel from './FundamentalPanel'
import AIReportPanel from './AIReportPanel'
import { exportSectionsToPdf } from '../../utils/pdfExport'

// 캔버스 정착 대기(ms) — Recharts 애니메이션(기본 ~1500ms) 완료 후 캡처
const SETTLE_MS = 1800
// 숨김 컨테이너 고정 폭(px) — ResponsiveContainer 0폭 방지
const DOC_WIDTH = 760

function pad2(n) {
  return String(n).padStart(2, '0')
}

function ymd(d) {
  return `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}`
}

function fmtDateTime(iso) {
  if (!iso) return null
  // 'YYYY-MM-DDTHH:MM...' → 'YYYY-MM-DD HH:MM'
  return String(iso).slice(0, 16).replace('T', ' ')
}

export default function ReportPdfDocument({ advData, report, meta = {}, onDone }) {
  const rootRef = useRef(null)
  // StrictMode 이중 마운트/리렌더에도 캡처 1회만 수행
  const startedRef = useRef(false)

  const { code, name, market } = meta
  const displayName = name || code || '종목'

  // 등급 요약(부재 시 숨김)
  const grade = report?.grade ?? report?.report?.['종목등급'] ?? null
  const gradeScore = report?.grade_score ?? report?.report?.['등급점수'] ?? null
  const compositeScore = report?.composite_score ?? report?.report?.['복합점수'] ?? null
  const generatedAt = fmtDateTime(report?.generated_at)
  const nowStr = fmtDateTime(new Date().toISOString())
  const hasReport = !!report

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    let cancelled = false

    const run = async () => {
      // rAF ×2 + 정착 대기로 차트 애니메이션/레이아웃 안정화
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
      await new Promise((r) => setTimeout(r, SETTLE_MS))
      if (cancelled) return

      try {
        const root = rootRef.current
        const els = root ? Array.from(root.querySelectorAll('[data-pdf]')) : []
        const filename = `${displayName}_종합리포트_${ymd(new Date())}.pdf`
        await exportSectionsToPdf(els, { filename, scale: 2 })
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('[ReportPdfDocument] PDF 생성 실패:', e)
        if (!cancelled) {
          // 사용자에게 최소 피드백(토스트 인프라 미연동 영역이라 alert로 폴백)
          window.alert('PDF 생성에 실패했습니다. 차트 로딩 후 다시 시도해주세요.')
        }
      } finally {
        if (!cancelled && onDone) onDone()
      }
    }

    run()
    return () => {
      cancelled = true
    }
    // 마운트 1회만 — 의존성 비움 (의도적)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={rootRef}
      aria-hidden="true"
      style={{
        position: 'fixed',
        left: '-10000px',
        top: 0,
        width: `${DOC_WIDTH}px`,
        background: '#ffffff',
        zIndex: -1,
        pointerEvents: 'none',
      }}
    >
      {/* ── 표지 ── */}
      <div data-pdf style={{ width: `${DOC_WIDTH}px`, background: '#ffffff' }} className="p-8">
        <div className="border-2 border-gray-300 rounded-2xl p-10">
          <p className="text-xs font-semibold tracking-widest text-indigo-500 mb-6">
            STOCK MANAGER · 종합 리포트
          </p>
          <h1 className="text-3xl font-black text-gray-900 mb-1">{displayName}</h1>
          <p className="text-sm text-gray-500 mb-8">
            {code} · {market === 'US' ? '미국(US)' : '국내(KR)'}
          </p>

          {grade != null && (
            <div className="flex items-center gap-4 mb-8">
              <span className="inline-flex items-center justify-center w-16 h-16 rounded-full border-2 border-indigo-400 bg-indigo-50 text-2xl font-black text-indigo-700">
                {grade}
              </span>
              <div className="text-sm text-gray-600 space-y-0.5">
                {gradeScore != null && (
                  <p>등급 점수: <span className="font-bold text-gray-800">{gradeScore}</span> / 28</p>
                )}
                {compositeScore != null && (
                  <p>복합 점수: <span className="font-bold text-gray-800">{Math.round(compositeScore)}</span> / 100</p>
                )}
              </div>
            </div>
          )}

          <dl className="text-sm text-gray-600 space-y-1 mb-8">
            <div className="flex gap-2">
              <dt className="w-24 text-gray-400">구성</dt>
              <dd>표지 · 기본적 분석{hasReport ? ' · AI 자문' : ''}</dd>
            </div>
            {generatedAt && (
              <div className="flex gap-2">
                <dt className="w-24 text-gray-400">AI 리포트</dt>
                <dd>{generatedAt} 생성</dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt className="w-24 text-gray-400">출력 일시</dt>
              <dd>{nowStr}</dd>
            </div>
          </dl>

          <p className="text-[11px] text-gray-400 leading-relaxed border-t border-gray-200 pt-4">
            ※ 본 리포트는 투자 참고용 정보이며 투자 권유나 매매 신호가 아닙니다.
            최종 투자 판단과 책임은 투자자 본인에게 있습니다.
          </p>
        </div>
      </div>

      {/* ── 기본적 분석 ── */}
      {advData && (
        <div data-pdf style={{ width: `${DOC_WIDTH}px`, background: '#ffffff' }} className="p-8">
          <h2 className="text-lg font-bold text-gray-900 mb-3 border-b-2 border-indigo-300 pb-2">
            기본적 분석
          </h2>
          <FundamentalPanel data={advData} market={market} code={code} printMode />
        </div>
      )}

      {/* ── AI 자문 ── */}
      <div data-pdf style={{ width: `${DOC_WIDTH}px`, background: '#ffffff' }} className="p-8">
        <h2 className="text-lg font-bold text-gray-900 mb-3 border-b-2 border-indigo-300 pb-2">
          AI 자문
        </h2>
        {hasReport ? (
          <AIReportPanel report={report} history={[]} printMode />
        ) : (
          <div className="border border-gray-200 rounded-lg p-8 text-center text-sm text-gray-500 bg-gray-50">
            AI 자문이 아직 생성되지 않았습니다. (AI분석 생성 후 다시 내보내면 포함됩니다)
          </div>
        )}
      </div>
    </div>
  )
}
