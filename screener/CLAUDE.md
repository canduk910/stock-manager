# screener/ — 스크리너 패키지

CLI와 API 라우터 양쪽에서 공용으로 사용한다.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `service.py` | CLI 독립 비즈니스 로직. `normalize_date`, `parse_sort_spec`, `apply_filters`, `sort_stocks`. `ScreenerValidationError` 예외. |
| `cli.py` | Click CLI. `service.py`를 호출하는 얇은 래퍼. `ScreenerValidationError` → `click.BadParameter` 변환. |
| `krx.py` | pykrx로 전종목 PER/PBR/EPS/BPS/시가총액 수집. ROE = EPS/BPS × 100. |
| `dart.py` | OpenDart API. `pblntf_ty=A` 단일 쿼리로 정기보고서 조회. `rcept_no` 기준 중복 제거. |
| `display.py` | Rich 테이블 출력 + CSV 내보내기. 시가총액 억/조 포맷팅. |
| `cache.py` | SQLite 캐시 (`screener_cache.db`). 동일 날짜 재조회 시 API 호출 생략. |

## 핵심 규칙

### krx.py — 거래일 자동 소급
- `_find_latest_trading_day()`: Step1=weekday() 체크(API 없음), Step2=pykrx API로 공휴일 감지.
- `get_all_stocks()` 반환타입: `tuple[list, str]` (실제 거래일 문자열 포함).

### dart.py — 캐시 주의
- **`end_date < today`인 경우만 캐시 사용**. 오늘 이상 날짜 포함 범위는 항상 DART API 직접 호출.
- 이유: 당일 오전 빈 결과가 캐시되면 이후 제출 공시 미노출 (골프존 3/19 사례).

### cache.py
- TTL 없는 영구 캐시 (날짜키 기반). 캐시 파일: `screener_cache.db` (프로젝트 루트).

> 함수 상세 → `docs/SCREENER_PACKAGE.md`
