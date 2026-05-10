# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드 + AI자문 기능.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 + AI자문 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)
- **해외주식 지원**: KIS OpenAPI 우선(현재가/일봉/15분봉/호가) + yfinance 폴백(PER/배당/재무) + SEC EDGAR(공시)
- **AI자문**: 기본적 분석(재무제표 3종 + 계량지표) + 기술적 분석(15분봉 + MACD/RSI/Stochastic) + OpenAI GPT-5.4 종합 투자 의견

> KIS API 키는 잔고 조회·주문·미국 시세에 필요. 스크리너/공시/관심종목 기능은 KIS 계정 없이 동작.
> AI자문은 `OPENAI_API_KEY` 필요. 데이터 수집은 키 없이 동작, 리포트 생성 시만 사용.

---

## 상세 스펙 (작업 전 반드시 참조)

| 문서 | 내용 |
|------|------|
| `docs/API_SPEC.md` | 전체 API 엔드포인트 설계 |
| `docs/FRONTEND_SPEC.md` | 프론트엔드 아키텍처/페이지/컴포넌트/라우팅 |
| `docs/KIS_API_REFERENCE.md` | wrapper.py 메서드 + KIS API 참조 |
| `docs/STOCK_PACKAGE.md` | `stock/` 패키지 (관심종목, 시장 데이터, DART, advisory_*) |
| `docs/SCREENER_PACKAGE.md` | `screener/` 패키지 (CLI, KRX, DART 공시, 캐시) |
| `docs/SERVICES.md` | `services/` 서비스 레이어 |
| `docs/CHANGELOG.md` | **모든 변경 이력 (phase 단위 상세 기록 단일 출처)** |
| `docs/kis/` | KIS OpenAPI TR_ID/필드 카테고리별 명세 (00_INDEX 참조) |

> 각 디렉토리(`routers/`, `services/`, `stock/`, `screener/`, `frontend/`)에 **디렉토리별 CLAUDE.md**가 있다. 해당 디렉토리 작업 시 자동 로드된다.

---

## 개발 명령어

```bash
# 백엔드
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload   # http://localhost:8000/docs

# 프론트엔드
cd frontend && npm install && npm run dev              # http://localhost:5173
cd frontend && npm run build                           # dist/ → FastAPI 정적 서빙

# Docker / 배포
docker-compose up --build                              # 로컬 프로덕션
git push origin main                                   # GitHub Actions → ECR → EC2

# 테스트 (PostgreSQL 5433 컨테이너 선행)
docker compose -f docker-compose.test.yml up -d
pytest tests/ -v                                       # unit + integration + api

# CLI
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20
python -m stock watch add 삼성전자 --memo "반도체 대장"
python -m stock watch dashboard --export csv
```

---

## 아키텍처

### 레이어 구성

```
config.py           환경변수 단일 진입점 (os.getenv)
wrapper.py          KIS API 완전 래퍼 (REST + WS, standalone)
main.py             FastAPI 진입점 (라우터 등록 + SPA 정적 + Alembic + lifespan: telemetry/scheduler)
db/                 SQLAlchemy ORM (base, session, utils, models, repositories)
alembic/            DB 스키마 마이그레이션
routers/            API 라우터 (20+, quote/market_board WS 포함)
services/           서비스 레이어 (advisory, watchlist, order, macro, backtest, ai_gateway 등)
screener/           스크리너 패키지 (CLI + API 공용)
stock/              관심종목 패키지 (CLI + API 공용, store 모듈은 db/repositories/ 위임)
frontend/           React SPA
```

**공유 모듈:**
- `services/ai_gateway.py` — 모든 OpenAI 호출 단일 진입점 (쿼터 + 사용량 기록). `AiQuotaExceededError(429)`.
- `services/macro_regime.py` — 공용 체제 판단 (REGIME_MATRIX 20셀 + VIX 오버라이드 + 하이스테리시스). 3개 서비스 공유.
- `services/safety_grade.py` — 7점 등급/복합점수/체제정합성/포지션사이징. advisory + pipeline 공유.
- `db/utils.py` — KST 헬퍼 정의 원본 (`KST`, `now_kst`, `now_kst_iso`).

### 분기 기준
- `stock/utils.py:is_domestic(code)` — 6자리 숫자 → 국내(KRX), 아니면 해외
- `stock/utils.py:is_fno(code)` — FNO 마스터 단축코드 형식 (알파벳+숫자 혼합) 판별

### 예외 계층 (`services/exceptions.py`)
`ServiceError`(400) → `NotFoundError`(404) / `ExternalAPIError`(502) / `ConfigError`(503) / `PaymentRequiredError`(402) / `ConflictError`(409) / `AiQuotaExceededError`(429). `main.py`에서 일괄 HTTP 변환. 서비스/라우터에서 `HTTPException` 직접 raise 금지.

