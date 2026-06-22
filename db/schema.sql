-- =============================================================================
-- db/schema.sql
-- Nifty 100 Financial Data Pipeline — SQLite Schema
-- =============================================================================

PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. sectors  (lookup — no FK dependencies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sectors (
    sector_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name     TEXT    NOT NULL UNIQUE,
    sector_code     TEXT,
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 2. companies  (root entity; FK → sectors)
-- =============================================================================
CREATE TABLE IF NOT EXISTS companies (
    company_id      TEXT    PRIMARY KEY,
    name            TEXT    NOT NULL,
    ticker          TEXT    NOT NULL UNIQUE,
    bse_code        TEXT    UNIQUE,
    nse_symbol      TEXT,
    isin            TEXT,
    sector_id       INTEGER REFERENCES sectors(sector_id) ON DELETE CASCADE,
    industry        TEXT,
    market_cap      REAL,
    face_value      REAL,
    listing_date    TEXT,
    website         TEXT,
    ceo             TEXT,
    employees       INTEGER,
    hq_city         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 3. profitandloss  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS profitandloss (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    revenue                 REAL,
    operating_profit        REAL,
    depreciation            REAL,
    ebit                    REAL,
    interest                REAL,
    profit_before_tax       REAL,
    tax                     REAL,
    net_profit              REAL,
    eps                     REAL,
    dividend                REAL,
    dividend_payout_ratio   REAL,
    opm_percent             REAL,
    npm_percent             REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 4. balancesheet  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS balancesheet (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    share_capital           REAL,
    reserves                REAL,
    equity                  REAL,
    borrowings              REAL,
    other_liabilities       REAL,
    total_liabilities       REAL,
    fixed_assets            REAL,
    cwip                    REAL,
    investments             REAL,
    other_assets            REAL,
    total_assets            REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 5. cashflow  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS cashflow (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    operating_cash_flow     REAL,
    investing_cash_flow     REAL,
    financing_cash_flow     REAL,
    net_cash                REAL,
    capex                   REAL,
    free_cash_flow          REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 6. financial_ratios  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    pe_ratio                REAL,
    pb_ratio                REAL,
    ev_ebitda               REAL,
    roe                     REAL,
    roce                    REAL,
    roa                     REAL,
    debt_to_equity          REAL,
    current_ratio           REAL,
    quick_ratio             REAL,
    interest_coverage       REAL,
    asset_turnover          REAL,
    inventory_turnover      REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 7. analysis  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS analysis (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    analyst_rating          TEXT,
    target_price            REAL,
    upside_potential        REAL,
    revenue_growth_yoy      REAL,
    profit_growth_yoy       REAL,
    sales_growth_3yr        REAL,
    profit_growth_3yr       REAL,
    roce_3yr_avg            REAL,
    score                   REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 8. stock_prices  (FK → companies; grain: company × year)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stock_prices (
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER NOT NULL,
    open_price              REAL,
    high_price              REAL,
    low_price               REAL,
    close_price             REAL,
    adj_close               REAL,
    volume                  REAL,
    week_52_high            REAL,
    week_52_low             REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, year)
);

-- =============================================================================
-- 9. documents  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    document_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER,
    doc_type                TEXT,
    title                   TEXT,
    report_url              TEXT,
    bse_url                 TEXT,
    nse_url                 TEXT,
    filing_date             TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 10. prosandcons  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS prosandcons (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    year                    INTEGER,
    type                    TEXT    CHECK(type IN ('pro','con')),
    description             TEXT,
    source                  TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 11. peer_groups  (FK → companies)
-- =============================================================================
CREATE TABLE IF NOT EXISTS peer_groups (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id              TEXT    NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    peer_company_id         TEXT    REFERENCES companies(company_id) ON DELETE CASCADE,
    peer_ticker             TEXT,
    sector_id               INTEGER REFERENCES sectors(sector_id) ON DELETE CASCADE,
    pe_ratio                REAL,
    pb_ratio                REAL,
    market_cap              REAL,
    revenue                 REAL,
    net_profit              REAL,
    roe                     REAL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- companies
CREATE INDEX IF NOT EXISTS idx_companies_ticker    ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_companies_sector_id ON companies(sector_id);
CREATE INDEX IF NOT EXISTS idx_companies_bse_code  ON companies(bse_code);

-- financial tables — year lookups
CREATE INDEX IF NOT EXISTS idx_pl_year    ON profitandloss(year);
CREATE INDEX IF NOT EXISTS idx_bs_year    ON balancesheet(year);
CREATE INDEX IF NOT EXISTS idx_cf_year    ON cashflow(year);
CREATE INDEX IF NOT EXISTS idx_fr_year    ON financial_ratios(year);
CREATE INDEX IF NOT EXISTS idx_sp_year    ON stock_prices(year);

-- documents
CREATE INDEX IF NOT EXISTS idx_documents_company_id ON documents(company_id);
CREATE INDEX IF NOT EXISTS idx_documents_year       ON documents(year);

-- peer_groups
CREATE INDEX IF NOT EXISTS idx_peers_company_id     ON peer_groups(company_id);
CREATE INDEX IF NOT EXISTS idx_peers_sector_id      ON peer_groups(sector_id);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- v_company_summary: one row per company with latest-year financials
CREATE VIEW IF NOT EXISTS v_company_summary AS
SELECT
    c.company_id,
    c.name,
    c.ticker,
    c.bse_code,
    s.sector_name,
    c.market_cap,
    pl.year          AS latest_year,
    pl.revenue,
    pl.net_profit,
    pl.eps,
    pl.opm_percent,
    pl.npm_percent,
    bs.total_assets,
    bs.equity,
    bs.total_liabilities,
    fr.roe,
    fr.roce,
    fr.pe_ratio,
    fr.debt_to_equity
FROM companies c
LEFT JOIN sectors s         ON c.sector_id = s.sector_id
LEFT JOIN profitandloss pl  ON c.company_id = pl.company_id
    AND pl.year = (
        SELECT MAX(year) FROM profitandloss WHERE company_id = c.company_id
    )
LEFT JOIN balancesheet bs   ON c.company_id = bs.company_id AND bs.year = pl.year
LEFT JOIN financial_ratios fr ON c.company_id = fr.company_id AND fr.year = pl.year;


-- v_financial_overview: all years of P&L + BS + CF per company
CREATE VIEW IF NOT EXISTS v_financial_overview AS
SELECT
    c.company_id,
    c.name,
    c.ticker,
    s.sector_name,
    pl.year,
    pl.revenue,
    pl.operating_profit,
    pl.net_profit,
    pl.eps,
    pl.opm_percent,
    bs.total_assets,
    bs.equity,
    bs.borrowings,
    bs.total_liabilities,
    cf.operating_cash_flow,
    cf.free_cash_flow,
    fr.roe,
    fr.roce,
    fr.pe_ratio,
    fr.debt_to_equity
FROM companies c
LEFT JOIN sectors s              ON c.sector_id = s.sector_id
LEFT JOIN profitandloss pl       ON c.company_id = pl.company_id
LEFT JOIN balancesheet bs        ON c.company_id = bs.company_id AND bs.year = pl.year
LEFT JOIN cashflow cf            ON c.company_id = cf.company_id AND cf.year = pl.year
LEFT JOIN financial_ratios fr    ON c.company_id = fr.company_id AND fr.year = pl.year;


-- v_peer_comparison: company vs peers with sector context
CREATE VIEW IF NOT EXISTS v_peer_comparison AS
SELECT
    pg.company_id,
    c.name          AS company_name,
    c.ticker        AS company_ticker,
    s.sector_name,
    pg.peer_company_id,
    p.name          AS peer_name,
    p.ticker        AS peer_ticker,
    pg.pe_ratio     AS peer_pe,
    pg.pb_ratio     AS peer_pb,
    pg.market_cap   AS peer_market_cap,
    pg.revenue      AS peer_revenue,
    pg.net_profit   AS peer_net_profit,
    pg.roe          AS peer_roe
FROM peer_groups pg
LEFT JOIN companies c   ON pg.company_id      = c.company_id
LEFT JOIN companies p   ON pg.peer_company_id = p.company_id
LEFT JOIN sectors s     ON pg.sector_id       = s.sector_id;
