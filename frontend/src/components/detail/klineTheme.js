// 한국식 색상 테마: 상승=빨강, 하락=파랑
export const krStyleOverrides = {
  candle: {
    type: 'candle_solid',
    bar: {
      upColor: '#ef4444',
      downColor: '#3b82f6',
      noChangeColor: '#6b7280',
      upBorderColor: '#ef4444',
      downBorderColor: '#3b82f6',
      noChangeBorderColor: '#6b7280',
      upWickColor: '#ef4444',
      downWickColor: '#3b82f6',
      noChangeWickColor: '#6b7280',
    },
    priceMark: {
      last: {
        upColor: '#ef4444',
        downColor: '#3b82f6',
        noChangeColor: '#6b7280',
      },
    },
  },
  indicator: {
    ohlc: {
      upColor: '#ef4444',
      downColor: '#3b82f6',
      noChangeColor: '#6b7280',
    },
    bars: [{
      upColor: 'rgba(239,68,68,0.5)',
      downColor: 'rgba(59,130,246,0.5)',
      noChangeColor: 'rgba(107,114,128,0.5)',
    }],
  },
  grid: {
    horizontal: { color: '#f3f4f6' },
    vertical: { color: '#f3f4f6' },
  },
  crosshair: {
    horizontal: {
      line: { color: '#9ca3af', dashedValue: [4, 2] },
      text: { color: '#ffffff', backgroundColor: '#374151' },
    },
    vertical: {
      line: { color: '#9ca3af', dashedValue: [4, 2] },
      text: { color: '#ffffff', backgroundColor: '#374151' },
    },
  },
  yAxis: {
    tickText: { color: '#6b7280', size: 10 },
  },
  xAxis: {
    tickText: { color: '#6b7280', size: 10 },
  },
}
