"""AnalystReport model — 증권사 리포트 메타데이터 + PDF 요약 영속화.

REQ-ANALYST-06:
  - 컬럼: id(PK), code, market, broker, target_price, opinion, title,
          pdf_url, summary, published_at, fetched_at
  - 유니크 인덱스: (code, market, broker, published_at, title)
  - 비유니크 인덱스: (code, market, published_at desc)
  - target_price: BigInteger (KR 메가캡 대응)
"""

from sqlalchemy import BigInteger, Column, Index, Integer, String, Text, UniqueConstraint

from db.base import Base


class AnalystReport(Base):
    __tablename__ = "analyst_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False)
    market = Column(String, nullable=False, default="KR")
    broker = Column(String, nullable=False)
    target_price = Column(BigInteger, nullable=True)  # KR=원, US=USD float은 round
    opinion = Column(String, nullable=True)            # 원본 5단계 라벨
    title = Column(String, nullable=False, default="")
    pdf_url = Column(String, nullable=False, default="")
    summary = Column(Text, nullable=False, default="")
    published_at = Column(String, nullable=False)      # YYYY-MM-DD
    fetched_at = Column(String, nullable=False)        # KST ISO datetime

    __table_args__ = (
        UniqueConstraint(
            "code", "market", "broker", "published_at", "title",
            name="uq_analyst_reports_unique",
        ),
        Index(
            "idx_analyst_reports_code_market_pub",
            "code", "market", "published_at",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "market": self.market,
            "broker": self.broker,
            "target_price": self.target_price,
            "opinion": self.opinion,
            "title": self.title,
            "pdf_url": self.pdf_url,
            "summary": self.summary,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
        }
