# Sprint 4 Retrospective — Dashboard & Valuation Module (Days 22–28)

## 📌 Sprint 4 Overview
**Epic 05**: 8-Screen Interactive Streamlit Dashboard (`src/dashboard/app.py` + `pages/`).  
**Epic 06**: Automated Valuation Engine (`src/analytics/valuation.py`) & Valuation Exports (`output/valuation_summary.xlsx`, `output/valuation_flags.csv`).  
**Story Points Completed**: 55 SP  
**Final Release Tag**: `v4.0`

---

## 💡 Key Accomplishments

1. **Streamlit Multi-Page App Architecture**:
   - Built scaffold (`src/dashboard/app.py`) with wide-layout configuration and sidebar navigation across 8 analytics screens.
   - Implemented centralized data query layer in `src/dashboard/utils/db.py` utilizing Streamlit `@st.cache_data(ttl=600)` caching, guaranteeing screen load times under 3 seconds.

2. **8 Interactive Analytics Screens**:
   - **01 Home Dashboard**: Executive summary with 6 KPI tiles, 11-sector Plotly donut chart, top-5 composite quality table, and financial year filter.
   - **02 Company Profile**: Instant ticker autocomplete, 10-year Revenue & Net Profit bar chart, ROE/ROCE dual-axis line chart, and color-coded pros/cons badges.
   - **03 Financial Screener**: 10 dynamic metric sliders, 6 preset filter triggers (Quality, Value, Growth, Dividend, Debt-Free, Turnaround), live result count, and CSV export capability.
   - **04 Peer Analytics**: 8-axis Plotly `Scatterpolar` radar chart comparing target company against peer group average, accompanied by benchmark matrix table.
   - **05 Financial Trends**: Multi-metric overlay trends (up to 3 metrics) featuring YoY percentage growth labels.
   - **06 Sector Analytics**: Interactive 4D Plotly bubble chart (X=Revenue, Y=ROE, Size=Market Cap, Color=Sub-sector) and sector median bar charts.
   - **07 Capital Allocation**: Plotly treemap organizing 92 companies by 8 capital allocation archetypes with drill-down tables.
   - **08 Annual Reports**: Document repository with year selectors, clickable BSE annual report links, and red 404 badges for missing links.

3. **Valuation Engine & Exports**:
   - Created `src/analytics/valuation.py` computing FCF Yield (%), 5-year Median P/E, Sector Median P/E, and Overvaluation Flags (Caution, Discount, Fair).
   - Exported `output/valuation_summary.xlsx` (92 rows, openpyxl styled) and `output/valuation_flags.csv` (44 flagged companies).

4. **Quality Assurance**:
   - Added `tests/dashboard/test_dashboard.py` bringing total test suite count to **199 passed unit tests** with 0 failures.

---

## 🎨 UX & Architectural Decisions

- **Caching & Query Performance**: Wrapping SQLite database calls with `@st.cache_data(ttl=600)` prevented redundant disk I/O on every slider movement or page navigation, resulting in instantaneous page re-renders.
- **Plotly Visual Consistency**: Selected consistent color palettes (`Viridis` for treemaps, custom hex values for dual-axis charts, pastel hues for sector donuts) to ensure a cohesive visual theme.
- **Form Navigation Reliability**: Created symlinks (`src/dashboard/pages` → `pages/`) and fallback `st.switch_page` handlers so the application launches seamlessly regardless of whether `streamlit run src/dashboard/app.py` or `streamlit run pages/01_home.py` is called.

---

## 🛠️ Edge Cases Handled

1. **Partial Historical Timelines**: For companies with less than 10 years of history or missing financials, charts gracefully render available years without throwing index errors or crashing.
2. **Extreme Slider Boundaries**: Extreme slider values in the Screener return an empty DataFrame with an informative prompt rather than raising a KeyError or layout crash.
3. **Missing Annual Report Links**: Checked document URLs with HTTP head requests and rendered clear red "❌ Report unavailable" badges when links are null or broken.
4. **Financial Sector Debt-to-Equity Exemption**: Financial sector companies (Banks, NBFCs, Insurance) are exempted from debt-to-equity ceiling filters to prevent improper filtering of leveraged financial balance sheets.

---

## 📈 Performance & Metrics Summary

- **Total Companies Covered**: 92
- **Total Unit Tests**: 199 Passed (101 ETL + 20 KPI + 14 Screener + 12 Dashboard & Valuation + 52 others)
- **Average Page Load Time**: < 1.2 seconds
- **Valuation Flags Identified**: 44 companies flagged (Caution / Discount)

---

## 🏁 Conclusion & Tagging
Sprint 4 fulfills all capstone objectives for the Nifty 100 Financial Data Pipeline & Dashboard project.

Git Tag: `v4.0`
