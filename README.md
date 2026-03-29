# Stock Manager

한국투자증권(KIS) OpenAPI 연동 주식 계좌 관리 서버 + 웹 기반 종목 스크리너/관심종목 대시보드 + AI자문 기능.

KIS 계정 없이도 종목 스크리닝과 공시 조회, 관심종목, AI자문 기능을 사용할 수 있습니다.

---

## 주요 기능

### 웹 대시보드
브라우저에서 `http://localhost:8000` 접속

| 메뉴 | 기능 |
|------|------|
| **대시보드** | 잔고 요약 + 오늘 공시 5건 + 시총 상위 10종목 (전일종가·현재가·수익률·배당수익률 포함) |
| **종목 스크리너** | PER·PBR·ROE·시가총액 멀티팩터 필터링 + 정렬. 전일종가·현재가·당일%·3개월%·6개월%·1년%·배당수익률 컬럼 표시. 관심종목 즉시 추가 버튼 |
| **공시 조회** | 날짜별 사업/반기/분기 보고서. 국내(DART) / 미국(SEC EDGAR) 탭 선택. 관심종목 추가 버튼 |
| **잔고 조회** | 국내주식·해외주식·선물옵션 잔고. 시가총액·PER·ROE·PBR·배당수익률 포함. 컬럼 클릭 정렬. (KIS API 키 필요) |
| **관심종목** | 국내·미국 종목 추가·관리. 시세·재무 대시보드. 종목 상세(재무 10년/4년·밸류에이션·종합 리포트). 종목 상세 모달에서 ROE·배당수익률·주당배당금(DPS)·영업이익률·순이익률 표시 |
| **종목 상세** | 탭 UI: 재무분석 / 밸류에이션 차트 / 종합 리포트 (CAGR 요약·기본적 분석·기술적 분석·AI자문 서브탭) |
| **주문** | 국내·해외·선물옵션 매수/매도. 국내/FNO=지정가/시장가/조건부지정가/최유리지정가+IOC/FOK, 해외=지정가/시장가. 실시간 호가창(국내·FNO=KIS WS, 해외=현재가). 호가 클릭 시 매매방향+가격 자동 입력. 신규주문/정정취소 서브탭. 가격 차트 패널. 미체결·체결내역·주문이력·예약주문 |
| **시세판** | 당일 신고가/신저가 Top10 (시총 기준, 컴팩트 카드 그리드). 관심종목 자동 표시(★) + 별도 추가 종목(DB 영속화, 최대 30개). 1년 주봉 미니 스파크라인 차트. 실시간 시세(WebSocket). **비개장일에도 직전 거래일 가격 표시** (국내·해외 모두 yfinance fallback). |

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
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |

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

---

## 아키텍처

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Pages     │ │Components│ │ Hooks    │ │ API Layer│           │
│  │ (7 pages)│→│(UI 조립) │→│(상태관리)│→│(fetch)   │           │
│  └──────────┘ └──────────┘ └──────────┘ └────┬─────┘           │
└──────────────────────────────────────────────┼──────────────────┘
                                               │ HTTP / WebSocket
┌──────────────────────────────────────────────┼──────────────────┐
│                    FastAPI Server (main.py)   │                   │
│                                              ▼                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Routers (routers/)                      │    │
│  │  screener │ earnings │ balance │ watchlist │ detail       │    │
│  │  order    │ quote(WS)│ advisory│ search   │ market_board │    │
│  └────────────────────────┬────────────────────────────────┘    │
│           (HTTP 검증 + 라우팅만) │ ← 계층 분리: services만 호출     │
│  ┌────────────────────────▼────────────────────────────────┐    │
│  │                  Services (services/)                      │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐   │    │
│  │  │order_service│ │quote_service│ │advisory_service  │   │    │
│  │  │ 주문/취소/  │ │ KIS WS 관리│ │ AI분석+리포트    │   │    │
│  │  │ 대사/이력   │ │ REST fallbk│ │ GPT-4o 호출      │   │    │
│  │  └──────┬──────┘ └──────┬──────┘ └────────┬─────────┘   │    │
│  │  ┌──────┴──────┐ ┌──────┴──────┐ ┌────────┴─────────┐   │    │
│  │  │watchlist_svc│ │detail_svc   │ │reservation_svc   │   │    │
│  │  │ 관심종목    │ │ 재무+밸류   │ │ 예약주문 스케줄러 │   │    │
│  │  └─────────────┘ └─────────────┘ └──────────────────┘   │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│           (비즈니스 로직 + 외부 API 호출) │                        │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │               Data Layer (stock/ + screener/)             │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │    │
│  │  │order_    │ │advisory_ │ │market_   │ │watchlist  │  │    │
│  │  │store     │ │store     │ │board_    │ │store      │  │    │
│  │  │(orders.db│ │(advisory.│ │store     │ │(watchlist.│  │    │
│  │  │ WAL모드) │ │ db)      │ │(mkt_brd. │ │ db)       │  │    │
│  │  └──────────┘ └──────────┘ │ db)      │ └───────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ └──────────┘ ┌───────────┐  │    │
│  │  │cache.py  │ │symbol_   │ ┌──────────┐ │fno_master │  │    │
│  │  │(cache.db │ │map.py    │ │dart_fin  │ │(마스터    │  │    │
│  │  │ WAL모드) │ │(종목코드)│ │(재무제표)│ │ 파일)     │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 외부 의존성 연결

