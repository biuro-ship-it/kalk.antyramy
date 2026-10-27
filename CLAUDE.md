# KALK_ANTYRAMY – instrukcja dla Claude

**Rodzaj:** FIRMOWA (Antyramy) · **Folder:** `C:\Claude\apps\KALK_ANTYRAMY` (docelowo `apps\FIRMOWE\KALK_ANTYRAMY` – migracja jeszcze nie zrobiona)
**Produkcja:** https://kalk.antyramy.eu (s61.mydevil.net, konto `Pluszek`)

## Co to jest
Kalkulator cen hurtowych ramek, antyram i ram aluminiowych dla wszystkich formatów (10x15 … 70x100) z panelem admina
i synchronizacją cen do WooCommerce (b2b.antyramy.eu). Szczegóły: `SPEC.md`.

## ⚠️ Niezmiennik (nigdy nie wolno tego zepsuć)
Cena wyliczona w kalkulatorze = cena wysłana do WooCommerce. Wzór liczenia (`api/calc.py`) jest jedynym źródłem prawdy
dla strony i dla `wc_sync.py`; zmiana wzoru, marż lub kluczy formatów musi działać w obu miejscach naraz.
Baza `data/cennik.db` (produkcyjny cennik) nie trafia do repo ani nie jest nadpisywana deployem.

## Przed rozpoczęciem pracy
1. Przeczytaj `HANDOVER.md` – aktualny stan i otwarte zadania.
2. Przy większych zmianach sprawdź `DECISIONS.md`, żeby nie łamać wcześniejszych ustaleń.
3. Sprawdź `C:\Claude\INBOX.md` (sekcja „Otwarte”, `DO: KALK_ANTYRAMY`).
4. Po skończonej sesji zaktualizuj `HANDOVER.md`; nową decyzję dopisz do `DECISIONS.md`.

## Stack
- Backend: Python / FastAPI + Jinja2 (szablony HTML), bez osobnego frontendu
- Baza: SQLite `data/cennik.db` (tworzona przez `init_db()`, migracje w `api/database.py`)
- Auth: jedno hasło admina (hash w tabeli `settings`, ciasteczko `kalk_admin`)
- Integracja: WooCommerce REST API (b2b.antyramy.eu) przez `httpx`
- Hosting: mydevil.net s61, Passenger + `a2wsgi` (`passenger_wsgi.py`), venv `~/.virtualenvs/kalk`
- Dystrybucja: WWW + PWA (`static/sw.js`, `/manifest.json`)

## Struktura folderów
```
api/index.py       – trasy FastAPI (strona, /calculate, API admina, backup, upload zdjęć)
api/calc.py        – wzór ceny, FORMATS_CONFIG, FRONT_TYPES (wypełnienia)
api/database.py    – schemat SQLite + domyślne ustawienia + migracje
api/wc_sync.py     – synchronizacja cen do WooCommerce (produkty variable i simple)
api/archive.py     – backup ZIP (dump SQL, CSV, zdjęcia)
api/auth.py        – hasło admina i ciasteczko sesji
templates/         – index.html (kalkulator), admin/login.html, admin/panel.html
static/            – sw.js; static/images/ = zdjęcia wgrane z panelu (nie w repo, nie nadpisywane deployem)
data/              – cennik.db (poza repo)
temp/              – testy pytest (poza repo)
manage.py          – CLI na serwerze: init, set-password
secret/            – hasła i notatki lokalne, NIGDY nie commitować
```

## Komendy
```bash
# lokalnie
pip install -r requirements.txt -r requirements-dev.txt
uvicorn api.index:app --reload
# testy (leżą w temp/)
pytest temp
# na serwerze (SSH)
source ~/.virtualenvs/kalk/bin/activate && cd ~/domains/kalk.antyramy.eu/public_python
python manage.py set-password NOWE_HASLO
```

## Zasady kodu
- Język interfejsu, komentarzy i commitów: polski.
- Wygląd: jasny/ciemny motyw (zmienne CSS), akcent #2563eb, mobile-first.
- Nowy format: dopisz w `FORMATS_CONFIG` (calc.py) i – jeśli jest w sklepie – w `WC_FORMAT_MAP` (wc_sync.py).
- Nowe wypełnienie: dopisz w `FRONT_TYPES`, domyślne ceny/marże i wirtualny profil antyramy w `database.py`, mapowanie w `WC_MATERIAL_MAP`.
- Sekrety (hasła, klucze WooCommerce) tylko w `.env` / `secret/` – nigdy w kodzie ani w repo.
- Małe, opisowe commity. Nie usuwaj działających funkcji bez pytania.

## Deploy
Obecnie: push na `origin` (GitHub `biuro-ship-it/kalk.antyramy`) uruchamia GitHub Actions (`.github/workflows/deploy.yml`):
rsync na s61 z pominięciem `data/` i `static/images/`, `pip install`, restart Passengera.
Docelowo (migracja): model 3 kopii (origin na D:, remote `github`) i ręczny `deploy.ps1` – push nie będzie wdrażał.
