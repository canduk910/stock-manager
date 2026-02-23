"""출력 포맷팅 모듈.

터미널 테이블(rich) 및 CSV 내보내기를 담당한다.
"""

import csv
import os
from datetime import datetime

from rich.console import Console
from rich.table import Table

console = Console()


def _fmt_mktcap(value: int) -> str:
    """시가총액을 읽기 쉬운 형식(억원)으로 변환."""
    if value == 0:
        return "-"
    eok = value / 1_0000_0000  # 억원
    if eok >= 10000:
        return f"{eok / 10000:,.1f}조"
    return f"{eok:,.0f}억"


def _fmt_float(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}"


def print_earnings_table(filings: list[dict], date_str: str) -> None:
    """실적발표(정기보고서) 종목 테이블 출력."""
    table = Table(
        title=f"정기보고서 제출 목록 ({date_str})",
        show_lines=False,
    )
    table.add_column("No.", justify="right", style="dim")
    table.add_column("종목코드", justify="center")
    table.add_column("종목명", justify="left", style="bold")
    table.add_column("보고서 종류", justify="center")
    table.add_column("보고서명", justify="left")
    table.add_column("제출일", justify="center")
    table.add_column("제출인", justify="left")

    for i, f in enumerate(filings, 1):
        table.add_row(
            str(i),
            f["stock_code"],
            f["corp_name"],
            f["report_type"],
            f["report_name"],
            f["rcept_dt"],
            f["flr_nm"],
        )

    console.print()
    console.print(table)
    console.print(f"\n총 {len(filings)}건")


def print_screen_table(stocks: list[dict], date_str: str, title: str = "") -> None:
    """스크리닝 결과 테이블 출력."""
    display_title = title or f"종목 스크리닝 결과 ({date_str})"
    table = Table(title=display_title, show_lines=False)
    table.add_column("순위", justify="right", style="dim")
    table.add_column("종목코드", justify="center")
    table.add_column("종목명", justify="left", style="bold")
    table.add_column("시장", justify="center")
    table.add_column("PER", justify="right")
    table.add_column("PBR", justify="right")
    table.add_column("ROE(%)", justify="right")
    table.add_column("시가총액", justify="right")

    for i, s in enumerate(stocks, 1):
        table.add_row(
            str(i),
            s["code"],
            s["name"],
            s["market"],
            _fmt_float(s["per"]),
            _fmt_float(s["pbr"]),
            _fmt_float(s["roe"]),
            _fmt_mktcap(s["mktcap"]),
        )

    console.print()
    console.print(table)
    console.print(f"\n총 {len(stocks)}종목")


def export_earnings_csv(filings: list[dict], date_str: str) -> str:
    """실적발표 데이터를 CSV로 저장. 파일 경로 반환."""
    filename = f"earnings_{date_str}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["종목코드", "종목명", "보고서종류", "보고서명", "제출일", "제출인"])
        for item in filings:
            writer.writerow([
                item["stock_code"],
                item["corp_name"],
                item["report_type"],
                item["report_name"],
                item["rcept_dt"],
                item["flr_nm"],
            ])
    return os.path.abspath(filename)


def export_screen_csv(stocks: list[dict], date_str: str) -> str:
    """스크리닝 결과를 CSV로 저장. 파일 경로 반환."""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"screen_{date_str}_{timestamp}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["순위", "종목코드", "종목명", "시장구분", "PER", "PBR", "ROE(%)", "시가총액"])
        for i, s in enumerate(stocks, 1):
            writer.writerow([
                i,
                s["code"],
                s["name"],
                s["market"],
                _fmt_float(s["per"]),
                _fmt_float(s["pbr"]),
                _fmt_float(s["roe"]),
                s["mktcap"],
            ])
    return os.path.abspath(filename)