"""
src/etl/normaliser.py
---------------------
Utility functions to normalise raw values extracted from Excel source files.

Functions
---------
normalize_year(value)  -> int | None
normalize_ticker(value) -> str | None
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Excel serial date epoch  (Windows / Lotus 1-2-3 epoch: 1900-01-00)
# Python's datetime does not support day-0, so we anchor at 1899-12-30.
# ---------------------------------------------------------------------------
_EXCEL_EPOCH = datetime(1899, 12, 30)

# Month abbreviation → month number (used for "Mar-21", "Mar 2021" patterns)
_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Ticker suffixes to strip (order matters: longer first)
_TICKER_SUFFIXES = re.compile(
    r"\.(BSE|NSE|NS|BO)$", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# normalize_year
# ---------------------------------------------------------------------------

def normalize_year(value) -> Optional[int]:
    """
    Convert a wide variety of year representations to a canonical integer year.

    Supported formats
    -----------------
    - FY2021, FY 2021, Fy2021, fy 2021   → 2021
    - FY21, FY 21, fy21                   → 2021  (century assumed: ≥50 → 19xx, <50 → 20xx)
    - 2020-21, 2020-2021, 2021-22          → 2021  (end year)
    - Mar-21, Mar 21, mar-21, mar 2021     → 2021
    - Plain int/float   2021, 2021.0       → 2021
    - Excel serial      44197              → 2021
    - None, "", whitespace                 → None
    - Unrecognisable garbage              → None

    Returns
    -------
    int or None
    """
    if value is None:
        return None

    # --- numeric path ---
    if isinstance(value, (int, float)):
        # NaN guard
        try:
            if value != value:          # NaN check (float nan)
                return None
        except Exception:
            return None

        int_val = int(value)

        # Reasonable 4-digit calendar year
        if 1900 <= int_val <= 2100:
            return int_val

        # Excel serial date (roughly 1900-01-01 = 1, 2100-01-01 = 73051)
        if 1 <= int_val <= 80000:
            try:
                dt = _EXCEL_EPOCH + timedelta(days=int_val)
                # Fiscal year: use the calendar year of the date
                return dt.year
            except Exception:
                return None

        return None

    # --- string path ---
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return None

    s = value.strip()
    if not s:
        return None

    # Pattern 1 – FY2021 / FY 2021 / Fy2021 / fy 2021
    m = re.fullmatch(r"[Ff][Yy]\s*(\d{4})", s)
    if m:
        return int(m.group(1))

    # Pattern 2 – FY21 / FY 21 / fy21 (2-digit year)
    m = re.fullmatch(r"[Ff][Yy]\s*(\d{2})", s)
    if m:
        yy = int(m.group(1))
        return 1900 + yy if yy >= 50 else 2000 + yy

    # Pattern 3 – 2020-21 / 2020-2021 / 2019-20
    m = re.fullmatch(r"(\d{4})[-/](\d{2,4})", s)
    if m:
        start = int(m.group(1))
        end_raw = m.group(2)
        if len(end_raw) == 2:
            end_yy = int(end_raw)
            end = 1900 + end_yy if end_yy >= 50 else 2000 + end_yy
        else:
            end = int(end_raw)
        # Return the end year (fiscal year convention)
        return end if end > start else start + 1

    # Pattern 4 – Mar-21 / Mar 21 / Mar-2021 / Mar 2021
    m = re.fullmatch(r"([A-Za-z]{3})[\s\-](\d{2,4})", s)
    if m:
        month_str = m.group(1).lower()
        if month_str in _MONTH_ABBR:
            year_raw = m.group(2)
            if len(year_raw) == 4:
                return int(year_raw)
            else:
                yy = int(year_raw)
                return 1900 + yy if yy >= 50 else 2000 + yy
        return None

    # Pattern 5 – plain 4-digit year "2021"
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        yr = int(m.group(1))
        if 1900 <= yr <= 2100:
            return yr

    # Pattern 6 – float string "2021.0"
    m = re.fullmatch(r"(\d{4})\.0+", s)
    if m:
        yr = int(m.group(1))
        if 1900 <= yr <= 2100:
            return yr

    return None


# ---------------------------------------------------------------------------
# normalize_ticker
# ---------------------------------------------------------------------------

def normalize_ticker(value) -> Optional[str]:
    """
    Normalise a stock ticker symbol.

    Rules
    -----
    1. None / non-string / empty → None
    2. Strip leading/trailing whitespace
    3. Remove exchange suffixes: .NS .BO .NSE .BSE (case-insensitive)
    4. UPPERCASE
    5. Replace internal spaces and hyphens with underscore  (e.g. "HDFC BANK" → "HDFC_BANK")
    6. Strip any remaining non-alphanumeric, non-underscore characters
    7. If result is empty after cleaning → None
    8. Pure-numeric strings → None  (e.g. "12345" is not a ticker)

    Returns
    -------
    str or None
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # Numeric values are not valid tickers
        return None

    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return None

    s = value.strip()
    if not s:
        return None

    # Remove exchange suffix
    s = _TICKER_SUFFIXES.sub("", s)

    # Uppercase
    s = s.upper()

    # Replace spaces and hyphens with underscore
    s = re.sub(r"[\s\-]+", "_", s)

    # Remove any character that is not alphanumeric or underscore
    s = re.sub(r"[^\w]", "", s)

    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)

    # Strip leading/trailing underscores
    s = s.strip("_")

    if not s:
        return None

    # Pure-numeric → not a valid ticker
    if s.isdigit():
        return None

    return s


