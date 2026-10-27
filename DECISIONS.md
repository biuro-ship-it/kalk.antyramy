# KALK_ANTYRAMY – decyzje

<!-- Nowe wpisy dodawaj NA GÓRZE. Wpisy #001–#006 odtworzone 2026-10-27 z historii gita (daty przybliżone). -->

## #007 – 2026-10-27 – Pliki schematu projektu
- **Status:** obowiązuje
- **Decyzja:** Aplikacja dostaje `CLAUDE.md`, `SPEC.md`, `DECISIONS.md`, `HANDOVER.md` wg `C:\Claude\szablony`.
- **Dlaczego:** Wspólny schemat dla wszystkich aplikacji, przygotowanie do migracji (model 3 kopii).
- **Konsekwencje:** Migracja do `apps\FIRMOWE\KALK_ANTYRAMY`, origin na D: i `deploy.ps1` – jeszcze do zrobienia.

## #006 – 2026 (lato) – Synchronizacja cen z WooCommerce
- **Status:** obowiązuje
- **Decyzja:** Kalkulator wysyła ceny do b2b.antyramy.eu przez REST API; profil może mieć wiele produktów WC (`wc_links`); obsługa produktów variable i simple.
- **Dlaczego:** Jedno źródło cen, bez ręcznego przepisywania do sklepu.
- **Konsekwencje:** Mapowania formatów i materiałów (`WC_FORMAT_MAP`, `WC_MATERIAL_MAP`) trzeba utrzymywać razem z `calc.py`.

## #005 – 2026 (lato) – Wirtualne profile antyram per wypełnienie
- **Status:** obowiązuje
- **Decyzja:** Antyramy mają ukryte profile (`active=0`) `ANTYRAMA_GLASS`, `_PLEXA`, `_GLASS_AR`, `_PLEXA_AR`.
- **Dlaczego:** Klucz obcy `format_margins.profile_id` wymaga realnego id; osobny profil = niezależne marże per format dla każdego wypełnienia.
- **Konsekwencje:** Nowe wypełnienie = nowy wirtualny profil w `database.py` i `antyrama_code` w `FRONT_TYPES`.

## #004 – 2026 (lato) – Marże per element i per format
- **Status:** obowiązuje
- **Decyzja:** Każdy materiał (wypełnienie, plecy, PP, klipsy, zestaw alu) ma własną marżę; listwa – marżę z profilu; admin może nadpisać marżę i robociznę dla formatu (wtedy jeden narzut na całość). Marża liczona od ceny sprzedaży, ograniczona do 99%. Robocizna bez marży.
- **Dlaczego:** Różna opłacalność materiałów; potrzeba ręcznej korekty pojedynczych formatów.

## #003 – 2026-06 – Passenger z a2wsgi zamiast natywnego ASGI
- **Status:** obowiązuje
- **Decyzja:** `passenger_wsgi.py` opakowuje FastAPI przez `a2wsgi`; `init_db()` wywoływane przy imporcie.
- **Dlaczego:** Passenger na mydevil to WSGI; lifespan/startup ASGI się nie odpala.
- **Odrzucone opcje:** WsgiToAsgi wrapper, natywne ASGI – nie działały stabilnie.

## #002 – 2026-06 – Deploy przez GitHub Actions (rsync na s61)
- **Status:** obowiązuje do migracji (zostanie zastąpiona przez `deploy.ps1` wg modelu 3 kopii)
- **Decyzja:** Push na `main` w GitHubie wdraża przez rsync; `data/` i `static/images/` wyłączone z nadpisywania.
- **Dlaczego:** Automatyczne wdrożenie bez utraty bazy i zdjęć na serwerze.

## #001 – 2026-06 – Stack v2: FastAPI + SQLite + panel admina
- **Status:** obowiązuje
- **Decyzja:** FastAPI + Jinja2 + SQLite na mydevil s61, hasło admina w bazie.
- **Dlaczego:** Prosty, tani hosting jak reszta aplikacji; cennik edytowalny w panelu.
- **Odrzucone opcje:** Vercel + Google Sheets (v1) – zależność od arkusza, brak panelu.
