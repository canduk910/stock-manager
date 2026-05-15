"""R6 (KIS 멀티 계좌) — H0STCNI0 체결통보 ACNT_NO → account_label 매칭 캐시.

REQ-ORDER-03:
- 체결통보 WS 응답의 ACNT_NO 8자리를 사용자의 등록 계좌 acnt_no_enc(복호화)와 매칭.
- 매칭 성공 → label 반환. 실패 → None + 경고 로그.
- 인메모리 LRU 100 캐시 — (user_id, acnt_no) 키.
- 계좌 추가/삭제/수정 시 invalidate_cache(user_id) 호출 필요.

도메인 정합: KIS 체결통보는 HTS_ID 단위 단일 스트림 — 사용자별 멀티 계좌 시 ACNT_NO 로만 분기 가능.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)

# LRU 캐시: (user_id, acnt_no_plain) → label
_LRU_MAX = 100
_cache: "OrderedDict[tuple[int, str], Optional[str]]" = OrderedDict()
_stats = {"hits": 0, "misses": 0}


def _lookup_db(user_id: int, acnt_no_plain: str) -> Optional[str]:
    """DB 에서 user_id 의 모든 계좌를 조회하여 acnt_no 평문 일치 행의 label 반환."""
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository

    with get_session() as db:
        accounts = UserKisRepository(db).list_accounts(user_id)

    for a in accounts:
        if a.get("acnt_no") == acnt_no_plain:
            return a.get("label")
    return None


def match_account_label(user_id: int, acnt_no_plain: str) -> Optional[str]:
    """체결통보의 ACNT_NO 평문 → 라벨 매칭.

    Args:
        user_id: 매칭 대상 사용자.
        acnt_no_plain: H0STCNI0 응답의 ACNT_NO (8자리 평문).

    Returns:
        매칭된 라벨, 또는 None (다른 사용자 계좌 또는 신규 미등록).
    """
    if user_id is None or not acnt_no_plain:
        return None

    key = (user_id, str(acnt_no_plain))
    if key in _cache:
        # LRU 이동
        _cache.move_to_end(key)
        _stats["hits"] += 1
        return _cache[key]

    _stats["misses"] += 1
    label = _lookup_db(user_id, str(acnt_no_plain))
    if label is None:
        logger.warning("[ExecNotice] ACNT_NO=%s 매칭 실패 (user_id=%s)", acnt_no_plain, user_id)
    _cache[key] = label
    # LRU 용량 초과 시 가장 오래된 항목 제거
    while len(_cache) > _LRU_MAX:
        _cache.popitem(last=False)
    return label


def invalidate_cache(user_id: Optional[int] = None) -> None:
    """계좌 추가/삭제/수정 시 호출.

    user_id=None → 전체 캐시 초기화.
    user_id=int → 해당 사용자 entry 만 삭제.
    """
    if user_id is None:
        _cache.clear()
        return
    keys_to_drop = [k for k in list(_cache.keys()) if k[0] == user_id]
    for k in keys_to_drop:
        _cache.pop(k, None)


def cache_stats() -> dict:
    """LRU 상태 — 테스트/모니터링용."""
    return {
        "current_size": len(_cache),
        "max_size": _LRU_MAX,
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "keys": list(_cache.keys()),
    }
