import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[3] / "db" / "nifty100.db"


def get_connection():
    """Get a SQLite database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=600)
def get_companies():
    """Fetch all companies with sector information."""
    conn = get_connection()
    query = """
        SELECT c.*, s.broad_sector, s.sub_sector
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        ORDER BY c.company_name ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_ratios(ticker=None, year=None):
    """Fetch financial ratios data joined with company metadata."""
    conn = get_connection()
    query = """
        SELECT fr.*, c.company_name, s.broad_sector, s.sub_sector
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE 1=1
    """
    params = []
    if ticker:
        query += " AND fr.company_id = ?"
        params.append(ticker)
    if year:
        query += " AND fr.year = ?"
        params.append(year)

    query += " ORDER BY fr.company_id, fr.year ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_pl(ticker):
    """Fetch Profit and Loss statement data for a ticker."""
    conn = get_connection()
    query = "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql_query(query, conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_bs(ticker):
    """Fetch Balance Sheet data for a ticker."""
    conn = get_connection()
    query = "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql_query(query, conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_cf(ticker):
    """Fetch Cash Flow statement data for a ticker."""
    conn = get_connection()
    query = "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql_query(query, conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_sectors():
    """Fetch sector breakdown and counts."""
    conn = get_connection()
    query = """
        SELECT s.broad_sector, s.sub_sector, COUNT(c.id) as company_count
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        GROUP BY s.broad_sector, s.sub_sector
        ORDER BY broad_sector, company_count DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_peers(group_name=None):
    """Fetch peer groups, members, and percentiles."""
    conn = get_connection()
    if group_name:
        query = """
            SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark,
                   c.company_name, s.broad_sector,
                   pp.metric, pp.value, pp.percentile_rank, pp.year
            FROM peer_groups pg
            JOIN companies c ON pg.company_id = c.id
            LEFT JOIN sectors s ON c.id = s.company_id
            LEFT JOIN peer_percentiles pp ON pg.company_id = pp.company_id AND pg.peer_group_name = pp.peer_group_name
            WHERE pg.peer_group_name = ?
            ORDER BY pg.company_id, pp.metric
        """
        df = pd.read_sql_query(query, conn, params=[group_name])
    else:
        query = """
            SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name, s.broad_sector
            FROM peer_groups pg
            JOIN companies c ON pg.company_id = c.id
            LEFT JOIN sectors s ON c.id = s.company_id
            ORDER BY pg.peer_group_name, c.company_name
        """
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_valuation(ticker=None):
    """Fetch valuation data including market cap, multiples, and FCF yield."""
    conn = get_connection()
    query = """
        SELECT fr.company_id, c.company_name, s.broad_sector as sector, fr.year,
               fr.market_cap_crore, fr.pe_ratio, fr.pb_ratio, fr.ev_ebitda,
               fr.dividend_yield_pct, fr.free_cash_flow_cr, fr.return_on_equity_pct
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE fr.year = (SELECT MAX(year) FROM financial_ratios)
    """
    params = []
    if ticker:
        query += " AND fr.company_id = ?"
        params.append(ticker)
    query += " ORDER BY fr.market_cap_crore DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Compute FCF yield
    if not df.empty:
        df["fcf_yield_pct"] = (df["free_cash_flow_cr"] / df["market_cap_crore"]) * 100
    return df


@st.cache_data(ttl=600)
def get_pros_cons(ticker):
    """Fetch pros and cons for a company."""
    conn = get_connection()
    query = "SELECT pros, cons FROM prosandcons WHERE company_id = ?"
    df = pd.read_sql_query(query, conn, params=[ticker])
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_documents(ticker):
    """Fetch annual reports / documents for a company."""
    conn = get_connection()
    query = "SELECT year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC"
    df = pd.read_sql_query(query, conn, params=[ticker])
    conn.close()
    return df
