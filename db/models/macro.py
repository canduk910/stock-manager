"""MacroGptCache model — daily KST-based GPT result cache."""

from sqlalchemy import Column, String
from sqlalchemy.types import JSON

from db.base import Base


class MacroGptCache(Base):
    __tablename__ = "macro_gpt_cache"

    category = Column(String, primary_key=True)
    date_kst = Column(String, primary_key=True)
    result = Column(JSON, nullable=False)
    created_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "date_kst": self.date_kst,
            "result": self.result,
            "created_at": self.created_at,
        }
