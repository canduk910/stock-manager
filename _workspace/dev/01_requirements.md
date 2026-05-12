# 기능 요건서: 수급정보(개인/외국인/기관) V1 — 매크로 지수 + 종목 상세

## 개요

KIS OpenAPI의 시장별/종목별 투자자매매동향(일별) TR을 wrapper.py에 신규 구현하고, 백엔드 서비스/캐시/API 엔드포인트와 프론트엔드 컴포넌트를 추가하여 다음 두 영역에 수급 데이터(개인/외국인/기관계 + 세부)를 가시화한다.

1. **매크로 페이지**: 코스피/코스닥 지수 단위 일별 수급 + 누적 추세 (`SupplyDemandSection`)
2. **종목 상세 페이지**: 종합 리포트 신규 서브탭 "수급/투자자" (`SupplyDemandPanel`)

**V1 범위(가시화 위주)**:
- 데이터 페치 + 표시. AI 자문/체제 판단 미반영.
- 단위: 거래대금 **억원** 통일(KIS `tr_pbmn` 백만원 ÷ 100).
- 기간: 기본 20거래일, 슬라이더 10~60일.
- KIS 키 미설정 환경 부분 실패 정책(다른 섹션 정상, 수급 카드만 안내).

**V2 분리 항목** (본 요건 범위 외):
- 섹터별 수급 가시화
- AI 자문 입력 통합(외국인·기관 동반 매수 N일 시그널)
- 외국인 보유비율 추이(별도 TR `FHKST01010800`)
- 체제 가중치 반영(REGIME_MATRIX 보조 단서)
- 개인 과열 경고 등급 감점

---

## 도메인 자문 합의 (V1 가벼움)

