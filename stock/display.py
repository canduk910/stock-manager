"""Rich 테이블 렌더링 + CSV 내보내기."""

import csv
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


# ── 포맷 유틸 ───────────────────────────────────────────────────────────────

def _awk(won: Optional[int]) -> str:
    """원 → 억원 문자열 (천단위 콤마). None이면 '-'."""
    if won is None:
        return "-"
    awk = round(won / 1_0000_0000)
    return f"{awk:,}"


def _pct(val: Optional[float], digits: int = 1) -> str:
    if val is None:
        return "-"
    return f"{val:.{digits}f}%"


def _price(val: Optional[int]) -> str:
    if val is None:
        return "-"
    return f"{val:,}"


def _change_color(pct: Optional[float]) -> str:
    """전일대비 컬러 마크업."""
    if pct is None:
        return "-"
    sign = "+" if pct > 0 else ""
    s = f"{sign}{pct:.2f}%"
    if pct > 0:
        return f"[green]{s}[/green]"
    if pct < 0:
        return f"[red]{s}[/red]"
    return s


def _op_margin(revenue: Optional[int], op: Optional[int]) -> str:
    if revenue and op and revenue != 0:
        return f"{op / revenue * 100:.1f}%"
    return "-"


def _period_label(fin: dict) -> str:
    """보고서기준 레이블. 예: '2024/12'."""
    dt_str = fin.get("thstrm_dt", "")
    # 형식: "2024.01.01 ~ 2024.12.31"
    if dt_str and "~" in dt_str:
        end = dt_str.split("~")[-1].strip()
        parts = end.replace("년", ".").replace("월", ".").replace("일", "").split(".")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1].zfill(2)}"
    # thstrm_dt 없으면 bsns_year + "/12" (대부분 12월 결산)
    bsns_year = fin.get("bsns_year")
    return f"{bsns_year}/12" if bsns_year else "-"


def _growth(cur: Optional[int], prev: Optional[int]) -> str:
    if cur is None or prev is None or prev == 0:
        return "-"
    g = (cur - prev) / abs(prev) * 100
    sign = "+" if g >= 0 else ""
    color = "green" if g >= 0 else "red"
    return f"[{color}]{sign}{g:.1f}%[/{color}]"


# ── watchlist list ───────────────────────────────────────────────────────────

def print_watchlist(items: list[dict]) -> None:
    if not items:
        console.print("[yellow]관심종목이 없습니다. `stock watch add <종목코드>` 로 추가하세요.[/yellow]")
        return

    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
    t.add_column("종목코드", style="dim", width=10)
    t.add_column("종목명", min_width=12)
    t.add_column("추가일", width=12)
    t.add_column("메모")

    for item in items:
        t.add_row(
            item["code"],
            item["name"],
            item.get("added_date", "-"),
            item.get("memo", "") or "-",
        )

    console.print(t)


# ── dashboard ────────────────────────────────────────────────────────────────

def print_dashboard(rows: list[dict], export: Optional[str] = None) -> None:
    """
    rows 각 원소:
        code, name, price(dict|None), fin(dict|None)
    """
    if export == "csv":
        _export_dashboard_csv(rows)
        return

    t = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        title="관심종목 대시보드",
    )
    t.add_column("종목코드", style="dim", width=8)
    t.add_column("종목명", min_width=12)
    t.add_column("현재가", justify="right", width=10)
    t.add_column("전일대비", justify="right", width=10)
    t.add_column("시가총액(억)", justify="right", width=12)
    t.add_column("매출액(억)", justify="right", width=12)
    t.add_column("영업이익(억)", justify="right", width=12)
    t.add_column("순이익(억)", justify="right", width=11)
    t.add_column("영업이익률", justify="right", width=10)
    t.add_column("보고서기준", justify="center", width=10)

    for row in rows:
        p = row.get("price") or {}
        f = row.get("fin") or {}

        revenue = f.get("revenue")
        op_income = f.get("operating_income")

        t.add_row(
            row["code"],
            row["name"],
            _price(p.get("close")),
            _change_color(p.get("change_pct")),
            _awk(p.get("mktcap")),
            _awk(revenue),
            _awk(op_income),
            _awk(f.get("net_income")),
            _op_margin(revenue, op_income),
            _period_label(f) if f.get("bsns_year") else "-",
        )

    console.print(t)


