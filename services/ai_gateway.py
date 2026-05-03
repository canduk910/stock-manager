"""AI API 호출 게이트웨이.

프로젝트 내 모든 OpenAI API 호출의 단일 진입점.
유저별 일일 호출 한도를 검사하고 사용량을 기록한다.

- user_id=None → 시스템/스케줄러 호출 (한도 검사 건너뜀)
- check_quota=False → 재시도 시 중복 한도 검사 방지
"""

import logging
import time
from typing import Optional

from config import OPENAI_API_KEY, OPENAI_MODEL
from services import _telemetry
from services.exceptions import ConfigError, ExternalAPIError, PaymentRequiredError, ServiceError

logger = logging.getLogger(__name__)

# ── 쿼터 관리 ─────────────────────────────────────────────────


class AiQuotaExceededError(ServiceError):
    """AI 일일 호출 한도 초과 (429)."""

    def __init__(self, message: str = "일일 AI 호출 한도를 초과했습니다."):
        super().__init__(message, status_code=429)


def _today_kst() -> str:
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")


def check_ai_quota(user_id: int) -> None:
    """유저의 일일 AI 호출 한도를 검사. 초과 시 AiQuotaExceededError."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository

    with get_session() as db:
        repo = AdminRepository(db)
        today = _today_kst()
        used = repo.get_daily_usage_count(user_id, today)
        limit = repo.get_effective_limit(user_id)
        if used >= limit:
            raise AiQuotaExceededError(
                f"일일 AI 호출 한도({limit}회)를 초과했습니다. (오늘 {used}회 사용)"
            )


def record_ai_usage(user_id: int, service_name: str) -> None:
    """AI 호출 1건을 사용량 로그에 기록."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository

    with get_session() as db:
        repo = AdminRepository(db)
        repo.record_usage(user_id, _today_kst(), service_name)


def get_ai_usage_status(user_id: int) -> dict:
    """유저의 오늘 사용량 + 한도 조회 (프론트엔드 표시용)."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository

    with get_session() as db:
        repo = AdminRepository(db)
        today = _today_kst()
        used = repo.get_daily_usage_count(user_id, today)
        limit = repo.get_effective_limit(user_id)
        return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


# ── OpenAI 호출 ───────────────────────────────────────────────


def call_openai_chat(
    messages: list[dict],
    user_id: Optional[int] = None,
    service_name: str = "unknown",
    check_quota: bool = True,
    **kwargs,
):
    """모든 OpenAI API 호출의 단일 진입점.

    Args:
        messages: OpenAI chat messages
        user_id: 사용자 ID. None이면 시스템 호출 (한도 검사 건너뜀)
        service_name: 호출 서비스명 (사용량 기록용)
        check_quota: True면 한도 검사 수행. 재시도 시 False로 설정
        **kwargs: max_completion_tokens, response_format 등 OpenAI 파라미터

    Returns:
        openai ChatCompletion 응답 객체

    Raises:
        ConfigError: OPENAI_API_KEY 미설정
        AiQuotaExceededError: 일일 한도 초과
        PaymentRequiredError: OpenAI 크레딧 부족
        ExternalAPIError: OpenAI 호출 실패
    """
    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    # 한도 검사 (유저 호출 + 최초 시도만)
    if user_id is not None and check_quota:
        check_ai_quota(user_id)

    # OpenAI 호출
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    model = kwargs.pop("model", None) or OPENAI_MODEL

    # T-4: OpenAI latency + token usage 계측
    _t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
    except Exception as e:
        _telemetry.record_event(f"ai_gateway.{service_name}.errors")
        _telemetry.record_event(f"ai_gateway.model.{model}.errors")
        err_str = str(e).lower()
        if "insufficient_quota" in err_str or "rate_limit" in err_str:
            raise PaymentRequiredError("OpenAI API 크레딧이 부족합니다.")
        raise ExternalAPIError(f"OpenAI API 호출 실패: {e}")
    finally:
        _dur_ms = (time.perf_counter() - _t0) * 1000.0
        _telemetry.observe(f"ai_gateway.{service_name}.duration_ms", _dur_ms)
        _telemetry.observe(f"ai_gateway.model.{model}.duration_ms", _dur_ms)

    _telemetry.record_event(f"ai_gateway.{service_name}.calls")
    _telemetry.record_event(f"ai_gateway.model.{model}.calls")
    # token usage (best effort — SDK 응답 구조 의존)
    try:
        usage = getattr(response, "usage", None)
        if usage is not None:
            prompt_tok = getattr(usage, "prompt_tokens", 0) or 0
            comp_tok = getattr(usage, "completion_tokens", 0) or 0
            _telemetry.record_event(f"ai_gateway.model.{model}.tokens.prompt", int(prompt_tok))
            _telemetry.record_event(f"ai_gateway.model.{model}.tokens.completion", int(comp_tok))
    except Exception:
        pass

    # 사용량 기록 (유저 호출만)
    if user_id is not None:
        try:
            record_ai_usage(user_id, service_name)
        except Exception as e:
            logger.warning("AI 사용량 기록 실패 (호출은 성공): %s", e)

    return response
