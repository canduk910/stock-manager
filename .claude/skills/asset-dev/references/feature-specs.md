# 투자 자동화 시스템 — 상세 기능 명세

각 모듈의 상세 API/DB/UI 설계. dev-architect가 구현 시 참조한다.

---

## Module 0: 투자 파이프라인 서비스 (핵심)

### 백엔드

#### 파이프라인 서비스 (`services/pipeline_service.py`)

기존 서비스 함수를 직접 호출하여 분석 파이프라인을 실행한다:

```python
async def run_pipeline(market: str = "KR") -> dict:
    # Step 1: _analyze_macro() → macro_service.get_sentiment()
    # Step 2: _screen_stocks(market, regime) → screener.krx.get_all_stocks() + apply_filters()
    # Step 3: _analyze_candidates(candidates[:10]) → advisory_service.refresh_stock_data()
    # Step 4: _generate_recommendations(analyses) → report_service.save_recommendations_batch()
    # Step 5: _generate_and_save_report() → report_service.save_daily_report()
    # Step 6: _send_telegram_notification() → telegram_service.send_report_notification()
```

#### 체제 판단 (`_determine_regime`)

버핏지수 × 공포탐욕 교차표:
- buffett: low(<0.8) / normal(0.8-1.2) / high(1.2-1.6) / extreme(>1.6)
- fear_greed: extreme_fear(<20) / fear(20-40) / neutral(40-60) / greed(60-80) / extreme_greed(>80)
- VIX > 35 오버라이드: extreme_fear로 강제

체제별 파라미터 (`REGIME_PARAMS`):
- accumulation: PER<20, PBR<2.0, ROE>5%, margin=20%, position=5%, invest=75%
- selective: PER<15, PBR<1.5, ROE>8%, margin=30%, position=4%, invest=65%
- cautious: PER<12, PBR<1.2, ROE>10%, margin=40%, position=3%, invest=50%
- defensive: 스크리닝 중단, 현금 100%

#### 7점 등급 (`_calc_safety_grade`)

7개 지표 × 4점 = 28점 만점:
1. Graham 할인율 (>40%=4, 20-40%=3, 0-20%=2, <0%=1)
2. PER vs 5년 평균 (<-30%=4, -30~-10%=3, -10~+10%=2, >+10%=1)
3. PBR 절대 (<0.7=4, 0.7-1.0=3, 1.0-1.5=2, >1.5=1)
4. 부채비율 (<50%=4, 50-100%=3, 100-200%=2, >200%=1)
5. 유동비율 (>2.0=4, 1.5-2.0=3, 1.0-1.5=2, <1.0=1)
6. FCF 추세 (3년양수=4, 2년=3, 1년=2, 음수=1)
7. 매출 CAGR (>10%=4, 5-10%=3, 0-5%=2, <0%=1)

등급: A(24-28), B+(20-23), B(16-19), C(12-15), D(<12)

#### 스케줄러 (`services/scheduler_service.py`)

APScheduler AsyncIOScheduler(timezone='Asia/Seoul'):
- 08:00 → run_pipeline('KR')
- 16:00 → run_pipeline('US')
- main.py lifespan에서 시작/종료

#### Telegram (`services/telegram_service.py`)

- `send_report_notification(report_id, recommendations)` → 요약 + 인라인 승인 버튼
- `handle_approval_callback(rec_id, action)` → 승인 시 예약주문 등록
- 환경변수: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

#### API 엔드포인트

```
POST /api/pipeline/run?market=KR     수동 파이프라인 실행
GET  /api/pipeline/status            스케줄러 상태 + 다음 실행 시각
GET  /api/pipeline/history           실행 이력
POST /api/telegram/webhook           Telegram 봇 콜백
GET  /api/telegram/status            봇 상태
```

#### DB 모델 (이미 생성됨)

- `recommendation_history` — 추천 이력 + 실행 추적 + 성과
- `macro_regime_history` — 체제 판단 일일 이력
- `daily_reports` — 통합 보고서 Markdown + JSON

---

## Module 1: 포트폴리오 대시보드 (`/portfolio`)

