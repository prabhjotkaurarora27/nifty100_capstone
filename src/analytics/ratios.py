"""
src/analytics/ratios.py
=======================
Sprint 2 — Days 08 & 09
Pure KPI formula functions.  No database calls, no side-effects.
All inputs are plain Python numbers (or None).

Day 08 — Return & Margin Ratios
    net_profit_margin
    operating_profit_margin
    return_on_equity
    return_on_capital_employed
    return_on_assets

Day 09 — Leverage & Liquidity Ratios
    debt_to_equity
    high_leverage_flag
    interest_coverage
    net_debt
    asset_turnover
"""

from __future__ import annotations

import logging
import math
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Day 08 — Return & Margin Ratios
# ─────────────────────────────────────────────────────────────────────────────

def net_profit_margin(net_profit: Optional[float],
                      sales: Optional[float]) -> Optional[float]:
    """
    Net Profit Margin (%).

    Parameters
    ----------
    net_profit : net profit in Cr
    sales      : total revenue / sales in Cr

    Returns
    -------
    float  : (net_profit / sales) * 100
    None   : if sales is 0 or None, or net_profit is None
    """
    if sales is None or net_profit is None:
        return None
    if sales == 0:
        return None
    return round((net_profit / sales) * 100, 4)


def operating_profit_margin(operating_profit: Optional[float],
                             sales: Optional[float],
                             opm_percentage: Optional[float] = None,
                             company_id: str = "",
                             year: Optional[float] = None) -> Optional[float]:
    """
    Operating Profit Margin (%).

    Cross-checks against the stored `opm_percentage` column if provided;
    logs a warning when the absolute difference exceeds 1 percentage point.

    Parameters
    ----------
    operating_profit : operating profit in Cr
    sales            : total revenue in Cr
    opm_percentage   : source value from profitandloss.opm_percentage (0–100 scale)
    company_id       : used in log messages only
    year             : used in log messages only

    Returns
    -------
    float : (operating_profit / sales) * 100
    None  : if sales is 0 or None, or operating_profit is None
    """
    if sales is None or operating_profit is None:
        return None
    if sales == 0:
        return None

    computed = round((operating_profit / sales) * 100, 4)

    if opm_percentage is not None:
        diff = abs(computed - opm_percentage)
        if diff > 1.0:
            logger.warning(
                "OPM mismatch — company=%s year=%s computed=%.2f%% stored=%.2f%% diff=%.2f%%",
                company_id, year, computed, opm_percentage, diff,
            )

    return computed


def return_on_equity(net_profit: Optional[float],
                     equity_capital: Optional[float],
                     reserves: Optional[float]) -> Optional[float]:
    """
    Return on Equity (%).

    ROE = (Net Profit / Shareholders' Equity) * 100
    Shareholders' Equity = equity_capital + reserves

    Returns None if equity_capital + reserves <= 0 (prevents divide-by-zero
    and economically meaningless negative-equity results).
    """
    if net_profit is None or equity_capital is None or reserves is None:
        return None
    equity = (equity_capital or 0.0) + (reserves or 0.0)
    if equity <= 0:
        return None
    return round((net_profit / equity) * 100, 4)


def return_on_capital_employed(ebit: Optional[float],
                                equity: Optional[float],
                                reserves: Optional[float],
                                borrowings: Optional[float],
                                is_financial: bool = False) -> Optional[float]:
    """
    Return on Capital Employed (%).

    ROCE = (EBIT / Capital Employed) * 100

    For non-financial companies:
        Capital Employed = equity_capital + reserves + borrowings

    For Financials sector companies, borrowings are a core operating input
    (deposits / debt capital), so we use only equity-side capital:
        Capital Employed = equity_capital + reserves

    Returns None if Capital Employed <= 0 or EBIT is None.
    """
    if ebit is None:
        return None
    eq = (equity or 0.0) + (reserves or 0.0)
    borr = (borrowings or 0.0)
    capital_employed = eq if is_financial else eq + borr
    if capital_employed <= 0:
        return None
    return round((ebit / capital_employed) * 100, 4)


def return_on_assets(net_profit: Optional[float],
                     total_assets: Optional[float]) -> Optional[float]:
    """
    Return on Assets (%).

    ROA = (Net Profit / Total Assets) * 100

    Returns None if total_assets is 0 or None.
    """
    if net_profit is None or total_assets is None:
        return None
    if total_assets == 0:
        return None
    return round((net_profit / total_assets) * 100, 4)


# ─────────────────────────────────────────────────────────────────────────────
# Day 09 — Leverage & Liquidity Ratios
# ─────────────────────────────────────────────────────────────────────────────

def debt_to_equity(borrowings: Optional[float],
                   equity_capital: Optional[float],
                   reserves: Optional[float]) -> Optional[float]:
    """
    Debt-to-Equity Ratio.

    D/E = Borrowings / (Equity Capital + Reserves)

    Returns
    -------
    0.0   : if borrowings is 0 or None (debt-free company)
    None  : if equity is 0 or negative (meaningless denominator)
    float : D/E ratio rounded to 4 dp
    """
    borr = borrowings or 0.0
    if borr <= 0:
        return 0.0
    eq = (equity_capital or 0.0) + (reserves or 0.0)
    if eq <= 0:
        return None
    return round(borr / eq, 4)


def high_leverage_flag(de_ratio: Optional[float],
                       is_financial: bool = False) -> bool:
    """
    Flag True when D/E > 5 AND the company is NOT in the Financials sector.

    Financials companies (banks, NBFCs, insurance) are exempt because
    high leverage is structurally normal for them.
    """
    if de_ratio is None:
        return False
    if is_financial:
        return False
    return de_ratio > 5.0


def interest_coverage(operating_profit: Optional[float],
                      other_income: Optional[float],
                      interest: Optional[float]) -> Tuple[Optional[float], Optional[str], bool]:
    """
    Interest Coverage Ratio (ICR).

    ICR = (Operating Profit + Other Income) / Interest

    Returns
    -------
    Tuple[icr_value, label, icr_warning]

    icr_value  : float (rounded) or None
    label      : "Debt Free" if interest == 0, else None
    icr_warning: True if 0 < ICR < 1.5 (financial stress signal)

    Special cases
    -------------
    * interest == 0 or None  → (None, "Debt Free", False)
    * numerator inputs None  → (None, None, False)
    """
    if interest is None or interest == 0:
        return (None, "Debt Free", False)

    if operating_profit is None:
        return (None, None, False)

    numerator = (operating_profit or 0.0) + (other_income or 0.0)
    icr = round(numerator / interest, 4)
    warning = 0 < icr < 1.5
    return (icr, None, warning)


def net_debt(borrowings: Optional[float],
             investments: Optional[float]) -> Optional[float]:
    """
    Net Debt (Cr).

    Net Debt = Borrowings − Investments
    A negative result means the company holds more liquid investments
    than its total debt (net cash position).
    """
    if borrowings is None:
        return None
    borr = borrowings or 0.0
    inv = investments or 0.0
    return round(borr - inv, 4)


def asset_turnover(sales: Optional[float],
                   total_assets: Optional[float]) -> Optional[float]:
    """
    Asset Turnover Ratio.

    Asset Turnover = Sales / Total Assets

    Returns None if total_assets is 0 or None.
    """
    if sales is None or total_assets is None:
        return None
    if total_assets == 0:
        return None
    return round(sales / total_assets, 4)
