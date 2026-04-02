---
name: order-recommend
description: "주문 추천 생성 + 예약주문 등록 보조. 분석 결과를 바탕으로 지정가 매수가, 수량, 손절가, 익절가를 산출하고 예약주문 등록을 지원한다. 자동 주문 실행은 하지 않으며 사용자 승인을 필수로 한다. 매수 추천, 주문 생성, 예약주문, 포지션 진입 요청 시 사용."
---

# 주문 추천 생성

분석 결과를 구체적인 매수 주문 파라미터로 변환한다. **자동 주문 실행 없음** — 사용자 승인 후에만 예약주문을 등록한다.

## 입력

- `_workspace/03_analyses/{code}_analysis.json` — 종목별 심층 분석 결과
- `_workspace/04_portfolio_state.json` — 포트폴리오 상태 + 포지션 한도
- `_workspace/01_macro_assessment.json` — 매크로 체제

## 주문 파라미터 산출

### 1. 매수 추천 자격 확인

다음 조건을 **모두** 충족해야 매수 추천:
- 안전마진 등급 B+ 이상 (fundamental_score ≥ 20)
- 할인율 ≥ recommended_margin_threshold (매크로 체제 연동)
- 기술적 진입 시그널 ≠ "unfavorable" (RSI > 70이면 보류)
- 해당 종목 미체결 매수주문 없음
- 포지션 한도 미도달

### 2. 지정가 산출

```
entry_price = min(current_price, target_entry_price)
```

target_entry_price 결정 로직:
- BB 하단 근처: BB lower band 가격
- 최근 지지선: 일봉 차트의 최근 저점
- Graham Number 대비 목표 할인율: `graham_number × (1 - target_discount/100)`
- 세 값 중 현재가에 가장 가까운 값 선택 (너무 낮으면 체결 불가)

### 3. 수량 산출

```
max_amount = min(available_per_stock, remaining_amount_for_stock)
quantity = floor(max_amount / entry_price)
actual_amount = quantity * entry_price
actual_position_pct = actual_amount / total_evaluation * 100
```

안전마진 등급에 따른 수량 조절:
- A (강력매수): 최대 수량
- B+: 최대 수량의 75%
- B: 최대 수량의 50%

### 4. 손절/익절 설정

```
stop_loss = entry_price × (1 - stop_pct/100)
take_profit = graham_number  # 내재가치 도달 시 익절
risk_reward = (take_profit - entry_price) / (entry_price - stop_loss)
```

| 등급 | stop_pct | 비고 |
|------|---------|------|
| A | 15% | 확신 높아 넓은 손절폭 허용 |
| B+ | 12% | |
| B | 10% | |

risk_reward < 2.0이면 매수 보류 (리스크 대비 보상 부족).

## 예약주문 등록 (사용자 승인 후)

```bash
curl -s -X POST http://localhost:8000/api/order/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "005930",
    "symbol_name": "삼성전자",
    "market": "KR",
    "side": "buy",
    "order_type": "00",
    "price": 54000,
    "quantity": 10,
    "condition_type": "price_below",
    "condition_value": 54000,
    "memo": "Graham 안전마진 30.9% — 지정가 매수"
  }'
```

- `order_type`: "00" = 지정가 (Graham 투자는 항상 지정가)
- `condition_type`: "price_below" = 가격 이하 도달 시 자동 발송
- 예약주문 스케줄러가 20초 간격으로 가격 체크 후 자동 발송

## 출력 형식

`_workspace/05_recommendations.json`에 저장:

```json
{
  "regime": "selective",
  "total_recommended_amount": 3200000,
  "recommendations": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "market": "KR",
      "action": "BUY_LIMIT",
      "entry_price": 54000,
      "quantity": 37,
      "amount": 1998000,
      "position_pct": 4.0,
      "stop_loss": 45900,
      "take_profit": 72000,
      "risk_reward": 3.3,
      "safety_grade": "A",
      "discount_rate": 30.9,
      "confidence": "high",
      "reasoning": [
        "Graham Number 72,000원 대비 30.9% 할인",
        "부채비율 35% — 재무 우량",
        "기술적 진입: RSI 35 + MACD 골든크로스"
      ],
      "reservation_ready": true,
      "reservation_params": {
        "condition_type": "price_below",
        "condition_value": 54000
      }
    }
  ],
  "skipped": [
    {"code": "035720", "name": "카카오", "reason": "할인율 15% — 안전마진 기준 25% 미달"}
  ],
  "timestamp": "2026-04-02T15:50:00+09:00"
}
```

## 핵심 원칙

1. **자동 주문 절대 금지**: 모든 주문은 사용자의 명시적 승인 후에만 실행한다. 추천서를 생성하되 `POST /api/order/place`를 자동으로 호출하지 않는다.
2. **Graham 보수적 원칙**: 의심스러우면 매수하지 않는다. 확실한 안전마진이 있을 때만 추천한다.
3. **분산 투자**: 단일 종목 5% 초과 금지. 집중 투자는 Graham 철학에 반한다.
4. **현금 보존**: 전체 자산의 25% 이상은 항상 현금으로 유지한다.
