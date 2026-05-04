"""R4 (2026-05-04): PageViewRepository.count_by_user 단위 테스트."""

import pytest

from db.repositories.page_view_repo import PageViewRepository


@pytest.fixture
def repo(db_session):
    """3 사용자(1, 2, 3) + anonymous 방문 데이터 셋업."""
    pv = PageViewRepository(db_session)
    # user 1: 5 방문
    for i in range(5):
        pv.record(user_id=1, path=f"/api/p{i}", method="GET", status_code=200, duration_ms=10)
    # user 2: 3 방문
    for i in range(3):
        pv.record(user_id=2, path="/api/q", method="GET", status_code=200, duration_ms=20)
    # anonymous: 7 방문 (제외 대상)
    for i in range(7):
        pv.record(user_id=None, path="/api/health", method="GET", status_code=200, duration_ms=5)
    db_session.flush()
    return pv


def test_count_by_user_basic(repo):
    """입력 user_ids별 정확한 카운트 반환."""
    counts = repo.count_by_user([1, 2])
    assert counts == {1: 5, 2: 3}


def test_count_by_user_zero_for_unknown(repo):
    """카운트 없는 user_id도 0으로 채워서 반환."""
    counts = repo.count_by_user([1, 2, 999])
    assert counts == {1: 5, 2: 3, 999: 0}


def test_count_by_user_excludes_anonymous(repo):
    """anonymous(user_id=NULL) 행은 어떤 사용자 카운트에도 포함되지 않음."""
    counts = repo.count_by_user([1, 2, 3])
    # user 3은 데이터 없음 → 0. anonymous 7건은 어디에도 합산 안 됨.
    assert counts[3] == 0
    assert sum(counts.values()) == 8  # 5 + 3 + 0


def test_count_by_user_empty_input(repo):
    """빈 입력은 빈 dict."""
    assert repo.count_by_user([]) == {}
