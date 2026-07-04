# 코드 감사 보고서 (백엔드 구조 개선 + 중복 제거) — 재감사 2026-06-20

- 감사 범위: `routers/` + `services/` + `stock/` (프론트 제외)
- 감사자: refactor-engineer (department-head 오케스트레이션)
- 이전 보고서(2026-04-03) 대비: order_service 분할 완료, stock/indicators.py 분리 완료, quote_kis/quote_overseas 분리 완료 → 해당 항목 종결.

## 정량 요약 (재측정)
- 백엔드 .py 합계: ~37,019줄
- 비대 TOP: advisory_service.py **1861** / macro_fetcher.py **1537** / yf_client.py 1432 / tax_service.py 1165 / dart_fin.py 1104 / portfolio_advisor_service.py 944 / quote_kis.py 890 / advisory_fetcher.py 873
- 레이어 위반 (HTTPException in services): **0건** ✓ clean
- 직접 SQL/sqlite3 in services·routers: **0건** ✓ clean
- 정규식 키워드 위반(단순 in/find on 사업/매출/감사): **0건** ✓ clean
- routers → stock.* 직접 import: 다수 (구조 관찰 항목)

## 발견 사항 (우선순위순)

### [HIGH-1] advisory_service.py 비대 (1861줄, 28함수) — 프롬프트/챗 블록 분리
- 문제: 단일 파일에 (a) 데이터 수집 코어(refresh/collect_fundamental/technical/strategy), (b) **프롬프트 문자열 조립 ~994줄**(L779-1772: `_build_macro_section`, `_build_strategy_signal_section`, `_format_cycle_regime_rule`, `_build_system_prompt`, `_format_money`, `_build_consensus_section`, `_build_prompt`, `_fmt`, `_parse_report`), (c) **챗봇 ~87줄**(L1775-end: `_trim_chat_history`, `_validate_chat_messages`, `chat_with_report`) 혼재.
- 영향: 유지보수성. 프롬프트 빌더는 순수 문자열 조립(외부 I/O 없음) → 분리 시 단위 테스트 용이.
- 도메인 자문 필요: **YES** — margin-analyst: 프롬프트 내 consensus/graham/등급 섹션이 safety_grade 도메인 룰과 결합되어 있는지. 단순 이동이라도 보존할 결합 확인.
- 제안: `services/advisory_prompt.py`(프롬프트 빌더 순수함수) + `services/advisory_chat.py`(chat_with_report 등) 분리. advisory_service.py에서 re-export로 기존 import 경로 100% 유지.

### [HIGH-2] macro_fetcher.py 비대 (1537줄, 31함수) — 테마별 분할
- 문제: 5개 테마 혼재 — index/sentiment(VIX/buffett/fear-greed), news/RSS, **credit-spread+FRED-OAS(~470줄: `_compute_oas_stats`/`_classify_oas_sentiment`/`_fetch_fred_oas`/`_fetch_fred_ig_oas`/`fetch_credit_spread`)**, currency/commodity, sector-returns. 전부 순수 fetch 함수.
- 영향: 유지보수성.
- 도메인 자문 필요: **YES** — macro-sentinel: `_classify_oas_sentiment`/`_compute_oas_stats` 임계값·percentile 로직이 macro_regime 공유 체제 판단과 결합되어 있는지. 단순 이동 시 임계값 보존 확인.
- 제안: 보수적으로 credit/OAS 블록만 `stock/macro_credit.py`로 분리 + macro_fetcher.py re-export. news/sentiment 분리는 ROI 낮아 보류.

### [MEDIUM-1] routers → stock.* 직접 import (서비스 우회)
- 문제: earnings/screener/quote/advisory/market_board/search/backtest가 stock.* 직접 import (다수 함수 내부 지연 import).
- 영향: 레이어 일관성. 다수가 얇은 패스스루(검색/심볼맵/CRUD)로 서비스 신설은 오버헤드만 증가.
- 도메인 자문 필요: NO
- 제안: **보류**. 신규 코드 서비스 경유 권장으로만 기록 (ROI 낮음, 일괄 변경은 과잉 추상화).

### [MEDIUM-2] tax_service(1165)/dart_fin(1104)/yf_client(1432) 비대
- 문제: 도메인 응집도 높은 대형 모듈(FIFO 로트/계정명 매핑/yfinance 어댑터).
- 영향: 유지보수성. 단 분할 시 도메인 위험 높음.
- 도메인 자문 필요: YES(분할 시도 시). 이번 사이클 보류, HIGH 2건 우선.
- 제안: 이번 사이클 **보류**.

### [LOW-1] except 587건 — silent pass 정밀 점검
- 문제: 대부분 asyncio.CancelledError/QueueFull 등 의도적. 2026-03 silent pass→logger 전환 정책으로 다수 정리됨.
- 도메인 자문 필요: NO
- 제안: **보류** (개별 정당성 높음, 일괄 변경 위험).

## 도메인 자문 필요 항목 (Phase 4)
1. [HIGH-1] advisory_service 프롬프트/챗 분리 → **margin-analyst**: "프롬프트 빌더(consensus/graham/등급 섹션)를 별도 모듈로 단순 이동해도 안전마진/등급 도메인 로직에 영향 없는가? 보존해야 할 결합이 있는가?"
2. [HIGH-2] macro_fetcher credit/OAS 분리 → **macro-sentinel**: "`_classify_oas_sentiment`/`_compute_oas_stats` 임계값·percentile 로직을 별도 모듈로 이동해도 macro_regime 공유 체제 판단과의 정합성이 유지되는가?"
