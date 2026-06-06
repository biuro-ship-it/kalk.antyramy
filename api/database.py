"""
Warstwa bazy danych — SQLite przez wbudowany sqlite3.
Brak zewnętrznych ORM, zero dodatkowych zależności.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "cennik.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    """Tworzy schemat bazy przy pierwszym uruchomieniu."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL CHECK(category IN ('drewno','plastik','alu','antyrama')),
            width_mm    REAL NOT NULL DEFAULT 0,
            price_mb    REAL NOT NULL DEFAULT 0,
            margin_hurt REAL NOT NULL DEFAULT 40,
            img_url     TEXT DEFAULT '',
            description TEXT DEFAULT '',
            active      INTEGER NOT NULL DEFAULT 1,
            sort_order  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS format_margins (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            mode       TEXT NOT NULL DEFAULT 'wholesale',
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            format     TEXT NOT NULL,
            margin     REAL,
            labor      REAL,
            UNIQUE(mode, profile_id, format)
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            changed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            changed_by TEXT NOT NULL DEFAULT 'admin',
            note       TEXT DEFAULT '',
            snapshot   TEXT NOT NULL
        );

        INSERT OR IGNORE INTO settings VALUES ('vat', '23');
        INSERT OR IGNORE INTO settings VALUES ('glass_price_m2', '28.00');
        INSERT OR IGNORE INTO settings VALUES ('plexsa_price_m2', '55.00');
        INSERT OR IGNORE INTO settings VALUES ('back_price_m2', '12.00');
        INSERT OR IGNORE INTO settings VALUES ('pp_price_m2', '18.00');
        INSERT OR IGNORE INTO settings VALUES ('hook_price', '0.40');
        INSERT OR IGNORE INTO settings VALUES ('clip_price', '0.60');
        INSERT OR IGNORE INTO settings VALUES ('alu_kit_price', '3.50');
        INSERT OR IGNORE INTO settings VALUES ('labor_small', '2.50');
        INSERT OR IGNORE INTO settings VALUES ('labor_medium', '4.00');
        INSERT OR IGNORE INTO settings VALUES ('labor_large', '6.50');
        INSERT OR IGNORE INTO settings VALUES ('margin_glass', '30');
        INSERT OR IGNORE INTO settings VALUES ('margin_plexsa', '45');
        INSERT OR IGNORE INTO settings VALUES ('margin_back', '20');
        INSERT OR IGNORE INTO settings VALUES ('margin_pp', '30');
        INSERT OR IGNORE INTO settings VALUES ('margin_alu_kit', '20');
        INSERT OR IGNORE INTO settings VALUES ('margin_clips', '20');
        INSERT OR IGNORE INTO settings VALUES ('admin_password_hash', '');
        """)
