// EventLabelsOverlay — Recharts <Customized component={<this />} /> 자식.
// recharts가 cloneElement(this, chartProps)로 호출 → events(외부) + xAxisMap/offset(internal) 동시 접근.
// 픽셀 공간에서 라벨 폭을 측정하여 같은 kind 내 충돌을 행 단위로 적층 → 침범 원천 차단.

const KIND_STYLE = {
  rec:  { fill: '#374151', prefix: '■' },
  bear: { fill: '#b91c1c', prefix: '▼' },
}

function _estimateWidth(text, charWidth) {
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

function _safeScale(xAxis, value) {
  // category scaleBand/scalePoint 모두 .scale(domainValue) 지원.
  // domain 밖이거나 매칭 실패 시 NaN — fallback으로 NaN 반환.
  try {
    const v = xAxis.scale(value)
    return Number.isFinite(v) ? v : NaN
  } catch (_) {
    return NaN
  }
}

export default function EventLabelsOverlay({
  events = [],
  // chart internals (recharts cloneElement로 주입)
  xAxisMap,
  offset,
  // 시각 옵션
  labelGap = 13,
  sidePadding = 4,
  charWidth = 6.2,
  fontSize = 9,
  topMargin = 4,
  bottomMargin = 14,
}) {
  if (!xAxisMap || !offset) return null
  const xAxisKey = Object.keys(xAxisMap)[0]
  const xAxis = xAxisMap[xAxisKey]
  if (!xAxis || typeof xAxis.scale !== 'function') return null

  // band scale은 .bandwidth() 존재 — 중심 보정에 사용
  const bw = typeof xAxis.scale.bandwidth === 'function' ? xAxis.scale.bandwidth() : 0

  const items = []
  for (const e of events) {
    let x1px = _safeScale(xAxis, e.x1)
    let x2px = _safeScale(xAxis, e.x2)
    if (!Number.isFinite(x1px) || !Number.isFinite(x2px)) continue
    // band scale은 left edge 반환 — 중심 보정
    if (bw) { x1px += bw / 2; x2px += bw / 2 }
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
    })
  }

  const place = (kindItems) => {
    const sorted = kindItems.sort((a, b) => a.cx - b.cx)
    const rowEnds = []
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
    const minCx = chartLeft + it.halfW
    const maxCx = chartRight - it.halfW
    const cx = Math.max(minCx, Math.min(maxCx, it.cx))
    return (
      <text
        key={`${it.kind}-${it.label}-${it.cx}-${it.row}`}
        x={cx}
        y={y}
        textAnchor="middle"
        fontSize={fontSize}
        fill={it.fill}
        style={{ pointerEvents: 'none' }}
      >
        {it.text}
      </text>
    )
  }

  return (
    <g className="event-labels-overlay">
      {bearItems.map(it => renderItem(it, topY + it.row * labelGap + fontSize))}
      {recItems.map(it => renderItem(it, bottomY - it.row * labelGap))}
    </g>
  )
}
