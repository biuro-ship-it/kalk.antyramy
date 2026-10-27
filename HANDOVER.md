# KALK_ANTYRAMY – handover

**Ostatnia aktualizacja:** 2026-10-27
**Wersja produkcyjna:** v2 – https://kalk.antyramy.eu (s61, wdrażana przez GitHub Actions)

## Stan obecny
### ✅ Działa
- Kalkulator 17 formatów, 5 wypełnień, 4 kategorie, passe-partout.
- Panel admina: ustawienia, profile, marże per format, backup ZIP, zmiana hasła, upload zdjęć.
- Synchronizacja cen do WooCommerce (b2b.antyramy.eu), produkty variable i simple.
- PWA.

### 🔧 W trakcie
- Migracja wg `C:\Claude\STAN-MIGRACJI.md` – zrobione tylko pliki schematu (2026-10-27).

### 🐛 Znane problemy
- `api/auth.py` ma stałą sól hasła w kodzie (`SALT`) – do rozważenia przeniesienie do `.env`.
- Brak `README.md`, `.env.example`, `deploy.ps1`, `wypchnij.ps1` ze schematu.

## Następne kroki (kolejność = priorytet)
1. Po wdrożeniu sprawdzić wydruk wyceny na produkcji z prawdziwą listwą (drewno/alu) – lokalna baza nie ma aktywnych profili.
2. Migracja: potwierdzić FIRMOWA → `apps\FIRMOWE\KALK_ANTYRAMY`, origin `D:\Repozytoria\git\kalk_antyramy.git`, obecny GitHub jako remote `github`.
3. `deploy.ps1` z `D:\Repozytoria\szablon-startowy` (te same wykluczenia co w `deploy.yml`) i decyzja o wyłączeniu GitHub Actions.
4. Uzupełnić `README.md` i `.env.example`.

## Ważne do zapamiętania
- Deploy NIE może nadpisać `data/` ani `public/static/images/` na serwerze – tam jest produkcyjny cennik i zdjęcia.
- Passenger: restart przez `touch tmp/restart.txt passenger_wsgi.py`.
- Klucze formatów: `21x29.7` i `29.7x42` (kropka); WooCommerce używa przecinka (`21x29,7`) – mapowanie w `wc_sync.py`.
- Konta: mydevil s61 użytkownik `Pluszek`, domena kalk.antyramy.eu; GitHub `biuro-ship-it/kalk.antyramy`. Hasła w `secret/` – bez haseł tutaj.

## Historia sesji
- **2026-10-27** – Założono pliki schematu (CLAUDE.md, SPEC.md, DECISIONS.md, HANDOVER.md); naprawiono wydruk wyceny (puste strony w ciemnym motywie, nagłówek wydruku); `data/` w `.gitignore`.
- **2026-07-30** – Porządki: `secret/` w `.gitignore`, testy przeniesione do `temp/`.
- **2026 (lato)** – Wypełnienia antyrefleks (szkło, plexi), format A3 29.7x42, sync WC dla produktów simple.
- **2026 (lato)** – Synchronizacja cen z WooCommerce b2b.antyramy.eu.
- **2026-06** – v2: FastAPI + SQLite + panel admina, deploy na s61.
