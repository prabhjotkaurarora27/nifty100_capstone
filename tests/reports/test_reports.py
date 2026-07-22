import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.reports.portfolio_summary import generate_portfolio_summary_pdf
from src.reports.sector_report import generate_sector_report
from src.reports.tearsheet import generate_company_tearsheet


def test_generate_company_tearsheet_pdf(tmp_path):
    pdf_path = tmp_path / "TCS_test.pdf"
    res_path = generate_company_tearsheet("TCS", pdf_path)
    assert res_path.exists()
    assert res_path.stat().st_size > 30 * 1024  # > 30 KB


def test_generate_sector_report_pdf(tmp_path):
    pdf_path = tmp_path / "IT_test.pdf"
    res_path = generate_sector_report("Information Technology", pdf_path)
    assert res_path.exists()
    assert res_path.stat().st_size > 2 * 1024  # > 2 KB


def test_generate_portfolio_summary_pdf(tmp_path):
    pdf_path = tmp_path / "portfolio_summary_test.pdf"
    res_path = generate_portfolio_summary_pdf(pdf_path)
    assert res_path.exists()
    assert res_path.stat().st_size > 50 * 1024  # > 50 KB
