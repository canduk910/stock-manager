/**
 * 섹터별 대표종목 정적 매핑.
 *
 * 매크로 섹터 히트맵에서 섹터명 옆에 대표종목 1개 표시 + 클릭 시 5+5 팬업.
 * 시가총액/대표성 기준 단순 매핑 — 실시간 업데이트 X (정적).
 *
 * 매칭 키:
 *   1순위: name (영문, US/KR 공용 카테고리)
 *   2순위: name_ko (한글, KR 전용)
 *   3순위: symbol (US ETF 티커)
 */

// 카테고리별 KR/US 대표종목 (각 5개)
export const SECTOR_REPS = {
  'Technology': {
    label: '기술',
    kr: [
      { code: '005930', name: '삼성전자' },
      { code: '000660', name: 'SK하이닉스' },
      { code: '035420', name: '네이버' },
      { code: '035720', name: '카카오' },
      { code: '036570', name: '엔씨소프트' },
    ],
    us: [
      { code: 'AAPL', name: 'Apple' },
      { code: 'MSFT', name: 'Microsoft' },
      { code: 'NVDA', name: 'NVIDIA' },
      { code: 'GOOGL', name: 'Alphabet' },
      { code: 'META', name: 'Meta' },
    ],
  },
  'Financials': {
    label: '금융',
    kr: [
      { code: '105560', name: 'KB금융' },
      { code: '055550', name: '신한지주' },
      { code: '086790', name: '하나금융지주' },
      { code: '316140', name: '우리금융지주' },
      { code: '138040', name: '메리츠금융지주' },
    ],
    us: [
      { code: 'JPM', name: 'JPMorgan' },
      { code: 'BAC', name: 'Bank of America' },
      { code: 'WFC', name: 'Wells Fargo' },
      { code: 'GS', name: 'Goldman Sachs' },
      { code: 'MS', name: 'Morgan Stanley' },
    ],
  },
  'Healthcare': {
    label: '헬스케어',
    kr: [
      { code: '207940', name: '삼성바이오로직스' },
      { code: '068270', name: '셀트리온' },
      { code: '000100', name: '유한양행' },
      { code: '128940', name: '한미약품' },
      { code: '326030', name: 'SK바이오팜' },
    ],
    us: [
      { code: 'UNH', name: 'UnitedHealth' },
      { code: 'JNJ', name: 'Johnson & Johnson' },
      { code: 'LLY', name: 'Eli Lilly' },
      { code: 'PFE', name: 'Pfizer' },
      { code: 'MRK', name: 'Merck' },
    ],
  },
  'Energy': {
    label: '에너지',
    kr: [
      { code: '096770', name: 'SK이노베이션' },
      { code: '010950', name: 'S-Oil' },
      { code: '015760', name: '한국전력' },
      { code: '078930', name: 'GS' },
      { code: '267250', name: 'HD현대' },
    ],
    us: [
      { code: 'XOM', name: 'ExxonMobil' },
      { code: 'CVX', name: 'Chevron' },
      { code: 'COP', name: 'ConocoPhillips' },
      { code: 'EOG', name: 'EOG Resources' },
      { code: 'SLB', name: 'Schlumberger' },
    ],
  },
  'Consumer Discretionary': {
    label: '경기소비재',
    kr: [
      { code: '005380', name: '현대차' },
      { code: '000270', name: '기아' },
      { code: '012330', name: '현대모비스' },
      { code: '139480', name: '이마트' },
      { code: '383220', name: 'F&F' },
    ],
    us: [
      { code: 'AMZN', name: 'Amazon' },
      { code: 'TSLA', name: 'Tesla' },
      { code: 'HD', name: 'Home Depot' },
      { code: 'MCD', name: 'McDonald\'s' },
      { code: 'NKE', name: 'Nike' },
    ],
  },
  'Consumer Staples': {
    label: '필수소비재',
    kr: [
      { code: '004370', name: '농심' },
      { code: '271560', name: '오리온' },
      { code: '097950', name: 'CJ제일제당' },
      { code: '007310', name: '오뚜기' },
      { code: '005300', name: '롯데칠성' },
    ],
    us: [
      { code: 'PG', name: 'Procter & Gamble' },
      { code: 'KO', name: 'Coca-Cola' },
      { code: 'PEP', name: 'PepsiCo' },
      { code: 'WMT', name: 'Walmart' },
      { code: 'COST', name: 'Costco' },
    ],
  },
  'Industrials': {
    label: '산업재',
    kr: [
      { code: '012450', name: '한화에어로스페이스' },
      { code: '329180', name: 'HD현대중공업' },
      { code: '034020', name: '두산에너빌리티' },
      { code: '047810', name: '한국항공우주' },
      { code: '010140', name: '삼성중공업' },
    ],
    us: [
      { code: 'CAT', name: 'Caterpillar' },
      { code: 'HON', name: 'Honeywell' },
      { code: 'UPS', name: 'UPS' },
      { code: 'RTX', name: 'RTX' },
      { code: 'GE', name: 'GE Aerospace' },
    ],
  },
  'Materials': {
    label: '소재',
    kr: [
      { code: '005490', name: 'POSCO홀딩스' },
      { code: '051910', name: 'LG화학' },
      { code: '011170', name: '롯데케미칼' },
      { code: '011780', name: '금호석유' },
      { code: '014680', name: '한솔케미칼' },
    ],
    us: [
      { code: 'LIN', name: 'Linde' },
      { code: 'SHW', name: 'Sherwin-Williams' },
      { code: 'APD', name: 'Air Products' },
      { code: 'ECL', name: 'Ecolab' },
      { code: 'FCX', name: 'Freeport-McMoRan' },
    ],
  },
  'Utilities': {
    label: '유틸리티',
    kr: [
      { code: '015760', name: '한국전력' },
      { code: '036460', name: '한국가스공사' },
      { code: '018670', name: 'SK가스' },
      { code: '071320', name: '지역난방공사' },
      { code: '004690', name: '삼천리' },
    ],
    us: [
      { code: 'NEE', name: 'NextEra Energy' },
      { code: 'SO', name: 'Southern Company' },
      { code: 'DUK', name: 'Duke Energy' },
      { code: 'AEP', name: 'American Electric' },
      { code: 'EXC', name: 'Exelon' },
    ],
  },
  'Real Estate': {
    label: '부동산',
    kr: [
      { code: '395400', name: 'SK리츠' },
      { code: '088980', name: '맥쿼리인프라' },
      { code: '330590', name: '롯데리츠' },
      { code: '404990', name: '신한서부티엔디리츠' },
      { code: '432320', name: '한화리츠' },
    ],
    us: [
      { code: 'AMT', name: 'American Tower' },
      { code: 'PLD', name: 'Prologis' },
      { code: 'CCI', name: 'Crown Castle' },
      { code: 'EQIX', name: 'Equinix' },
      { code: 'SPG', name: 'Simon Property' },
    ],
  },
  'Communication': {
    label: '커뮤니케이션',
    kr: [
      { code: '017670', name: 'SK텔레콤' },
      { code: '030200', name: 'KT' },
      { code: '032640', name: 'LG유플러스' },
      { code: '035720', name: '카카오' },
      { code: '035420', name: '네이버' },
    ],
    us: [
      { code: 'GOOGL', name: 'Alphabet' },
      { code: 'META', name: 'Meta' },
      { code: 'NFLX', name: 'Netflix' },
      { code: 'DIS', name: 'Disney' },
      { code: 'T', name: 'AT&T' },
    ],
  },
}

