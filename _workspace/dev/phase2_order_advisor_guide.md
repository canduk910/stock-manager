# Phase 2 — OrderAdvisor 사전 가이드 메모

**수신**: 2026-04-16 OrderAdvisor
**용도**: Phase 2 착수 시 safety_grade.py / advisory_service.py / 응답 JSON 스키마 구현에 참조

---

## Phase 1 반영 승인

OrderAdvisor가 Phase 1 추가 반영(포지션 계산식/매수 불가 6가지/규칙 E/F/G) 모두 의도대로 반영 확인. 토큰 여유 6710은 Phase 2 추가 섹션 투입에도 안정적.

---

## Phase 2 구현 가이드 (원문 수신)

### 2-4 `services/safety_grade.py` 구현

#### GRADE_FACTOR 상수
```python
GRADE_FACTOR = {"A": 1.0, "B+": 0.75, "B": 0.5, "C": 0.0, "D": 0.0}
```

#### compute_position_size() 신규 헬퍼 (권장)
```python
def compute_position_size(
    grade: str,
    regime_single_cap_pct: float,  # 체제별 종목당 한도 (5/4/3/0)
    total_portfolio: float,
    cash_available: float,
    entry_price: float,
) -> dict:
    factor = GRADE_FACTOR.get(grade, 0.0)
    if factor == 0 or entry_price <= 0:
        return {
            "qty": 0,
            "amount": 0,
            "position_pct": 0,
            "reason": "grade_or_price_invalid",
        }
    target_pct = regime_single_cap_pct * factor / 100  # 예: 4% × 0.75 = 0.03
    max_amount = total_portfolio * target_pct
    available = min(max_amount, cash_available)
    raw_qty = int(available // entry_price)  # floor
    return {
        "qty": raw_qty,
        "amount": raw_qty * entry_price,
        "position_pct": target_pct * 100,
        "grade_factor": factor,
    }
```

#### 분할매수 50/30/20 주의사항
- **총 수량을 먼저 계산한 후** 3개 주문으로 분할 (×0.5, ×0.3, ×0.2 각각 floor)
- 반올림 오차 누적 방지: **3차 = total_qty - tranche_1 - tranche_2** 로 계산
- 1차 지정가 = entry_price (BB 하단/지지선 기반)
- 2차/3차 지정가 = 1차 × (1 − 3%), 1차 × (1 − 6%) — 추후 OrderAdvisor 재자문 여지 있음

#### `valid_entry: bool` 필드 포함 권장
- safety_grade.py에서 dict 반환 시점에 `valid_entry: bool` 필드 포함
- C/D 등급은 safety_grade 레이어에서 `valid_entry=False` 반환 → advisory_service 후처리 단순화
- advisory_service 레이어에서 중복 판단할 필요 없음

---

### 2-7 응답 JSON 스펙 확장 — 포지션가이드 섹션

```json
"포지션가이드": {
  "등급팩터": 0.75,
  "체제종목당한도_pct": 4.0,
  "최종포지션_pct": 3.0,
  "진입가_1차": 123000,
  "손절가": 113160,     // entry × (1 - 0.10)  ← B+ 등급
  "익절가": 145000,     // graham_number
  "손절폭_pct": -10.0,
  "risk_reward": 2.23,
  "분할매수": [
    {"차수": 1, "비율_pct": 50, "가격": 123000},
    {"차수": 2, "비율_pct": 30, "가격": 119310},
    {"차수": 3, "비율_pct": 20, "가격": 115620}
  ],
  "recommendation": "HOLD | ENTER | SKIP"
}
```

#### `recommendation` 필드 추가 권장
- `risk_reward < 2.0` 시 보류 처리 → `recommendation: "HOLD"` 또는 `"SKIP"`
- `valid_entry=False` 또는 C/D 등급 → `"SKIP"`
- 정상 진입 가능 → `"ENTER"`

---

### Value Trap 경고 시 포지션 가이드 처리

`Value_Trap_경고=true` 이면:
- `포지션가이드.최종포지션_pct = 0` 강제
- `qty = 0` 강제
- `reasoning`에 "Value Trap 근거로 진입 보류" 명시 요구
- `recommendation: "SKIP"`

Phase 2-4 safety_grade.py에서 compute_grade_7point() 결과와 Value_Trap_경고 플래그를 교차 체크하는 함수 필요.

---

### 해외 종목 주의

- USD 기준 entry_price / stop_loss / take_profit 그대로 사용 (환산 금지)
- KRW 포트폴리오 총액 × 환율로 available_capital 산정 시 **환율 스냅샷 시점 기록** (변동성 고려)
- safety_grade.py 레벨에서는 통화 무관 (입력 entry_price와 일관된 통화로만 계산)

---

## 구현 우선순위 (Phase 2 착수 시)

1. **2-4 신규** `services/safety_grade.py` — `GRADE_FACTOR`, `compute_grade_7point()`, `compute_composite_score()`, `compute_regime_alignment()`, `compute_position_size()` (OrderAdvisor 가이드 반영)
2. **2-5 수정** `advisory_service._collect_fundamental_*()` — valuation_stats + quarterly 추가
3. **2-6 수정** `advisory_service._build_prompt()` — 4개 신규 섹션 추가 (PER/PBR 히스토리, 분기 실적, 거래량·변동성, 7점 등급 사전계산)
4. **2-7 수정** `advisory_service._build_prompt()` JSON schema 블록 — `포지션가이드` 에 `등급팩터/체제종목당한도/최종포지션_pct/recommendation` 필드 추가
5. **2-1 수정** `stock/indicators.py` — volume_signal, bb_position, volume_5d_avg/20d_avg 추가
6. **2-2 신규** `stock/advisory_fetcher.fetch_valuation_stats()`
7. **2-3 신규** `stock/dart_fin.fetch_quarterly_financials()` + `stock/yf_client.fetch_quarterly_financials_yf()`
8. **2-8 수정** `portfolio_advisor_service._build_context()` — `portfolio_grade_weighted_avg`, `grade_distribution`, `regime_alignment_score` 추가

---

## Phase 2 착수 시 추가 자문 예상 질문

| 질문 | 대상 | 답변(사전 획득) |
|------|------|----------------|
| grade_factor C/D=0 규칙을 어느 레이어에서 강제? | OrderAdvisor | safety_grade.py에서 `valid_entry: bool` 필드 포함 권장 |
| risk_reward < 2.0 시 처리 흐름? | OrderAdvisor | `포지션가이드.recommendation: "HOLD"/"ENTER"/"SKIP"` 필드 추가 |
| 2차/3차 분할 가격 계산 공식? | OrderAdvisor | 1차 × (1 − 3%), 1차 × (1 − 6%) 가이드 — 실제 착수 시 재자문 여지 |
| 해외 종목 USD→KRW 환산 시점? | OrderAdvisor | 환율 스냅샷 시점 기록 필수 |
| 해외 매출 CAGR USD vs KRW 기준? | MarginAnalyst | 아직 자문 대기 — Phase 2-4 착수 시 재자문 |
