/**
 * 클라이언트 사이드 PDF 내보내기 유틸 (html2canvas-pro + jsPDF).
 *
 * 채택 사유: Tailwind v4가 색상을 oklch()로 출력 → 원조 html2canvas는
 *   "unsupported color function oklch" throw. html2canvas-pro 포크가
 *   oklch/lab/lch/color() 파싱을 지원하므로 이 결함의 직접 해법.
 *
 * DOM(이미 렌더된 화면)을 래스터화하므로 한글 폰트 임베딩 불필요
 *   (시스템 폰트가 캡처에 그대로 반영). jsPDF는 이미지만 배치(텍스트 미사용).
 *
 * 기존 클라이언트 다운로드 컨벤션(WatchlistDashboard.jsx의 Blob/a.download)과
 *   동일 계열의 "버튼 클릭 → 파일 즉시 저장" UX.
 */
import html2canvas from 'html2canvas-pro'
import { jsPDF } from 'jspdf'

// A4 mm 상수
const A4_WIDTH_MM = 210
const A4_HEIGHT_MM = 297

/**
 * 여러 DOM 요소를 각각 새 페이지에서 시작하는 단일 A4 PDF로 내보낸다.
 *
 * 각 요소는 html2canvas-pro로 캔버스 래스터화 후, A4 콘텐츠 높이 비율로
 * 슬라이스해 멀티페이지로 배치한다(표준 jsPDF 멀티페이지 패턴 — 페이지
 * 클리핑 활용: 한 장 폭에 맞춘 전체 이미지를 음수 offset으로 위로 밀며
 * 페이지마다 다른 구간이 보이게 함).
 *
 * @param {HTMLElement[]} elements 캡처 대상(표지/기본적/AI). 빈 값은 무시.
 * @param {Object}   opts
 * @param {string}   opts.filename  저장 파일명 (.pdf)
 * @param {number}   [opts.scale=2] 캡처 해상도 배율(차트 선명도 보정)
 * @param {number}   [opts.margin=8] 페이지 여백(mm)
 */
export async function exportSectionsToPdf(elements, { filename, scale = 2, margin = 8 } = {}) {
  const els = (elements || []).filter(Boolean)
  if (els.length === 0) throw new Error('내보낼 콘텐츠가 없습니다.')

  const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' })
  const contentWidthMm = A4_WIDTH_MM - margin * 2
  const contentHeightMm = A4_HEIGHT_MM - margin * 2

  let firstPage = true

  for (const el of els) {
    const canvas = await html2canvas(el, {
      scale,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    })

    // 캔버스 폭을 콘텐츠 폭(mm)에 맞춤 → 전체 이미지 높이(mm) 환산
    const imgWidthMm = contentWidthMm
    const imgHeightMm = (canvas.height / canvas.width) * imgWidthMm

    // 한 요소당 필요한 페이지 수 = ceil(전체 높이 / 페이지 콘텐츠 높이)
    const pageCount = Math.max(1, Math.ceil(imgHeightMm / contentHeightMm))
    const imgData = canvas.toDataURL('image/png')

    for (let p = 0; p < pageCount; p++) {
      if (!firstPage) pdf.addPage()
      firstPage = false

      // 음수 offset으로 이미지를 위로 밀어 해당 페이지 구간만 노출
      const offsetMm = p * contentHeightMm
      pdf.addImage(
        imgData,
        'PNG',
        margin,
        margin - offsetMm,
        imgWidthMm,
        imgHeightMm,
        undefined,
        'FAST',
      )
    }
  }

  pdf.save(filename)
}
