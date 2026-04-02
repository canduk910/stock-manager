---
name: portfolio-check
description: "현재 포트폴리오 상태 확인 + 포지션 사이징 제약 계산. 보유 잔고, 예수금, 매수가능금액, 미체결주문을 조회하여 신규 매수 여력과 포지션 한도를 산출한다. 잔고 확인, 매수 가능, 포트폴리오 상태, 투자 여력 확인 시 사용."
---

# 포트폴리오 상태 확인

현재 보유 잔고와 예수금을 확인하고, Graham 보수적 포지션 사이징 제약을 계산한다.

## API 호출

### 1단계: 잔고 조회

```bash
curl -s http://localhost:8000/api/balance
```

응답에서 추출:
- `total_evaluation` — 총 평가금액 (보유주식 + 예수금)
- `deposit_domestic` — 국내 예수금
- `deposit_overseas_krw` — 해외 예수금(원화 환산)
- `stock_list` — 국내 보유종목 리스트 (code, name, quantity, eval_amount, profit_rate)
- `overseas_list` — 해외 보유종목 리스트
- `futures_list` — 선물옵션 보유

### 2단계: 매수가능금액 조회

```bash
curl -s "http://localhost:8000/api/order/buyable?market=KR&symbol={symbol}&price={price}"
```

- `symbol`: 매수 대상 종목코드 (필요 시)
- `price`: 예상 매수가 (지정가)
- 응답: 매수 가능 금액 / 매수 가능 수량

### 3단계: 미체결주문 확인 (중복 방지)

```bash
curl -s "http://localhost:8000/api/order/open?market=KR"
```

동일 종목 미체결 매수 주문이 있으면 추가 매수 추천을 하지 않는다.

## 포지션 사이징 계산

### Graham 보수적 규칙

```
total_portfolio = total_evaluation  # 총 평가금액
current_stock_ratio = stock_eval / total_portfolio  # 현재 주식 비중
available_invest = total_portfolio * max_invest_pct - stock_eval  # 추가 투자 가능 금액
max_per_stock = total_portfolio * max_position_pct  # 종목당 최대 금액
```

체제별 한도:

| 체제 | max_invest_pct | max_position_pct | 현금 버퍼 |
|------|---------------|-----------------|---------|
| accumulation | 75% | 5% | 25%+ |
| selective | 65% | 4% | 35%+ |
| cautious | 50% | 3% | 50%+ |
| defensive | 0% | 0% | 100% |

### 기존 보유 종목 체크

후보 종목이 이미 포트폴리오에 있으면:
- 현재 보유비중 확인 (`eval_amount / total_portfolio`)
- max_position_pct 미만이면 추가 매수 가능 수량 계산
- 이미 한도 도달이면 "추가 매수 불가" 표기

## 출력 형식

`_workspace/04_portfolio_state.json`에 저장:

```json
{
  "total_evaluation": 50000000,
  "deposit": 15000000,
  "stock_eval": 35000000,
  "current_stock_ratio": 70.0,
  "regime": "selective",
  "max_invest_pct": 65,
  "max_position_pct": 4,
  "available_for_new_invest": -2500000,
  "available_per_stock": 2000000,
  "existing_holdings": {
    "005930": {"name": "삼성전자", "quantity": 10, "eval_amount": 550000, "weight_pct": 1.1},
    "000660": {"name": "SK하이닉스", "quantity": 5, "eval_amount": 750000, "weight_pct": 1.5}
  },
  "open_orders": [
    {"code": "035720", "side": "buy", "quantity": 10, "price": 45000}
  ],
  "position_limits": {
    "005930": {"current_pct": 1.1, "max_pct": 4.0, "remaining_amount": 1450000},
    "000660": {"current_pct": 1.5, "max_pct": 4.0, "remaining_amount": 1250000}
  },
  "kis_available": true,
  "timestamp": "2026-04-02T15:45:00+09:00"
}
```

## 주의사항

- KIS 키 미설정 시 잔고/매수력 조회 불가 → `kis_available: false`로 표기하고, 분석 결과만 제공(주문 추천 생략).
- 해외 종목은 `market=US`로 별도 매수가능금액 조회 필요.
- `available_for_new_invest`가 음수이면 현재 투자비중이 한도를 초과한 상태 — 신규 매수 대신 리밸런싱 권고.