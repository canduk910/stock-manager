"""R_x (호가 silent failure 차단): KISQuoteManager.start() 실패 시 사유 노출 검증.

가설 2 회귀 가드 — .env KIS_APP_KEY 미설정 시 silent skip이 아니라
`_start_failed_reason`에 사유 기록 + logger.error로 표면화되어야 한다.

pytest-asyncio 미설치 환경 대응 — asyncio.run으로 sync 래핑.
"""

import asyncio
import logging
from unittest.mock import patch

import pytest


def test_start_silent_skip_records_reason_and_errors(caplog):
    """KIS 키 미설정 → _running=False + _start_failed_reason 채워짐 + ERROR 로그."""
    from services.quote_kis import KISQuoteManager
    import services.quote_kis as qk_mod

    m = KISQuoteManager()
    with patch.object(qk_mod, "KIS_APP_KEY", ""), \
         patch.object(qk_mod, "KIS_APP_SECRET", ""), \
         caplog.at_level(logging.ERROR, logger="services.quote_kis"):
        asyncio.run(m.start())

    assert m._running is False
    assert m._start_failed_reason is not None
    assert "KIS_APP_KEY" in m._start_failed_reason
    # ERROR 로그 1건 이상 발생 (silent warning 아님)
    assert any(rec.levelno >= logging.ERROR for rec in caplog.records)


def test_start_with_keys_runs_normally():
    """KIS 키 있음 → _running=True 후 stop() → _running=False + _start_failed_reason is None."""
    from services.quote_kis import KISQuoteManager
    import services.quote_kis as qk_mod

    m = KISQuoteManager()
    with patch.object(qk_mod, "KIS_APP_KEY", "test"), \
         patch.object(qk_mod, "KIS_APP_SECRET", "test"):
        async def _run():
            await m.start()
            await m.stop()
        asyncio.run(_run())

    assert m._running is False  # stop() 후
    assert m._start_failed_reason is None


def test_consecutive_failure_counter_initialized():
    """_consecutive_connect_failures 초기값 0."""
    from services.quote_kis import KISQuoteManager
    m = KISQuoteManager()
    assert m._consecutive_connect_failures == 0


def test_get_approval_key_classifies_http_error():
    """approval_key HTTP 401/403 등 → RuntimeError(상세 메시지) raise."""
    from services.quote_kis import KISQuoteManager
    from unittest.mock import MagicMock

    m = KISQuoteManager()
    fake_res = MagicMock()
    fake_res.status_code = 403
    fake_res.text = '{"error":"forbidden"}'

    with patch("services.quote_kis.requests.post", return_value=fake_res):
        with pytest.raises(RuntimeError) as exc_info:
            m._get_approval_key()
        assert "403" in str(exc_info.value)


def test_get_approval_key_classifies_parse_error():
    """approval_key 응답이 JSON 아닐 때 → RuntimeError(파싱 실패)."""
    from services.quote_kis import KISQuoteManager
    from unittest.mock import MagicMock

    m = KISQuoteManager()
    fake_res = MagicMock()
    fake_res.status_code = 200
    fake_res.text = "not-json"
    fake_res.json.side_effect = ValueError("parse fail")

    with patch("services.quote_kis.requests.post", return_value=fake_res):
        with pytest.raises(RuntimeError) as exc_info:
            m._get_approval_key()
        assert "파싱" in str(exc_info.value)


def test_get_approval_key_missing_field():
    """approval_key 응답에 키 부재 → RuntimeError."""
    from services.quote_kis import KISQuoteManager
    from unittest.mock import MagicMock

    m = KISQuoteManager()
    fake_res = MagicMock()
    fake_res.status_code = 200
    fake_res.json.return_value = {"other": "data"}

    with patch("services.quote_kis.requests.post", return_value=fake_res):
        with pytest.raises(RuntimeError) as exc_info:
            m._get_approval_key()
        assert "키 부재" in str(exc_info.value)