# ---------------------------------------------------------------------------
# Self-test (run with:  python src/etl/normaliser.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    YEAR_CASES: list[tuple] = [
        # (input, expected_output, description)
        ("FY2021",   2021, "FY2021 string"),
        ("FY 2021",  2021, "FY 2021 with space"),
        ("FY21",     2021, "FY21 two-digit"),
        ("FY 21",    2021, "FY 21 two-digit with space"),
        ("fy2021",   2021, "lowercase fy2021"),
        ("fy 2021",  2021, "lowercase fy 2021"),
        ("fy21",     2021, "lowercase fy21"),
        ("2020-21",  2021, "dash range 2020-21"),
        ("2021-22",  2022, "dash range 2021-22"),
        ("2020-2021",2021, "full dash range 2020-2021"),
        ("Mar-21",   2021, "Mar-21"),
        ("Mar 21",   2021, "Mar 21"),
        ("mar-21",   2021, "mar-21 lowercase"),
        ("Mar 2021", 2021, "Mar 2021"),
        ("2021",     2021, "plain int string"),
        (2021,       2021, "plain int"),
        (2021.0,     2021, "float 2021.0"),
        ("  2021  ", 2021, "leading/trailing spaces"),
        (None,       None, "None input"),
        ("",         None, "empty string"),
        ("garbage",  None, "garbage string"),
        ("abc",      None, "short garbage"),
        (44197,      2021, "Excel serial 44197 → 2021"),
        ("FY50",     1950, "FY50 → century boundary"),
        ("FY49",     2049, "FY49 → 20xx century"),
    ]

    TICKER_CASES: list[tuple] = [
        ("RELIANCE",       "RELIANCE",     "plain ticker"),
        ("reliance",       "RELIANCE",     "lowercase ticker"),
        ("RELIANCE.NS",    "RELIANCE",     ".NS suffix"),
        ("RELIANCE.BO",    "RELIANCE",     ".BO suffix"),
        ("RELIANCE.BSE",   "RELIANCE",     ".BSE suffix"),
        ("RELIANCE.NSE",   "RELIANCE",     ".NSE suffix"),
        ("HDFC BANK",      "HDFC_BANK",    "space in name"),
        ("HDFC-BANK",      "HDFC_BANK",    "hyphen in name"),
        ("hdfc bank.ns",   "HDFC_BANK",    "lowercase + space + .ns"),
        ("  RELIANCE  ",   "RELIANCE",     "leading/trailing spaces"),
        (None,             None,           "None input"),
        ("",               None,           "empty string"),
        ("   ",            None,           "whitespace only"),
        (12345,            None,           "numeric int"),
        ("12345",          None,           "numeric string"),
    ]

    passed = 0
    failed = 0

    print("\n" + "="*60)
    print("  normalize_year  self-tests")
    print("="*60)
    for inp, expected, desc in YEAR_CASES:
        result = normalize_year(inp)
        ok = result == expected
        icon = "✅" if ok else "❌"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon}  {desc:<35}  input={repr(inp):<15}  got={repr(result):<10}  expected={repr(expected)}")

    print("\n" + "="*60)
    print("  normalize_ticker  self-tests")
    print("="*60)
    for inp, expected, desc in TICKER_CASES:
        result = normalize_ticker(inp)
        ok = result == expected
        icon = "✅" if ok else "❌"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon}  {desc:<35}  input={repr(inp):<20}  got={repr(result):<15}  expected={repr(expected)}")

    total = passed + failed
    print("\n" + "="*60)
    print(f"  Result: {passed}/{total} passed", "✅ ALL PASS" if failed == 0 else f"❌ {failed} FAILED")
    print("="*60 + "\n")

    sys.exit(0 if failed == 0 else 1)
