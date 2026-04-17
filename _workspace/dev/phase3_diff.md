# Phase 3 — DB 스키마 + Pydantic + UI (Diff 리포트)

**작성**: 2026-04-17 DevArchitect

---

## 파일 변경 요약

| 파일 | 상태 | 비고 |
|------|------|------|
| `db/models/advisory.py` | 수정 | AdvisoryReport +6컬럼, PortfolioReport +3컬럼 (3-1) |
| `alembic/versions/2e051b80939e_*.py` | **신규** | nullable=True ALTER TABLE, batch mode (SQLite+PG 호환) (3-1) |
| `db/repositories/advisory_repo.py` | 수정 | save_report/save_portfolio_report 파라미터 확장 (3-2) |
| `stock/advisory_store.py` | 수정 | Adapter 래퍼 파라미터 전달 (3-2) |
| `services/schemas/__init__.py` | **신규** | 패키지 초기화 (3-3) |
| `services/schemas/advisory_report_v2.py` | **신규** | Pydantic v2 스키마 검증 (3-3) |
| `services/advisory_service.py` | 수정 | generate_ai_report 재시도 로직 + v2 필드 DB 저장 (3-4) |
| `services/portfolio_advisor_service.py` | 수정 | 재시도 로직 + 규칙 F-3 + v2 필드 DB 저장 (3-4) |
| `frontend/src/components/advisory/AIReportPanel.jsx` | 수정 | v2 등급 카드 + Value Trap 배너 (3-5) |
| `frontend/src/components/advisor/AdvisorPanel.jsx` | 수정 | 가중 등급 연계 카드 (3-6) |

---

## 3-1. DB 스키마 확장

### AdvisoryReport 신규 컬럼 (모두 nullable=True)
| 컬럼 | 타입 | 용도 |
|------|------|------|
| `grade` | String | A/B+/B/C/D |
| `grade_score` | Integer | 0~28 |
| `composite_score` | Float | 0~100 |
| `regime_alignment` | Float | 0~100 |
| `schema_version` | String | v1/v2 (기본 v1) |
| `value_trap_warning` | Boolean | false (기본) |

### PortfolioReport 신규 컬럼
| 컬럼 | 타입 | 용도 |
|------|------|------|
| `weighted_grade_avg` | Float | 포트폴리오 가중 평균 등급 |
| `regime` | String | 체제명 (필터용) |
| `schema_version` | String | v1/v2 |

### Alembic 마이그레이션
- `2e051b80939e_add_advisory_grade_fields.py`
- `batch_alter_table` 사용 (SQLite + PostgreSQL 양쪽 호환)
- `alembic upgrade head` 성공 확인

---

## 3-2. Repository + Adapter 확장

- `advisory_repo.py save_report()`: 6개 파라미터 추가 (grade, grade_score, composite_score, regime_alignment, schema_version, value_trap_warning)
- `advisory_repo.py save_portfolio_report()`: 3개 파라미터 추가 (weighted_grade_avg, regime, schema_version)
- `advisory_store.py`: 양쪽 모두 파라미터 전달 래퍼 업데이트
- `to_dict()` / `to_summary_dict()`: 신규 필드 노출

---

## 3-3. Pydantic 응답 검증

- `services/schemas/advisory_report_v2.py` 신규
- `AdvisoryReportV2Schema(BaseModel)`: 종목등급 Literal, 등급점수 ge=0/le=28, 복합점수/체제정합성 ge=0/le=100
- `validate_v2_report()`: (success, schema_obj, error_msg) 반환
- `extract_v2_fields()`: DB 저장용 최소 필드 추출 (Pydantic 검증 무관)
- 검증 테스트: 정상 v2 통과, 등급 누락 실패, 점수 범위 초과 실패

---

## 3-4. 토큰 잘림 + 재시도 로직

### advisory_service.py generate_ai_report()
- `max_completion_tokens`: 8000 → **10000** (기본), 재시도 시 **12000**
- `finish_reason=="length"`: 1차 재시도(12000) → 2차 실패 시 `ExternalAPIError` (저장 거부)
- Pydantic v2 검증 실패: 1회 재시도 (프롬프트 끝에 JSON 정합성 요구 부가)
- 일반 OpenAI 에러: 1회 재시도 (backoff 2초)
- v2 필드 추출 → `save_report()` 확장 파라미터로 DB 저장

