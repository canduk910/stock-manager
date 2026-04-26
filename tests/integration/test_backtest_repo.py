"""BacktestRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.backtest_repo import BacktestRepository


class TestBacktestJob:
    def test_create_job(self, db_session):
        repo = BacktestRepository(db_session)
        job = repo.create_job(1, 
            job_id="job-001",
            strategy_name="SMA Cross",
            symbol="005930",
            market="KR",
            strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        assert job["job_id"] == "job-001"
        assert job["status"] == "submitted"
        assert job["symbol"] == "005930"

    def test_update_job_result(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-001", strategy_name="SMA Cross",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        ok = repo.update_job_result(
            "job-001",
            metrics={
                "total_return_pct": 25.5,
                "cagr": 12.3,
                "sharpe_ratio": 1.5,
                "max_drawdown": -10.2,
                "win_rate": 60.0,
                "total_trades": 42,
            },
            result_json={"equity_curve": [100, 110, 125]},
            completed_at="2026-04-19T11:00:00",
        )
        db_session.commit()
        assert ok is True

        job = repo.get_job("job-001")
        assert job["status"] == "completed"
        assert job["total_return_pct"] == 25.5
        assert job["cagr"] == 12.3
        assert job["result_json"]["equity_curve"] == [100, 110, 125]

    def test_update_job_result_nonexistent(self, db_session):
        repo = BacktestRepository(db_session)
        ok = repo.update_job_result(
            "nonexistent", metrics={}, result_json={},
            completed_at="2026-04-19T11:00:00",
        )
        assert ok is False

    def test_update_job_status(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-001", strategy_name="SMA Cross",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        ok = repo.update_job_status("job-001", "failed")
        db_session.commit()
        assert ok is True

        job = repo.get_job("job-001")
        assert job["status"] == "failed"
        assert job["completed_at"] is not None

    def test_update_job_status_nonexistent(self, db_session):
        repo = BacktestRepository(db_session)
        ok = repo.update_job_status("nonexistent", "failed")
        assert ok is False

    def test_get_job(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-001", strategy_name="SMA Cross",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        job = repo.get_job("job-001")
        assert job is not None
        assert job["strategy_name"] == "SMA Cross"

    def test_get_job_nonexistent(self, db_session):
        repo = BacktestRepository(db_session)
        assert repo.get_job("nonexistent") is None

    def test_get_latest_metrics(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-001", strategy_name="SMA Cross",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        repo.create_job(1, 
            job_id="job-002", strategy_name="RSI",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T11:00:00",
        )
        db_session.commit()

        # job-001 완료
        repo.update_job_result(
            "job-001",
            metrics={"total_return_pct": 10.0, "cagr": 5.0},
            result_json={},
            completed_at="2026-04-19T10:30:00",
        )
        # job-002 완료
        repo.update_job_result(
            "job-002",
            metrics={"total_return_pct": 20.0, "cagr": 10.0},
            result_json={},
            completed_at="2026-04-19T11:30:00",
        )
        db_session.commit()

        metrics = repo.get_latest_metrics("005930", "KR")
        assert metrics is not None
        assert metrics["job_id"] == "job-002"
        assert metrics["total_return_pct"] == 20.0

    def test_get_latest_metrics_no_completed(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-001", strategy_name="SMA",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        # submitted 상태 — completed가 없으므로 None
        assert repo.get_latest_metrics("005930", "KR") is None

    def test_list_jobs_filter(self, db_session):
        repo = BacktestRepository(db_session)
        repo.create_job(1, 
            job_id="job-kr", strategy_name="SMA",
            symbol="005930", market="KR", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        repo.create_job(1, 
            job_id="job-us", strategy_name="RSI",
            symbol="AAPL", market="US", strategy_type="preset",
            submitted_at="2026-04-19T10:00:00",
        )
        db_session.commit()

        kr_jobs = repo.list_jobs(1, market="KR")
        assert len(kr_jobs) == 1
        assert kr_jobs[0]["symbol"] == "005930"

        all_jobs = repo.list_jobs(1, )
        assert len(all_jobs) == 2

        aapl_jobs = repo.list_jobs(1, symbol="AAPL")
        assert len(aapl_jobs) == 1


class TestStrategy:
    def test_save_strategy(self, db_session):
        repo = BacktestRepository(db_session)
        strategy = repo.save_strategy(1, 
            name="My SMA", strategy_type="custom",
            description="SMA crossover", yaml_content="sma: {fast: 5, slow: 20}",
        )
        db_session.commit()

        assert strategy["name"] == "My SMA"
        assert strategy["strategy_type"] == "custom"

    def test_save_strategy_upsert(self, db_session):
        repo = BacktestRepository(db_session)
        repo.save_strategy(1, name="My SMA", strategy_type="custom", description="v1")
        db_session.commit()

        # 같은 이름으로 다시 저장 → 덮어쓰기
        updated = repo.save_strategy(1, 
            name="My SMA", strategy_type="custom", description="v2",
        )
        db_session.commit()

        assert updated["description"] == "v2"

        strategies = repo.list_strategies(1, )
        assert len(strategies) == 1

    def test_list_strategies(self, db_session):
        repo = BacktestRepository(db_session)
        repo.save_strategy(1, name="SMA", strategy_type="preset")
        repo.save_strategy(1, name="Custom1", strategy_type="custom")
        db_session.commit()

        all_s = repo.list_strategies(1, )
        assert len(all_s) == 2

        presets = repo.list_strategies(1, strategy_type="preset")
        assert len(presets) == 1
        assert presets[0]["name"] == "SMA"

    def test_list_strategies_empty(self, db_session):
        repo = BacktestRepository(db_session)
        assert repo.list_strategies(1, ) == []
