"""Watchlist + WatchlistOrder models."""

from sqlalchemy import Column, Integer, String, Text

from db.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    name = Column(String, nullable=False)
    added_date = Column(String, nullable=False)
    memo = Column(Text, nullable=False, default="")

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "name": self.name,
            "added_date": self.added_date,
            "memo": self.memo,
        }


class WatchlistOrder(Base):
    __tablename__ = "watchlist_order"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    position = Column(Integer, nullable=False)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "position": self.position,
        }
