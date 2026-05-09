# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드 + AI자문 기능.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 + AI자문 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)
- **해외주식 지원**: yfinance (미국 시세/재무) + SEC EDGAR (미국 공시)
- **AI자문**: 기본적 분석(재무제표 3종 + 계량지표) + 기술적 분석(15분봉 + MACD/RSI/Stochastic) + OpenAI GPT-5.4 종합 투자 의견

> KIS API 키는 잔고 조회에만 필요하다. 스크리너, 공시, 관심종목 기능은 KIS 계정 없이 동작한다.
> AI자문 기능은 `OPENAI_API_KEY`가 필요하다 (데이터 수집은 키 없이 동작, AI 리포트 생성 시만 필요).

---

## 상세 스펙 (작업 전 반드시 참조)

| 문서 | 내용 |
|------|------|
| `docs/API_SPEC.md` | 전체 API 엔드포인트 설계 (screener, earnings, balance, watchlist, detail, advisory) |
| `docs/FRONTEND_SPEC.md` | 프론트엔드 아키텍처, 페이지, 컴포넌트, 라우팅 |
| `docs/KIS_API_REFERENCE.md` | wrapper.py 메서드 + KIS API 참조 |
| `docs/STOCK_PACKAGE.md` | `stock/` 패키지 (관심종목 CLI, 시장 데이터, DART 재무, advisory_store, advisory_fetcher) |
| `docs/SCREENER_PACKAGE.md` | `screener/` 패키지 (스크리너 CLI, KRX, DART 공시, 캐시) |
| `docs/SERVICES.md` | `services/` 서비스 레이어 (watchlist_service, detail_service, advisory_service) |
| `docs/CHANGELOG.md` | 시세 수신 Phase 1~4 개선 이력 + 버그 수정 이력 |

> 각 디렉토리(`routers/`, `services/`, `stock/`, `screener/`, `frontend/`)에 **디렉토리별 CLAUDE.md**가 있다. 해당 디렉토리 작업 시 자동 로드된다.

---

## 개발 명령어

```bash
# ── 백엔드 ───────────────────────────────────────────────────
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI: http://localhost:8000/docs

# ── 프론트엔드 (개발) ─────────────────────────────────────────
cd frontend && npm install
cd frontend && npm run dev          # http://localhost:5173 (Vite 프록시로 백엔드 연결)

# ── 프론트엔드 (빌드) ─────────────────────────────────────────
cd frontend && npm run build        # dist/ 생성 → FastAPI가 정적 파일로 서빙

# ── Docker (로컬 프로덕션) ─────────────────────────────────────
docker-compose up --build           # 멀티스테이지 빌드 후 http://localhost:8000

# ── AWS 배포 ─────────────────────────────────────────────────
cd infra && terraform init && terraform apply  # 인프라 생성 (EC2+RDS+ECR+SSM)
git push origin main                           # GitHub Actions → ECR → EC2 자동 배포

# ── 스크리너 CLI ──────────────────────────────────────────────
python -m screener screen --help
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20
python -m screener screen --per-range 0 15 --roe-min 10 --export csv
python -m screener earnings --date 2025-02-20
python -m screener screen --earnings-today --sort-by PER

# ── 관심종목 CLI ──────────────────────────────────────────────
python -m stock watch add 삼성전자 --memo "반도체 대장"
python -m stock watch list
python -m stock watch dashboard --export csv
python -m stock watch info 005930
python -m stock watch remove 삼성전자

# ── wrapper.py 직접 테스트 ────────────────────────────────────
python test.py                      # 삼성전자 현재가 조회
```

---

## 아키텍처

### 레이어 구성

```
config.py           환경변수 중앙 관리 (os.getenv 단일 진입점, DATABASE_URL 포함)
wrapper.py          KIS API 완전 래퍼 (standalone)
main.py             FastAPI 서버 진입점 (라우터 등록 + SPA 정적 파일 서빙 + Alembic 마이그레이션 + /api/health + lifespan: telemetry periodic flush 등록). 보안 헤더는 nginx SSoT(2026-05-03 Phase 2b).
db/                 SQLAlchemy ORM 패키지 (base, session, utils, models/14개, repositories/9개)
alembic/            DB 스키마 마이그레이션 관리
routers/            API 라우터 패키지 (20개, quote/market_board는 WebSocket 포함, _kis_auth는 사용자별 토큰 캐시 분기, me_kis/admin_users/admin_stats 신규)
services/           서비스 레이어 (watchlist_service, detail_service, order_service, advisory_service, macro_service, macro_cycle, portfolio_advisor_service, quote_kis/quote_overseas, order_kr/order_us/order_fno, macro_regime, safety_grade, schemas/, mcp_client, backtest_service, strategy_builder_service, tax_service, ai_gateway, _telemetry, _dashboard_cache, secure_store, kis_validator)
services/ai_gateway.py  모든 OpenAI API 호출의 단일 진입점 (쿼터 체크 + 사용량 기록 + 호출). AiQuotaExceededError(429).
services/exceptions.py  서비스 레이어 공용 예외 계층 (ServiceError / NotFoundError / ExternalAPIError / ConfigError / PaymentRequiredError / ConflictError)
services/macro_regime.py  공용 체제 판단 (REGIME_MATRIX 20셀 + VIX 오버라이드 + 하이스테리시스). 3개 서비스 공유.
services/safety_grade.py  7점 등급/복합점수/체제정합성/포지션사이징 공유 모듈. advisory_service + pipeline_service 공유.
services/schemas/    Pydantic v2 응답 스키마 (advisory_report_v2.py)
screener/           스크리너 패키지 (CLI + API 공용, pykrx + OpenDart)
stock/              관심종목 패키지 (CLI + API 공용). store 모듈은 db/repositories/ 위임 래퍼
db/utils.py         KST 타임존 헬퍼 정의 원본 (KST, now_kst, now_kst_iso). db/repositories/ 전용
stock/db_base.py    SQLite 캐시 전용 유틸 (connect contextmanager, cache.py 공용). KST 헬퍼는 db/utils.py에서 re-export
frontend/           React SPA (Vite + Tailwind + Recharts)
```

### `wrapper.py` — KIS API 래퍼 (standalone)

`KoreaInvestment`(REST) + `KoreaInvestmentWS`(WebSocket 실시간 스트리밍). `main.py`/`routers/`와 독립적. 상세는 `docs/KIS_API_REFERENCE.md` 참조.

### 국내/해외/FNO 분기 기준

- `stock/utils.py`의 `is_domestic(code)` — 6자리 숫자이면 국내(KRX), 아니면 해외
- `is_fno(code)` — FNO 마스터 단축코드 형식(6자리 숫자가 아니고 알파벳+숫자 혼합) 여부 판별

### 예외 계층

`ServiceError`(400) → `NotFoundError`(404) / `ExternalAPIError`(502) / `ConfigError`(503) / `PaymentRequiredError`(402) / `ConflictError`(409) / `AiQuotaExceededError`(429). `main.py`에서 일괄 HTTP 변환. 모든 서비스/라우터에서 `HTTPException` 직접 raise 금지.

---

## 환경변수

`.env` 파일에 설정. 항목별 필요 기능:

