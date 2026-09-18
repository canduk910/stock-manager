"""이 프로젝트 cache.db 의 FRED OAS 누적 시계열 → macro_lite seed JSON 추출.

    python scripts/export_oas_history.py
    python scripts/export_oas_history.py --db /path/to/cache.db --out /path/to/oas_history_seed.json
    python scripts/export_oas_history.py --container stock-manager
    python scripts/export_oas_history.py --container prodclone-web --container-path /home/app/stock-watchlist/cache.db

- 읽는 키: `macro:oas_history_persist:BAMLH0A0HYM2` (HY OAS), `macro:oas_history_persist:BAMLC0A0CM` (IG OAS)
  (원본 `stock/oas_history_store.py` 영속 키. value 는 JSON 문자열
   `[{"date": "YYYY-MM-DD", "value": float}, ...]` date 오름차순, TTL 50년 — 만료 여부는 무시)
- 출력: `{series_id: [{"date", "value"}, ...]}` (macro_lite `oas_history_store.load_seed` 입력 포맷)
- `--db`: 호스트의 cache.db 경로 (기본 `~/stock-watchlist/cache.db`). 로컬 호스트 파일에는 누적 키가
  없을 수 있다 — 운영 데이터는 docker 볼륨(컨테이너 내부 `/home/app/stock-watchlist/cache.db`).
- `--container <name>`: `docker cp <name>:<container-path> <tmp>` 로 컨테이너 내부 파일을 임시 경로에
  꺼낸 뒤 동일 로직으로 읽는다(`docker exec` 미사용). docker 미설치/컨테이너 없음 → stderr 경고 + exit 1.
  `--db` 와 상호배타. 컨테이너 내 경로는 `--container-path` (기본 `/home/app/stock-watchlist/cache.db`).
- 키가 없거나 파싱 실패 시 해당 시리즈는 빈 리스트 + stderr 경고 (exit 0)
- 표준 라이브러리만 사용 — 이 프로젝트 모듈 import 없음 (운영 볼륨에서 꺼낸 cache.db 를 어디서든 처리 가능)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

SERIES_IDS = ("BAMLH0A0HYM2", "BAMLC0A0CM")
KEY_PREFIX = "macro:oas_history_persist:"

DEFAULT_DB = Path.home() / "stock-watchlist" / "cache.db"
DEFAULT_CONTAINER_PATH = "/home/app/stock-watchlist/cache.db"
DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "packaging" / "macro_lite" / "backend" / "data" / "oas_history_seed.json"
)


def _warn(msg: str) -> None:
    print(f"[export_oas_history] 경고: {msg}", file=sys.stderr)


def _normalize_rows(raw) -> list[dict]:
    """persist 구조 → seed 행. date/value 없는 항목은 버리고 date 오름차순 정렬."""
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for r in raw:
        if not isinstance(r, dict):
            continue
        d = r.get("date")
        v = r.get("value")
        if not d or v is None:
            continue
        try:
            rows.append({"date": str(d), "value": float(v)})
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x["date"])
    return rows


def read_series(db_path: Path, series_id: str) -> list[dict]:
    """cache.db 에서 시리즈 1개 읽기. 없거나 실패 시 빈 리스트 + 경고."""
    key = f"{KEY_PREFIX}{series_id}"
    try:
        con = sqlite3.connect(str(db_path), timeout=10.0)
        try:
            row = con.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        finally:
            con.close()
    except sqlite3.Error as e:
        _warn(f"{series_id}: cache.db 읽기 실패 ({e}) → 빈 리스트")
        return []
    if not row:
        _warn(f"{series_id}: 키 없음 ({key}) → 빈 리스트")
        return []
    try:
        raw = json.loads(row[0])
    except (TypeError, ValueError) as e:
        _warn(f"{series_id}: value JSON 파싱 실패 ({e}) → 빈 리스트")
        return []
    rows = _normalize_rows(raw)
    if not rows:
        _warn(f"{series_id}: 유효 행 0건 → 빈 리스트")
    return rows


def copy_from_container(container: str, container_path: str, dest_dir: Path) -> Path:
    """`docker cp <container>:<container_path> <dest_dir>/cache.db`. 실패 시 RuntimeError."""
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker 실행 파일을 찾을 수 없습니다 (PATH 에 docker 없음)")
    dest = dest_dir / "cache.db"
    cmd = [docker, "cp", f"{container}:{container_path}", str(dest)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"docker cp 실행 실패: {e}") from e
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"docker cp 실패 (exit {proc.returncode}) — 컨테이너 '{container}' 또는 "
            f"경로 '{container_path}' 확인: {detail}"
        )
    if not dest.exists():
        raise RuntimeError(f"docker cp 후 파일 없음: {dest}")
    return dest


def export(db_path: Path, out_path: Path) -> dict[str, list[dict]]:
    if not db_path.exists():
        _warn(f"cache.db 없음: {db_path} → 모든 시리즈 빈 리스트")
        seed = {sid: [] for sid in SERIES_IDS}
    else:
        seed = {sid: read_series(db_path, sid) for sid in SERIES_IDS}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False)
        f.write("\n")
    return seed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="stock-manager cache.db → macro_lite oas_history_seed.json 추출",
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--db", default=None, help=f"호스트 cache.db 경로 (기본: {DEFAULT_DB})")
    src.add_argument(
        "--container", default=None,
        help="docker 컨테이너 이름 — `docker cp` 로 컨테이너 내부 cache.db 를 꺼내 읽는다 (--db 와 상호배타)",
    )
    parser.add_argument(
        "--container-path", default=DEFAULT_CONTAINER_PATH,
        help=f"--container 사용 시 컨테이너 내 cache.db 경로 (기본: {DEFAULT_CONTAINER_PATH})",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"출력 seed JSON 경로 (기본: {DEFAULT_OUT})")
    args = parser.parse_args(argv)

    out_path = Path(args.out).expanduser()

    if args.container:
        with tempfile.TemporaryDirectory(prefix="oas_export_") as tmp:
            try:
                db_path = copy_from_container(args.container, args.container_path, Path(tmp))
            except RuntimeError as e:
                _warn(str(e))
                return 1
            seed = export(db_path, out_path)
            src_label = f"docker://{args.container}:{args.container_path}"
    else:
        db_path = Path(args.db).expanduser() if args.db else DEFAULT_DB
        seed = export(db_path, out_path)
        src_label = str(db_path)

    print(f"db : {src_label}")
    print(f"out: {out_path}")
    for sid, rows in seed.items():
        rng = f"{rows[0]['date']} ~ {rows[-1]['date']}" if rows else "-"
        print(f"  {sid}: {len(rows)} rows ({rng})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
