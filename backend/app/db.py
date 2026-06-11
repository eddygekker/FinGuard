import os
import sqlite3
from contextlib import contextmanager

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "finguard.db")


def get_db_path() -> str:
    return os.getenv("DATABASE_PATH") or DEFAULT_DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()):
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple = ()):
    with get_connection() as conn:
        return conn.execute(query, params).fetchone()


def execute(query: str, params: tuple = ()):
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()
