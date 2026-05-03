"""UserKisCredentials 모델 — 사용자별 KIS API 자격증명 (AES-GCM 암호화 저장).

분리 테이블(User 모델 비대화 방지). 1:1 (user_id PK + FK).
모든 민감 필드는 services.secure_store로 암호화된 b64 문자열로 저장.
"""

from sqlalchemy import Column, ForeignKey, Integer, String

from db.base import Base


class UserKisCredentials(Base):
    __tablename__ = "user_kis_credentials"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    app_key_enc = Column(String, nullable=False)
    app_secret_enc = Column(String, nullable=False)
    acnt_no_enc = Column(String, nullable=False)
    acnt_prdt_cd_stk = Column(String, nullable=False)
    acnt_prdt_cd_fno = Column(String, nullable=True)
    hts_id = Column(String, nullable=True)
    base_url = Column(String, nullable=False, default="https://openapi.koreainvestment.com:9443")
    validated_at = Column(String, nullable=True)  # KST ISO. None=미검증
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
