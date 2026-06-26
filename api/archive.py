"""
Backup cennika — tworzy ZIP z:
- dump SQL bazy (wystarczy do pełnego przywrócenia)
- CSV profili, ustawień, wyjątków marż (czytelny podgląd)
- wszystkie wgrane zdjęcia z static/images/
- README z datą i notatką
"""
import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path
from .database import get_conn

IMAGES_DIR = Path(__file__).parent.parent / "static" / "images"


def create_archive(note: str = "") -> bytes:
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M")
    folder = f"backup_{timestamp}"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        with get_conn() as conn:
            sql_dump = "\n".join(conn.iterdump())

        zf.writestr(f"{folder}/dump.sql",          sql_dump)
        zf.writestr(f"{folder}/profile.csv",       _profiles_csv())
        zf.writestr(f"{folder}/ustawienia.csv",    _settings_csv())
        zf.writestr(f"{folder}/wyjatki_marzy.csv", _margins_csv())

        # Zdjęcia wgrane przez panel admina
        images_added = 0
        if IMAGES_DIR.exists():
            for img in IMAGES_DIR.iterdir():
                if img.is_file():
                    zf.write(img, f"{folder}/images/{img.name}")
                    images_added += 1

        zf.writestr(f"{folder}/README.txt",
            f"Backup Antyramy.eu — kalkulator ramek\n"
            f"Data: {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"Notatka: {note or '—'}\n\n"
            f"Zawartość:\n"
            f"  dump.sql          — pełny dump bazy SQLite (do przywrócenia)\n"
            f"  profile.csv       — lista profili/listew\n"
            f"  ustawienia.csv    — ceny i marże globalne\n"
            f"  wyjatki_marzy.csv — marże per format\n"
            f"  images/           — wgrane zdjęcia ({images_added} plików)\n\n"
            f"Przywracanie: podaj ten plik Claude'owi — wgra dane na serwer.\n"
        )

        _save_history(note=note, timestamp=timestamp, sql_dump=sql_dump)

    buf.seek(0)
    return buf.read()


def _profiles_csv() -> str:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY category, sort_order, code").fetchall()
    out = io.StringIO()
    if rows:
        w = csv.DictWriter(out, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows([dict(r) for r in rows])
    return out.getvalue()


def _settings_csv() -> str:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    out = io.StringIO()
    csv.writer(out).writerows([["key", "value"]] + list(rows))
    return out.getvalue()


def _margins_csv() -> str:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT fm.mode, p.code, fm.format, fm.margin, fm.labor
            FROM format_margins fm
            JOIN profiles p ON p.id = fm.profile_id
            ORDER BY fm.mode, p.code, fm.format
        """).fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["mode", "profile_code", "format", "margin", "labor"])
    w.writerows(rows)
    return out.getvalue()


def _save_history(note: str, timestamp: str, sql_dump: str) -> None:
    with get_conn() as c:
        c.execute(
            "INSERT INTO price_history (note, snapshot) VALUES (?, ?)",
            (note or timestamp, sql_dump[:500] + "…"),
        )


def list_archives() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, changed_at, changed_by, note FROM price_history ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return [dict(r) for r in rows]
