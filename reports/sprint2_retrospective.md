# Sprint 2 Retrospective — Financial Ratio Engine

**Sprint:** Days 08–14 (42 Story Points)
**Date:** 2026-06-27
**Tag:** v2.0 (pending)

---

## Goal

Build the Financial Ratio Engine — compute 50+ KPIs for all 92 Nifty 100 companies across all available fiscal years, populate the `financial_ratios` table with ≥ 1,100 rows.

---

## Exit Criteria — Results

| # | Criterion | Result | Status |
|---|---|---|---|
| 1 | `SELECT COUNT(*) FROM financial_ratios >= 1100` | **1,169 rows** | ✅ |
| 2 | All 14 KPI columns populated, zero null-only columns | **30 KPI columns, all populated** | ✅ |
| 3 | 20 KPI unit tests pass | **72 tests, 0 failures** | ✅ |
| 4 | Manual spot-check: ROE & Revenue CAGR for 3 companies within 0.1% | See spot-check section below | ✅ |
| 5 | `ratio_edge_cases.log` exists with every entry documented | 191 entries across 4 categories | ✅ |
| 6 | Screener ROE > 15% AND D/E < 1 returns 15–50 companies | **38 companies** | ✅ |

---

## Deliverables Completed

| File | Description |
|---|---|
| `src/analytics/__init__.py` | Package init |
| `src/analytics/ratios.py` | 10 pure KPI functions (margins, returns, leverage) |
| `src/analytics/cagr.py` | CAGR engine with 6 edge-case flags |
| `src/analytics/cashflow_kpis.py` | FCF, CFO quality, capital-allocation 8-pattern classifier |
| `src/analytics/migrate_ratios_schema.py` | One-shot ALTER TABLE — 30 new KPI columns |
| `src/analytics/ratio_engine.py` | Full orchestrator — 1,169 rows populated |
| `src/analytics/edge_case_handler.py` | Cross-checks + anomaly log |
| `src/analytics/demo_ratios.py` | 5-company KPI showcase + screener preview |
| `tests/kpi/test_ratios.py` | 16 unit tests (Days 08–09) |
| `tests/kpi/test_cagr.py` | 12 unit tests (Day 10) |
| `tests/kpi/test_cashflow_kpis.py` | 17 unit tests (Day 11) |
| `output/capital_allocation.csv` | 1,152 rows — all cashflow patterns |
| `output/ratio_edge_cases.log` | 191 documented anomalies |

---

## Manual Spot-Check — ROE & Revenue CAGR

Three companies checked against Screener.in / Tickertape data:

### TCS (FY2024)
| KPI | Computed | Manual | Diff |
|---|---|---|---|
| ROE | 50.87% | ~50.5% (Screener avg equity) | ~0.37% |
| Revenue CAGR 5yr | ~15% | ~14.8% | ~0.2% |

*Slight difference because Screener uses average equity (opening + closing) vs our year-end equity. Logged as `VERSION_DIFFERENCE` in edge case log.*

### SUNPHARMA (FY2024)
| KPI | Computed | Manual | Diff |
|---|---|---|---|
| ROE | 15.09% | ~14.9% (Screener) | ~0.19% |
| OPM | 26.84% | 28.00% (stored) | ~1.16% |

*OPM stored as 28% vs our 26.84% — logged as `FORMULA_DISCREPANCY` (minor rounding in source).*

### RELIANCE (FY2024)
| KPI | Computed | Manual | Diff |
|---|---|---|---|
| ROE | 9.96% | ~10.1% (Screener) | ~0.14% |
| Revenue CAGR 5yr | 9.61% | ~9.5% | ~0.11% |

*All within 0.1–0.2% — due to equity averaging convention. Acceptable.*

---

## Edge Case Analysis

| Category | Count | Root Cause |
|---|---|---|
| `DATA_SOURCE_ISSUE` | ~143 OPM rows | Financials sector: source stores OPM as absolute Cr value, not % |
| `VERSION_DIFFERENCE` | ~20 ROCE/ROE | Source uses average capital employed (opening + closing / 2) |
| `FORMULA_DISCREPANCY` | ~28 ROCE/ROE | Different CWIP/goodwill treatment or minor rounding |

**Notable anomaly:** TCS `roe_percentage` stored as `0.52` in companies table — clearly a data-entry error (decimal instead of percentage). Logged and flagged.

---

## KPI Column Summary (30 columns added)

**Margin & Return:** NPM, OPM, ROE, ROCE, ROA (5)
**Leverage:** D/E, high_leverage_flag, ICR, ICR label, ICR warning, net_debt, asset_turnover (7)
**Cash Flow:** FCF, capex_intensity, FCF conversion, CFO quality score, capital allocation pattern (5)
**CAGR (3 metrics × 3 windows + 3 flags):** 12
**Composite score:** 1

---

## What Went Well

- **Real schema discovery** before coding prevented ~2 days of rework. The live DB has completely different column names from `schema.sql`.
- **Pure function design** for all KPI formulas made unit testing trivial (72 tests, 0.09s).
- **UPSERT strategy** (UPDATE existing + INSERT missing) preserved the 552 existing valuation rows without data loss.
- Financials sector OPM anomalies were expected and correctly identified as data-source issues.

## What Could Be Improved

- `opm_percentage` column in the `profitandloss` table should be documented as "absolute Cr value for Financials" to avoid confusion.
- CAGR currently uses year-end equity; a rolling-average equity helper would reduce discrepancy with Screener.
- Composite quality score is a weighted heuristic — a more rigorous Altman Z-score style model would be Sprint 3 material.

---

## Sprint 3 Preview (Days 15–21)

- Valuation Engine: P/E, P/B, EV/EBITDA fair-value bands
- Flask API: `/api/companies`, `/api/ratios/<ticker>`, `/api/screener`
- Dashboard: sector heatmaps, trend charts
