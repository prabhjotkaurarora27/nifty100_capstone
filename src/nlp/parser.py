import re
import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_FILE = PROJECT_ROOT / "data" / "raw" / "100" / "analysis.xlsx"
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

REGEX_PATTERN = re.compile(r"(\d+)\s*Years?:?\s*(-?[\d.]+)%", re.IGNORECASE)


def parse_analysis_file():
    """Parses text fields in analysis.xlsx using regex patterns and cross-validates

    parsed CAGR vs computed CAGR from the Ratio Engine.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {ANALYSIS_FILE}")

    # Read analysis.xlsx (header at row 1)
    df = pd.read_excel(ANALYSIS_FILE, header=1)

    target_fields = [
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ]

    parsed_rows = []
    failure_rows = []

    for idx, row in df.iterrows():
        company_id = str(row.get("company_id", "")).strip()
        if not company_id or company_id == "nan":
            continue

        for field in target_fields:
            cell_val = str(row.get(field, "")).strip()
            if not cell_val or cell_val == "nan":
                continue

            match = REGEX_PATTERN.search(cell_val)
            if match:
                period_years = int(match.group(1))
                value_pct = float(match.group(2))
                parsed_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": field,
                        "period_years": period_years,
                        "value_pct": value_pct,
                        "raw_text": cell_val,
                    }
                )
            else:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": field,
                        "raw_text": cell_val,
                        "reason": "Regex pattern mismatch",
                    }
                )

    parsed_df = pd.DataFrame(parsed_rows)
    failure_df = pd.DataFrame(failure_rows)

    # Export output/analysis_parsed.csv
    parsed_csv = OUTPUT_DIR / "analysis_parsed.csv"
    if not parsed_df.empty:
        parsed_df[
            ["company_id", "metric_type", "period_years", "value_pct"]
        ].to_csv(parsed_csv, index=False)
        print(f"✅ Exported {len(parsed_df)} parsed records to {parsed_csv.name}")
    else:
        pd.DataFrame(
            columns=["company_id", "metric_type", "period_years", "value_pct"]
        ).to_csv(parsed_csv, index=False)

    # Export output/parse_failures.csv
    failures_csv = OUTPUT_DIR / "parse_failures.csv"
    failure_df.to_csv(failures_csv, index=False)
    print(f"✅ Exported {len(failure_df)} parse failures to {failures_csv.name}")

    # Cross-validate parsed CAGR vs computed CAGR from Ratio Engine
    divergence_df = cross_validate_cagr(parsed_df)

    return parsed_df, failure_df, divergence_df


def cross_validate_cagr(parsed_df: pd.DataFrame) -> pd.DataFrame:
    """Cross-validates parsed sales/profit 5yr CAGR vs ratio engine computed

    ratios.
    """
    if parsed_df.empty:
        return pd.DataFrame()

    conn = sqlite3.connect(str(DB_PATH))
    ratios_query = """
        SELECT company_id, revenue_cagr_5yr, pat_cagr_5yr
        FROM financial_ratios
        WHERE year = (SELECT MAX(year) FROM financial_ratios)
    """
    db_ratios = pd.read_sql_query(ratios_query, conn)
    conn.close()

    divergences = []

    # Map target metric to DB column
    mapping = {
        "compounded_sales_growth": "revenue_cagr_5yr",
        "compounded_profit_growth": "pat_cagr_5yr",
    }

    for metric_type, db_col in mapping.items():
        subset = parsed_df[
            (parsed_df["metric_type"] == metric_type)
            & (parsed_df["period_years"] == 5)
        ]
        for _, row in subset.iterrows():
            cid = row["company_id"]
            parsed_val = row["value_pct"]

            db_match = db_ratios[db_ratios["company_id"] == cid]
            if not db_match.empty:
                db_val = db_match.iloc[0].get(db_col)
                if pd.notnull(db_val):
                    diff = abs(parsed_val - db_val)
                    divergence_flag = diff > 5.0
                    divergences.append(
                        {
                            "company_id": cid,
                            "metric_type": metric_type,
                            "period_years": 5,
                            "parsed_value_pct": parsed_val,
                            "ratio_engine_value_pct": db_val,
                            "abs_divergence": diff,
                            "divergence_flag": divergence_flag,
                        }
                    )

    divergence_df = pd.DataFrame(divergences)
    if not divergence_df.empty:
        flagged_count = divergence_df["divergence_flag"].sum()
        print(
            f"🔍 CAGR Cross-Validation: {len(divergence_df)} comparisons, {flagged_count} flagged with > 5% divergence."
        )

    return divergence_df


if __name__ == "__main__":
    parse_analysis_file()
