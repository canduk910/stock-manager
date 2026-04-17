# KIS AI Extensions 상세 조사 보고서

**조사일**: 2026-04-17
**저장소**: https://github.com/koreainvestment/kis-ai-extensions
**버전**: 0.1.0

---

## 📋 Executive Summary

KIS AI Extensions는 **한국투자증권 OpenAPI를 AI 에이전트에서 활용하기 위한 확장 기능 모음**으로, 3단계 투자 파이프라인을 자동화합니다:

1. **전략 설계** (kis-strategy-builder) — 10개 프리셋 + 83개 기술지표로 `.kis.yaml` 생성
2. **백테스팅** (kis-backtester) — Docker 기반 QuantConnect Lean 엔진으로 성과 검증 및 최적화
3. **주문 실행** (kis-order-executor) — 신호 강도(0~1) 확인 후 모의/실전 거래

**지원 에이전트**: Claude Code, Cursor, Codex, Gemini CLI (`.claude/`, `.cursor/`, `.codex/`, `.gemini/` 독립 구조)

---

## 🏗️ 시스템 아키텍처

### 에이전트별 구성

```
kis-ai-extensions/
├── agents/              # AI 플랫폼별 설정 (4종)
│   ├── claude/         # Claude 에이전트
│   ├── cursor/         # Cursor 에이전트
│   ├── codex/          # Codex 에이전트
│   └── gemini/         # Gemini CLI
├── shared/
│   ├── commands/       # 공통 커맨드 (auth, kis-help, kis-setup, my-status)
│   ├── hooks/          # 보안 훅 (시크릿 보호, 프로덕션 보호, MCP 로깅, 거래 로깅)
│   ├── scripts/        # Python 스크립트 (api_client.py, auth.py, do_auth.py, setup_check.py)
│   └── skills/         # 5개 스킬 모듈 (전략빌더, 백테스터, 주문실행, 팀, CS)
├── bin/                # CLI 도구 (cli.js)
└── test/               # 테스트 (unit, commands, smoke)
```

### MCP 서버 구성

- **포트**: 3846 (HTTP)
- **엔진**: Docker 기반 QuantConnect LEAN
- **호스트**: 127.0.0.1 (로컬 전용)
- **헬스체크**: `http://127.0.0.1:3846/health`

---

## 🛠️ 핵심 기능 상세

### 1️⃣ kis-strategy-builder (전략 설계)

#### 제공 자산

| 항목 | 수량 | 설명 |
|------|------|------|
| 기술지표 | 83개 | SMA, EMA, MACD, RSI, 볼린저밴드, ATR, 스토캐스틱 등 |
| 프리셋 전략 | 10개 | 골든크로스, 모멘텀, 52주신고가, ADX 추세 등 |
| 캔들패턴 | 66종 | hammer, doji, engulfing, morning_star, evening_star 등 |

#### 지표 카테고리

- **이동평균**: SMA, EMA, VWAP
- **모멘텀**: RSI, MACD, ROC, Returns
- **변동성**: 볼린저밴드, ATR, 표준편차, ZScore
- **오실레이터**: 스토캐스틱, CCI, Williams%R, MFI, IBS
- **추세**: ADX, 이격도(Disparity)
- **거래량**: OBV
- **기타**: 연속캔들, 66종 캔들패턴

#### 10개 프리셋 전략

| 전략 | 카테고리 | 핵심지표 |
|------|----------|----------|
| 골든크로스 | trend | SMA(50/200) 교차 |
| ADX 추세 | trend | ADX(14) > 25 |
| OBV 다이버전스 | volume | OBV 관찰 |
| MFI 과매도 | oscillator | MFI(14) < 20 |
| VWAP 반등 | trend | VWAP 지지선 |
| CCI 반전 | oscillator | CCI(20) 극값 |
| Williams %R | oscillator | Williams%R(14) |
| ATR 돌파 | volatility | ATR(14) 활용 |
| 이격도 평균회귀 | mean_reversion | Disparity(20) |
| 연속캔들패턴 | momentum | Consecutive(3) |

#### YAML 생성 규칙

**올바른 구조**:
```yaml
version: "1.0"
metadata:
  name: 전략명
strategy:
  id: snake_case_id          # 필수
  indicators: [...]
  entry: { conditions: [...] }
  exit: { conditions: [...] }
risk:                         # strategy 외부 (최상위)
  stop_loss: { enabled: true, percent: 3.0 }
```