/**
 * KR 섹터 ETF symbol → 대표종목 직접 매핑.
 *
 * KRX 자체 분류는 GICS와 1:1 매핑 안 되어 카테고리 기반 매핑으로는
 * 잘못된 종목이 노출됨 (예: KODEX 자동차에 이마트, KODEX 미디어에 통신사).
 * → ETF symbol을 키로 KODEX/TIGER 구성종목 직접 정의.
 *
 * 출처: KODEX/TIGER ETF의 실제 비중 상위 종목 (시가총액·기여도 기준).
 */
export const KR_SECTOR_REPS = {
  '091160.KS': {  // KODEX 반도체
    label: '반도체',
    stocks: [
      { code: '005930', name: '삼성전자' },
      { code: '000660', name: 'SK하이닉스' },
      { code: '042700', name: '한미반도체' },
      { code: '240810', name: '원익IPS' },
      { code: '058470', name: '리노공업' },
    ],
  },
  '157490.KS': {  // KODEX IT — 광의 IT(인터넷·플랫폼·SI)
    label: 'IT/인터넷',
    stocks: [
      { code: '035420', name: '네이버' },
      { code: '035720', name: '카카오' },
      { code: '018260', name: '삼성에스디에스' },
      { code: '036570', name: '엔씨소프트' },
      { code: '251270', name: '넷마블' },
    ],
  },
  '305720.KS': {  // KODEX 2차전지산업
    label: '2차전지',
    stocks: [
      { code: '373220', name: 'LG에너지솔루션' },
      { code: '006400', name: '삼성SDI' },
      { code: '003670', name: '포스코퓨처엠' },
      { code: '247540', name: '에코프로비엠' },
      { code: '086520', name: '에코프로' },
    ],
  },
  '117700.KS': {  // KODEX 건설
    label: '건설',
    stocks: [
      { code: '000720', name: '현대건설' },
      { code: '006360', name: 'GS건설' },
      { code: '375500', name: 'DL이앤씨' },
      { code: '047040', name: '대우건설' },
      { code: '294870', name: 'HDC현대산업개발' },
    ],
  },
  '244580.KS': {  // KODEX 바이오
    label: '바이오/헬스케어',
    stocks: [
      { code: '207940', name: '삼성바이오로직스' },
      { code: '068270', name: '셀트리온' },
      { code: '000100', name: '유한양행' },
      { code: '128940', name: '한미약품' },
      { code: '326030', name: 'SK바이오팜' },
    ],
  },
  '091170.KS': {  // KODEX 은행
    label: '은행/금융',
    stocks: [
      { code: '105560', name: 'KB금융' },
      { code: '055550', name: '신한지주' },
      { code: '086790', name: '하나금융지주' },
      { code: '316140', name: '우리금융지주' },
      { code: '323410', name: '카카오뱅크' },
    ],
  },
  '117680.KS': {  // KODEX 철강
    label: '철강/소재',
    stocks: [
      { code: '005490', name: 'POSCO홀딩스' },
      { code: '004020', name: '현대제철' },
      { code: '103140', name: '풍산' },
      { code: '001230', name: '동국제강' },
      { code: '014285', name: '세아베스틸지주' },
    ],
  },
  '091180.KS': {  // KODEX 자동차
    label: '자동차',
    stocks: [
      { code: '005380', name: '현대차' },
      { code: '000270', name: '기아' },
      { code: '012330', name: '현대모비스' },
      { code: '161390', name: '한국타이어앤테크놀로지' },
      { code: '204320', name: 'HL만도' },
    ],
  },
  '117460.KS': {  // KODEX 에너지화학
    label: '에너지/화학',
    stocks: [
      { code: '051910', name: 'LG화학' },
      { code: '011170', name: '롯데케미칼' },
      { code: '096770', name: 'SK이노베이션' },
      { code: '010950', name: 'S-Oil' },
      { code: '009830', name: '한화솔루션' },
    ],
  },
  '266390.KS': {  // KODEX 미디어&엔터
    label: '미디어/엔터',
    stocks: [
      { code: '035760', name: 'CJ ENM' },
      { code: '352820', name: '하이브' },
      { code: '041510', name: 'SM엔터테인먼트' },
      { code: '122870', name: '와이지엔터테인먼트' },
      { code: '253450', name: '스튜디오드래곤' },
    ],
  },
  '266410.KS': {  // KODEX 필수소비재
    label: '필수소비재',
    stocks: [
      { code: '033780', name: 'KT&G' },
      { code: '004370', name: '농심' },
      { code: '271560', name: '오리온' },
      { code: '097950', name: 'CJ제일제당' },
      { code: '007310', name: '오뚜기' },
    ],
  },
  '266420.KS': {  // KODEX 경기소비재
    label: '경기소비재',
    stocks: [
      { code: '008770', name: '호텔신라' },
      { code: '139480', name: '이마트' },
      { code: '004170', name: '신세계' },
      { code: '383220', name: 'F&F' },
      { code: '090430', name: '아모레퍼시픽' },
    ],
  },
  '140710.KS': {  // KODEX 운송
    label: '운송/물류',
    stocks: [
      { code: '003490', name: '대한항공' },
      { code: '011200', name: 'HMM' },
      { code: '000120', name: 'CJ대한통운' },
      { code: '028670', name: '팬오션' },
      { code: '002320', name: '한진' },
    ],
  },
  '227550.KS': {  // KODEX 유틸리티(가스)
    label: '유틸리티',
    stocks: [
      { code: '015760', name: '한국전력' },
      { code: '036460', name: '한국가스공사' },
      { code: '018670', name: 'SK가스' },
      { code: '071320', name: '지역난방공사' },
      { code: '004690', name: '삼천리' },
    ],
  },
}

