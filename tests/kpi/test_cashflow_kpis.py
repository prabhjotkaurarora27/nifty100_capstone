"""
tests/kpi/test_cashflow_kpis.py
================================
Sprint 2 — Day 11
Unit tests for src/analytics/cashflow_kpis.py

Tests 1–8 cover:
  * free_cash_flow           (1)
  * cfo_quality_score        (2–3)
  * capex_intensity          (4)
  * fcf_conversion_rate      (5)
  * classify_capital_allocation — 4 key patterns (6–8)
"""

from __future__ import annotations

import pytest

from src.analytics.cashflow_kpis import (
    PATTERN_CASH_ACCUMULATOR,
    PATTERN_DISTRESS_SIGNAL,
    PATTERN_GROWTH_BY_DEBT,
    PATTERN_REINVESTOR,
    PATTERN_SHAREHOLDER_RETURNS,
    capex_intensity,
    classify_capital_allocation,
    fcf_conversion_rate,
    cfo_quality_score,
    free_cash_flow,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — free_cash_flow
# ─────────────────────────────────────────────────────────────────────────────


class TestFreeCashFlow:

    def test_positive_fcf(self):
        """CFO 1000, investing -300 → FCF = 700."""
        assert free_cash_flow(1000.0, -300.0) == pytest.approx(700.0, abs=1e-3)

    def test_negative_fcf(self):
        """CFO 200, investing -500 → FCF = -300 (burning cash on capex)."""
        assert free_cash_flow(200.0, -500.0) == pytest.approx(-300.0, abs=1e-3)

    def test_both_none_returns_none(self):
        assert free_cash_flow(None, None) is None

    def test_none_investing_treated_as_zero(self):
        assert free_cash_flow(500.0, None) == pytest.approx(500.0, abs=1e-3)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 2–3 — cfo_quality_score
# ─────────────────────────────────────────────────────────────────────────────


class TestCfoQualityScore:

    def test_high_quality(self):
        """CFO consistently ≥ 75% of PAT."""
        cfo = [800.0, 850.0, 900.0, 950.0, 1000.0]
        pat = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
        assert cfo_quality_score(cfo, pat) == "High Quality"

    def test_moderate_quality(self):
        """CFO around 50–70% of PAT → Moderate."""
        cfo = [500.0, 550.0, 600.0, 580.0, 620.0]
        pat = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
        assert cfo_quality_score(cfo, pat) == "Moderate"

    def test_accrual_risk(self):
        """CFO < 40% of PAT — earnings not converting to cash."""
        cfo = [100.0, 150.0, 120.0]
        pat = [1000.0, 1000.0, 1000.0]
        assert cfo_quality_score(cfo, pat) == "Accrual Risk"

    def test_insufficient_data(self):
        """Only one valid pair → Insufficient Data."""
        assert cfo_quality_score([800.0], [1000.0]) == "Insufficient Data"

    def test_zero_pat_excluded(self):
        """Years where PAT=0 are excluded from average."""
        cfo = [800.0, 100.0, 900.0]
        pat = [1000.0, 0.0, 1000.0]  # middle year excluded
        # avg of 0.8 and 0.9 = 0.85 → High Quality
        assert cfo_quality_score(cfo, pat) == "High Quality"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — capex_intensity
# ─────────────────────────────────────────────────────────────────────────────


class TestCapexIntensity:

    def test_asset_light(self):
        """|investing| / sales < 5% → Asset Light."""
        assert capex_intensity(-40.0, 1000.0) == "Asset Light"

    def test_moderate(self):
        """5–15% → Moderate."""
        assert capex_intensity(-100.0, 1000.0) == "Moderate"

    def test_capital_intensive(self):
        """≥ 15% → Capital Intensive."""
        assert capex_intensity(-200.0, 1000.0) == "Capital Intensive"

    def test_zero_sales_returns_none(self):
        assert capex_intensity(-100.0, 0.0) is None

    def test_none_sales_returns_none(self):
        assert capex_intensity(-100.0, None) is None


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — fcf_conversion_rate
# ─────────────────────────────────────────────────────────────────────────────


class TestFcfConversionRate:

    def test_normal(self):
        assert fcf_conversion_rate(700.0, 1000.0) == pytest.approx(0.7, abs=1e-3)

    def test_zero_operating_profit_returns_none(self):
        assert fcf_conversion_rate(700.0, 0.0) is None

    def test_none_fcf_returns_none(self):
        assert fcf_conversion_rate(None, 1000.0) is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests 6–8 — classify_capital_allocation
# ─────────────────────────────────────────────────────────────────────────────


class TestClassifyCapitalAllocation:

    def test_reinvestor(self):
        """CFO+, CFI−, CFF− → healthy reinvestor."""
        assert classify_capital_allocation(1000.0, -300.0, -200.0) == PATTERN_REINVESTOR

    def test_growth_funded_by_debt(self):
        """CFO+, CFI−, CFF+ → expanding via debt."""
        assert (
            classify_capital_allocation(500.0, -800.0, 400.0) == PATTERN_GROWTH_BY_DEBT
        )

    def test_shareholder_returns(self):
        """CFO+, CFI+, CFF− → selling assets, returning capital."""
        assert (
            classify_capital_allocation(800.0, 200.0, -500.0)
            == PATTERN_SHAREHOLDER_RETURNS
        )

    def test_distress_signal(self):
        """CFO−, CFI+, CFF− → burning cash, selling assets to repay debt."""
        assert (
            classify_capital_allocation(-300.0, 500.0, -200.0)
            == PATTERN_DISTRESS_SIGNAL
        )

    def test_cash_accumulator(self):
        """CFO+, CFI+, CFF+ → building cash reserves (all inflows)."""
        assert (
            classify_capital_allocation(1000.0, 500.0, 200.0)
            == PATTERN_CASH_ACCUMULATOR
        )
