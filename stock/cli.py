"""관심종목 관리 CLI.

사용법:
    python -m stock watch add 005930 --memo "반도체 업황 회복"
    python -m stock watch list
    python -m stock watch dashboard
    python -m stock watch info 005930
"""

import sys

import click
from rich.console import Console

console = Console()


# ── 공통 헬퍼 ───────────────────────────────────────────────────────────────

def _resolve_or_exit(code_or_name: str, refresh: bool = False) -> tuple[str, str]:
    """종목코드/종목명 → (code, name). 실패 시 에러 출력 후 종료."""
    from .symbol_map import name_to_results, resolve

    result = resolve(code_or_name, refresh=refresh)
    if result:
        return result

    import re
    if re.match(r"^\d{6}$", code_or_name):
        console.print(f"[red]종목코드 '{code_or_name}'를 찾을 수 없습니다.[/red]")
        console.print("[dim]종목 캐시를 갱신하려면 --refresh 옵션을 사용하세요.[/dim]")
        sys.exit(1)

    # 이름 검색 결과가 복수인 경우 목록 출력
    matches = name_to_results(code_or_name, refresh=refresh)
    if not matches:
        console.print(f"[red]'{code_or_name}'에 해당하는 종목이 없습니다.[/red]")
        sys.exit(1)

    console.print(f"[yellow]'{code_or_name}'에 해당하는 종목이 여러 개입니다:[/yellow]")
    for code, name, market in matches[:10]:
        console.print(f"  [cyan]{code}[/cyan]  {name}  ({market})")
    if len(matches) > 10:
        console.print(f"  ... 외 {len(matches) - 10}개")
    console.print("[dim]종목코드를 직접 입력하세요.[/dim]")
    sys.exit(1)


# ── CLI 그룹 정의 ────────────────────────────────────────────────────────────

@click.group()
def stock():
    """주식 관리 CLI."""
    pass


@stock.group()
def watch():
    """관심종목 관리."""
    pass


# ── watch add ────────────────────────────────────────────────────────────────

@watch.command("add")
@click.argument("code_or_name")
@click.option("--memo", "-m", default="", help="메모")
@click.option("--refresh", is_flag=True, help="종목 캐시 갱신 후 검색")
def watch_add(code_or_name: str, memo: str, refresh: bool):
    """관심종목 추가. 종목코드 또는 종목명 입력 가능.

    \b
    예시:
      stock watch add 005930
      stock watch add 삼성전자 --memo "반도체 업황 회복"
    """
    console.print("[dim]종목 정보 조회 중...[/dim]")
    code, name = _resolve_or_exit(code_or_name, refresh=refresh)

    from .store import add_item

    if add_item(code, name, memo):
        console.print(f"[green]추가 완료:[/green] {name} ({code})")
        if memo:
            console.print(f"  메모: {memo}")
    else:
        console.print(f"[yellow]이미 등록된 종목입니다:[/yellow] {name} ({code})")


# ── watch remove ─────────────────────────────────────────────────────────────

@watch.command("remove")
@click.argument("code_or_name")
@click.option("--refresh", is_flag=True, hidden=True)
def watch_remove(code_or_name: str, refresh: bool):
    """관심종목 삭제.

    \b
    예시:
      stock watch remove 005930
      stock watch remove 삼성전자
    """
    from .store import all_items, remove_item

    import re
    # watchlist에서 먼저 검색 (오프라인에서도 삭제 가능)
    items = all_items()
    if re.match(r"^\d{6}$", code_or_name):
        target = next((i for i in items if i["code"] == code_or_name), None)
    else:
        target = next((i for i in items if i["name"] == code_or_name), None)

    if not target:
        console.print(f"[red]관심종목에 없는 종목입니다:[/red] {code_or_name}")
        sys.exit(1)

    code, name = target["code"], target["name"]
    if remove_item(code):
        console.print(f"[green]삭제 완료:[/green] {name} ({code})")
    else:
        console.print(f"[red]삭제 실패:[/red] {name} ({code})")


# ── watch list ───────────────────────────────────────────────────────────────

@watch.command("list")
def watch_list():
    """관심종목 목록 출력."""
    from .store import all_items
    from .display import print_watchlist

    print_watchlist(all_items())


# ── watch memo ───────────────────────────────────────────────────────────────

