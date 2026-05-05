// EventLabelsOverlay — Recharts Customized 오버레이.
// 차트 픽셀 공간에서 라벨 폭을 측정하여 겹치는 라벨을 행 단위로 적층.
// ReferenceArea 자체 label 대신 사용해 침범을 원천 차단.
//
// props:
//   events: [{ kind: 'rec'|'bear', x1, x2, label }]
//   labelGap: 행 간격(px), default 13
//   sidePadding: 라벨 좌우 여백(px), default 4
//   charWidth: 글자당 폭(px) 추정치, default 6.2 (fontSize 9 한글/기호 평균)

const KIND_STYLE = {
  rec:  { fill: '#374151', prefix: '■' },
  bear: { fill: '#b91c1c', prefix: '▼' },
}

function _estimateWidth(text, charWidth) {
  // 한글/한자는 charWidth, ASCII는 70%로 가정
  let w = 0
  for (const ch of text) {
    w += /[\x00-\x7f]/.test(ch) ? charWidth * 0.6 : charWidth
  }
  return w
}

function _shortLabel(label, x1, x2) {
  const days = (new Date(x2) - new Date(x1)) / 86400000
  if (days < 365 && label.length > 5) {
    return label.replace('약세장', '').replace('침체', '').trim() || label
  }
  return label
}

export default function EventLabelsOverlay({
  events = [],
  labelGap = 13,
  sidePadding = 4,
  charWidth = 6.2,
  fontSize = 9,
  topMargin = 4,
  bottomMargin = 14,
}) {
  // Recharts <Customized component={...} /> 호출 시 chart 내부 상태 props 주입
  return function CustomizedRender(chartProps) {
    const { xAxisMap, offset } = chartProps || {}
    if (!xAxisMap || !offset) return null
    const xAxisKey = Object.keys(xAxisMap)[0]
    const xAxis = xAxisMap[xAxisKey]
    if (!xAxis || typeof xAxis.scale !== 'function') return null

    // 각 이벤트의 픽셀 좌표 + 라벨 텍스트 + 추정 폭 계산
    const items = []
    for (const e of events) {
      const x1px = xAxis.scale(e.x1)
      const x2px = xAxis.scale(e.x2)
      if (!Number.isFinite(x1px) || !Number.isFinite(x2px)) continue
      const left = Math.min(x1px, x2px)
      const right = Math.max(x1px, x2px)
      const cx = (left + right) / 2
      const style = KIND_STYLE[e.kind] || KIND_STYLE.rec
      const labelText = `${style.prefix} ${_shortLabel(e.label, e.x1, e.x2)}`
      const w = _estimateWidth(labelText, charWidth) + sidePadding * 2
      items.push({
        kind: e.kind,
        label: e.label,
        cx,
        halfW: w / 2,
        text: labelText,
        fill: style.fill,
        bandLeft: left,
        bandRight: right,
      })
    }

    // 같은 kind끼리 cx 오름차순 정렬 후 그리디 행 배정
    // 각 kind는 자기 영역(상단=bear, 하단=rec)에서만 적층
    const place = (kindItems) => {
      const sorted = kindItems.sort((a, b) => a.cx - b.cx)
      const rowEnds = [] // rowEnds[r] = 해당 행에 마지막으로 배치된 라벨의 우측 끝 px
      const placed = []
      for (const it of sorted) {
        const desiredLeft = it.cx - it.halfW
        const desiredRight = it.cx + it.halfW
        let row = 0
        while (row < rowEnds.length && rowEnds[row] > desiredLeft) row++
        if (row === rowEnds.length) rowEnds.push(desiredRight)
        else rowEnds[row] = desiredRight
        placed.push({ ...it, row })
      }
      return placed
    }

    const recItems = place(items.filter(i => i.kind === 'rec'))
    const bearItems = place(items.filter(i => i.kind === 'bear'))

    const topY = (offset.top || 0) + topMargin
    const bottomY = (offset.top || 0) + (offset.height || 0) - bottomMargin
    const chartLeft = offset.left || 0
    const chartRight = chartLeft + (offset.width || 0)

    const renderItem = (it, y) => {
      // 차트 영역을 벗어나지 않게 cx clamp (라벨 폭 절반 보정)
      const minCx = chartLeft + it.halfW
      const maxCx = chartRight - it.halfW
      const cx = Math.max(minCx, Math.min(maxCx, it.cx))
      return (
        <g key={`${it.kind}-${it.label}-${it.cx}`}>
          <text
            x={cx}
            y={y}
            textAnchor="middle"
            fontSize={fontSize}
            fill={it.fill}
            style={{ pointerEvents: 'none' }}
          >
            {it.text}
          </text>
        </g>
      )
    }

    return (
      <g className="event-labels-overlay">
        {bearItems.map(it => renderItem(it, topY + it.row * labelGap + fontSize))}
        {recItems.map(it => renderItem(it, bottomY - it.row * labelGap))}
      </g>
    )
  }
}