### 보안 헤더
nginx SSoT (2026-05-03 Phase 2b). `infra/nginx/app.conf`. FastAPI 미들웨어로 추가하지 말 것.

---

## 환경변수

`.env`에 설정. SSM Parameter Store `/stock-manager/prod/*` (SecureString)에서 EC2 자동 주입.

**KIS (잔고/주문/미국 시세):** `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACNT_NO`, `KIS_ACNT_PRDT_CD_STK` 필수. `KIS_ACNT_PRDT_CD_FNO`(선물옵션 활성), `KIS_BASE_URL`(기본: 실전 9443; 모의 `openapivts:29443`), `KIS_HTS_ID`(체결통보 WS).

**사용자별 KIS 자격증명:** `KIS_ENCRYPTION_KEY` (AES-GCM 32-byte b64. SSM SecureString. **분실 시 모든 사용자 KIS 자격증명 영구 복구 불가**), `KIS_VALIDATION_TTL_HOURS`(기본 24).

**외부 데이터:** `OPENDART_API_KEY`(국내 공시/재무), `FINNHUB_API_KEY`(미국 실시간 시세, 옵션), `FRED_API_KEY`(매크로 OAS 폴백 권장).

**AI:** `OPENAI_API_KEY`(필수), `OPENAI_MODEL`(기본 `gpt-5.4`).

**백테스트:** `KIS_MCP_URL`(기본 `http://127.0.0.1:3846/mcp`), `KIS_MCP_ENABLED`(기본 false).

**DB/캐시:** `DATABASE_URL`(기본 SQLite, RDS PostgreSQL 전환 가능), `CACHE_PURGE_ON_START`(기본 0; 스키마 변경 배포 시 1).

**런타임 튜닝:** `UVICORN_CONCURRENCY`(기본 20, t3.small 보호), `UVICORN_KEEPALIVE`(기본 5s), `ADVISOR_CACHE_TTL_HOURS`(기본 0.5).

**계측:** `TELEMETRY_ENABLED`(기본 1), `TELEMETRY_FLUSH_SEC`(기본 300).

**테스트:** `TEST_DATABASE_URL`(기본 `postgresql://stocktest:stocktest@localhost:5433/stocktest`), `TEST_KIS_*`(모의계좌).

---

## 데이터 소스

| 소스 | 용도 | 모듈 |
|------|------|------|
| **KIS OpenAPI** | 잔고/주문/현재가/일봉/15분봉/호가 (국내+미국). 키 필요 | `wrapper.py`, `stock/kis_overseas_client.py` |
| **pykrx** | KRX 데이터 (PER/PBR/시가총액/시세) | `screener/krx.py`, `stock/market.py` |
| **OpenDart** | 국내 정기보고서 + 재무제표. `OPENDART_API_KEY` 필요 | `screener/dart.py`, `stock/dart_fin.py` |
| **yfinance** | 미국 PER/EPS/배당/52주/베타/재무 (KIS 미제공 항목) | `stock/yf_client.py` |
| **SEC EDGAR** | 미국 10-K/10-Q 공시 | `stock/sec_filings.py` |
| **OpenAI API** | AI 자문 + 챗봇 (gpt-5.4). 단일 진입점 `ai_gateway` | `services/advisory_service.py` 등 |
| **KIS AI Extensions** | 백테스트 (10 프리셋 + Lean). `KIS_MCP_ENABLED=true` | `services/mcp_client.py`, `services/backtest_service.py` |
| **FRED** | 매크로 (HY/IG OAS, 수익률곡선) | `stock/macro_fetcher.py` |

---

## DB 시스템

### SQLAlchemy ORM (비즈니스 데이터)
단일 `app.db`. `DATABASE_URL`로 PostgreSQL/Oracle 전환. 모델/Repository 전체 목록은 `db/models/` + `db/repositories/` 디렉토리 직접 확인.

핵심 테이블 그룹:
- 관심종목/주문/주문이력 (watchlist, orders+exchange, reservations)
- AI 자문 (advisory_stocks/cache/reports, portfolio_reports, analyst_reports)
- 시장 (market_board_*, stock_info+exchange, macro_gpt_cache, macro_regime_history)
- 보고서/추천 (recommendation_history, daily_reports)
- 세금 (tax_transactions/calculations/fifo_lots)
- 백테스트/전략 (strategies, backtest_jobs+symbols+mcp_job_id)
- 관리자 (ai_usage_log, ai_limits, audit_log, page_view, user_kis)

**규칙:**
- **Adapter 패턴**: `stock/store.py` 등 store 모듈은 Repository 위임 래퍼 (시그니처 100% 유지)
- **Session**: `get_session()` = Store 래퍼 contextmanager / `get_db()` = FastAPI Depends
- **Alembic**: `entrypoint.sh` + `main.py` lifespan에서 `alembic upgrade head` 자동 실행 (alembic 미적용 graceful 처리는 repository 측에서)
- **WAL 모드**: `db/session.py` engine event listener에서 SQLite 자동 설정