@watch.command("memo")
@click.argument("code_or_name")
@click.argument("text")
def watch_memo(code_or_name: str, text: str):
    """메모 수정.

    \b
    예시:
      stock watch memo 005930 "목표가 90,000원"
      stock watch memo 삼성전자 "목표가 90,000원"
    """
    from .store import all_items, update_memo

    import re
    items = all_items()
    if re.match(r"^\d{6}$", code_or_name):
        target = next((i for i in items if i["code"] == code_or_name), None)
    else:
        target = next((i for i in items if i["name"] == code_or_name), None)

    if not target:
        console.print(f"[red]관심종목에 없는 종목입니다:[/red] {code_or_name}")
        sys.exit(1)

    code, name = target["code"], target["name"]
    if update_memo(code, text):
        console.print(f"[green]메모 수정 완료:[/green] {name} ({code})")
        console.print(f"  → {text}")
    else:
        console.print(f"[red]메모 수정 실패[/red]")


# ── watch dashboard ──────────────────────────────────────────────────────────

@watch.command("dashboard")
@click.option("--refresh", is_flag=True, help="캐시 무시하고 최신 데이터 조회")
@click.option("--export", "export_fmt", type=click.Choice(["csv"]), default=None, help="CSV 내보내기")
def watch_dashboard(refresh: bool, export_fmt):
    """관심종목 전체 대시보드 출력.

    \b
    예시:
      stock watch dashboard
      stock watch dashboard --refresh
      stock watch dashboard --export csv
    """
    from .store import all_items
    from .market import fetch_price
    from .dart_fin import fetch_financials
    from .display import print_dashboard

    items = all_items()
    if not items:
        console.print("[yellow]관심종목이 없습니다.[/yellow]")
        return

    rows = []
    for item in items:
        code = item["code"]
        console.print(f"[dim]  조회 중: {item['name']} ({code})...[/dim]")

        price = None
        fin = None

        try:
            price = fetch_price(code, refresh=refresh)
        except Exception as e:
            console.print(f"  [red]시세 오류 ({code}): {e}[/red]")

        try:
            fin = fetch_financials(code, refresh=refresh)
        except Exception as e:
            console.print(f"  [red]재무 오류 ({code}): {e}[/red]")

        rows.append({"code": code, "name": item["name"], "price": price, "fin": fin})

    print_dashboard(rows, export=export_fmt)


# ── watch info ───────────────────────────────────────────────────────────────

@watch.command("info")
@click.argument("code_or_name")
@click.option("--refresh", is_flag=True, help="캐시 무시하고 최신 데이터 조회")
@click.option("--export", "export_fmt", type=click.Choice(["csv"]), default=None, help="CSV 내보내기")
def watch_info(code_or_name: str, refresh: bool, export_fmt):
    """단일 종목 상세 조회 (기본정보 + 최근 3개년 재무).

    \b
    예시:
      stock watch info 005930
      stock watch info 삼성전자
      stock watch info 005930 --export csv
    """
    from .store import get_item
    from .market import fetch_detail
    from .dart_fin import fetch_financials
    from .display import print_stock_info

    import re

    # watchlist에 있으면 메모도 포함, 없으면 심볼맵에서 조회
    if re.match(r"^\d{6}$", code_or_name):
        item = get_item(code_or_name)
        if not item:
            code, name = _resolve_or_exit(code_or_name, refresh=refresh)
            item = {"code": code, "name": name, "memo": ""}
    else:
        from .store import all_items
        stored = next((i for i in all_items() if i["name"] == code_or_name), None)
        if stored:
            item = stored
        else:
            code, name = _resolve_or_exit(code_or_name, refresh=refresh)
            item = {"code": code, "name": name, "memo": ""}

    code = item["code"]
    console.print(f"[dim]{item['name']} ({code}) 조회 중...[/dim]")

    detail = None
    fin = None

    try:
        detail = fetch_detail(code, refresh=refresh)
        if detail is None:
            console.print(f"[red]종목코드 '{code}'의 시세 정보를 찾을 수 없습니다.[/red]")
    except Exception as e:
        console.print(f"[red]시세 조회 오류: {e}[/red]")

    try:
        fin = fetch_financials(code, refresh=refresh)
    except Exception as e:
        console.print(f"[red]재무 조회 오류: {e}[/red]")

    print_stock_info(item, detail, fin, export=export_fmt)
