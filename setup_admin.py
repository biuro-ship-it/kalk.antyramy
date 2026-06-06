"""
Skrypt jednorazowy — uruchom raz na serwerze po pierwszym deployu:
  python setup_admin.py

Ustawia hasło admina i inicjalizuje bazę danych.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from api.database import init_db
from api.auth import set_password

print("Inicjalizacja bazy danych...")
init_db()
print("OK")

password = input("Podaj hasło admina: ").strip()
if not password:
    print("Błąd: hasło nie może być puste")
    sys.exit(1)

set_password(password)
print(f"Hasło admina ustawione.")
print("Możesz się teraz zalogować pod /admin/login")
