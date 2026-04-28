"""StockInfo model — persistent stock info cache (survives Docker restart)."""

from sqlalchemy import BigInteger, Column, Float, Index, Integer, String

from db.base import Base


class StockInfo(Base):
    __tablename__ = "stock_info"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    price = Column(Float)
    change_val = Column(Float)
    change_pct = Column(Float)
    mktcap = Column(Float)
    shares = Column(BigInteger)
    high_52 = Column(Float)
    low_52 = Column(Float)
    price_updated_at = Column(String)
    per = Column(Float)
    pbr = Column(Float)
    roe = Column(Float)
    dividend_yield = Column(Float)
    dividend_per_share = Column(Float)
    market_type = Column(String)
    sector = Column(String)
    metrics_updated_at = Column(String)
    revenue = Column(BigInteger)
    operating_income = Column(BigInteger)
    net_income = Column(BigInteger)
    bsns_year = Column(Integer)
    fin_updated_at = Column(String)
    return_3m = Column(Float)
    return_6m = Column(Float)
    return_1y = Column(Float)
    returns_updated_at = Column(String)

    __table_args__ = (
        Index("idx_stock_info_price_updated", "price_updated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "price": self.price,
            "change_val": self.change_val,
            "change_pct": self.change_pct,
            "mktcap": self.mktcap,
            "shares": self.shares,
            "high_52": self.high_52,
            "low_52": self.low_52,
            "price_updated_at": self.price_updated_at,
            "per": self.per,
            "pbr": self.pbr,
            "roe": self.roe,
            "dividend_yield": self.dividend_yield,
            "dividend_per_share": self.dividend_per_share,
            "market_type": self.market_type,
            "sector": self.sector,
            "metrics_updated_at": self.metrics_updated_at,
            "revenue": self.revenue,
            "operating_income": self.operating_income,
            "net_income": self.net_income,
            "bsns_year": self.bsns_year,
            "fin_updated_at": self.fin_updated_at,
            "return_3m": self.return_3m,
            "return_6m": self.return_6m,
            "return_1y": self.return_1y,
            "returns_updated_at": self.returns_updated_at,
        }