**핵심 제약사항**:
- 조건 `value`는 **숫자 리터럴만** (변수 `$param_name` 불가)
- `risk` 블록은 strategy **외부**에 위치
- 지원 연산자: `greater_than`, `less_than`, `cross_above`, `cross_below`, `equals`, `not_equal`, `breaks`
  - ⚠️ `>=`, `<=` **미지원** — `greater_than: 값`으로 표현

#### MACD 골든크로스 예시

```yaml
indicators:
  - id: macd
    alias: macd
    params: { fast: 12, slow: 26, signal: 9 }

entry:
  conditions:
    - indicator: macd
      output: value          # MACD 라인
      operator: cross_above
      compare_to: macd       # 동일 alias
      compare_output: signal # 신호선과 비교
```

#### 입출력 형식

| 항목 | 설명 |
|------|------|
| 입력 | 프리셋 선택 or 커스텀 지표 + 진입/청산 조건식 + 리스크 파라미터 |
| 출력 | `.kis.yaml` 파일 (JSON or YAML) + Python 클래스 프리뷰 |

---

### 2️⃣ kis-backtester (성과 검증)

#### 백테스팅 엔진

- **기반**: Docker 기반 QuantConnect LEAN (`quantconnect/lean:latest`)
- **실행**: MCP 서버 (포트 3846)
- **지원 형식**: 10개 프리셋 + 커스텀 `.kis.yaml`
- **시간제한**: 최대 5분 내 자동 완료

#### 실행 워크플로우

1. **전략 선택** — 프리셋 ID or YAML 콘텐츠
2. **파라미터 설정** — 기본값: 1년 전 ~ 오늘 (커스텀 범위 가능)
3. **실행 및 대기** — `run_preset_backtest_tool` 또는 `run_backtest_tool` 호출
4. **결과 수집** — HTML 리포트 + 통계 JSON

#### 최적화 방식

| 방법 | 설명 |
|------|------|
| 파라미터 최적화 | Grid 또는 Random search. Target: Sharpe/수익률/최대낙폭/승률 |
| 배치 백테스트 | 여러 전략 동시 비교 (Sharpe/수익률/낙폭 기준) |
| 포트폴리오 분석 | 복수 종목 동시 실행하여 효과 분석 |

#### 핵심 지표 (JSON)

| 지표 | 설명 | 평가 기준 |
|------|------|----------|
| Total Return | 총 수익률 (%) | - |
| CAGR | 연평균 복리 수익률 | - |
| Sharpe Ratio | 위험 대비 수익 | 1.5+ 우수, 1.0~1.5 양호 |
| Max Drawdown | 최대 낙폭 (%) | < 10% 우수, < 20% 권장 |
| Win Rate | 승률 (%) | > 55% 양호 |
| Profit Factor | 손익비 | - |

#### 리포트 생성

- **포맷**: HTML 브라우저 자동 오픈
- **포함내용**: 차트, 거래 내역, 통계 지표

---

### 3️⃣ kis-order-executor (주문 실행)

#### 신호 생성

**반환값**: `BUY/SELL/HOLD` + 강도(0~1)

```
예: 삼성전자 → "RSI 28.3 < 30" 이유로 강도 0.85의 BUY 신호
```

#### 신호 강도별 처리

| 강도 범위 | 처리 방식 |
|----------|----------|
| 0.8 ~ 1.0 | 시장가 주문 실행 |
| 0.5 ~ 0.8 | 지정가 주문 (현재가 기준) |
| < 0.5 | 주문 자동 건너뜀 |

#### 안전장치

**실전(prod) 주문 전**:
1. 종목명, 수량, 예상금액, 현재 모드 명시
2. 사용자 승인 필수 (대화식)

**모의(vps)**: 바로 실행

#### 모의/실전 전환

```bash
/auth vps   # 모의투자 선택
/auth prod  # 실전투자 선택
```

주문 전마다 현재 모드 고지.

---

## 📡 API 클라이언트 (api_client.py)

### KISSession 클래스

**주요 속성**:
- `token`: JWT 토큰
- `mode`: "prod" or "vps"
- `_appkey`, `_appsecret`: API 자격증명
- `_acct`: 계좌번호
- `_base_url`: 모드별 기본 URL

**핵심 메서드**:

| 메서드 | 설명 | 반환 |
|--------|------|------|
| `get(api_path, tr_id, params)` | GET 요청 | JSON 응답 |
| `acct_masked` | 계좌번호 마스킹 | 뒷자리만 표시 |
| `balance()` | 예수금/잔고 | dict |
| `holdings()` | 보유종목 | list |
| `index()` | 코스피/코스닥 지수 | dict |

