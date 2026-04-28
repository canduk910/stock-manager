# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

한국투자증권(KIS) OpenAPI를 연동한 주식 계좌 관리 FastAPI 서버 + 웹 기반 주식 스크리너/관심종목 대시보드 + AI자문 기능.

- **백엔드**: FastAPI. 종목 스크리닝 + 공시 조회 + 잔고 조회 + 관심종목 + 종목 상세 분석 + AI자문 API
- **프론트엔드**: React 19 + Vite + Tailwind CSS v4 + Recharts SPA
- **CLI**: `python -m screener` (종목 스크리너) + `python -m stock watch` (관심종목 관리)
- **해외주식 지원**: yfinance (미국 시세/재무) + SEC EDGAR (미국 공시)
- **AI자문**: 기본적 분석(재무제표 3종 + 계량지표) + 기술적 분석(15분봉 + MACD/RSI/Stochastic) + OpenAI GPT-4o 종합 투자 의견

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
main.py             FastAPI 서버 진입점 (라우터 등록 + SPA 정적 파일 서빙 + Alembic 마이그레이션 + /api/health + 보안 헤더 미들웨어)
db/                 SQLAlchemy ORM 패키지 (base, session, utils, models/13개, repositories/8개)
alembic/            DB 스키마 마이그레이션 관리
routers/            API 라우터 패키지 (16개, quote/market_board는 WebSocket 포함)
services/           서비스 레이어 (watchlist_service, detail_service, order_service, advisory_service, macro_service, macro_cycle, portfolio_advisor_service, quote_kis/quote_overseas, order_kr/order_us/order_fno, macro_regime, safety_grade, schemas/, mcp_client, backtest_service, strategy_builder_service, tax_service)
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

`ServiceError`(400) → `NotFoundError`(404) / `ExternalAPIError`(502) / `ConfigError`(503) / `PaymentRequiredError`(402) / `ConflictError`(409). `main.py`에서 일괄 HTTP 변환. 모든 서비스/라우터에서 `HTTPException` 직접 raise 금지.

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
| `OPENAI_MODEL` | 선택 | AI자문 리포트 생성 모델. 기본값: `gpt-4o`. `max_completion_tokens` 사용 (신규 모델 호환). |
| `FINNHUB_API_KEY` | 선택 | 해외주식 실시간 시세 (Finnhub WS). 미설정 시 yfinance 2초 폴링(15분 지연). |
| `KIS_HTS_ID` | 선택 | KIS HTS ID. 체결통보(H0STCNI0) WS 실시간 수신용. 미설정 시 폴링만 동작. |
| `ADVISOR_CACHE_TTL_HOURS` | 선택 | 포트폴리오 자문 캐시 유효기간 (시간). 기본값: `0.5` (30분). |
| `DATABASE_URL` | 선택 | SQLAlchemy DB URL. 기본값: `sqlite:///~/stock-watchlist/app.db`. PostgreSQL/Oracle 전환 시 변경. |
| `KIS_MCP_URL` | 선택 | KIS AI Extensions MCP 서버 URL. 기본값: `http://127.0.0.1:3846/mcp`. |
| `KIS_MCP_ENABLED` | 선택 | MCP 백테스트 연동 활성화. 기본값: `false`. `true` 설정 시 백테스트 기능 활성화. |
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
- **CI/CD**: `main` push → pytest + frontend build → Docker ���드 → ECR → **백테스터 MCP ��인** → EC2 자동 배포 (command_timeout: 5m)
- **도메인/HTTPS**: `dkstock.cloud` (가비아 DNS → Elastic IP). nginx 리버스 프록시 + Let's Encrypt certbot 자동 갱신
- **캐시 DB**: `cache.db`, `screener_cache.db`는 EC2 로컬 Docker 볼륨에 SQLite 유지

---

## 패키지 주의사항

`requirements.txt` 포함: `websockets` (KIS WS), `sqlalchemy` (ORM), `alembic` (마이그레이션), `pytest` (테스트), `psycopg2-binary` (PostgreSQL), `pyyaml` (전략빌더 YAML 변환)

미포함 (별도 설치): `pycryptodome` — `KoreaInvestmentWS` 체결통보 AES 복호화용

---

## 하네스: 계층형 TDD 애자일 투자 자동화

**목표:** 부서장 → 팀장 → 팀원 계층 구조로 모든 개발 요청을 자동 라우팅하고, TDD(RED-GREEN-VERIFY) 사이클로 투자 자동화 시스템을 개발한다.

**트리거:** 코드 변경이 수반되는 모든 요청(기능 개발, 리팩토링, QA, 구조 개선 등) 시 반드시 `asset-dev` 스킬을 사용하라. 단순 질문, 설명 요청, 환경설정만 직접 응답 가능.

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
| 2026-04-28 | 테스트 DB PostgreSQL 전환 | conftest.py, ci.yml, docker-compose.test.yml | 프��덕션 동일 DBMS. stock_info BigInteger 버그 발견+수정 |
| 2026-04-26 | 계층형 하네스 재구성 | 부서장+도메인팀장+개발팀장 신규, asset-dev 스킬 | 부서장→팀장→팀원 계층으로 자동 라우팅. 단일 진입점(asset-dev)으로 통합 |
| 2026-04-28 | 도메인+HTTPS 설정 | deploy.yml, docker-compose.prod.yml, nginx, init-ssl.sh | dkstock.cloud 도메인 연결 + Let's Encrypt SSL + nginx 리버스 프록시 |
