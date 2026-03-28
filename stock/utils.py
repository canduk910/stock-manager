"""공통 유틸리티."""

import re


def is_domestic(code: str) -> bool:
    """6자리 숫자 코드면 국내(KRX), 아니면 해외."""
    return bool(re.match(r'^\d{6}$', code))


def is_fno(code: str) -> bool:
    """선물옵션 단축코드 판별. 1xxx=지수선물, 2xxx=지수옵션, 3xxx=주식선물옵션."""
    if not code or len(code) < 4:
        return False
    return code[0] in ('1', '2', '3') and not re.match(r'^\d{6}$', code)
