# Stock Manager

한국투자증권(KIS) OpenAPI 연동 주식 계좌 관리 서버 + 웹 기반 종목 스크리너 대시보드.

KIS 계정 없이도 종목 스크리닝과 공시 조회를 사용할 수 있습니다.

---

## 주요 기능

### 웹 대시보드
브라우저에서 `http://localhost:8000` 접속

| 메뉴 | 기능 |
|------|------|
| **대시보드** | 잔고 요약 + 오늘 공시 5건 + 시총 상위 10종목 한눈에 보기 |
| **종목 스크리너** | PER·PBR·ROE·시가총액 멀티팩터 필터링 + 정렬 |
| **공시 조회** | 날짜별 사업/반기/분기 보고서 제출 목록. 보고서명 클릭 → DART 원문 |
| **잔고 조회** | 보유종목·평가금액·손익 현황 (KIS API 키 필요) |

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
| `KIS_APP_KEY` | 잔고 조회 시 필수 | KIS 실계좌 앱 키 |
| `KIS_APP_SECRET` | 잔고 조회 시 필수 | KIS 실계좌 앱 시크릿 |
| `KIS_ACNT_NO` | 잔고 조회 시 필수 | 계좌번호 앞 8자리 |
| `KIS_ACNT_PRDT_CD` | 잔고 조회 시 필수 | 계좌번호 뒤 2자리 (보통 `01`) |
| `OPENDART_API_KEY` | 공시 조회 시 필수 | [OpenDART](https://opendart.fss.or.kr) 에서 발급 |
| `KIS_BASE_URL` | 선택 | 기본값: `https://openapi.koreainvestment.com:9443` |

> 스크리너와 공시 기능은 `OPENDART_API_KEY`만 있으면 됩니다. KIS 계정 없이 사용 가능합니다.

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

`http://localhost:8000` 에서 웹 대시보드와 API가 함께 동작합니다.

### 방법 4 — Docker (프로덕션)

```bash
docker-compose up --build
```

내부적으로 Node.js 멀티스테이지 빌드(프론트엔드 빌드 → Python 런타임)를 수행합니다.
완료 후 `http://localhost:8000` 에서 접속합니다.

> **개발 시 핫리로드**: Docker 볼륨 마운트를 사용하면 컨테이너 내부의 `frontend/dist/`가 가려지므로, 개발 중에는 방법 2를 권장합니다.

---

## 사용법

### 종목 스크리너 (웹)

1. 사이드바에서 **종목 스크리너** 클릭
2. 필터 설정:
   - **시장**: 전체 / KOSPI / KOSDAQ
   - **PER 범위**: 최소~최대 (예: 0 ~ 15)
   - **PBR 최대**, **ROE 최소** 입력
   - **정렬 기준**: PER·PBR·ROE·시가총액·종목명 중 선택, 오름/내림차순
   - **상위 N개**: 결과 수 제한
   - **적자기업 포함**: PER 음수 종목 포함 여부
   - **당일 실적발표만**: 오늘 보고서 제출 종목만 필터
3. **조회하기** 버튼 클릭

> 첫 조회는 전종목 데이터를 수집하므로 수십 초가 걸릴 수 있습니다. 이후 동일 날짜는 캐시에서 즉시 반환됩니다.

### 종목 스크리너 (CLI)

```bash
# 기본 사용법
python -m screener screen

# KOSPI 종목을 ROE 내림차순, PER 오름차순으로 정렬해 상위 20개
python -m screener screen --sort-by "ROE desc, PER asc" --market KOSPI --top 20

# PER 0~15, ROE 10% 이상 필터 후 CSV 저장
python -m screener screen --per-range 0 15 --roe-min 10 --export csv

# 오늘 실적발표 종목만 PER 낮은 순
python -m screener screen --earnings-today --sort-by PER

# 모든 옵션 보기
python -m screener screen --help
```

**지원 날짜 형식**: `YYYYMMDD`, `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`

### 공시 조회 (웹)

1. 사이드바에서 **공시 조회** 클릭
2. 날짜를 선택하고 **조회** 클릭
3. 사업보고서·반기보고서·분기보고서 제출 목록 확인
4. **보고서명 클릭** → DART 전자공시 원문이 새 탭으로 열림

### 공시 조회 (CLI)

```bash
# 오늘 공시
python -m screener earnings

# 특정 날짜 공시
python -m screener earnings --date 2025-02-20
```

### 잔고 조회 (웹)

KIS API 키가 `.env`에 설정되어 있어야 합니다.

1. 사이드바에서 **잔고 조회** 클릭
2. 총평가금액·예수금·주식평가금액 카드 확인
3. 보유종목별 현재가·평가손익·수익률 확인

> 키가 없으면 에러 대신 설정 안내 메시지가 표시됩니다.

---

## API 엔드포인트

백엔드를 직접 호출하거나 Swagger UI(`/docs`)에서 테스트할 수 있습니다.

### `GET /api/screener/stocks`

멀티팩터 종목 스크리닝

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `date` | string | 오늘 | `YYYYMMDD` 또는 `YYYY-MM-DD` |
| `sort_by` | string | `mktcap desc` | `"ROE desc, PER asc"` 형태 |
| `top` | int | 50 | 상위 N개 반환 |
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

날짜별 정기보고서 제출 목록

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `date` | string | 오늘 | `YYYYMMDD` 또는 `YYYY-MM-DD` |

```bash
curl "http://localhost:8000/api/earnings/filings?date=2025-02-20"
```

### `GET /api/balance`

KIS 실전계좌 잔고 조회. KIS API 키 미설정 시 503 반환.

```bash
curl "http://localhost:8000/api/balance"
```

---

## 데이터 소스

| 데이터 | 출처 | 비고 |
|--------|------|------|
| PER·PBR·EPS·BPS·시가총액 | [pykrx](https://github.com/sharebook-kr/pykrx) (KRX) | 당일 장 종료 후 갱신 |
| ROE | EPS ÷ BPS × 100 계산값 | |
| 정기보고서 공시 | [OpenDART API](https://opendart.fss.or.kr) | `OPENDART_API_KEY` 필요 |
| 계좌 잔고 | 한국투자증권 OpenAPI | KIS API 키 필요 |

---

## 주의사항

- `.env` 파일에 민감정보가 포함되므로 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함됨)
- pykrx는 KRX 데이터를 당일 장 마감 이후 제공합니다. 장중에는 전일 데이터가 반환될 수 있습니다
- 동일 날짜 스크리닝 결과는 `screener_cache.db`에 캐시됩니다. 오래된 캐시를 지우려면 해당 파일을 삭제하세요
