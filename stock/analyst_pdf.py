"""애널리스트 PDF 본문 추출 + GPT-4o-mini 요약.

REQ-ANALYST-01/02/03/12:
  - 시스템 프롬프트로 6항목 강제 (catalyst 2 / risk 2 / TP 근거 1 / EPS 변경 1)
  - 환각 방지: "본문에 명시된 숫자만 인용, 추정 금지"
  - 첫 5페이지만 추출, 5000자 절단, 100자 미만 시 요약 생략
  - ai_gateway 시스템 호출 모드 (user_id=None, check_quota=False)
  - 캐시 키: analyst:summary:{md5(pdf_url)}, 영구 (PDF 불변)
  - PDF 다운로드 보안: 10MB 한도, Content-Type 검증, 모든 예외 흡수

데이터 흐름:
  summarize_one(pdf_url)
    → cache hit? return cached
    → requests.get (timeout=15, stream=True, UA 헤더)
    → Content-Length/Type 가드
    → pdfplumber 첫 5페이지 텍스트 추출
    → 5000자 절단, 100자 미만 시 ""
    → ai_gateway.call_openai_chat (gpt-4o-mini, system 호출)
    → JSON 파싱 → 6항목 텍스트 결합
    → cache.set(영구)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

import pdfplumber
import requests

from stock.cache import get_cached, set_cached

logger = logging.getLogger(__name__)


# ── 상수 ─────────────────────────────────────────────────────────────────────

_DOWNLOAD_TIMEOUT = 15
_MAX_BYTES = 10 * 1024 * 1024            # 10MB
_MAX_PAGES = 5
_MAX_TEXT_CHARS = 5000
_MIN_TEXT_CHARS = 100
_USER_AGENT = "Mozilla/5.0 (compatible; stock-manager analyst-pdf/1.0)"
_CACHE_TTL_HOURS = 24 * 365 * 10         # 영구 (PDF 내용 불변, 10년 사실상 영구)
_SUMMARY_MAX_CHARS = 300
_SUMMARY_MAX_TOKENS = 400


_SUMMARY_SYSTEM_PROMPT = (
    "당신은 증권사 리서치 보고서 요약 어시스턴트이다. "
    "본문에서 다음 6개 항목만 정확히 추출하라. "
    "본문에 명시된 숫자만 인용. 추정·외삽·외부 지식 사용 금지. 환각 절대 금지. "
    "각 항목 50자 이내, 총 300자 이하 강제.\n\n"
    "추출 항목:\n"
    "1. 투자포인트(catalyst) 2개:\n"
    "   - catalyst[0] = 매출/이익 성장 동인 (매출 CAGR과 연결)\n"
    "   - catalyst[1] = 영업이익률/마진 개선 동인\n"
    "2. 리스크 요인 2개:\n"
    "   - risk[0] = 산업/거시 리스크 (매크로 분석과 연결)\n"
    "   - risk[1] = 종목 고유 리스크 (부채/재무/규제)\n"
    "3. tp_basis: 목표가 산정 근거 (DCF/PER multiple/PBR 어느 방법론인지 + 핵심 가정 1개)\n"
    "4. eps_revision: EPS 추정 변경 사유 (상향/하향 시 본문 명시 사유, 변경 없으면 빈 문자열)\n\n"
    "응답은 반드시 다음 JSON 형식이어야 한다:\n"
    '{"catalyst":["...","..."], "risk":["...","..."], '
    '"tp_basis":"...", "eps_revision":"..."}\n'
    "본문에 해당 정보가 없으면 빈 문자열로 둔다. 추측 금지."
)


# ── 유틸 ─────────────────────────────────────────────────────────────────────


def _cache_key(pdf_url: str) -> str:
    """캐시 키: analyst:summary:{md5(pdf_url)}."""
    h = hashlib.md5(pdf_url.encode("utf-8")).hexdigest()
    return f"analyst:summary:{h}"


def _format_summary(parsed: dict) -> str:
    """JSON 응답 → 300자 이하 문자열 결합."""
    catalysts = parsed.get("catalyst") or []
    risks = parsed.get("risk") or []
    tp = parsed.get("tp_basis") or ""
    eps = parsed.get("eps_revision") or ""

    parts = []
    for i, c in enumerate(catalysts[:2], 1):
        if c:
            parts.append(f"투자포인트{i}: {c}")
    for i, r in enumerate(risks[:2], 1):
        if r:
            parts.append(f"리스크{i}: {r}")
    if tp:
        parts.append(f"TP근거: {tp}")
    if eps:
        parts.append(f"EPS변경: {eps}")

    text = " / ".join(parts)
    if len(text) > _SUMMARY_MAX_CHARS:
        text = text[:_SUMMARY_MAX_CHARS]
    return text


def _download_pdf(pdf_url: str) -> Optional[bytes]:
    """PDF 다운로드. 실패/예외 시 None.

    REQ-ANALYST-12: 모든 예외 흡수, 상위 전파 금지.
    """
    try:
        with requests.get(
            pdf_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_DOWNLOAD_TIMEOUT,
            stream=True,
        ) as resp:
            try:
                resp.raise_for_status()
            except Exception as e:
                logger.warning("PDF 다운로드 HTTP 오류 (%s): %s", pdf_url, e)
                return None

            # Content-Type 검증
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "application/pdf" not in ctype and "octet-stream" not in ctype:
                logger.debug("PDF가 아닌 Content-Type: %s (%s)", ctype, pdf_url)
                return None

            # Content-Length 검증
            try:
                length = int(resp.headers.get("Content-Length") or 0)
            except (TypeError, ValueError):
                length = 0
            if length and length > _MAX_BYTES:
                logger.warning("PDF 크기 초과 (%d bytes, %s)", length, pdf_url)
                return None

            # 스트리밍 다운로드 (런타임 길이 검증 포함)
            buf = bytearray()
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > _MAX_BYTES:
                    logger.warning("PDF 다운로드 중 크기 초과 (%s)", pdf_url)
                    return None
            return bytes(buf)
    except Exception as e:
        logger.warning("PDF 다운로드 예외 (%s): %s", pdf_url, e)
        return None


def _extract_text(pdf_bytes: bytes) -> str:
    """pdfplumber로 첫 5페이지 텍스트 추출. 실패 시 빈 문자열."""
    import io
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages[:_MAX_PAGES]
            chunks = []
            for p in pages:
                try:
                    t = p.extract_text() or ""
                except Exception as e:
                    logger.debug("PDF 페이지 추출 실패: %s", e)
                    continue
                if t:
                    chunks.append(t)
            text = "\n".join(chunks).strip()
            if len(text) > _MAX_TEXT_CHARS:
                text = text[:_MAX_TEXT_CHARS]
            return text
    except Exception as e:
        logger.warning("pdfplumber 파싱 실패: %s", e)
        return ""


def _call_openai_for_summary(pdf_text: str) -> str:
    """ai_gateway 시스템 호출 → JSON 응답 → 결합 텍스트.

    REQ-ANALYST-03: user_id=None, check_quota=False, model='gpt-4o-mini'.
    """
    from services import ai_gateway
    try:
        resp = ai_gateway.call_openai_chat(
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": pdf_text},
            ],
            user_id=None,
            service_name="analyst_summary",
            check_quota=False,
            model="gpt-4o-mini",
            max_completion_tokens=_SUMMARY_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except Exception:
            logger.warning("PDF 요약 JSON 파싱 실패")
            return ""
        if not isinstance(parsed, dict):
            return ""
        return _format_summary(parsed)
    except Exception as e:
        logger.warning("PDF 요약 OpenAI 호출 실패: %s", e)
        return ""


# ── 공개 API ─────────────────────────────────────────────────────────────────


def summarize_one(pdf_url: Optional[str]) -> str:
    """PDF 본문을 다운로드 → 추출 → GPT-4o-mini 요약 → 캐시 저장.

    REQ-ANALYST-01~03/12 통합. 모든 실패는 빈 문자열 반환 (상위 전파 없음).

    Args:
        pdf_url: PDF 절대 URL. 빈/None이면 ''.

    Returns:
        요약 문자열 (최대 300자) 또는 빈 문자열.
    """
    if not pdf_url:
        return ""

    key = _cache_key(pdf_url)
    cached = get_cached(key)
    if cached is not None:
        # 빈 문자열도 캐시한 경우 그대로 반환 (재호출 방지)
        return cached if isinstance(cached, str) else ""

    pdf_bytes = _download_pdf(pdf_url)
    if not pdf_bytes:
        # 실패는 캐시하지 않음 (다음 호출 시 재시도 허용)
        return ""

    text = _extract_text(pdf_bytes)
    if len(text) < _MIN_TEXT_CHARS:
        # 짧은 본문 — 환각 위험으로 요약 생략. 빈 문자열 캐시(재호출 방지).
        set_cached(key, "", ttl_hours=_CACHE_TTL_HOURS)
        return ""

    summary = _call_openai_for_summary(text)
    set_cached(key, summary, ttl_hours=_CACHE_TTL_HOURS)
    return summary
