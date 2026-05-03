"""services/kis_validator.py 단위 테스트 — requests.post mock."""

from unittest.mock import patch, MagicMock

import pytest

from services.exceptions import ExternalAPIError


def _mock_response(status: int, body: dict) -> MagicMock:
    res = MagicMock()
    res.status_code = status
    res.json.return_value = body
    res.text = str(body)
    return res


class TestKisValidator:
    def test_success_returns_true(self):
        from services import kis_validator
        with patch("services.kis_validator.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, {"access_token": "tok123"})
            assert kis_validator.validate_kis("KEY", "SECRET") is True

    def test_http_401_raises_external_api_error(self):
        from services import kis_validator
        with patch("services.kis_validator.requests.post") as mock_post:
            mock_post.return_value = _mock_response(401, {"error_description": "invalid key"})
            with pytest.raises(ExternalAPIError):
                kis_validator.validate_kis("BAD", "BAD")

    def test_network_error_raises_external_api_error(self):
        from services import kis_validator
        import requests as _r
        with patch("services.kis_validator.requests.post", side_effect=_r.RequestException("dns")):
            with pytest.raises(ExternalAPIError):
                kis_validator.validate_kis("KEY", "SECRET")

    def test_missing_access_token_raises(self):
        from services import kis_validator
        with patch("services.kis_validator.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, {})
            with pytest.raises(ExternalAPIError):
                kis_validator.validate_kis("KEY", "SECRET")

    def test_uses_custom_base_url(self):
        from services import kis_validator
        with patch("services.kis_validator.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, {"access_token": "x"})
            kis_validator.validate_kis("K", "S", base_url="https://openapivts.koreainvestment.com:29443")
            args, kwargs = mock_post.call_args
            url = args[0]
            assert "openapivts" in url
            assert url.endswith("/oauth2/tokenP")
