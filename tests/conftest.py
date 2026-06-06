"""
Konfiguracja testów — izolacja bazy danych.

Każde uruchomienie testów używa własnej, tymczasowej bazy SQLite.
Ścieżkę podmieniamy PRZED importem api.index, który tworzy schemat
przy imporcie modułu (init_db()).
"""
import tempfile
from pathlib import Path

import api.database as database

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="kalk_test_"))
database.DB_PATH = _TEST_DB_DIR / "test.db"
