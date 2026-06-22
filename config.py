"""
config.py
---------
Central configuration for the Nifty 100 pipeline.
All values are loaded from .env via python-dotenv.
Paths are resolved to absolute Path objects relative to this file's directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = directory containing this file
BASE_DIR: Path = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

# ── Core paths ────────────────────────────────────────────────────────────────
DB_PATH: Path          = BASE_DIR / os.getenv("DB_PATH",           "db/nifty100.db")
DATA_RAW_DIR: Path     = BASE_DIR / os.getenv("DATA_RAW_DIR",      "data/raw")
DATA_PROCESSED_DIR: Path = BASE_DIR / os.getenv("DATA_PROCESSED_DIR", "data/processed")
OUTPUT_DIR: Path       = BASE_DIR / os.getenv("OUTPUT_DIR",        "output")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: Path  = BASE_DIR / os.getenv("LOG_FILE", "output/pipeline.log")

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_ENV: str   = os.getenv("FLASK_ENV",   "development")
FLASK_PORT: int  = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG: bool = bool(int(os.getenv("FLASK_DEBUG", "1")))

# ── Data-quality thresholds ───────────────────────────────────────────────────
DQ_BS_BALANCE_TOLERANCE: float = float(os.getenv("DQ_BS_BALANCE_TOLERANCE", "0.01"))
DQ_OPM_MIN: float              = float(os.getenv("DQ_OPM_MIN",              "-1.0"))
DQ_OPM_MAX: float              = float(os.getenv("DQ_OPM_MAX",               "1.0"))
DQ_DIVIDEND_CAP: float         = float(os.getenv("DQ_DIVIDEND_CAP",          "1.0"))
DQ_MIN_YEAR_COVERAGE: int      = int(os.getenv("DQ_MIN_YEAR_COVERAGE",       "3"))
