"""트랙 1: advisory_cache 공유 캐시 전환 검증.

동일 (code, market) 종목을 user_id=1과 user_id=2가 저장해도
DB 행은 1개만 존재해야 한다 (PK = (code, market)).
"""
from db.repositories.advisory_repo import AdvisoryRepository
from db.models.advisory import AdvisoryCache


def test_shared_cache_single_row_for_same_code(db_session):
    """두 사용자가 동일 종목 캐시 저장 시 DB row 1개만 존재."""
    repo = AdvisoryRepository(db_session)
    fundamental = {"metrics": {"per": 10, "pbr": 1.2}}
    technical = {"indicators": {"rsi": 50}}

    repo.save_cache(1, "005930", "KR", fundamental, technical)
    db_session.flush()

    fundamental2 = {"metrics": {"per": 11, "pbr": 1.3}}
    repo.save_cache(2, "005930", "KR", fundamental2, technical)
    db_session.flush()

    rows = db_session.query(AdvisoryCache).filter_by(code="005930", market="KR").all()
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    # 두 번째 저장이 첫 번째를 덮어써야 함 (공유 캐시)
    assert rows[0].fundamental["metrics"]["per"] == 11


def test_shared_cache_user_id_irrelevant(db_session):
    """get_cache는 user_id 무관하게 동일 데이터 반환."""
    repo = AdvisoryRepository(db_session)
    fundamental = {"metrics": {"per": 10}}
    technical = {"indicators": {"rsi": 60}}

    repo.save_cache(1, "AAPL", "US", fundamental, technical)
    db_session.flush()

    cache_a = repo.get_cache(1, "AAPL", "US")
    cache_b = repo.get_cache(2, "AAPL", "US")
    cache_c = repo.get_cache(999, "AAPL", "US")

    assert cache_a is not None
    assert cache_b is not None
    assert cache_c is not None
    assert cache_a["fundamental"] == cache_b["fundamental"] == cache_c["fundamental"]
    assert cache_a["technical"] == cache_b["technical"] == cache_c["technical"]


def test_save_research_data_shared(db_session):
    """save_research_data도 공유 (user_id 무관)."""
    repo = AdvisoryRepository(db_session)

    repo.save_cache(1, "005930", "KR", {"f": 1}, {"t": 1})
    db_session.flush()

    repo.save_research_data(2, "005930", "KR", {"news": "x"})
    db_session.flush()

    rows = db_session.query(AdvisoryCache).filter_by(code="005930", market="KR").all()
    assert len(rows) == 1
    assert rows[0].research_data == {"news": "x"}
    # fundamental/technical은 유지
    assert rows[0].fundamental == {"f": 1}


def test_market_separation(db_session):
    """동일 code라도 market이 다르면 별도 row."""
    repo = AdvisoryRepository(db_session)
    repo.save_cache(1, "005930", "KR", {"k": 1}, {})
    repo.save_cache(1, "005930", "US", {"u": 1}, {})
    db_session.flush()

    rows = db_session.query(AdvisoryCache).filter_by(code="005930").all()
    assert len(rows) == 2
    markets = sorted(r.market for r in rows)
    assert markets == ["KR", "US"]
