"""
tests/etl/test_validator.py
---------------------------
35+ tests for all 16 DQ rules in validator.py.
Uses in-memory SQLite with minimal fixture data.

Run with:
    pytest tests/etl/test_validator.py -v
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.etl.validator import (
    check_dq01,
    check_dq02,
    check_dq03,
    check_dq04,
    check_dq05,
    check_dq06,
    check_dq07,
    check_dq08,
    check_dq09,
    check_dq10,
    check_dq11,
    check_dq12,
    check_dq13,
    check_dq14,
    check_dq15,
    check_dq16,
    run_all_checks,
    write_failures,
    _FIELDNAMES,
)


# ── fixture helpers ────────────────────────────────────────────────────────────


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _make_companies(conn, rows):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS companies "
        "(company_id TEXT, ticker TEXT, bse_code TEXT)"
    )
    conn.executemany("INSERT INTO companies VALUES (?,?,?)", rows)
    conn.commit()


def _make_pl(conn, rows):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS profitandloss "
        "(company_id TEXT, year INTEGER, revenue REAL, operating_profit REAL, "
        "net_profit REAL, eps REAL, tax REAL, profit_before_tax REAL, dividend REAL)"
    )
    conn.executemany("INSERT INTO profitandloss VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()


def _make_bs(conn, rows):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS balancesheet "
        "(company_id TEXT, year INTEGER, total_assets REAL, total_liabilities REAL, equity REAL)"
    )
    conn.executemany("INSERT INTO balancesheet VALUES (?,?,?,?,?)", rows)
    conn.commit()


def _make_cf(conn, rows):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cashflow "
        "(company_id TEXT, year INTEGER, "
        "operating_cash_flow REAL, investing_cash_flow REAL, "
        "financing_cash_flow REAL, net_cash REAL)"
    )
    conn.executemany("INSERT INTO cashflow VALUES (?,?,?,?,?,?)", rows)
    conn.commit()


def _make_docs(conn, rows):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS documents "
        "(company_id TEXT, year INTEGER, report_url TEXT)"
    )
    conn.executemany("INSERT INTO documents VALUES (?,?,?)", rows)
    conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# DQ-01  PK uniqueness on companies.company_id
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ01:

    def test_no_duplicates_passes(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C2", "TCS", "532540")])
        assert check_dq01(conn) == []

    def test_duplicate_company_id_fails(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C1", "REL2", "500326")])
        failures = check_dq01(conn)
        assert len(failures) == 1
        assert failures[0]["rule_id"] == "DQ-01"
        assert failures[0]["severity"] == "CRITICAL"

    def test_missing_table_returns_empty(self):
        conn = _conn()
        assert check_dq01(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-02  Composite PK uniqueness (company_id, year)
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ02:

    def test_unique_composite_key_passes(self):
        conn = _conn()
        _make_pl(
            conn,
            [
                ("C1", 2021, 100, 20, 10, 5, 3, 13, 2),
                ("C1", 2022, 110, 22, 11, 5.5, 3.3, 14.3, 2),
            ],
        )
        assert check_dq02(conn) == []

    def test_duplicate_composite_key_fails(self):
        conn = _conn()
        _make_pl(
            conn,
            [
                ("C1", 2021, 100, 20, 10, 5, 3, 13, 2),
                ("C1", 2021, 110, 22, 11, 5.5, 3.3, 14.3, 2),
            ],
        )
        failures = check_dq02(conn)
        assert any(f["rule_id"] == "DQ-02" for f in failures)
        assert failures[0]["severity"] == "CRITICAL"

    def test_different_companies_same_year_passes(self):
        conn = _conn()
        _make_pl(
            conn,
            [
                ("C1", 2021, 100, 20, 10, 5, 3, 13, 2),
                ("C2", 2021, 200, 40, 20, 10, 6, 26, 4),
            ],
        )
        assert check_dq02(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-03  FK integrity
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ03:

    def test_valid_fk_passes(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325")])
        _make_pl(conn, [("C1", 2021, 100, 20, 10, 5, 3, 13, 2)])
        assert check_dq03(conn) == []

    def test_orphan_fk_fails(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325")])
        _make_pl(conn, [("ORPHAN", 2021, 100, 20, 10, 5, 3, 13, 2)])
        failures = check_dq03(conn)
        assert any(f["rule_id"] == "DQ-03" for f in failures)
        assert failures[0]["severity"] == "CRITICAL"

    def test_no_companies_table_skips(self):
        conn = _conn()
        # No companies table — should not crash
        assert check_dq03(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-04  Balance sheet balance
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ04:

    def test_balanced_sheet_passes(self):
        conn = _conn()
        # assets = liab + equity exactly
        _make_bs(conn, [("C1", 2021, 1000.0, 600.0, 400.0)])
        assert check_dq04(conn) == []

    def test_imbalanced_sheet_fails(self):
        conn = _conn()
        # assets=1000, liab+equity=800 → diff=20%
        _make_bs(conn, [("C1", 2021, 1000.0, 500.0, 300.0)])
        failures = check_dq04(conn)
        assert any(f["rule_id"] == "DQ-04" for f in failures)
        assert failures[0]["severity"] == "WARNING"

    def test_within_tolerance_passes(self):
        conn = _conn()
        # diff = 0.5% < 1% tolerance
        _make_bs(conn, [("C1", 2021, 1000.0, 600.0, 394.0)])
        assert check_dq04(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-05  OPM cross-check
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ05:

    def test_opm_within_range_passes(self):
        conn = _conn()
        # opm = 20/100 = 0.2 → within [-1, 1]
        _make_pl(conn, [("C1", 2021, 100, 20, 10, 5, 3, 13, 2)])
        assert check_dq05(conn) == []

    def test_opm_out_of_range_fails(self):
        conn = _conn()
        # opm = 200/100 = 2.0 → above max 1.0
        _make_pl(conn, [("C1", 2021, 100, 200, 10, 5, 3, 13, 2)])
        failures = check_dq05(conn)
        assert any(f["rule_id"] == "DQ-05" for f in failures)
        assert failures[0]["severity"] == "WARNING"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-06  Positive sales
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ06:

    def test_positive_revenue_passes(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, 100, 20, 10, 5, 3, 13, 2)])
        assert check_dq06(conn) == []

    def test_zero_revenue_fails(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, 0, 20, 10, 5, 3, 13, 2)])
        failures = check_dq06(conn)
        assert any(f["rule_id"] == "DQ-06" for f in failures)

    def test_negative_revenue_fails(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, -50, 20, 10, 5, 3, 13, 2)])
        failures = check_dq06(conn)
        assert any(f["rule_id"] == "DQ-06" for f in failures)


# ══════════════════════════════════════════════════════════════════════════════
# DQ-07  No null company_id
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ07:

    def test_no_null_company_id_passes(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325")])
        assert check_dq07(conn) == []

    def test_null_company_id_fails(self):
        conn = _conn()
        _make_companies(conn, [(None, "REL", "500325")])
        failures = check_dq07(conn)
        assert any(f["rule_id"] == "DQ-07" for f in failures)
        assert failures[0]["severity"] == "CRITICAL"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-08  No null year in financial tables
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ08:

    def test_no_null_year_passes(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, 100, 20, 10, 5, 3, 13, 2)])
        assert check_dq08(conn) == []

    def test_null_year_fails(self):
        conn = _conn()
        _make_pl(conn, [("C1", None, 100, 20, 10, 5, 3, 13, 2)])
        failures = check_dq08(conn)
        assert any(f["rule_id"] == "DQ-08" for f in failures)
        assert failures[0]["severity"] == "CRITICAL"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-09  Net cash check
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ09:

    def test_matching_net_cash_passes(self):
        conn = _conn()
        # 100 + (-30) + (-20) = 50 = net_cash
        _make_cf(conn, [("C1", 2021, 100, -30, -20, 50)])
        assert check_dq09(conn) == []

    def test_mismatched_net_cash_fails(self):
        conn = _conn()
        # computed=50, reported=100 → diff=50%
        _make_cf(conn, [("C1", 2021, 100, -30, -20, 100)])
        failures = check_dq09(conn)
        assert any(f["rule_id"] == "DQ-09" for f in failures)
        assert failures[0]["severity"] == "WARNING"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-10  Tax rate 0–60%
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ10:

    def test_valid_tax_rate_passes(self):
        conn = _conn()
        # tax/pbt = 30/100 = 30%
        _make_pl(conn, [("C1", 2021, 100, 20, 70, 5, 30, 100, 2)])
        assert check_dq10(conn) == []

    def test_excessive_tax_rate_fails(self):
        conn = _conn()
        # tax/pbt = 70/100 = 70% → > 60%
        _make_pl(conn, [("C1", 2021, 100, 20, 30, 5, 70, 100, 2)])
        failures = check_dq10(conn)
        assert any(f["rule_id"] == "DQ-10" for f in failures)
        assert failures[0]["severity"] == "WARNING"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-11  Dividend payout ≤ cap
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ11:

    def test_dividend_within_cap_passes(self):
        conn = _conn()
        # div/np = 80/100 = 0.8 ≤ 1.0
        _make_pl(conn, [("C1", 2021, 200, 50, 100, 5, 30, 130, 80)])
        assert check_dq11(conn) == []

    def test_dividend_exceeds_cap_fails(self):
        conn = _conn()
        # div/np = 150/100 = 1.5 > 1.0
        _make_pl(conn, [("C1", 2021, 200, 50, 100, 5, 30, 130, 150)])
        failures = check_dq11(conn)
        assert any(f["rule_id"] == "DQ-11" for f in failures)
        assert failures[0]["severity"] == "WARNING"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-12  URL format check
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ12:

    def test_valid_url_passes(self):
        conn = _conn()
        _make_docs(conn, [("C1", 2021, "https://example.com/report.pdf")])
        assert check_dq12(conn) == []

    def test_invalid_url_fails(self):
        conn = _conn()
        _make_docs(conn, [("C1", 2021, "not-a-url")])
        failures = check_dq12(conn)
        assert any(f["rule_id"] == "DQ-12" for f in failures)
        assert failures[0]["severity"] == "INFO"

    def test_http_url_passes(self):
        conn = _conn()
        _make_docs(conn, [("C1", 2021, "http://bse.com/report")])
        assert check_dq12(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-13  No duplicate tickers
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ13:

    def test_unique_tickers_passes(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C2", "TCS", "532540")])
        assert check_dq13(conn) == []

    def test_duplicate_ticker_fails(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C2", "REL", "500326")])
        failures = check_dq13(conn)
        assert any(f["rule_id"] == "DQ-13" for f in failures)
        assert failures[0]["severity"] == "CRITICAL"


# ══════════════════════════════════════════════════════════════════════════════
# DQ-14  EPS sign consistency
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ14:

    def test_positive_np_positive_eps_passes(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, 100, 20, 50, 5.0, 30, 80, 10)])
        assert check_dq14(conn) == []

    def test_positive_np_negative_eps_fails(self):
        conn = _conn()
        _make_pl(conn, [("C1", 2021, 100, 20, 50, -5.0, 30, 80, 10)])
        failures = check_dq14(conn)
        assert any(f["rule_id"] == "DQ-14" for f in failures)
        assert failures[0]["severity"] == "WARNING"

    def test_negative_np_negative_eps_not_flagged(self):
        conn = _conn()
        # net_profit < 0 so DQ-14 does not check EPS sign
        _make_pl(conn, [("C1", 2021, 100, 20, -10, -1.0, 30, -15, 0)])
        assert check_dq14(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# DQ-15  BSE code format
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ15:

    def test_valid_bse_code_passes(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325")])
        assert check_dq15(conn) == []

    def test_invalid_bse_code_fails(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "REL500")])
        failures = check_dq15(conn)
        assert any(f["rule_id"] == "DQ-15" for f in failures)
        assert failures[0]["severity"] == "WARNING"

    def test_five_digit_bse_fails(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "50032")])
        failures = check_dq15(conn)
        assert any(f["rule_id"] == "DQ-15" for f in failures)


# ══════════════════════════════════════════════════════════════════════════════
# DQ-16  Year coverage
# ══════════════════════════════════════════════════════════════════════════════


class TestDQ16:

    def test_sufficient_coverage_passes(self):
        conn = _conn()
        _make_pl(
            conn,
            [
                ("C1", 2019, 100, 20, 10, 5, 3, 13, 2),
                ("C1", 2020, 110, 22, 11, 5.5, 3.3, 14, 2),
                ("C1", 2021, 120, 24, 12, 6.0, 3.6, 15.6, 2),
            ],
        )
        assert check_dq16(conn) == []

    def test_insufficient_coverage_fails(self):
        conn = _conn()
        # Only 1 year of data; min required = 3
        _make_pl(conn, [("C1", 2021, 100, 20, 10, 5, 3, 13, 2)])
        failures = check_dq16(conn)
        assert any(f["rule_id"] == "DQ-16" for f in failures)
        assert failures[0]["severity"] == "INFO"

    def test_exactly_min_coverage_passes(self):
        conn = _conn()
        _make_pl(
            conn,
            [
                ("C2", 2019, 50, 10, 5, 2.5, 1.5, 6.5, 1),
                ("C2", 2020, 55, 11, 5.5, 2.75, 1.65, 7.15, 1),
                ("C2", 2021, 60, 12, 6, 3.0, 1.8, 7.8, 1),
            ],
        )
        assert check_dq16(conn) == []


# ══════════════════════════════════════════════════════════════════════════════
# run_all_checks  &  write_failures  – orchestrator tests
# ══════════════════════════════════════════════════════════════════════════════


class TestOrchestrator:

    def _full_conn(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C2", "TCS", "532540")])
        _make_pl(
            conn,
            [
                ("C1", 2019, 100, 20, 50, 5.0, 25, 75, 20),
                ("C1", 2020, 110, 22, 55, 5.5, 27.5, 82.5, 22),
                ("C1", 2021, 120, 24, 60, 6.0, 30, 90, 24),
                ("C2", 2019, 200, 40, 100, 10, 50, 150, 40),
                ("C2", 2020, 220, 44, 110, 11, 55, 165, 44),
                ("C2", 2021, 240, 48, 120, 12, 60, 180, 48),
            ],
        )
        return conn

    def test_run_all_returns_list(self):
        conn = self._full_conn()
        result = run_all_checks(conn)
        assert isinstance(result, list)

    def test_clean_data_has_no_critical(self):
        conn = self._full_conn()
        result = run_all_checks(conn)
        criticals = [f for f in result if f["severity"] == "CRITICAL"]
        assert criticals == []

    def test_failure_dict_has_required_keys(self):
        conn = _conn()
        _make_companies(conn, [("C1", "REL", "500325"), ("C1", "REL", "500325")])
        result = run_all_checks(conn)
        for f in result:
            for key in _FIELDNAMES:
                assert key in f, f"Key '{key}' missing from failure dict"

    def test_write_failures_creates_csv(self, tmp_path):
        import csv as _csv

        out = tmp_path / "validation_failures.csv"
        failures = [{k: "" for k in _FIELDNAMES}]
        # Patch the output path temporarily
        import src.etl.validator as v

        orig = v.FAILURES_FILE
        v.FAILURES_FILE = out
        write_failures(failures)
        v.FAILURES_FILE = orig
        assert out.exists()
        with out.open() as f:
            reader = _csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1

    def test_multiple_rule_failures_combined(self):
        conn = _conn()
        # company_id dup → DQ-01 & DQ-13; null year → DQ-08
        _make_companies(conn, [("C1", "REL", "500325"), ("C1", "REL", "500325")])
        _make_pl(conn, [("C1", None, 100, 20, 10, 5, 3, 13, 2)])
        result = run_all_checks(conn)
        rule_ids = {f["rule_id"] for f in result}
        assert "DQ-01" in rule_ids
        assert "DQ-08" in rule_ids
