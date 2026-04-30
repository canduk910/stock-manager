"""네이버 증권 리서치 — 증권사별 목표가 + 리포트 수집.

네이버 증권의 기업분석 리서치 페이지를 파싱하여
증권사별 최신 목표가·투자의견·리포트 제목·PDF 링크를 수집한다.

데이터 흐름:
  1) 리스트 페이지 1회 호출 → 증권사·제목·날짜·PDF·nid 수집
  2) 증권사별 최신 1건만 필터
  3) 개별 리포트 페이지 병렬 호출 → 목표가·투자의견 추출
  4) cache.db에 6시간 캐시
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests

from stock.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

_BASE = "https://finance.naver.com/research"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_TIMEOUT = 10


# ── 리스트 페이지 파싱 ───────────────────────────────────────────────────────

def _fetch_list_page(stock_code: str) -> list[dict]:
    """리서치 리스트 페이지에서 리포트 목록 파싱.

    Returns: [{nid, broker, title, date, pdf_url}, ...]
    """
    url = f"{_BASE}/company_list.naver?searchType=itemCode&itemCode={stock_code}"
    try:
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("네이버 리서치 리스트 조회 실패 (%s): %s", stock_code, e)
        return []

    html = resp.content.decode("euc-kr", errors="replace")

    # type_1 테이블에서 데이터 행 추출
    table = re.search(r'<table[^>]*class="type_1"[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table:
        return []

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table.group(1), re.DOTALL)
    results = []

    for row in rows:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(tds) < 5:
            continue

        # td0: 종목명 (건너뜀)
        # td1: 제목 + nid 링크
        title_match = re.search(r'company_read\.naver\?nid=(\d+)[^"]*"[^>]*>([^<]+)', tds[1])
        if not title_match:
            continue
        nid = title_match.group(1)
        title = title_match.group(2).strip()

        # td2: 증권사
        broker = re.sub(r'<[^>]+>', '', tds[2]).strip()
        if not broker:
            continue

        # td3: PDF 링크
        pdf_match = re.search(r'href="(https://[^"]+\.pdf)"', tds[3])
        pdf_url = pdf_match.group(1) if pdf_match else ""

        # td4: 작성일
        date_str = re.sub(r'<[^>]+>', '', tds[4]).strip()

        results.append({
            "nid": nid,
            "broker": broker,
            "title": title,
            "date": date_str,
            "pdf_url": pdf_url,
        })

    return results


# ── 개별 리포트 페이지에서 목표가/투자의견 추출 ──────────────────────────────

def _fetch_report_detail(nid: str, stock_code: str) -> dict:
    """개별 리포트 페이지에서 목표가·투자의견 추출.

    Returns: {"target_price": int|None, "opinion": str|None}
    """
    url = (
        f"{_BASE}/company_read.naver"
        f"?nid={nid}&searchType=itemCode&itemCode={stock_code}"
    )
    try:
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.debug("네이버 리포트 상세 조회 실패 (nid=%s): %s", nid, e)
        return {"target_price": None, "opinion": None}

    html = resp.content.decode("euc-kr", errors="replace")

    # 목표가: <em class="money"><strong>2,000,000</strong></em>
    tp_match = re.search(
        r'목표가\s*<em[^>]*class="money"[^>]*>\s*<strong>([^<]+)</strong>',
        html,
    )
    target_price = None
    if tp_match:
        try:
            target_price = int(tp_match.group(1).replace(",", "").strip())
        except ValueError:
            pass

    # 투자의견: <em class="coment">Buy</em>
    op_match = re.search(r'투자의견\s*<em[^>]*class="coment"[^>]*>([^<]+)</em>', html)
    opinion = op_match.group(1).strip() if op_match else None

    return {"target_price": target_price, "opinion": opinion}


# ── 공개 API ─────────────────────────────────────────────────────────────────

def fetch_analyst_reports(stock_code: str, limit: int = 20) -> list[dict]:
    """증권사별 최신 리포트 + 목표가 수집.

    Args:
        stock_code: 6자리 종목코드 (예: "000660")
        limit: 최대 리포트 수

    Returns: [{
        "broker": "메리츠증권",
        "title": "계단식 리레이팅 구간 진입",
        "target_price": 2000000,
        "opinion": "Buy",
        "date": "26.04.29",
        "pdf_url": "https://..."
    }, ...]
    """
    cache_key = f"naver:research:{stock_code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # Step 1: 리스트 페이지에서 기본 정보 수집
    all_reports = _fetch_list_page(stock_code)
    if not all_reports:
        set_cached(cache_key, [], ttl_hours=1)
        return []

    # Step 2: 증권사별 최신 1건만 (리스트는 최신순이므로 첫 등장 유지)
    seen_brokers: set[str] = set()
    unique_reports: list[dict] = []
    for r in all_reports:
        if r["broker"] not in seen_brokers:
            seen_brokers.add(r["broker"])
            unique_reports.append(r)
        if len(unique_reports) >= limit:
            break

    # Step 3: 개별 페이지에서 목표가/투자의견 병렬 수집
    def _enrich(report: dict) -> dict:
        detail = _fetch_report_detail(report["nid"], stock_code)
        return {**report, **detail}

    enriched = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(_enrich, r): r for r in unique_reports}
        for fut in as_completed(futs):
            try:
                enriched.append(fut.result())
            except Exception:
                enriched.append(futs[fut])

    # nid 필드 제거 (내부용), 목표가 내림차순 정렬
    result = []
    for r in enriched:
        result.append({
            "broker": r["broker"],
            "title": r["title"],
            "target_price": r.get("target_price"),
            "opinion": r.get("opinion"),
            "date": r["date"],
            "pdf_url": r["pdf_url"],
        })

    result.sort(key=lambda x: x.get("target_price") or 0, reverse=True)

    set_cached(cache_key, result, ttl_hours=6)
    return result
