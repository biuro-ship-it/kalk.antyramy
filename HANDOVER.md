# KALK_ANTYRAMY – handover

**Ostatnia aktualizacja:** 2026-10-27
**Wersja produkcyjna:** v2 – https://kalk.antyramy.eu (s61, wdrażana przez GitHub Actions po pushu na `main`)

## Stan obecny
### ✅ Działa
- Kalkulator 17 formatów, 5 wypełnień, 4 kategorie, passe-partout.
- Antyramy wg nowej formuły: pole·(wypełnienie + tył) + spinki + zaczepy, 4 marże per wypełnienie (`margin_ant_*`, panel → „Marże antyram (%)”) – wdrożone 2026-10-27.
- Wydruk wyceny: 1 strona A4, jasne kolory także w ciemnym motywie, nagłówek wydruku; nazwa pliku PDF wg wyceny (`antyrama_szklo`, `drewno_a123` …).
- Panel admina: ustawienia, profile, marże per format (bez antyram), backup ZIP, zmiana hasła, upload zdjęć.
- Synchronizacja cen do WooCommerce (b2b.antyramy.eu), produkty variable i simple – liczona tą samą funkcją co strona.
- PWA.

### 🔧 W trakcie
- Produkcja po nowej formule antyram: marże antyram stoją na domyślnych 50%, dopóki Krzysiek nie wpisze własnych; sklep ma jeszcze stare ceny antyram (synchronizacja niewykonana).
- Migracja wg `C:\Claude\STAN-MIGRACJI.md` – zrobione tylko pliki schematu.

### 🐛 Znane problemy
- Przykład kontrolny ze zlecenia (50x60 szkło: 12.32 / 24.64 / 30.31) nie zgadza się z formułą – z formuły wychodzi 12.92 / 25.84 / 31.78 (różnica 0,60 zł = 5 spinek). Do potwierdzenia przez Krzyśka, czy liczba spinek dla 50x60 jest dobra.
- Pole „Marża spinki/zaczepy” w panelu nic już nie zmienia (działało tylko na antyramy).
- `api/auth.py` ma stałą sól hasła w kodzie (`SALT`) – do rozważenia przeniesienie do `.env`.
- Testy w `temp/` są poza repo (`temp/` w `.gitignore`) – istnieją tylko na tym komputerze.
- Brak `README.md`, `.env.example`, `deploy.ps1`, `wypchnij.ps1` ze schematu.

## Następne kroki (kolejność = priorytet)
1. Panel → „Marże antyram (%)”: wpisać 4 marże; sprawdzić ceny zakupu; sprawdzić wycenę antyram na stronie.
2. Ręcznie „Synchronizuj” profile antyram (4 wypełnienia) do WooCommerce.
3. Potwierdzić przykład kontrolny 50x60 (liczba spinek) – ewentualnie poprawić `FORMATS_CONFIG`.
4. Sprawdzić na produkcji wydruk i nazwę PDF z prawdziwą listwą (drewno/alu) – lokalna baza nie ma aktywnych profili.
5. Decyzja: usunąć czy zostawić pole „Marża spinki/zaczepy”; przenieść testy z `temp/` do repo (np. `tests/`, już wykluczone z deployu)?
6. Migracja: FIRMOWA → `apps\FIRMOWE\KALK_ANTYRAMY`, origin `D:\Repozytoria\git\kalk_antyramy.git`, obecny GitHub jako remote `github`; `deploy.ps1` zamiast GitHub Actions; `README.md`, `.env.example`.

## Ważne do zapamiętania
- Push na GitHub = natychmiastowy deploy (GitHub Actions, ok. 40–80 s). Deploy NIE nadpisuje `data/` ani `public/static/images/` na serwerze.
- Passenger: restart przez `touch tmp/restart.txt passenger_wsgi.py`.
- Klucze formatów: `21x29.7` i `29.7x42` (kropka); WooCommerce używa przecinka (`21x29,7`) – mapowanie w `wc_sync.py`.
- Kopia lokalnej bazy sprzed nowej formuły: `data/backup-przed-nowa-formula.db` (poza repo).
- Konta: mydevil s61 użytkownik `Pluszek`, domena kalk.antyramy.eu; GitHub `biuro-ship-it/kalk.antyramy`. Hasła w `secret/` – bez haseł tutaj.

## Historia sesji
- **2026-10-27** – Pliki schematu; naprawa wydruku (puste strony w ciemnym motywie, nagłówek); `data/` w `.gitignore`; nowa formuła antyram z 4 marżami per wypełnienie (wdrożona); nazwa pliku PDF wg wyceny.
- **2026-07-30** – Porządki: `secret/` w `.gitignore`, testy przeniesione do `temp/`.
- **2026 (lato)** – Wypełnienia antyrefleks (szkło, plexi), format A3 29.7x42, sync WC dla produktów simple.
- **2026 (lato)** – Synchronizacja cen z WooCommerce b2b.antyramy.eu.
- **2026-06** – v2: FastAPI + SQLite + panel admina, deploy na s61.
