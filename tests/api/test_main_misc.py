"""Phase 2b: main.py 잡다 검증.

(1) SPA catchall HEAD 메서드 지원 — uptime/curl -I 모니터링용.
(2) 보안 헤더 single source of truth = nginx. backend(TestClient)에서는 추가 안 됨.
"""
import pytest


# ── (1) SPA catchall HEAD ────────────────────────────────────────────
class TestSpaCatchallHead:
    def test_spa_get_returns_200_with_no_cache(self, client):
        """기존 동작 유지: GET /(임의 경로) → 200 + Cache-Control: no-cache."""
        resp = client.get("/some-spa-route")
        # frontend/dist가 없으면 catchall 자체가 등록 안 됨 → skip
        if resp.status_code == 404 and "Not Found" in resp.text:
            pytest.skip("frontend/dist 미빌드 — catchall 미등록")
        assert resp.status_code == 200
        assert "no-cache" in resp.headers.get("Cache-Control", "")

    def test_spa_head_returns_200_not_405(self, client):
        """신규: HEAD /(임의 경로) → 200 (이전: 405 Method Not Allowed)."""
        resp = client.head("/some-spa-route")
        if resp.status_code == 404:
            pytest.skip("frontend/dist 미빌드 — catchall 미등록")
        assert resp.status_code == 200, (
            f"HEAD가 405가 아니라 200이어야 함 (uptime/curl -I 호환). got={resp.status_code}"
        )
        # HEAD 응답에서도 Cache-Control 헤더 유지
        assert "no-cache" in resp.headers.get("Cache-Control", "")

    def test_spa_head_root_returns_200(self, client):
        """루트 경로도 HEAD 정상."""
        resp = client.head("/")
        if resp.status_code == 404:
            pytest.skip("frontend/dist 미빌드 — catchall 미등록")
        assert resp.status_code == 200


# ── (2) 보안 헤더 single source of truth = nginx ──────────────────────
class TestSecurityHeadersSourceOfTruth:
    """backend는 보안 헤더를 추가하지 않는다 (nginx가 단일 소스).

    프로덕션에서는 nginx가 6종 헤더(HSTS 포함)를 추가한다.
    dev/TestClient에서는 nginx 통과하지 않으므로 헤더 부재가 정상.
    """

    SECURITY_HEADER_NAMES = [
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Content-Security-Policy",
        # HSTS는 원래부터 backend에 없음 — 변동 없음
        "Strict-Transport-Security",
    ]

    def test_backend_does_not_add_security_headers(self, client):
        """backend 응답(nginx 미통과)에는 보안 헤더가 추가되지 않는다."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        for header in self.SECURITY_HEADER_NAMES:
            assert header not in resp.headers, (
                f"{header} 헤더가 backend에서 추가되고 있음. "
                f"nginx single source of truth 정책 위반."
            )
