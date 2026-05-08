"""REQ-DB-02 + REQ-REPO-03: stock_info.exchange 컬럼 + Repository 헬퍼.

검증 대상:
- StockInfo 모델에 `exchange: VARCHAR(8) NULL` 컬럼이 존재
- StockInfoRepository.get_exchange / set_exchange 동작
  - 종목 부재 → get None
  - set 시 INSERT (최소 필드)
  - 기존 종목 set → UPDATE (다른 필드 보존)
  - exchange가 NULL이면 get None
"""

from __future__ import annotations

import pytest

from db.models.stock_info import StockInfo
from db.repositories.stock_info_repo import StockInfoRepository


def test_stock_info_has_exchange_column():
    """StockInfo 모델에 exchange 컬럼이 정의되어 있는지."""
    cols = {c.name: c for c in StockInfo.__table__.columns}
    assert "exchange" in cols, "stock_info.exchange 컬럼 누락"
    col = cols["exchange"]
    # nullable
    assert col.nullable is True, "exchange는 NULLABLE이어야 함 (무손실 마이그레이션)"
    # String 타입
    assert "VARCHAR" in str(col.type).upper() or "STRING" in str(col.type).upper()


def test_get_exchange_returns_none_when_row_missing(db_session):
    """종목이 없으면 get_exchange는 None."""
    repo = StockInfoRepository(db_session)
    assert repo.get_exchange("UNKNOWN", "US") is None


def test_set_exchange_inserts_when_row_missing(db_session):
    """종목이 없으면 INSERT (code/market/exchange 최소 필드 채움)."""
    repo = StockInfoRepository(db_session)
    repo.set_exchange("AAPL", "US", "NAS")
    db_session.commit()

    assert repo.get_exchange("AAPL", "US") == "NAS"


def test_set_exchange_updates_existing_preserves_other_fields(db_session):
    """기존 종목 set → UPDATE만, 다른 필드(price 등) 보존."""
    repo = StockInfoRepository(db_session)
    # 사전 조건: 가격 정보가 이미 있는 종목
    repo.upsert_price("MSFT", "US", {"close": 400.0, "change": 1.0, "change_pct": 0.25, "mktcap": 3.0e12})
    db_session.commit()

    repo.set_exchange("MSFT", "US", "NAS")
    db_session.commit()

    # exchange 반영 + 가격 보존
    assert repo.get_exchange("MSFT", "US") == "NAS"
    info = repo.get_stock_info("MSFT", "US")
    assert info is not None
    assert info["price"] == 400.0


def test_get_exchange_returns_none_when_column_null(db_session):
    """종목이 있어도 exchange 컬럼이 NULL이면 get None."""
    repo = StockInfoRepository(db_session)
    repo.upsert_price("GOOGL", "US", {"close": 150.0})
    db_session.commit()

    # exchange 미설정
    assert repo.get_exchange("GOOGL", "US") is None


def test_set_exchange_overwrites_existing_exchange(db_session):
    """이미 exchange가 설정된 종목에 대해 새 값으로 덮어쓰기 가능."""
    repo = StockInfoRepository(db_session)
    repo.set_exchange("AMZN", "US", "NAS")
    db_session.commit()

    repo.set_exchange("AMZN", "US", "NYS")
    db_session.commit()

    assert repo.get_exchange("AMZN", "US") == "NYS"


def test_get_exchange_default_market_us(db_session):
    """REQ-REPO-03: 기본 market="US"."""
    repo = StockInfoRepository(db_session)
    repo.set_exchange("TSLA", "US", "NAS")
    db_session.commit()

    # market 인자 생략 → "US" 기본
    assert repo.get_exchange("TSLA") == "NAS"
