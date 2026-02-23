"""관심종목 목록 CRUD (~/stock-watchlist/watchlist.json)."""

import json
from datetime import date
from pathlib import Path
from typing import Optional

_WATCHLIST_DIR = Path.home() / "stock-watchlist"
_WATCHLIST_PATH = _WATCHLIST_DIR / "watchlist.json"


def _load() -> list[dict]:
    if not _WATCHLIST_PATH.exists():
        return []
    try:
        return json.loads(_WATCHLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    _WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def all_items() -> list[dict]:
    return _load()


def get_item(code: str) -> Optional[dict]:
    return next((i for i in _load() if i["code"] == code), None)


def add_item(code: str, name: str, memo: str = "") -> bool:
    """이미 존재하면 False, 새로 추가하면 True."""
    items = _load()
    if any(i["code"] == code for i in items):
        return False
    items.append(
        {
            "code": code,
            "name": name,
            "added_date": date.today().isoformat(),
            "memo": memo,
        }
    )
    _save(items)
    return True


def remove_item(code: str) -> bool:
    items = _load()
    new_items = [i for i in items if i["code"] != code]
    if len(new_items) == len(items):
        return False
    _save(new_items)
    return True


def update_memo(code: str, memo: str) -> bool:
    items = _load()
    for item in items:
        if item["code"] == code:
            item["memo"] = memo
            _save(items)
            return True
    return False
