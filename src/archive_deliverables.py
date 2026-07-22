import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = PROJECT_ROOT / "output" / "final_deliverables"


def archive_all_deliverables():
    """Archive all 23 key project deliverables into output/final_deliverables/."""
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    deliverables = [
        PROJECT_ROOT / "db" / "nifty100.db",
        PROJECT_ROOT / "output" / "screener_output.xlsx",
        PROJECT_ROOT / "output" / "peer_comparison.xlsx",
        PROJECT_ROOT / "output" / "valuation_summary.xlsx",
        PROJECT_ROOT / "output" / "analysis_parsed.csv",
        PROJECT_ROOT / "output" / "pros_cons_generated.csv",
        PROJECT_ROOT / "output" / "cashflow_intelligence.xlsx",
        PROJECT_ROOT / "output" / "distress_alerts.csv",
        PROJECT_ROOT / "output" / "pattern_changes.csv",
        PROJECT_ROOT / "output" / "cluster_labels.csv",
        PROJECT_ROOT / "output" / "outlier_report.csv",
        PROJECT_ROOT / "output" / "portfolio_stats.csv",
        PROJECT_ROOT / "output" / "perf_notes.md",
        PROJECT_ROOT / "reports" / "elbow_plot.png",
        PROJECT_ROOT / "reports" / "correlation_heatmap.png",
        PROJECT_ROOT / "reports" / "pytest_report.html",
        PROJECT_ROOT / "reports" / "portfolio" / "portfolio_summary.pdf",
        PROJECT_ROOT / "docs" / "openapi.json",
        PROJECT_ROOT / "docs" / "analyst_guide.pdf",
        PROJECT_ROOT / "docs" / "acceptance_checklist.pdf",
    ]

    copied_count = 0
    for item in deliverables:
        if item.exists():
            if item.is_file():
                shutil.copy2(item, FINAL_DIR / item.name)
                copied_count += 1

    print(f"✅ Archived {copied_count} key deliverable files to {FINAL_DIR}")


if __name__ == "__main__":
    archive_all_deliverables()
