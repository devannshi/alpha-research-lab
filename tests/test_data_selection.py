import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from alpha_research.data import parse_french_daily, validate_returns
from alpha_research.selection import information_coefficient, select_candidate


def archive(text):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as out:
        out.writestr("test.csv", text)
    return buffer.getvalue()


def test_parser_selects_first_value_weighted_panel_and_scales():
    text = "Header\n  Average Value Weighted Returns -- Daily\n,A,B\n20000103,1.00,-99.99\n20000104,-2.00,3.00\n\nAverage Equal Weighted Returns\n,A,B\n20000103,99,99\n"
    result, meta = parse_french_daily(archive(text))
    assert len(result) == 2
    assert result.iloc[0, 0] == .01
    assert np.isnan(result.iloc[0, 1])
    assert result.iloc[1, 0] == -.02
    assert meta["missing_cells"] == 1


def test_parser_rejects_missing_panel_marker():
    with pytest.raises(ValueError):
        parse_french_daily(archive("No daily data"))


def test_duplicate_dates_rejected():
    frame = pd.DataFrame([[0, 0], [0, 0]], index=pd.to_datetime(["2000-01-03"] * 2))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_returns(frame)


def result_frame(values):
    return pd.DataFrame({"net_return": values, "turnover": 0., "gross_exposure": 1., "net_exposure": 0.},
                         index=pd.bdate_range("2010-01-01", periods=len(values)))


def test_selection_ignores_returns_after_cutoff():
    rng = np.random.default_rng(15)
    data = {"a": result_frame(rng.normal(.001, .01, 100)),
            "b": result_frame(rng.normal(0, .01, 100))}
    cutoff = data["a"].index[60]
    winner, _ = select_candidate(data, cutoff)
    data["b"].loc[data["b"].index > cutoff, "net_return"] = 100
    changed, _ = select_candidate(data, cutoff)
    assert winner == changed


def test_selection_ties_use_candidate_name():
    frame = result_frame(np.linspace(-.01, .01, 100))
    winner, _ = select_candidate({"z": frame, "a": frame}, frame.index[-1])
    assert winner == "a"


def test_ic_labels_start_after_execution_close():
    dates = pd.bdate_range("2020-01-01", periods=80)
    r = pd.DataFrame(np.tile(np.linspace(-.01, .01, 5), (80, 1)), index=dates)
    scores = r.copy()
    result = information_coefficient(r, scores, horizon=5, min_eligible=3)
    row = result.iloc[0]
    decision_i = dates.get_loc(row.decision_date)
    assert row.execution_date == dates[decision_i + 1]
    assert row.label_start == dates[decision_i + 2]
    assert row.label_end == dates[decision_i + 6]
    np.testing.assert_allclose(row.rank_ic, 1)

