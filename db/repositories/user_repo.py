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

    # ── Phase 4 (단계 4): 사용자 관리 ─────────────────────────────

    def list_users(self, q: Optional[str] = None, limit: int = 20, offset: int = 0) -> list[dict]:
        """username/name 부분 검색 + 페이지네이션. id asc."""
        query = self.db.query(User)
        if q:
            from sqlalchemy import or_
            pat = f"%{q}%"
            query = query.filter(or_(User.username.ilike(pat), User.name.ilike(pat)))
        rows = query.order_by(User.id.asc()).offset(offset).limit(limit).all()
        return [r.to_dict() for r in rows]

    def count_users(self, q: Optional[str] = None) -> int:
        query = self.db.query(User)
        if q:
            from sqlalchemy import or_
            pat = f"%{q}%"
            query = query.filter(or_(User.username.ilike(pat), User.name.ilike(pat)))
        return query.count()

    def update_role(self, user_id: int, role: str) -> bool:
        from db.utils import now_kst_iso
        if role not in ("admin", "user"):
            raise ValueError(f"invalid role: {role}")
        count = (
            self.db.query(User)
            .filter_by(id=user_id)
            .update({"role": role, "updated_at": now_kst_iso()})
        )
        return count > 0

    def delete_user(self, user_id: int) -> bool:
        count = self.db.query(User).filter_by(id=user_id).delete()
        return count > 0
