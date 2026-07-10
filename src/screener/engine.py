"""
src/screener/engine.py
======================
Sprint 3 — Days 15, 16, 17
ScreenerEngine: load data, apply threshold filters, 6 preset screeners,
composite quality score (0–100, P10/P90 winsorised).

Run with:
    python -m src.screener.engine
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "screener_config.yaml"

# ── Column mapping: filter key → financial_ratios column ─────────────────────
FILTER_COL_MAP: Dict[str, str] = {
    "roe_min":               "return_on_equity_pct",
    "opm_min":               "operating_profit_margin_pct",
    "net_profit_min":        "net_profit",
    "debt_to_equity_max":    "debt_to_equity",
    "interest_coverage_min": "interest_coverage",
    "fcf_min":               "free_cash_flow_cr",
    "revenue_cagr_5yr_min":  "revenue_cagr_5yr",
    "pat_cagr_5yr_min":      "pat_cagr_5yr",
    "eps_cagr_min":          "eps_cagr_5yr",
    "revenue_cagr_3yr_min":  "revenue_cagr_3yr",
    "pe_max":                "pe_ratio",
    "pb_max":                "pb_ratio",
    "dividend_yield_min":    "dividend_yield_pct",
    "market_cap_min":        "market_cap_crore",
    "sales_min":             "sales",
    "asset_turnover_min":    "asset_turnover",
}

# Metrics where filter applies "max" (fail if value EXCEEDS threshold)
MAX_FILTERS = {"debt_to_equity_max", "pe_max", "pb_max"}


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_latest_ratios(db_path: Path) -> pd.DataFrame:
    """
    Load the latest-year financial_ratios row per company, joined with
    companies (name), sectors (broad_sector), and profitandloss (sales,
    net_profit, dividend_payout).
    """
    sql = """
    SELECT
        fr.company_id,
        c.company_name,
        s.broad_sector,
        fr.year,
        fr.return_on_equity_pct,
        fr.return_on_capital_employed_pct,
        fr.net_profit_margin_pct,
        fr.operating_profit_margin_pct,
        fr.return_on_assets_pct,
        fr.debt_to_equity,
        fr.interest_coverage,
        fr.icr_label,
        fr.free_cash_flow_cr,
        fr.fcf_conversion_rate,
        fr.cfo_quality_score,
        fr.revenue_cagr_3yr,
        fr.revenue_cagr_5yr,
        fr.pat_cagr_3yr,
        fr.pat_cagr_5yr,
        fr.eps_cagr_5yr,
        fr.asset_turnover,
        fr.composite_quality_score        AS raw_composite_score,
        fr.market_cap_crore,
        fr.pe_ratio,
        fr.pb_ratio,
        fr.dividend_yield_pct,
        fr.high_leverage_flag,
        pl.sales,
        pl.net_profit,
        pl.dividend_payout
    FROM financial_ratios fr
    JOIN companies c  ON fr.company_id = c.id
    LEFT JOIN sectors s ON fr.company_id = s.company_id
    LEFT JOIN profitandloss pl
           ON fr.company_id = pl.company_id AND fr.year = pl.year
    WHERE fr.year = (
        SELECT MAX(year) FROM financial_ratios fr2
        WHERE fr2.company_id = fr.company_id
          AND fr2.return_on_equity_pct IS NOT NULL
    )
    ORDER BY fr.company_id
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(sql, conn)
    logger.info("Loaded %d companies (latest year each)", len(df))
    return df


