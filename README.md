# Stock Manager

한국투자증권(KIS) OpenAPI 연동 주식 계좌 관리 서버 + 웹 기반 종목 스크리너/관심종목 대시보드 + AI자문 기능.

KIS 계정 없이도 종목 스크리닝과 공시 조회, 관심종목, AI자문 기능을 사용할 수 있습니다.

---

## 주요 기능

### 웹 대시보드
브라우저에서 `http://localhost:8000` 접속

| 메뉴 | 기능 |
|------|------|
| **시세판** | 당일 신고가/신저가 Top10 (시총 기준, 컴팩트 카드 그리드). 관심종목 자동 표시(★) + 별도 추가 종목(DB 영속화, 최대 30개). 1년 주봉 미니 스파크라인 차트. 실시간 시세(WebSocket). |
| **관심종목** | 종목 자동완성 검색 추가. 시세·재무 대시보드. 종목 상세(재무 10년/4년·밸류에이션·종합 리포트). |
| **분석** ▼ | 매크로 분석 / 종목 스크리너(52주 하락률 필터 포함) / 공시 조회 |
| **포트폴리오** | 잔고 요약 + AI 자문(역발상 매수 전략 포함) + 자산배분 차트 |
| **매매** ▼ | 주문(국내/해외/FNO, 실시간 호가창) / 잔고 조회 / 양도세(FIFO 자동 계산+시뮬레이션) |
| **백테스트** | KIS AI Extensions MCP 연동. 10개 프리셋 전략 + 커스텀 YAML. 수익률/샤프/MDD/승률 분석 |
| **보고서** | 일일 투자 보고서 / 추천 이력 / 성과 통계 |

### AI자문 (DetailPage 종합리포트 탭)
- **기본적 분석**: 재무제표 3종 (손익·대차·현금흐름) + 계량지표 (PER·PBR·ROE·ROA·PSR·EV/EBITDA)
- **기술적 분석**: 타임프레임 선택 (15분/60분/1일/1주) + 캔들차트·볼린저밴드·MACD·RSI·Stochastic
- **AI 리포트**: OpenAI GPT-4o 종합투자의견 (매수/중립/매도) + 기술적 시그널 + 리스크·투자포인트
- **리포트 히스토리**: 생성할 때마다 DB에 누적 보관. 2개 이상이면 날짜 드롭다운으로 과거 평가 비교 가능
- `OPENAI_API_KEY` 없어도 데이터 수집·조회 가능. AI 리포트 생성 시만 필요.

### CLI 스크리너
KIS 계정 없이 터미널에서 바로 사용 가능

```bash
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20
python -m screener screen --per-range 0 15 --roe-min 10 --export csv
python -m screener earnings --date 2025-02-20
```

---

## 설치

### 요구사항
- Python 3.11+
- Node.js 18+ (프론트엔드 빌드 시)

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 환경변수 설정

`.env.example`을 복사해 `.env`를 만들고 값을 채웁니다.

```bash
cp .env.example .env
```

