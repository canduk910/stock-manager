"""공통 유틸리티."""

import re


def is_domestic(code: str) -> bool:
    """6자리 숫자 코드면 국내(KRX), 아니면 해외."""
    return bool(re.match(r'^\d{6}$', code))
