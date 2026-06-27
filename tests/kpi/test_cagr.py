"""
tests/kpi/test_cagr.py
======================
Sprint 2 — Day 10
Unit tests for src/analytics/cagr.py

Tests 1–10 cover:
  * Normal CAGR computation (1–2)
  * All 6 edge-case flags (3–8)
  * Multi-window helper with gaps (9–10)
"""

from __future__ import annotations

import math
import pytest

from src.analytics.cagr import (
    FLAG_BOTH_NEGATIVE,
    FLAG_DECLINE_TO_LOSS,
    FLAG_INSUFFICIENT,
    FLAG_NORMAL,
    FLAG_TURNAROUND,
    FLAG_ZERO_BASE,
    compute_cagr,
    eps_cagr,
    pat_cagr,
    revenue_cagr,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 1–2 — Normal computation
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeCagrNormal:

    def test_doubling_in_5_years(self):
        """
        100 → 200 in 5 yrs  →  CAGR = 2^(1/5) − 1 ≈ 14.8698%
        """
        val, flag = compute_cagr(100.0, 200.0, 5)
        assert flag == FLAG_NORMAL
        assert val == pytest.approx(14.8698, abs=0.01)

    def test_growth_over_3_years(self):
        """
        1000 → 1331 in 3 yrs  →  CAGR = 10.0% exactly
        """
        val, flag = compute_cagr(1000.0, 1331.0, 3)
        assert flag == FLAG_NORMAL
        assert val == pytest.approx(10.0, abs=0.01)

    def test_negative_growth(self):
        """
        1000 → 800 in 2 yrs  →  CAGR ≈ −10.557%
        """
        val, flag = compute_cagr(1000.0, 800.0, 2)
        assert flag == FLAG_NORMAL
        assert val < 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests 3–8 — Edge-case flags
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeCagrEdgeCases:

    def test_decline_to_loss(self):
        """Profitable base, loss end → DECLINE_TO_LOSS."""
        val, flag = compute_cagr(500.0, -100.0, 5)
        assert flag == FLAG_DECLINE_TO_LOSS
        assert val is None

    def test_turnaround(self):
        """Loss base, profitable end → TURNAROUND."""
        val, flag = compute_cagr(-200.0, 400.0, 5)
        assert flag == FLAG_TURNAROUND
        assert val is None

    def test_both_negative(self):
        """Both losses → BOTH_NEGATIVE."""
        val, flag = compute_cagr(-100.0, -50.0, 5)
        assert flag == FLAG_BOTH_NEGATIVE
        assert val is None

    def test_zero_base(self):
        """Start = 0 → ZERO_BASE (undefined division)."""
        val, flag = compute_cagr(0.0, 500.0, 5)
        assert flag == FLAG_ZERO_BASE
        assert val is None

    def test_insufficient_none_start(self):
        """None inputs → INSUFFICIENT."""
        val, flag = compute_cagr(None, 500.0, 5)
        assert flag == FLAG_INSUFFICIENT
        assert val is None

    def test_insufficient_n_zero(self):
        """n < 1 → INSUFFICIENT."""
        val, flag = compute_cagr(100.0, 200.0, 0)
        assert flag == FLAG_INSUFFICIENT
        assert val is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests 9–10 — Multi-window CAGR helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiWindowCagr:

    def test_revenue_cagr_all_windows_present(self):
        """
        Continuous data — all 3 windows (3/5/10) should be NORMAL.
        Series spans 2011–2024 at 1000*1.1^t (10% annual growth).
        """
        series = {2011 + t: round(1000.0 * (1.1 ** t), 2) for t in range(14)}
        result = revenue_cagr(series, windows=(3, 5, 10))
        assert result[3]["flag"] == FLAG_NORMAL
        assert result[5]["flag"] == FLAG_NORMAL
        assert result[10]["flag"] == FLAG_NORMAL
        # 10% growth → all CAGR ≈ 10%
        assert result[5]["value"] == pytest.approx(10.0, abs=0.1)

    def test_pat_cagr_with_missing_years(self):
        """
        Missing start year for 10yr window → INSUFFICIENT for that window.
        """
        # Only years 2020–2024 present
        series = {2020: 100.0, 2021: 110.0, 2022: 121.0, 2023: 133.0, 2024: 146.0}
        result = pat_cagr(series, windows=(3, 5, 10))
        # Anchor = 2024; 3yr start = 2021 ✓, 5yr start = 2019 ✗, 10yr start = 2014 ✗
        assert result[3]["flag"] == FLAG_NORMAL
        assert result[5]["flag"] == FLAG_INSUFFICIENT
        assert result[10]["flag"] == FLAG_INSUFFICIENT

    def test_eps_cagr_turnaround_in_window(self):
        """
        EPS goes from negative to positive → TURNAROUND flag.
        """
        series = {2019: -50.0, 2020: -30.0, 2021: -10.0, 2022: 20.0, 2023: 50.0, 2024: 80.0}
        result = eps_cagr(series, windows=(5,))
        # anchor=2024, start_year=2019 → start=-50, end=80 → TURNAROUND
        assert result[5]["flag"] == FLAG_TURNAROUND
        assert result[5]["value"] is None
