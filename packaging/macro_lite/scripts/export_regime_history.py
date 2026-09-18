"""macro_regime_history 테이블 → JSON export (stock-manager → 타 프로젝트 이관용).

체제 판정 일별 이력(regime/buffett_ratio/vix/fear_greed_score/kospi/sp500)을 JSON으로 내보낸다.
macro_lite 패키지는 이 데이터를 소비하지 않는다(regime 판정은 무상태). 이관 대상 프로젝트가
자체 스냅샷 테이블과 비교하거나 과거 이력을 백필할 때 쓰는 참고 데이터다.

표준 라이브러리만 사용. 세 가지 소스 중 하나를 지정:
  --sqlite <path>        로컬 app.db (SQLAlchemy 단일 DB)
  --container <name>     docker PostgreSQL 컨테이너 (컨테이너 env POSTGRES_USER/POSTGRES_DB 사용)
  --pg-url <url>         psql이 로컬에 있을 때 직접 접속

사용 예:
  python -m scripts.export_regime_history --container prodclone-db
  python -m scripts.export_regime_history --sqlite ~/stock-watchlist/app.db --out /tmp/regime.json

출력: {"table": "macro_regime_history", "exported_at": ISO, "rows": [{date, regime, buffett_ratio,
        vix, fear_greed_score, kospi, sp500, notes, created_at}, ...]}  (date 오름차순)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

COLUMNS = ["date", "regime", "buffett_ratio", "vix", "fear_greed_score", "kospi", "sp500", "notes", "created_at"]
FLOAT_COLS = {"buffett_ratio", "vix", "fear_greed_score", "kospi", "sp500"}
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "packaging" / "macro_lite" / "backend" / "data" / "macro_regime_history_seed.json"
_SQL = f"SELECT {', '.join(COLUMNS)} FROM macro_regime_history ORDER BY date"


def _normalize(row: dict) -> dict:
    out = {}
    for c in COLUMNS:
        v = row.get(c)
        if v in ("", None):
            out[c] = None if c in FLOAT_COLS else (v if v is not None else "")
            continue
        if c in FLOAT_COLS:
            try:
                out[c] = float(v)
            except (TypeError, ValueError):
                out[c] = None
        else:
            out[c] = str(v)
    return out


def _from_sqlite(path: str) -> list[dict]:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(p)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return [_normalize(dict(r)) for r in conn.execute(_SQL)]


def _rows_from_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return [_normalize(r) for r in reader]


def _from_container(name: str) -> list[dict]:
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker 실행 파일을 찾을 수 없음")
    cmd = [docker, "exec", name, "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --csv -c "{_SQL}"']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"docker exec psql 실패 (exit {proc.returncode}): {proc.stderr.strip()}")
    return _rows_from_csv(proc.stdout)


def _from_pg_url(url: str) -> list[dict]:
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("psql 실행 파일을 찾을 수 없음 (--container 사용 권장)")
    proc = subprocess.run([psql, url, "--csv", "-c", _SQL], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"psql 실패 (exit {proc.returncode}): {proc.stderr.strip()}")
    return _rows_from_csv(proc.stdout)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sqlite", help="로컬 app.db 경로")
    src.add_argument("--container", help="PostgreSQL docker 컨테이너 이름")
    src.add_argument("--pg-url", help="postgresql://user:pw@host:port/db")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help=f"출력 JSON 경로 (기본 {DEFAULT_OUT})")
    args = ap.parse_args(argv)

    try:
        if args.sqlite:
            rows, src_desc = _from_sqlite(args.sqlite), f"sqlite://{args.sqlite}"
        elif args.container:
            rows, src_desc = _from_container(args.container), f"docker://{args.container}"
        else:
            rows, src_desc = _from_pg_url(args.pg_url), "pg-url"
    except Exception as e:  # noqa: BLE001
        print(f"[export_regime_history] 실패: {e}", file=sys.stderr)
        return 1

    kst = timezone(timedelta(hours=9))
    payload = {
        "table": "macro_regime_history",
        "source": src_desc,
        "exported_at": datetime.now(kst).isoformat(timespec="seconds"),
        "rows": rows,
    }
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if rows:
        print(f"src: {src_desc}\nout: {out}\n  rows={len(rows)} ({rows[0]['date']} ~ {rows[-1]['date']})")
    else:
        print(f"[export_regime_history] 경고: 행 없음\nsrc: {src_desc}\nout: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
