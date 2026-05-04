"""매크로 음영 이벤트 — NBER 침체 + S&P500 -20% 약세장.

R2 (2026-05-04, 사용자 요청): 장단기 금리차/HY OAS 그래프에 경기침체와 S&P -20%
폭락 구간을 시각적으로 표시하기 위한 정적 데이터 + 범위 필터 헬퍼.

출처:
  NBER Business Cycle Dating Committee — 미국 경제 침체 시작/종료 공식 발표
    https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions
  Macrotrends / Yardeni Research — S&P 500 약세장(고점 대비 -20% 이상) 통계
    https://www.macrotrends.net/2324/sp-500-historical-chart-data
    https://winthropwealth.com/wp-content/uploads/2023/01/SP-500-Bear-Markets-CQ.pdf

도메인 자문 합의 (MacroSentinel):
  - 두 시계열은 의미가 다르다: NBER는 실물경제 침체, S&P 약세장은 자산가격 패닉.
  - 둘 다 표시하되 색상/투명도를 달리해 시각적 구분: 침체=회색 alpha 0.15,
    약세장=붉은색 alpha 0.10. 침체가 위 레이어.
"""

from __future__ import annotations

from typing import Optional

# NBER Business Cycle Dating Committee 공식 침체 기간 (2000년 이후)
NBER_RECESSIONS: list[dict] = [
    {"start": "2001-03-01", "end": "2001-11-30", "label": "닷컴 침체"},
    {"start": "2007-12-01", "end": "2009-06-30", "label": "글로벌 금융위기"},
    {"start": "2020-02-01", "end": "2020-04-30", "label": "코로나 침체"},
]

# S&P 500 -20% 이상 약세장 (Macrotrends 종가 기준)
SP500_BEAR_MARKETS: list[dict] = [
    {"start": "2000-03-24", "end": "2002-10-09", "drawdown": -49.1, "label": "닷컴 약세장"},
    {"start": "2007-10-09", "end": "2009-03-09", "drawdown": -56.8, "label": "GFC 약세장"},
    {"start": "2020-02-19", "end": "2020-03-23", "drawdown": -33.9, "label": "코로나 약세장"},
    {"start": "2022-01-03", "end": "2022-10-12", "drawdown": -25.4, "label": "인플레 약세장"},
]


def _clip(event: dict, start: str, end: str) -> Optional[dict]:
    """주어진 입력 범위 [start, end]와 이벤트 기간이 겹치면 클립된 사본 반환.

    원본 시작/종료는 `original_start` / `original_end`로 보존(차트 툴팁 표시용).
    겹치지 않으면 None.
    """
    e_start = event["start"]
    e_end = event["end"]
    if e_end < start or e_start > end:
        return None
    return {
        **event,
        "original_start": e_start,
        "original_end": e_end,
        "start": max(e_start, start),
        "end": min(e_end, end),
    }


def get_events_in_range(start_date: str, end_date: str) -> dict:
    """주어진 기간 [start_date, end_date]와 겹치는 침체/약세장 이벤트 반환.

    날짜는 ISO 형식 "YYYY-MM-DD" 문자열. 입력 범위와 부분이라도 겹치면 포함하며,
    표시용 start/end는 입력 범위로 클립한다.

    Returns: {"recessions": [...], "bear_markets": [...]}
    """
    if not start_date or not end_date or start_date > end_date:
        return {"recessions": [], "bear_markets": []}
    rec = [c for c in (_clip(e, start_date, end_date) for e in NBER_RECESSIONS) if c]
    bear = [c for c in (_clip(e, start_date, end_date) for e in SP500_BEAR_MARKETS) if c]
    return {"recessions": rec, "bear_markets": bear}
