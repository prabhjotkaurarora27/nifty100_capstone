import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"


def generate_pros_cons():
    """Evaluates 12 Pro rules and 12 Con rules against company financial data.

    Exports output/pros_cons_generated.csv guaranteeing at least 1 pro and 1
    con per company.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    # Fetch companies metadata
    companies = pd.read_sql_query(
        "SELECT c.id, c.company_name, s.broad_sector FROM companies c LEFT JOIN sectors s ON c.id = s.company_id",
        conn,
    )

    # Fetch full ratio history per company
    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios ORDER BY company_id, year ASC", conn
    )

    # Fetch P&L history per company
    pl_df = pd.read_sql_query(
        "SELECT * FROM profitandloss ORDER BY company_id, year ASC", conn
    )

    # Fetch Balance Sheet history per company
    bs_df = pd.read_sql_query(
        "SELECT * FROM balancesheet ORDER BY company_id, year ASC", conn
    )

    conn.close()

    results = []

    for _, comp in companies.iterrows():
        cid = comp["id"]
        c_ratios = ratios[ratios["company_id"] == cid]
        c_pl = pl_df[pl_df["company_id"] == cid]
        c_bs = bs_df[bs_df["company_id"] == cid]
        is_financial = comp["broad_sector"] == "Financials"

        if c_ratios.empty:
            continue

        latest_ratio = c_ratios.iloc[-1]
        latest_pl = c_pl.iloc[-1] if not c_pl.empty else None
        latest_bs = c_bs.iloc[-1] if not c_bs.empty else None

        matched_pros = []
        matched_cons = []

        # =====================================================================
        # PRO RULES (PR-01 to PR-12)
        # =====================================================================

        # PR-01: ROE > 20% sustained 3+ years
        roe_history = c_ratios["return_on_equity_pct"].dropna()
        if len(roe_history) >= 3 and (roe_history.tail(3) > 20).all():
            matched_pros.append(
                {
                    "rule_id": "PR-01",
                    "text": "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
                    "confidence_pct": min(
                        100, int(80 + (roe_history.tail(3).mean() - 20))
                    ),
                }
            )

        # PR-02: FCF positive 5+ consecutive years
        fcf_history = c_ratios["free_cash_flow_cr"].dropna()
        if len(fcf_history) >= 5 and (fcf_history.tail(5) > 0).all():
            matched_pros.append(
                {
                    "rule_id": "PR-02",
                    "text": "Strong free cash flow generation over 5 years signals healthy business fundamentals",
                    "confidence_pct": 90,
                }
            )

        # PR-03: D/E = 0 latest year
        de_val = latest_ratio.get("debt_to_equity")
        if pd.notnull(de_val) and de_val == 0:
            matched_pros.append(
                {
                    "rule_id": "PR-03",
                    "text": "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
                    "confidence_pct": 95,
                }
            )

        # PR-04: Revenue CAGR > 15% over 5yr
        rev_cagr = latest_ratio.get("revenue_cagr_5yr")
        if pd.notnull(rev_cagr) and rev_cagr > 15:
            matched_pros.append(
                {
                    "rule_id": "PR-04",
                    "text": f"Revenue growing at above 15% CAGR over 5 years ({rev_cagr:.1f}%) reflects strong business momentum",
                    "confidence_pct": min(100, int(75 + (rev_cagr - 15))),
                }
            )

        # PR-05: OPM > 25% latest year
        opm_val = latest_ratio.get("operating_profit_margin_pct")
        if pd.notnull(opm_val) and opm_val > 25:
            matched_pros.append(
                {
                    "rule_id": "PR-05",
                    "text": f"Operating profit margin above 25% ({opm_val:.1f}%) indicates strong pricing power and cost discipline",
                    "confidence_pct": min(100, int(80 + (opm_val - 25))),
                }
            )

        # PR-06: PAT CAGR > 20% over 5yr
        pat_cagr = latest_ratio.get("pat_cagr_5yr")
        if pd.notnull(pat_cagr) and pat_cagr > 20:
            matched_pros.append(
                {
                    "rule_id": "PR-06",
                    "text": f"Net profit compounding at above 20% over 5 years ({pat_cagr:.1f}%) creates significant shareholder value",
                    "confidence_pct": min(100, int(80 + (pat_cagr - 20))),
                }
            )

        # PR-07: ICR > 10 or Debt Free
        icr_val = latest_ratio.get("interest_coverage")
        icr_lbl = str(latest_ratio.get("icr_label", ""))
        if (
            icr_lbl == "Debt Free"
            or (pd.notnull(de_val) and de_val == 0)
            or (pd.notnull(icr_val) and icr_val > 10)
        ):
            matched_pros.append(
                {
                    "rule_id": "PR-07",
                    "text": "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
                    "confidence_pct": 85,
                }
            )

        # PR-08: Dividend Yield > 2% with FCF positive
        div_y = latest_ratio.get("dividend_yield_pct")
        fcf_latest = latest_ratio.get("free_cash_flow_cr")
        if (
            pd.notnull(div_y)
            and div_y > 2.0
            and pd.notnull(fcf_latest)
            and fcf_latest > 0
        ):
            matched_pros.append(
                {
                    "rule_id": "PR-08",
                    "text": f"Consistent dividend yield above 2% ({div_y:.2f}%) backed by positive free cash flow",
                    "confidence_pct": 85,
                }
            )

        # PR-09: EPS CAGR > 15% over 5yr
        eps_cagr = latest_ratio.get("eps_cagr_5yr")
        if pd.notnull(eps_cagr) and eps_cagr > 15:
            matched_pros.append(
                {
                    "rule_id": "PR-09",
                    "text": f"Earnings per share growing above 15% CAGR ({eps_cagr:.1f}%) indicates strong earnings quality and compounding",
                    "confidence_pct": min(100, int(75 + (eps_cagr - 15))),
                }
            )

        # PR-10: ROE improving 3 consecutive years
        if len(roe_history) >= 4:
            tail4 = roe_history.tail(4).values
            if tail4[1] > tail4[0] and tail4[2] > tail4[1] and tail4[3] > tail4[2]:
                matched_pros.append(
                    {
                        "rule_id": "PR-10",
                        "text": "Return on equity improving for 3 consecutive years shows strengthening business quality",
                        "confidence_pct": 80,
                    }
                )

        # PR-11: PAT CAGR > Revenue CAGR (Operating leverage benefit)
        if (
            pd.notnull(pat_cagr)
            and pd.notnull(rev_cagr)
            and pat_cagr > rev_cagr
            and pat_cagr > 5
        ):
            matched_pros.append(
                {
                    "rule_id": "PR-11",
                    "text": "Revenue growing slower than profits shows improving operating leverage and scale benefits",
                    "confidence_pct": 75,
                }
            )

        # PR-12: Assets growing with declining debt
        if len(c_bs) >= 2 and not is_financial:
            ta_hist = c_bs["total_assets"].dropna()
            b_hist = c_bs["borrowings"].dropna()
            if (
                len(ta_hist) >= 2
                and len(b_hist) >= 2
                and ta_hist.iloc[-1] > ta_hist.iloc[-2]
                and b_hist.iloc[-1] <= b_hist.iloc[-2]
            ):
                matched_pros.append(
                    {
                        "rule_id": "PR-12",
                        "text": "Growing asset base funded by internal accruals reflects self-sustaining growth",
                        "confidence_pct": 80,
                    }
                )

        # =====================================================================
        # CON RULES (CR-01 to CR-12)
        # =====================================================================

        # CR-01: D/E > 2.0 non-financial
        if not is_financial and pd.notnull(de_val) and de_val > 2.0:
            matched_cons.append(
                {
                    "rule_id": "CR-01",
                    "text": f"Debt-to-equity ratio of {de_val:.2f} is elevated for a non-financial company and warrants monitoring",
                    "confidence_pct": min(100, int(70 + (de_val - 2.0) * 10)),
                }
            )

        # CR-02: FCF negative 3 consecutive years
        if len(fcf_history) >= 3 and (fcf_history.tail(3) < 0).all():
            matched_cons.append(
                {
                    "rule_id": "CR-02",
                    "text": "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
                    "confidence_pct": 85,
                }
            )

        # CR-03: OPM declining 3 consecutive years
        opm_hist = c_ratios["operating_profit_margin_pct"].dropna()
        if len(opm_hist) >= 4:
            tail4 = opm_hist.tail(4).values
            if tail4[1] < tail4[0] and tail4[2] < tail4[1] and tail4[3] < tail4[2]:
                matched_cons.append(
                    {
                        "rule_id": "CR-03",
                        "text": "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
                        "confidence_pct": 80,
                    }
                )

        # CR-04: Net profit negative latest year
        np_latest = latest_pl.get("net_profit") if latest_pl is not None else None
        if pd.notnull(np_latest) and np_latest < 0:
            matched_cons.append(
                {
                    "rule_id": "CR-04",
                    "text": "Company reported a net loss in the most recent financial year",
                    "confidence_pct": 95,
                }
            )

        # CR-05: Revenue declining 2+ years
        if not c_pl.empty and len(c_pl) >= 3:
            sales_hist = c_pl["sales"].dropna()
            if (
                len(sales_hist) >= 3
                and sales_hist.iloc[-1] < sales_hist.iloc[-2]
                and sales_hist.iloc[-2] < sales_hist.iloc[-3]
            ):
                matched_cons.append(
                    {
                        "rule_id": "CR-05",
                        "text": "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
                        "confidence_pct": 85,
                    }
                )

        # CR-06: ICR < 1.5
        if (
            not is_financial
            and pd.notnull(icr_val)
            and icr_val < 1.5
            and icr_lbl != "Debt Free"
        ):
            matched_cons.append(
                {
                    "rule_id": "CR-06",
                    "text": f"Interest coverage ratio below 1.5x ({icr_val:.2f}x) indicates the company is at risk of not meeting its debt obligations",
                    "confidence_pct": 90,
                }
            )

        # CR-07: Dividend payout > 100%
        div_payout = latest_pl.get("dividend_payout") if latest_pl is not None else None
        if pd.notnull(div_payout) and div_payout > 100:
            matched_cons.append(
                {
                    "rule_id": "CR-07",
                    "text": f"Dividend payout ratio above 100% ({div_payout:.1f}%) means the company is paying dividends from reserves, which is unsustainable",
                    "confidence_pct": 85,
                }
            )

        # CR-08: D/E rising 3 consecutive years
        de_hist = c_ratios["debt_to_equity"].dropna()
        if len(de_hist) >= 4 and not is_financial:
            tail4 = de_hist.tail(4).values
            if tail4[1] > tail4[0] and tail4[2] > tail4[1] and tail4[3] > tail4[2]:
                matched_cons.append(
                    {
                        "rule_id": "CR-08",
                        "text": "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
                        "confidence_pct": 80,
                    }
                )

        # CR-09: EPS declining 3 consecutive years
        if not c_pl.empty and len(c_pl) >= 4:
            eps_hist = c_pl["eps"].dropna()
            if len(eps_hist) >= 4:
                tail4 = eps_hist.tail(4).values
                if tail4[1] < tail4[0] and tail4[2] < tail4[1] and tail4[3] < tail4[2]:
                    matched_cons.append(
                        {
                            "rule_id": "CR-09",
                            "text": "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
                            "confidence_pct": 80,
                        }
                    )

        # CR-10: ROCE < 10%
        roce_val = latest_ratio.get("return_on_capital_employed_pct")
        if pd.notnull(roce_val) and roce_val < 10:
            matched_cons.append(
                {
                    "rule_id": "CR-10",
                    "text": f"Return on capital employed below 10% ({roce_val:.1f}%) suggests the business is not generating sufficient returns on invested capital",
                    "confidence_pct": 75,
                }
            )

        # CR-11: Net Debt > 3x EBITDA
        net_debt = latest_ratio.get("net_debt_cr")
        if (
            not is_financial
            and pd.notnull(net_debt)
            and net_debt > 0
            and not c_pl.empty
        ):
            op = latest_pl.get("operating_profit", 0)
            if op > 0 and (net_debt / op) > 3.0:
                matched_cons.append(
                    {
                        "rule_id": "CR-11",
                        "text": f"Net debt exceeding 3 times EBITDA ({net_debt/op:.1f}x) is a high leverage ratio and limits financial flexibility",
                        "confidence_pct": 85,
                    }
                )

        # CR-12: Revenue CAGR < 5% over 5yr
        if pd.notnull(rev_cagr) and rev_cagr < 5:
            matched_cons.append(
                {
                    "rule_id": "CR-12",
                    "text": f"Revenue growing at below 5% over 5 years ({rev_cagr:.1f}%) lags inflation and suggests limited business momentum",
                    "confidence_pct": 70,
                }
            )

        # =====================================================================
        # FALLBACK GUARANTEE: Ensure >= 1 Pro and >= 1 Con for EVERY company
        # =====================================================================
        if not matched_pros:
            # Fallback Pro rule
            roe_l = latest_ratio.get("return_on_equity_pct", 0)
            if pd.notnull(roe_l) and roe_l > 10:
                matched_pros.append(
                    {
                        "rule_id": "PR-FB",
                        "text": f"Healthy return on equity of {roe_l:.1f}% demonstrates stable profitability",
                        "confidence_pct": 70,
                    }
                )
            else:
                matched_pros.append(
                    {
                        "rule_id": "PR-FB",
                        "text": "Established market positioning in Nifty 100 index with active operational footprint",
                        "confidence_pct": 65,
                    }
                )

        if not matched_cons:
            # Fallback Con rule
            pe_val = latest_ratio.get("pe_ratio")
            if pd.notnull(pe_val) and pe_val > 40:
                matched_cons.append(
                    {
                        "rule_id": "CR-FB",
                        "text": f"Valuation ratio of P/E {pe_val:.1f}x is elevated relative to broader market averages",
                        "confidence_pct": 70,
                    }
                )
            elif pd.notnull(rev_cagr) and rev_cagr < 10:
                matched_cons.append(
                    {
                        "rule_id": "CR-FB",
                        "text": f"Moderate 5-year revenue growth of {rev_cagr:.1f}% indicates maturing market conditions",
                        "confidence_pct": 65,
                    }
                )
            else:
                matched_cons.append(
                    {
                        "rule_id": "CR-FB",
                        "text": "Exposure to macroeconomic cyclicality and industry competitive shifts",
                        "confidence_pct": 65,
                    }
                )

        # Append to master results
        for p in matched_pros:
            if p["confidence_pct"] > 60:
                results.append(
                    {
                        "company_id": cid,
                        "type": "pro",
                        "rule_id": p["rule_id"],
                        "text": p["text"],
                        "confidence_pct": p["confidence_pct"],
                    }
                )

        for c in matched_cons:
            if c["confidence_pct"] > 60:
                results.append(
                    {
                        "company_id": cid,
                        "type": "con",
                        "rule_id": c["rule_id"],
                        "text": c["text"],
                        "confidence_pct": c["confidence_pct"],
                    }
                )

    res_df = pd.DataFrame(results)

    # Export output/pros_cons_generated.csv
    csv_path = OUTPUT_DIR / "pros_cons_generated.csv"
    res_df.to_csv(csv_path, index=False)

    # Verification: Check every company has >= 1 pro and >= 1 con
    unique_companies = res_df["company_id"].unique()
    pros_companies = res_df[res_df["type"] == "pro"]["company_id"].unique()
    cons_companies = res_df[res_df["type"] == "con"]["company_id"].unique()

    print(
        f"✅ Exported {len(res_df)} rules across {len(unique_companies)} companies to {csv_path.name}"
    )
    print(f"  - Companies with 1+ Pro: {len(pros_companies)} / {len(companies)}")
    print(f"  - Companies with 1+ Con: {len(cons_companies)} / {len(companies)}")

    return res_df


if __name__ == "__main__":
    generate_pros_cons()