### Raw SQLite (캐시)
- `screener_cache.db` — 스크리너 KRX/DART (날짜키, 만료 없음)
- `~/stock-watchlist/cache.db` — 시세/재무/종목코드/수익률 (키별 TTL 상이)
- **NaN 주의**: `cache.py:_sanitize()`가 get/set 양쪽에서 NaN → None 변환
- **WAL + timeout 10s**: `db_base.py`, `cache.py`

---

## Docker / AWS 배포

**Docker 멀티스테이지:** Stage 1 `node:22-slim`(npm build) → Stage 2 `python:3.11-slim`(앱 + dist 복사).
- `docker-compose.yml` (로컬 개발), `docker-compose.test.yml` (PostgreSQL 16 tmpfs 5433), `docker-compose.prod.yml` (app + nginx + certbot), `docker-compose.cloudwatch.yml` (awslogs override, `CLOUDWATCH_LOGS=true` 시 활성)
- `entrypoint.sh`: 환경변수 점검 + 경고 (키 없어도 시작). `CACHE_PURGE_ON_START=1` 시 cache.db 초기화.

**AWS 인프라 (`infra/` Terraform IaC):**
- 컴퓨팅: stock-manager EC2 t3.small (2GB RAM + 4GB swap, swappiness 10) / backtester EC2 t3.micro (Lean Docker 27.5GB + 50GB EBS, MCP 3846 `0.0.0.0`)
- DB: RDS PostgreSQL 16 db.t3.micro (프리티어)
- 이미지: ECR `stock-manager`, GitHub Actions 빌드+푸시
- 시크릿: SSM Parameter Store `/stock-manager/prod/*` SecureString
- CI/CD: `main` push → pytest + frontend build → Docker → ECR → backtester MCP health → EC2 자동 배포 (5m timeout)
- 도메인/HTTPS: `dkstock.cloud` (가비아 DNS → Elastic IP), nginx 리버스 프록시 + Let's Encrypt 자동 갱신
- 로그: CloudWatch Logs `/stock-manager/prod` (retention 14일, 옵션 토글)

**nginx 라우팅:** `infra/nginx/app.conf`
- `^~ /api/backtest/run/` 310s (백테스트 long-running)
- `^~ /ws/` 3600s (WebSocket)
- `/api/` 90s, `/` 60s
- 보안 헤더 6종 + HSTS, gzip 8 MIME, `/assets/*` 1년 immutable

---

## 코드 가이드라인

### 키워드 텍스트 검색은 정규식 (2026-05-10 사용자 결정)

문서/문자열 내 **키워드 기반 검색은 단순 `in`/`find` 대신 정규식(`re.compile`/`RegExp`) 사용**. 띄어쓰기/조사/한자 변형/괄호 변형을 자동 흡수해 미매칭 결함 방지.

**금지 패턴** (단순 string 검사):
```python
KEYWORDS = ["사업의 내용", "II. 사업의 내용"]  # ❌ 변형 못 잡음
if any(k in text for k in KEYWORDS): ...
```

**권장 패턴** (정규식 + `\s*` 변형 흡수):
```python
import re
PATTERNS = [
    re.compile(r"[IⅡ]{1,2}\s*\.?\s*사업의\s*내용"),  # II/Ⅱ + 점/공백 유무 흡수
    re.compile(r"영업의\s*현황"),
]
if any(p.search(text) for p in PATTERNS): ...
```

**근거 사례** (2026-05-10 215000 골프존):
- 단순 `xml.find("II. 사업의 내용")` → 한자 `Ⅱ.` 표기 회사 미매칭 → 매출비중 5년 추이 빠짐
- 정규식 일괄 적용 후 215000 covered 3 → **6년치** 회복

**적용 영역**: DART 사업보고서 헤더/표 키워드(`stock/dart_segments.py`), 보고서 분류(`screener/dart.py`), 감사의견 부정 키워드(`frontend/.../FilingsTable.jsx:_AUDIT_RISK_PATTERN`) 등. 새 키워드 검색 추가 시 동일 원칙.

**JS도 동일** — `String.includes`/`indexOf` 대신 `RegExp.test`/`match`.

---

## 패키지 주의사항

`requirements.txt`: `websockets`, `sqlalchemy`, `alembic`, `pytest`, `psycopg2-binary`, `pyyaml`, `cryptography>=42` (KIS 자격증명 AES-GCM), `pycryptodome>=3.20` (`wrapper.py` 모듈 레벨 `from Crypto.Cipher import AES` — KIS 체결통보 H0STCNI0 복호화. 누락 시 `wrapper.py` import 자체가 ModuleNotFoundError로 실패해 CI/배포 차단), `apscheduler` (매크로 cleanup cron).

