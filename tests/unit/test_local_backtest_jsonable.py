"""REQ-FIX-04: numpy/pandas → Python native 재귀 변환.

`result_json` 안의 numpy float/int, pd.Timestamp가 FastAPI JSON 인코딩 단계에서 실패 → raw 500.

본 fix:
- `services/local_backtest/engine.py` 의 `_to_jsonable(obj)` 헬퍼 (재귀)
- numpy float64/int64 → Python float/int
- pd.Timestamp → ISO 문자열
- 중첩 dict/list 재귀 처리
- run_local_backtest 응답 직전에 한 번 더 적용 (이중 안전망)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from services.local_backtest.engine import _to_jsonable


def test_numpy_scalars_converted():
    """(a) numpy float64/int64 → Python native → json.dumps 통과."""
    obj = {
        "v_f64": np.float64(1.5),
        "v_i64": np.int64(42),
        "v_f32": np.float32(2.5),
        "v_i32": np.int32(10),
    }
    out = _to_jsonable(obj)
    assert isinstance(out["v_f64"], float)
    assert isinstance(out["v_i64"], int)
    assert isinstance(out["v_f32"], float)
    assert isinstance(out["v_i32"], int)
    json.dumps(out)  # raise 없으면 OK


def test_pandas_timestamp_to_iso_string():
    """(b) pd.Timestamp → ISO 문자열."""
    ts = pd.Timestamp("2024-06-01 10:00:00", tz="Asia/Seoul")
    out = _to_jsonable({"date": ts})
    assert isinstance(out["date"], str)
    assert "2024-06-01" in out["date"]
    json.dumps(out)


def test_nested_dict_list_recursion():
    """(c) 중첩 dict/list 재귀 변환."""
    obj = {
        "trades": [
            {"qty": np.int64(100), "pnl": np.float64(123.45), "date": pd.Timestamp("2024-01-15")},
            {"qty": np.int64(50), "pnl": np.float64(-10.0), "date": pd.Timestamp("2024-02-01")},
        ],
        "metrics": {"sharpe": np.float64(1.2), "n": np.int64(5)},
    }
    out = _to_jsonable(obj)
    json.dumps(out)
    assert isinstance(out["trades"][0]["qty"], int)
    assert isinstance(out["trades"][0]["pnl"], float)
    assert isinstance(out["trades"][0]["date"], str)
    assert isinstance(out["metrics"]["sharpe"], float)


def test_nan_inf_become_none():
    """(d) NaN/Inf 는 JSON spec 위반이므로 None 으로 변환."""
    obj = {"a": float("nan"), "b": float("inf"), "c": float("-inf"), "d": np.nan}
    out = _to_jsonable(obj)
    json.dumps(out)
    assert out["a"] is None
    assert out["b"] is None
    assert out["c"] is None
    assert out["d"] is None


def test_native_python_passthrough():
    """(e) Python native 타입 (str/int/float/list/dict/None/bool) 은 그대로."""
    obj = {"s": "hello", "i": 1, "f": 2.5, "l": [1, 2, 3], "n": None, "b": True}
    out = _to_jsonable(obj)
    assert out == obj
    json.dumps(out)
