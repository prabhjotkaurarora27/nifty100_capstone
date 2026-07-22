import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import pytest
from src.analytics.valuation import run_valuation_analysis
from src.dashboard.utils.db import (
    get_bs,
    get_cf,
    get_companies,
    get_documents,
    get_peers,
    get_pl,
    get_pros_cons,
    get_ratios,
    get_sectors,
    get_valuation,
)
from src.screener.engine import ScreenerEngine


def test_get_companies_count():
    df = get_companies()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 92
    assert "company_name" in df.columns
    assert "broad_sector" in df.columns


def test_get_ratios_data():
    df = get_ratios(year=2024)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 92
    assert "return_on_equity_pct" in df.columns
    assert "debt_to_equity" in df.columns


def test_get_pl_single_company():
    df = get_pl("TCS")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "sales" in df.columns
    assert "net_profit" in df.columns


def test_get_bs_single_company():
    df = get_bs("RELIANCE")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "total_assets" in df.columns


def test_get_cf_single_company():
    df = get_cf("HDFCBANK")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "operating_activity" in df.columns


def test_get_sectors():
    df = get_sectors()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "broad_sector" in df.columns


def test_get_peers():
    df = get_peers(group_name="IT Services")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "percentile_rank" in df.columns


def test_get_valuation_all():
    df = get_valuation()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 92
    assert "fcf_yield_pct" in df.columns


def test_run_valuation_analysis_outputs():
    summary_df, flags_df = run_valuation_analysis()
    assert isinstance(summary_df, pd.DataFrame)
    assert len(summary_df) == 92
    assert "P/E" in summary_df.columns
    assert "flag" in summary_df.columns
    assert set(flags_df["flag"].unique()).issubset({"Caution", "Discount"})


def test_screener_extreme_sliders_no_crash():
    engine = ScreenerEngine()
    filters = {
        "roe_min": 99.0,
        "de_max": 0.0,
        "fcf_min": 50000.0,
        "pe_max": 1.0,
    }
    filtered_df = engine.apply_filters(filters)
    assert isinstance(filtered_df, pd.DataFrame)


def test_partial_data_handling():
    # Test ticker with missing values or unknown ticker
    df_pl = get_pl("UNKNOWN_TICKER")
    assert isinstance(df_pl, pd.DataFrame)
    assert df_pl.empty


def test_get_documents():
    df = get_documents("INFY")
    assert isinstance(df, pd.DataFrame)
    assert "annual_report" in df.columns
