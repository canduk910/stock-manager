"""UserKisCredentials 모델 — 사용자별 KIS API 자격증명 (AES-GCM 암호화 저장).

R1 (KIS 멀티 계좌, 2026-05-15): PK 를 `id` AUTO_INCREMENT 로 전환하여 1:N 으로 확장.
- (user_id, label) UNIQUE — 사용자당 라벨 중복 금지.
- is_default BOOLEAN — 사용자당 최대 1개 default 계좌(Repository 트랜잭션 가드).
- 기존 컬럼은 모두 보존 — 백워드 호환.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, text

from db.base import Base


class UserKisCredentials(Base):
    __tablename__ = "user_kis_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # R1: 사용자당 라벨 중복 금지. UI 표시명(예: '주식', '연금', '미국').
    label = Column(String(50), nullable=False, server_default="기본")
    is_default = Column(Boolean, nullable=False, server_default=text("false"))

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

    __table_args__ = (
        UniqueConstraint("user_id", "label", name="uq_user_kis_credentials_user_label"),
    )
