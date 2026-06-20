"""AI자문 보고서 챗봇 (stateless).

advisory_service.py에서 분리(2026-06-20 구조 리팩토링). 이미 생성된 자문보고서에 대한
질의응답을 처리한다. 보고서 본문을 system prompt에 첨부하고 슬라이딩 윈도우로 히스토리를
관리하며, 서버는 대화를 저장하지 않는다(stateless).

기존 호출 경로 호환: advisory_service.chat_with_report 로 re-export 되어
routers/advisory.py 등 모든 기존 import 경로가 그대로 동작한다.
"""

from __future__ import annotations

import json
import logging

from config import OPENAI_API_KEY, OPENAI_MODEL

from stock import advisory_store
from services.exceptions import ConfigError, NotFoundError

logger = logging.getLogger(__name__)


# ── 보고서 챗봇 ────────────────────────────────────────────────────────────────

_CHAT_HISTORY_MAX_TURNS = 20  # user/assistant 합산 메시지 상한 (약 10턴)
_CHAT_MESSAGE_MAX_CHARS = 4000

_CHAT_SYSTEM_TEMPLATE = """당신은 사용자가 아래 자문보고서 내용을 이해하도록 돕는 전문 어시스턴트입니다.
종목: {label} ({market} {code})

[규칙]
1. 답변은 반드시 보고서에 수록된 내용 범위 안에서만 제공합니다.
2. 보고서에 없는 사실(현재가, 거시 데이터, 재무 수치 등)은 추정하지 말고 "보고서에는 해당 정보가 없습니다"라고 안내합니다.
3. 새로운 투자 의견이나 등급을 만들지 마세요. 보고서의 등급/의견을 인용하여 설명하세요.
4. 예측·확정 표현 대신 "보고서에 따르면 ~로 평가됩니다" 형식을 사용합니다.
5. 한국어로 간결하고 명확하게 답변합니다 (불필요하게 길게 늘리지 않습니다).

[자문보고서 본문 (JSON)]
{report_json}
"""


def _trim_chat_history(messages: list[dict]) -> list[dict]:
    """슬라이딩 윈도우: 최근 _CHAT_HISTORY_MAX_TURNS 개만 유지."""
    if len(messages) <= _CHAT_HISTORY_MAX_TURNS:
        return list(messages)
    return list(messages[-_CHAT_HISTORY_MAX_TURNS:])


def _validate_chat_messages(messages) -> list[dict]:
    """챗 messages 입력 검증. 문제 시 ServiceError."""
    from services.exceptions import ServiceError

    if not isinstance(messages, list) or not messages:
        raise ServiceError("messages는 비어있지 않은 배열이어야 합니다.")
    if len(messages) > 50:
        raise ServiceError("messages는 최대 50개까지 허용됩니다.")
    cleaned: list[dict] = []
    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            raise ServiceError(f"messages[{idx}] 형식이 올바르지 않습니다.")
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant"):
            raise ServiceError(f"messages[{idx}].role은 user/assistant 여야 합니다.")
        if not isinstance(content, str) or not content.strip():
            raise ServiceError(f"messages[{idx}].content는 비어있지 않은 문자열이어야 합니다.")
        if len(content) > _CHAT_MESSAGE_MAX_CHARS:
            raise ServiceError(
                f"messages[{idx}].content는 {_CHAT_MESSAGE_MAX_CHARS}자를 초과할 수 없습니다."
            )
        cleaned.append({"role": role, "content": content})
    if cleaned[-1]["role"] != "user":
        raise ServiceError("마지막 메시지는 user 역할이어야 합니다.")
    return cleaned


def chat_with_report(
    code: str,
    market: str,
    report_id: int,
    messages: list,
    user_id: int,
) -> dict:
    """이미 생성된 자문보고서에 대한 stateless 챗봇.

    보고서 본문(JSON)을 system prompt에 첨부하고, 클라이언트가 보낸 messages 히스토리에서
    최근 20개를 슬라이딩 윈도우로 잘라 OpenAI에 전달한다. 서버는 대화를 저장하지 않는다.
    """
    cleaned = _validate_chat_messages(messages)

    report_row = advisory_store.get_report_by_id(int(report_id), user_id=user_id)
    if not report_row:
        raise NotFoundError("자문보고서를 찾을 수 없습니다.")
    if (report_row.get("code") or "").upper() != (code or "").upper() or \
            (report_row.get("market") or "").upper() != (market or "").upper():
        raise NotFoundError("보고서가 요청한 종목과 일치하지 않습니다.")

    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    label = report_row.get("name") or report_row.get("code") or code
    report_body = report_row.get("report") or {}
    try:
        report_json = json.dumps(report_body, ensure_ascii=False)
    except Exception:
        report_json = str(report_body)

    system_prompt = _CHAT_SYSTEM_TEMPLATE.format(
        label=label,
        market=(market or "").upper(),
        code=(code or "").upper(),
        report_json=report_json,
    )

    history = _trim_chat_history(cleaned)
    chat_messages = [{"role": "system", "content": system_prompt}, *history]

    from services.ai_gateway import call_openai_chat
    resp = call_openai_chat(
        messages=chat_messages,
        user_id=user_id,
        service_name="advisory_chat",
        max_completion_tokens=1500,
    )
    reply = (resp.choices[0].message.content or "").strip()
    model_used = getattr(resp, "model", None) or OPENAI_MODEL
    return {"reply": reply, "model": model_used, "report_id": int(report_id)}
