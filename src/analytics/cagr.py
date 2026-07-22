"""
src/analytics/cagr.py
=====================
Sprint 2 — Day 10
CAGR (Compound Annual Growth Rate) computation with 6 edge-case flags.

Edge-case flags
---------------
NORMAL          : Both start & end positive, n >= 1
DECLINE_TO_LOSS : start > 0, end <= 0 (profitable → loss)
TURNAROUND      : start <= 0, end > 0  (loss → profitable)
BOTH_NEGATIVE   : Both start & end negative
ZERO_BASE       : start == 0 (undefined CAGR)
INSUFFICIENT    : Not enough data points for the requested window

Public API
----------
compute_cagr(start, end, n)  → (value | None, flag)

revenue_cagr(year_series, windows=(3, 5, 10))
pat_cagr(year_series, windows=(3, 5, 10))
eps_cagr(year_series, windows=(3, 5, 10))

Each *_cagr function accepts a dict {year: value} and returns:
    {n: {"value": float | None, "flag": str}}
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Constants — edge-case flag labels
# ─────────────────────────────────────────────────────────────────────────────
FLAG_NORMAL = "NORMAL"
FLAG_DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
FLAG_TURNAROUND = "TURNAROUND"
FLAG_BOTH_NEGATIVE = "BOTH_NEGATIVE"
FLAG_ZERO_BASE = "ZERO_BASE"
FLAG_INSUFFICIENT = "INSUFFICIENT"


def compute_cagr(
    start: Optional[float],
    end: Optional[float],
    n: int,
) -> Tuple[Optional[float], str]:
    """
    Compute CAGR over n years.

    Formula (when valid): ((end / start) ** (1 / n) - 1) * 100

    Parameters
    ----------
    start : value at the beginning of the period (year_t)
    end   : value at the end of the period (year_t+n)
    n     : number of years (must be >= 1)

    Returns
    -------
    (cagr_value, flag)
    cagr_value is None for all non-NORMAL flags.

    Edge cases handled
    ------------------
    * n < 1                     → INSUFFICIENT
    * start is None or end None → INSUFFICIENT
    * start == 0                → ZERO_BASE
    * start > 0, end <= 0       → DECLINE_TO_LOSS
    * start <= 0, end > 0       → TURNAROUND
    * start < 0, end < 0        → BOTH_NEGATIVE
    * start > 0, end > 0        → NORMAL  (computed)
    """
    if start is None or end is None or n < 1:
        return (None, FLAG_INSUFFICIENT)

    if start == 0:
        return (None, FLAG_ZERO_BASE)

    if start > 0 and end <= 0:
        return (None, FLAG_DECLINE_TO_LOSS)

    if start <= 0 and end > 0:
        return (None, FLAG_TURNAROUND)

    if start < 0 and end < 0:
        return (None, FLAG_BOTH_NEGATIVE)

    # NORMAL — both positive
    ratio = end / start
    cagr = (math.pow(ratio, 1.0 / n) - 1.0) * 100.0
    return (round(cagr, 4), FLAG_NORMAL)


# ─────────────────────────────────────────────────────────────────────────────
# Helper — extract start/end from a year→value series
# ─────────────────────────────────────────────────────────────────────────────


def _cagr_for_window(
    year_series: Dict[int, Optional[float]],
    anchor_year: int,
    window: int,
) -> Tuple[Optional[float], str]:
    """
    Given a {year: value} dict, compute CAGR anchored at anchor_year.

    Looks for the value at anchor_year − window (start) and anchor_year (end).
    Returns INSUFFICIENT if either year is missing or has a None value.
    """
    start_year = anchor_year - window
    start_val = year_series.get(start_year)
    end_val = year_series.get(anchor_year)

    if start_val is None or end_val is None:
        return (None, FLAG_INSUFFICIENT)

    return compute_cagr(start_val, end_val, window)


def _multi_window_cagr(
    year_series: Dict[int, Optional[float]],
    windows: Tuple[int, ...] = (3, 5, 10),
) -> Dict[int, Dict[str, object]]:
    """
    Compute CAGR for multiple windows using the latest available year as anchor.

    Returns
    -------
    {
        3:  {"value": float | None, "flag": str},
        5:  {"value": float | None, "flag": str},
        10: {"value": float | None, "flag": str},
    }
    """
    valid_years = sorted(y for y, v in year_series.items() if v is not None)
    if not valid_years:
        return {w: {"value": None, "flag": FLAG_INSUFFICIENT} for w in windows}

    anchor = valid_years[-1]  # latest year with data
    result: Dict[int, Dict[str, object]] = {}

    for w in windows:
        val, flag = _cagr_for_window(year_series, anchor, w)
        result[w] = {"value": val, "flag": flag}

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public convenience wrappers
# ─────────────────────────────────────────────────────────────────────────────


def revenue_cagr(
    year_series: Dict[int, Optional[float]],
    windows: Tuple[int, ...] = (3, 5, 10),
) -> Dict[int, Dict[str, object]]:
    """Revenue CAGR for 3yr, 5yr, 10yr windows."""
    return _multi_window_cagr(year_series, windows)


def pat_cagr(
    year_series: Dict[int, Optional[float]],
    windows: Tuple[int, ...] = (3, 5, 10),
) -> Dict[int, Dict[str, object]]:
    """PAT (Profit After Tax / Net Profit) CAGR for 3yr, 5yr, 10yr windows."""
    return _multi_window_cagr(year_series, windows)


def eps_cagr(
    year_series: Dict[int, Optional[float]],
    windows: Tuple[int, ...] = (3, 5, 10),
) -> Dict[int, Dict[str, object]]:
    """EPS CAGR for 3yr, 5yr, 10yr windows."""
    return _multi_window_cagr(year_series, windows)
