"""UserRepository — 사용자 CRUD."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, name: str, hashed_password: str, role: str = "user") -> dict:
        from db.utils import now_kst_iso
        now = now_kst_iso()
        user = User(
            username=username,
            name=name,
            hashed_password=hashed_password,
            role=role,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        self.db.flush()
        return user.to_dict()

    def get_by_username(self, username: str) -> Optional[dict]:
        row = self.db.query(User).filter_by(username=username).first()
        if not row:
            return None
        d = row.to_dict()
        d["hashed_password"] = row.hashed_password
        return d

    def get_by_id(self, user_id: int) -> Optional[dict]:
        row = self.db.query(User).filter_by(id=user_id).first()
        return row.to_dict() if row else None

    def update_password(self, user_id: int, hashed_password: str) -> bool:
        from db.utils import now_kst_iso
        count = (
            self.db.query(User)
            .filter_by(id=user_id)
            .update({"hashed_password": hashed_password, "updated_at": now_kst_iso()})
        )
        return count > 0

    def count(self) -> int:
        return self.db.query(User).count()