### 백엔드

#### API 엔드포인트

```
GET /api/portfolio/overview
```

기존 API를 조합하여 통합 뷰를 반환한다:

```json
{
  "total_evaluation": 50000000,
  "total_profit_rate": 8.5,
  "cash_amount": 15000000,
  "cash_ratio": 30.0,
  "stock_eval": 35000000,
  "stock_ratio": 70.0,
  "regime": "selective",
  "regime_color": "yellow",
  "regime_summary": "선별 매수 체제 — 안전마진 25%+ 종목만 매수 권장",
  "holdings": [
    {
      "code": "005930",
      "name": "삼성전자",
      "market": "KR",
      "quantity": 100,
      "avg_price": 55000,
      "current_price": 58000,
      "eval_amount": 5800000,
      "profit_rate": 5.45,
      "weight_pct": 11.6,
      "sector": "반도체",
      "graham_grade": "B+",
      "margin_of_safety": 22.5
    }
  ],
  "sector_allocation": [
    {"sector": "반도체", "weight_pct": 25.0, "amount": 12500000},
    {"sector": "금융", "weight_pct": 15.0, "amount": 7500000}
  ],
  "updated_at": "2026-04-03T15:00:00+09:00"
}
```

**구현 방법**: `services/portfolio_service.py`에서 `/api/balance` 결과를 가공. 종목별 `advisory/{code}/data`로 안전마진/등급 수집. `/api/macro/sentiment`로 체제 정보 추가.

#### DB (선택)

포트폴리오 스냅샷 이력 저장이 필요하면 `stock/portfolio_store.py`에 일일 스냅샷 테이블:

```sql
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    total_evaluation REAL,
    cash_amount REAL,
    stock_eval REAL,
    regime TEXT,
    holdings_json TEXT,  -- JSON 직렬화
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date)
);
```

### 프론트엔드

#### 컴포넌트 구조

```
components/portfolio/
├── PortfolioSummaryCard.jsx   — 총 자산/수익률/현금비중 카드
├── AssetAllocationChart.jsx   — Recharts PieChart (종목별/섹터별 토글)
├── HoldingsTable.jsx          — 보유종목 테이블 (등급 뱃지, 안전마진 %)
├── RegimeBanner.jsx           — 매크로 체제 상단 배너 (색상 코딩)
└── PerformanceSparkline.jsx   — 최근 30일 수익률 미니 차트
```

#### 체제별 색상

| 체제 | 색상 | Tailwind 클래스 |
|------|------|----------------|
| accumulation | 초록 | `bg-green-100 text-green-800 border-green-300` |
| selective | 노랑 | `bg-yellow-100 text-yellow-800 border-yellow-300` |
| cautious | 주황 | `bg-orange-100 text-orange-800 border-orange-300` |
| defensive | 빨강 | `bg-red-100 text-red-800 border-red-300` |

---

## Module 2: 리밸런싱 엔진 (`/rebalance`)

### 백엔드

#### API 엔드포인트

```
GET /api/rebalance/status
```

현재 포트폴리오의 리밸런싱 필요 상태를 반환:

```json
{
  "needs_rebalance": true,
  "regime": "selective",
  "target_cash_ratio": 35.0,
  "current_cash_ratio": 20.0,
  "overweight_stocks": [
    {"code": "005930", "name": "삼성전자", "current_pct": 8.0, "target_pct": 4.0, "excess_pct": 4.0}
  ],
  "underweight_stocks": [],
  "violations": [
    "삼성전자: 단일종목 8.0% → 한도 4.0% 초과",
    "현금비중 20.0% → 목표 35.0% 미달"
  ]
}
```

```
POST /api/rebalance/propose
```

리밸런싱 실행 제안 생성:

```json
{
  "proposals": [
    {
      "action": "sell",
      "code": "005930",
      "name": "삼성전자",
      "quantity": 50,
      "price": 58000,
      "amount": 2900000,
      "reason": "단일종목 한도 초과 (8.0% → 4.0%)"
    },
    {
      "action": "buy",
      "code": "035720",
      "name": "카카오",
      "quantity": 30,
      "price": 42000,
      "amount": 1260000,
      "reason": "안전마진 32.5% (등급 A) — 신규 편입"
    }
  ],
  "estimated_after": {
    "cash_ratio": 36.0,
    "max_single_stock_pct": 4.0,
    "total_stock_ratio": 64.0
  }
}
```

```
POST /api/rebalance/execute
```

제안된 리밸런싱을 예약주문으로 등록 (사용자 명시적 승인 후):
- 각 proposal을 `POST /api/order/reserve`로 변환
- 매도 우선 → 매수 순서

#### 서비스

`services/rebalance_service.py`:
- `check_rebalance_status()` — 현재 배분 vs Graham 목표 비교
- `generate_proposals()` — 매도/매수 제안 생성
- `execute_proposals()` — 예약주문 일괄 등록

**핵심 규칙 (OrderAdvisor 원칙 준수)**:
- 체제별 목표: accumulation 75%/5%, selective 65%/4%, cautious 50%/3%, defensive 0%/0%
- 매도 우선: 과대비중 매도 → 현금 확보 → 신규/과소비중 매수
- 지정가만 사용 (시장가 금지)
- 자동 실행 금지: 반드시 사용자 승인 후 예약주문

### 프론트엔드

```
components/rebalance/
├── RebalanceStatusCard.jsx    — 리밸런싱 필요 여부 + 위반 사항
├── AllocationCompareTable.jsx — 현재 vs 목표 비교 (편차 색상)
├── ProposalList.jsx           — 매도/매수 제안 카드
└── ExecuteButton.jsx          — "예약주문 등록" 확인 다이얼로그
```

---

## Module 3: 리스크 모니터링 (`/risk`)

### 백엔드

#### API 엔드포인트

```
GET /api/risk/dashboard
```

```json
{
  "hhi_index": 1250,
  "hhi_level": "moderate",
  "concentration_warning": "삼성전자 11.6% — 한도(4.0%) 초과",
  "margin_alerts": [
    {
      "code": "005930",
      "name": "삼성전자",
      "current_margin": 15.2,
      "previous_margin": 22.5,
      "change": -7.3,
      "grade": "B",
      "alert_level": "warning"
    }
  ],
  "stoploss_alerts": [
    {
      "code": "035720",
      "name": "카카오",
      "current_price": 43000,
      "stoploss_price": 42000,
      "distance_pct": 2.3,
      "alert_level": "danger"
    }
  ],
  "regime_history": [
    {"date": "2026-04-01", "regime": "selective"},
    {"date": "2026-03-15", "regime": "cautious"}
  ]
}
```

#### DB

`stock/risk_store.py` — `~/stock-watchlist/risk.db`:

```sql
CREATE TABLE IF NOT EXISTS margin_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    graham_number REAL,
    current_price REAL,
    margin_of_safety REAL,
    grade TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(code, date)
);

CREATE TABLE IF NOT EXISTS regime_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    regime TEXT NOT NULL,
    buffett_ratio REAL,
    fear_greed_score REAL,
    vix REAL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(date)
);
```

#### HHI 계산

```python
# 허핀달-허쉬만 지수: 각 종목 비중의 제곱합 × 10000
hhi = sum(w**2 for w in weight_pcts) * 10000
# < 1000: 분산 양호, 1000-1800: 보통, > 1800: 집중
```

### 프론트엔드

```
components/risk/
├── RiskDashboard.jsx        — 전체 리스크 요약
├── ConcentrationGauge.jsx   — HHI 게이지 차트
├── MarginAlertList.jsx      — 안전마진 변화 알림 리스트
├── StoplossAlertList.jsx    — 손절 근접 종목 경고
└── RegimeTimeline.jsx       — 체제 변화 타임라인 (세로)
```

---

## Module 4: 성과 추적 (`/performance`)

### 백엔드

#### API 엔드포인트

```
GET /api/performance/returns?period=1m|3m|6m|1y|ytd|all
```

