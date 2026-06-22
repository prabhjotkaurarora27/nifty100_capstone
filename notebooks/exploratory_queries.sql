-- =============================================================================
-- notebooks/exploratory_queries.sql
-- Nifty 100 — Post-load exploration queries
-- Run against: db/nifty100.db
-- Usage: sqlite3 db/nifty100.db < notebooks/exploratory_queries.sql
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Query 1: Company count by sector
-- -----------------------------------------------------------------------------
SELECT
    s.sector_name,
    COUNT(c.company_id)  AS company_count
FROM companies c
JOIN sectors s ON c.sector_id = s.sector_id
GROUP BY s.sector_name
ORDER BY company_count DESC;

-- -----------------------------------------------------------------------------
-- Query 2: Top 10 companies by revenue (latest year)
-- -----------------------------------------------------------------------------
SELECT
    c.name,
    c.ticker,
    s.sector_name,
    pl.year,
    ROUND(pl.revenue, 2)     AS revenue_cr,
    ROUND(pl.net_profit, 2)  AS net_profit_cr,
    ROUND(pl.opm_percent, 2) AS opm_pct
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.company_id
JOIN sectors   s ON c.sector_id   = s.sector_id
WHERE pl.year = (
    SELECT MAX(year) FROM profitandloss WHERE company_id = pl.company_id
)
ORDER BY pl.revenue DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Query 3: Average OPM by sector (latest year per company)
-- -----------------------------------------------------------------------------
SELECT
    s.sector_name,
    COUNT(DISTINCT pl.company_id)    AS companies,
    ROUND(AVG(pl.opm_percent), 2)    AS avg_opm_pct,
    ROUND(MIN(pl.opm_percent), 2)    AS min_opm_pct,
    ROUND(MAX(pl.opm_percent), 2)    AS max_opm_pct
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.company_id
JOIN sectors   s ON c.sector_id   = s.sector_id
WHERE pl.year = (
    SELECT MAX(year) FROM profitandloss WHERE company_id = pl.company_id
)
GROUP BY s.sector_name
ORDER BY avg_opm_pct DESC;

-- -----------------------------------------------------------------------------
-- Query 4: Companies with incomplete year coverage (< 5 years of P&L)
-- -----------------------------------------------------------------------------
SELECT
    c.company_id,
    c.name,
    c.ticker,
    s.sector_name,
    COUNT(DISTINCT pl.year) AS years_of_data
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.company_id
LEFT JOIN sectors s ON c.sector_id = s.sector_id
GROUP BY pl.company_id
HAVING years_of_data < 5
ORDER BY years_of_data ASC;

-- -----------------------------------------------------------------------------
-- Query 5: YoY revenue growth for a sample company (RELIANCE)
-- -----------------------------------------------------------------------------
SELECT
    curr.year,
    ROUND(curr.revenue, 2)                          AS revenue_cr,
    ROUND(prev.revenue, 2)                          AS prev_revenue_cr,
    ROUND(
        (curr.revenue - prev.revenue) * 100.0
        / NULLIF(prev.revenue, 0), 2
    )                                               AS yoy_growth_pct
FROM profitandloss curr
JOIN profitandloss prev
  ON curr.company_id = prev.company_id
 AND curr.year       = prev.year + 1
JOIN companies c ON curr.company_id = c.company_id
WHERE c.ticker = 'RELIANCE'
ORDER BY curr.year;

-- -----------------------------------------------------------------------------
-- Query 6: Balance sheet health — debt-to-equity ratio (latest year)
-- -----------------------------------------------------------------------------
SELECT
    c.name,
    c.ticker,
    s.sector_name,
    bs.year,
    ROUND(bs.borrowings, 2)                         AS borrowings_cr,
    ROUND(bs.equity, 2)                             AS equity_cr,
    ROUND(bs.borrowings / NULLIF(bs.equity, 0), 2) AS debt_to_equity
FROM balancesheet bs
JOIN companies c ON bs.company_id = c.company_id
LEFT JOIN sectors s ON c.sector_id = s.sector_id
WHERE bs.year = (
    SELECT MAX(year) FROM balancesheet WHERE company_id = bs.company_id
)
ORDER BY debt_to_equity DESC
LIMIT 20;