// US ETF symbol → 카테고리 매핑
const _US_SYMBOL_TO_CATEGORY = {
  XLK: 'Technology',
  XLF: 'Financials',
  XLV: 'Healthcare',
  XLE: 'Energy',
  XLY: 'Consumer Discretionary',
  XLP: 'Consumer Staples',
  XLI: 'Industrials',
  XLB: 'Materials',
  XLU: 'Utilities',
  XLRE: 'Real Estate',
  XLC: 'Communication',
}

// KR 섹터 한글명 → 카테고리 매핑 (정규식 키워드 매칭, CLAUDE.md 지침)
// 순서가 중요 — 위에서부터 처음 매치되는 카테고리 채택. 더 구체적인 패턴을 위로.
const _KR_NAME_PATTERNS = [
  { pattern: /2차전지|배터리|이차전지/, category: 'Energy' },           // KR 특화 → Energy 광의
  { pattern: /반도체|IT|소프트웨어|인터넷/, category: 'Technology' },
  { pattern: /미디어|엔터|통신|텔레콤/, category: 'Communication' },     // 자동차/소비재 패턴 위로
  { pattern: /바이오|제약|의료|헬스/, category: 'Healthcare' },
  { pattern: /은행|증권|보험|금융|지주/, category: 'Financials' },
  { pattern: /필수소비/, category: 'Consumer Staples' },                  // 경기보다 위 (필수가 더 구체)
  { pattern: /경기소비|자동차|화장품|패션|유통/, category: 'Consumer Discretionary' },
  { pattern: /식품|음식료|생활용품/, category: 'Consumer Staples' },
  { pattern: /에너지|정유|화학|석유|전력/, category: 'Energy' },
  { pattern: /철강|금속|화학소재|소재/, category: 'Materials' },
  { pattern: /조선|항공|방산|기계|건설|운송|물류|중공업|산업/, category: 'Industrials' },
  { pattern: /유틸|가스|난방/, category: 'Utilities' },
  { pattern: /리츠|부동산|REIT/i, category: 'Real Estate' },
]

