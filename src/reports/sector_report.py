import sqlite3
from pathlib import Path
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
SECTOR_REPORTS_DIR = PROJECT_ROOT / "reports" / "sector"


def generate_sector_report(sector_name: str, output_pdf_path: Path = None) -> Path:
    """Generates a sector analytics report PDF for a broad sector."""
    SECTOR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sector_name.replace(" ", "_").replace("&", "and")
    if output_pdf_path is None:
        output_pdf_path = SECTOR_REPORTS_DIR / f"{safe_name}_report.pdf"

    conn = sqlite3.connect(str(DB_PATH))

    # Fetch sector companies and latest ratios
    query = """
        SELECT fr.company_id, c.company_name, s.broad_sector, s.sub_sector,
               fr.return_on_equity_pct, fr.return_on_capital_employed_pct,
               fr.net_profit_margin_pct, fr.debt_to_equity, fr.free_cash_flow_cr,
               fr.revenue_cagr_5yr, fr.pat_cagr_5yr, fr.composite_quality_score
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE s.broad_sector = ? AND fr.year = (SELECT MAX(year) FROM financial_ratios)
        ORDER BY fr.composite_quality_score DESC
    """
    sector_df = pd.read_sql_query(query, conn, params=[sector_name])
    conn.close()

    if sector_df.empty:
        raise ValueError(f"No company data found for sector '{sector_name}'.")

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
        fontSize=8,
        leading=10,
    )

    story = []

    # Header Banner
    header_p1 = Paragraph(
        f"<b>{sector_name} — Sector Intelligence Report</b>", title_style
    )
    header_p2 = Paragraph(
        f"Nifty 100 Benchmark | Total Companies: {len(sector_df)}", subtitle_style
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
    story.append(Spacer(1, 10))

    # Sector Median Summary Table
    story.append(Paragraph("<b>📊 Sector Median Key Metrics</b>", section_heading))

    med_roe = sector_df["return_on_equity_pct"].median()
    med_roce = sector_df["return_on_capital_employed_pct"].median()
    med_npm = sector_df["net_profit_margin_pct"].median()
    med_de = sector_df["debt_to_equity"].median()
    med_rev_cagr = sector_df["revenue_cagr_5yr"].median()
    med_pat_cagr = sector_df["pat_cagr_5yr"].median()

    summary_data = [
        [
            Paragraph(
                (
                    f"<b>Median ROE</b><br/>{med_roe:.1f}%"
                    if pd.notnull(med_roe)
                    else "N/A"
                ),
                cell_style,
            ),
            Paragraph(
                (
                    f"<b>Median ROCE</b><br/>{med_roce:.1f}%"
                    if pd.notnull(med_roce)
                    else "N/A"
                ),
                cell_style,
            ),
            Paragraph(
                (
                    f"<b>Median NPM</b><br/>{med_npm:.1f}%"
                    if pd.notnull(med_npm)
                    else "N/A"
                ),
                cell_style,
            ),
        ],
        [
            Paragraph(
                f"<b>Median D/E</b><br/>{med_de:.2f}" if pd.notnull(med_de) else "N/A",
                cell_style,
            ),
            Paragraph(
                (
                    f"<b>Rev CAGR 5y</b><br/>{med_rev_cagr:.1f}%"
                    if pd.notnull(med_rev_cagr)
                    else "N/A"
                ),
                cell_style,
            ),
            Paragraph(
                (
                    f"<b>PAT CAGR 5y</b><br/>{med_pat_cagr:.1f}%"
                    if pd.notnull(med_pat_cagr)
                    else "N/A"
                ),
                cell_style,
            ),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[180, 180, 180])
    summary_table.setStyle(
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
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Sector Company Comparison Matrix Table
    story.append(
        Paragraph("<b>📋 Sector Company Comparison Matrix</b>", section_heading)
    )

    table_data = [
        [
            Paragraph("<b>Ticker</b>", cell_style),
            Paragraph("<b>Company</b>", cell_style),
            Paragraph("<b>ROE%</b>", cell_style),
            Paragraph("<b>ROCE%</b>", cell_style),
            Paragraph("<b>NPM%</b>", cell_style),
            Paragraph("<b>D/E</b>", cell_style),
            Paragraph("<b>FCF Cr</b>", cell_style),
            Paragraph("<b>Rev 5y%</b>", cell_style),
            Paragraph("<b>Score</b>", cell_style),
        ]
    ]

    for _, row in sector_df.iterrows():
        table_data.append(
            [
                Paragraph(str(row["company_id"]), cell_style),
                Paragraph(str(row["company_name"])[:20], cell_style),
                Paragraph(
                    (
                        f"{row['return_on_equity_pct']:.1f}"
                        if pd.notnull(row["return_on_equity_pct"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['return_on_capital_employed_pct']:.1f}"
                        if pd.notnull(row["return_on_capital_employed_pct"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['net_profit_margin_pct']:.1f}"
                        if pd.notnull(row["net_profit_margin_pct"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['debt_to_equity']:.2f}"
                        if pd.notnull(row["debt_to_equity"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['free_cash_flow_cr']:,.0f}"
                        if pd.notnull(row["free_cash_flow_cr"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['revenue_cagr_5yr']:.1f}"
                        if pd.notnull(row["revenue_cagr_5yr"])
                        else "N/A"
                    ),
                    cell_style,
                ),
                Paragraph(
                    (
                        f"{row['composite_quality_score']:.1f}"
                        if pd.notnull(row["composite_quality_score"])
                        else "N/A"
                    ),
                    cell_style,
                ),
            ]
        )

    matrix_table = Table(
        table_data,
        colWidths=[45, 115, 45, 45, 45, 40, 55, 50, 45],
        repeatRows=1,
    )
    matrix_table.setStyle(
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
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(matrix_table)

    doc.build(story)
    return output_pdf_path


def generate_all_sector_reports():
    """Generates sector reports for all 11 broad sectors."""
    conn = sqlite3.connect(str(DB_PATH))
    sectors = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT broad_sector FROM sectors WHERE broad_sector IS NOT NULL ORDER BY broad_sector"
        ).fetchall()
    ]
    conn.close()

    generated_paths = []
    for s in sectors:
        path = generate_sector_report(s)
        generated_paths.append(path)
        print(f"✅ Generated Sector Report: {path.name}")
    return generated_paths


if __name__ == "__main__":
    generate_all_sector_reports()
