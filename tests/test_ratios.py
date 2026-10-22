from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fsa.ratios import (compare_to_benchmark, compute_ratios, dupont_3, dupont_5, validate)

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(DATA / "financials.csv")


def one_company(**over):
    base = dict(company="X", year=2025, revenue=1000, cogs=600, ebitda=200, da=50, ebit=150,
                interest_expense=30, tax=30, net_income=90, cash=100, receivables=150, inventory=120,
                current_assets=370, total_assets=1000, payables=80, short_term_debt=50,
                current_liabilities=200, long_term_debt=250, equity=500)
    base.update(over)
    return pd.DataFrame([base])


def test_hand_computed_ratios():
    r = compute_ratios(one_company()).iloc[0]
    assert r["current_ratio"] == pytest.approx(370 / 200)
    assert r["quick_ratio"] == pytest.approx(250 / 200)
    assert r["debt_to_equity"] == pytest.approx(300 / 500)
    assert r["net_debt_to_ebitda"] == pytest.approx(200 / 200)
    assert r["interest_coverage"] == pytest.approx(150 / 30)
    assert r["gross_margin"] == pytest.approx(0.4)
    assert r["roe"] == pytest.approx(90 / 500)
    assert r["cash_conversion_cycle"] == pytest.approx(150 / 1000 * 365 + 120 / 600 * 365 - 80 / 600 * 365)


def test_dupont_3_reproduces_roe(df):
    d = dupont_3(df)
    assert d["roe"].to_numpy() == pytest.approx(compute_ratios(df)["roe"].to_numpy())


def test_dupont_5_reproduces_roe(df):
    d = dupont_5(df)
    assert d["roe"].to_numpy() == pytest.approx(compute_ratios(df)["roe"].to_numpy())


def test_sample_data_is_internally_consistent(df):
    ebt = df["ebit"] - df["interest_expense"]
    assert (df["net_income"] - (ebt - df["tax"])).abs().max() < 0.2
    assert (df["ebitda"] - df["da"] - df["ebit"]).abs().max() < 0.2
    liab_eq = df["current_liabilities"] + df["long_term_debt"] + df["equity"]
    assert (liab_eq - df["total_assets"]).abs().max() < 0.3


def test_zero_interest_gives_nan_coverage_not_error():
    r = compute_ratios(one_company(interest_expense=0))
    assert np.isnan(r["interest_coverage"].iloc[0])


def test_validate_reports_missing_columns():
    with pytest.raises(ValueError):
        validate(one_company().drop(columns=["equity"]))


def test_benchmark_verdict_direction():
    latest = pd.DataFrame({"debt_to_equity": [0.4], "roe": [0.20], "equity_multiplier": [3.0]}, index=["X"])
    bench = pd.Series({"debt_to_equity": 0.7, "roe": 0.11, "equity_multiplier": 1.9})
    out = compare_to_benchmark(latest, bench).set_index("ratio")["verdict"]
    assert out["debt_to_equity"] == "better"     # lower leverage is better
    assert out["roe"] == "better"
    assert out["equity_multiplier"] == "n/a"
    inline = compare_to_benchmark(pd.DataFrame({"roe": [0.112]}, index=["X"]), pd.Series({"roe": 0.11}))
    assert inline["verdict"].iloc[0] == "in line"


def test_score_is_positive_when_better():
    latest = pd.DataFrame({"debt_to_equity": [0.35], "roe": [0.22]}, index=["X"])
    bench = pd.Series({"debt_to_equity": 0.7, "roe": 0.11})
    out = compare_to_benchmark(latest, bench).set_index("ratio")["score"]
    assert out["debt_to_equity"] == pytest.approx(0.5)
    assert out["roe"] == pytest.approx(1.0)