### 지원 API 엔드포인트

| 기능 | 엔드포인트 | TR_ID |
|------|---------|-------|
| 예수금/잔고 | `/uapi/domestic-stock/v1/trading/inquire-balance` | TTTC8434R |
| 지수 | `/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice` | FHKUP03500100 |

---

## 🔐 보안 메커니즘

### 1. Secret Guard 훅 (kis-secret-guard.sh.tmpl)

**실행 시점**: PreToolUse (도구 실행 전)

**대상 도구**: Bash, Write, Edit

**감지 패턴 (6가지)**:

| 패턴 | 예시 |
|------|------|
| `appkey = "값"` | API 키 |
| `appsecret = "값"` | API 시크릿 |
| `app_key/app_secret` | 변형 버전 |
| `authorization: Bearer 토큰` | 인증 헤더 |
| `approval_key = "값"` | 승인 키 |

**동작**:
- 대소문자 무관 검사 (`re.IGNORECASE`)
- 직접 차단 (마스킹 없음)
- stderr에 처음 60자 출력
- 사용자: "환경변수 또는 설정 파일을 사용하세요"

**예외**: `.gitignore`, `README`, `CLAUDE.md` (문서 변수명만 언급 시 생략)

### 2. Production Guard 훅 (kis-prod-guard.sh.tmpl)

**실행 시점**: PreToolUse

**대상**: Bash 도구에서 `/api/orders` 경로 포함 명령

**동작**:
1. auth.py 실행 → 현재 운영 모드(prod/vps) 판별
2. 프로덕션 모드 감지 시 즉시 차단
3. 메시지: "실전투자(prod) 주문 감지! 종목/수량/금액을 명시하고 확인을 받은 후 실행하세요"
4. 모든 시도를 타임스탬프와 함께 로깅

**특징**: 자동화된 주문 실행 전 **인간의 개입 강제**

### 3. 토큰 관리 (do_auth.py)

**REST 토큰**:
- 엔드포인트: `/oauth2/tokenP`
- 캐싱: 유효한 토큰 재사용 (API 호출 최소화)
- Fallback: 오늘 토큰 없으면 어제 파일 확인 (자정 전후 대응)

**WebSocket 승인**:
- 엔드포인트: `/oauth2/Approval`
- 반환: `approval_key` (실시간 데이터 연결용)

**모드 판별**: JWT `jti` 클레임 디코딩

---

## 🎯 5가지 Skills (자동 활성화)

| Skill | 트리거 문구 | 단계 | 기능 |
|-------|------------|------|------|
| **kis-strategy-builder** | "전략 만들어줘", "YAML 전략" | Step 1 | 10개 프리셋 or 커스텀 `.kis.yaml` 생성 |
| **kis-backtester** | "백테스트 해줘", "성과 분석" | Step 2 | 과거 성과 검증, 파라미터 최적화, HTML 리포트 |
| **kis-order-executor** | "신호 확인해줘", "실행해줘" | Step 3 | 신호 생성(BUY/SELL/HOLD) → 모의/실전 주문 |
| **kis-team** | "다 해줘", "풀파이프라인" | Step 1→2→3 | 3단계 전체 자동 오케스트레이션 |
| **kis-cs** | 오류 문의 | - | 고객 서비스 지원 |

---

## 📝 3가지 커맨드

| 커맨드 | 용도 | 입력 예시 |
|--------|------|----------|
| `/auth` | "인증 상태 확인·모의/실전 인증·WebSocket 인증" | `/auth vps`, `/auth prod` |
| `/my-status` | "잔고·보유종목·지수 조회" | `/my-status`, `/my-status 잔고` |
| `/kis-help` | "도움말 및 키워드 검색" | `/kis-help EGW00201` |

---

## 🔧 Claude 에이전트 설정 프로세스

### 설정 자동화 (11단계)

```bash
npx @koreainvestment/kis-quant-plugin init --agent claude --force
```

**핵심 단계**:

1-2. 플러그인 파일 확인 → 환경 진단
3-4. Python 3.11+, Node.js, Docker 확인
5-9. 의존성 설치 + 서버 설정 (MCP 포트 3846)
10-11. 인증 및 최종 검증

### 필수 환경변수

**backtester/.env**:
| 변수 | 기본값 | 용도 |
|------|--------|------|
| `MCP_PORT` | 3846 | MCP 서버 포트 |
| `MCP_HOST` | 127.0.0.1 | MCP 서버 호스트 |

