import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.validator import (
    check_dq01,
    check_dq02,
    check_dq03,
    check_dq04,
    check_dq05,
    check_dq06,
    check_dq07,
    check_dq08,
    check_dq09,
    check_dq10,
    check_dq11,
    check_dq12,
    check_dq13,
    check_dq14,
    run_all_checks,
)

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


def test_dq01_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq01(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq02_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq02(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq03_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq03(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq04_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq04(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq05_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq05(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq06_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq06(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq07_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq07(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq08_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq08(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq09_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq09(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq10_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq10(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq11_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq11(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq12_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq12(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq13_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq13(conn)
    conn.close()
    assert isinstance(res, list)


def test_dq14_rule():
    conn = sqlite3.connect(str(DB_PATH))
    res = check_dq14(conn)
    conn.close()
    assert isinstance(res, list)


def test_run_all_dq_checks():
    conn = sqlite3.connect(str(DB_PATH))
    res = run_all_checks(conn)
    conn.close()
    assert isinstance(res, list)
