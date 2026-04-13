"""보고서 Markdown 생성 단위 테스트."""

from services.report_service import generate_daily_report_markdown


class TestGenerateDailyReportMarkdown:
    def test_with_recommendations(self):
        md = generate_daily_report_markdown(
            regime_data={"regime": "selective", "vix": 22.5, "buffett_ratio": 1.28, "fear_greed_score": 45},
            recommendations=[{
                "name": "삼성전자", "code": "005930", "safety_grade": "A",
                "discount_rate": 35, "entry_price": 62000, "recommended_qty": 80,
                "stop_loss": 55800, "take_profit": 82500, "risk_reward": 2.8,
            }],
            market="KR",
            date="2026-04-13",
        )
        assert "# 일일 투자 보고서 (2026-04-13 / KR)" in md
        assert "selective" in md
        assert "삼성전자" in md
        assert "62,000" in md
        assert "등급 A" in md

    def test_empty_recommendations(self):
        md = generate_daily_report_markdown(
            regime_data={"regime": "defensive", "vix": 40},
            recommendations=[],
            market="KR",
            date="2026-04-13",
        )
        assert "매수 추천 없음" in md
        assert "defensive" in md

    def test_no_regime_data(self):
        md = generate_daily_report_markdown(
            regime_data=None,
            recommendations=[],
            market="US",
            date="2026-04-13",
        )
        assert "US" in md
        assert "시장 체제" not in md

    def test_multiple_recommendations(self):
        recs = [
            {"name": "A종목", "code": "000001", "safety_grade": "A",
             "discount_rate": 40, "entry_price": 10000, "recommended_qty": 100,
             "stop_loss": 9000, "take_profit": 15000, "risk_reward": 5.0},
            {"name": "B종목", "code": "000002", "safety_grade": "B+",
             "discount_rate": 25, "entry_price": 5000, "recommended_qty": 200,
             "stop_loss": 4500, "take_profit": 7000, "risk_reward": 4.0},
        ]
        md = generate_daily_report_markdown(
            regime_data={"regime": "accumulation"},
            recommendations=recs,
            market="KR",
            date="2026-04-13",
        )
        assert "매수 추천 (2건)" in md
        assert "A종목" in md
        assert "B종목" in md
