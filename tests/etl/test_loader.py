"""
tests/etl/test_loader.py
------------------------
35+ unit / integration tests for normaliser.py and loader.py.

Run with:
    pytest tests/etl/test_loader.py -v
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import the modules under test
# ---------------------------------------------------------------------------
import sys

# Ensure project root is on sys.path so imports work regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.etl.normaliser import normalize_year, normalize_ticker
from src.etl.loader import apply_normalisations, load_table, _normalise_columns


# ===========================================================================
#  normalize_year  – 20 tests
# ===========================================================================

class TestNormalizeYear:

    # 1
    def test_fy2021_uppercase(self):
        assert normalize_year("FY2021") == 2021

    # 2
    def test_fy2021_with_space(self):
        assert normalize_year("FY 2021") == 2021

    # 3
    def test_fy21_two_digit(self):
        assert normalize_year("FY21") == 2021

    # 4
    def test_fy21_with_space(self):
        assert normalize_year("FY 21") == 2021

    # 5
    def test_fy2021_lowercase(self):
        assert normalize_year("fy2021") == 2021

    # 6
    def test_fy2021_lowercase_with_space(self):
        assert normalize_year("fy 2021") == 2021

    # 7
    def test_fy21_lowercase(self):
        assert normalize_year("fy21") == 2021

    # 8
    def test_dash_range_2020_21(self):
        assert normalize_year("2020-21") == 2021

    # 9
    def test_dash_range_2021_22(self):
        assert normalize_year("2021-22") == 2022

    # 10
    def test_full_dash_range_2020_2021(self):
        assert normalize_year("2020-2021") == 2021

    # 11
    def test_mar_21_dash(self):
        assert normalize_year("Mar-21") == 2021

    # 12
    def test_mar_21_space(self):
        assert normalize_year("Mar 21") == 2021

    # 13
    def test_mar_21_lowercase(self):
        assert normalize_year("mar-21") == 2021

    # 14
    def test_mar_2021_full_year(self):
        assert normalize_year("Mar 2021") == 2021

    # 15
    def test_plain_int(self):
        assert normalize_year(2021) == 2021

    # 16
    def test_plain_float(self):
        assert normalize_year(2021.0) == 2021

    # 17
    def test_plain_string_year(self):
        assert normalize_year("2021") == 2021

    # 18
    def test_leading_trailing_spaces(self):
        assert normalize_year("  2021  ") == 2021

    # 19
    def test_none_input(self):
        assert normalize_year(None) is None

    # 20
    def test_empty_string(self):
        assert normalize_year("") is None

    # 21
    def test_garbage_string(self):
        assert normalize_year("garbage") is None

    # 22
    def test_excel_serial(self):
        # Excel serial 44197 → 2021-01-01
        result = normalize_year(44197)
        assert result == 2021

    # 23
    def test_fy50_century_boundary(self):
        # 2-digit year ≥50 → 19xx
        assert normalize_year("FY50") == 1950

    # 24
    def test_fy49_century_boundary(self):
        # 2-digit year <50 → 20xx
        assert normalize_year("FY49") == 2049

    # 25
    def test_float_string(self):
        assert normalize_year("2021.0") == 2021

    # 26
    def test_nan_float(self):
        import math
        assert normalize_year(float("nan")) is None


# ===========================================================================
#  normalize_ticker  – 15 tests
# ===========================================================================

class TestNormalizeTicker:

    # 1
    def test_plain_ticker_uppercase(self):
        assert normalize_ticker("RELIANCE") == "RELIANCE"

    # 2
    def test_lowercase_ticker(self):
        assert normalize_ticker("reliance") == "RELIANCE"

    # 3
    def test_ns_suffix(self):
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE"

    # 4
    def test_bo_suffix(self):
        assert normalize_ticker("RELIANCE.BO") == "RELIANCE"

    # 5
    def test_bse_suffix(self):
        assert normalize_ticker("RELIANCE.BSE") == "RELIANCE"

    # 6
    def test_nse_suffix(self):
        assert normalize_ticker("RELIANCE.NSE") == "RELIANCE"

    # 7
    def test_space_in_name(self):
        assert normalize_ticker("HDFC BANK") == "HDFC_BANK"

    # 8
    def test_hyphen_in_name(self):
        assert normalize_ticker("HDFC-BANK") == "HDFC_BANK"

    # 9
    def test_lowercase_space_ns(self):
        assert normalize_ticker("hdfc bank.ns") == "HDFC_BANK"

    # 10
    def test_leading_trailing_spaces(self):
        assert normalize_ticker("  RELIANCE  ") == "RELIANCE"

    # 11
    def test_none_input(self):
        assert normalize_ticker(None) is None

    # 12
    def test_empty_string(self):
        assert normalize_ticker("") is None

    # 13
    def test_whitespace_only(self):
        assert normalize_ticker("   ") is None

    # 14
    def test_numeric_int(self):
        assert normalize_ticker(12345) is None

    # 15
    def test_numeric_string(self):
        assert normalize_ticker("12345") is None

    # 16
    def test_mixed_case_suffix(self):
        assert normalize_ticker("Infosys.Ns") == "INFOSYS"

    # 17
    def test_multiple_spaces(self):
        assert normalize_ticker("STATE  BANK") == "STATE_BANK"


# ===========================================================================
#  apply_normalisations  – integration (uses real normaliser)
# ===========================================================================

class TestApplyNormalisations:

    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "ticker":      ["RELIANCE.NS", "hdfc bank", None, "12345", "TCS.BO"],
            "fiscal_year": ["FY2021",      "2020-21",   "FY22", "FY2023", None],
            "revenue":     [100,            200,         300,   400,      500],
        })

    # 1 – ticker normalisation applied
    def test_ticker_column_normalised(self):
        df = self._make_df()
        out, _ = apply_normalisations(df, [], ["ticker"])
        assert out["ticker"].tolist() == ["RELIANCE", "HDFC_BANK", "TCS"]

    # 2 – rows with all-None tickers are rejected
    def test_all_none_ticker_rows_rejected(self):
        df = self._make_df()
        out, rejected = apply_normalisations(df, [], ["ticker"])
        # None → None, "12345" → None  → 2 rows rejected
        assert rejected == 2

    # 3 – year normalisation applied
    def test_year_column_normalised(self):
        import math
        df = self._make_df()
        out, _ = apply_normalisations(df, ["fiscal_year"], [])
        values = out["fiscal_year"].tolist()
        # pandas stores mixed int/None columns as float64 (NaN for missing)
        def _norm(v):
            if v is None:
                return None
            try:
                if math.isnan(float(v)):
                    return None
                return int(v)
            except (TypeError, ValueError):
                return v
        assert [_norm(v) for v in values] == [2021, 2021, 2022, 2023, None]

    # 4 – non-existent columns are silently skipped
    def test_missing_columns_skipped(self):
        df = pd.DataFrame({"revenue": [1, 2, 3]})
        out, rejected = apply_normalisations(df, ["year"], ["ticker"])
        assert len(out) == 3
        assert rejected == 0

    # 5 – column normalisation lowercases headers
    def test_normalise_columns_lowercase(self):
        df = pd.DataFrame({"Ticker": [1], "Fiscal Year": [2021]})
        out = _normalise_columns(df)
        assert list(out.columns) == ["ticker", "fiscal_year"]

    # 6 – combined year + ticker
    def test_combined_year_and_ticker(self):
        df = pd.DataFrame({
            "ticker": ["RELIANCE.NS"],
            "year":   ["FY2022"],
            "value":  [999],
        })
        out, rejected = apply_normalisations(df, ["year"], ["ticker"])
        assert out["ticker"].iloc[0] == "RELIANCE"
        assert out["year"].iloc[0]   == 2022
        assert rejected == 0


# ===========================================================================
#  load_table  – in-memory SQLite integration
# ===========================================================================

class TestLoadTable:

    def _make_conn(self):
        return sqlite3.connect(":memory:")

    # 1 – core load creates table with correct row count
    def test_core_load_creates_table(self):
        df = pd.DataFrame({"ticker": ["TCS", "INFY"], "year": [2021, 2021]})
        conn = self._make_conn()
        rows = load_table(df, "companies", "core", conn)
        assert rows == 2
        result = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        assert result == 2
        conn.close()

    # 2 – core load replaces existing data
    def test_core_load_replaces_existing(self):
        df1 = pd.DataFrame({"ticker": ["TCS", "INFY", "WIPRO"]})
        df2 = pd.DataFrame({"ticker": ["RELIANCE"]})
        conn = self._make_conn()
        load_table(df1, "companies", "core", conn)
        load_table(df2, "companies", "core", conn)
        result = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        assert result == 1
        conn.close()

    # 3 – each load replaces the table (pipeline uses replace for all tables)
    def test_supplementary_load_replaces(self):
        df1 = pd.DataFrame({"ticker": ["TCS", "INFY"]})
        df2 = pd.DataFrame({"ticker": ["RELIANCE", "WIPRO"]})
        conn = self._make_conn()
        load_table(df1, "stock_prices", "supplementary", conn)
        load_table(df2, "stock_prices", "supplementary", conn)
        # Second call replaces → only df2's 2 rows remain
        result = conn.execute("SELECT COUNT(*) FROM stock_prices").fetchone()[0]
        assert result == 2
        conn.close()

    # 4 – load returns correct rows_loaded
    def test_load_returns_row_count(self):
        df = pd.DataFrame({"a": range(10)})
        conn = self._make_conn()
        rows = load_table(df, "test_table", "core", conn)
        assert rows == 10
        conn.close()

    # 5 – empty DataFrame can be loaded without error
    def test_load_empty_dataframe(self):
        df = pd.DataFrame({"ticker": pd.Series([], dtype="str")})
        conn = self._make_conn()
        rows = load_table(df, "empty_table", "core", conn)
        assert rows == 0
        conn.close()

    # 6 – table persists after reload (core replace)
    def test_table_schema_after_replace(self):
        df = pd.DataFrame({"ticker": ["A"], "value": [1]})
        conn = self._make_conn()
        load_table(df, "test_tbl", "core", conn)
        # Reload with different column set
        df2 = pd.DataFrame({"ticker": ["B"], "extra": [99]})
        load_table(df2, "test_tbl", "core", conn)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(test_tbl)")]
        assert "extra" in cols
        conn.close()