---

## 하네스: 계층형 TDD 애자일 투자 자동화

**부서장 → 팀장 → 팀원 계층으로 모든 개발 요청을 자동 라우팅. TDD(RED-GREEN-VERIFY) 사이클로 개발.**

### 기본 라우팅 (필수)

**모든 비-사소 요청은 `department-head` 에이전트를 단일 진입점으로 사용.** 우선순위:
1. **`asset-dev` 스킬 호출** — 표준 진입점. 부서장 오케스트레이션 + 유형 A/B/C/D 자동 분류.
2. **부서장 에이전트 직접 호출** — `Agent(subagent_type="department-head", ...)`. 커스텀 워크플로우/단발성 자문 등.

**메인 직접 처리 가능 예외:**
- 단순 정보 질문, 코드 설명, 문서 조회
- 환경변수·로컬 설정 조회/안내
- 운영 진단(SSM 로그 등) 단발성 read-only
- 사용자가 "직접 진행" 명시한 경우

**금지:** 메인이 부서장 우회로 12명 하위 에이전트(`backend-dev`/`frontend-dev`/도메인 전문가 등)를 직접 호출. 라우팅 책임자는 부서장.

### Commit/Push 정책 (2026-05-10 사용자 결정)

**작업 단위 자동 commit/push 금지.** 사용자가 명시적으로 `/doc-commit`을 호출할 때만 commit + push로 운영 배포 트리거.

- 코드 변경 + 단위 테스트(`pytest tests/unit/`) 실행은 OK
- 단위 테스트 PASS 후 작업 완료 보고 — 사용자가 로컬 docker(`docker-compose up --build`)로 직접 검증
- `git commit` / `git push`는 `/doc-commit` 호출 시에만
- ScheduleWakeup 운영 라이브 검증 예약 금지(push 안 됐으면 운영 변경 없음)
- 운영 진단(SSM 로그 등) read-only는 가능
- 예외: 사용자 명시적 "push해줘" 요청 또는 hotfix 긴급 상황

작업 결과 보고 시 "push는 하지 않았습니다 — `/doc-commit` 호출 부탁드립니다" 명시.

### 모델 라우팅 정책 (2026-05-09)
- **Opus 4.7** — 계획·검증·자문·감사 (department-head/dev-lead/domain-lead/qa-inspector/refactor-engineer + 도메인 전문가 4명)
- **Sonnet** — 일반 구현 (backend-dev/frontend-dev/test-engineer)
- **Haiku** — 명령어 작성 (사용자 정의 에이전트 없음, `/model haiku` 수동)

### 에이전트 12명 (`.claude/agents/`)
- **관리 (3)**: `department-head`(단일 진입점), `domain-lead`, `dev-lead`
- **TDD 개발 (5)**: `test-engineer`(RED), `backend-dev`(GREEN), `frontend-dev`(GREEN), `qa-inspector`(VERIFY), `refactor-engineer`
- **도메인 전문가 (4)**: `macro-sentinel`(체제), `value-screener`(스크리닝), `margin-analyst`(등급/안전마진), `order-advisor`(주문/포지션)

각 에이전트의 상세 책임/프롬프트는 `.claude/agents/<name>.md` 단일 출처.

### 워크플로우
```
asset-dev (부서장)
  ├── 유형 A 기능 개발: 도메인팀장 → 요건서 → 개발팀장 → RED→GREEN→VERIFY → 취합
  ├── 유형 B 리팩토링: 개발팀장 → RefactorEngineer + QA (도메인 자문 시 도메인팀장)
  ├── 유형 C QA 검증: 개발팀장 → QA Inspector (도메인 검증 시 도메인팀장)
  └── 유형 D 소규모 수정: 부서장 직접 처리
```

### 스킬 (`.claude/skills/`)
- `asset-dev` — 코드 변경 수반 모든 요청 (부서장 오케스트레이터)
- `qa-verify` — 교차 비교 검증 (직접 호출용, asset-dev 유형 C로도)
- `refactor-audit` — 감사→자문→실행→QA (직접 호출용, asset-dev 유형 B로도)
- `doc-commit` — 문서 반영(CLAUDE.md+CHANGELOG) + 커밋

---

## 변경 이력

**모든 변경 이력은 [`docs/CHANGELOG.md`](docs/CHANGELOG.md)가 단일 출처.** 새 변경은 `doc-commit` 스킬을 통해 CHANGELOG에 phase 단위 상세 기록(진단/변경/회귀 가드/도메인 자문)으로 추가하고, 본 CLAUDE.md는 cross-cutting 사실(아키텍처/환경변수/하네스 정책)만 반영한다.
