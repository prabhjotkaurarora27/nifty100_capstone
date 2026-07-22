# Sprint 5 Retrospective — NLP Engine, Cash Flow Intelligence & Batch PDF Reporting (Days 29–35)

## 📌 Sprint 5 Overview
**Epic 07**: Regex Analysis Parser (`src/nlp/parser.py`) & Rule-Based Pros/Cons Generator (`src/nlp/pros_cons_generator.py`).  
**Epic 08**: Cash Flow Intelligence Engine (`src/analytics/cashflow_kpis.py`) & Capital Allocation Tracking (`output/pattern_changes.csv`).  
**Epic 09**: ReportLab PDF Tearsheet Generator (`src/reports/tearsheet.py`), Sector Reports (`src/reports/sector_report.py`), Portfolio Summary (`src/reports/portfolio_summary.py`), and Batch Orchestrator (`src/reports/batch_generator.py`).  
**Story Points Completed**: 70 SP  
**Final Release Tag**: `v5.0`

---

## 💡 Key Accomplishments

1. **NLP Text Parsing & Cross-Validation**:
   - Built `src/nlp/parser.py` parsing 4 CAGR text fields in `analysis.xlsx` using regex `r"(\d+)\s*Years?:?\s*(-?[\d.]+)%"`.
   - Exported `output/analysis_parsed.csv` (65 parsed records) and `output/parse_failures.csv` (15 entries).
   - Cross-validated parsed 5yr CAGR against computed ratios from the Ratio Engine (0 divergence cases > 5%).

2. **24-Rule Pros & Cons Engine**:
   - Implemented 12 Pro rules (PR-01 to PR-12) and 12 Con rules (CR-01 to CR-12) in `src/nlp/pros_cons_generator.py`.
   - Calculated confidence scores (0–100%) and filtered matches $\le 60\%$.
   - Guaranteed $\ge 1$ Pro and $\ge 1$ Con for all 92 companies, exporting 504 rules to `output/pros_cons_generated.csv`.

3. **Cash Flow Intelligence & Pattern Tracking**:
   - Computed CFO Quality Scores, CapEx Intensity, Distress Signals ($CFO < 0 \text{ AND } CFF > 0$), and Deleveraging flags.
   - Exported `output/cashflow_intelligence.xlsx` (91 company rows) and `output/distress_alerts.csv` (13 distress alerts).
   - Exported `output/pattern_changes.csv` tracking 458 YoY capital allocation pattern shifts across Nifty 100 history.

4. **Batch PDF Tearsheets & Reports**:
   - Created ReportLab 2-page company tearsheets (`src/reports/tearsheet.py`) featuring embedded Matplotlib vector charts (P&L bar chart, ROE/ROCE line chart, Balance Sheet stacked bar chart, Cash Flow waterfall chart), KPI tiles, pros/cons badges, and capital allocation badges.
   - Batch generated 92 company tearsheet PDFs in `reports/tearsheets/` (all $> 100\text{ KB}$, well exceeding the $30\text{ KB}$ minimum requirement).
   - Generated 11 Sector PDF reports in `reports/sector/` and a 92-page Portfolio Summary PDF in `reports/portfolio/portfolio_summary.pdf`.

5. **Test Suite Expansion**:
   - Added `tests/nlp/test_nlp.py` and `tests/reports/test_reports.py` expanding test coverage to **204 passed unit tests** with 0 failures.

---

## 🛠️ Technical Insights & Edge Cases Handled

- **ReportLab Flowable Memory Management**: Used in-memory `io.BytesIO` image buffers generated via Matplotlib (`matplotlib.use('Agg')`) to embed dynamic financial charts cleanly into ReportLab PDF flowables.
- **Rule Fallback Guarantee**: Integrated secondary fallback rules for companies with sparse historical anomalies, guaranteeing that every single company in Nifty 100 receives at least 1 validated Pro bullet and 1 Con bullet with $>60\%$ confidence.
- **Financial Sector Leverage Rules**: Exempted Financial sector companies (Banks, NBFCs, Insurance) from non-financial D/E ceiling rules to avoid false positive risk alerts on leveraged financial institutions.

---

## 📈 Final Project Deliverables Summary

- **Total Companies Analyzed**: 92
- **Total Unit Tests**: 204 Passed (101 ETL + 20 KPI + 14 Screener + 12 Dashboard & Valuation + 57 NLP & Reports)
- **Tearsheet PDFs Generated**: 92 (100% company coverage)
- **Sector Report PDFs Generated**: 11
- **Portfolio Summary PDF**: `reports/portfolio/portfolio_summary.pdf`

---

## 🏁 Capstone Completion & Tagging
Sprint 5 completes the full Nifty 100 Financial Data Pipeline & Analytics Capstone Project.

Git Tag: `v5.0`