```
                    ┌──────────────────────┐
                    │   KIS OpenAPI 서버    │
                    │  (한국투자증권)        │
                    └──────┬───────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                  │
    REST API          WebSocket          OAuth2 토큰
  (주문/잔고/시세)   (실시간 호가)      (12시간 TTL)
         │                 │                  │
         ▼                 ▼                  ▼
  ┌──────────────────────────────────────────────┐
  │              FastAPI Server                    │
  │                                                │
  │  order_service ◄── KIS REST (주문/잔고)        │
  │  quote_service ◄── KIS WS (체결/호가)          │
  │       │              │                         │
  │       │         WS 끊김 시                      │
  │       │         REST fallback                   │
  │       │         (3초 폴링)                      │
  │       ▼              ▼                         │
  │  ┌─────────┐  ┌─────────────┐                  │
  │  │orders.db│  │ yfinance    │ ◄── 비개장일     │
  │  │(SQLite) │  │ (fallback)  │     직전 종가     │
  │  └─────────┘  └─────────────┘                  │
  └────────────────────────────────────────────────┘

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ OpenDART │  │ yfinance │  │ SEC      │  │ OpenAI   │
  │ (공시/   │  │ (해외시세│  │ EDGAR    │  │ (GPT-4o) │
  │  재무)   │  │  /재무)  │  │ (미국공시│  │          │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 실시간 시세 데이터 흐름

```
┌── 국내 주식 (KR) ──────────────────────────────────────────────┐
│                                                                  │
│  KIS WS (단일 연결)                                              │
│    ├─ H0STCNT0 (체결가)  ──┐                                    │
│    └─ H0STASP0 (10호가)  ──┤                                    │
│                             ▼                                    │
│  KISQuoteManager ──► _broadcast() ──► asyncio.Queue (per tab)   │
│       │                                     │                    │
│       │ (WS 끊김 시)                        ▼                    │
│       └─► REST fallback ──────────► /ws/quote/{symbol}          │
│           (3초 폴링, 0.1초/심볼)     100ms 배칭 → 브라우저 WS    │
│                                           │                      │
│                                           ▼                      │
│                                    useQuote() 훅               │
│                                    rAF throttle                  │
│                                    → React 렌더링                │
└──────────────────────────────────────────────────────────────────┘

┌── 선물옵션 (FNO) ──────────────────────────────────────────────┐
│                                                                  │
│  동일 KIS WS 연결에서 구독                                       │
│    ├─ H0IFASP0/CNT0 (지수선물, 5레벨)                           │
│    ├─ H0IOASP0/CNT0 (지수옵션, 5레벨)                           │
│    ├─ H0ZFASP0/CNT0 (주식선물, 10레벨)                          │
│    └─ H0ZOASP0/CNT0 (주식옵션, 10레벨)                          │
│                                                                  │
│  _resolve_fno_type(symbol) → IF/IO/ZF/ZO (캐싱)               │
│  /ws/quote/{symbol}?market=FNO → 100ms 배칭                    │
└──────────────────────────────────────────────────────────────────┘

┌── 해외 주식 (US) ──────────────────────────────────────────────┐
│                                                                  │
│  ┌── FINNHUB_API_KEY 있음 ──┐  ┌── 없음 ────────────────────┐  │
│  │ Finnhub WS (30심볼 한도) │  │ yfinance 2초 폴링 (15분지연)│  │
│  │ 실시간 체결가             │  │ fast_info.last_price         │  │
│  └────────────┬─────────────┘  └──────────┬──────────────────┘  │
│               └──────────┬────────────────┘                      │
│                          ▼                                       │
│              OverseasQuoteManager                                │
│              심볼당 1개 폴링 태스크 (N 탭 → 1 호출)             │
│                          │                                       │
│                          ▼                                       │
│              /ws/quote/{symbol} → 브라우저                       │
└──────────────────────────────────────────────────────────────────┘

