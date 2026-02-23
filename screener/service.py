"""CLI 독립적인 비즈니스 로직 모듈.

screener/cli.py에서 추출한 핵심 함수들.
FastAPI 라우터와 CLI 양쪽에서 사용한다.
"""

from datetime import date, datetime


class ScreenerValidationError(Exception):
    """스크리너 입력값 검증 오류."""
    pass


def normalize_date(date_str: str | None) -> str:
    """날짜 문자열을 YYYYMMDD 형식으로 정규화.

    Args:
        date_str: YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD 등.
                  None이면 오늘 날짜 반환.

    Raises:
        ScreenerValidationError: 형식이 올바르지 않거나 유효하지 않은 날짜.
    """
    if date_str is None:
        return date.today().strftime("%Y%m%d")
    cleaned = date_str.replace("-", "").replace("/", "").replace(".", "")
    if len(cleaned) != 8 or not cleaned.isdigit():
        raise ScreenerValidationError(
            f"날짜 형식이 올바르지 않습니다: {date_str} (예: 20250220 또는 2025-02-20)"
        )
    try:
        datetime.strptime(cleaned, "%Y%m%d")
    except ValueError:
        raise ScreenerValidationError(f"유효하지 않은 날짜입니다: {date_str}")
    return cleaned


def parse_sort_spec(sort_str: str, order: str | None = None) -> list[tuple[str, bool]]:
    """정렬 조건을 파싱.

    Examples:
        "PER"               -> [("per", False)]  # ascending
        "ROE desc, PER asc" -> [("roe", True), ("per", False)]

    Returns:
        list of (field_name, is_descending) tuples

    Raises:
        ScreenerValidationError: 유효하지 않은 필드명이나 정렬 방향.
    """
    valid_fields = {"per", "pbr", "roe", "mktcap"}
    specs = []

    for part in sort_str.split(","):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        field = tokens[0].lower()
        if field not in valid_fields:
            raise ScreenerValidationError(
                f"정렬 기준 '{tokens[0]}'은(는) 유효하지 않습니다. "
                f"사용 가능: {', '.join(sorted(valid_fields))}"
            )

        if len(tokens) > 1:
            direction = tokens[1].lower()
            if direction not in ("asc", "desc"):
                raise ScreenerValidationError(
                    f"정렬 방향 '{tokens[1]}'은(는) 유효하지 않습니다. (asc 또는 desc)"
                )
            descending = direction == "desc"
        elif order:
            descending = order.lower() == "desc"
        else:
            descending = False

        specs.append((field, descending))

    return specs


def apply_filters(
    stocks: list[dict],
    *,
    market: str | None = None,
    per_min: float | None = None,
    per_max: float | None = None,
    pbr_max: float | None = None,
    roe_min: float | None = None,
    include_negative: bool = False,
) -> list[dict]:
    """필터 조건 적용.

    per_range 튜플 대신 per_min/per_max 개별 파라미터를 사용한다.
    """
    filtered = []
    for s in stocks:
        # 시장 필터
        if market and s["market"] != market.upper():
            continue

        per = s["per"]
        pbr = s["pbr"]
        roe = s["roe"]

        # 적자기업 필터 (PER 음수)
        if not include_negative and per is not None and per < 0:
            continue

        # PER 범위 필터
        if per_min is not None or per_max is not None:
            if per is None:
                continue
            if per_min is not None and per < per_min:
                continue
            if per_max is not None and per > per_max:
                continue

        # PBR 최대값 필터
        if pbr_max is not None:
            if pbr is None:
                continue
            if pbr > pbr_max:
                continue

        # ROE 최소값 필터
        if roe_min is not None:
            if roe is None:
                continue
            if roe < roe_min:
                continue

        filtered.append(s)

    return filtered


def sort_stocks(
    stocks: list[dict], sort_specs: list[tuple[str, bool]]
) -> list[dict]:
    """다중 기준 정렬. None 값은 마지막으로 밀어낸다."""
    if not sort_specs:
        return stocks

    def sort_key(stock: dict):
        keys = []
        for field, descending in sort_specs:
            val = stock.get(field)
            if val is None:
                # None은 항상 마지막
                keys.append((1, 0))
            else:
                keys.append((0, -val if descending else val))
        return keys

    return sorted(stocks, key=sort_key)
