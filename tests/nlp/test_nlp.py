import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.nlp.parser import parse_analysis_file
from src.nlp.pros_cons_generator import generate_pros_cons


def test_parse_analysis_file():
    parsed_df, failure_df, div_df = parse_analysis_file()
    assert isinstance(parsed_df, pd.DataFrame)
    assert not parsed_df.empty
    assert "period_years" in parsed_df.columns
    assert "value_pct" in parsed_df.columns


def test_generate_pros_cons_coverage():
    res_df = generate_pros_cons()
    assert isinstance(res_df, pd.DataFrame)
    assert not res_df.empty
    assert "company_id" in res_df.columns
    assert "confidence_pct" in res_df.columns

    # Verify every company has 1+ pro and 1+ con
    pros_companies = set(res_df[res_df["type"] == "pro"]["company_id"])
    cons_companies = set(res_df[res_df["type"] == "con"]["company_id"])
    all_companies = set(res_df["company_id"])

    assert len(pros_companies) == len(all_companies)
    assert len(cons_companies) == len(all_companies)
