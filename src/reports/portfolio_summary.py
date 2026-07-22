import sqlite3
from pathlib import Path
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
PORTFOLIO_DIR = PROJECT_ROOT / "reports" / "portfolio"


def generate_portfolio_summary_pdf(output_pdf_path: Path = None) -> Path:
    """Generates a 92-page Portfolio Summary PDF (one page per company with top KPIs

    and trend arrows).
    """
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    if output_pdf_path is None:
        output_pdf_path = PORTFOLIO_DIR / "portfolio_summary.pdf"

    conn = sqlite3.connect(str(DB_PATH))

    # Fetch all companies ordered alphabetically by ticker
    query = """
        SELECT fr.*, c.company_name, s.broad_sector, s.sub_sector
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        ORDER BY fr.company_id ASC, fr.year ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise ValueError("No financial ratio data found for portfolio summary.")

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

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
        spaceBefore=10,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    story = []
    unique_tickers = sorted(df["company_id"].unique())

    for idx, cid in enumerate(unique_tickers):
        c_df = df[df["company_id"] == cid]
        if c_df.empty:
            continue

        latest = c_df.iloc[-1]
        prev = c_df.iloc[-2] if len(c_df) >= 2 else None
        comp_name = latest["company_name"]
        sector = latest.get("broad_sector", "N/A")

        # Compute trend arrows
        def get_arrow(curr, previous):
            if pd.isnull(curr) or pd.isnull(previous) or previous == 0:
                return "→"
            diff_pct = ((curr - previous) / abs(previous)) * 100
            if diff_pct > 2.0:
                return "↑"
            elif diff_pct < -2.0:
                return "↓"
            else:
                return "→"

        roe_arr = get_arrow(
            latest.get("return_on_equity_pct"),
            prev.get("return_on_equity_pct") if prev is not None else None,
        )
        roce_arr = get_arrow(
            latest.get("return_on_capital_employed_pct"),
            prev.get("return_on_capital_employed_pct") if prev is not None else None,
        )
        npm_arr = get_arrow(
            latest.get("net_profit_margin_pct"),
            prev.get("net_profit_margin_pct") if prev is not None else None,
        )
        de_arr = get_arrow(
            prev.get("debt_to_equity") if prev is not None else None,
            latest.get("debt_to_equity"),
        )  # lower D/E is better
        rev_arr = get_arrow(
            latest.get("revenue_cagr_5yr"),
            prev.get("revenue_cagr_5yr") if prev is not None else None,
        )
        fcf_arr = get_arrow(
            latest.get("free_cash_flow_cr"),
            prev.get("free_cash_flow_cr") if prev is not None else None,
        )

        # Header Bar
        header_p1 = Paragraph(f"<b>{comp_name} ({cid})</b>", title_style)
        header_p2 = Paragraph(
            f"Sector: {sector} | Nifty 100 Portfolio Summary", subtitle_style
        )

        header_table = Table([[header_p1], [header_p2]], colWidths=[540])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1F497D")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 15))

        # Top 6 KPIs Table with Trend Arrows
        story.append(
            Paragraph(
                "<b>📊 Key Financial Ratios & Recent YoY Trend</b>", section_heading
            )
        )

        roe_val = latest.get("return_on_equity_pct")
        roce_val = latest.get("return_on_capital_employed_pct")
        npm_val = latest.get("net_profit_margin_pct")
        de_val = latest.get("debt_to_equity")
        rev_cagr_val = latest.get("revenue_cagr_5yr")
        fcf_val = latest.get("free_cash_flow_cr")

        kpi_data = [
            [
                Paragraph("<b>Metric</b>", cell_style),
                Paragraph("<b>Latest Value</b>", cell_style),
                Paragraph("<b>Trend (YoY)</b>", cell_style),
                Paragraph("<b>Status</b>", cell_style),
            ],
            [
                Paragraph("Return on Equity (ROE)", cell_style),
                Paragraph(
                    f"{roe_val:.1f}%" if pd.notnull(roe_val) else "N/A", cell_style
                ),
                Paragraph(f"<font size=14><b>{roe_arr}</b></font>", cell_style),
                Paragraph(
                    "High Efficiency" if roe_val and roe_val > 15 else "Moderate",
                    cell_style,
                ),
            ],
            [
                Paragraph("Return on Capital (ROCE)", cell_style),
                Paragraph(
                    f"{roce_val:.1f}%" if pd.notnull(roce_val) else "N/A",
                    cell_style,
                ),
                Paragraph(f"<font size=14><b>{roce_arr}</b></font>", cell_style),
                Paragraph(
                    (
                        "Strong Capital Returns"
                        if roce_val and roce_val > 15
                        else "Moderate"
                    ),
                    cell_style,
                ),
            ],
            [
                Paragraph("Net Profit Margin (NPM)", cell_style),
                Paragraph(
                    f"{npm_val:.1f}%" if pd.notnull(npm_val) else "N/A", cell_style
                ),
                Paragraph(f"<font size=14><b>{npm_arr}</b></font>", cell_style),
                Paragraph(
                    "High Margin" if npm_val and npm_val > 15 else "Standard Margin",
                    cell_style,
                ),
            ],
            [
                Paragraph("Debt to Equity (D/E)", cell_style),
                Paragraph(f"{de_val:.2f}" if pd.notnull(de_val) else "N/A", cell_style),
                Paragraph(f"<font size=14><b>{de_arr}</b></font>", cell_style),
                Paragraph(
                    "Conservative Leverage" if de_val and de_val < 1.0 else "Elevated",
                    cell_style,
                ),
            ],
            [
                Paragraph("Revenue CAGR (5yr)", cell_style),
                Paragraph(
                    f"{rev_cagr_val:.1f}%" if pd.notnull(rev_cagr_val) else "N/A",
                    cell_style,
                ),
                Paragraph(f"<font size=14><b>{rev_arr}</b></font>", cell_style),
                Paragraph(
                    (
                        "Strong Growth"
                        if rev_cagr_val and rev_cagr_val > 10
                        else "Moderate Growth"
                    ),
                    cell_style,
                ),
            ],
            [
                Paragraph("Free Cash Flow (FCF)", cell_style),
                Paragraph(
                    f"₹{fcf_val:,.0f} Cr" if pd.notnull(fcf_val) else "N/A",
                    cell_style,
                ),
                Paragraph(f"<font size=14><b>{fcf_arr}</b></font>", cell_style),
                Paragraph(
                    (
                        "Positive Cash Generation"
                        if fcf_val and fcf_val > 0
                        else "Negative FCF"
                    ),
                    cell_style,
                ),
            ],
        ]

        kpi_table = Table(kpi_data, colWidths=[160, 120, 100, 160], repeatRows=1)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F497D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F9F9F9")],
                    ),
                    ("ALIGN", (1, 1), (2, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 15))

        # Composite Quality Summary
        score = latest.get("composite_quality_score")
        if pd.notnull(score):
            story.append(
                Paragraph(
                    f"<b>Composite Quality Score:</b> <font color='#1F497D'><b>{score:.2f} / 100</b></font>",
                    section_heading,
                )
            )

        if idx < len(unique_tickers) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(
        f"✅ Exported Portfolio Summary PDF to {output_pdf_path.name} ({output_pdf_path.stat().st_size / 1024:.1f} KB)"
    )
    return output_pdf_path


if __name__ == "__main__":
    generate_portfolio_summary_pdf()