### MacroSentinel 자문 결론
- **단위**: 억원(거래대금 기준, `tr_pbmn` ÷ 100)
- **기간**: 20거래일 기본, 10~60일 슬라이더. 60일 초과는 V2(누적 추세 분석)
- **누적선**: 기간 시작일 0 기준 누적합, 보조 y축(우측) 별도 노출
- **색상 표준**(한국 차트 컨벤션): 외국인=파란(#3B82F6), 기관=초록(#10B981), 개인=빨강(#EF4444)
- **체제 가중치 미반영**: REGIME_MATRIX 결합은 V2. SupplyDemandSection은 매크로 페이지 내 독립 카드로 분리(체제 배너와 색상/계산 충돌 없음).
- **Graham 근거**: 수급은 시장 심리(공포탐욕) 보조 지표일 뿐, 밸류에이션(버핏지수)을 대체하지 않음.

### OrderAdvisor 자문 결론
- **V1은 표시만**: 주문 도메인 변경 0건. 매수/매도 의사결정에 **단독 시그널로 사용 금지**(Graham 원칙).
- **안전 고지**: 종목 상세 수급 패널에 "참고용 데이터, 매매 신호 아님" 1줄 명시.
- **데이터 결측 처리**: 휴장일·신규 상장(30일 미만) 시 응답은 빈/부분 배열, UI는 "데이터 부족, N거래일분 표시" 안내. None 폴백.
- **자동 주문 트리거 금지**: V1엔 트리거 없으나 미래 방지 위해 라우터 응답에 매매 액션 키 포함 금지.
- **V2 통합 시 임계값(사전 합의, 본 요건 미적용)**:
  - 외국인·기관 동반 매수 **5거래일 연속** = 수급 청신호 보조
  - 6개월 누적 외국인+기관 매도 + 개인 매수 우세 = 개인 과열 경고
  - 등급 가중치 ≤ 0.1로 제한(매크로/안전마진 우위 유지)

### 전문가 간 합의
- 단위 억원 통일(양측 동의, 매크로/종목 일관성)
- V1은 단순 표시(체제 가중치·AI 입력은 V2 명확 분리)
- 안전 고지 문구는 종목 상세에만(매크로는 시장 단위라 매매 트리거 우려 낮음)

---

## 요건 항목

### SUPPLY-API: KIS wrapper TR 신규 구현

#### [REQ-SUPPLY-API-01] 시장별 투자자매매동향(일별) wrapper 메서드

설명: KIS TR_ID `FHPTJ04040000`을 호출하는 `wrapper.py` 메서드 추가. KOSPI/KOSDAQ 지수 단위 일별 개인/외국인/기관(세부 11종)/etc 순매수 거래대금·수량 응답을 표준화하여 반환.

수용 기준:
- 메서드 시그니처: `get_market_investor_daily(market_code: str, days: int = 20) -> list[dict]`
- `market_code` 허용값: `"U001"` (KOSPI) 또는 `"U201"` (KOSDAQ). 그 외 ValueError.
- `days` 범위: 1 ≤ days ≤ 60. 범위 외 ValueError.
- KIS 요청 파라미터: `FID_COND_MRKT_DIV_CODE=U`, `FID_INPUT_ISCD=0001(코스피)/1001(코스닥)`, `FID_INPUT_DATE_1=오늘 yyyymmdd`, `FID_INPUT_ISCD_1=KSP/KSQ`, `FID_INPUT_DATE_2=오늘 yyyymmdd`, `FID_INPUT_ISCD_2=KSP/KSQ`.
- (정확한 입력 파라미터 매핑은 `docs/kis/07_KR_MARKET_ANALYSIS.md` L1685~1693을 1차 출처로 하되, 구현 시 `mcp__kis-code-assistant__search_domestic_stock_api`로 재검증 필수.)
- 응답 표준화 후 반환 키:
  - `date` (str, YYYY-MM-DD), `index_close` (float, `bstp_nmix_prpr`), `prev_diff` (float, `bstp_nmix_prdy_vrss`), `prev_pct` (float, `bstp_nmix_prdy_ctrt`)
  - 거래대금 키 (단위: 백만원, 원본 그대로): `personal_net_amt`(`prsn_ntby_tr_pbmn`), `foreign_net_amt`(`frgn_ntby_tr_pbmn`), `institution_net_amt`(`orgn_ntby_tr_pbmn`)
  - 기관 세부(11종, 백만원): `securities_net_amt`(`scrt_*`), `inv_trust_net_amt`(`ivtr_*`), `private_fund_net_amt`(`pe_fund_*`), `bank_net_amt`(`bank_*`), `insurance_net_amt`(`insu_*`), `mrbn_net_amt`(`mrbn_*`), `pension_net_amt`(`fund_*`), `etc_finance_net_amt`(`etc_*`), `etc_corp_net_amt`(`etc_corp_*`), `etc_org_net_amt`(`etc_orgt_*`)
- 빈 응답 또는 KIS 에러 시: `ExternalAPIError(502)` raise (캐시·라우터 레이어에서 처리).
- 단위 변환(억원)은 service 레이어에서 수행. wrapper는 원본 단위(백만원) 유지.

테스트 힌트:
- 입력: `("U001", 20)` → 길이 20 list, 각 항목에 위 키 모두 포함, `date` 포맷 검증
- 입력: `("U999", 20)` → ValueError
- 입력: `("U001", 0)` → ValueError
- 입력: `("U001", 70)` → ValueError
- KIS 503 mock → ExternalAPIError

도메인 근거: KIS API 명세 (`docs/kis/07_KR_MARKET_ANALYSIS.md` L1641~1860). 시장 TR은 기관 11종 세부 + 외국인 등록/비등록 분해 제공.
레이어: unit
관련 전문가: 없음(외부 API 매핑)

---

#### [REQ-SUPPLY-API-02] 종목별 투자자매매동향(일별) wrapper 메서드

설명: KIS TR_ID `FHPTJ04160001`을 호출하는 `wrapper.py` 메서드 추가. 종목 단위 일별 개인/외국인/기관(세부 11종) 순매수 거래대금·수량 + 매수·매도 분리 응답을 표준화.

수용 기준:
- 메서드 시그니처: `get_stock_investor_daily(code: str, days: int = 30) -> list[dict]`
- `code`: 6자리 숫자 검증, 그 외 ValueError. 비국내 종목(US 등)은 ValueError("국내 종목만 지원").
- `days` 범위: 1 ≤ days ≤ 60. 범위 외 ValueError.
- 응답 표준화 키(REQ-SUPPLY-API-01과 동일 11종 기관 분해) + 추가 키:
  - `personal_buy_amt`/`personal_sell_amt` (개인 매수·매도 분리 거래대금, 백만원)
  - `foreign_buy_amt`/`foreign_sell_amt`
  - `institution_buy_amt`/`institution_sell_amt`
  - `close_price` (종가, 원, `stck_clpr` 또는 동등 필드)
- 신규 상장 등으로 30일 데이터 부족 시: 실제 반환된 일수만큼만 반환(가능한 만큼). 빈 배열은 정상 응답(예외 X).
- KIS 에러(rt_cd != "0") 시: `ExternalAPIError(502)` raise.
- 단위 변환(억원)은 service 레이어. wrapper는 백만원 유지.

테스트 힌트:
- 입력: `("005930", 30)` → 길이 ≤ 30, 표준 키 모두 존재
- 입력: `("AAPL", 30)` → ValueError
- 입력: `("00593", 30)` → ValueError (5자리)
- 입력: `("005930", 0)` → ValueError
- 신규 상장 종목 mock(7일 응답) → 길이 7 list (예외 X)
- KIS rt_cd="1" mock → ExternalAPIError

도메인 근거: KIS API 명세 (`docs/kis/07_KR_MARKET_ANALYSIS.md` L1968~2330). 종목 TR은 기관 세부 + 매수/매도 분리 제공(매크로 TR에는 없음).
레이어: unit
관련 전문가: 없음

---

### SUPPLY-CACHE: 캐시 정책

#### [REQ-SUPPLY-CACHE-01] 일별 수급 캐시(영속 + in-memory)

설명: 일별 수급 데이터의 캐시 전략. KST 일자 종료 후 데이터는 변경되지 않으므로 영속 캐시, 장중 호출은 in-memory TTL 10분.

수용 기준:
- 영속 캐시: `stock/macro_store.py` 패턴 재사용. 카테고리 키 명명:
  - 시장: `supply_demand:market:{market}` (예: `supply_demand:market:kospi`)
  - 종목: `supply_demand:stock:{code}` (예: `supply_demand:stock:005930`)
- 영속 캐시 적중 조건: 응답의 가장 최근 날짜(`date`)가 **전 거래일** 또는 그 이전인 경우 (오늘 데이터 없거나 마감 후) → 캐시 hit.
- 장중(KST 09:00~15:30, 토·일 제외)에는 마지막 데이터가 오늘 날짜면 in-memory 10분 TTL 적용. 만료 시 KIS 재호출.
- DB 마이그레이션 0건. `macro_store`의 `category` 컬럼에 위 키 그대로 저장(KST `date` 기반).
- 캐시 적중 시에도 응답 단위 변환(억원)은 서비스 레이어에서 매번 수행.

테스트 힌트:
- 첫 호출(캐시 미스) → KIS 호출 1회 + macro_store.save_today
- 두 번째 호출(같은 일자) → macro_store.get_today hit, KIS 호출 0회
- 장중 시뮬레이션(`now_kst` mock, 14:00) + 같은 카테고리 11분 후 호출 → KIS 재호출
- 60거래일 데이터 캐시 후 30거래일 요청 → 캐시에서 slice 반환(KIS 호출 0회)

도메인 근거: 기존 `services/macro_service.py` GPT 일일 캐시와 동일 패턴(macro_store 재사용).
레이어: unit
관련 전문가: 없음

---

### SUPPLY-MACRO: 매크로 시장 수급 서비스

#### [REQ-SUPPLY-MACRO-01] `services/supply_demand_service.fetch_market_supply_demand`

설명: 시장(코스피/코스닥) 일별 수급 + 누적 데이터를 반환하는 서비스 함수.

수용 기준:
- 함수 시그니처: `fetch_market_supply_demand(market: str, days: int = 20) -> dict`
- `market` 허용값: `"kospi"` 또는 `"kosdaq"`. 그 외 `ServiceError(400)`.
- `days` 범위: 10 ≤ days ≤ 60. 범위 외 `ServiceError(400)`.
- KIS 키 미설정(`KIS_APP_KEY` 또는 `KIS_APP_SECRET` 빈 값) → `ConfigError(503)`.
- KIS 호출 실패(timeout/HTTP 5xx) → `ExternalAPIError(502)`.
- 단위 변환: 모든 `*_amt` 필드는 백만원 → **억원** (÷100, 정수 반올림).
- 응답 shape:
  ```
  {
    "market": "kospi",
    "days": 20,
    "as_of": "2026-05-11",
    "color_map": {"personal":"#EF4444","foreign":"#3B82F6","institution":"#10B981"},
    "daily": [
      {
        "date": "2026-04-15",
        "index_close": 2724.62,
        "personal_net": 7207,   // 억원
        "foreign_net": -5974,
        "institution_net": -1506,
        "institution_detail": {  // 억원
          "securities": -188, "inv_trust": -72, "private_fund": -256,
          "bank": 33, "insurance": -137, "mrbn": -27, "pension": -856,
          "etc_finance": 273, "etc_corp": 273, "etc_org": 0
        }
      }, ...
    ],
    "cumulative": [
      {"date": "2026-04-15", "personal_cum": 7207, "foreign_cum": -5974, "institution_cum": -1506},
      // 기간 시작일 0 기준 누적합
    ],
    "summary": {  // 오늘(가장 최근 일자) 기준
      "personal_today": 7207,
      "foreign_today": -5974,
      "institution_today": -1506,
      "personal_cum_total": 12345,
      "foreign_cum_total": -8765,
      "institution_cum_total": -3580
    }
  }
  ```
- `daily` 배열은 오래된 날짜 → 최근 날짜 순(ascending).
- `cumulative`는 `daily` 시작일 0부터 누적합 계산. `daily[i]`와 `cumulative[i]`는 1:1 매칭.
- 데이터 부족 시(휴장 등으로 N일 미만 응답): 반환된 일수만큼만 반환. `days` 필드는 요청값 유지, `daily` 길이는 실제 응답 일수.

테스트 힌트:
- `fetch_market_supply_demand("kospi", 20)` → daily 길이 ≤ 20, summary 키 모두 존재
- `fetch_market_supply_demand("FX", 20)` → ServiceError
- `fetch_market_supply_demand("kospi", 5)` → ServiceError(범위 외)
- KIS 키 mock 빈 값 → ConfigError
- KIS 호출 mock raise → ExternalAPIError
- 누적 검증: `cumulative[-1].foreign_cum == sum(daily[i].foreign_net for i in range(N))`
- 단위 변환: KIS `prsn_ntby_tr_pbmn=720787` → `personal_net=7208` (백만원 → 억원, 반올림)

도메인 근거: MacroSentinel 자문(억원 단위 + 20일 기본 + Graham 보조지표). REQ-SUPPLY-API-01 응답 표준화.
레이어: unit / integration
관련 전문가: MacroSentinel

---

### SUPPLY-STOCK: 종목 수급 서비스

#### [REQ-SUPPLY-STOCK-01] `services/supply_demand_service.fetch_stock_supply_demand`

설명: 종목 일별 수급 + 누적 + 매수·매도 분리 데이터를 반환하는 서비스 함수.

수용 기준:
- 함수 시그니처: `fetch_stock_supply_demand(code: str, days: int = 30) -> dict`
- `code`: `stock.utils.is_domestic(code)` True여야 함. 아니면 `ServiceError(400, "국내 종목만 지원")`.
- `days` 범위: 10 ≤ days ≤ 60. 범위 외 `ServiceError(400)`.
- KIS 키 미설정 → `ConfigError(503)`.
- 종목 미존재(KIS rt_cd!="0" 또는 빈 응답) → `NotFoundError(404)` (REQ-SUPPLY-MACRO-01과 차이점: 시장은 항상 존재).
- 단위: 모든 `*_amt`는 억원 변환.
- 응답 shape (시장 응답에 매수/매도 분리 + close_price 추가):
  ```
  {
    "code": "005930",
    "name": "삼성전자",
    "days": 30,
    "as_of": "2026-05-11",
    "color_map": {...},
    "advisory_note": "참고용 데이터입니다. 매매 신호로 단독 사용 금지(Graham 원칙).",
    "daily": [
      {
        "date": "2026-04-15",
        "close": 71500,
        "personal_net": 152, "personal_buy": 432, "personal_sell": 280,
        "foreign_net": -89, "foreign_buy": 210, "foreign_sell": 299,
        "institution_net": -63, "institution_buy": 178, "institution_sell": 241,
        "institution_detail": {...}  // REQ-SUPPLY-MACRO-01과 동일 11종
      }, ...
    ],
    "cumulative": [...],
    "summary": {...}
  }
  ```
- `advisory_note`는 OrderAdvisor 자문 결과 고지 문구로 고정. 응답에 항상 포함.
- 신규 상장 등으로 30일 미만 응답: 정상 처리(예외 X), `daily`는 실제 일수, summary 첫 일자=실제 시작일.

테스트 힌트:
- `fetch_stock_supply_demand("005930", 30)` → daily 키 정상
- `fetch_stock_supply_demand("AAPL", 30)` → ServiceError
- 7일 응답 mock(신규 상장) → daily 길이 7, 예외 X
- KIS rt_cd="1" mock → NotFoundError
- 응답에 `advisory_note` 키 항상 존재
- `personal_net == personal_buy - personal_sell` (매수/매도 일관성)

도메인 근거: OrderAdvisor 자문(참고용 고지 + 단독 시그널 금지). REQ-SUPPLY-API-02 응답 표준화.
레이어: unit / integration
관련 전문가: OrderAdvisor

---

### SUPPLY-ROUTER: 라우터 엔드포인트

#### [REQ-SUPPLY-ROUTER-01] `GET /api/macro/supply-demand`

설명: 매크로 페이지용 시장 수급 API. `routers/macro.py` 확장.

수용 기준:
- 메서드/경로: `GET /api/macro/supply-demand`
- 쿼리 파라미터: `market: Literal["kospi","kosdaq"]` (필수), `days: int = 20` (기본 20, 10~60)
- 응답: REQ-SUPPLY-MACRO-01 dict 그대로 (단위 억원)
- 예외 매핑: `ServiceError`→400, `ConfigError`→503, `ExternalAPIError`→502
- `HTTPException` 직접 raise 금지. `services/exceptions.py` 경유.
- KIS 키 미설정 환경에서 503 응답 시 `{"detail": {"message": "KIS API 키 설정이 필요합니다."}}` 포함.

테스트 힌트:
- `GET /api/macro/supply-demand?market=kospi&days=20` → 200, daily 키 존재
- `GET /api/macro/supply-demand?market=fx` → 422 (FastAPI Literal 검증)
- `GET /api/macro/supply-demand?market=kospi&days=100` → 400 (ServiceError)
- KIS 키 비움 mock → 503, message 검증

도메인 근거: 기존 routers/macro.py 부분 실패 패턴.
레이어: api
관련 전문가: MacroSentinel

---

#### [REQ-SUPPLY-ROUTER-02] `GET /api/advisory/{code}/supply-demand`

설명: 종목 상세용 종목 수급 API. `routers/advisory.py` 확장.

수용 기준:
- 메서드/경로: `GET /api/advisory/{code}/supply-demand`
- 쿼리 파라미터: `days: int = 30` (기본 30, 10~60)
- 응답: REQ-SUPPLY-STOCK-01 dict 그대로
- 예외 매핑: `ServiceError`→400, `NotFoundError`→404, `ConfigError`→503, `ExternalAPIError`→502
- 응답 키 `advisory_note` 반드시 포함(OrderAdvisor 자문 고지 문구).
- 매매 액션 키(예: `recommendation`, `action`) 포함 금지(OrderAdvisor 자문: V1은 표시만).

테스트 힌트:
- `GET /api/advisory/005930/supply-demand?days=30` → 200, advisory_note 존재
- `GET /api/advisory/AAPL/supply-demand` → 400
- `GET /api/advisory/999999/supply-demand` (미존재) → 404
- 응답 JSON에 `recommendation`/`action`/`buy_signal` 키 부재 검증
- KIS 키 비움 mock → 503

도메인 근거: OrderAdvisor 자문(고지 + 매매 액션 없음).
레이어: api
관련 전문가: OrderAdvisor

---

### SUPPLY-UI: 프론트엔드

#### [REQ-SUPPLY-UI-01] 매크로 페이지 `SupplyDemandSection.jsx`

설명: 매크로 페이지에 코스피/코스닥 토글 + 일별 막대 + 누적 라인 차트 컴포넌트 추가.

수용 기준:
- 파일: `frontend/src/components/macro/SupplyDemandSection.jsx` (신규)
- 마운트 위치: `frontend/src/pages/MacroPage.jsx`의 `<IndexSection />` 직후
- 토글: 코스피/코스닥 segment control (기존 `SectorHeatmapSection`의 KR/US 토글 패턴 차용)
- 기간 슬라이더: 10~60일, step 5, 기본 20
- 차트: Recharts `ComposedChart`
  - x축: 일자 (MM-DD, 툴팁 YYYY-MM-DD)
  - 좌측 y축: 일별 막대(억원), 양수 위/음수 아래
  - 우측 y축: 누적 라인(억원), 3선(개인/외국인/기관)
  - 색상: 개인=#EF4444, 외국인=#3B82F6, 기관=#10B981 (응답 `color_map` 활용)
- 당일 요약 칩 (1줄): "외국인 +X억 / 기관 -Y억 / 개인 +Z억", 부호별 색상 표시
- 부분 실패 격리: API 503/502 시 카드 내부에 "수급 데이터는 KIS API 키 설정이 필요합니다" / "KIS API 호출 실패" 안내, 다른 매크로 섹션은 정상 렌더
- 로딩 상태: 스켈레톤 또는 spinner
- `frontend/src/api/macro.js`에 `fetchSupplyDemand(market, days)` 추가 (axios)
- `frontend/src/hooks/useMacro.js`에 `useSupplyDemand(market, days)` 훅 추가(다른 매크로 훅과 동일 패턴, 독립 로딩/에러 state)

테스트 힌트:
- 매크로 페이지 진입 → 지수 카드 아래 수급 카드 노출
- 코스피 → 코스닥 토글 → 새 데이터 페치
- 슬라이더 20 → 60 → 새 데이터 페치 (debounce 권장 300ms)
- KIS 키 미설정 환경 → 다른 섹션 정상, 수급 카드만 안내 메시지
- 차트 색상 visual 검증

도메인 근거: MacroSentinel 자문(20일 기본, 억원, 한국 차트 색상 표준).
레이어: ui (수동 검증)
관련 전문가: MacroSentinel

---

#### [REQ-SUPPLY-UI-02] 종목 상세 페이지 `SupplyDemandPanel.jsx`

설명: 종목 상세 페이지 종합 리포트 탭에 신규 서브탭 "수급/투자자" 추가.

수용 기준:
- 파일: `frontend/src/components/advisory/SupplyDemandPanel.jsx` (신규)
- 마운트: `frontend/src/pages/DetailPage.jsx`의 `REPORT_SUB_TABS`에 `{id:'supply-demand', label:'수급/투자자'}` 추가 (기존 4개 + 1 = 5개)
- lazy-mount: 탭 선택 시에만 렌더
- 차트: REQ-SUPPLY-UI-01과 동일 패턴(ComposedChart, 일별 막대 + 누적 라인 + 색상 표준)
- 기간 슬라이더: 10~60일, 기본 30일
- 매수/매도 분리 표시(옵션): 차트 하단 토글 "순매수 / 매수·매도 분리". 분리 모드에서는 매수 양수/매도 음수 막대로 표시.
- 안전 고지 (OrderAdvisor 자문): 카드 상단에 1줄 노란색 배너로 응답의 `advisory_note` 표시 ("참고용 데이터입니다. 매매 신호로 단독 사용 금지(Graham 원칙).")
- 부분 실패 격리: API 503/502 시 패널 내부 안내, 다른 서브탭은 정상
- `frontend/src/api/advisory.js`에 `fetchStockSupplyDemand(code, days)` 추가
- `frontend/src/hooks/useAdvisory.js`에 `useStockSupplyDemand(code, days)` 훅 추가
- 외국인 보유비율 추이는 미포함(V2)

테스트 힌트:
- 005930 진입 → 종합 리포트 → "수급/투자자" 서브탭 클릭 → 차트 + 고지 배너
- 신규 상장 종목(예: 30일 미만 이력) → daily 일수만큼만 표시, 에러 없음
- 매수/매도 분리 토글 → 막대 모양 변경
- 응답 검증: `advisory_note` 텍스트 정확 표시
- KIS 키 미설정 → 패널 안내 메시지, 다른 서브탭 정상

도메인 근거: OrderAdvisor 자문(고지 배너, 매매 액션 없음, 결측 부드러운 처리).
레이어: ui (수동 검증)
관련 전문가: OrderAdvisor

---

## 교차 검토 체크리스트

- [x] 단위 통일(억원): API/Service/UI 일관 — REQ-SUPPLY-API-01/02는 백만원 유지, Service에서 ÷100 변환, UI는 변환된 값 그대로 표시
- [x] 기간 범위 일관(10~60): API/Service/UI 모두 10~60 검증
- [x] 색상 표준(개인 빨강/외국인 파랑/기관 초록): Service `color_map` 응답 → UI 사용
- [x] KIS 키 미설정 시 부분 실패: ConfigError 503 + UI 안내 카드(다른 섹션 정상)
- [x] 예외 계층 준수: ServiceError(400)/NotFoundError(404)/ConfigError(503)/ExternalAPIError(502)만 사용, HTTPException 금지
- [x] 자동 주문 트리거 금지(OrderAdvisor): 응답에 매매 액션 키 부재 검증 테스트 포함
- [x] 안전 고지(OrderAdvisor): 종목 응답에 `advisory_note` 키 + UI 노란 배너
- [x] 데이터 결측 부드러운 처리: 신규 상장 30일 미만 → 빈 배열 아닌 부분 배열, 예외 X
- [x] DB 마이그레이션 0건: macro_store 재사용
- [x] V2 명확 분리: 섹터/AI 입력/보유비율/체제 가중치/과열 경고 모두 본 요건 범위 외 표시
- [x] defensive 체제 예외 처리: 매크로 페이지 독립 카드(체제 배너와 충돌 없음). V1 가시화이므로 투자 중단 로직 무관.

## 통합 테스트 매트릭스

| 시나리오 | 기대 결과 |
|----------|----------|
| 정상 KIS 키 + KOSPI 20일 | 200, daily 길이 ≤ 20, 누적 일관 |
| KIS 키 빈 값 | 매크로/종목 양쪽 503 + UI 안내, 다른 섹션 정상 |
| 신규 상장 7일 종목 | 200, daily 길이 7, 예외 X |
| 미존재 종목 999999 | 404 |
| KIS 5xx 시뮬레이션 | 502 |
| 같은 일자 재호출(영속 캐시) | KIS 호출 0회 |
| 장중 11분 후 재호출 | KIS 재호출 1회 |
| 응답에 매매 액션 키 | 없음 (검증) |
| 코스피 → 코스닥 토글 | 새 fetch, 차트 갱신 |
| 슬라이더 20 → 60 | 새 fetch, 차트 갱신 |
