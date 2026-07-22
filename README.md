# 📈 Nifty 100 Financial Data Pipeline & Analytics Platform

[![Python 3.9](https://img.shields.io/badge/Python-3.9.6-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red.svg)](https://streamlit.io/)
[![pytest](https://img.shields.io/badge/pytest-250_passed-brightgreen.svg)](https://docs.pytest.org/)
[![Tag](https://img.shields.io/badge/Release-v6.0-gold.svg)](https://github.com/prabhjotkaurarora27/nifty100_capstone)

An end-to-end institutional financial data engine, ratio calculation engine, quality screener, peer benchmarking framework, machine learning clustering module, 8-screen Streamlit web application, 16-endpoint FastAPI REST API, and ReportLab PDF reporting suite covering all **92 Nifty 100 constituent companies** over a 10-year historical horizon (2015–2024).

---

## 🚀 Key Platform Features

1. **Robust ETL Data Pipeline**: Ingests multi-sheet raw Excel financial statements across 92 Nifty 100 companies, normalizes year formats & tickers, and enforces 16 automated Data-Quality (DQ) validation rules into SQLite (`db/nifty100.db`).
2. **Comprehensive Ratio Engine**: Computes 20+ financial KPIs including ROE, ROCE, NPM, OPM, Debt-to-Equity, Asset Turnover, FCF Conversion, and Interest Coverage with financial sector leverage exemptions.
3. **Quality Stock Screener**: Supports 6 analyst-configurable preset screens with a Winsorized Composite Quality Score (0–100) and exports formatted Excel reports (`screener_output.xlsx`, `peer_comparison.xlsx`).
4. **Peer Analytics & Polar Radar Charts**: Maps companies to 11 peer groups with inverted leverage rankings and generates 91 high-resolution polar radar charts in `reports/radar_charts/`.
5. **Interactive 8-Screen Streamlit Dashboard**: Served on `http://localhost:8501`, providing interactive visual analytics, 10-year trend overlays, dynamic screener sliders, sector bubble charts, and capital allocation treemaps.
6. **NLP Analysis Engine**: Parses text fields via regex and evaluates 24 Pro/Con rules with confidence scoring (>60%) guaranteeing $\ge 1$ Pro and $\ge 1$ Con for every company.
7. **Machine Learning Clustering**: Segments 92 companies into 5 financial archetypes via KMeans ($k=5$) with elbow plots (`reports/elbow_plot.png`) and correlation heatmaps (`reports/correlation_heatmap.png`).
8. **Institutional PDF Reporting Suite**: Generates 92 2-page company executive tearsheet PDFs ($>100\text{ KB}$ each), 11 sector PDF reports, and a 92-page portfolio summary PDF (`reports/portfolio/portfolio_summary.pdf`).
9. **Production REST API (16 Endpoints)**: Built with FastAPI on `http://localhost:8000`, featuring OpenAPI documentation (`/docs`, `docs/openapi.json`), CORS middleware, request logging, and sub-100ms response times.
10. **250 Passed Unit Tests**: 100% test passing rate across all 6 Sprints with HTML test reports (`reports/pytest_report.html`).

---

## 🛠️ Quick Start & Setup Guide

### 1. Environment Setup
```bash
git clone https://github.com/prabhjotkaurarora27/nifty100_capstone.git
cd nifty100_capstone
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch Streamlit Web Dashboard (Port 8501)
```bash
venv/bin/streamlit run src/dashboard/app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

### 3. Launch FastAPI REST Server (Port 8000)
```bash
venv/bin/uvicorn src.api.main:app --port 8000 --reload
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for interactive OpenAPI documentation.

### 4. Run Machine Learning Clustering & Statistics
```bash
PYTHONPATH=. venv/bin/python3 src/analytics/clustering.py
```

### 5. Generate Batch PDF Tearsheets & Reports
```bash
PYTHONPATH=. venv/bin/python3 src/reports/batch_generator.py
```

### 6. Run Comprehensive Pytest Suite (250 Tests)
```bash
PYTHONPATH=. venv/bin/pytest tests/ --html=reports/pytest_report.html -v
```

---

## 📑 REST API Endpoint Summary (16 Endpoints)

| Method | Endpoint Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System health status, database row counts, uptime |
| `GET` | `/api/v1/companies` | List all 92 companies with sector & search filters |
| `GET` | `/api/v1/companies/{ticker}` | Full company profile and latest ratios |
| `GET` | `/api/v1/companies/{ticker}/pl` | Historical Profit & Loss statements |
| `GET` | `/api/v1/companies/{ticker}/bs` | Historical Balance Sheet statements |
| `GET` | `/api/v1/companies/{ticker}/cashflow` | Historical Cash Flow statements |
| `GET` | `/api/v1/companies/{ticker}/ratios` | Computed ratio history per year |
| `GET` | `/api/v1/companies/{ticker}/tearsheet` | Binary PDF download of 2-page tearsheet |
| `GET` | `/api/v1/screener` | Multi-parameter quality screener execution |
| `GET` | `/api/v1/sectors` | Summary and median KPIs across 11 broad sectors |
| `GET` | `/api/v1/sectors/{sector}/companies` | All constituent companies in a sector |
| `GET` | `/api/v1/peers/{group_name}` | Peer group members and percentile ranks |
| `GET` | `/api/v1/companies/{ticker}/peers/compare` | Radar chart comparative metrics vs peer avg |
| `GET` | `/api/v1/market-cap/{ticker}` | Historical valuation multiples (P/E, P/B, EV/EBITDA) |
| `GET` | `/api/v1/portfolio/stats` | Portfolio P10–P90 percentile statistics table |
| `GET` | `/api/v1/companies/{ticker}/documents` | Annual report BSE document URLs |

---

## 📁 Repository Structure

```
nifty100_capstone/
├── config.py                   # Central configuration
├── config/
│   └── screener_config.yaml    # Screener threshold criteria
├── db/
│   └── nifty100.db             # SQLite database (10 tables)
├── docs/
│   ├── openapi.json            # OpenAPI REST specification
│   ├── analyst_guide.pdf       # 11-page Technical Analyst Guide PDF
│   └── acceptance_checklist.pdf# Final signed-off audit checklist
├── src/
│   ├── etl/                    # Normaliser, Validator (16 DQ), Loader
│   ├── analytics/              # Ratios, CAGR, Cashflow, Valuation, Clustering
│   ├── screener/               # Quality screener engine & radar charts
│   ├── dashboard/              # Streamlit scaffold & 8 page modules
│   ├── nlp/                    # Regex parser & 24-rule Pros/Cons generator
│   ├── reports/                # ReportLab PDF tearsheets & sector reports
│   └── api/                    # FastAPI main app & 8 router modules
├── output/                     # Excel reports, CSV exports, stats, final_deliverables/
├── reports/                    # Radar charts, elbow plot, heatmap, PDF reports, pytest_report.html
└── tests/                      # 250 unit & API tests (100% passed)
```

---

## 📜 Final Acceptance Sign-Off

The Nifty 100 Capstone Project has passed all **20 formal Acceptance Gates (AC-01 to AC-20)** and has been delivered with **tag `v6.0`**.