**strategy_builder/frontend/.env.local**:
| 변수 | 값 | 용도 |
|------|-----|------|
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | 실시간 호가 필수 |

**인증** (`~/KIS/config/kis_devlp.yaml`):
- 모의투자 최소: `paper_app`, `paper_sec`

### 보안 원칙

- 토큰, 앱키, 시크릿은 절대 출력 금지
- `kis_devlp.yaml`을 직접 읽거나 쓰지 않음

---

## 🚀 우리 stock-manager와의 통합 가능성

### 직접 활용할 수 있는 부분

#### 1. API 클라이언트 (api_client.py)

```python
from shared.scripts.api_client import KISSession

# KIS REST API 래퍼
session = KISSession(mode="vps")  # or "prod"
balance = session.balance()
holdings = session.holdings()
index = session.index()
```

**활용 시나리오**:
- 우리 `wrapper.py`에서 토큰 캐싱 로직 개선
- 계좌 정보 조회 캡슐화

#### 2. 인증 프로세스 (do_auth.py)

- **토큰 캐싱 전략**: 유효한 토큰 재사용 + Fallback (자정 전후)
- **WebSocket 승인**: `approval_key` 발급 프로세스
- **모드 판별**: JWT `jti` 클레임 디코딩 기법

**활용 시나리오**:
- 우리 `routers/_kis_auth.py`의 토큰 관리 개선
- WebSocket 연결 시 approval_key 활용

#### 3. 기술지표 구현 (83개 표준화)

**우리가 현재 구현한 지표**:
- MACD, RSI(Wilder), Stochastic, 볼린저밴드, MA5/20/60

**KIS AI Extensions에서 추가 가능**:
- ADX, ROC, CCI, Williams%R, MFI, IBS, VWAP, OBV
- 66종 캔들패턴 (hammer, doji, engulfing 등)

**활용 시나리오**:
- `stock/advisory_fetcher.py`에 표준 지표 추가
- TechnicalPanel에 지표 선택 UI 확장

#### 4. 전략 YAML 형식 (표준화)

```yaml
version: "1.0"
metadata:
  name: 전략명
strategy:
  id: snake_case_id
  indicators: [...]
  entry: { conditions: [...] }
  exit: { conditions: [...] }
risk:
  stop_loss: { enabled: true, percent: 3.0 }
```

**활용 시나리오**:
- 우리 advisory_service에 custom strategy 저장 (미래 확장)
- 백테스팅 기능 추가 시 YAML 형식 도입

#### 5. 보안 훅 패턴

**우리가 참고할 사항**:
- Secret Guard: 시크릿 감지 패턴 (6가지)
- Production Guard: 실전 주문 전 사용자 승인 강제
- MCP 로깅: 거래 내역 추적

**활용 시나리오**:
- 우리 hook.json에 유사한 보안 검사 추가
- 실전 주문 전 사용자 확인 로직 강화

### 직접 활용 불가능한 부분

#### 1. QuantConnect LEAN 백테스팅 엔진
- 별도 Docker 환경 필요
- 우리 FastAPI는 별도 로직 구현 필요

#### 2. 웹 기반 전략 빌더 UI (localhost:3000/builder)
- Next.js 기반 별도 프론트엔드
- 우리 React SPA와 독립적

#### 3. 신호 강도(0~1) 계산 알고리즘
- KIS AI Extensions 내부 구현 (공개되지 않음)
- 우리 TechnicalPanel과 다른 방식

---

## 📊 기술 스택 요약

| 계층 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI/Flask, MCP 서버 |
| 프론트엔드 | Next.js, Tailwind CSS |
| 백테스팅 | Docker, QuantConnect LEAN |
| 인증 | KIS OpenAPI (OAuth2 + JWT) |
| 보안 | Pre-commit Hook (시크릿 감지) |
| CLI | Node.js 18+ (bin/cli.js) |

---

## 🎓 KIS AI Extensions가 제공하는 가치

1. **표준화된 전략 설계** — 83개 지표 + 10개 프리셋
2. **백테스팅 엔진** — QuantConnect Lean (산업 표준)
3. **신호 기반 주문 실행** — 강도(0~1) 기반 위치결정
4. **다중 에이전트 지원** — Claude/Cursor/Codex/Gemini
5. **엔드-투-엔드 보안** — Secret Guard + Production Guard

---

## 🔗 참고 자료

- **GitHub**: https://github.com/koreainvestment/kis-ai-extensions
- **MCP 서버**: http://127.0.0.1:3846 (로컬)
- **설치**: `npx @koreainvestment/kis-quant-plugin init --agent claude`

