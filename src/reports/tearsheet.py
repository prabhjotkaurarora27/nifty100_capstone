import io
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports" / "tearsheets"


def generate_company_tearsheet(ticker: str, output_pdf_path: Path = None) -> Path:
    """Generates a 2-page PDF company tearsheet using ReportLab."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_pdf_path is None:
        output_pdf_path = REPORTS_DIR / f"{ticker}_tearsheet.pdf"

    conn = sqlite3.connect(str(DB_PATH))

    # Fetch company info
    comp_df = pd.read_sql_query(
        "SELECT c.*, s.broad_sector, s.sub_sector FROM companies c LEFT JOIN sectors s ON c.id = s.company_id WHERE c.id = ?",
        conn,
        params=[ticker],
    )
    if comp_df.empty:
        conn.close()
        raise ValueError(f"Ticker '{ticker}' not found in database.")

    comp_info = comp_df.iloc[0]

    # Fetch financial data
    ratios_df = pd.read_sql_query(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC",
        conn,
        params=[ticker],
    )
    pl_df = pd.read_sql_query(
        "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC",
        conn,
        params=[ticker],
    )
    bs_df = pd.read_sql_query(
        "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC",
        conn,
        params=[ticker],
    )
    cf_df = pd.read_sql_query(
        "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC",
        conn,
        params=[ticker],
    )
    conn.close()

    # Fetch pros & cons
    pros_cons_path = OUTPUT_DIR / "pros_cons_generated.csv"
    pros_list, cons_list = [], []
    if pros_cons_path.exists():
        pc_df = pd.read_csv(pros_cons_path)
        c_pc = pc_df[pc_df["company_id"] == ticker]
        pros_list = c_pc[c_pc["type"] == "pro"]["text"].tolist()
        cons_list = c_pc[c_pc["type"] == "con"]["text"].tolist()

    # Build PDF document
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#FFFFFF"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#D9E2EC"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1F497D"),
        spaceBefore=8,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    story = []

    # =========================================================================
    # PAGE 1
    # =========================================================================

    # Header Bar Table
    header_p1 = Paragraph(
        f"<b>{comp_info['company_name']} ({ticker})</b>", title_style
    )
    header_p2 = Paragraph(
        f"Sector: {comp_info.get('broad_sector', 'N/A')} | Sub-Sector: {comp_info.get('sub_sector', 'N/A')}",
        subtitle_style,
    )

    header_data = [[header_p1], [header_p2]]
    header_table = Table(header_data, colWidths=[540])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1F497D")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 6 KPI Tiles Table
    latest_r = ratios_df.iloc[-1] if not ratios_df.empty else {}
    latest_c = cf_df.iloc[-1] if not cf_df.empty else {}

    roe = latest_r.get("return_on_equity_pct")
    roce = latest_r.get("return_on_capital_employed_pct")
    npm = latest_r.get("net_profit_margin_pct")
    de = latest_r.get("debt_to_equity")
    rev_cagr = latest_r.get("revenue_cagr_5yr")
    fcf = latest_r.get("free_cash_flow_cr")

    kpi_data = [
        [
            Paragraph(f"<b>ROE</b><br/>{roe:.1f}%" if pd.notnull(roe) else "<b>ROE</b><br/>N/A", bullet_style),
            Paragraph(f"<b>ROCE</b><br/>{roce:.1f}%" if pd.notnull(roce) else "<b>ROCE</b><br/>N/A", bullet_style),
            Paragraph(f"<b>NPM</b><br/>{npm:.1f}%" if pd.notnull(npm) else "<b>NPM</b><br/>N/A", bullet_style),
        ],
        [
            Paragraph(f"<b>D/E</b><br/>{de:.2f}" if pd.notnull(de) else "<b>D/E</b><br/>N/A", bullet_style),
            Paragraph(f"<b>Rev CAGR 5y</b><br/>{rev_cagr:.1f}%" if pd.notnull(rev_cagr) else "<b>Rev CAGR 5y</b><br/>N/A", bullet_style),
            Paragraph(f"<b>FCF (Cr)</b><br/>₹{fcf:,.0f}" if pd.notnull(fcf) else "<b>FCF (Cr)</b><br/>N/A", bullet_style),
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[180, 180, 180])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BCCCDC")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # Render Charts 1 & 2 for Page 1
    chart1_img = _create_pl_chart(pl_df)
    chart2_img = _create_return_ratios_chart(ratios_df)

    story.append(Paragraph("<b>10-Year Revenue & Net Profit Trend (₹ Cr)</b>", section_heading))
    story.append(Image(chart1_img, width=540, height=180))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>10-Year ROE & ROCE (%) Trend</b>", section_heading))
    story.append(Image(chart2_img, width=540, height=180))

    # Page Break to Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2
    # =========================================================================

    story.append(Paragraph(f"<b>{comp_info['company_name']} — Balance Sheet & Cash Flow Intelligence</b>", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F497D"), spaceAfter=8))

    chart3_img = _create_bs_chart(bs_df)
    chart4_img = _create_cf_waterfall_chart(cf_df)

    story.append(Paragraph("<b>Balance Sheet Structure (Equity vs Debt vs Liabilities)</b>", section_heading))
    story.append(Image(chart3_img, width=540, height=160))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Latest Year Cash Flow Breakdown (CFO / CFI / CFF)</b>", section_heading))
    story.append(Image(chart4_img, width=540, height=140))
    story.append(Spacer(1, 8))

    # Capital Allocation Badge
    cap_pattern = latest_r.get("capital_allocation_pattern", "Reinvestor") if latest_r is not None else "Reinvestor"
    story.append(
        Paragraph(
            f"<b>Capital Allocation Archetype:</b> <font color='#1F497D'><b>{cap_pattern}</b></font>",
            section_heading,
        )
    )
    story.append(Spacer(1, 4))

    # Pros & Cons Section
    pros_cons_data = []

    pro_text_formatted = "<br/>".join([f"• <font color='#155724'>{p}</font>" for p in pros_list[:3]]) if pros_list else "• Stable operational profile"
    con_text_formatted = "<br/>".join([f"• <font color='#721C24'>{c}</font>" for c in cons_list[:3]]) if cons_list else "• Subject to broader market risks"

    pros_p = Paragraph(f"<b>✅ Investment Pros / Strengths</b><br/>{pro_text_formatted}", bullet_style)
    cons_p = Paragraph(f"<b>❌ Risk Factors & Weaknesses</b><br/>{con_text_formatted}", bullet_style)

    pc_table = Table([[pros_p, cons_p]], colWidths=[265, 265])
    pc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#D4EDDA")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8D7DA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ]
        )
    )
    story.append(pc_table)

    # Build PDF document
    doc.build(story)
    return output_pdf_path


# Helper chart generation functions (returns BytesIO image buffer)

def _create_pl_chart(pl_df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7.5, 2.5), dpi=150)
    if not pl_df.empty and "sales" in pl_df.columns:
        years = pl_df["year"].astype(str)
        ax.bar(years, pl_df["sales"], width=0.4, label="Revenue (Sales)", color="#1F497D", align="center")
        ax.bar(years, pl_df["net_profit"], width=0.4, label="Net Profit", color="#2E7D32", align="edge")
        ax.legend(loc="upper left", fontsize=7)
        ax.set_ylabel("Amount (₹ Cr)", fontsize=8)
        ax.tick_params(axis="both", labelsize=7)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
    else:
        ax.text(0.5, 0.5, "No P&L Trend Data Available", ha="center", va="center")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _create_return_ratios_chart(ratios_df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7.5, 2.5), dpi=150)
    if not ratios_df.empty:
        years = ratios_df["year"].astype(str)
        if "return_on_equity_pct" in ratios_df.columns:
            ax.plot(years, ratios_df["return_on_equity_pct"], marker="o", color="#E65100", label="ROE (%)", linewidth=2)
        if "return_on_capital_employed_pct" in ratios_df.columns:
            ax.plot(years, ratios_df["return_on_capital_employed_pct"], marker="s", color="#0288D1", label="ROCE (%)", linewidth=2)
        ax.legend(loc="upper left", fontsize=7)
        ax.set_ylabel("Percentage (%)", fontsize=8)
        ax.tick_params(axis="both", labelsize=7)
        ax.grid(True, linestyle="--", alpha=0.5)
    else:
        ax.text(0.5, 0.5, "No Return Ratio Data Available", ha="center", va="center")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _create_bs_chart(bs_df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7.5, 2.2), dpi=150)
    if not bs_df.empty and "equity_capital" in bs_df.columns:
        years = bs_df["year"].astype(str)
        eq = bs_df["equity_capital"] + bs_df["reserves"]
        borrowings = bs_df["borrowings"]
        other_liab = bs_df["other_liabilities"]

        ax.bar(years, eq, label="Equity & Reserves", color="#2E7D32")
        ax.bar(years, borrowings, bottom=eq, label="Borrowings", color="#C62828")
        ax.bar(years, other_liab, bottom=eq + borrowings, label="Other Liabilities", color="#757575")
        ax.legend(loc="upper left", fontsize=7)
        ax.set_ylabel("Amount (₹ Cr)", fontsize=8)
        ax.tick_params(axis="both", labelsize=7)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
    else:
        ax.text(0.5, 0.5, "No Balance Sheet Data Available", ha="center", va="center")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _create_cf_waterfall_chart(cf_df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7.5, 1.9), dpi=150)
    if not cf_df.empty:
        latest = cf_df.iloc[-1]
        cfo = latest.get("operating_activity", 0) or 0
        cfi = latest.get("investing_activity", 0) or 0
        cff = latest.get("financing_activity", 0) or 0
        net_cf = latest.get("net_cash_flow", 0) or 0

        cats = ["CFO", "CFI", "CFF", "Net Cash Flow"]
        vals = [cfo, cfi, cff, net_cf]
        colors_list = ["#2E7D32" if v >= 0 else "#C62828" for v in vals]

        ax.bar(cats, vals, color=colors_list, width=0.5)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel("Amount (₹ Cr)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
    else:
        ax.text(0.5, 0.5, "No Cash Flow Data Available", ha="center", va="center")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


if __name__ == "__main__":
    # Test on 5 companies
    test_tickers = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]
    for t in test_tickers:
        pdf_path = generate_company_tearsheet(t)
        print(f"✅ Generated tearsheet: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.1f} KB)")
