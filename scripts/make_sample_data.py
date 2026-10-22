"""Generate the fictional sample financial statements used in the notebook.

Three fictional European mid-cap industrial companies over FY2023-FY2025, built so that the
statements are internally consistent: the balance sheet balances (non-current assets are the
plug), equity rolls forward with net income and dividends, and net income follows the P&L.
Run from the repository root:  python scripts/make_sample_data.py
"""
from pathlib import Path

import pandas as pd

YEARS = [2023, 2024, 2025]
TAX = 0.25

COMPANIES = {
    "Alpine Industries": dict(rev=[1130, 1200, 1272], ebitda_m=[.150, .155, .160], da=.040, gross=.34,
                              st=[60, 60, 50], lt=[540, 520, 500], cash=[110, 130, 150], rate=.045,
                              ar=55, inv=80, ap=60, eq0=800, payout=.30),
    "Baltic Components": dict(rev=[640, 655, 690], ebitda_m=[.115, .105, .110], da=.050, gross=.27,
                              st=[90, 110, 100], lt=[200, 210, 190], cash=[40, 35, 45], rate=.055,
                              ar=62, inv=95, ap=52, eq0=260, payout=.25),
    "Iberia Machinery": dict(rev=[900, 960, 1010], ebitda_m=[.190, .195, .198], da=.045, gross=.41,
                             st=[30, 25, 25], lt=[150, 120, 100], cash=[210, 260, 320], rate=.035,
                             ar=48, inv=70, ap=65, eq0=900, payout=.35),
}


def build() -> pd.DataFrame:
    rows = []
    for name, p in COMPANIES.items():
        equity = None
        for i, year in enumerate(YEARS):
            rev = p["rev"][i]
            cogs = rev * (1 - p["gross"])
            ebitda = rev * p["ebitda_m"][i]
            da = rev * p["da"]
            ebit = ebitda - da
            debt = p["st"][i] + p["lt"][i]
            interest = debt * p["rate"]
            tax = (ebit - interest) * TAX
            net_income = ebit - interest - tax

            ar, inv = rev * p["ar"] / 365, cogs * p["inv"] / 365
            ap, other_cl = cogs * p["ap"] / 365, rev * 0.04
            cash = p["cash"][i]
            current_assets = cash + ar + inv
            current_liabilities = ap + other_cl + p["st"][i]

            equity = p["eq0"] if equity is None else equity + net_income * (1 - p["payout"])
            total_liab_equity = current_liabilities + p["lt"][i] + equity
            non_current_assets = total_liab_equity - current_assets

            rows.append(dict(
                company=name, year=year, revenue=rev, cogs=cogs, ebitda=ebitda, da=da, ebit=ebit,
                interest_expense=interest, tax=tax, net_income=net_income,
                cash=cash, receivables=ar, inventory=inv, current_assets=current_assets,
                non_current_assets=non_current_assets, total_assets=current_assets + non_current_assets,
                payables=ap, other_current_liabilities=other_cl, short_term_debt=p["st"][i],
                current_liabilities=current_liabilities, long_term_debt=p["lt"][i], equity=equity,
            ))
    return pd.DataFrame(rows).round(1)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "data"
    df = build()
    assert (df["non_current_assets"] > 0).all()
    df.to_csv(out / "financials.csv", index=False)
    print(df.to_string(index=False))
