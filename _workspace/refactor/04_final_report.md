# 리팩토링 완료 보고 — 메뉴 간 공유 기능/데이터 공통화

- 사이클: 2026-07-04 ~ 07-05
- 요청: "각 메뉴기능간 공유하는 기능이나 데이터가 있다면 공통화시켜줘. (모듈, 데이터)"
- 워크플로우: refactor-audit (감사 → 도메인 자문 → 계획 → 실행 → QA)
- 이전 사이클(2026-06-20) 산출물은 `archive_20260619_4axis/`에 보존

## 요약

- 리팩토링 항목: **6건 실행** / 3건 보류 (F-7 LOW 미착수, F-8/F-9 도메인·설계 사유 보류)
- 변경 규모: **42개 파일, +676 / −1016줄** (신규 공용 모듈 3개 제외 시 본체 약 −340줄)
- QA: 전체 PASS (기능 퇴행 없음, unit 1704 passed, npm build PASS, API 계약 무변경)
- 커밋: 없음 (사용자 /doc-commit 정책)

## 실행된 리팩토링

| # | 항목 | 신규/변경 | 효과 | 도메인 자문 |
|---|------|----------|------|-----------|
| F-1 | KIS 인증 모듈 레이어 교정 | `services/kis_auth.py` 신설(265줄) + shim 8줄 + 14파일 | 레이어 역방향 import 17개소 해소, 순환 회피용 지연 import 제거 | 불요 (동작 무변경) |
| F-2 | 프론트 공용 포맷터 | `frontend/src/utils/format.js` 신설 + 5컴포넌트 | 포맷터/등락색 17곳 분산 → 단일 출처, 표기 옵션으로 화면별 차이 보존 | 불요 |
| F-3 | KST 타임존 SSoT | 13파일 | 자체 정의 12곳 → `db/utils.KST` 위임 (telemetry는 stdlib-only 의도적 예외) | 불요 |
| F-5 | DART HTTP 공용 클라이언트 | `stock/dart_client.py` 신설(33줄) + 3파일 | 3중 구현 통합 + ConnectionError 재시도 정책을 전 호출부로 승격 | 불요 (전송 레이어만) |
| F-4 | 관심종목 KR 시세 배치화 | `services/watchlist_service.py` + 테스트 | 종목별 개별 조회(N+1) → `fetch_prices_batch` 1회. 시세판과 조회 경로 공유 | **value-screener CAUTION** — 제약 3건 이행 |
| F-6 | VIX 스팟 단일 진입점 | `stock/macro_fetcher.py` `get_vix_spot()` + 3곳 위임 | 3중 조회 통합 + '같은 화면 섹션별 VIX 상이' 결함 해소. TTL 10분 고정 | **macro-sentinel CAUTION** — 제약 4건 이행 |

신규 회귀 테스트 14건 추가 (`test_watchlist_price_prefetch.py` 7 + `test_macro_vix_spot.py` 7).

## 보류 항목 + 사유

| 항목 | 사유 |
|------|------|
| F-7 SEC UA 문자열 3곳 조립 (LOW) | 우선순위 낮음 — 차기 사이클 후보 |
| F-8 ai_ipo_tracker yfinance 직접 호출 (LOW) | 테스트 mock 경계 유지 목적의 의도적 구조 — 현행 유지 |
| F-9 캐시 저장소 2중 구현 (LOW) | screener_cache.db(날짜키·무만료) vs cache.db(TTL)는 데이터 전략이 의도적으로 상이 — 통합 부적합 |
| 의도적 분리 판정 | order_kr/us/fno(TR_ID·파라미터 규격 상이), quote_kis/overseas, useMarketClock/useUsMarketClock, SupplyDemandSection vs Panel(요건 상이) — 변경 금지 확인 |

## 도메인 자문 요약 (02_domain_advice.json)

- **value-screener (F-4)**: 변경 OK, 단 배치 응답 shape 갭 주의 — mktcap 부재(→metrics 소싱), price↔close 키명, 배치 누락 종목의 partial_failure 시맨틱 보존. **감사 전제 정정**: fetch_prices_batch는 2026-06-01 정책으로 캐시 우회 — 이득은 캐시 공유가 아니라 API 호출 수 N→1 감소.
- **macro-sentinel (F-6)**: 3중 조회는 의도적 분리가 아닌 중복 — 통합 승인. 단 TTL은 최단 10분 고정(VIX>35 오버라이드 즉각 반응 보존), PCA용 7년 시계열은 통합 금지, 폴백값 캐시 오염 금지.

## QA 검증 결과 (qa_report.md)

- 기능 퇴행: **없음** / 빌드: PASS / API 호환성: PASS (routers 변경은 shim 1파일뿐)
- unit: 1704 passed (실패 25건은 pytest-asyncio·pdfplumber 미설치 환경성 — baseline 동일)
- 자문 제약 이행: F-4 3건 / F-6 4건 전부 코드 확인
- MINOR 참고: 공용 formatPct는 null 입력 시 '-' 표시 (기존 일부 로컬 포맷터의 '0.00%' 오인 표시 개선 — 퇴행 아님)
- 비고: qa-inspector 에이전트 2회 무응답으로 오케스트레이터가 직접 검증 수행

## 후속

- 커밋/배포: 사용자 `/doc-commit` 호출 시 문서 반영 + 커밋
- 차기 후보: F-7 (SEC UA 조립 공용화)
