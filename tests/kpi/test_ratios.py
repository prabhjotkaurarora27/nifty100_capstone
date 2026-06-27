"""
tests/kpi/test_ratios.py
========================
Sprint 2 — Days 08 & 09
Unit tests for src/analytics/ratios.py

Day 08 tests (1–8)  : net_profit_margin, operating_profit_margin,
                       return_on_equity, return_on_capital_employed,
                       return_on_assets
Day 09 tests (9–16) : debt_to_equity, high_leverage_flag,
                       interest_coverage, net_debt, asset_turnover
"""

from __future__ import annotations

import logging
import pytest

from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


# ─────────────────────────────────────────────────────────────────────────────
# Day 08 — Return & Margin Ratios  (tests 1–8)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetProfitMargin:
    """Tests 1–2"""

    def test_normal_case(self):
        """100 net profit on 1000 sales → 10.0%"""
        result = net_profit_margin(100.0, 1000.0)
        assert result == pytest.approx(10.0, abs=1e-3)

    def test_zero_sales_returns_none(self):
        """Sales = 0 must return None (guard against ZeroDivisionError)."""
        assert net_profit_margin(50.0, 0) is None

    def test_none_inputs_return_none(self):
        assert net_profit_margin(None, 500.0) is None
        assert net_profit_margin(100.0, None) is None

    def test_negative_net_profit(self):
        """Loss-making company → negative margin."""
        assert net_profit_margin(-200.0, 1000.0) == pytest.approx(-20.0, abs=1e-3)


class TestOperatingProfitMargin:
    """Tests 3–4"""

    def test_normal_case_no_cross_check(self):
        result = operating_profit_margin(300.0, 1000.0)
        assert result == pytest.approx(30.0, abs=1e-3)

    def test_cross_check_logs_warning_when_diff_exceeds_1pct(self, caplog):
        """Stored OPM differs by >1 pp — warning must be emitted."""
        with caplog.at_level(logging.WARNING, logger="src.analytics.ratios"):
            result = operating_profit_margin(
                300.0, 1000.0,
                opm_percentage=27.0,   # stored = 27%, computed = 30% → diff 3%
                company_id="TEST",
                year=2023,
            )
        assert result == pytest.approx(30.0, abs=1e-3)
        assert "OPM mismatch" in caplog.text

    def test_cross_check_no_warning_when_diff_within_1pct(self, caplog):
        """Stored OPM within 1 pp → no warning."""
        with caplog.at_level(logging.WARNING, logger="src.analytics.ratios"):
            operating_profit_margin(
                300.0, 1000.0,
                opm_percentage=30.5,   # diff = 0.5% — within tolerance
                company_id="TEST",
                year=2023,
            )
        assert "OPM mismatch" not in caplog.text

    def test_zero_sales_returns_none(self):
        assert operating_profit_margin(200.0, 0) is None


class TestReturnOnEquity:
    """Tests 5"""

    def test_normal_case(self):
        # Net profit 150 on equity 1000 (cap 100 + reserves 900) → 15%
        assert return_on_equity(150.0, 100.0, 900.0) == pytest.approx(15.0, abs=1e-3)

    def test_negative_equity_returns_none(self):
        assert return_on_equity(100.0, 50.0, -200.0) is None

    def test_zero_equity_returns_none(self):
        assert return_on_equity(100.0, 0.0, 0.0) is None

    def test_none_inputs(self):
        assert return_on_equity(None, 100.0, 200.0) is None


class TestReturnOnCapitalEmployed:
    """Tests 6"""

    def test_non_financial_company(self):
        # EBIT=200, equity=500, reserves=300, borrowings=200 → CE=1000 → 20%
        result = return_on_capital_employed(200.0, 500.0, 300.0, 200.0, is_financial=False)
        assert result == pytest.approx(20.0, abs=1e-3)

    def test_financial_company_excludes_borrowings(self):
        # EBIT=100, equity=200, reserves=300 → CE=500 → 20%
        result = return_on_capital_employed(100.0, 200.0, 300.0, 10_000.0, is_financial=True)
        assert result == pytest.approx(20.0, abs=1e-3)

    def test_zero_capital_employed_returns_none(self):
        assert return_on_capital_employed(100.0, 0.0, 0.0, 0.0) is None