### portfolio_advisor_service.py analyze_portfolio()
- 동일 재시도 패턴 적용 (10000 → 12000 → ExternalAPIError)
- `save_portfolio_report()` 확장 파라미터 (weighted_grade_avg, regime, schema_version) 전달

### QA 이월 반영: 규칙 F-3 긴급 리스크
- `_build_system_prompt()` 규칙 F에 3번째 예외 추가:
  - "분식회계", "횡령", "상장폐지", "감사의견 거절/한정", "자본잠식", "회계이상" → immediate + exit 강제

---

## 3-5. 프론트 UI — 개별 리포트 (AIReportPanel.jsx)

### v2 등급 카드 (최상단, hasV2 조건부 렌더)
- `SafetyGradeBadge` 컴포넌트: A(진녹)/B+(연녹)/B(황)/C(주)/D(적) 원형 배지
- `ScoreBar` 컴포넌트: 등급점수(28만점)/복합점수(100만점)/체제정합성(100만점) 게이지 바
- 등급팩터 + recommendation 배지 (ENTER=초록/HOLD=노랑/SKIP=빨강)
- Value Trap 경고 배너 (적색, 근거 리스트)
- **하위 호환**: `report.grade` 부재 또는 `schema_version !== 'v2'` → 카드 숨김, 기존 UI 유지

---

## 3-6. 프론트 UI — 포트폴리오 자문 (AdvisorPanel.jsx)

### 개별 종목 리포트 연계 카드 (diagnosis 위, 조건부 렌더)
- 가중 평균 등급 대형 표시 (2xl font, 색상 분기)
- 등급 분포 미니 막대 그래프 (A/B+/B/C/D/unknown)
- C/D 종목 개수 경고
- 가중 평균 B 미만(< 16) → "신규 편입 전면 보류" 경고
- 체제명 배지
- **하위 호환**: `portfolio_grade_weighted_avg` 부재 시 카드 숨김

---

## 검증 결과

| 항목 | 결과 |
|------|------|
| Alembic upgrade head | 성공 (SQLite) |
| py_compile (13개 파일) | 전체 통과 |
| npm run build | 성공 (779 modules, 1.21s) |
| Pydantic 검증 (3시나리오) | 정상 통과/실패/실패 |
| v1 리포트 graceful | grade 부재 → 카드 숨김 |
| 예외 계층 | ServiceError 하위만 사용 (HTTPException 0건) |

---

## 전체 Phase 1+2+3 변경 파일 총괄

### 신규 파일 (6개)
1. `services/macro_regime.py` — 공용 체제 판단 (Phase 1)
2. `services/safety_grade.py` — 7점등급/복합/정합성/포지션 (Phase 2)
3. `services/schemas/__init__.py` — 패키지 초기화 (Phase 3)
4. `services/schemas/advisory_report_v2.py` — Pydantic 스키마 (Phase 3)
5. `alembic/versions/2e051b80939e_*.py` — 마이그레이션 (Phase 3)
6. `_workspace/dev/phase2_order_advisor_guide.md` — OrderAdvisor 가이드 메모

### 수정 파일 (12개)
1. `services/advisory_service.py` — 전 Phase 핵심 (프롬프트+수집+스키마+재시도+DB저장)
2. `services/portfolio_advisor_service.py` — 전 Phase (52주캐시+리포트연계+가중등급+재시도+규칙F-3)
3. `services/pipeline_service.py` — 공용 모듈 위임 (Phase 1-1, 2-4)
4. `stock/indicators.py` — volume/bb 신호 (Phase 2-1)
5. `stock/advisory_fetcher.py` — valuation_stats (Phase 2-2)
6. `stock/yf_client.py` — quarterly_financials_yf (Phase 2-3)
7. `stock/dart_fin.py` — quarterly_financials (Phase 2-3)
8. `stock/advisory_store.py` — Adapter 파라미터 (Phase 3-2)
9. `db/models/advisory.py` — ORM 컬럼 (Phase 3-1)
10. `db/repositories/advisory_repo.py` — Repository 파라미터 (Phase 3-2)
11. `frontend/src/components/advisory/AIReportPanel.jsx` — 등급 카드 (Phase 3-5)
12. `frontend/src/components/advisor/AdvisorPanel.jsx` — 연계 카드 (Phase 3-6)
