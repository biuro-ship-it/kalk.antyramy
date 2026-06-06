"""
Narzędzie administracyjne uruchamiane ręcznie przez SSH na mydevil.net.

Użycie (po aktywacji venv, w katalogu aplikacji):
    source ~/.virtualenvs/kalk/bin/activate
    cd ~/domains/kalk.antyramy.eu/public_python

    python manage.py init                  # utworzenie schematu bazy
    python manage.py set-password HASLO    # ustawienie / zmiana hasła admina
"""
import sys

from api.auth import set_password
from api.database import init_db


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    command = argv[1]

    if command == "init":
        init_db()
        print("OK: schemat bazy utworzony.")
        return 0

    if command == "set-password":
        if len(argv) < 3:
            print("Błąd: podaj hasło — python manage.py set-password HASLO")
            return 1
        init_db()
        set_password(argv[2])
        print("OK: hasło admina ustawione.")
        return 0

    print(f"Nieznana komenda: {command}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
