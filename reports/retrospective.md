# Sprint 1 Retrospective — Nifty 100 Financial Data Pipeline

**Sprint:** Sprint 1 — Data Foundation
**Duration:** 7 Days
**Status:** ✅ Complete

---

## Sprint Metrics

| Metric | Value |
|--------|-------|
| Days completed | 7 |
| Files created | 20+ |
| Unit tests written | 101 (55 loader + 46 validator) |
| DQ rules implemented | 16 |
| DB tables | 11 |
| DB indexes | 12 |
| DB views | 3 |
| Makefile targets | 12 |
| Git commits | 3 |
| Final tag | `v1.0` |

---

## What Went Well ✅

1. **Modular ETL design** — each file has a single responsibility; `normaliser.py`, `loader.py`, `validator.py`, and `load_pipeline.py` are independently testable and reusable in Sprint 2.

2. **Test-first approach** — writing 101 tests before touching real data caught edge cases in year normalisation (Excel serials, FY50 century boundary, NaN handling) that would have caused silent data corruption.

3. **Config-driven thresholds** — all DQ tolerances live in `.env` / `config.py`, making it trivial to tighten rules without changing code.

4. **Audit trail** — `load_audit.csv`, `validation_failures.csv`, `fix_audit.csv`, and `manual_review_report.txt` give a complete paper trail for every pipeline run, which is critical for a regulated financial dataset.

5. **Schema-first discipline** — defining `db/schema.sql` on Day 4 before loading any data forced us to think through FK relationships and data types upfront, preventing schema drift.

---

## What to Improve 🔧

1. **Column name mapping is fragile** — `loader.py` assumes column names match exactly after lowercase normalisation. Real Excel files from different vendors often have inconsistent headers. Sprint 2 should add a YAML-based column alias map.

2. **No data type coercion beyond year/ticker** — numeric columns that arrive as strings (e.g. `"1,234.56"` with commas) silently become NaN. A `clean_numeric()` helper is needed.

3. **Missing test coverage for `load_pipeline.py` and `demo.py`** — integration tests against a real (small) SQLite fixture would catch orchestration bugs early.

---

## Action Items for Sprint 2 📋

| # | Action Item | Owner | Priority |
|---|-------------|-------|----------|
| 1 | Add YAML column-alias map to `loader.py` for flexible header matching | _(you)_ | HIGH |
| 2 | Build `src/etl/clean_numeric.py` — strip commas, handle `Cr`/`Lakhs` suffixes | _(you)_ | HIGH |
| 3 | Add integration test suite `tests/etl/test_pipeline.py` using a tiny fixture DB | _(you)_ | MEDIUM |

---

## Technical Debt Log 🗒️

| Item | Location | Risk | Plan |
|------|----------|------|------|
| `load_table()` uses `if_exists="replace"` for core tables — wipes existing data on each run | `loader.py` L239 | MEDIUM — safe for now since pipeline always resets DB first | Add upsert logic in Sprint 2 |
| `normalize_ticker()` rejects numeric strings globally — edge case for some BSE-only companies that use numeric codes | `normaliser.py` L115 | LOW | Add `allow_numeric` flag if needed |
| `run_all_checks()` catches all exceptions silently | `validator.py` L288 | LOW | Surface to audit log |

---

## Sprint 2 Preview 🔭

Sprint 2 will build on this foundation with:

| Module | Description |
|--------|-------------|
| **EDA Notebooks** | Jupyter notebooks for revenue trends, OPM distribution, sector heatmaps |
| **Financial Ratios Engine** | Compute derived ratios (CAGR, ROE, ROCE, Altman Z-score) in `src/analytics/ratios.py` |
| **Visualisation Dashboard** | Streamlit app with sector filter, company deep-dive, and YoY comparison charts |
| **REST API** | Flask endpoints: `/companies`, `/financials/<id>`, `/sector/<name>` |
| **PDF Report Generator** | Automated company factsheet generator using `reportlab` |

---

*Nifty 100 Capstone — Sprint 1 complete. Ready for Sprint 2.*