-- -----------------------------------------------------------------------------
-- Query 7: Cash flow consistency — FCF-positive companies (latest year)
-- -----------------------------------------------------------------------------
SELECT
    c.name,
    c.ticker,
    s.sector_name,
    cf.year,
    ROUND(cf.operating_cash_flow, 2) AS operating_cf,
    ROUND(cf.capex, 2)               AS capex,
    ROUND(cf.free_cash_flow, 2)      AS free_cash_flow
FROM cashflow cf
JOIN companies c ON cf.company_id = c.company_id
LEFT JOIN sectors s ON c.sector_id = s.sector_id
WHERE cf.year = (
    SELECT MAX(year) FROM cashflow WHERE company_id = cf.company_id
)
  AND cf.free_cash_flow > 0
ORDER BY cf.free_cash_flow DESC
LIMIT 20;

-- -----------------------------------------------------------------------------
-- Query 8: Stock price range — 52-week high/low per company (latest year)
-- -----------------------------------------------------------------------------
SELECT
    c.name,
    c.ticker,
    sp.year,
    ROUND(sp.week_52_high, 2)  AS high_52w,
    ROUND(sp.week_52_low, 2)   AS low_52w,
    ROUND(sp.close_price, 2)   AS close,
    ROUND(
        (sp.close_price - sp.week_52_low) * 100.0
        / NULLIF(sp.week_52_high - sp.week_52_low, 0), 1
    )                          AS position_in_range_pct
FROM stock_prices sp
JOIN companies c ON sp.company_id = c.company_id
WHERE sp.year = (
    SELECT MAX(year) FROM stock_prices WHERE company_id = sp.company_id
)
ORDER BY position_in_range_pct DESC
LIMIT 20;

-- -----------------------------------------------------------------------------
-- Query 9: Peer group comparison — average P/E by sector
-- -----------------------------------------------------------------------------
SELECT
    s.sector_name,
    COUNT(DISTINCT pg.company_id)     AS companies_in_sector,
    ROUND(AVG(pg.pe_ratio), 2)        AS avg_peer_pe,
    ROUND(MIN(pg.pe_ratio), 2)        AS min_peer_pe,
    ROUND(MAX(pg.pe_ratio), 2)        AS max_peer_pe
FROM peer_groups pg
JOIN sectors s ON pg.sector_id = s.sector_id
WHERE pg.pe_ratio IS NOT NULL
  AND pg.pe_ratio > 0
GROUP BY s.sector_name
ORDER BY avg_peer_pe DESC;

-- -----------------------------------------------------------------------------
-- Query 10: Companies with potential DQ concerns (NULL financials in latest year)
-- -----------------------------------------------------------------------------
SELECT
    c.company_id,
    c.name,
    c.ticker,
    pl.year,
    CASE WHEN pl.revenue       IS NULL THEN 'revenue '       ELSE '' END ||
    CASE WHEN pl.net_profit    IS NULL THEN 'net_profit '    ELSE '' END ||
    CASE WHEN pl.eps           IS NULL THEN 'eps '           ELSE '' END ||
    CASE WHEN bs.total_assets  IS NULL THEN 'total_assets '  ELSE '' END ||
    CASE WHEN cf.operating_cash_flow IS NULL THEN 'operating_cf ' ELSE '' END
        AS null_fields
FROM profitandloss pl
JOIN companies c   ON pl.company_id = c.company_id
LEFT JOIN balancesheet bs ON bs.company_id = pl.company_id AND bs.year = pl.year
LEFT JOIN cashflow cf     ON cf.company_id = pl.company_id AND cf.year = pl.year
WHERE pl.year = (
    SELECT MAX(year) FROM profitandloss WHERE company_id = pl.company_id
)
  AND (
       pl.revenue       IS NULL
    OR pl.net_profit    IS NULL
    OR pl.eps           IS NULL
    OR bs.total_assets  IS NULL
    OR cf.operating_cash_flow IS NULL
  )
ORDER BY c.name;