/**
 * 섹터 응답에서 GICS 카테고리 식별 (US 전용 — KR은 직접 매핑 사용).
 * @param {object} sector - { symbol, name, name_ko }
 * @returns {string|null}
 */
export function resolveCategory(sector) {
  if (!sector) return null
  if (sector.name && SECTOR_REPS[sector.name]) return sector.name
  if (sector.symbol && _US_SYMBOL_TO_CATEGORY[sector.symbol]) {
    return _US_SYMBOL_TO_CATEGORY[sector.symbol]
  }
  // KR name_ko 정규식 매칭 — 폴백 (KR ETF symbol에 직접 매핑 없을 때만)
  const text = `${sector.name_ko || ''} ${sector.name || ''}`
  for (const { pattern, category } of _KR_NAME_PATTERNS) {
    if (pattern.test(text)) return category
  }
  return null
}

/**
 * 섹터 응답에서 대표종목 1개 반환 (KR/US 각각).
 * KR은 ETF symbol 직접 룩업(KR_SECTOR_REPS) 우선. US는 GICS 카테고리.
 * @returns {{kr: {code,name}|null, us: {code,name}|null}}
 */
export function getPrimaryReps(sector) {
  if (!sector) return { kr: null, us: null }
  // KR — ETF symbol 직접 매핑
  let krStock = null
  if (sector.symbol && KR_SECTOR_REPS[sector.symbol]) {
    krStock = KR_SECTOR_REPS[sector.symbol].stocks?.[0] || null
  }
  // US — GICS 카테고리
  let usStock = null
  const cat = resolveCategory(sector)
  if (cat && SECTOR_REPS[cat]) {
    usStock = SECTOR_REPS[cat].us?.[0] || null
    // KR 직접 매핑 못 찾았을 때만 카테고리 폴백
    if (!krStock) krStock = SECTOR_REPS[cat].kr?.[0] || null
  }
  return { kr: krStock, us: usStock }
}

/**
 * 섹터 응답에서 5개씩 전체 대표종목 반환 (토글 팬업용).
 * KR은 ETF symbol 직접 룩업, US는 GICS 카테고리.
 * @returns {{kr: array, us: array, label: string}|null}
 */
export function getAllReps(sector) {
  if (!sector) return null
  let krStocks = []
  let label = ''
  if (sector.symbol && KR_SECTOR_REPS[sector.symbol]) {
    krStocks = KR_SECTOR_REPS[sector.symbol].stocks || []
    label = KR_SECTOR_REPS[sector.symbol].label
  }
  let usStocks = []
  const cat = resolveCategory(sector)
  if (cat && SECTOR_REPS[cat]) {
    usStocks = SECTOR_REPS[cat].us || []
    if (!krStocks.length) krStocks = SECTOR_REPS[cat].kr || []
    if (!label) label = SECTOR_REPS[cat].label
  }
  if (!krStocks.length && !usStocks.length) return null
  return { kr: krStocks, us: usStocks, label }
}
