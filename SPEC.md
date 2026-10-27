# KALK_ANTYRAMY – specyfikacja

## Cel
Szybka, spójna wycena hurtowa ramek i antyram we wszystkich formatach naraz, z jednym miejscem do zmiany cen zakupu
i marż, oraz przeniesienie wyliczonych cen do sklepu B2B (b2b.antyramy.eu) jednym kliknięciem.

## Użytkownicy
- **Handlowiec / klient hurtowy** – wybiera listwę i wypełnienie, widzi ceny netto/brutto dla wszystkich formatów.
- **Admin (Krzysiek)** – po zalogowaniu widzi koszty, zysk i marże, edytuje cennik, profile, marże per format i synchronizuje WooCommerce.

## Funkcje
### Działa (v2)
- [x] Wycena dla 17 formatów (10x15 … 70x100, w tym 21x29.7 i 29.7x42 = A4/A3) – tabela wyników po wyborze profilu.
- [x] Kategorie: drewno, plastik, alu (z zestawem alu), antyrama (klipsy + wieszaki zamiast listwy).
- [x] Wypełnienia: szkło, szkło antyrefleks, pleksa, plexi antyrefleks, sama rama; opcjonalne passe-partout.
- [x] Wzór (drewno/plastik/alu): listwa = 2·(szer+wys) + 8 cm odpadu na narożniki; materiały × marża per element; robocizna wg wielkości (bez marży); VAT.
- [x] Wzór antyram: koszt = pole·(wypełnienie + tył) + spinki + zaczepy (ilości wg formatu); netto = koszt / (1 − marża wypełnienia); bez PP i robocizny.
      4 marże antyram w ustawieniach: szkło, szkło AR, pleksa, plexi AR (domyślnie 50%).
- [x] Marże per format (wyjątki marży i robocizny) zapisywane z widoku wyceny przez admina – nie dotyczy antyram.
- [x] Panel admina: ustawienia globalne (ceny zakupu, marże, robocizna, VAT), profile listew (dodaj/edytuj/usuń, zdjęcie, link do sklepu), zmiana hasła.
- [x] Synchronizacja cen do WooCommerce: powiązanie profilu z wieloma produktami (variable – warianty format×materiał, simple – jedna cena).
- [x] Backup ZIP z panelu (dump SQL, CSV profili/ustawień/marż, zdjęcia, notatka) + historia backupów.
- [x] Upload zdjęć profili (jpg/png/webp/gif, max 1 MB).
- [x] Wydruk wyceny: 1 strona A4, zawsze jasne kolory, nagłówek (profil, wypełnienie/PP, VAT, data), bez marż i pracy.
- [x] PWA (manifest, service worker), jasny/ciemny motyw.

### Później
- [ ] [do ustalenia z Krzyśkiem]

### Poza zakresem (świadomie NIE robimy)
- Zamówienia i koszyk – to robi sklep WooCommerce.
- Ceny detaliczne – tryb `mode` istnieje w kodzie, ale używany jest tylko `wholesale`.

## Ekrany
| Ekran | Co zawiera | Akcje użytkownika |
|---|---|---|
| Kalkulator `/` | Wybór kategorii, profilu, wypełnienia, PP; tabela cen dla formatów | Oblicz; admin: edycja marży/robocizny per format, sync WC |
| Logowanie `/admin/login` | Pole hasła | Zaloguj |
| Panel `/admin` | Backup, ustawienia globalne (ceny, marże per element, marże antyram, robocizna, WooCommerce), profile listew, zmiana hasła | Zapis ustawień, CRUD profili, backup, wylogowanie |

## Przepływy
1. **Wycena:** kategoria → profil (lub antyrama) → wypełnienie (+PP) → Oblicz → tabela netto/brutto.
2. **Zmiana cennika:** admin → panel → ustawienia globalne / profil → zapis → nowe ceny od razu w kalkulatorze.
3. **Aktualizacja sklepu:** admin → wycena profilu → powiązania WC (ID produktów) → Synchronizuj → ceny w b2b.antyramy.eu.

## Wygląd
- Styl: czyste karty, zaokrąglenia, motyw jasny i ciemny (przełącznik), mobile-first.
- Kolory: tło #f8fafc / #0f172a, akcent #2563eb / #3b82f6, tekst #0f172a / #f1f5f9.

## Dane
- SQLite `data/cennik.db`: `settings` (ceny zakupu, marże, VAT, hash hasła), `profiles` (listwy + 4 wirtualne profile antyram),
  `format_margins` (wyjątki marży/robocizny), `wc_links` (profil ↔ produkty WC), `price_history` (backupy).
- Dane handlowe firmy (ceny zakupu, marże) – widoczne tylko dla admina. Brak danych osobowych.

## Płatności
Brak – narzędzie wewnętrzne.

## Wymagania niefunkcjonalne
- Działa na telefonie i komputerze; PWA do instalacji.
- Hosting mydevil s61 (Passenger, WSGI przez a2wsgi – bez zdarzeń startup ASGI, więc `init_db()` w `passenger_wsgi.py`).
