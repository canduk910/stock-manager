"""KIS 선물옵션 마스터파일 다운로드/파싱/검색.

지수선물/옵션, 주식선물/옵션 종목 마스터파일을 KIS 서버에서 다운로드하여
단축코드 ↔ 종목명 매핑과 검색 기능을 제공한다.

캐시: stock/cache.py (TTL 7일).
"""

import io
import ssl
import time
import urllib.request
import zipfile

from stock.cache import get_cached, set_cached

# 마스터파일 다운로드 URL (KIS 공식)
_IDX_MASTER_URL = "https://new.real.download.dws.co.kr/common/master/fo_idx_code_mts.mst.zip"
_STK_MASTER_URL = "https://new.real.download.dws.co.kr/common/master/fo_stk_code_mts.mst.zip"

_CACHE_KEY = "fno:master"
_CACHE_TTL_HOURS = 24 * 7  # 7일

# 모듈 레벨 인메모리 캐시 (cache.db 반복 조회 방지)
_fno_cache: dict | None = None
_fno_cache_at: float = 0
_FNO_MEM_TTL = 24 * 3600  # 24시간


def _download_and_parse(url: str, filename: str) -> list[dict]:
    """ZIP 다운로드 후 파이프 구분자 마스터파일 파싱. CP949 인코딩."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(url, context=ctx, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        raise RuntimeError(f"마스터파일 다운로드 실패 ({url}): {e}")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            raw = zf.read(filename)
    except KeyError:
        # 파일명이 다를 경우 첫 번째 파일 사용
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            raw = zf.read(zf.namelist()[0])

    lines = raw.decode("cp949", errors="replace").splitlines()

    # 컬럼: 상품종류|단축코드|표준코드|한글종목명|ATM구분|행사가|월물구분코드|기초자산단축코드|기초자산명
    columns = ["product_type", "code", "std_code", "name", "atm", "strike",
               "month_div", "underlying_code", "underlying_name"]
    results = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        row = {}
        for i, col in enumerate(columns):
            row[col] = parts[i].strip() if i < len(parts) else ""
        if row["code"]:
            results.append(row)
    return results


def get_fno_symbol_map() -> dict:
    """선물옵션 전체 종목 맵 반환. {단축코드: {name, std_code, product_type, ...}}

    인메모리 캐시(24시간) → cache.db(7일) → ZIP 다운로드 순으로 조회.
    """
    global _fno_cache, _fno_cache_at

    # 1) 인메모리 캐시 히트
    if _fno_cache is not None and (time.time() - _fno_cache_at) < _FNO_MEM_TTL:
        return _fno_cache

    # 2) cache.db 조회
    cached = get_cached(_CACHE_KEY)
    if cached:
        _fno_cache = cached
        _fno_cache_at = time.time()
        return _fno_cache

    # 3) ZIP 다운로드
    symbol_map = {}
    errors = []

    # 지수선물/옵션
    try:
        rows = _download_and_parse(_IDX_MASTER_URL, "fo_idx_code_mts.mst")
        for row in rows:
            symbol_map[row["code"]] = row
    except Exception as e:
        errors.append(f"지수선물: {e}")

    # 주식선물/옵션
    try:
        rows = _download_and_parse(_STK_MASTER_URL, "fo_stk_code_mts.mst")
        for row in rows:
            symbol_map[row["code"]] = row
    except Exception as e:
        errors.append(f"주식선물: {e}")

    if symbol_map:
        set_cached(_CACHE_KEY, symbol_map, ttl_hours=_CACHE_TTL_HOURS)
    elif errors:
        # 모두 실패 시 빈 맵이라도 1시간 캐시 (반복 실패 방지)
        set_cached(_CACHE_KEY, {}, ttl_hours=1)

    _fno_cache = symbol_map
    _fno_cache_at = time.time()
    return _fno_cache


def search_fno_symbols(query: str, limit: int = 10) -> list[dict]:
    """종목명 또는 단축코드로 검색. 부분매칭 지원.

    Returns:
        [{"code": "101W09", "name": "KOSPI200 2409", "product_type": "...", ...}]
    """
    if not query:
        return []

    symbol_map = get_fno_symbol_map()
    q = query.upper().strip()
    results = []

    for code, info in symbol_map.items():
        name = info.get("name", "")
        underlying = info.get("underlying_name", "")
        if q in code.upper() or q in name.upper() or q in underlying.upper():
            results.append({
                "code": code,
                "name": name,
                "std_code": info.get("std_code", ""),
                "product_type": info.get("product_type", ""),
                "atm": info.get("atm", ""),
                "strike": info.get("strike", ""),
                "underlying_code": info.get("underlying_code", ""),
                "underlying_name": underlying,
            })
        if len(results) >= limit:
            break

    return results


def validate_fno_symbol(code: str) -> dict | None:
    """단축코드 유효성 검증. 존재하면 종목 정보 반환, 없으면 None."""
    symbol_map = get_fno_symbol_map()
    return symbol_map.get(code.strip().upper())