class TestReturnOnAssets:
    """Tests 7–8"""

    def test_normal_case(self):
        # 100 profit on 2000 total assets → 5%
        assert return_on_assets(100.0, 2000.0) == pytest.approx(5.0, abs=1e-3)

    def test_zero_assets_returns_none(self):
        assert return_on_assets(100.0, 0.0) is None

    def test_none_total_assets_returns_none(self):
        assert return_on_assets(100.0, None) is None


# ─────────────────────────────────────────────────────────────────────────────
# Day 09 — Leverage & Liquidity Ratios  (tests 9–16)
# ─────────────────────────────────────────────────────────────────────────────

class TestDebtToEquity:
    """Tests 9–10"""

    def test_normal_case(self):
        # 500 borrowings, equity 100+400=500 → D/E = 1.0
        assert debt_to_equity(500.0, 100.0, 400.0) == pytest.approx(1.0, abs=1e-3)

    def test_zero_borrowings_returns_zero(self):
        assert debt_to_equity(0.0, 200.0, 800.0) == 0.0

    def test_none_borrowings_returns_zero(self):
        assert debt_to_equity(None, 200.0, 800.0) == 0.0

    def test_negative_equity_returns_none(self):
        assert debt_to_equity(500.0, 50.0, -300.0) is None


class TestHighLeverageFlag:
    """Test 11"""

    def test_high_de_non_financial_is_flagged(self):
        assert high_leverage_flag(6.0, is_financial=False) is True

    def test_high_de_financial_not_flagged(self):
        """Banks/NBFCs are exempt regardless of D/E."""
        assert high_leverage_flag(20.0, is_financial=True) is False

    def test_de_below_threshold_not_flagged(self):
        assert high_leverage_flag(4.9, is_financial=False) is False

    def test_none_de_not_flagged(self):
        assert high_leverage_flag(None, is_financial=False) is False


class TestInterestCoverage:
    """Tests 12–13"""

    def test_zero_interest_returns_debt_free(self):
        icr, label, warning = interest_coverage(500.0, 50.0, 0)
        assert icr is None
        assert label == "Debt Free"
        assert warning is False

    def test_none_interest_returns_debt_free(self):
        icr, label, warning = interest_coverage(500.0, 50.0, None)
        assert label == "Debt Free"

    def test_normal_icr(self):
        # (500+50)/100 = 5.5 — well above 1.5, no warning
        icr, label, warning = interest_coverage(500.0, 50.0, 100.0)
        assert icr == pytest.approx(5.5, abs=1e-3)
        assert label is None
        assert warning is False

    def test_low_icr_triggers_warning(self):
        # (100+20)/100 = 1.2 < 1.5 → warning
        icr, label, warning = interest_coverage(100.0, 20.0, 100.0)
        assert icr == pytest.approx(1.2, abs=1e-3)
        assert warning is True


class TestNetDebt:
    """Test 14"""

    def test_net_debt_positive(self):
        # 1000 borrowings, 200 investments → net debt = 800
        assert net_debt(1000.0, 200.0) == pytest.approx(800.0, abs=1e-3)

    def test_net_cash_position(self):
        # 100 borrowings, 500 investments → net debt = -400 (net cash)
        assert net_debt(100.0, 500.0) == pytest.approx(-400.0, abs=1e-3)

    def test_none_borrowings_returns_none(self):
        assert net_debt(None, 200.0) is None

    def test_none_investments_treated_as_zero(self):
        assert net_debt(500.0, None) == pytest.approx(500.0, abs=1e-3)


class TestAssetTurnover:
    """Tests 15–16"""

    def test_normal_case(self):
        # 1000 sales, 2000 assets → turnover = 0.5
        assert asset_turnover(1000.0, 2000.0) == pytest.approx(0.5, abs=1e-3)

    def test_zero_assets_returns_none(self):
        assert asset_turnover(1000.0, 0.0) is None

    def test_none_assets_returns_none(self):
        assert asset_turnover(1000.0, None) is None

    def test_none_sales_returns_none(self):
        assert asset_turnover(None, 2000.0) is None
