import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.normaliser import normalize_ticker, normalize_year


def test_norm_year_plain_int():
    assert normalize_year(2021) == 2021


def test_norm_year_plain_float():
    assert normalize_year(2021.0) == 2021


def test_norm_year_str_four_digits():
    assert normalize_year("2024") == 2024


def test_norm_year_fy_prefix_four_digits():
    assert normalize_year("FY2021") == 2021


def test_norm_year_fy_space_four_digits():
    assert normalize_year("FY 2023") == 2023


def test_norm_year_fy_two_digits():
    assert normalize_year("FY21") == 2021


def test_norm_year_fy_space_two_digits():
    assert normalize_year("FY 22") == 2022


def test_norm_year_range_dash_short():
    assert normalize_year("2020-21") == 2021


def test_norm_year_range_dash_long():
    assert normalize_year("2020-2021") == 2021


def test_norm_year_month_abbr_dash_short():
    assert normalize_year("Mar-21") == 2021


def test_norm_year_month_abbr_space_four_digits():
    assert normalize_year("Mar 2021") == 2021


def test_norm_year_excel_serial():
    assert normalize_year(44256) == 2021


def test_norm_year_none_returns_none():
    assert normalize_year(None) is None


def test_norm_year_empty_str_returns_none():
    assert normalize_year("") is None


def test_norm_year_whitespace_returns_none():
    assert normalize_year("   ") is None


def test_norm_year_garbage_returns_none():
    assert normalize_year("invalid_year_string") is None


def test_norm_year_lowercase_fy():
    assert normalize_year("fy2024") == 2024


def test_norm_ticker_strip_suffix_nse():
    assert normalize_ticker("TCS.NSE") == "TCS"


def test_norm_ticker_strip_suffix_bse():
    assert normalize_ticker("RELIANCE.BSE") == "RELIANCE"


def test_norm_ticker_uppercase():
    assert normalize_ticker("hdfcbank") == "HDFCBANK"
