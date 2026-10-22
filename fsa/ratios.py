"""Financial ratio analysis: liquidity, leverage, profitability, efficiency and DuPont."""
from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "company", "year", "revenue", "cogs", "ebitda", "da", "ebit", "interest_expense", "tax",
    "net_income", "cash", "receivables", "inventory", "current_assets", "total_assets", "payables",
    "short_term_debt", "current_liabilities", "long_term_debt", "equity",
]

# True: higher is better. False: lower is better. None: no clear direction (shown as informative).
DIRECTION = {
    "current_ratio": True, "quick_ratio": True, "cash_ratio": True,
    "debt_to_equity": False, "net_debt_to_ebitda": False, "interest_coverage": True, "debt_to_assets": False,
    "gross_margin": True, "ebitda_margin": True, "ebit_margin": True, "net_margin": True,
    "roa": True, "roe": True, "asset_turnover": True, "equity_multiplier": None,
    "dso": False, "dio": False, "dpo": None, "cash_conversion_cycle": False,
}

GROUPS = {
    "Liquidity": ["current_ratio", "quick_ratio", "cash_ratio"],
    "Leverage": ["debt_to_equity", "net_debt_to_ebitda", "interest_coverage", "debt_to_assets"],
    "Profitability": ["gross_margin", "ebitda_margin", "ebit_margin", "net_margin", "roa", "roe"],
    "Efficiency": ["asset_turnover", "dso", "dio", "dpo", "cash_conversion_cycle"],
}


def validate(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")


def compute_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row of ratios per company and year. Balance sheet items are year-end values."""
    validate(df)
    d = df.set_index(["company", "year"]).sort_index()
    debt = d["short_term_debt"] + d["long_term_debt"]
    net_debt = debt - d["cash"]
    r = pd.DataFrame(index=d.index)

    r["current_ratio"] = d["current_assets"] / d["current_liabilities"]
    r["quick_ratio"] = (d["cash"] + d["receivables"]) / d["current_liabilities"]
    r["cash_ratio"] = d["cash"] / d["current_liabilities"]

    r["debt_to_equity"] = debt / d["equity"]
    r["net_debt_to_ebitda"] = net_debt / d["ebitda"]
    r["interest_coverage"] = d["ebit"] / d["interest_expense"].replace(0, np.nan)
    r["debt_to_assets"] = debt / d["total_assets"]

    r["gross_margin"] = (d["revenue"] - d["cogs"]) / d["revenue"]
    r["ebitda_margin"] = d["ebitda"] / d["revenue"]
    r["ebit_margin"] = d["ebit"] / d["revenue"]
    r["net_margin"] = d["net_income"] / d["revenue"]
    r["roa"] = d["net_income"] / d["total_assets"]
    r["roe"] = d["net_income"] / d["equity"]

    r["asset_turnover"] = d["revenue"] / d["total_assets"]
    r["equity_multiplier"] = d["total_assets"] / d["equity"]
    r["dso"] = d["receivables"] / d["revenue"] * 365
    r["dio"] = d["inventory"] / d["cogs"] * 365
    r["dpo"] = d["payables"] / d["cogs"] * 365
    r["cash_conversion_cycle"] = r["dso"] + r["dio"] - r["dpo"]
    return r


def dupont_3(df: pd.DataFrame) -> pd.DataFrame:
    """ROE = net margin x asset turnover x equity multiplier."""
    r = compute_ratios(df)
    out = r[["net_margin", "asset_turnover", "equity_multiplier"]].copy()
    out["roe"] = out["net_margin"] * out["asset_turnover"] * out["equity_multiplier"]
    return out


def dupont_5(df: pd.DataFrame) -> pd.DataFrame:
    """ROE = tax burden x interest burden x EBIT margin x asset turnover x equity multiplier."""
    validate(df)
    d = df.set_index(["company", "year"]).sort_index()
    ebt = d["ebit"] - d["interest_expense"]
    out = pd.DataFrame(index=d.index)
    out["tax_burden"] = d["net_income"] / ebt                    # NI / EBT
    out["interest_burden"] = ebt / d["ebit"]                     # EBT / EBIT
    out["ebit_margin"] = d["ebit"] / d["revenue"]
    out["asset_turnover"] = d["revenue"] / d["total_assets"]
    out["equity_multiplier"] = d["total_assets"] / d["equity"]
    out["roe"] = out.prod(axis=1)
    return out


def compare_to_benchmark(latest: pd.DataFrame, benchmark: pd.Series, tolerance: float = 0.05) -> pd.DataFrame:
    """Compare a ratios table (rows: companies) to benchmark values.

    Returns a long table with the company value, benchmark, relative gap, a direction-adjusted score and a verdict
    ('better', 'worse', 'in line' within +/- tolerance, or 'n/a' when no direction applies).
    """
    rows = []
    for company, vals in latest.iterrows():
        for ratio, bench in benchmark.items():
            if ratio not in vals.index:
                continue
            v = vals[ratio]
            gap = (v - bench) / abs(bench) if bench else np.nan
            direction = DIRECTION.get(ratio)
            if direction is None or np.isnan(gap):
                verdict = "n/a"
            elif abs(gap) <= tolerance:
                verdict = "in line"
            else:
                verdict = "better" if (gap > 0) == direction else "worse"
            # score: relative gap oriented so that positive always means "better than benchmark"
            score = np.nan if direction is None else (gap if direction else -gap)
            rows.append(dict(company=company, ratio=ratio, value=v, benchmark=bench, gap=gap,
                             score=score, verdict=verdict))
    return pd.DataFrame(rows)
