# 리팩토링 완료 보고 (백엔드 구조 개선 + 중복 제거)

- 사이클: 2026-06-20
- 범위: routers/ + services/ + stock/ (프론트 제외)
- 워크플로우: refactor-audit 7단계 (감사 → 도메인 자문 → 계획 → 실행 → QA)

## 요약
- 실행: **1건** (HIGH-1 advisory_service 분할)
- 보류: **4건** (HIGH-2 + MEDIUM-1/2 + LOW-1 — 도메인/ROI 사유)
- 변경 파일: 신규 2 (advisory_prompt.py, advisory_chat.py) + 수정 2 (advisory_service.py, test_advisory_service_chat.py)
- 코드 재배치: advisory_service.py **1861줄 → 800줄** (-1061)

## 실행된 리팩토링

### HIGH-1: advisory_service.py 분할
| 산출 | 내용 | 줄수 |
|------|------|------|
| services/advisory_prompt.py (신규) | 프롬프트 빌더 순수함수 9개 + _REGIME_MARGIN + _CYCLE_REGIME_RULES (verbatim 이동) | 1010 |
| services/advisory_chat.py (신규) | chat_with_report + _trim/_validate + 챗 상수 (verbatim 이동) | 129 |
| services/advisory_service.py | 데이터 수집 코어 + re-export 2블록 | 800 (was 1861) |

- **공개 API 무변경**: 엔드포인트 URL/응답 shape/에러 코드 동일. routers/advisory.py 무수정.
- **re-export로 기존 import 경로 100% 보존**:
  - `advisory_service.{refresh_stock_data, generate_ai_report, chat_with_report}` (routers 모듈속성 접근) 유지
  - `from services.advisory_service import _calc_graham_number` (pipeline_service private import) 유지 — `_calc_graham_number`는 advisory_service에 **잔류**(이동 안 함)
  - `_build_prompt/_build_system_prompt/_parse_report` 등 프롬프트 함수 re-export (identity 검증 통과)
- **도메인 보존 (margin-analyst 자문 준수)**: 7점 등급/손절/grade_factor/VIX>35/Value Trap 문자열 byte-identical 이동. safety_grade.py와의 '3중 일관성 필수' 의도적 중복 — 제거/상수화 안 함.

## 보류된 항목 + 사유
| 항목 | 사유 |
|------|------|
| HIGH-2 macro_fetcher credit 분리 | macro-sentinel: OK_BUT_DEFER. 동작 안전하나 소비처 다수(5 서비스 모듈속성 접근) + _KR_SECTOR_ETFS/oas_history_store 결합 위험. HIGH-1 우선. |
| MEDIUM-1 routers→stock 직접 import | ROI 낮음. 얇은 패스스루에 서비스 신설은 과잉 추상화. |
| MEDIUM-2 tax/dart_fin/yf_client 분할 | 도메인 응집도 높음(FIFO/계정명/yf 어댑터). 별도 사이클. |
| LOW-1 except 587건 | 대부분 의도적(asyncio/Queue). 일괄 변경 위험. |

## QA 검증 결과
- import 정합성: PASS (main + routers.advisory + pipeline_service)
- 순환 의존: PASS (양 import 순서 독립)
- 공개 API 호환: PASS (엔드포인트 surface 무변경)
- re-export identity: PASS (_build_prompt is advisory_prompt._build_prompt 등)
- 도메인 문자열 보존: PASS (7점 등급/손절/VIX>35/grade_factor verbatim)
- 단위 테스트: **1652 passed, 8 skipped** (baseline과 동일). 25 failed = 전부 사전 존재 환경 결함(pdfplumber 미설치 + quote_overseas WS dep). **신규 회귀 0건.**
- 테스트 인프라: test_advisory_service_chat.py 3건 patch 대상 advisory_service→advisory_chat 갱신(로직 이동 반영, 동작 무변경).

## 도메인 전문가 자문 요약
- **margin-analyst** (services/CLAUDE.md + safety_grade.py 코드화 규칙 근거): 프롬프트 빌더 이동 CONDITIONAL_OK. 문자열 리터럴 무수정 + _calc_graham_number 잔류/re-export + safety_grade 의도적 중복 제거 금지. → 준수.
- **macro-sentinel** (stock/CLAUDE.md OAS 임계값 + macro_regime 결합 근거): credit 분리 OK_BUT_DEFER. 임계값 보존 가능하나 결합 위험으로 이번 사이클 보류 권고. → 보류.

## 산출물
- _workspace/refactor/01_audit_report.md
- _workspace/refactor/02_domain_advice.json
- _workspace/refactor/03_plan.md
- _workspace/refactor/04_final_report.md (본 문서)