| 변수 | 필수 여부 | 설명 |
|------|----------|------|
| `KIS_APP_KEY` | 잔고·주문 조회 시 필수 | KIS 실계좌 앱 키 |
| `KIS_APP_SECRET` | 잔고·주문 조회 시 필수 | KIS 실계좌 앱 시크릿 |
| `KIS_ACNT_NO` | 잔고·주문 조회 시 필수 | 계좌번호 앞 8자리 |
| `KIS_ACNT_PRDT_CD_STK` | 잔고·주문 조회 시 필수 | 주식 계좌상품코드(뒤 2자리, 예: `01`) |
| `KIS_ACNT_PRDT_CD_FNO` | 선택 | 선물옵션 계좌상품코드(뒤 2자리, 예: `03`). 미설정 시 선물옵션 잔고 미조회 |
| `OPENDART_API_KEY` | 국내 공시·재무 조회 시 필수 | [OpenDART](https://opendart.fss.or.kr) 에서 발급 |
| `OPENAI_API_KEY` | AI자문 리포트 생성 시 필수 | [OpenAI Platform](https://platform.openai.com) 에서 발급 |
| `OPENAI_MODEL` | 선택 | 기본값: `gpt-4o`. `gpt-4o-mini`, `o3-mini` 등 지원 |
| `FINNHUB_API_KEY` | 선택 | 해외주식 실시간 시세. [Finnhub](https://finnhub.io) 무료 플랜. 미설정 시 yfinance 2초 폴링(15분 지연) |
| `KIS_HTS_ID` | 선택 | KIS HTS ID. 체결통보 실시간 수신용. 미설정 시 REST 폴링만 동작 |
| `KIS_MCP_ENABLED` | 선택 | MCP 백테스트 연동 활성화. 기본값: `false`. [open-trading-api](https://github.com/koreainvestment/open-trading-api) MCP 서버 필요 |
| `KIS_MCP_URL` | 선택 | MCP 서버 URL. 기본값: `http://127.0.0.1:3846/mcp`. Docker 내부: `http://host.docker.internal:3846/mcp` |
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |
| `DATABASE_URL` | 선택 | DB URL. 기본값: `sqlite:///~/stock-watchlist/app.db`. PostgreSQL/Oracle 전환 시 변경 |

> 스크리너·공시는 `OPENDART_API_KEY`만 있으면 됩니다. KIS 계정 없이 사용 가능합니다.

---

## 실행 방법

### 방법 1 — 백엔드만 (API 서버)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API 문서: `http://localhost:8000/docs`

### 방법 2 — 풀스택 개발 모드 (프론트 + 백엔드)

터미널 두 개를 열어 각각 실행합니다.

```bash
# 터미널 1 — 백엔드
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2 — 프론트엔드 개발 서버 (Vite, 핫리로드)
cd frontend && npm install && npm run dev
```

프론트엔드: `http://localhost:5173` (Vite가 `/api` 요청을 백엔드로 자동 프록시)

### 방법 3 — 프론트엔드 빌드 후 통합 서버

프론트엔드를 빌드하면 백엔드 서버 하나에서 UI + API를 모두 서빙합니다.

```bash
cd frontend && npm run build
cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 방법 4 — Docker (프로덕션)

```bash
docker-compose up --build
```

멀티스테이지 빌드(Node.js → Python) 후 `http://localhost:8000` 에서 접속합니다.

> **개발 시**: Docker 볼륨 마운트가 `frontend/dist/`를 가리므로 개발 중에는 방법 2를 권장합니다.

---

## 사용법

### 종목 스크리너 (웹)

1. 사이드바에서 **종목 스크리너** 클릭
2. 필터 설정:
   - **시장**: 전체 / KOSPI / KOSDAQ
   - **PER 범위**, **PBR 최대**, **ROE 최소** 입력
   - **정렬 기준**: PER·PBR·ROE·시가총액 등, 오름/내림차순
   - **상위 N개**: 결과 수 제한
3. **조회하기** 버튼 클릭
4. 결과 테이블: 순위·종목코드·종목명·시장·**전일종가·현재가·당일%·3개월%·6개월%·1년%·배당수익률**·PER·PBR·ROE·시가총액
5. 각 행 첫 번째 셀의 **`+ 관심`** 버튼으로 관심종목 즉시 추가

> 첫 조회는 전종목 데이터를 수집하므로 수십 초가 걸릴 수 있습니다. 이후 동일 날짜는 캐시에서 즉시 반환됩니다.

### 종목 스크리너 (CLI)

```bash
# KOSPI 종목을 ROE 내림차순, PER 오름차순으로 정렬해 상위 20개
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20

# PER 0~15, ROE 10% 이상 필터 후 CSV 저장
python -m screener screen --per-range 0 15 --roe-min 10 --export csv

# 오늘 실적발표 종목만 PER 낮은 순
python -m screener screen --earnings-today --sort-by PER

# 모든 옵션 보기
python -m screener screen --help
```

### 공시 조회 (웹)

1. **공시 조회** 클릭 → 국내(DART) / 미국(SEC EDGAR) 탭 선택
2. 날짜 범위 선택 후 **조회** 클릭
3. 보고서명 클릭 → DART/SEC 원문이 새 탭으로 열림
4. 각 행의 `+ 관심종목` 버튼으로 관심종목 추가

### 잔고 조회 (웹)

KIS API 키가 `.env`에 설정되어 있어야 합니다.

1. **잔고 조회** 클릭
2. 총평가금액·예수금·주식평가금액 카드 확인
3. 국내주식 / 해외주식 / 선물옵션 섹션별 보유 현황 확인
4. 컬럼 헤더 클릭으로 원하는 기준 정렬

**국내주식 컬럼**: 거래소 | 종목코드 | 종목명 | 투자비중 | 보유수량 | 평가금액 | 매입단가 | 현재가 | 평가손익 | 수익률 | 시가총액 | PER | ROE | PBR | **배당수익률** | 주문

**해외주식 컬럼**: 거래소 | 종목코드 | 종목명 | 투자비중 | 통화 | 보유수량 | 평가금액(외화) | 매입단가 | 현재가 | 평가손익(외화/원화) | 수익률 | 시가총액 | PER | ROE | PBR | **배당수익률** | 주문

> 키가 없으면 에러 대신 설정 안내 메시지가 표시됩니다.

### 관심종목 (웹)

1. **관심종목** 클릭 → 상단 폼에서 국내(6자리 코드·종목명) 또는 미국(티커) 추가
2. 대시보드: 현재가·등락·시가총액·매출·영업이익·순이익·영업이익률·배당수익률 조회
3. 종목명 클릭 → 종목 상세 모달: **ROE·배당수익률·주당배당금(DPS)**·PER·PBR·52주 고저·업종 + 재무 테이블(매출·영업이익·**영업이익률**·순이익·**순이익률**)
4. 종목명 클릭(대시보드) → `/detail/:symbol` 상세 페이지로 이동

### 주문 (웹)

KIS API 키 필요. **주문** 페이지 → 5탭 UI:
- **주문발송**: 상단 시장+종목 검색바(공유) + [신규주문 | 정정/취소] 서브탭. xl 이상에서 2컬럼(왼쪽=호가창, 오른쪽=주문폼). 호가 클릭 시 매매방향+가격 자동 입력. 하단에 가격 차트 패널(캔들+MA5/20+볼린저밴드+거래량).
- **미체결**: 미체결 주문 조회. API 발주분만 정정/취소 가능.
- **체결내역**: 당일 체결 내역
- **주문이력**: 로컬 DB 주문 이력 (날짜·종목·상태 필터)
- **예약주문**: 가격조건(`price_below`/`price_above`) 또는 시간예약 자동 발주

### 해외주식 양도소득세 (`/tax`)

1. **요약** 탭: 연간 양도차익/기본공제(250만)/과세표준/예상세액(22%) 카드 + 종목별 차트
2. **매매내역** 탭: KIS API 동기화 버튼 (CTOS4001R+TTTS3035R 병합, 잔고 기반 적응적 소급 ~2015년) + 수동 추가
3. **계산 상세** 탭: FIFO 매도→매수 매핑 상세 (시간순 재생, 매도 시점 이전 매수만 소진)
4. **시뮬레이션** 탭: 현재 보유 종목 가상 매도 → 예상 양도세 계산 (DB 저장 없음)

도메인 규칙: `docs/TAX_DOMAIN.md`

### 백테스트 (`/backtest`)

KIS AI Extensions MCP 서버 연동. `KIS_MCP_ENABLED=true` + MCP 서버 실행 필요.

1. 종목 선택 + 프리셋 전략 선택 (10개, 상세 설명 카드 표시) 또는 커스텀 YAML
2. 기간/초기자금 설정 → **백테스트 실행** (서버에서 Docker 기반 QuantConnect Lean 엔진)
3. 결과: 수익률/샤프비율/MDD/승률 + 수익률 곡선 + 거래 내역
4. **전략 비교**: 4개 대표 전략 동시 실행 → 비교 테이블

> 백테스트는 서버에서 실행되므로 다른 페이지로 이동해도 작업이 중단되지 않습니다.

### AI자문 (DetailPage → 종합 리포트 탭)

1. 관심종목 대시보드 또는 종목 스크리너에서 종목 클릭 → `/detail/:symbol`
2. **종합 리포트** 탭 → **기본적 분석** 서브탭: 재무제표 3종 + 계량지표 파이차트
3. **기술적 분석** 서브탭: 타임프레임(15분/60분/1일/1주) + 기간 선택 → 캔들·지표 차트
4. **AI자문** 서브탭 → **[AI분석 생성]** 버튼 → GPT-4o 종합투자의견 생성 (10~30초)

---

## API 엔드포인트

백엔드를 직접 호출하거나 Swagger UI(`/docs`)에서 테스트할 수 있습니다.

### `GET /api/screener/stocks`

멀티팩터 종목 스크리닝. 결과에 현재가·수익률·배당수익률 enrichment 포함.

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `date` | string | 오늘 | `YYYYMMDD` 또는 `YYYY-MM-DD` |
| `sort_by` | string | `mktcap desc` | `"ROE desc, PER asc"` 형태 |
| `top` | int | 전체 | 상위 N개 반환 |
| `per_min` | float | - | PER 최소값 |
| `per_max` | float | - | PER 최대값 |
| `pbr_max` | float | - | PBR 최대값 |
| `roe_min` | float | - | ROE 최소값 (%) |
| `market` | string | - | `KOSPI` 또는 `KOSDAQ` |
| `include_negative` | bool | false | 적자기업(PER < 0) 포함 |
| `earnings_only` | bool | false | 당일 실적발표 종목만 |
| `drop_from_high` | float | - | 52주 고점 대비 최대 하락률 (%, 예: -30) |

```bash
curl "http://localhost:8000/api/screener/stocks?market=KOSPI&per_max=15&roe_min=10&sort_by=ROE+desc&top=20"
```

### `GET /api/earnings/filings`

날짜별 정기보고서 제출 목록 (국내 DART / 미국 SEC EDGAR)

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `market` | string | `KR` | `KR`(국내 DART) 또는 `US`(미국 SEC) |
| `start_date` | string | 오늘 | 시작일 |
| `end_date` | string | 오늘 | 종료일 |

```bash
curl "http://localhost:8000/api/earnings/filings?date=2025-02-20"
curl "http://localhost:8000/api/earnings/filings?market=US&start_date=20250201&end_date=20250228"
```

### `GET /api/balance`

KIS 실전계좌 잔고 조회. KIS API 키 미설정 시 503 반환.

### `GET /api/advisory/{code}/ohlcv`

타임프레임·기간별 OHLCV + 기술지표 조회.

| 파라미터 | 설명 |
|---------|------|
| `market` | `KR` 또는 `US` |
| `interval` | `15m` / `60m` / `1d` / `1wk` |
| `period` | `60d` / `6mo` / `1y` 등 (interval별 최대 기간 자동 조정) |

---

## 데이터 소스

| 데이터 | 출처 | 비고 |
|--------|------|------|
| 국내 PER·PBR·EPS·BPS·시가총액 | [pykrx](https://github.com/sharebook-kr/pykrx) (KRX) | 스크리너 전용. 당일 장 종료 후 갱신 |
| 국내 시세·시가총액·배당수익률·주당배당금 | [yfinance](https://github.com/ranaroussi/yfinance) `.KS`/`.KQ` | 관심종목·잔고·AI자문. 2026-02 KRX 서버 변경으로 전환 |
| 정기보고서 공시 (국내) | [OpenDART API](https://opendart.fss.or.kr) | `OPENDART_API_KEY` 필요 |
| 재무제표 (국내) | [OpenDART API](https://opendart.fss.or.kr) `fnlttSinglAcntAll` | `OPENDART_API_KEY` 필요. 최대 10년 |
| 정기보고서 공시 (미국) | [SEC EDGAR](https://www.sec.gov) EFTS API | 키 불필요 |
| 미국 주식 시세·재무·배당수익률·주당배당금 | [yfinance](https://github.com/ranaroussi/yfinance) | 15분 지연, 최대 4년 재무 |
| 계좌 잔고·주문·국내 실시간 호가 | 한국투자증권 OpenAPI | KIS API 키 필요. WS 끊김 시 REST 자동 fallback |
| 해외주식 실시간 시세 | [Finnhub](https://finnhub.io) WS | `FINNHUB_API_KEY` 설정 시 활성화. 무료 30 심볼. 미설정 시 yfinance 폴링 |
| AI 투자의견 | [OpenAI API](https://platform.openai.com) (GPT-4o) | `OPENAI_API_KEY` 필요. 모델 변경 가능 |
| 백테스트 엔진 | [KIS AI Extensions](https://github.com/koreainvestment/open-trading-api) MCP | `KIS_MCP_ENABLED=true`. QuantConnect Lean (Docker) |

---

## 아키텍처

### 전체 시스템 구조

```
┌───────────────────────────────────────────────────────────────┐
│                      Browser (React SPA)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Pages     │ │Components│ │ Hooks    │ │ API Layer│          │
│  │(12 pages)│→│(UI 조립)  │→│(상태관리)  │→│(fetch)   │          │
│  └──────────┘ └──────────┘ └──────────┘ └────┬─────┘          │
└──────────────────────────────────────────────┼────────────────┘
                                               │ HTTP / WebSocket
┌──────────────────────────────────────────────┼────────────────┐
│                  FastAPI Server (main.py)     │               │
│                                              ▼                │
│  ┌───────────────────────────────────────────────────────┐    │
│  │                  Routers (routers/)                   │    │
│  │  screener │ earnings │ balance │ watchlist │ detail   │    │
│  │  order    │ quote(WS)│ advisory│ search   │ mkt_board │    │
│  └────────────────────────┬──────────────────────────────┘    │
│      (HTTP 검증 + 라우팅만) │ ← 계층 분리: services만 호출           │
│  ┌────────────────────────▼──────────────────────────────┐    │
│  │                 Services (services/)                  │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐   │   │
│  │  │order_service│ │quote_service│ │advisory_service│   │   │
│  │  │ 주문/취소/    │ │ KIS WS 관리│ │ AI분석+리포트  │  │   │
│  │  │ 대사/이력     │ │ REST fallbk│ │ GPT-4o 호출    │  │   │
│  │  └──────┬──────┘ └──────┬──────┘ └───────┬────────┘  │   │
│  │  ┌──────┴──────┐ ┌──────┴──────┐ ┌───────┴────────┐  │   │
│  │  │watchlist_svc│ │detail_svc   │ │reservation_svc │  │   │
│  │  │ 관심종목    │ │ 재무+밸류   │ │ 예약주문 스케줄│  │   │
│  │  └─────────────┘ └─────────────┘ └────────────────┘  │   │
│  └────────────────────────┬──────────────────────────────┘   │
│     (비즈니스 로직 + 외부 API 호출) │                         │
│  ┌────────────────────────▼──────────────────────────────┐   │
│  │        Data Layer (db/ + stock/ + screener/)           │   │
│  │  ┌───────────────────────────────────────────────────┐ │   │
│  │  │  SQLAlchemy ORM (db/)      → app.db (통합)       │ │   │
│  │  │  models/ (12 테이블) + repositories/ (6개)       │ │   │
│  │  │  store 모듈은 Repository 위임 래퍼 (시그니처 유지)│ │   │
│  │  └───────────────────────────────────────────────────┘ │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │   │
│  │  │cache.py  │ │symbol_   │ │dart_fin  │ │fno_     │  │   │
│  │  │(cache.db │ │map.py    │ │(재무제표)│ │master   │  │   │
│  │  │raw SQLite│ │(종목코드)│ │          │ │(마스터) │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘  │   │
│  └───────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### 외부 의존성 연결

```
                  ┌────────────────────────┐
                  │    KIS OpenAPI 서버     │
                  │   (한국투자증권)        │
                  └──────┬─────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                  │
  REST API          WebSocket          OAuth2 토큰
(주문/잔고/시세)   (실시간 호가)      (12시간 TTL)
       │                 │                  │
       ▼                 ▼                  ▼
  ┌────────────────────────────────────────────┐
  │             FastAPI Server                  │
  │                                            │
  │  order_service ◄── KIS REST (주문/잔고)    │
  │  quote_service ◄── KIS WS (체결/호가)      │
  │       │              │                     │
  │       │         WS 끊김 시                 │
  │       │         REST fallback              │
  │       │         (3초 폴링)                 │
  │       ▼              ▼                     │
  │  ┌─────────┐  ┌─────────────┐              │
  │  │ app.db  │  │ yfinance    │ ◄── 비개장일 │
  │  │ (ORM)   │  │ (fallback)  │   직전 종가   │
  │  └─────────┘  └─────────────┘              │
  └────────────────────────────────────────────┘

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ OpenDART │  │ yfinance │  │ SEC      │  │ OpenAI   │
  │ (공시/   │  │ (해외시세│  │ EDGAR    │  │ (GPT-4o) │
  │  재무)   │  │  /재무)  │  │(미국공시)│  │          │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 실시간 시세 데이터 흐름

```
┌── 국내 주식 (KR) ────────────────────────────────────────────┐
│                                                               │
│  KIS WS (단일 연결)                                           │
│    ├─ H0STCNT0 (체결가)  ──┐                                 │
│    └─ H0STASP0 (10호가)  ──┤                                 │
│                             ▼                                 │
│  KISQuoteManager ──► _broadcast() ──► asyncio.Queue (per tab)│
│       │                                     │                 │
│       │ (WS 끊김 시)                        ▼                 │
│       └─► REST fallback ──────────► /ws/quote/{symbol}       │
│           (3초 폴링, 0.1초/심볼)     100ms 배칭 → 브라우저 WS │
│                                           │                   │
│                                           ▼                   │
│                                    useQuote() 훅              │
│                                    rAF throttle               │
│                                    → React 렌더링             │
└───────────────────────────────────────────────────────────────┘

┌── 선물옵션 (FNO) ────────────────────────────────────────────┐
│                                                               │
│  동일 KIS WS 연결에서 구독                                    │
│    ├─ H0IFASP0/CNT0 (지수선물, 5레벨)                        │
│    ├─ H0IOASP0/CNT0 (지수옵션, 5레벨)                        │
│    ├─ H0ZFASP0/CNT0 (주식선물, 10레벨)                       │
│    └─ H0ZOASP0/CNT0 (주식옵션, 10레벨)                       │
│                                                               │
│  _resolve_fno_type(symbol) → IF/IO/ZF/ZO (캐싱)              │
│  /ws/quote/{symbol}?market=FNO → 100ms 배칭                  │
└───────────────────────────────────────────────────────────────┘

┌── 해외 주식 (US) ────────────────────────────────────────────┐
│                                                               │
│  ┌── FINNHUB_API_KEY 있음 ──┐  ┌── 없음 ──────────────────┐ │
│  │ Finnhub WS (30심볼 한도) │  │ yfinance 2초 폴링(15분)  │ │
│  │ 실시간 체결가             │  │ fast_info.last_price      │ │
│  └────────────┬─────────────┘  └──────────┬───────────────┘ │
│               └──────────┬────────────────┘                  │
│                          ▼                                   │
│              OverseasQuoteManager                            │
│              심볼당 1개 폴링 태스크 (N 탭 → 1 호출)          │
│                          │                                   │
│                          ▼                                   │
│              /ws/quote/{symbol} → 브라우저                   │
└───────────────────────────────────────────────────────────────┘

┌── 시세판 (Market Board) ─────────────────────────────────────┐
│                                                               │
│  /ws/market-board (다중 심볼 단일 WS)                        │
│    ├─ 클라이언트 → subscribe/unsubscribe 메시지              │
│    ├─ 서버 → 200ms 배칭 → {"type":"prices","data":{}} 일괄   │
│    └─ 국내+해외 심볼 혼합 가능                                │
└───────────────────────────────────────────────────────────────┘
```

### 주문 도메인 상태 동기화

```
┌─ 주문 발송 ──────────────────────────────────────────────────┐
│                                                               │
│  프론트 → POST /api/order/place                               │
│              │                                                │
│              ▼                                                │
│      order_service.place_order()                              │
│         ├─ KIS API 호출 (매수/매도)                           │
│         ├─ 성공 → order_store.insert_order(PLACED)            │
│         └─ 응답: { order: {...}, balance_stale: true }        │
│                                     │                         │
│                     프론트: 잔고 재조회 트리거 ◄──┘            │
└───────────────────────────────────────────────────────────────┘

┌─ 주문 취소 ──────────────────────────────────────────────────┐
│                                                               │
│  프론트 → POST /api/order/{no}/cancel                         │
│              │                                                │
│              ▼                                                │
│      order_service.cancel_order()                             │
│         ├─ KIS API 호출 (취소)                                │
│         ├─ 성공 → order_store.update_status(CANCELLED)        │
│         └─ 응답: { success, local_synced: true,               │
│                     order_status: "CANCELLED" }               │
│                                     │                         │
│           프론트: 미체결 목록 자동 재조회 ◄──┘                 │
└───────────────────────────────────────────────────────────────┘

┌─ 대사 (Reconciliation) ─────────────────────────────────────┐
│                                                               │
│  GET /api/order/history 또는 POST /api/order/sync             │
│              │                                                │
│              ▼                                                │
│    _reconcile_active_orders()                                 │
│      ├─ 로컬 DB: PLACED/PARTIAL 주문 조회                     │
│      ├─ KIS: 체결 내역 조회 (get_executions)                  │
│      ├─ KIS: 미체결 내역 조회 (get_open_orders)               │
│      └─ 매칭:                                                │
│           체결에 있음 ──────► FILLED / PARTIAL                │
│           미체결에 있음 ────► 상태 유지                        │
│           양쪽 다 없음 ────► CANCELLED (자동 감지)            │
└───────────────────────────────────────────────────────────────┘
```

### 디렉토리 구조

```
stock-manager/
├── config.py              # 환경변수 중앙 관리
├── main.py                # FastAPI 진입점 + lifespan (WS 관리자/스케줄러 시작)
├── routers/               # API 라우터 (HTTP 검증 + 라우팅만)
│   ├── _kis_auth.py       #   KIS 인증 공통 (ConfigError/ExternalAPIError)
│   ├── screener.py        #   GET /api/screener/stocks
│   ├── earnings.py        #   GET /api/earnings/filings
│   ├── balance.py         #   GET /api/balance
│   ├── watchlist.py       #   /api/watchlist/*
│   ├── detail.py          #   /api/detail/*
│   ├── order.py           #   /api/order/* (order_service만 import)
│   ├── quote.py           #   WS /ws/quote/{symbol}
│   ├── advisory.py        #   /api/advisory/*
│   ├── search.py          #   GET /api/search
│   ├── market_board.py    #   /api/market-board/* + WS (200ms 배칭)
│   ├── macro.py           #   /api/macro/* (지수/뉴스/심리/투자자)
│   ├── portfolio_advisor.py #  /api/portfolio-advisor/* (AI 포트폴리오 자문)
│   ├── report.py          #   /api/reports/* (일일보고서/추천이력/성과)
│   ├── pipeline.py        #   /api/pipeline/* (투자 파이프라인)
│   ├── backtest.py        #   /api/backtest/* (MCP 백테스트)
│   └── tax.py             #   /api/tax/* (해외주식 양도세)
├── services/              # 비즈니스 로직
│   ├── exceptions.py      #   ServiceError 예외 계층
│   ├── order_service.py   #   주문/취소/정정/대사/이력/예약/FNO시세
│   ├── quote_service.py   #   KIS WS + REST fallback + Finnhub + yfinance
│   ├── advisory_service.py#   AI분석 + GPT-4o 리포트
│   ├── watchlist_service.py#  관심종목 대시보드
│   ├── detail_service.py  #   재무/밸류에이션/종합리포트
│   ├── reservation_service.py # 예약주문 스케줄러 (20초 폴링)
│   ├── macro_service.py   #   매크로 분석 (지수/뉴스/심리지표)
│   ├── portfolio_advisor_service.py # AI 포트폴리오 자문
│   ├── tax_service.py     #   해외주식 양도세 (FIFO + 시뮬레이션)
│   ├── mcp_client.py      #   MCP Streamable HTTP 클라이언트
│   └── backtest_service.py#   백테스트 오케스트레이션 (MCP 연동)
├── db/                    # SQLAlchemy ORM 패키지
│   ├── base.py            #   DeclarativeBase
│   ├── session.py         #   Engine, SessionLocal, get_db(), get_session()
│   ├── models/            #   ORM 모델 15개 (Watchlist, Order, Advisory, Tax 등)
│   └── repositories/      #   Repository 8개 (JPA Repository 패턴)
├── alembic/               # DB 스키마 마이그레이션 (Alembic)
├── stock/                 # 데이터 레이어 (Store 래퍼 + 외부 데이터 수집)
│   ├── db_base.py         #   cache.py 전용 SQLite 유틸 + KST 헬퍼
│   ├── store.py           #   WatchlistRepository 위임 래퍼
│   ├── order_store.py     #   OrderRepository 위임 래퍼
│   ├── advisory_store.py  #   AdvisoryRepository 위임 래퍼
│   ├── market_board_store.py # MarketBoardRepository 위임 래퍼
│   ├── report_store.py    #   ReportRepository 위임 래퍼
│   ├── macro_store.py     #   MacroRepository 위임 래퍼
│   ├── strategy_store.py  #   BacktestRepository 위임 래퍼
│   ├── tax_store.py       #   TaxRepository 위임 래퍼
│   ├── cache.py           #   cache.db (raw SQLite TTL 캐시)
│   ├── market.py          #   yfinance 기반 시세/펀더멘털
│   ├── yf_client.py       #   해외주식 yfinance 클라이언트
│   ├── dart_fin.py        #   OpenDART 재무제표
│   ├── fno_master.py      #   KIS 선물옵션 마스터파일
│   ├── symbol_map.py      #   종목코드 ↔ 종목명 매핑
│   ├── utils.py           #   is_domestic() / is_fno()
│   └── sec_filings.py     #   SEC EDGAR 공시
├── screener/              # 스크리너 패키지 (CLI + API 공용)
├── frontend/              # React 19 + Vite + Tailwind CSS v4
│   └── src/
│       ├── pages/         #   7개 페이지 (SPA 라우팅)
│       ├── components/    #   재사용 UI 컴포넌트
│       ├── hooks/         #   커스텀 훅 (API 통신 + 상태 관리)
│       └── api/           #   fetch 래퍼 (hooks에서만 사용)
├── Dockerfile             # 멀티스테이지 빌드 (Node → Python)
└── docker-compose.yml     # 프로덕션 배포
```

**국내/해외/FNO 분기 기준**: `stock/utils.py`의 `is_domestic(code)` — 6자리 숫자이면 국내(KRX), `is_fno(code)` — 1/2/3xxx 형식이면 선물옵션, 나머지는 해외(US).

**계층 분리 원칙**: `routers/`는 오직 `services/`만 호출. `stock/` store 직접 접근 금지. 예외는 `ServiceError` 계층(`ConfigError`/`ExternalAPIError`) 사용 — `main.py` 중앙 핸들러에서 HTTP 응답으로 일괄 변환.

---

## 해외주식 지원 범위

| 기능 | 지원 | 비고 |
|------|------|------|
| 관심종목 추가/삭제 | ✅ | 티커 직접 입력 (AAPL, NVDA 등) |
| 대시보드 시세·재무·배당수익률 | ✅ | USD, 15분 지연 |
| 종목 상세 재무 (최대 4년) | ✅ | yfinance 기준 |
| 종목 상세: ROE·배당수익률·주당배당금 | ✅ | yfinance |
| 공시 조회 (SEC 10-K/10-Q) | ✅ | 키 불필요 |
| AI자문 | ✅ | yfinance 재무 3종 + GPT-4o |
| PER/PBR 히스토리 차트 | ✅ | 분기 EPS/BPS + 일별 주가 기반 추정 (yfinance) |
| 스크리너 | ❌ | 국내 전용 |
| 지원 시장 | US | NASDAQ/NYSE/AMEX |

---

## DB 시스템

### 비즈니스 데이터 (SQLAlchemy ORM)

`~/stock-watchlist/app.db` — 비즈니스 DB 단일 파일 통합. 15개 테이블 (watchlist, orders, advisory, market_board, stock_info, macro, report, backtest, tax).

`DATABASE_URL` 환경변수로 PostgreSQL/Oracle 전환 가능:
```bash
# SQLite (기본)
DATABASE_URL=sqlite:///~/stock-watchlist/app.db

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/stockmanager
```

### 캐시 (raw SQLite)

| 파일 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` | 스크리너 KRX/DART 데이터 | 영구 (날짜키 기반) |
| `~/stock-watchlist/cache.db` | 시세·재무·배당·수익률 캐시 | 장중 2분~1시간 / 장외 30분~12시간 |

> **캐시 초기화**: Docker 컨테이너 시작 시 `cache.db`를 자동 삭제합니다. `app.db`는 영향 없음.

---

## AI 에이전트 팀 (하네스)

Benjamin Graham의 안전마진 철학을 기반으로 한 7명의 AI 에이전트 팀이 투자 의사결정과 시스템 개발을 지원합니다. 에이전트는 기존 API를 호��하여 동작하며, 서비스 코드를 변경하지 않습니다.

### 에이전트 구성

**도메인 전문가 (4명)** — 투자 분석 파이프라인:

| 에이전트 | 역할 |
|---------|------|
| MacroSentinel | 매크로 환경 분석 — 버핏지수/VIX/공포탐욕 → 시장 체제(적극매수/선별/신중/방어) 판단 |
| ValueScreener | Graham 기준 PER/PBR/ROE 동적 필터로 저평가 종목 스크리닝 |
| MarginAnalyst | Graham Number 내재가치 산출 + 재무 건전성 + 기술적 매수 타이밍 심층 분석 |
| OrderAdvisor | 포지션 사이징 + 지정가/손절/익절 주문 추천 (자동 주문 실행 없음, 사용자 승인 필수) |

**빌더 (3명)** — 시스템 개발/검증/개선:

| 에이전트 | 역할 |
|---------|------|
| DevArchitect | 도메인 전문가에게 자문받으며 통합자산관리 기능(포트폴리오/리밸런싱/리스크/성과/일지) 풀스택 개발 |
| QA Inspector | API↔프론트 shape 교차 비교, 라우팅 정합성, 투자 로직 정확성 등 경계면 통합 검증 |
| RefactorEngineer | 도메인 전문가에게 "왜 이렇게 되어있는가" 확인 후 안전한 리팩토링 (도메인 정합성 보존) |

### 파이프라인

| 파이프라인 | 오케스트레이터 | 트리거 예시 | 흐름 |
|-----------|-------------|-----------|------|
| 분석 | value-invest | "종목 발굴해줘", "저평가 종목", "안전마진 분석" | Macro → Screener → Analyst → Advisor |
| 개발 | asset-dev | "대시보드 만들어줘", "리밸런싱 기능" | 자문 → 설계 → 백엔드 → QA → 프론트 → QA → 보고 |
| 리팩토링 | refactor-audit | "리팩토링 해줘", "코드 감사", "구조 개선" | 감사 → 도메인자문 → 계획 → 실행 → QA → 보고 |

### 워크스페이스 산출물

분석 파이프라인 실행 시 `_workspace/` 디렉토리에 단계별 결과가 저장됩니다:

| 파일 | 내용 |
|------|------|
| `01_macro_assessment.json` | 매크로 체제 판단 (regime, 버핏지수, 공포탐욕) |
| `02_screened_candidates.json` | Graham 필터 통과 후보 종목 (최대 10개) |
| `03_analyses/{code}_analysis.json` | 종목별 심층 분석 (Graham Number, 7지표 등급) |
| `05_recommendations.json` | 최종 매수 추천서 (지정가, 수량, 손절/익절) |

> 에이전트 정의: `.claude/agents/`, 스킬 정의: `.claude/skills/`

---

## 주의사항

- `.env` 파일에 민감정보가 포함되므로 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)
- 스크리너 KRX 데이터(pykrx)는 당일 장 마감 이후 제공됩니다. 장중에는 전일 데이터가 반환될 수 있습니다
- 국내 시세·펀더멘털(관심종목·잔고·AI자문용)은 yfinance 기반이며 15분 지연됩니다
- 스크리너 첫 조회: KRX 전종목 수집 + yfinance enrichment로 수십 초 소요. 이후 캐시로 빠르게 응답
- 미국 주식 재무 데이터는 yfinance 기준 최대 4년치만 제공됩니다
- `FINNHUB_API_KEY` 미설정 시 해외주식 호가는 yfinance 2초 폴링(15분 지연)으로 동작합니다
- KIS WebSocket 끊김 시 REST API 자동 fallback으로 국내 시세를 3초 간격으로 유지합니다
- KIS Approval Key / REST 토큰은 12시간 TTL로 자동 갱신됩니다
- **비개장일(주말/공휴일)에도 직전 거래일 가격이 표시됩니다** — 국내: KIS WS 구독 즉시 yfinance 초기 push / 해외: `fast_info.last_price or previous_close` fallback
