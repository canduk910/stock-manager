"""CLI 인터페이스 (Click 기반)."""

import click

from .dart import fetch_filings
from .display import (
    console,
    export_earnings_csv,
    export_screen_csv,
    print_earnings_table,
    print_screen_table,
)
from .krx import get_all_stocks
from .service import (
    ScreenerValidationError,
    apply_filters,
    normalize_date,
    parse_sort_spec,
    sort_stocks,
)


def _safe_normalize_date(date_str: str | None) -> str:
    """normalize_date의 CLI 래퍼. ScreenerValidationError -> click.BadParameter."""
    try:
        return normalize_date(date_str)
    except ScreenerValidationError as e:
        raise click.BadParameter(str(e))


def _safe_parse_sort_spec(sort_str: str, order: str | None) -> list[tuple[str, bool]]:
    """parse_sort_spec의 CLI 래퍼."""
    try:
        return parse_sort_spec(sort_str, order)
    except ScreenerValidationError as e:
        raise click.BadParameter(str(e))


@click.group()
@click.version_option(version="1.0.0", prog_name="stock-screener")
def cli():
    """한국 주식시장(KOSPI/KOSDAQ) 종목 스크리너"""
    pass


@cli.command()
@click.option("--date", "date_str", default=None, help="조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD, 기본: 오늘)")
@click.option("--export", "export_fmt", type=click.Choice(["csv"]), default=None, help="내보내기 형식")
def earnings(date_str: str | None, export_fmt: str | None):
    """당일 실적발표(정기보고서 제출) 종목 조회"""
    try:
        target_date = _safe_normalize_date(date_str)
    except click.BadParameter as e:
        console.print(f"[red]오류:[/red] {e.format_message()}")
        raise SystemExit(1)

    formatted = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
    console.print(f"[cyan]{formatted}[/cyan] 정기보고서 제출 종목을 조회합니다...")

    try:
        filings = fetch_filings(target_date, target_date)
    except RuntimeError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise SystemExit(1)

    if not filings:
        console.print(f"\n{formatted}에 제출된 정기보고서가 없습니다.")
        return

    if export_fmt == "csv":
        path = export_earnings_csv(filings, target_date)
        console.print(f"\n[green]CSV 저장 완료:[/green] {path}")
    else:
        print_earnings_table(filings, formatted)


@cli.command()
@click.option("--date", "date_str", default=None, help="조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD, 기본: 오늘)")
@click.option("--sort-by", "sort_by", default=None, help='정렬 기준 (예: PER, "ROE desc, PER asc")')
@click.option("--order", default=None, type=click.Choice(["asc", "desc"]), help="정렬 순서 (단일 정렬 시)")
@click.option("--top", "top_n", default=None, type=int, help="상위 N개만 출력")
@click.option("--per-range", nargs=2, type=float, default=None, help="PER 범위 (최소 최대)")
@click.option("--pbr-max", type=float, default=None, help="PBR 최대값")
@click.option("--roe-min", type=float, default=None, help="ROE 최소값 (%)")
@click.option("--market", default=None, type=click.Choice(["KOSPI", "KOSDAQ"], case_sensitive=False), help="시장 필터")
@click.option("--include-negative", is_flag=True, default=False, help="적자기업(PER 음수) 포함")
@click.option("--earnings-today", is_flag=True, default=False, help="당일 실적발표 종목만 대상")
@click.option("--export", "export_fmt", type=click.Choice(["csv"]), default=None, help="내보내기 형식")
def screen(
    date_str: str | None,
    sort_by: str | None,
    order: str | None,
    top_n: int | None,
    per_range: tuple[float, float] | None,
    pbr_max: float | None,
    roe_min: float | None,
    market: str | None,
    include_negative: bool,
    earnings_today: bool,
    export_fmt: str | None,
):
    """전체 상장종목 멀티팩터 스크리닝"""
    try:
        target_date = _safe_normalize_date(date_str)
    except click.BadParameter as e:
        console.print(f"[red]오류:[/red] {e.format_message()}")
        raise SystemExit(1)

    formatted = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"

    # 정렬 조건 파싱
    sort_specs = []
    if sort_by:
        try:
            sort_specs = _safe_parse_sort_spec(sort_by, order)
        except click.BadParameter as e:
            console.print(f"[red]오류:[/red] {e.format_message()}")
            raise SystemExit(1)
    else:
        # 기본 정렬: 시가총액 내림차순
        sort_specs = [("mktcap", True)]

    # KRX 데이터 수집
    console.print(f"[cyan]{formatted}[/cyan] 전종목 데이터를 수집합니다...")
    try:
        stocks = get_all_stocks(target_date)
    except RuntimeError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise SystemExit(1)

    console.print(f"  전종목 {len(stocks)}개 로드 완료")

    # 당일 실적발표 종목 필터
    title = ""
    if earnings_today:
        console.print("  당일 실적발표 종목을 필터링합니다...")
        try:
            filings = fetch_filings(target_date, target_date)
        except RuntimeError as e:
            console.print(f"[red]오류:[/red] {e}")
            raise SystemExit(1)

        filing_codes = {f["stock_code"] for f in filings}
        stocks = [s for s in stocks if s["code"] in filing_codes]
        console.print(f"  실적발표 종목 {len(stocks)}개로 필터링됨")
        title = f"당일 실적발표 종목 스크리닝 ({formatted})"

    # 필터 적용 (per_range 튜플을 per_min/per_max로 변환)
    per_min = per_range[0] if per_range is not None else None
    per_max = per_range[1] if per_range is not None else None
    stocks = apply_filters(
        stocks,
        market=market,
        per_min=per_min,
        per_max=per_max,
        pbr_max=pbr_max,
        roe_min=roe_min,
        include_negative=include_negative,
    )

    # 정렬
    stocks = sort_stocks(stocks, sort_specs)

    # 상위 N개 제한
    if top_n is not None and top_n > 0:
        stocks = stocks[:top_n]

    if not stocks:
        console.print("\n조건에 맞는 종목이 없습니다.")
        return

    # 출력
    if export_fmt == "csv":
        path = export_screen_csv(stocks, target_date)
        console.print(f"\n[green]CSV 저장 완료:[/green] {path}")
    else:
        print_screen_table(stocks, formatted, title=title)
