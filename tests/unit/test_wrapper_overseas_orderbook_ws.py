"""REQ-WRAPPER-03: 해외 호가 WebSocket 메시지 파서 + 구독/해지 메서드 단위 테스트.

- parse_overseas_orderbook(raw): asks[10]/bids[10]/total_ask_volume/total_bid_volume 반환
- 응답 단계 부족 시 받은 단계만 반환(10단계 미만 허용)
- 비정상 입력은 None
- KoreaInvestmentWS.subscribe_overseas_orderbook / unsubscribe_overseas_orderbook
  → tr_key_list 토픽 등록/해지 (rsym = D{exchange3}{symbol})
"""

from __future__ import annotations

import pytest

from wrapper import KoreaInvestmentWS, parse_overseas_orderbook


# ── 메시지 파서 ─────────────────────────────────────────────────────────────


def _build_raw_orderbook_payload(rsym: str = "DNASAAPL", n_levels: int = 10) -> str:
    """KIS 해외 호가 가이드 기반 ^ 구분 페이로드 빌더.

    [0]=rsym, [1]=영업일, [2]=현지영업일, [3]=현지일자, [4]=현지시간, [5]=한국일자, [6]=한국시간
    [7..16]=매도호가1~10, [17..26]=매수호가1~10
    [27..36]=매도잔량1~10, [37..46]=매수잔량1~10
    [47]=총매도잔량, [48]=총매수잔량
    """
    fields = [rsym, "20260508", "20260508", "20260508", "150000", "20260509", "040000"]
    # 매도호가 (오름차순 - 최우선이 가장 낮음)
    for i in range(n_levels):
        fields.append(f"{200.10 + i * 0.10:.2f}")
    for _ in range(10 - n_levels):
        fields.append("")
    # 매수호가 (내림차순 - 최우선이 가장 높음)
    for i in range(n_levels):
        fields.append(f"{199.90 - i * 0.10:.2f}")
    for _ in range(10 - n_levels):
        fields.append("")
    # 매도잔량
    for i in range(n_levels):
        fields.append(str(100 + i * 10))
    for _ in range(10 - n_levels):
        fields.append("")
    # 매수잔량
    for i in range(n_levels):
        fields.append(str(120 + i * 10))
    for _ in range(10 - n_levels):
        fields.append("")
    fields.append("5500")  # 총매도잔량
    fields.append("6700")  # 총매수잔량
    return "^".join(fields)


def test_parse_overseas_orderbook_full_10_levels():
    raw = _build_raw_orderbook_payload(n_levels=10)
    result = parse_overseas_orderbook(raw)
    assert result is not None
    assert result["symbol"] == "AAPL"
    assert result["exchange"] == "NAS"
    assert len(result["asks"]) == 10
    assert len(result["bids"]) == 10
    # 매도1호가 200.10
    assert result["asks"][0]["price"] == pytest.approx(200.10)
    assert result["asks"][0]["volume"] == 100
    # 매수1호가 199.90
    assert result["bids"][0]["price"] == pytest.approx(199.90)
    assert result["bids"][0]["volume"] == 120
    assert result["total_ask_volume"] == 5500
    assert result["total_bid_volume"] == 6700


def test_parse_overseas_orderbook_partial_levels():
    """10단계 미만 응답(빈 가격/잔량) → 빈 단계 제외하고 받은 단계만 반환."""
    raw = _build_raw_orderbook_payload(n_levels=3)
    result = parse_overseas_orderbook(raw)
    assert result is not None
    # 0 가격 단계는 제외
    assert len(result["asks"]) == 3
    assert len(result["bids"]) == 3
    assert result["asks"][0]["price"] == pytest.approx(200.10)
    assert result["asks"][2]["price"] == pytest.approx(200.30)


def test_parse_overseas_orderbook_invalid_input_none():
    """필드 부족 → None."""
    assert parse_overseas_orderbook("") is None
    assert parse_overseas_orderbook("DNASAAPL^20260508") is None


def test_parse_overseas_orderbook_rsym_nys():
    """NYS 거래소 인식."""
    raw = _build_raw_orderbook_payload(rsym="DNYSMSFT", n_levels=5)
    result = parse_overseas_orderbook(raw)
    assert result is not None
    assert result["symbol"] == "MSFT"
    assert result["exchange"] == "NYS"


def test_parse_overseas_orderbook_rsym_realtime_prefix_r():
    """rsym prefix R(지연) 도 처리되어야 함 (실시간 D 외)."""
    raw = _build_raw_orderbook_payload(rsym="RNASTSLA", n_levels=2)
    result = parse_overseas_orderbook(raw)
    assert result is not None
    assert result["symbol"] == "TSLA"
    assert result["exchange"] == "NAS"


# ── KoreaInvestmentWS 구독/해지 ─────────────────────────────────────────────


def _make_ws() -> KoreaInvestmentWS:
    """tr_id_list/tr_key_list 비어있는 인스턴스 생성 (Process __init__ 호출)."""
    return KoreaInvestmentWS(
        api_key="K",
        api_secret="S",
        tr_id_list=[],
        tr_key_list=[],
        user_id=None,
    )


def test_subscribe_overseas_orderbook_adds_topic():
    ws = _make_ws()
    ws.subscribe_overseas_orderbook("DNASAAPL")
    assert "HDFSASP0" in ws.tr_id_list
    assert "DNASAAPL" in ws.tr_key_list


def test_subscribe_overseas_orderbook_dedupe():
    """중복 호출 시 토픽이 한 번만 등록."""
    ws = _make_ws()
    ws.subscribe_overseas_orderbook("DNASAAPL")
    ws.subscribe_overseas_orderbook("DNASAAPL")
    assert ws.tr_id_list.count("HDFSASP0") == 1
    assert ws.tr_key_list.count("DNASAAPL") == 1


def test_unsubscribe_overseas_orderbook_removes_topic():
    ws = _make_ws()
    ws.subscribe_overseas_orderbook("DNASAAPL")
    ws.subscribe_overseas_orderbook("DNYSMSFT")
    ws.unsubscribe_overseas_orderbook("DNASAAPL")
    assert "DNASAAPL" not in ws.tr_key_list
    assert "DNYSMSFT" in ws.tr_key_list


def test_unsubscribe_unknown_safe_noop():
    ws = _make_ws()
    # 미등록 키 해지는 예외 없이 통과
    ws.unsubscribe_overseas_orderbook("DNASZZZZ")
