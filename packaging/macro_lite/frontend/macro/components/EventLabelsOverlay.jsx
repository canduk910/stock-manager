// 이벤트 라벨 stagger 계산 — 시간 도메인에서 글로벌 충돌 검사로 row 할당.
// ReferenceArea의 label 콜백(viewBox 수신)에서 사용. Customized 우회로 100% 렌더 보장.
//
// 가정: 차트 X축이 균일 시간 매핑이라고 가정하여 라벨 픽셀 폭 → 시간 폭으로 환산.
// kind(rec/bear)별 독립 적층. 같은 kind 내에서 cx가 가까우면 다음 row로 밀어냄.

const _CHAR_PX = 6.2
const _CHART_PX_FALLBACK = 600  // ResponsiveContainer 기본 폭 추정

function _shortLabel(label, x1, x2) {
  const days = (new Date(x2) - new Date(x1)) / 86400000
  if (days < 365 && label.length > 5) {
    return label.replace('약세장', '').replace('침체', '').trim() || label
  }
  return label
}

function _estimateLabelChars(text) {
  let n = 0
  for (const ch of text) {
    n += /[\x00-\x7f]/.test(ch) ? 0.6 : 1
  }
  return n
}

// events: [{kind, x1, x2, label}] - 정렬 안 됨
// 반환: [{kind, x1, x2, label, displayLabel, row}] - row=0/1/2/...
const _EMPTY_ROW_MAP = {
  rowFor: () => 0,
  rowDisplayFor: () => ({ row: 0, displayLabel: '' }),
}

export function computeEventRows(events, chartPxWidth = _CHART_PX_FALLBACK) {
  if (!events?.length) return _EMPTY_ROW_MAP
  // 전체 시간 범위
  const allDates = events.flatMap(e => [e.x1, e.x2])
  const minMs = Math.min(...allDates.map(d => new Date(d).getTime()))
  const maxMs = Math.max(...allDates.map(d => new Date(d).getTime()))
  const spanMs = Math.max(1, maxMs - minMs)
  const msPerPx = spanMs / chartPxWidth

  const items = events.map(e => {
    const cMs = (new Date(e.x1).getTime() + new Date(e.x2).getTime()) / 2
    const displayLabel = _shortLabel(e.label, e.x1, e.x2)
    const prefix = e.kind === 'rec' ? '■ ' : '▼ '
    const fullText = prefix + displayLabel
    const widthPx = _estimateLabelChars(fullText) * _CHAR_PX + 8
    const widthMs = widthPx * msPerPx
    return { ...e, displayLabel, cMs, widthMs }
  })

  const place = (kindItems) => {
    const sorted = kindItems.sort((a, b) => a.cMs - b.cMs)
    const rowEnds = [] // 각 row의 마지막 라벨의 right ms
    return sorted.map(it => {
      const left = it.cMs - it.widthMs / 2
      const right = it.cMs + it.widthMs / 2
      let row = 0
      while (row < rowEnds.length && rowEnds[row] > left) row++
      if (row === rowEnds.length) rowEnds.push(right)
      else rowEnds[row] = right
      return { ...it, row }
    })
  }

  const recItems = place(items.filter(i => i.kind === 'rec'))
  const bearItems = place(items.filter(i => i.kind === 'bear'))
  // events 원래 순서로 묶어 반환할 필요 없음 — kind별 lookup 맵 제공
  const map = new Map()
  for (const it of [...recItems, ...bearItems]) {
    map.set(`${it.kind}|${it.x1}|${it.x2}`, it.row)
  }
  return {
    rowFor: (kind, x1, x2) => map.get(`${kind}|${x1}|${x2}`) ?? 0,
    rowDisplayFor: (kind, x1, x2) => {
      const it = [...recItems, ...bearItems].find(
        x => x.kind === kind && x.x1 === x1 && x.x2 === x2,
      )
      return it ? { row: it.row, displayLabel: it.displayLabel } : { row: 0, displayLabel: '' }
    },
  }
}

// ReferenceArea label 콜백 헬퍼 — viewBox 받아 row*step만큼 dy 적용 후 SVG <text> 반환.
// kind: 'rec'(아래) | 'bear'(위)
export function makeLabelRenderer({ kind, displayLabel, row, fill, fontSize = 9, step = 13 }) {
  const prefix = kind === 'rec' ? '■' : '▼'
  return (props) => {
    const vb = props?.viewBox || {}
    const x = (vb.x ?? 0) + (vb.width ?? 0) / 2
    const yBase = kind === 'rec'
      ? (vb.y ?? 0) + (vb.height ?? 0) - 4
      : (vb.y ?? 0) + fontSize + 2
    const dy = kind === 'rec' ? -row * step : row * step
    return (
      <text
        x={x}
        y={yBase + dy}
        textAnchor="middle"
        fontSize={fontSize}
        fill={fill}
        style={{ pointerEvents: 'none' }}
      >
        {prefix} {displayLabel}
      </text>
    )
  }
}
