# 리팩토링 계획 (도메인 자문 반영)

## 실행 항목

### [실행] HIGH-1: advisory_service.py 프롬프트/챗 분리 (1861줄 → 코어 + 2모듈)
- **신규 `services/advisory_prompt.py`**: 순수 프롬프트 빌더 이동
  - `_build_macro_section`, `_build_strategy_signal_section`, `_format_cycle_regime_rule`, `_build_system_prompt`, `_format_money`, `_build_consensus_section`, `_build_prompt`, `_fmt`, `_parse_report`
  - 의존 import 동반: `_REGIME_MARGIN`(macro_regime.REGIME_PARAMS 파생), `is_domestic`, logging
- **신규 `services/advisory_chat.py`**: 챗봇 이동
  - `_trim_chat_history`, `_validate_chat_messages`, `chat_with_report`
  - 의존: ai_gateway, advisory_store, exceptions
- **advisory_service.py**: re-export로 기존 import 경로 100% 보존
  - `from services.advisory_prompt import _build_prompt, _build_system_prompt, _parse_report, ...`
  - `from services.advisory_chat import chat_with_report`
  - `_calc_graham_number`는 advisory_service에 **잔류**(pipeline_service가 직접 import, 또한 _build_prompt가 호출 가능)
- **도메인 제약 (margin-analyst)**:
  - 문자열 리터럴 1글자도 수정 금지 (pure cut-paste). 7점 등급/손절/Value Trap 텍스트 = safety_grade.py와 의도적 3중 일관성 → 제거·상수화 금지.
  - 공개 3함수(refresh_stock_data/generate_ai_report/chat_with_report) advisory_service 네임스페이스 유지.
- **rollback**: 신규 파일 삭제 + re-export 라인 제거 → 원본 함수 복원. git stash 가능.
- **검증**: `python -c "import main"` + `from services.advisory_service import refresh_stock_data, _calc_graham_number, chat_with_report, _build_prompt, _parse_report` + `from services.pipeline_service import *` + `pytest tests/unit/`.

## 실행하지 않는 항목 + 사유

- **HIGH-2 macro_fetcher credit 분리**: macro-sentinel 자문 OK_BUT_DEFER. 동작상 안전하나 소비처 다수(macro_service/advisory/portfolio/order_us/pipeline 모듈 속성 접근) + `_KR_SECTOR_ETFS`/oas_history_store 결합으로 re-export 누락 위험. HIGH-1 검증 후 여력 시 후속 사이클.
- **MEDIUM-1 routers→stock 직접 import**: ROI 낮음. 다수가 얇은 패스스루(검색/심볼맵/CRUD), 서비스 신설은 과잉 추상화. 신규 코드 권고로만 기록.
- **MEDIUM-2 tax/dart_fin/yf_client 분할**: 도메인 응집도 높음(FIFO/계정명 매핑/yfinance 어댑터). 분할 시 도메인 위험. 별도 사이클.
- **LOW-1 except 587건**: 대부분 의도적(asyncio/Queue). 일괄 변경 위험. 보류.

## 위험 관리
- HIGH-1만 단독 실행 → 의존 항목 없음, 실패 시 단독 revert.
- 순환 의존 위험: advisory_prompt가 advisory_service를 import하지 않도록(단방향). 빌더는 인자로만 데이터 받음 → 순환 없음 확인 필요.
- 공개 API(엔드포인트/응답 shape/에러코드) 무변경 — 내부 모듈 재배치만.
