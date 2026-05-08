"""REQ-INT-03: KIS 실키 해외시세 통합 테스트.

실 KIS 키로 다음 3개 응답을 검증한다:
  1. HHDFS76200100 — 10단계 호가 REST (``stock.kis_overseas_client.get_kis_orderbook``)
  2. HHDFS76200200 — 현재가 상세 REST (``stock.kis_overseas_client.get_kis_price_detail``)
  3. HDFSASP0     — 호가 WS (``services.quote_overseas.KISOverseasOrderbookWS``)

실행 방법:
    KIS_LIVE_TEST=1 pytest tests/integration/test_kis_overseas_live.py -v
                              -m live --no-header

CI(KIS_LIVE_TEST 미설정) 환경에서는 모든 테스트가 자동 skip — 회귀 0.

자세한 운영 가이드: ``_workspace/dev/05_live_test_runbook.md``
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os

import pytest


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.getenv("KIS_LIVE_TEST"),
        reason="KIS_LIVE_TEST 환경변수 미설정 — 실키 테스트 skip",
    ),
]


# ── 1. HHDFS76200100 (REST 호가) ─────────────────────────────────────────────


def test_live_kis_orderbook_rest_aapl_returns_non_empty_levels():
    """AAPL @ NAS 호가 REST 호출이 실제 호가 단계를 반환하는지 검증.

    응답 필드명이 가이드 추정과 다른 경우 실패 메시지에서 명확히 지적.
    """
    from stock.kis_overseas_client import get_kis_orderbook

    ob = get_kis_orderbook("AAPL")
    assert ob is not None, (
        "[FAIL] get_kis_orderbook(AAPL) 가 None 반환. 원인 후보:\n"
        "  - KIS 키 미설정/만료 (.env 또는 SSM 확인)\n"
        "  - HHDFS76200100 응답 rt_cd != '0'\n"
        "  - _normalize_orderbook_response 가 빈 dict 반환 (필드명 불일치 — "
        "kis_overseas_client.py:_normalize_orderbook_response의 'pask{i}'/'vask{i}'/'pbid{i}'/'vbid{i}' "
        "키를 실 응답 필드와 비교 필요. KIS Developer Portal HHDFS76200100 명세 참조)."
    )
    assert isinstance(ob.get("asks"), list) and len(ob["asks"]) > 0, \
        f"[FAIL] asks 배열 비어있음. 받은 키: {list(ob.keys())}. " \
        f"_normalize_orderbook_response의 pask/vask 매핑 점검 필요."
    assert isinstance(ob.get("bids"), list) and len(ob["bids"]) > 0, \
        f"[FAIL] bids 배열 비어있음. _normalize의 pbid/vbid 매핑 점검 필요."
    # 모든 가격이 양수
    for level in ob["asks"]:
        assert level["price"] > 0, f"asks price <= 0: {level}"
    for level in ob["bids"]:
        assert level["price"] > 0, f"bids price <= 0: {level}"


# ── 2. HHDFS76200200 (REST 상세) ──────────────────────────────────────────────


def test_live_kis_price_detail_rest_aapl_returns_full_fields():
    """AAPL 현재가 상세 REST가 open/high/low/prev_close/52w 필드를 모두 채우는지."""
    from stock.kis_overseas_client import get_kis_price_detail

    detail = get_kis_price_detail("AAPL")
    assert detail is not None, (
        "[FAIL] get_kis_price_detail(AAPL) 가 None 반환. "
        "_normalize_price_detail_response의 'last' 키 매핑 점검 필요."
    )
    # 핵심 필드 모두 양수
    must_positive = ["open", "high", "low", "last", "prev_close", "high_52w", "low_52w"]
    missing_or_zero = []
    for k in must_positive:
        v = detail.get(k)
        if v is None or v <= 0:
            missing_or_zero.append((k, v))
    assert not missing_or_zero, (
        f"[FAIL] 필드 누락/0: {missing_or_zero}. "
        f"받은 dict: {detail}. KIS HHDFS76200200 응답 키 'open'/'high'/'low'/'base'/'h52p'/'l52p' "
        f"실제 필드명과 비교 필요(_normalize_price_detail_response 참조)."
    )


# ── 3. HDFSASP0 (WS 호가) ─────────────────────────────────────────────────────


def _is_us_market_open_now() -> bool:
    """ET 09:30~16:00 평일 + 공휴일 제외(보수적: 단순 시간만)."""
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    # ET = UTC-5 (DST 미고려 — 보수적, 시간외에는 skip 처리)
    et = now_utc - dt.timedelta(hours=5)
    if et.weekday() >= 5:
        return False
    open_t = et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = et.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_t <= et <= close_t


@pytest.mark.skipif(
    not _is_us_market_open_now(),
    reason="미국 정규장 외 — HDFSASP0 WS 메시지 미수신, skip",
)
def test_live_kis_ws_orderbook_aapl_receives_message_within_5s():
    """KIS WS HDFSASP0 — AAPL 구독 후 5초 내 메시지 수신 검증.

    `KISOverseasOrderbookWS.start()` → subscribe('DNASAAPL') → on_orderbook 콜백 도달.
    """
    from services.quote_overseas import KISOverseasOrderbookWS

    received: list[dict] = []

    async def _capture(payload: dict):
        received.append(payload)

    async def _run():
        ws = KISOverseasOrderbookWS(on_orderbook=_capture)
        await ws.start()
        await ws.subscribe("DNASAAPL")
        # 5초간 대기 (정규장이면 호가 변동 메시지 다수)
        deadline = asyncio.get_event_loop().time() + 5.0
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.2)
            if received:
                break
        await ws.stop()

    asyncio.get_event_loop().run_until_complete(_run()) \
        if not asyncio.get_event_loop().is_running() else None

    # asyncio.run은 새 루프 — 간단히 사용
    if not received:
        asyncio.run(_run())

    assert len(received) > 0, (
        "[FAIL] HDFSASP0 WS 메시지 5초 내 미수신. 원인 후보:\n"
        "  - 정규장 외 시간(테스트 skip 조건 보강 필요)\n"
        "  - approval_key 발급 실패\n"
        "  - 토픽 키 형식 'DNASAAPL' 다름 (실제는 'DNAS AAPL' 또는 다른 형태)\n"
        "  - parse_overseas_orderbook offset 가정과 실 메시지 다름\n"
        "    (wrapper.parse_overseas_orderbook의 t[0..48] offset 점검 필요)"
    )
    sample = received[0]
    assert sample.get("symbol") == "AAPL"
    assert isinstance(sample.get("asks"), list)
    assert isinstance(sample.get("bids"), list)