def _load_prior_year_de(db_path: Path) -> Dict[str, Optional[float]]:
    """Return {company_id: debt_to_equity for year-1} for Turnaround preset."""
    sql = """
    SELECT fr.company_id, fr.debt_to_equity, fr.year
    FROM financial_ratios fr
    WHERE fr.year = (
        SELECT MAX(year) - 1 FROM financial_ratios fr2
        WHERE fr2.company_id = fr.company_id
          AND fr2.return_on_equity_pct IS NOT NULL
    )
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(sql).fetchall()
    return {r[0]: r[1] for r in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Composite quality score — P10/P90 winsorised, 0–100
# ─────────────────────────────────────────────────────────────────────────────

def _winsorise_scale(series: pd.Series) -> pd.Series:
    """Winsorise at P10/P90 then scale to 0–100."""
    p10, p90 = series.quantile(0.10), series.quantile(0.90)
    if p90 == p10:
        return pd.Series(50.0, index=series.index)
    clipped = series.clip(lower=p10, upper=p90)
    return (clipped - p10) / (p90 - p10) * 100.0


def _compute_composite_score(df: pd.DataFrame) -> pd.Series:
    """
    Composite quality score (0–100):
      35% Profitability  : ROE×15 + ROCE×10 + NPM×10
      30% Cash Quality   : FCF CAGR×15 + CFO/PAT×10 + FCF positive flag×5
      20% Growth         : Revenue CAGR 5yr×10 + PAT CAGR 5yr×10
      15% Leverage       : D/E score×10 + ICR score×5

    Each metric is individually winsorised (P10/P90) and scaled 0–100
    before weighting.
    """
    def ws(col: str) -> pd.Series:
        s = pd.to_numeric(df[col], errors="coerce").fillna(df[col].median()
                         if pd.to_numeric(df[col], errors="coerce").notna().any()
                         else 0)
        return _winsorise_scale(s)

    # Profitability (35%)
    roe_s  = ws("return_on_equity_pct")          * 0.15
    roce_s = ws("return_on_capital_employed_pct") * 0.10
    npm_s  = ws("net_profit_margin_pct")          * 0.10

    # Cash Quality (30%)
    # FCF CAGR proxy: use pat_cagr_5yr as surrogate when fcf_cagr not stored
    fcf_cagr_s = ws("pat_cagr_5yr")              * 0.15
    # CFO/PAT: cfo_quality_score is categorical → map to numeric
    cfo_map = {"High Quality": 100, "Moderate": 50, "Accrual Risk": 10,
               "Insufficient Data": 0}
    cfo_num = df["cfo_quality_score"].map(cfo_map).fillna(0)
    cfo_s   = _winsorise_scale(cfo_num)           * 0.10
    # FCF positive flag (5%)
    fcf_flag = (pd.to_numeric(df["free_cash_flow_cr"], errors="coerce") > 0
                ).astype(float) * 100
    fcf_flag_s = fcf_flag                         * 0.05

    # Growth (20%)
    rev_s  = ws("revenue_cagr_5yr")               * 0.10
    pat_s  = ws("pat_cagr_5yr")                   * 0.10

    # Leverage (15%) — D/E inverted so lower D/E = higher score
    de_raw = pd.to_numeric(df["debt_to_equity"], errors="coerce").fillna(0)
    de_inv = _winsorise_scale(-de_raw)             * 0.10   # invert
    icr_raw = pd.to_numeric(df["interest_coverage"], errors="coerce").fillna(0)
    # "Debt Free" icr_label → treat ICR as 999
    debt_free_mask = df["icr_label"] == "Debt Free"
    icr_raw = icr_raw.where(~debt_free_mask, 999.0)
    icr_s   = _winsorise_scale(icr_raw)            * 0.05

    score = roe_s + roce_s + npm_s + fcf_cagr_s + cfo_s + fcf_flag_s \
            + rev_s + pat_s + de_inv + icr_s

    return score.round(2)


def _compute_sector_relative_score(df: pd.DataFrame) -> pd.Series:
    """Normalise composite_quality_score within each broad_sector (0–100)."""
    result = pd.Series(index=df.index, dtype=float)
    for sector, group in df.groupby("broad_sector"):
        scores = group["composite_quality_score"]
        p10, p90 = scores.quantile(0.10), scores.quantile(0.90)
        if p90 == p10:
            result.loc[group.index] = 50.0
        else:
            result.loc[group.index] = (
                (scores.clip(p10, p90) - p10) / (p90 - p10) * 100
            ).round(2)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ScreenerEngine
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerEngine:
    """
    Load financial_ratios data and apply configurable threshold filters.

    Usage
    -----
    engine = ScreenerEngine()
    engine.load_data()
    result_df = engine.run_preset("Quality Compounder")
    """

    PRESET_NAMES = [
        "Quality Compounder",
        "Value Pick",
        "Growth Accelerator",
        "Dividend Champion",
        "Debt-Free Blue Chip",
        "Turnaround Watch",
    ]

    def __init__(
        self,
        db_path: Path = config.DB_PATH,
        config_path: Path = CONFIG_PATH,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self._cfg: dict = {}
        self._df: Optional[pd.DataFrame] = None
        self._prior_de: Dict[str, Optional[float]] = {}
        self._load_config()

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        with open(self.config_path, encoding="utf-8") as fh:
            self._cfg = yaml.safe_load(fh)
        logger.info("Screener config loaded from %s", self.config_path)

    @property
    def _financials_label(self) -> str:
        return self._cfg.get("financials_sector_label", "Financials")

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_data(self) -> pd.DataFrame:
        """Load + enrich latest-year financial_ratios for all 92 companies."""
        df = _load_latest_ratios(self.db_path)
        self._prior_de = _load_prior_year_de(self.db_path)

        # Composite quality score
        df["composite_quality_score"] = _compute_composite_score(df)
        df["sector_relative_score"]   = _compute_sector_relative_score(df)

        self._df = df
        return df

    @property
    def data(self) -> pd.DataFrame:
        if self._df is None:
            self.load_data()
        return self._df

    # ── Generic filter application ────────────────────────────────────────────

    def apply_filters(self, filters: Dict) -> pd.DataFrame:
        """
        Apply a dict of {filter_key: threshold_value} to self.data.

        Rules
        -----
        * Null/None threshold → filter is skipped.
        * debt_to_equity_max → Financials sector rows pass unconditionally.
        * interest_coverage_min → icr_label == "Debt Free" always passes.
        * _max filters → fail if value > threshold.
        * _min filters → fail if value < threshold.
        * Rows where the metric column is NULL → excluded (conservative).
        """
        df = self.data.copy()

        for key, threshold in filters.items():
            if threshold is None:
                continue

            col = FILTER_COL_MAP.get(key)
            if col is None or col not in df.columns:
                logger.warning("Unknown filter key or missing column: %s", key)
                continue

            is_max = key in MAX_FILTERS
            fin_label = self._financials_label

            if key == "debt_to_equity_max":
                # Financials sector: pass unconditionally
                fin_mask  = df["broad_sector"] == fin_label
                non_fin   = df[~fin_mask]
                de_col    = pd.to_numeric(non_fin[col], errors="coerce")
                pass_mask = de_col <= threshold
                keep_ids  = set(non_fin.loc[pass_mask].index) | set(df[fin_mask].index)
                df = df.loc[sorted(keep_ids)]

            elif key == "interest_coverage_min":
                # "Debt Free" always passes
                debt_free = df["icr_label"] == "Debt Free"
                icr_val   = pd.to_numeric(df[col], errors="coerce")
                pass_mask = debt_free | (icr_val >= threshold)
                df = df[pass_mask]

            else:
                numeric_col = pd.to_numeric(df[col], errors="coerce")
                if is_max:
                    df = df[numeric_col.notna() & (numeric_col <= threshold)]
                else:
                    df = df[numeric_col.notna() & (numeric_col >= threshold)]

        sort_col = self._cfg.get("sort_by", "composite_quality_score")
        asc      = bool(self._cfg.get("sort_ascending", False))
        if sort_col in df.columns:
            df = df.sort_values(sort_col, ascending=asc)

        return df.reset_index(drop=True)

    # ── 6 Preset screeners ───────────────────────────────────────────────────

    def preset_quality_compounder(self) -> pd.DataFrame:
        """ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5yr > 10%."""
        return self.apply_filters({
            "roe_min":              15.0,
            "debt_to_equity_max":   1.0,
            "fcf_min":              0.0,
            "revenue_cagr_5yr_min": 10.0,
        })

    def preset_value_pick(self) -> pd.DataFrame:
        """P/E < 35, P/B < 5.0, D/E < 2.0, Dividend Yield > 0.3%."""
        return self.apply_filters({
            "pe_max":              35.0,
            "pb_max":               5.0,
            "debt_to_equity_max":   2.0,
            "dividend_yield_min":   0.3,
        })

    def preset_growth_accelerator(self) -> pd.DataFrame:
        """PAT CAGR 5yr > 15%, Revenue CAGR 5yr > 12%, D/E < 2.0."""
        return self.apply_filters({
            "pat_cagr_5yr_min":     15.0,
            "revenue_cagr_5yr_min": 12.0,
            "debt_to_equity_max":    2.0,
        })

    def preset_dividend_champion(self) -> pd.DataFrame:
        """Dividend Yield > 1.5%, Dividend Payout < 80%, FCF > 0."""
        df = self.apply_filters({
            "dividend_yield_min": 1.5,
            "fcf_min":            0.0,
        })
        # Dividend payout filter (column is in P&L join)
        if "dividend_payout" in df.columns:
            div_pay = pd.to_numeric(df["dividend_payout"], errors="coerce")
            df = df[div_pay.isna() | (div_pay <= 80.0)]
        return df.reset_index(drop=True)

    def preset_debt_free_blue_chip(self) -> pd.DataFrame:
        """D/E <= 0.1 (near debt-free), ROE > 12%, Sales > 500 Cr."""
        df = self.data.copy()
        de = pd.to_numeric(df["debt_to_equity"], errors="coerce").fillna(0)
        df = df[de <= 0.1]
        roe = pd.to_numeric(df["return_on_equity_pct"], errors="coerce")
        df = df[roe >= 12.0]
        sales = pd.to_numeric(df["sales"], errors="coerce")
        df = df[sales >= 500.0]
        sort_col = self._cfg.get("sort_by", "composite_quality_score")
        if sort_col in df.columns:
            df = df.sort_values(sort_col, ascending=False)
        return df.reset_index(drop=True)

    def preset_turnaround_watch(self) -> pd.DataFrame:
        """Revenue CAGR 3yr > 8%, FCF positive, D/E declining YoY."""
        df = self.apply_filters({
            "revenue_cagr_3yr_min": 8.0,
            "fcf_min":              0.0,
        })
        # D/E declining: latest D/E < prior year D/E
        if self._prior_de:
            def _de_declining(row: pd.Series) -> bool:
                prior = self._prior_de.get(row["company_id"])
                if prior is None:
                    return False
                curr = pd.to_numeric(row["debt_to_equity"], errors="coerce")
                if pd.isna(curr):
                    return False
                return float(curr) < float(prior)

            mask = df.apply(_de_declining, axis=1)
            df = df[mask]
        return df.reset_index(drop=True)

    def run_preset(self, name: str) -> pd.DataFrame:
        """Dispatch to the named preset. Raises ValueError for unknown names."""
        dispatch = {
            "Quality Compounder":  self.preset_quality_compounder,
            "Value Pick":          self.preset_value_pick,
            "Growth Accelerator":  self.preset_growth_accelerator,
            "Dividend Champion":   self.preset_dividend_champion,
            "Debt-Free Blue Chip": self.preset_debt_free_blue_chip,
            "Turnaround Watch":    self.preset_turnaround_watch,
        }
        if name not in dispatch:
            raise ValueError(f"Unknown preset: '{name}'. Valid: {list(dispatch)}")
        result = dispatch[name]()
        n = len(result)
        logger.info("Preset '%s' → %d companies", name, n)
        if n < 5:
            logger.warning("Preset '%s' returned only %d companies (< 5)", name, n)
        return result

    def run_all_presets(self) -> Dict[str, pd.DataFrame]:
        """Run all 6 presets and return {preset_name: DataFrame}."""
        return {name: self.run_preset(name) for name in self.PRESET_NAMES}


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    engine = ScreenerEngine()
    engine.load_data()

    print(f"\n{'='*65}")
    print("  NIFTY 100 SCREENER — All 6 Presets")
    print(f"{'='*65}")

    for preset_name in ScreenerEngine.PRESET_NAMES:
        result = engine.run_preset(preset_name)
        print(f"\n  [{preset_name}] — {len(result)} companies")
        print(f"  {'Ticker':<14} {'Company':<28} {'ROE%':>7} {'D/E':>6} {'Score':>7}")
        print(f"  {'-'*62}")
        for _, row in result.head(10).iterrows():
            roe = row.get("return_on_equity_pct")
            de  = row.get("debt_to_equity")
            sc  = row.get("composite_quality_score")
            print(
                f"  {str(row['company_id']):<14} "
                f"{str(row['company_name'])[:28]:<28} "
                f"{(f'{roe:.1f}' if roe is not None else '—'):>7} "
                f"{(f'{de:.2f}' if de is not None else '—'):>6} "
                f"{(f'{sc:.1f}' if sc is not None else '—'):>7}"
            )
