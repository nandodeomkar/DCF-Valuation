"""SQLite persistence for saved valuations. One table, JSON columns for the
full inputs/result snapshots so a saved run is perfectly reproducible.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models import DcfInputs, DcfResult, SavedValuation

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "valuations.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    price_at_run REAL,
    inputs_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def save_valuation(valuation: SavedValuation, db_path: Path | None = None) -> SavedValuation:
    created_at = datetime.now(timezone.utc)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO valuations (ticker, company_name, created_at, price_at_run, inputs_json, result_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                valuation.ticker.upper(),
                valuation.company_name,
                created_at.isoformat(),
                valuation.price_at_run,
                valuation.inputs.model_dump_json(),
                valuation.result.model_dump_json(),
            ),
        )
        valuation.id = cursor.lastrowid
    valuation.created_at = created_at
    return valuation


def list_valuations(db_path: Path | None = None) -> list[SavedValuation]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM valuations ORDER BY created_at DESC").fetchall()
    return [_row_to_valuation(row) for row in rows]


def get_valuation(valuation_id: int, db_path: Path | None = None) -> SavedValuation | None:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM valuations WHERE id = ?", (valuation_id,)).fetchone()
    return _row_to_valuation(row) if row else None


def delete_valuation(valuation_id: int, db_path: Path | None = None) -> bool:
    with _connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM valuations WHERE id = ?", (valuation_id,))
    return cursor.rowcount > 0


def _row_to_valuation(row: sqlite3.Row) -> SavedValuation:
    return SavedValuation(
        id=row["id"],
        ticker=row["ticker"],
        company_name=row["company_name"],
        created_at=datetime.fromisoformat(row["created_at"]),
        price_at_run=row["price_at_run"],
        inputs=DcfInputs.model_validate_json(row["inputs_json"]),
        result=DcfResult.model_validate_json(row["result_json"]),
    )