```json
{
  "period": "3m",
  "total_return_pct": 8.5,
  "benchmark_return_pct": 5.2,
  "excess_return_pct": 3.3,
  "daily_returns": [
    {"date": "2026-01-03", "portfolio_pct": 0.5, "benchmark_pct": 0.3}
  ],
  "top_contributors": [
    {"code": "005930", "name": "삼성전자", "contribution_pct": 3.2}
  ],
  "bottom_contributors": [
    {"code": "035720", "name": "카카오", "contribution_pct": -1.1}
  ],
  "dividend_total": 250000,
  "twr_pct": 9.1
}
```

#### DB

`stock/portfolio_store.py`의 `portfolio_snapshots` 테이블 활용 + 체결이력(`orders.db`)에서 매매 기록 추출.

**TWR (Time-Weighted Return) 계산**:
```python
# 외부 현금흐름(입출금) 영향 제거
# 각 sub-period 수익률의 기하 평균
twr = product(1 + r_i for r_i in sub_returns) - 1
```

### 프론트엔드

```
components/performance/
├── ReturnSummaryCard.jsx     — 수익률 요약 (포트폴리오 vs 벤치마크)
├── ReturnChart.jsx           — Recharts LineChart (듀얼 라인)
├── ContributionWaterfall.jsx — 종목별 기여도 워터폴 차트
├── PeriodSelector.jsx        — 기간 선택 (1m/3m/6m/1y/YTD/전체)
└── DividendSummary.jsx       — 배당 수익 요약
```

---

## Module 5: 투자 일지 (`/journal`)

### 백엔드

#### API 엔드포인트

```
GET /api/journal/entries?page=1&limit=20
POST /api/journal/entries       — 메모 추가
PUT /api/journal/entries/{id}   — 메모 수정
DELETE /api/journal/entries/{id}
```

```json
{
  "entries": [
    {
      "id": 1,
      "date": "2026-04-01",
      "type": "trade",
      "code": "005930",
      "name": "삼성전자",
      "action": "buy",
      "quantity": 50,
      "price": 55000,
      "context": {
        "regime": "selective",
        "margin_of_safety": 25.3,
        "grade": "B+",
        "buffett_ratio": 92.5,
        "fear_greed": 28
      },
      "memo": "안전마진 25%+ 확인 후 1차 분할 매수. 반도체 업황 반등 기대.",
      "outcome": {
        "current_price": 58000,
        "profit_pct": 5.45,
        "holding_days": 2
      }
    }
  ],
  "total_count": 45,
  "page": 1
}
```

#### DB

`stock/journal_store.py` — `~/stock-watchlist/journal.db`:

```sql
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'trade',  -- trade / memo / alert
    code TEXT,
    name TEXT,
    action TEXT,            -- buy / sell / null (memo)
    quantity INTEGER,
    price REAL,
    context_json TEXT,      -- 매매 시점 체제/등급/안전마진 스냅샷
    memo TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(date);
CREATE INDEX IF NOT EXISTS idx_journal_code ON journal_entries(code);
```

### 프론트엔드

```
components/journal/
├── JournalTimeline.jsx    — 타임라인 뷰 (날짜 그룹핑)
├── TradeEntry.jsx         — 매매 기록 카드 (컨텍스트 태그 포함)
├── MemoEntry.jsx          — 메모 기록 카드
├── JournalEditor.jsx      — 메모 작성/수정 모달
└── OutcomeTag.jsx         — 수익률 뱃지 (수익=초록, 손실=빨강)
```

---

## 공통 컴포넌트

모듈 간 공유되는 UI 요소:

```
components/common/
├── GradeBadge.jsx         — 안전마진 등급 뱃지 (A=초록, B+=연두, B=노랑, C=주황, D=빨강)
├── RegimeIndicator.jsx    — 매크로 체제 인디케이터 (dot + label)
├── PercentageChange.jsx   — 변화율 표시 (▲초록/▼빨강)
├── LoadingSpinner.jsx     — 로딩 스피너 (이미 존재할 수 있음)
└── EmptyState.jsx         — 데이터 없음 상태 (이미 존재할 수 있음)
```