┌── 시세판 (Market Board) ───────────────────────────────────────┐
│                                                                  │
│  /ws/market-board (다중 심볼 단일 WS)                           │
│    ├─ 클라이언트 → subscribe/unsubscribe 메시지                  │
│    ├─ 서버 → 200ms 배칭 → {"type":"prices", "data":{...}} 일괄  │
│    └─ 국내+해외 심볼 혼합 가능                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 주문 도메인 상태 동기화

```
┌─ 주문 발송 ────────────────────────────────────────────────────┐
│                                                                  │
│  프론트 → POST /api/order/place                                  │
│              │                                                   │
│              ▼                                                   │
│      order_service.place_order()                                │
│         ├─ KIS API 호출 (매수/매도)                              │
│         ├─ 성공 → order_store.insert_order(PLACED)              │
│         └─ 응답: { order: {...}, balance_stale: true }          │
│                                     │                            │
│                     프론트: 잔고 재조회 트리거 ◄──┘               │
└──────────────────────────────────────────────────────────────────┘

┌─ 주문 취소 ────────────────────────────────────────────────────┐
│                                                                  │
│  프론트 → POST /api/order/{no}/cancel                            │
│              │                                                   │
│              ▼                                                   │
│      order_service.cancel_order()                               │
│         ├─ KIS API 호출 (취소)                                   │
│         ├─ 성공 → order_store.update_order_status(CANCELLED)    │
│         └─ 응답: { success, local_synced: true,                 │
│                     order_status: "CANCELLED" }                  │
│                                     │                            │
│           프론트: 미체결 목록 자동 재조회 ◄──┘                    │
└──────────────────────────────────────────────────────────────────┘

┌─ 대사 (Reconciliation) ───────────────────────────────────────┐
│                                                                  │
│  GET /api/order/history 또는 POST /api/order/sync               │
│              │                                                   │
│              ▼                                                   │
│    _reconcile_active_orders()                                   │
│      ├─ 로컬 DB: PLACED/PARTIAL 주문 조회                       │
│      ├─ KIS: 체결 내역 조회 (get_executions)                    │
│      ├─ KIS: 미체결 내역 조회 (get_open_orders)                 │
│      └─ 매칭:                                                   │
│           체결에 있음 ──────► FILLED / PARTIAL                   │
│           미체결에 있음 ────► 상태 유지                           │
│           양쪽 다 없음 ────► CANCELLED (자동 감지)              │
└──────────────────────────────────────────────────────────────────┘
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
│   └── market_board.py    #   /api/market-board/* + WS (200ms 배칭)
├── services/              # 비즈니스 로직
│   ├── exceptions.py      #   ServiceError 예외 계층
│   ├── order_service.py   #   주문/취소/정정/대사/이력/예약/FNO시세
│   ├── quote_service.py   #   KIS WS + REST fallback + Finnhub + yfinance
│   ├── advisory_service.py#   AI분석 + GPT-4o 리포트
│   ├── watchlist_service.py#  관심종목 대시보드
│   ├── detail_service.py  #   재무/밸류에이션/종합리포트
│   └── reservation_service.py # 예약주문 스케줄러 (20초 폴링)
├── stock/                 # 데이터 레이어 (DB + 외부 데이터 수집)
│   ├── db_base.py         #   SQLite 공용 (WAL 모드, timeout 10초)
│   ├── order_store.py     #   orders.db CRUD
│   ├── advisory_store.py  #   advisory.db CRUD
│   ├── market_board_store.py # market_board.db CRUD
│   ├── store.py           #   watchlist.db CRUD
│   ├── cache.py           #   cache.db (TTL 캐시, WAL 모드)
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

## 캐시 시스템

| 파일 | 용도 | TTL |
|------|------|-----|
| `screener_cache.db` | 스크리너 KRX/DART 데이터 | 영구 (날짜키 기반) |
| `~/stock-watchlist/cache.db` | 시세·재무·배당·수익률 캐시 | 장중 2분~1시간 / 장외 30분~12시간 |
| `~/stock-watchlist/watchlist.db` | 관심종목 목록 | 영구 |
| `~/stock-watchlist/orders.db` | 주문 이력 + 예약주문 | 영구 |
| `~/stock-watchlist/advisory.db` | AI자문 데이터·리포트 | 영구 |

> **캐시 초기화**: Docker 컨테이너 시작 시 `cache.db`를 자동 삭제합니다. 배포 후 구버전 캐시로 인한 문제를 방지합니다. `watchlist.db`는 영향 없음.

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
