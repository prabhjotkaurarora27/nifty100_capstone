# Nifty 100 Financial Data Pipeline

> **Sprint 1: Data Foundation** — A production-grade ETL pipeline for Nifty 100 company financials, built as a capstone project for the Bluestock Fintech internship.

---

## Architecture

```
data/raw/  (12 Excel/CSV files)
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                   ETL Pipeline                      │
│                                                     │
│  file_inspector.py  ──► normaliser.py               │
│                              │                      │
│                         loader.py                   │
│                              │                      │
│                    load_pipeline.py                  │
│                    (orchestrator)                    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              db/nifty100.db  (SQLite)
              ┌──────────────────────┐
              │  11 tables           │
              │  12 indexes          │
              │  3 views             │
              └──────────┬───────────┘
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
        validator.py  demo.py   exploratory_queries.py
        (16 DQ rules)          (10 analysis queries)
             │
             ▼
   output/validation_failures.csv
   output/load_audit.csv
   output/manual_review_report.txt
```

---

## Quickstart

```bash
# 1. Clone and enter project
git clone <your-repo-url>
cd nifty100_capstone

# 2. Create venv and install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Initialise database schema
make schema

# 4. Place Excel/CSV files in data/raw/, then load
make load

# 5. Run the full Sprint 1 demo
python src/etl/demo.py
```

---

## Directory Structure

```
nifty100_capstone/
├── config.py                   # Central config (loaded from .env)
├── .env                        # Environment variables (not in git)
├── .gitignore
├── Makefile                    # 12 make targets
├── requirements.txt
├── data/
│   ├── raw/                    # 12 source Excel/CSV files
│   └── processed/
├── db/
│   ├── schema.sql              # 11 tables, 12 indexes, 3 views
│   └── init_db.py              # Schema initialiser + verifier
├── notebooks/
│   ├── exploratory_queries.sql # 10 SQL queries
│   └── exploratory_queries.py  # Same queries, Python + tabulate
├── output/                     # Generated reports (gitignored)
│   ├── load_audit.csv
│   ├── validation_failures.csv
│   ├── manual_review_report.txt
│   └── pipeline.log
├── reports/
│   ├── sprint1_review.md       # Sprint 1 review template
│   └── retrospective.md        # Sprint 1 retrospective
├── src/
│   └── etl/
│       ├── normaliser.py       # normalize_year(), normalize_ticker()
│       ├── loader.py           # 12-file ETL loader
│       ├── validator.py        # 16 DQ rules
│       ├── load_pipeline.py    # Orchestrator (reset→load→verify)
│       ├── file_inspector.py   # Scan data/raw/ before loading
│       ├── manual_review.py    # Sample 5 companies, DQ review
│       ├── fix_loader.py       # Retry SKIPPED/ERROR files
│       └── demo.py             # Sprint 1 end-to-end demo
└── tests/
    └── etl/
        ├── test_loader.py      # 55 tests
        └── test_validator.py   # 46 tests
```

---

## Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `make install` | `pip install -r requirements.txt` | Install all dependencies |
| `make schema` | `python db/init_db.py` | Create / reset SQLite schema |
| `make load` | `python src/etl/load_pipeline.py` | Full load: reset → ETL → verify |
| `make inspect` | `python src/etl/file_inspector.py` | Preview files in `data/raw/` |
| `make validate` | `python src/etl/validator.py` | Run 16 DQ rules |
| `make review` | `python src/etl/manual_review.py` | Sample 5 companies, write review |
| `make fix` | `python src/etl/fix_loader.py` | Retry SKIPPED/ERROR files |
| `make demo` | `python src/etl/demo.py` | End-to-end Sprint 1 demo |
| `make explore` | `python notebooks/exploratory_queries.py` | Run 10 analytical queries |
| `make test` | `pytest tests/etl/ --tb=short -q` | Run 101 unit tests |
| `make clean` | Remove `__pycache__`, `.pyc` | Clean build artefacts |
| `make reset` | `rm db/nifty100.db && make schema` | Drop and recreate DB |

---

## Data Quality Rules (16)

| Rule | Severity | Check |
|------|----------|-------|
| DQ-01 | CRITICAL | PK uniqueness on `companies.company_id` |
| DQ-02 | CRITICAL | Composite PK `(company_id, year)` in P&L, BS, CF |
| DQ-03 | CRITICAL | FK integrity — child tables → companies |
| DQ-04 | WARNING | Balance sheet: `assets ≈ liabilities + equity` (±1%) |
| DQ-05 | WARNING | OPM: `operating_profit / revenue` within configured range |
| DQ-06 | WARNING | Positive sales: `revenue > 0` |
| DQ-07 | CRITICAL | No null `company_id` in any table |
| DQ-08 | CRITICAL | No null `year` in financial tables |
| DQ-09 | WARNING | Net cash: `op + inv + fin ≈ net_cash` (±5%) |
| DQ-10 | WARNING | Tax rate: 0% – 60% |
| DQ-11 | WARNING | Dividend payout ratio ≤ configured cap |
| DQ-12 | INFO | URL format check in `documents` table |
| DQ-13 | CRITICAL | No duplicate tickers in `companies` |
| DQ-14 | WARNING | EPS sign consistency with net profit |
| DQ-15 | WARNING | BSE code is 6-digit numeric |
| DQ-16 | INFO | Year coverage ≥ `DQ_MIN_YEAR_COVERAGE` per company |

---

## Expected Row Counts

| Table | Expected Rows | Tolerance |
|-------|--------------|-----------|
| companies | 92 | Exact |
| profitandloss | ~1276 | ±10% |
| balancesheet | ~1312 | ±10% |
| cashflow | ~1187 | ±10% |
| stock_prices | 5520 | Exact |
| sectors | varies | — |
| financial_ratios | varies | — |
| peer_groups | varies | — |

---

## Tech Stack

| Component | Library / Tool |
|-----------|---------------|
| Language | Python 3.9.6 |
| Database | SQLite 3 (via `sqlite3` stdlib) |
| Data loading | `pandas` 2.1.4, `openpyxl` 3.1.2 |
| Normalisation | Custom (`normaliser.py`) |
| Logging | `loguru` 0.7.2 |
| Progress bars | `tqdm` 4.66.1 |
| Table output | `tabulate` |
| Config | `python-dotenv` 1.0.1 |
| Testing | `pytest` 8.0.0, `pytest-cov` 4.1.0 |
| Dashboard (Sprint 2) | `streamlit` 1.31.0 |
| API (Sprint 2) | `flask` 3.0.1 |

---

## Running Tests

```bash
source venv/bin/activate

# Run full suite with coverage
make test

# Verbose with test names
pytest tests/etl/ -v

# Single file
pytest tests/etl/test_loader.py -v
pytest tests/etl/test_validator.py -v
```

**Test count:** 101 (55 loader + 46 validator)

---

## Sprint 1 Exit Criteria

- [ ] All 12 source files loaded without ERROR
- [ ] `companies` table = 92 rows
- [ ] `PRAGMA foreign_key_check` = 0 violations
- [ ] 0 CRITICAL DQ failures
- [ ] 101 unit tests passing
- [ ] Sprint review report completed and committed

---

## Author

**Internship:** Bluestock Fintech — Nifty 100 Capstone Project
**Sprint:** Sprint 1 — Data Foundation
**Python version:** 3.9.6 | **OS:** macOS
**Tag:** `v1.0`