| 변수 | 필수 여부 | 용도 |
|------|----------|------|
| `KIS_APP_KEY` | 잔고 조회 시 필수 | KIS 실계좌 앱 키 |
| `KIS_APP_SECRET` | 잔고 조회 시 필수 | KIS 실계좌 앱 시크릿 |
| `KIS_ACNT_NO` | 잔고 조회 시 필수 | 계좌번호 앞 8자리 |
| `KIS_ACNT_PRDT_CD_STK` | 잔고 조회 시 필수 | 주식 계좌상품코드(뒤 2자리, 예: 01) |
| `KIS_ACNT_PRDT_CD_FNO` | 선택 | 선물옵션 계좌상품코드(뒤 2자리, 예: 03). 미설정 시 선물옵션 잔고·주문 기능 비활성화 |
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |
| `OPENDART_API_KEY` | 국내 공시/재무 조회 시 필수 | https://opendart.fss.or.kr 에서 발급 |
| `OPENAI_API_KEY` | AI자문 리포트 생성 시 필수 | https://platform.openai.com 에서 발급. 미설정 시 `/analyze` → 503. 크레딧 부족 시 402 반환. |
| `OPENAI_MODEL` | 선택 | AI자문 리포트 생성 모델. 기본값: `gpt-5.4`. `max_completion_tokens` 사용 (신규 모델 호환). |
| `FINNHUB_API_KEY` | 선택 | 해외주식 실시간 시세 (Finnhub WS). 미설정 시 yfinance 2초 폴링(15분 지연). |
| `FRED_API_KEY` | 선택 | FRED 공식 JSON API 폴백용. 무료 발급(https://fred.stlouisfed.org/docs/api/api_key.html). 미설정 시 `fredgraph.csv` 익명 다운로드만 — 운영 IP 차단 시 HY/IG OAS partial_failure 발생. 키 설정 시 CSV 실패→JSON API 자동 폴백. |
| `KIS_HTS_ID` | 선택 | KIS HTS ID. 체결통보(H0STCNI0) WS 실시간 수신용. 미설정 시 폴링만 동작. |
| `ADVISOR_CACHE_TTL_HOURS` | 선택 | 포트폴리오 자문 캐시 유효기간 (시간). 기본값: `0.5` (30분). |
| `DATABASE_URL` | 선택 | SQLAlchemy DB URL. 기본값: `sqlite:///~/stock-watchlist/app.db`. PostgreSQL/Oracle 전환 시 변경. |
| `KIS_MCP_URL` | 선택 | KIS AI Extensions MCP 서버 URL. 기본값: `http://127.0.0.1:3846/mcp`. |
| `KIS_MCP_ENABLED` | 선택 | MCP 백테스트 연동 활성화. 기본값: `false`. `true` 설정 시 백테스트 기능 활성화. |
| `CACHE_PURGE_ON_START` | 선택 | 컨테이너 시작 시 cache.db 전체 초기화. 기본값: `0`(보존). 스키마 변경/필드 추가 배포 시에만 `1`로 켜고 다음 배포 때 다시 `0`. |
| `UVICORN_CONCURRENCY` | 선택 | uvicorn `--limit-concurrency`. 기본값: `20` (t3.small worker 보호). 큰 인스턴스에서는 50~100 권장. |
| `UVICORN_KEEPALIVE` | 선택 | uvicorn `--timeout-keep-alive` 초. 기본값: `5`. idle 연결 정리 주기. |
| `TELEMETRY_ENABLED` | 선택 | `services/_telemetry.py` 계측 활성. 기본값: `1`. `0` 설정 시 모든 `@timed`/`record_event`/`observe`가 no-op. |
| `TELEMETRY_FLUSH_SEC` | 선택 | 계측 카운터 주기적 flush 간격(초). 기본값: `300` (5분). lifespan에서 background task로 stdout dump 후 reset. |
| `KIS_ENCRYPTION_KEY` | **사용자별 KIS 기능 사용 시 필수** | 사용자 KIS 자격증명 AES-GCM 암호화 마스터 키. 32-byte b64 인코딩. SSM `/stock-manager/prod/KIS_ENCRYPTION_KEY`(SecureString). 미설정 시 `/api/me/kis` POST/PUT 503. 키 분실 시 저장된 모든 사용자 KIS 자격증명 영구 복구 불가 — 별도 안전 백업 필수. |
| `KIS_VALIDATION_TTL_HOURS` | 선택 | 사용자 KIS 자격증명 유효 검증 TTL. 기본값: `24` (시간). 만료 후 재검증(`/api/me/kis/validate`) 필요. |
| `TEST_DATABASE_URL` | 선택 | 테스트 DB URL. 기본값: `postgresql://stocktest:stocktest@localhost:5433/stocktest` |
| `TEST_KIS_*` | 선택 | 모의계좌용 (`test.py`에서 사용) |

모의투자 BASE_URL: `https://openapivts.koreainvestment.com:29443`

---

## 데이터 소스

| 소스 | 용도 | 모듈 |
|------|------|------|
| **pykrx** | KRX 데이터 (PER/PBR/시가총액/시세) | `screener/krx.py`, `stock/market.py` |
| **OpenDart API** | 국내 정기보고서 + 재무제표. `OPENDART_API_KEY` 필요 | `screener/dart.py`, `stock/dart_fin.py` |
| **yfinance** | 미국 주식 시세/재무 (15분 지연, 최대 4년). 키 불필요 | `stock/yf_client.py` |
| **SEC EDGAR** | 미국 10-K/10-Q 공시. 키 불필요 | `stock/sec_filings.py` |
| **KIS OpenAPI** | 잔고, 현재가, 주문 등. `KIS_APP_KEY`/`KIS_APP_SECRET` 필요 | `wrapper.py`, `routers/balance.py` |
| **OpenAI API** | 종합 투자 의견 (3전략 프레임워크). `OPENAI_API_KEY` 필요 | `services/advisory_service.py` |
| **KIS AI Extensions** | 전략 백테스팅 (10 프리셋 + 80 기술지표, QuantConnect Lean). `KIS_MCP_ENABLED=true` 필요 | `services/mcp_client.py`, `services/backtest_service.py` |

---

## DB 시스템

### SQLAlchemy ORM (비즈니스 데이터)

6개 비즈니스 DB를 단일 `app.db`로 통합. `DATABASE_URL` 환경변수로 PostgreSQL/Oracle 전환 가능.

| 테이블 | 모델 | Repository | 용도 |
|--------|------|-----------|------|
| watchlist, watchlist_order | Watchlist, WatchlistOrder | WatchlistRepository | 관심종목 |
| orders, reservations | Order, Reservation | OrderRepository | 주문/예약 |
| advisory_stocks, advisory_cache, advisory_reports, portfolio_reports | AdvisoryStock/Cache/Report, PortfolioReport | AdvisoryRepository | AI자문 |
| market_board_stocks, market_board_order | MarketBoardStock/Order | MarketBoardRepository | 시세판 |
| stock_info | StockInfo | StockInfoRepository | 종목 영속 캐시 |
| macro_gpt_cache | MacroGptCache | MacroRepository | 매크로 일일 캐시 |
| recommendation_history | RecommendationHistory | ReportRepository | 투자 추천 이력 + 성과 추적 |
| macro_regime_history | MacroRegimeHistory | ReportRepository | 매크로 체제 일일 이력 |
| daily_reports | DailyReport | ReportRepository | 일일 투자 보고서 |
| tax_transactions, tax_calculations, tax_fifo_lots | TaxTransaction, TaxCalculation, TaxFifoLot | TaxRepository | 해외주식 양도세 |
| strategies (builder_state_json 컬럼) | Strategy | BacktestRepository | 전략빌더 저장/CRUD |
| ai_usage_log | AiUsageLog | AdminRepository | AI API 호출 일별 사용량 기록 |
| ai_limits | AiLimit | AdminRepository | AI 일별 호출 한도 설정 (기본+유저별) |
| audit_log | AuditLog | AdminRepository | 관리자 작업 감사 로그 |
| analyst_reports | AnalystReport | AnalystRepository | 증권사 리포트 메타데이터 + PDF 요약 + 목표가 시간축 추이 |

- **Adapter 패턴**: `stock/store.py` 등 7개 파일은 Repository 위임 래퍼 (기존 함수 시그니처 100% 유지)
- **Session**: `get_session()` = Store 래퍼 전용 contextmanager, `get_db()` = FastAPI Depends 전용
- **Alembic**: 스키마 마이그레이션. `entrypoint.sh` + `main.py` lifespan에서 `alembic upgrade head` 실행
- **WAL 모드**: `db/session.py`의 engine event listener에서 자동 설정 (SQLite 사용 시)

### Raw SQLite (캐시)

| 위치 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` (프로젝트 루트) | 스크리너 KRX/DART 캐시 | 만료 없음 (날짜키) |
| `~/stock-watchlist/cache.db` | 시세/재무/종목코드/수익률 캐시 | 키별 상이 |

- **NaN 주의**: `cache.py`의 `_sanitize()`가 get/set 양쪽에서 NaN → None 변환 보장
- **시작 시 초기화**: `entrypoint.sh`에서 `cache.db` 삭제 (구버전 캐시 방지). app.db는 영향 없음
- **WAL 모드**: `db_base.py`와 `cache.py`에서 `PRAGMA journal_mode=WAL` + timeout 10초

---

## Docker

```
Stage 1  node:22-slim    → npm ci + npm run build → /frontend/dist
Stage 2  python:3.11-slim → pip install + 앱 소스 + COPY --from Stage 1
```

- `docker-compose.yml`: 로컬 개발용 (build + watchlist-data 볼륨)
- `docker-compose.test.yml`: 테스트용 PostgreSQL 16 (tmpfs, 포트 5433)
- `docker-compose.prod.yml`: AWS 프로덕션용 (app + nginx + certbot, HTTPS)
- `entrypoint.sh`: 환경변수 점검 + 경고 출력 (키 없어도 서버 시작). `cache.db` 초기화.
- 로컬: `docker-compose up --build` → `http://localhost:8000`
- AWS: `docker-compose -f docker-compose.prod.yml up -d` → `https://dkstock.cloud`
- 개발: `npm run dev` 별도 실행 (Vite 프록시로 백엔드 연결)

## AWS 배포

```
infra/              Terraform IaC (VPC, EC2×2, RDS, ECR, SSM)
infra/nginx/        nginx 리버스 프록시 설정 (app.conf)
.github/workflows/  GitHub Actions CI/CD (ci.yml, deploy.yml)
scripts/            ec2-deploy.sh (수동 배포), init-ssl.sh (Let's Encrypt 초기 발급)
```

- **컴퓨팅 (stock-manager)**: EC2 t3.small (2GB RAM, docker-compose). 2GB swap 자동 설정
- **컴퓨팅 (backtester)**: EC2 t3.micro (Lean 엔진 + MCP 서버). 2GB swap + 50GB EBS. `infra/modules/backtester/`
  - QuantConnect Lean Docker (27.5GB) + MCP(3846, `0.0.0.0` 바인딩)
  - `open-trading-api/backtester` 레포 clone → `/opt/backtester/open-trading-api/`
  - stock-manager → `KIS_MCP_URL=http://<backtester-private-ip>:3846/mcp` 연결
- **DB**: RDS PostgreSQL 16 (db.t3.micro, 프리티어). `DATABASE_URL` 환경변수로 전환
- **이미지**: ECR `stock-manager` 리포. GitHub Actions에서 빌드+푸시
- **시크릿**: SSM Parameter Store `/stock-manager/prod/*` (SecureString). `BACKTESTER_HOST` GitHub Secret
- **CI/CD**: `main` push → pytest + frontend build → Docker 빌드 → ECR → **백테스터 MCP 확인** → EC2 자동 배포 (command_timeout: 5m)
- **도메인/HTTPS**: `dkstock.cloud` (가비아 DNS → Elastic IP). nginx 리버스 프록시 + Let's Encrypt certbot 자동 갱신
- **캐시 DB**: `cache.db`, `screener_cache.db`는 EC2 로컬 Docker 볼륨에 SQLite 유지

---

## 패키지 주의사항

`requirements.txt` 포함: `websockets` (KIS WS), `sqlalchemy` (ORM), `alembic` (마이그레이션), `pytest` (테스트), `psycopg2-binary` (PostgreSQL), `pyyaml` (전략빌더 YAML 변환)

미포함 (별도 설치): `pycryptodome` — `KoreaInvestmentWS` 체결통보 AES 복호화용

---

## 하네스: 계층형 TDD 애자일 투자 자동화

**목표:** 부서장 → 팀장 → 팀원 계층 구조로 모든 개발 요청을 자동 라우팅하고, TDD(RED-GREEN-VERIFY) 사이클로 투자 자동화 시스템을 개발한다.

### 기본 라우팅 (필수)

**모든 비-사소 요청은 `department-head` 에이전트(Opus 4.7)를 단일 진입점으로 사용한다.** 메인 에이전트는 사용자 요청을 받자마자 다음 우선순위로 부서장에 라우팅한다:

1. **`asset-dev` 스킬 호출** — 표준 진입점. 부서장 오케스트레이션 + 유형 A/B/C/D 자동 분류. 코드 변경·리팩토링·QA·도메인 자문이 수반되는 모든 요청.
2. **부서장 에이전트 직접 호출** — `Agent(subagent_type="department-head", ...)`. 스킬을 우회해야 하는 명시적 케이스(커스텀 워크플로우, 단발성 자문 등).

**메인 에이전트가 직접 처리해도 되는 예외(직접 응답 가능):**
- 단순 정보 질문, 코드 설명, 문서 조회
- 환경변수·로컬 설정 조회/안내
- 운영 진단(SSM 로그 조회 등) 같은 단발성 read-only 작업
- 사용자가 명시적으로 "직접 진행", "에이전트 거치지 마" 등 우회 지시한 경우

**금지:**
- 부서장 라우팅 없이 메인이 임의로 12명 하위 에이전트(`backend-dev`/`frontend-dev`/도메인 전문가 등)를 직접 호출하지 말 것 — 부서장이 라우팅 책임자.
- 사용자 요청 분류가 모호할 때 메인이 자체 판단하지 말고 부서장에게 위임.

**모델 라우팅 정책(2026-05-09):**
- 계획·검증·자문·감사 = Opus 4.7 (department-head/dev-lead/domain-lead/qa-inspector/refactor-engineer/도메인 전문가 4명)
- 일반 구현 = Sonnet (backend-dev/frontend-dev/test-engineer)
- 명령어 작성 = Haiku (현재 사용자 정의 에이전트 없음 — `/model haiku` 수동 전환)

### 에이전트 12명 (`.claude/agents/`)

#### 관리 에이전트 (3명) — 부서장 + 팀장

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| **부서장** | `department-head.md` | 단일 진입점. 요청 분석 → 팀장에게 업무 배분 → 결과 취합 |
| **도메인팀장** | `domain-lead.md` | 도메인 전문가 팀 관리. 요건 정의 + 도메인 자문 제공 |
| **개발팀장** | `dev-lead.md` | 개발 팀 관리. TDD 개발 + QA 검증 + 리팩토링 |

#### TDD 개발 에이전트 (5명) — 개발팀장 휘하

| 에이전트 | 파일 | TDD 역할 |
|---------|------|----------|
| TestEngineer | `test-engineer.md` | **RED**: 요건 수용 기준 → pytest 테스트 선행 작성 |
| BackendDev | `backend-dev.md` | **BACKEND GREEN**: FastAPI+SQLAlchemy 백엔드 구현 |
| FrontendDev | `frontend-dev.md` | **FRONTEND**: React+Tailwind 프론트엔드 구현 |
| QA Inspector | `qa-inspector.md` | **VERIFY**: 각 GREEN 직후 경계면 교차 비교 검증 |
| RefactorEngineer | `refactor-engineer.md` | 도메인 인지 리팩토링 |

#### 도메인 전문가 에이전트 (4명) — 도메인팀장 휘하

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| MacroSentinel | `macro-sentinel.md` | 체제 판단 요건 수립 + 임계값 자문 |
| ValueScreener | `value-screener.md` | 스크리닝 요건 수립 + 점수/필터 자문 |
| MarginAnalyst | `margin-analyst.md` | 등급/안전마진 요건 수립 + 공식 자문 |
| OrderAdvisor | `order-advisor.md` | 주문/포지션 요건 수립 + 안전 규칙 자문 |

### 워크플로우 (계층형)

```
사용자 요청 → asset-dev 스킬 (부서장)
  ├── 유형 A (기능 개발):
  │   Phase 1: 부서장 → 도메인팀장 → 도메인전문가 팀 → 요건서
  │   Phase 2: 부서장 → 개발팀장 → TDD 팀 → RED→GREEN→VERIFY
  │   Phase 3: 부서장 → 결과 취합 + 보고
  ├── 유형 B (리팩토링):
  │   부서장 → 개발팀장 → RefactorEngineer + QA (도메인 자문 시 도메인팀장)
  ├── 유형 C (QA 검증):
  │   부서장 → 개발팀장 → QA Inspector (도메인 검증 시 도메인팀장)
  └── 유형 D (소규모 수정):
      부서장 → 직접 처리 (팀 구성 불필요)
```

### 스킬 4개 (`.claude/skills/`)

| 스킬 | 트리거 | 용도 |
|------|--------|------|
| `asset-dev/` | **코드 변경이 수반되는 모든 요청** | 부서장 오케스트레이터: 유형 A/B/C/D 자동 라우팅 |
| `qa-verify/` | "QA", "정합성 검사" (직접 호출용) | 교차 비교 검증 (asset-dev 유형 C로도 접근 가능) |
| `refactor-audit/` | "리팩토링", "코드 감사" (직접 호출용) | 감사→자문→실행→QA (asset-dev 유형 B로도 접근 가능) |
| `doc-commit/` | "커밋", "문서 반영" | 문서 반영(CLAUDE.md+CHANGELOG) + 커밋 |

### 테스트 (`tests/`)

테스트 DB: **PostgreSQL** (프로덕션과 동일 DBMS). `docker-compose.test.yml`로 테스트 컨테이너 기동.

```bash
# 테스트 DB 기동 (최초 1회)
docker compose -f docker-compose.test.yml up -d

# 테스트 실행 (TEST_DATABASE_URL 기본값: localhost:5433)
pytest tests/ -v              # 전체 (단위+통합+API)
pytest tests/unit/ -v         # 단위 테스트만
pytest tests/integration/ -v  # DB 통합 테스트
pytest tests/api/ -v          # API 엔드포인트 테스트
```

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-13 | 초기 구성 | 전체 | - |
| 2026-04-25 | 멀티유저 인증 추가 | 전체 | JWT+역할기반접근 |
| 2026-04-26 | TDD 애자일 재구성 | 에이전트 7개 + asset-dev 스킬 | 도메인 전문가 팀 토론→요건 수립, RED-GREEN-VERIFY TDD 사이클 도입 |
| 2026-04-26 | DevArchitect → BackendDev + FrontendDev 분리 | agents/ + asset-dev 스킬 | 백엔드(FastAPI)/프론트(React) 전문성 분리, API shape 명세 기반 협업 |
| 2026-04-28 | AI자문 v3 전면 통합 | advisory_service, v3 스키마, research_collector, 프론트 | 1프롬프트+1데이터+1보고서. 6대 비판적 분석. 10년 재무+리서치 통합 수집 |
| 2026-04-28 | 테스트 DB PostgreSQL 전환 | conftest.py, ci.yml, docker-compose.test.yml | 프로덕션 동일 DBMS. stock_info BigInteger 버그 발견+수정 |
| 2026-04-26 | 계층형 하네스 재구성 | 부서장+도메인팀장+개발팀장 신규, asset-dev 스킬 | 부서장→팀장→팀원 계층으로 자동 라우팅. 단일 진입점(asset-dev)으로 통합 |
| 2026-04-28 | 도메인+HTTPS 설정 | deploy.yml, docker-compose.prod.yml, nginx, init-ssl.sh | dkstock.cloud 도메인 연결 + Let's Encrypt SSL + nginx 리버스 프록시 |
| 2026-04-29 | AI 게이트웨이 + 사용량 관리 | ai_gateway, admin 라우터/페이지, 6개 서비스 전환 | 모든 OpenAI 호출 단일 진입점. 유저별 일일 한도. Admin 관리 페이지(사용량/한도/감사로그) |
| 2026-04-29 | 섹터 추천 데이터 기반 개선 | macro_fetcher, sector_recommendation_service, pipeline_service | 한국 섹터 ETF 13종 수익률 수집. 실제 가격 데이터를 GPT 프롬프트에 전달. defensive 하드코딩 규칙 제거 |
| 2026-04-29 | PER fallback 직접 계산 | stock/market.py | yfinance forwardPE 부정확 → 시총/TTM순이익 직접 계산 (PBR/ROE fallback과 동일 패턴) |
| 2026-04-29 | 보고서 비admin 접근 수정 | ReportPage.jsx | 일반 유저는 파이프라인 대신 fetchReportByDate로 기존 보고서 조회 |
| 2026-04-30 | 스크리너 KRX 세션 재시도 | screener/krx.py, krx_auth.py | 빈 응답 시 force_relogin() 후 1회 재시도 |
| 2026-04-30 | 관심종목 기등록 표시 | SectorConceptTabs, WatchlistButton | 데일리 추천 페이지에서 기등록 종목 ★ 표시 |
| 2026-04-30 | 메뉴명 변경 | Header, ReportPage | 분석→보고서 → 분석→데일리 추천. 페이지 제목도 동일 변경 |
| 2026-04-30 | Advisory 새로고침 500 수정 | advisory_service.py | user_id 미전달 NameError → 호출 체인에 user_id 파라미터 추가 |
| 2026-04-30 | 섹터히트맵 3Y 추가 | macro_fetcher, SectorHeatmapSection | 3년 히스토리 조회 + 3Y 컬럼 추가. 현재가 컬럼 제거 |
| 2026-04-30 | PER 산출 개선 | stock/market.py | forwardPE 제거 + fallback을 연간 income_stmt 기반으로 변경 + trailingPE 보존 |
| 2026-04-30 | DART 보고서 링크 수정 | stock/dart_fin.py | 3년 배치→연도별 API 호출로 각 연도 고유 rcept_no 보장 |
| 2026-04-30 | 증권사 목표가 팝업 | naver_research, advisory, AnalystReportsModal | 목표주가 클릭→증권사별 목표가+리포트+PDF 링크 모달 |
| 2026-04-30 | HY OAS 하워드 막스 시계추 | macro_fetcher, CreditSpreadSection | FRED OAS 5년 시계열+시계추 게이지(탐욕/정상/공포)+임계선 |
| 2026-04-30 | 코드 품질 개선 | DetailPage, OrderPage, cache.py, order_fno.py | useRef 수정, setTimeout cleanup, 캐시 로깅, hashkey 로깅 |
| 2026-05-01 | 애널리스트 보고서 → AI 자문 통합 | stock/analyst_pdf, db/models/analyst, db/repositories/analyst_repo, alembic, stock/research_collector(6번째 카테고리), services/advisory_service(12번 섹션), 5개 신규 테스트 | PDF 본문(catalyst 2/risk 2/TP 근거/EPS 변경 6항목) gpt-5.4 요약 + 영구 캐시 + analyst_reports 테이블 영속. 컨센서스 통계(중앙값/dispersion/momentum 5단계/consensus_overheated). 체제별 차등 표시(defensive 미표시, cautious 50% 감산). Value Trap 6번째 규칙. |
| 2026-05-01 | AI자문 프롬프트 누락데이터 보강 + 미래지향/역발상 | services/advisory_service, services/schemas/advisory_report_v3, stock/yf_client | 사업개요/사업부문/52주 위치/자본행위 분류(CB/BW/유증/자사주/M&A)/10년 밸류에이션 사이클/경쟁사 비교/배당수익률 6종 추가. 시스템 프롬프트에 catalyst 식별 의무 + 역발상 4대 시그널 + peak-out 검증. 8대 비판적 분석(미래성장동력/역발상관점 추가). Pydantic Optional → backward-compat. |
| 2026-05-01 | AI 입력 데이터 패널 통합 + 증권사 컨센서스 노출 | frontend/src/components/advisory/ResearchDataPanel.jsx | 기본/리서치 2섹션 구분 제거 → 16카테고리 단일 목록. 신규: 증권사 컨센서스(통계 6종+의견분포+모멘텀5단계+과열+6개월 추이+리포트 5건). 계량지표 ROA/주당배당금/시총 추가. 거시지표에 52주 위치 통합. |
| 2026-05-02 | 워치리스트 t3.small OOM 핫픽스 | services/watchlist_service.py | ThreadPool max_workers 10→4. 26종목 × 3종 외부 API 호출이 10병렬로 메모리 폭증→swap thrashing→nginx 499 발생하던 문제 해결. |
| 2026-05-02 | 워치리스트 안정화 추가 개선 4종 | entrypoint.sh, db/repositories/stock_info_repo.py, infra/modules/compute/user_data.sh, CLAUDE.md | (1) cache.db 매재시작 초기화 폐지 → CACHE_PURGE_ON_START=1 옵션화(기본 보존). (2) stock_info TTL 연장: price off 6h→12h, metrics 2h→6h(trading)·12h→24h(off), returns off 6h→12h. (3) uvicorn --limit-concurrency 20 + --timeout-keep-alive 5 적용(ENV 가변). (4) Swap 2GB→4GB + vm.swappiness 60→10 (신규 EC2 user_data 적용). |
| 2026-05-02 | AI 자문 보수성 완화 + 사이클×체제 + 성장주 트랙 | services/growth_grade(신규), services/macro_regime(get_regime_params 16셀), services/safety_grade(C 부분진입), services/advisory_service(cycle 통합·매트릭스·톤 완화), services/portfolio_advisor_service(톤 균형화), schemas/advisory_report_v3(GrowthAuxiliary), 6개 신규/수정 테스트 | defensive "어떤 경우에도 매수 금지" 폐기. cycle×regime 16셀 매트릭스(defensive+회복=single_cap 7%·margin 35%). C 등급 factor 0.25 부분진입. 가치D+성장G-A factor 0.30 우회진입(분할매수+손절 -20%). Graham 임계 cycle 보정(15%/25%/10%). portfolio "매도 우선/전면 보류" 톤 → "조합 권고/한정 허용/3안 균형". 414 PASS / 0 FAIL. 도메인 자문 4명 합의. |
| 2026-05-03 | Phase 1 인프라 P0 (nginx 보안 헤더 drift + proxy_read_timeout 분리) | infra/nginx/app.conf, .github/workflows/deploy.yml, scripts/ec2-deploy.sh | 매 배포마다 deploy.yml heredoc이 nginx 설정을 덮어쓰면서 보안 헤더 6종+HSTS 누락되던 drift 해소. heredoc 70줄 제거 → SCP staging + nginx -t 자동 검증. proxy_read_timeout 86400 단일 적용 → location 분리: `^~ /ws/` 3600s, `/api/` 90s, `/` 60s. 백엔드 hang이 24시간 nginx 워커 점유하던 문제 해소. nginx -s reload 명시 호출(설정 변경 반영). 사전 docker prune(EBS 디스크 보호). |
| 2026-05-03 | Phase 2 Week 1 Quick Win 5건 (워치리스트/macro 성능) | services/watchlist_service.py, services/_dashboard_cache.py(신규), db/repositories/stock_info_repo.py, stock/yf_client.py, routers/watchlist.py, frontend/src/components/watchlist/WatchlistDashboard.jsx, infra/nginx/app.conf, tests/unit/test_*(신규 4) | QW-1 stock_info N+1 제거(`is_stale_from_dict()` + dict 기반 단축, 26종목 SELECT 104→26 -75%). QW-2 macro 7심볼 ThreadPool 병렬(7~14초 → 1~2초). QW-3 partial_failure 메타필드 + logger.warning 승격(외부 API 부분 실패 가시화). QW-4 dashboard 응답 60s 캐시(부분실패 15s, F5 연타 즉시 응답). INF-3 nginx gzip 8 MIME + `/assets/*` 1년 immutable 캐시(JS 1.4MB→386KB -72.5%). 도메인 변경 0건. 후방 호환 100%(`is_stale` 시그니처 보존). 단위 453 PASS / 0 FAIL / 6 skip. |
| 2026-05-03 | Phase 2b 보안 헤더 SSoT 통합 + SPA HEAD 지원 | main.py, tests/api/test_main_misc.py(신규), .github/workflows/deploy.yml | FastAPI 미들웨어 5종 헤더 추가 코드 제거 → nginx single source of truth(infra/nginx/app.conf). 응답 헤더 중복 노출 해소(backend+nginx 양쪽 → nginx 단일). dev/TestClient는 nginx 미통과로 보안 헤더 부재 정상. HSTS는 nginx HTTPS 한정(dev 도메인 락인 위험 없음). SPA catchall `@app.get` → `@app.api_route(methods=["GET","HEAD"])` — uptime 모니터/curl -I 호환(405→200). deploy.yml 사전 docker prune(EBS 가득 참 회피). |
| 2026-05-03 | Phase 3 계측(Telemetry) 도입 | services/_telemetry.py(신규), tests/unit/test_telemetry.py(신규), routers/watchlist.py, services/watchlist_service.py, services/advisory_service.py, services/ai_gateway.py, db/repositories/stock_info_repo.py, stock/yf_client.py, stock/analyst_pdf.py, main.py | 외부 의존성 0(stdlib only). `@timed` 데코레이터 + `record_event` 카운터 + `observe` percentile(p50/p95/p99 deque). 7개 hot path 계측: watchlist.dashboard / _fetch_dashboard_row / stock_info.get·is_stale / ai_gateway.call_openai / advisory 4페이즈 / yf_client._ticker hit·miss / analyst_pdf 캐시. lifespan 5분 주기 stdout dump 후 reset. `TELEMETRY_ENABLED=0/1` + `TELEMETRY_FLUSH_SEC` 제어. 메모리 < 300KB 상한. 1주 누적 측정 후 max_workers 복원/RefreshContext/Single-flight 우선순위 재평가 자료. 본 로직 미터치, 도메인 영향 0. 단위 453 PASS / 0 FAIL / 6 skip. |
| 2026-05-04 | Phase 4 — 관리 영역 확장 + 사용자별 KIS 자격증명 | services/secure_store.py·kis_validator.py(신규), db/models/user_kis.py·page_view.py(신규), db/repositories/user_kis_repo.py·page_view_repo.py(신규), routers/me_kis.py·admin_users.py·admin_stats.py(신규), routers/_kis_auth.py(사용자별 토큰 dict), routers/balance/order/tax/portfolio_advisor(user_id Depends 전파), services/order_service·tax_service(user_id 시그니처), services/auth_deps.py(require_kis 의존성), db/repositories/order_repo·tax_repo·user_repo(user_id 필터·list_users 등), alembic 3건(user_kis/page_view/user_id 컬럼), main.py(page_view 미들웨어), config.py(KIS_ENCRYPTION_KEY/KIS_VALIDATION_TTL_HOURS), requirements.txt(cryptography>=42), 프론트 신규 7(SettingsKisPage·AdminAIPage·AdminUsersPage·AdminPageStatsPage·KisRequiredNotice 등) + 수정 6(Header·App·ProtectedRoute·useAuth·api/admin·api/me 신규) | (1) AI관리 user_id 입력 점검: UI는 정상, 백엔드 사용자 목록 API 부재 → `GET /api/admin/users?q=&limit=&offset=` 신설 + LimitsTab 콤보박스 교체. (2) 관리 페이지 3섹션 분할: `/admin/ai`·`/admin/users`·`/admin/page-stats`. Header "AI관리" → "관리" 드롭다운. (3) 페이지별 이용현황 통계: PageView 모델 + FastAPI 미들웨어(`asyncio.create_task` 비동기 INSERT) + admin_stats 라우터(경로별 호출/평균·p95 latency/유저 수/일별 시계열) + Recharts 차트. (4) 사용자별 KIS 자격증명: AES-GCM 암호화(`secure_store.py`) + 분리 테이블 `UserKisCredentials` + `_kis_auth.py` 사용자별 토큰 캐시 dict + 라우터/서비스 user_id 전파(`Depends(get_current_user)`) + orders/reservations/tax_* 테이블에 user_id 컬럼 추가(NULL 허용) + `POST /api/me/kis` 즉시 검증(`/oauth2/tokenP`) + 마스킹된 GET 응답 + `/api/auth/me`에 `has_kis: bool` + ProtectedRoute `requireKis` 가드 + Header 회색+🔒 메뉴(클릭 시 `/settings/kis`). 시세(quote/market_board) 운영자 키 통합 유지(미터치). 도메인 변경 0건. 신규 단위 14 PASS + 통합/API 24(CI 위탁) = 신규 38 케이스. SSM `/stock-manager/prod/KIS_ENCRYPTION_KEY` SecureString 등록 필수(미설정 시 `/api/me/kis` 503). |
| 2026-05-04 | HY OAS 하워드 막스 시계추 전면 개편 (P0~P3) | stock/macro_fetcher.py, services/macro_service.py·macro_regime.py·macro_cycle.py, frontend/src/components/macro/CreditSpreadSection.jsx, tests/unit/test_macro_fetcher_oas.py·test_macro_regime_credit_integration.py·test_safety_grade_credit_propagation.py·test_macro_cycle_oas_momentum.py(신규), tests/integration/test_credit_spread_api.py(신규) | 사용자 신고 "HY 스프레드 동작 안 함" 근본 원인 4건: (1) 임계값 3.5%/7%는 막스 원전 비정합·역사적 5%ile은 거의 도달 불가 → **백분위 5단계 sentiment**(extreme_greed/greed/normal/fear/extreme_fear) + OAS>10% 절대 안전장치. (2) 5년 baseline 코로나 이후 저금리만 잡힘 → **전 기간(1996-12~) baseline** + `oas_stats{p10..p95,max,mean,median,std}`/`oas_percentile`/`oas_zscore`. (3) macro_regime에 신용 사이클 누락 → **Phase 1 F&G 보정**(p≥90/≤10 한 단계) + **Phase 2 신용 오버라이드**(OAS>10% OR p>95 → extreme_fear+accumulation 강제, 단 버핏 high/extreme이면 selective 완화) + **Phase 3** macro_cycle `_score_credit`에 oas_momentum_6m 가중. (4) 캐시 1h → **24h 일일 영속**(MacroRepository). 보조: IG OAS(`BAMLC0A0CM`)·HY-IG 스프레드 카드(>5%p 정크패닉). 프론트 게이지 0~12% 선형 → 백분위 축 + 절댓값 라벨 병기, ReferenceLine 백분위 임계(p10/p25/p75/p90)에 동적 매핑. 도메인 자문 합의: MacroSentinel ✅ / MarginAnalyst ✅(safety_grade는 cycle 입력 변화를 16셀 매트릭스로 자동 흡수, 회귀 테스트로 검증) / OrderAdvisor ✅(accumulation REGIME_PARAMS=margin20/single_cap5%/cash25%, dual extreme은 selective 4% 완화). API 후방호환: `oas_history`·`percentile` alias 유지. 단위 495 PASS / 0 FAIL / 6 skip(+17 신규). |
| 2026-05-05 | 매크로 음영/섹터 산점도/방문수 + FRED 안정화 + 미국체결 | services/macro_events.py(신규), stock/macro_fetcher.py(_http_get_fred_csv·_fetch_fred_via_api·_compute_sma20_trend_days·_compute_intensity_zscore), services/macro_service.py(_events_for_history), services/order_us.py(NASD/NYSE/AMEX 순회), db/repositories/page_view_repo.py(count_by_user), routers/admin_users.py(visit_count), config.py(FRED_API_KEY), frontend/src/components/macro/{YieldCurve,CreditSpread,SectorHeatmap}Section.jsx + SectorRelativeChart.jsx(신규), frontend/src/pages/{AdminUsersPage,BacktestPage}.jsx, tests/unit·api 신규 5+1보강 | (1) **음영(R2)**: NBER 침체 3건 + S&P -20% 약세장 4건 ReferenceArea 음영, 차트 데이터셋 snap + ifOverflow="hidden" + 인접 라벨 dy stagger + 좁은 음영 라벨 단축. (2) **섹터 산점도(R3)**: x=SMA20 cross 경과일 ±365 / y=1Y z-score ±3, 4분면 음영, 14개 섹터 색상+아이콘. (3) **방문수(R4)**: PageViewRepository.count_by_user 1쿼리(N+1 방지) + admin_users 응답 visit_count. (4) **FRED 안정화(R1)**: Mozilla UA + timeout 25s + Content-Type 검증 + 1회 재시도 + 7일 stale 캐시 + FRED 공식 JSON API 폴백(`FRED_API_KEY`). 핫픽스: 미국 체결내역 NASD 단일 → NASD/NYSE/AMEX 3거래소 순회. 백테스트 가용 기간 가이드(US ≥ 1998-01-02 / KR ≥ 2000-01-04). SSM `/stock-manager/prod/FRED_API_KEY` SecureString 등록(Version 1). 신규 27 케이스 PASS / 회귀 0. |
| 2026-05-05 | UI 후속 — 라벨 충돌 회피 / HYG-LQD 폐기 / 섹터 3Y / 금리차 3단 레이아웃 / 방문수 카운트 fix | frontend/src/components/macro/EventLabelsOverlay.jsx(신규), YieldCurveSection.jsx, CreditSpreadSection.jsx, SectorRelativeChart.jsx, stock/macro_fetcher.py, services/macro_service.py, routers/macro.py, main.py | (1) **EventLabelsOverlay**: `computeEventRows` 시간 도메인 글로벌 row 계산 + `makeLabelRenderer` ReferenceArea label 콜백(viewBox+row×13px dy). 침체/약세장 라벨 충돌 원천 차단(이전 dy stagger의 한계 — 같은 kind 내에서만 stack 가능, 코로나/인플레 인접 라벨 겹침 발생). (2) **HYG/LQD ETF 폐기**: `fetch_credit_spread`에서 yfinance HYG/LQD 호출 + `hyg_yield/lqd_yield/spread/spread_direction/history` 필드 제거(의미 약화). 캐시 v4→v5. 사이클 `credit_direction` = oas_momentum_6m 부호 기반(>0.5 widening / <-0.5 narrowing). (3) **섹터 3Y 버그**: yfinance period `3y → 5y` (거래일 ~755 → ~1260, 3Y/SMA20 둘 다 안전). 캐시 v3→v4. (4) **금리차 3단 레이아웃**: 1행 4금리 카드 → 2행 SpreadCard\|수익률곡선 → 3행 스프레드 추이 풀폭 h-80. (5) **섹터 산점도 동적 스케일**: 고정 ±365/±3 → 데이터 기반 `max(\|값\|) × 1.18`(최소 ±30일/±0.5σ). dot 크기 60→110. (6) **방문수 fix**: BaseHTTPMiddleware ContextVar propagation 문제 해소 — JWT 직접 파싱(`_extract_user_id_from_jwt`)으로 우회. 침체/약세장 시계열 1962~ 전 시계열로 확장(NBER 9건/약세장 9건, GFC→서브프라임 한국화). |
| 2026-05-06 | 자문보고서·포트폴리오 보고서 챗봇 + 상단 AI 사용량 게이지 | services/advisory_service.py(`chat_with_report`), services/portfolio_advisor_service.py(`chat_with_report`), routers/advisory.py(`POST /{code}/chat`), routers/portfolio_advisor.py(`POST /chat`), frontend/src/api/chatbot.js(신규), frontend/src/components/common/{ReportChatBubble,AiUsageGauge}.jsx(신규), frontend/src/hooks/useAiUsage.jsx(신규), frontend/src/components/layout/Header.jsx(게이지 마운트), frontend/src/App.jsx(AiUsageProvider), frontend/src/hooks/{useAdvisory,usePortfolioAdvisor}.js(`ai-usage-changed` dispatch), frontend/src/pages/{DetailPage,PortfolioPage}.jsx(ReportChatBubble 통합), tests/unit·api 신규 4(단위 13 PASS) | 보고서 컨텍스트 stateless 챗봇: 보고서 본문(`advisory_reports.report` / `portfolio_reports.report`)을 system prompt에 주입(가드: 보고서 외 추정·새 의견 금지, 한국어 간결 답변), 슬라이딩 윈도우(최근 20개), `ai_gateway.call_openai_chat(service_name="advisory_chat"\|"portfolio_chat", max_completion_tokens=1500)`. 입력 검증(messages 비어있음/role/4000자·50개 상한/마지막 user 강제). 권한: advisory=user_id+code+market 일치 / portfolio=require_admin. **DB 마이그레이션 0건**(세션 휘발, 메시지 히스토리는 클라이언트 useState만 보관, 페이지 이동·새로고침 시 초기화). UI: 우하단 플로팅 버블(💬 토글, 예시 질문 칩 3개, textarea+Enter 전송, 모바일 풀폭). DetailPage(AI 자문 서브탭에서만 마운트, contextId=`report.id`) + PortfolioPage(contextId=`advisor.result.report_id`). **상단 AI 사용량 게이지**: 기존 `GET /api/admin/ai-usage/me` 재사용(백엔드 신규 0). `<AiUsageGauge />` Header 우측 배치 — 가로 24px 게이지바 + `used/limit` + 80% amber/95% red. `AiUsageProvider` Context로 전역 단일 소스, `'ai-usage-changed'` window 이벤트 자동 갱신(폴링 X). 챗봇·analyze 응답 후(성공/실패 모두) dispatch. 도메인 변경 0건(보고서 재설명 한정). 회귀 0건. |
| 2026-05-06 | 챗봇 권한 검증 버그 수정 + 기본적분석 비즈니스 모델 섹션 | db/repositories/advisory_repo.py(`get_report_by_id(report_id, user_id=None)`), stock/advisory_store.py(시그니처 위임), services/advisory_service.py(`chat_with_report` user_id 검증을 Repo로 위임 + `_collect_fundamental_kr/us`에 business_model 통합), routers/advisory.py(`GET /{code}/reports/{id}` 호출 인자 정상화), stock/advisory_fetcher.py(`fetch_business_model` 신규 + `_BUSINESS_MODEL_SYSTEM_PROMPT` 도메인 가이드 내장 + 캐시 키 `advisor:business_model:{market}:{code}` TTL 7일), frontend/src/components/advisory/FundamentalPanel.jsx(`BusinessModelSection` 신규 3카드), tests/unit·integration 신규 10건+보강 5건(단위 19 PASS) | (1) **챗봇 버그**: `AdvisoryReport.to_dict()`에 `user_id` 누락 → `report_row.get("user_id") != user_id` 검증이 항상 None != user_id로 실패해 본인 보고서임에도 항상 "자문보고서를 찾을 수 없습니다" 응답하던 문제 해소. **DB 레벨 user_id 필터링** 통일(B안) — `AdvisoryRepository.get_report_by_id(report_id, user_id=None)`로 시그니처 확장, user_id 주어지면 `filter_by(id, user_id)`. portfolio 측 `get_portfolio_report_by_id(report_id)` 패턴과 일관. to_dict 응답에 user_id 노출 안 함. **부수 버그**: `routers/advisory.py:237`이 `get_report_by_id(user_id, report_id)`로 인자 2개로 깨진 호출(시그니처 1개) → `get_report_by_id(report_id, user_id=user_id)`로 정상화(GET `/{code}/reports/{id}` TypeError → 정상). (2) **비즈니스 모델 narrative**: 도메인 자문 합의 — MarginAnalyst(OCF/NI≥1.0 전환력, FCF 마진 양수 지속·5%, capex 강도 <30%/30~70%/>70% 분류, 환원율 지속가능성, 운전자본 품질) + ValueScreener(방어형 vs 공격형 R&D, 산업 평균 R&D 비중 반도체 8~15%/제약 15~20%/소비재 1~3%, 자본배분 효율, value trap "R&D↑매출↓" 경계, "공시 한정" 명시). `fetch_business_model(code, name, market, segments_dict, financial_dict, user_id)` GPT 1회(`response_format=json_object`, `max_completion_tokens=1500`, `service_name="advisory_business_model"` 유저 쿼터 차감) → `{revenue_model, cash_generation, rd_strategy}`. 캐시 hit 시 GPT 미호출, 모든 필드 None이면 캐시 안 함(다음 재시도). `refresh_stock_data` 페이즈에서만 호출(매 GET 호출 금지, research_collector 패턴). fundamental dict에 `business_model` Optional 필드 추가(백워드 호환). 프론트 BusinessOverview 직후 `<BusinessModelSection>` — 3카드 그리드(💰 매출 흐름 / 💵 현금 창출 / 🔬 R&D 투자), 모든 필드 빈 값이면 미렌더. DB 마이그레이션 0건. |
| 2026-05-07 | AI 자문 입력데이터 "사업 개요/부문" 페이지 크래시 버그 수정 + ResearchDataPanel 객체 렌더 방어망 | frontend/src/components/advisory/ResearchDataPanel.jsx | `renderSegments` 키 mismatch 해소 — 백엔드(`{segment, revenue_pct, note}`) ↔ 프론트(`s.name`/`s.ratio`) 불일치로 `s.name||s` 폴백이 객체 자체를 React child로 넘겨 "Objects are not valid as a React child" 크래시 발생하던 버그 수정. 키 매핑 `s.segment||s.name||s.product` + `s.revenue_pct ?? s.ratio ?? s.percentage ?? s.pct`. keywords 배열 객체도 안전 처리. `MiniStat`/`Tr` 공용 안전망 `_safeText()` — 객체 value를 `JSON.stringify`로 변환, 향후 16개 카테고리 중 어떤 백엔드 응답이 객체로 와도 페이지 크래시 없이 폴백 표시. 나머지 15 카테고리는 백엔드↔프론트 키 일치 점검 완료. DB/백엔드 변경 0건. 빌드 OK(854 modules). |
| 2026-05-07 | 백테스트 강화 — 4개 KR 단기/추세 전략 프리셋 + 1~10종목 포트폴리오 균등 배분 (자체 일봉 엔진) | services/local_backtest/(신규 패키지: engine/portfolio/metrics/data_loader/presets/strategies × 4 — momentum/volatility_breakout/donchian_swing/long_tail_volatility), services/backtest_service.py(`run_local_backtest`/`list_local_presets` 추가, MCP 함수 미터치), routers/backtest.py(`LocalBacktestBody` + `POST /run/local` + `GET /local/presets` 신규 2건), db/models/backtest.py(`BacktestJob.symbols` JSON nullable 컬럼), db/repositories/backtest_repo.py(create_job symbols 키워드), stock/strategy_store.py(symbols 위임), alembic/versions/e1f2a3b4c5d6_add_backtest_symbols.py, frontend/src/components/backtest/SymbolMultiInput.jsx(신규 1~10 칩 입력), frontend/src/components/backtest/StrategySelector.jsx(4탭 — 빌더/MCP/로컬/커스텀), frontend/src/components/backtest/BacktestResultPanel.jsx(per_symbol_contribution 카드 + symbol 컬럼), frontend/src/pages/BacktestPage.jsx(local-preset 분기 + multiSymbols state + MCP 미연결 차단→안내 배너 완화), frontend/src/api/backtest.js(`runLocalBacktest`/`fetchLocalPresets`), frontend/src/hooks/useBacktest.js(`useLocalPresets`/`runLocal`), tests/unit 신규 5모듈(30건) + tests/api 신규 2모듈(8건 — PostgreSQL CI 위탁) | 사용자 라이브 트레이딩 4개 KR 전략을 일봉 단위로 단순화(트레일링·15:20 청산 생략) → stock-manager 자체 Python 엔진. **VB·long_tail K20 정의**: `K20 = 직전 20일 평균 노이즈 비율 (1 - |Close-Open|/(High-Low))` — 횡보장 K≈1 진입 장벽↑·추세장 K≈0 빠른 추격 (Range=0 도지 평균 제외, 라이브 표준 K=0.5 스케일과 동일 의미). **균등 배분**: `max_slots = min(10, len(symbols))`, 슬롯 가득 시 신규 신호 스킵, 청산 후 자본 회수 → 재배분. **응답**: equity_curve / trades(symbol·entry·exit·pnl_pct·reason) / per_symbol_contribution(종목별 수익률+거래수+기여도) / 8개 메트릭 / failures. **도메인 정합성**: 단기/추세 전용 → 가치주 등급·Value Trap·체제 매트릭스와 직교(safety_grade/macro_regime 미터치). **백워드 호환**: 기존 MCP 백테스트(`run/preset`/`run/custom`/`run/batch`) 100% 미터치, BacktestJob.symbol 유지+symbols JSON 추가, strategy_type "preset"/"custom"+"local". **DB 마이그레이션**: 1건(symbols JSON 컬럼). 단위 30 PASS / 회귀 baseline 648 → 680 (+32). frontend 빌드 OK. 외부 backtester(MCP/Lean) 레포 변경 0건. |
| 2026-05-07 | 자문보고서·포트폴리오 자문 사용자 코멘트 양면 평가 (동의/반박 + strength 1~10) | services/schemas/advisory_report_v3.py(`AgreePoint`/`DisagreePoint`/`UserCommentaryEvaluation` 신규 + `AdvisoryReportV3Schema.user_commentary_evaluation: Optional`), services/advisory_service.py(`generate_ai_report(..., user_comment=None)` + `_build_system_prompt` 가이드 블록 후미 append + `_build_prompt` user 메시지 echo), services/portfolio_advisor_service.py(`_compute_cache_key(balance, user_comment)` SHA256 payload에 코멘트 포함 + `analyze_portfolio(..., user_comment)` + `_build_prompt`/`_build_system_prompt` 가이드 + JSON 스키마 명세), routers/advisory.py(`AnalyzeBody(user_comment: Optional[str])` + `Body(None)` 백워드 호환 + 1000자 ServiceError), routers/portfolio_advisor.py(`AnalyzeBody.user_comment` + 1000자 검증), frontend/src/components/common/UserCommentInput.jsx(신규 textarea+카운터 0/1000+80%/100% 임계 색상), frontend/src/components/advisory/UserCommentaryCard.jsx(신규 stance 5단계 배지+좌(👍 녹색)/우(👎 빨강) 2컬럼+strength 1~10 게이지 막대+모바일 1컬럼 스택), frontend/src/api/{advisory,advisor}.js(generateReport/analyzePortfolio userComment 파라미터), frontend/src/hooks/{useAdvisory,usePortfolioAdvisor}.js(generate/analyze 시그니처 확장), frontend/src/components/{advisory/AIReportPanel,advisor/AdvisorPanel}.jsx(액션바 위 입력 + 본문 최상단 카드 마운트), frontend/src/pages/DetailPage.jsx(userComment state + handleGenerate 전파), tests/unit 신규 4(35건) + tests/api 신규 1(8건, PostgreSQL 의존 CI 위탁) | system prompt 후미 가이드 블록 6개 규칙: ① 동의/반박 양면 의무(악마의 변호인 — 한쪽 압도여도 반대측 1건 이상), ② strength 1~10 임계값(1~3 약한 단서 / 4~6 통상 / 7~8 강한 정량 / 9~10 결정적), ③ overall_stance 5단계(strong_agree=동의 평균≥7&반박<5 / agree=동의>반박 / balanced=±1 이내 / disagree / strong_disagree), ④ summary 1~3문장 직접 답변, ⑤ 본문 8대 분석과 stance 정합성(본문 우선, stance 보정), ⑥ JSON `user_commentary_evaluation` 필드 필수 + 형식 명시. **도메인 정합성**: 등급(A~D)·composite_score·action(적극매수~전량매도)은 코멘트와 무관하게 데이터 기반 유지, stance만 가설 평가 전용. Value Trap 6규칙 불변. **포트폴리오 캐시 키**: 동일 잔고+다른 코멘트=다른 보고서, None/""/" "=같은 키(strip 정규화). **백워드 호환**: 모든 변경 `Optional[str] = None`/`Body(None)`/키워드 기본값, 기존 보고서 조회 시 `user_commentary_evaluation` 누락 → Pydantic 통과. **DB 마이그레이션 0건**(JSON 컬럼 안에 자연 저장). 단위 648 PASS / 0 FAIL / 회귀 0건 + 신규 35건. frontend 빌드 OK(853 modules). 도메인 자문 호출 0건(plan 사전 합의). |
| 2026-05-08 | 시세판/호가창/체결통보 가격 갱신 안 되는 버그 수정 (WS URL stale token) | frontend/src/hooks/useWebSocket.js(url 인자 함수형 추가, connect 안에서 lazy 평가), useMarketBoardWS.js(모듈 const WS_URL → 모듈 함수 buildMarketBoardUrl), useExecutionNotice.js(모듈 함수 buildExecutionNoticeUrl), useQuote.js(useMemo string url → useCallback url 빌더 함수) | 사용자 신고: 시세판 가격 갱신 안 됨. 사용자가 공유한 WS handshake URL의 JWT 디코드 결과 `exp = 2026-05-07 17:20:04 KST`로 이미 만료. 근본 원인은 **WS URL의 stale access_token + 인증 처리 비대칭**: ① 모듈 const `WS_URL = buildWsUrl(...)`이 모듈 로드 시점에 1회만 평가되어 localStorage의 stale token을 즉시 URL에 박음, ② React 마운트 → REST API 401 → `api/client.js:35~46`이 자동 refresh → 새 토큰 저장, ③ 하지만 WS는 이미 stale URL로 시도 → 백엔드 `verify_token` 실패 → 1008 close, ④ `useWebSocket.js:71~80`이 동일 stale URL로 무한 백오프(500ms→10s) 재시도. REST는 401 인터셉터로 자동 갱신되지만 WS 경로엔 동등한 인터셉터가 없는 것이 본질. F5도 모듈 const 평가가 401 refresh보다 빨라 같은 시퀀스 반복. 동일 패턴이 useExecutionNotice/useQuote에도 존재(호가창·체결통보도 토큰 만료 후 회복 불가). **A안 (사용자 승인)**: useWebSocket이 url 인자에 함수형도 받도록 확장 → connect 안에서 `typeof url === 'function' ? url() : url` lazy 평가. 1008 close 후 백오프 재시도 시점에 자동으로 신선한 access_token 반영(자기치유). 호출자 3곳은 모듈 함수 또는 useCallback으로 안정 reference 전달. **백엔드/DB/도메인/nginx 변경 0건**. frontend 빌드 OK(854 modules). 회귀 테스트 0건(클라이언트 단일 버그). |
| 2026-05-08 | KIS API 신 TR_ID 일괄 전환 + KRX+NXT 통합시세 + SOR 활용 (매매화면 풀스택 개선) | 백엔드 8건(services/order_kr 신 TR_ID `TTTC0012U/0011U/0013U/0084R/0081R` + `EXCG_ID_DVSN_CD` + `_validate_ord_dvsn` + `_normalize_excg_code` + 미체결 3거래소 dedup, services/order_service `place_order(exchange="SOR")` + 모의투자 차단 + PENDING/PLACED 거래소 흐름 + 정정·취소 시 DB 거래소 조회, services/quote_kis `_KR_TR_MATRIX(UN/KRX/NXT) + _resolve_exchange_by_clock 4구간 + subscribe_market_status 멀티플렉스(H0UNMKO0+H0STMKO0+H0NXMKO0)`, routers/order `PlaceOrderBody.exchange: Literal["SOR","KRX","NXT"]`, routers/quote `WS /ws/quote/{symbol}?exchange=auto + 신규 WS /ws/market-status`, db/models/order.py·repositories/order_repo.py·stock/order_store.py `exchange varchar(16) nullable` 흐름, alembic/versions/f5a6b7c8d9e0_add_orders_exchange.py), 프론트 9건(hooks/useMarketClock.js 신규 KST 4구간 + WS market-status override, hooks/useQuote.js exchange 3번째 파라미터, hooks/useExecutionNotice.js mapOrdExgGb 헬퍼 + ord_exg_gb 매핑, components/order/ExchangeBadge.jsx 신규 5종 배지, components/order/OrderForm.jsx KR_EXCHANGE_OPTIONS 셀렉터 + 모의투자 차단, components/order/OrderbookPanel.jsx useMarketClock 거래소 라벨 헤더, components/order/{OpenOrders,Executions}Table 거래소 컬럼, pages/OrderPage.jsx 토스트 거래소 prefix), 신규 docs/kis/ 23개 마크다운(338 시트 → 카테고리별 + 00_INDEX) + scripts/kis_excel_to_md.py, 단위/API 신규 5(test_order_repo_exchange/test_order_kr_exchange/test_quote_kis_exchange/test_order_service_exchange/test_order_place_exchange/test_quote_ws_exchange) | KIS 차세대시스템 출범으로 신 TR_ID 체계 일괄 도입(구 TR_ID 사전고지 없이 차단 가능) + NXT(넥스트레이드) 정식 가동(08:00~09:00 / 15:40~20:00) + 09:00~15:30 KRX+NXT 통합시세 + SOR(Smart Order Routing) 시세·주문 양면 노출. 기존 구현은 KRX 단일 + 구 TR_ID(`TTTC0801U/0802U/0803U/8036R/8001R`) + 호가 WS `H0STCNT0/H0STASP0` 고정 → NXT 시간대 호가 표시 불가, SOR 가격개선 0, 신 TR_ID 차단 시 매매 중단 위험. **사용자 결정 4개** (모두 추천 옵션): ① 셀렉터 SOR/KRX/NXT 3개(SOR 기본, 통합 UN은 시세 전용 코드라 주문값 X), ② 신 TR_ID 일괄 전환, ③ 시간대 자동 전환(프론트 KST 시계 4구간 + 백엔드 H0UNMKO0 WS 둘 다, 휴장 자동), ④ DB orders.exchange 컬럼 + 미체결/체결 테이블 거래소 배지 + 토스트 거래소 표기. **거래소 매트릭스**: 09~15:30=UN/H0UNCNT0+H0UNASP0(통합), 15:30~15:40=KRX/H0STCNT0+H0STASP0(KRX 동시호가/마감), 08~09 또는 15:40~20=NXT/H0NXCNT0+H0NXASP0(NXT 시간외). KIS 명세 검증(docs/kis/09_KR_REALTIME.md): NXT/통합 호가도 ASKP1~10+RSQN1~10 동일 10호가 → 기존 `_parse_orderbook()/_parse_execution()` 재사용. **모의투자 차단**: `KIS_BASE_URL.startswith("https://openapivts")` → SOR/NXT 시 ServiceError + UI 비활성화 이중 방어(KIS 명세상 모의투자는 KRX만 가능). **체결통보 ORD_EXG_GB**(1=KRX/2=NXT/3=SOR-KRX/4=SOR-NXT)는 useExecutionNotice 가 enrich, 토스트에 거래소 prefix 표기(`[⚡SOR-KRX] 체결: 삼성전자 매수 10주 @ 71,500원`). **백워드 호환**: 기존 `orders.exchange=NULL` → `to_dict()` 에서 'KRX' 폴백, 기존 데이터 영향 0. **회귀**: 919 passed / 0 failed / 6 skipped (baseline 680 → +239 신규 PASS). frontend 빌드 856 modules OK. **v1 범위 외(v2)**: 신용주문, 예약주문 거래소 셀렉터, 통합증거금, KRX 시간외(H0STOAA0/H0STOUP0). |
| 2026-05-08 | 미국주식 시세 KIS API 1차 대체 (현재가/일봉/15분봉) + stock_info.exchange 영속 매핑 | wrapper.py(`fetch_minute_bar_overesea` HHDFS76950200), stock/kis_overseas_client.py(신규 모듈 — `get_kis_price`/`get_kis_ohlcv_daily`/`get_kis_ohlcv_15min` 3종 게이트웨이 + `_resolve_exchange` NAS→NYS→AMS 순회), db/models/stock_info.py(`exchange: String(8) NULL`), db/repositories/stock_info_repo.py(`get_exchange`/`set_exchange`), alembic/versions/e4f5a6b7c8d9_add_exchange_to_stock_info.py(신규), services/quote_overseas.py(`_fetch_quote_message` 추출 + KIS 우선 + yfinance fallback + `record_event("quote_overseas.fallback_to_yf")`), stock/yf_client.py(`fetch_price_yf`/`fetch_detail_yf`/`fetch_period_returns_yf` 미국 종목에서 KIS 우선 + 가격 필드만 덮어쓰기), stock/advisory_fetcher.py(`fetch_15min_ohlcv_us` KIS 우선 + `_normalize_kis_15min_to_advisory` 통일), 신규 단위 6모듈/51 케이스(test_wrapper_overseas_minute/test_stock_info_repo_exchange/test_kis_overseas_client/test_quote_overseas_kis_first/test_yf_client_kis_first/test_advisory_fetcher_kis_first) | yfinance 의존성(15분 지연·비공식 API·간헐 차단) 축소를 위해 미국주식 **현재가(HHDFS00000300) + 일봉(HHDFS76240000) + 15분봉(HHDFS76950200)** 3종을 KIS OpenAPI 우선으로 전환. **사용자 결정**: ① 범위 = 현재가+일봉+15분봉(확장), ② 거래소 매핑 = `stock_info.exchange` 캐시 + 미스 시 NAS→NYS→AMS 순회 후 영속, ③ Fallback = KIS 실패 시 yfinance 자동, ④ 인증 = 사용자 키 우선 + 운영자 키 폴백(기존 `routers/_kis_auth.get_kis_credentials(user_id)` 재사용). **유지(yfinance)**: PER/PBR/EPS/배당/52주/베타/재무 4종/매크로 ETF — KIS 미제공. **단일 게이트웨이**: wrapper.py 직접 호출은 `stock/kis_overseas_client.py`에서만. 외부 호출 실패 시 None 반환(fallback hook), ConfigError(키 부재)는 그대로 raise. 텔레메트리 카운터 신규(`kis_overseas.{resolve_exchange,get_kis_price,get_kis_ohlcv_daily,get_kis_ohlcv_15min}.{success,fail}` + `quote_overseas.fallback_to_yf`). **회귀 가드**: 함수 시그니처/반환 dict 키 100% 보존(후방호환), DB 무손실(NULLABLE 컬럼만), 도메인 알고리즘(safety_grade/macro_regime) 무영향. 단위 817 PASS / 0 FAIL (베이스라인 766 + 신규 51). 부수 해소: yf_client.py logger 정의 누락 잠재 NameError 수정. |
| 2026-05-08 | 해외매매화면 호가창 + 현재가 상세 + USD/KRW 환율 + 미국 거래시간 | wrapper.py(`fetch_oversea_asking_price` HHDFS76200100 + `fetch_oversea_price_detail` HHDFS76200200 + `KoreaInvestmentWS.subscribe/unsubscribe_overseas_orderbook` HDFSASP0 + `parse_overseas_orderbook` 메시지 파서), stock/kis_overseas_client.py(`get_kis_orderbook`/`get_kis_price_detail` + `_normalize_orderbook_response` 헬퍼), services/quote_overseas.py(`_orderbook_pollers` dict + `_orderbook_poll_loop` 2초 주기 + broadcast `{type:"orderbook", asks, bids, total_*_volume}` 국내와 동일 shape), routers/quote.py(`GET /api/quote/us/{symbol}/orderbook` + `GET /api/quote/us/{symbol}/detail` REST 폴백 엔드포인트 2종, 200/503/504), services/order_us.py(`_fetch_usd_krw_rate` + `get_overseas_buyable` 응답에 `usd_krw_rate`/`deposit_krw`/`buyable_amount_krw` 추가, `macro_fetcher.fetch_currency_quotes` lazy import 재사용), frontend/src/components/order/OrderbookPanel.jsx(US 분기 활성화 — `market !== 'US'` 가드 제거 + `displayAsks = asks.slice(0, asks.length || 10)` 동적 단계 + USD `toFixed(2)` 포맷 + useUsMarketClock 헤더 라벨), frontend/src/hooks/useUsMarketClock.js(신규 ET 시계 4구간 — `pre`/`regular`/`after`/`closed`, `Intl.DateTimeFormat('en-US', {timeZone:'America/New_York'})` DST 자동, 1분 setInterval, 순수 함수 `resolveUsPhaseByClock(now)` export), frontend/src/components/order/OrderForm.jsx(US 매수가능 표시 `$X (₩X) · 환율 ₩1,XXX/USD` + 환율 누락 시 graceful degrade), 신규 단위 6모듈/39 케이스(test_wrapper_overseas_orderbook/test_wrapper_overseas_detail/test_wrapper_overseas_orderbook_ws/test_kis_overseas_orderbook/test_quote_overseas_kis_orderbook/test_order_us_buyable_krw) + API 1모듈/8 케이스(test_quote_us_orderbook_detail) | 이전 phase에서 미국 시세는 KIS로 전환됐지만 `/order` 페이지 해외 매매화면(`market='US'`)은 호가창 미지원("해외주식 호가는 지원되지 않습니다") + 현재가 상세 미표시 + 매수가능금액 USD만 + 미국 거래세션 라벨 부재 등 정보 밀도 부족. KIS 미구현 API 4종(HHDFS76200100 호가/HHDFS76200200 상세/HDFSASP0 WS 호가/USDKRW 매수가능 환산)을 통합해 국내매매화면 수준으로 끌어올림. **사용자 결정 4개**: ① 범위 = 호가창+현재가상세+환율표시+거래시간 모두, ② 호가 소스 = WS(HDFSASP0)+REST(HHDFS76200100) 동시 구현(WS 우선/REST 폴백), ③ 모의투자 정책 = 해외거래 미사용이라 분기 생략(실전 한정), ④ 호가 단계 = 10단계 시도, 응답 부족 시 동적 표시. **현 phase 호가 채널**은 KIS REST 2초 폴링이 1차 운영(WS 인터페이스만 마련, 실제 통합은 후속 phase에서). **응답 필드명**은 KIS 가이드 추정 + `_normalize_orderbook_response`가 None/0/누락 키 안전 처리(graceful) → 실 키 통합 테스트 시 한 줄 매핑 패치로 보정. **회귀 가드**: 국내(KR)/FNO 호가창 무영향(분기 가드 제거만, 그리드 코드 100% 공유), DB 변경 0건, 도메인 알고리즘 무영향, 프론트 useQuote 메시지 shape 100% 일치. 단위 838 PASS / 0 FAIL (베이스라인 817 + 신규 39 + 회귀 0). frontend 빌드 857 modules / 5.27s / 0 error. |
| 2026-05-09 | 해외매매화면 후속 — KIS WS 호가 채널 실제 통합 + 미국 공휴일 휴장 + 실 키 통합 테스트 스크립트 | services/quote_overseas.py(`KISOverseasOrderbookWS` 신규 내부 클래스 — KIS WS HDFSASP0 단일 연결 + 다종목 토픽 구독 + `wrapper.parse_overseas_orderbook` 재사용 + 지수 백오프 재연결 1→2→4→8→16→30s 캡 + WS 메시지 수신 시 해당 종목 REST 폴링 자동 중단/끊김 시 자동 재시작), frontend/src/hooks/useUsMarketClock.js(`US_HOLIDAYS_ET` 2026~2028 30일 + `isUsHoliday` + `resolveUsPhaseByClock` 휴장 분기), tests/integration/test_kis_overseas_live.py(신규 — `pytest.mark.live` + `KIS_LIVE_TEST` 환경변수 가드, HHDFS76200100/76200200/HDFSASP0 응답 필드명 확정용), pytest.ini(`live` 마커 등록), `_workspace/dev/05_live_test_runbook.md`(사용자 실 키 검증 절차 + 응답 필드 보정 가이드) | 이전 phase의 호가 채널은 REST 2초 폴링만 운영. WS 인터페이스(`KoreaInvestmentWS.subscribe_overseas_orderbook`)와 메시지 파서만 마련된 상태였음. 본 phase에서 실제 WS 채널을 OverseasQuoteManager에 연결 → WS 정상 시 WS 우선 / 끊김·실패·KIS 키 부재 시 REST 폴백 자동(graceful, 개발/CI 무영향). 미국 정규 공휴일(NYSE/NASDAQ) 휴장은 `useUsMarketClock`이 주말만 판정하던 한계 해소 — 30일 명단(New Year/MLK/Presidents/Good Friday/Memorial/Juneteenth/Independence/Labor/Thanksgiving/Christmas) 하드코딩. 부분 휴장(Black Friday 13:00 ET 조기마감 등)은 v3 보류. 실 키 통합 테스트 스크립트는 `KIS_LIVE_TEST` 가드로 CI에서 자동 skip → 회귀 0. 사용자가 로컬 실 키 환경에서 1회 실행 후 응답 필드 매핑 보정 가능(런북에 보정 위치 명시). **도메인 자문**: OrderAdvisor — WS 재연결 백오프 30s 캡으로 KIS rate limit 안전 마진 확보, 메시지 파서는 기존 `wrapper.parse_overseas_orderbook` 재사용(offset 가정은 실 키 통합 테스트로 검증). **회귀 가드**: 가격 채널(Finnhub/yfinance/KIS price) 무영향(호가만 신규), KIS 키 부재 환경 graceful → REST 폴링, 평일 거래시간 동작 무영향(휴장 분기만 강화), broadcast shape 5키 100% 보존. 단위 849 PASS / 0 FAIL (베이스라인 838 + 신규 10 + 회귀 0). 통합 3 SKIP(KIS_LIVE_TEST 미설정 의도). frontend 빌드 vite v6.4.1 / 4.64s / 0 error. 신규 텔레메트리 8종(`quote_overseas.kis_orderbook_ws.{start,stop,connect,disconnect,reconnect_attempt,topic_subscribe,topic_unsubscribe,message}`). |
| 2026-05-09 | 백테스트 500 두 갈래 픽스 + 운영 가시성 + KIS yaml SSM 영속화 | services/backtest_service.py(`_classify_local_failure` 분류 헬퍼 + `_classify_backtester_error(error_msg)` 'vps_key_missing'/'data_prep'/None 분류 + `_VPS_KEY_FRIENDLY_MESSAGE` yaml 가이드 + `_DATA_PREP_FRIENDLY_MESSAGE` 종목/날짜 가이드 + save_backtest_job try/except → ServiceError 변환 + `_to_jsonable` 응답 직렬화 안전화), services/local_backtest/data_loader.py(yfinance None 영구 캐시 회피 + 1회 재시도 5s + TTL 10분), services/local_backtest/engine.py(DataFrame index `normalize().tz_localize(None)` 통일 + `_idx_for` silent skip 가시화 + `_to_jsonable` numpy/pd.Timestamp 재귀 변환), db/repositories/backtest_repo.py(symbols 컬럼 부재 OperationalError 자동 graceful — INSERT 페이로드에서 자동 누락 + 재시도), routers/backtest.py(`run_local`/`run_preset`/`run_custom`/`run_batch` 4 핸들러 entry/exit 로그 — preset/symbols/market/dates/user_id + duration_ms/job_id/status), main.py(ServiceError handler에 `error_id=uuid4().hex[:8]` 추가 + `logger.error(f"[{error_id}] ...", exc_info=True)` + lifespan에 alembic_command.current() vs head 비교 + 불일치 시 `logger.error("alembic 미적용: current={}, head={}")` 부팅 알림), infra/modules/backtester/{main.tf,user_data.sh}(EC2 IAM에 `ssm:PutParameter` 권한 추가(kis_devlp_yaml 한정) + user_data.sh가 부팅 시 `aws ssm get-parameter --with-decryption`으로 yaml 자동 다운로드 + chmod 600 + 필수 키 5종 검증(자격증명 본문 미노출) + 미등록 시 WARNING + 수동 fallback), infra/modules/compute/main.tf(`aws_cloudwatch_log_group.main` `/stock-manager/prod` retention 14일 + `aws_iam_role_policy.cloudwatch_logs` CreateLogStream/PutLogEvents/DescribeLogStreams + `log_retention_days` 변수 + outputs 2건), docker-compose.cloudwatch.yml(신규 override — app/nginx awslogs 드라이버, region=ap-northeast-2, stream-prefix 분리), .github/workflows/deploy.yml(`CLOUDWATCH_LOGS=${{ vars.CLOUDWATCH_LOGS }}` env 토글 + SCP 대상에 cloudwatch override 포함 + 배포 분기 `if CLOUDWATCH_LOGS=true → -f docker-compose.cloudwatch.yml 추가`), 신규 단위 6모듈/25 케이스(test_backtest_local_alembic_safe/test_local_backtest_data_loader_cache/test_local_backtest_engine_datetime/test_local_backtest_jsonable/test_backtest_mcp_vps_error/test_backtest_router_logging), `_workspace/dev/06_followup_runbook.md`/`07_kis_yaml_ssm_runbook.md`(CloudWatch + SSM Parameter 운영 절차) | 사용자 운영 보고: (Bug A) MCP 단일 종목 백테스트 시 `오류: MCP 백테스트 실패: 백테스트 실패: 데이터 준비 실패: 'vps'` 메시지 노출. (Bug B) 로컬 포트폴리오 백테스트(2종목 이상) raw HTTP 500, 종목 무관 100% 재현. **진단**: SSM Send-Command로 backtester EC2(`i-05c673384e1093d61`) `~/KIS/config/kis_devlp.yaml` 키 검사 → 필수 5개 키 중 `vps:`만 누락(실제로는 `vts:`로 잘못 작성). KIS MCP 코드 `kis_backtest/providers/kis/auth.py:158` 의 `svr = "vps" if is_paper else "prod"` 가 dict 접근 시 KeyError → `RuntimeError: 데이터 준비 실패: 'vps'` 전파. stock-manager 호출 양식 회귀 아님 — backtester EC2 yaml 휴먼 에러. **즉시 fix**: SSM Send-Command로 `sed -i 's/^vts:/vps:/'` 적용 + MCP 재기동(PID 1411983) → health OK. **재발 방지**: SSM Parameter Store(`/stock-manager/prod/kis_devlp_yaml` SecureString)에 yaml 영속화(Console 등록, Version 1) + EC2 재생성 시 user_data.sh가 자동 다운로드 + 필수 키 검증 시 누락 즉시 WARNING. SSM 본문 1110bytes ↔ EC2 yaml 1110bytes diff MATCHED. **로컬 포트폴리오 raw 500 4 후보 모두 graceful 처리**: 1순위 alembic `BacktestJob.symbols` 컬럼 부재(OperationalError 자동 누락) / 2순위 yfinance None 영구 캐시(조기 return + TTL) / 3순위 datetime 미스매치(normalize) / 4순위 numpy 직렬화(_to_jsonable). **운영 가시성**: ServiceError 본문에 `error_id` + 동일 id 로그 매칭 / 라우터 entry·exit + telemetry `backtest.local.{success,fail.cause}` / CloudWatch logs 통합(`CLOUDWATCH_LOGS=true` 토글 시 awslogs 드라이버 활성). **회귀 가드**: 단위 874 PASS(베이스라인 849 + 신규 25, 회귀 0) / 17 ERROR는 PostgreSQL CI 의존(변경 무관). DB 변경 0 / 프론트 변경 0 / 도메인 알고리즘 무영향. **도메인 자문**: OrderAdvisor — symbols NULL graceful은 데이터 무결성 영향 없음(이력 표시·조회 정상), 'vps' 친화 메시지는 사용자 의사결정 충분(yaml 가이드 + 로컬 백테스트 권고). **인프라 잔여**: terraform apply는 별도 운영자 admin 자격증명 영역(stock_manager_remote는 IAM PutRolePolicy 권한 부재로 자동 실행 불가) — 다음 인프라 변경 사이클에 동기화. CloudWatch GitHub Variables `CLOUDWATCH_LOGS=true` 설정 + Terraform apply 후 활성화. |
| 2026-05-09 | 백테스트 fire-and-poll 패턴 도입 (504 + 이력 결과 보존 동시 해소) | db/models/backtest.py(BacktestJob.mcp_job_id), alembic/versions/a9b8c7d6e5f4_add_mcp_job_id_to_backtest_jobs.py(다중 head merge), db/repositories/backtest_repo.py(set_mcp_job_id/update_job_failed + alembic 미적용 graceful), stock/strategy_store.py(위임 래퍼), services/backtest_service.py(`_submit_mcp_job`/`_fetch_mcp_result_nowait`/`poll_backtest_job`/`_surface_error` + run_preset/custom_backtest 즉시 반환 + run_batch_backtest 동기 흐름 인라인 유지), routers/backtest.py(GET /result/{id} → poll_backtest_job 위임) | 진단(SSM Send-Command + MCP 로그): backtester EC2 정상 가동, yaml 5개 키 OK — 사용자 의문(yaml fix가 모드 잘못 바꿨는지) 해소: `vps`는 KIS 공식 용어 Virtual Paper Session(모의)로 원래 의도. 단일 005930 sma_crossover 1년 백테스트 정상(Lean 27.5초). 실패 케이스는 KIS 모의투자 인증 서버 응답 빈 JSON / SSL EOF / Connection refused / EGW00201 rate limit. **진짜 문제**: 504 발생 시 stock-manager가 동기 대기에서 끊겨 backtester가 백그라운드로 진행해도 결과 회수 안 됨 → 이력에 실패로 마킹. **해결**: POST 즉시 `{job_id, status:"running", mcp_job_id}` 반환 + GET /result/{id}에서 `get_backtest_result_tool(wait=False)` lazy 1회 폴링. 프론트 3초×200회(10분) 폴링 인프라 이미 구현됨(useBacktest.js). 504 자체 소멸 + 어떤 실패도 BacktestJob.result_json.error_message에 보존. **회귀 가드**: get_strategy_signals/run_local_backtest 미터치. alembic 미적용 환경 graceful(컬럼 부재 silent skip). 프론트 0건 변경. 단위 894 PASS(베이스라인 877 + 신규 18 - merge 1, 회귀 0). |
| 2026-05-09 | 백테스트 504 픽스 (nginx `/api/backtest/run/` location 분리) | infra/nginx/app.conf | 운영 dkstock.cloud 백테스트 HTTP 504 지속 발생. 사용자 의문(yaml `vts:`→`vps:` fix가 모드를 잘못 바꿨는지) 해소: `vps`는 KIS 공식 용어 Virtual Paper Session(모의)로 원래 의도대로의 설정 — stock-manager → MCP 호출에 paper/prod 플래그 없고 backtester EC2 yaml에서 자동 판정. **진짜 원인**: 타임아웃 매트릭스 불일치 — `infra/nginx/app.conf:79` `/api/` 90s vs `services/mcp_client.py:52` httpx 300s vs `services/backtest_service.py:175-196` MCP wait 280s. 백테스트 90s 초과 시 nginx가 504로 잘라버림(stock-manager는 still-waiting). 2026-05-03 Phase 1 nginx 분리 시 백테스트 long-running 케이스 누락. **수정**: `^~ /api/backtest/run/` location 신규 추가(`/api/` 위), `proxy_read_timeout 310s` (MCP 280s + httpx 300s 상회). `^~` prefix로 우선 매칭. 다른 `/api/*` 90s 그대로 유지(백엔드 hang nginx 워커 무한 점유 방어 효과 보존). 백테스트 4개 흐름(preset/custom/batch/local) 모두 새 location 매칭. **회귀 가드**: 코드 변경 0건(서비스/라우터/DB/프론트 미터치), 도메인 알고리즘 무영향, KIS_MCP_ENABLED=false 환경 무영향(로컬 백테스트도 동일 prefix 보호). |
| 2026-05-09 | 매크로 GPT 캐시 일일 자정 cleanup + 헤더 sticky | db/repositories/macro_repo.py(`delete_before_today()` 신규 — `MacroGptCache.date_kst < today_kst` 일괄 DELETE, 삭제 건수 반환), stock/macro_store.py(위임 래퍼 `delete_before_today()`), services/scheduler_service.py(`_run_macro_cleanup_job()` + APScheduler `CronTrigger(hour=0, minute=5)` cron job 등록 — replace_existing=True, Asia/Seoul 타임존), tests/integration/test_macro_repo.py(`TestMacroDeleteBeforeToday` 3 케이스 — yesterday+older 삭제 / 빈 테이블 / today 보존), frontend/src/components/layout/Header.jsx(`<header>` 루트 className 에 `sticky top-0 z-40` 추가) | 사용자 보고: 매크로 GPT 캐시 자동 정리 정책 확인 → 함수 `cleanup_old(days=30)` 만 있고 어디서도 호출되지 않아 무한 누적 상태 식별. **사용자 결정 2개**: ① 삭제 대상 = `macro_gpt_cache` 테이블만(cache.db `macro:*` TTL 캐시 미터치 — 1년 스파크라인/5년 OAS 등 장기 시계열 보호), ② 트리거 = APScheduler 자정 KST 00:05 일회(자정 정각 race 회피로 5분 여유). 매크로 정보는 당일치만 유지, 어제 이전 row 자동 삭제. main.py lifespan `setup_scheduler()` 자동 통합 → EC2 재기동 시 다음 KST 00:05에 자동 실행. `GET /api/pipeline/status` 응답 jobs 배열에 `macro_cleanup` 포함. **추가**: 헤더 메뉴바 sticky 적용 — `<header>` 루트 className 에 `sticky top-0 z-40` 추가, 스크롤 시 viewport 상단 고정 유지. 모달/드롭다운(z-50+)이 헤더 위에 표시되어 가림 없음. **회귀 가드**: 도메인 알고리즘 무영향, 기존 `save_today`/`get_today`/`cleanup_old(days=30)`/`delete_today(category)` 100% 보존, cache.db macro:* TTL 캐시 미터치. 단위 877 PASS / 0 FAIL (베이스라인 874 + 신규 통합 3건). 17 ERROR는 PostgreSQL CI 의존(변경 무관). |