def _export_dashboard_csv(rows: list[dict]) -> None:
    filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    headers = [
        "종목코드", "종목명", "현재가", "전일대비(%)",
        "시가총액(억)", "매출액(억)", "영업이익(억)", "순이익(억)",
        "영업이익률(%)", "보고서기준",
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            p = row.get("price") or {}
            fin = row.get("fin") or {}
            revenue = fin.get("revenue")
            op_income = fin.get("operating_income")
            op_margin = (
                f"{op_income / revenue * 100:.1f}"
                if revenue and op_income
                else ""
            )
            w.writerow([
                row["code"],
                row["name"],
                p.get("close", ""),
                p.get("change_pct", ""),
                round(p["mktcap"] / 1e8) if p.get("mktcap") else "",
                round(revenue / 1e8) if revenue else "",
                round(op_income / 1e8) if op_income else "",
                round(fin["net_income"] / 1e8) if fin.get("net_income") else "",
                op_margin,
                _period_label(fin) if fin.get("bsns_year") else "",
            ])
    console.print(f"[green]CSV 저장 완료:[/green] {filename}")


# ── info ─────────────────────────────────────────────────────────────────────

def print_stock_info(
    item: dict,
    detail: Optional[dict],
    fin: Optional[dict],
    export: Optional[str] = None,
) -> None:
    if export == "csv":
        _export_info_csv(item, detail, fin)
        return

    # 기본정보 패널
    code = item["code"]
    name = item["name"]
    memo = item.get("memo", "") or ""

    d = detail or {}
    info_lines = [
        f"[bold]종목명[/bold]     {name}  ([dim]{code}[/dim])",
        f"[bold]시장구분[/bold]   {d.get('market_type') or '-'}",
        f"[bold]업종[/bold]       {d.get('sector') or '-'}",
        f"[bold]현재가[/bold]     {_price(d.get('close'))}원  {_change_color(d.get('change_pct'))}",
        f"[bold]시가총액[/bold]   {_awk(d.get('mktcap'))}억원",
        f"[bold]상장주식수[/bold] {_price(d.get('shares'))}주",
        f"[bold]52주 고가[/bold]  {_price(d.get('high_52'))}원",
        f"[bold]52주 저가[/bold]  {_price(d.get('low_52'))}원",
    ]
    if memo:
        info_lines.append(f"[bold]메모[/bold]       {memo}")

    console.print(Panel("\n".join(info_lines), title=f"[bold cyan]{name}[/bold cyan]", expand=False))

    # 재무 요약 (최근 3개년)
    if not fin or fin.get("bsns_year") is None:
        console.print("[yellow]재무데이터 없음 (신규상장 또는 API 키 미설정)[/yellow]")
        return

    fs_label = "연결" if fin.get("fs_div") == "CFS" else "개별"
    p0 = fin.get("period_cur", "당기")
    p1 = fin.get("period_prev", "전기")
    p2 = fin.get("period_prev2", "전전기")

    t = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
        title=f"재무 요약 ({fs_label}재무제표, 단위: 억원)",
    )
    t.add_column("항목", min_width=14)
    t.add_column(p2, justify="right", width=14)
    t.add_column(p1, justify="right", width=14)
    t.add_column(f"{p1}→{p0} 증감", justify="right", width=12)
    t.add_column(p0, justify="right", width=14)

    def row(label, key):
        v0 = fin.get(key)
        v1 = fin.get(f"{key}_prev")
        v2 = fin.get(f"{key}_prev2")
        t.add_row(label, _awk(v2), _awk(v1), _growth(v0, v1), _awk(v0))

    row("매출액", "revenue")
    row("영업이익", "operating_income")
    row("당기순이익", "net_income")

    # 영업이익률 행
    def margin_str(rev, op):
        if rev and op and rev != 0:
            return f"{op / rev * 100:.1f}%"
        return "-"

    t.add_row(
        "영업이익률",
        margin_str(fin.get("revenue_prev2"), fin.get("operating_income_prev2")),
        margin_str(fin.get("revenue_prev"), fin.get("operating_income_prev")),
        "-",
        margin_str(fin.get("revenue"), fin.get("operating_income")),
    )

    console.print(t)


def _export_info_csv(item: dict, detail: Optional[dict], fin: Optional[dict]) -> None:
    filename = f"info_{item['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    d = detail or {}
    f = fin or {}
    rows = [
        ["항목", "값"],
        ["종목코드", item["code"]],
        ["종목명", item["name"]],
        ["시장구분", d.get("market_type", "")],
        ["업종", d.get("sector", "")],
        ["현재가", d.get("close", "")],
        ["전일대비(%)", d.get("change_pct", "")],
        ["시가총액(억)", round(d["mktcap"] / 1e8) if d.get("mktcap") else ""],
        ["상장주식수", d.get("shares", "")],
        ["52주 고가", d.get("high_52", "")],
        ["52주 저가", d.get("low_52", "")],
        [],
        ["재무항목", "전전기", "전기", "당기"],
        [
            "매출액(억)",
            round(f["revenue_prev2"] / 1e8) if f.get("revenue_prev2") else "",
            round(f["revenue_prev"] / 1e8) if f.get("revenue_prev") else "",
            round(f["revenue"] / 1e8) if f.get("revenue") else "",
        ],
        [
            "영업이익(억)",
            round(f["operating_income_prev2"] / 1e8) if f.get("operating_income_prev2") else "",
            round(f["operating_income_prev"] / 1e8) if f.get("operating_income_prev") else "",
            round(f["operating_income"] / 1e8) if f.get("operating_income") else "",
        ],
        [
            "당기순이익(억)",
            round(f["net_income_prev2"] / 1e8) if f.get("net_income_prev2") else "",
            round(f["net_income_prev"] / 1e8) if f.get("net_income_prev") else "",
            round(f["net_income"] / 1e8) if f.get("net_income") else "",
        ],
    ]
    with open(filename, "w", newline="", encoding="utf-8-sig") as fp:
        csv.writer(fp).writerows(rows)
    console.print(f"[green]CSV 저장 완료:[/green] {filename}")
