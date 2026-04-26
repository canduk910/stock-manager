"""User 모델 — 사용자 인증 및 역할 관리."""

from sqlalchemy import Column, Integer, String

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # "admin" | "user"
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
