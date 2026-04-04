"""MarketBoardStock + MarketBoardOrder models."""

from sqlalchemy import Column, Integer, String

from db.base import Base


class MarketBoardStock(Base):
    __tablename__ = "market_board_stocks"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    name = Column(String, nullable=False)
    added_date = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "name": self.name,
            "added_date": self.added_date,
        }


class MarketBoardOrder(Base):
    __tablename__ = "market_board_order"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    position = Column(Integer, nullable=False)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "position": self.position,
        }
