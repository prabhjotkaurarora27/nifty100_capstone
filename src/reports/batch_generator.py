import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.reports.sector_report import generate_all_sector_reports
from src.reports.tearsheet import generate_company_tearsheet

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEARSHEETS_DIR = PROJECT_ROOT / "reports" / "tearsheets"


def run_batch_generation():
    """Batch generates tearsheets for all 92 companies, 11 sector reports, and

    logs skipped companies.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEARSHEETS_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))

    # Fetch all companies
    companies = pd.read_sql_query(
        "SELECT id, company_name FROM companies ORDER BY id ASC", conn
    )

    # Fetch financial history count per company
    history_counts = (
        pd.read_sql_query(
            "SELECT company_id, COUNT(DISTINCT year) as yr_count FROM financial_ratios GROUP BY company_id",
            conn,
        )
        .set_index("company_id")["yr_count"]
        .to_dict()
    )

    conn.close()

    generated_count = 0
    skipped_rows = []

    print("🚀 Starting Batch PDF Generation...")

    for _, comp in companies.iterrows():
        cid = comp["id"]
        c_name = comp["company_name"]
        yrs = history_counts.get(cid, 0)

        # Skip companies with < 3 years data
        if yrs < 3:
            skipped_rows.append(
                {
                    "company_id": cid,
                    "company_name": c_name,
                    "years_available": yrs,
                    "reason": "Insufficient financial history (< 3 years)",
                }
            )
            continue

        try:
            pdf_path = generate_company_tearsheet(cid)
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                generated_count += 1
        except Exception as e:
            print(f"❌ Error generating tearsheet for {cid}: {e}")
            skipped_rows.append(
                {
                    "company_id": cid,
                    "company_name": c_name,
                    "years_available": yrs,
                    "reason": f"Generation error: {str(e)}",
                }
            )

    # Log skipped companies to output/skipped_tearsheets.csv
    skipped_df = pd.DataFrame(skipped_rows)
    skipped_csv = OUTPUT_DIR / "skipped_tearsheets.csv"
    skipped_df.to_csv(skipped_csv, index=False)

    print(
        f"✅ Batch Tearsheet Generation Complete: {generated_count} tearsheets generated in {TEARSHEETS_DIR.name}/"
    )
    print(f"⚠️ Logged {len(skipped_df)} skipped companies to {skipped_csv.name}")

    # Generate 11 Sector Reports
    print("\n🌐 Generating Sector PDF Reports...")
    sector_paths = generate_all_sector_reports()

    return generated_count, len(skipped_df), len(sector_paths)


if __name__ == "__main__":
    run_batch_generation()
