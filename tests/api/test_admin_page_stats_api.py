"""tests/api/test_admin_page_stats_api.py — /api/admin/page-stats."""

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def _seed(db, paths_calls: dict[str, int]):
    from db.repositories.page_view_repo import PageViewRepository
    repo = PageViewRepository(db)
    for path, n in paths_calls.items():
        for _ in range(n):
            repo.record(user_id=1, path=path, method="GET", status_code=200, duration_ms=15.0)
    db.commit()


def test_page_stats_basic(client, db_session):
    _seed(db_session, {"/api/balance": 5, "/api/watchlist": 3})

    today = datetime.now(KST).strftime("%Y-%m-%d")
    res = client.get(f"/api/admin/page-stats?from={today}&to={today}&top=10")
    assert res.status_code == 200, res.text
    body = res.json()
    paths = [item["path"] for item in body["summary"]]
    assert "/api/balance" in paths
    assert "/api/watchlist" in paths
    assert body["summary"][0]["calls"] == 5  # 가장 많은 호출
    assert "timeseries" in body


def test_page_stats_empty_window(client, db_session):
    res = client.get("/api/admin/page-stats?from=2020-01-01&to=2020-01-02")
    assert res.status_code == 200
    body = res.json()
    assert body["summary"] == []
    assert body["timeseries"] == []
