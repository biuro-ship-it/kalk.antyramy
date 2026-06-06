"""
Główna aplikacja FastAPI — kalk.antyramy.eu
Uruchamiana przez Phusion Passenger (passenger_wsgi.py) na mydevil.net
"""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db, get_conn
from .calc import calculate_all
from .auth import verify_password, verify_cookie, make_session_token, set_password
from .archive import create_archive, list_archives

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Schemat bazy tworzymy przy imporcie modułu, NIE w zdarzeniu startup.
# Passenger uruchamia aplikację przez a2wsgi (ASGI->WSGI), który nie obsługuje
# protokołu lifespan ASGI — zdarzenia @app.on_event("startup") nigdy się nie wykonują.
init_db()

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    print(f"[ERROR] {exc}")
    return HTMLResponse(
        "<div style='padding:20px;color:#b91c1c;font-family:sans-serif'>"
        "<h3>Błąd serwera.</h3><p>Spróbuj ponownie lub skontaktuj się z obsługą.</p>"
        "</div>",
        status_code=500,
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _settings() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def _profiles(category: Optional[str] = None) -> list:
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE active=1 AND category=? ORDER BY sort_order, code",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE active=1 ORDER BY category, sort_order, code"
            ).fetchall()
    return [dict(r) for r in rows]


def _margin_exceptions(profile_id: int) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mode, format, margin, labor FROM format_margins WHERE profile_id=?",
            (profile_id,)
        ).fetchall()
    return {f"{r['mode']}__{r['format']}": {"margin": r["margin"], "labor": r["labor"]} for r in rows}


def _is_admin(request: Request) -> bool:
    token = request.cookies.get("kalk_admin", "")
    return verify_cookie(token) if token else False


# ── strona główna ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "profiles": _profiles(),
        "is_admin": _is_admin(request),
    })


@app.post("/refresh")
async def refresh():
    return RedirectResponse("/", status_code=303)


# ── oblicz cenę ───────────────────────────────────────────────────────────────

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
    profile_id: Optional[str] = Form(None),
    category: str = Form("drewno"),
    front_type: str = Form("szklo"),
    with_pp: Optional[str] = Form(None),
    mode: str = Form("wholesale"),
):
    s = _settings()
    is_admin = _is_admin(request)

    if category == "antyrama":
        profile = {
            "id": 0, "code": "ANTYRAMA", "name": "Antyrama",
            "category": "antyrama", "width_mm": 0, "price_mb": 0,
            "margin_hurt": float(s.get("margin_antyrama", 35)),
            "img_url": "", "description": "",
        }
    else:
        pid = int(profile_id) if profile_id and str(profile_id).strip() else None
        if not pid:
            return RedirectResponse("/", status_code=303)
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE id=? AND active=1", (pid,)).fetchone()
        if not row:
            return RedirectResponse("/", status_code=303)
        profile = dict(row)

    exc = _margin_exceptions(profile["id"])
    results = calculate_all(
        profile=profile, settings=s, category=category,
        front_type=front_type, with_pp=bool(with_pp),
        margin_exceptions=exc, mode=mode,
    )

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": results,
        "profile": profile,
        "profiles": _profiles(),
        "category": category,
        "front_type": front_type,
        "with_pp": with_pp,
        "mode": mode,
        "is_admin": is_admin,
        "vat": s.get("vat", 23),
    })


# ── API admin — marże ─────────────────────────────────────────────────────────

@app.post("/api/save-margins")
async def save_margins(request: Request):
    if not _is_admin(request):
        return JSONResponse({"ok": False, "error": "Brak autoryzacji"}, status_code=403)
    data = await request.json()
    with get_conn() as conn:
        for u in data.get("updates", []):
            conn.execute("""
                INSERT INTO format_margins (mode, profile_id, format, margin, labor)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mode, profile_id, format) DO UPDATE SET
                    margin=excluded.margin, labor=excluded.labor
            """, (u["mode"], u["profile_id"], u["format"], u["margin"], u["labor"]))
        if data.get("profile_id"):
            conn.execute(
                "UPDATE profiles SET img_url=?, description=? WHERE id=?",
                (data.get("img_url", ""), data.get("description", ""), data["profile_id"])
            )
    return JSONResponse({"ok": True})


# ── API admin — profile ───────────────────────────────────────────────────────

@app.post("/api/profiles")
async def add_profile(request: Request):
    if not _is_admin(request):
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO profiles (code, name, category, width_mm, price_mb, margin_hurt, img_url, description, sort_order)
            VALUES (:code, :name, :category, :width_mm, :price_mb, :margin_hurt, :img_url, :description, :sort_order)
        """, data)
    return JSONResponse({"ok": True})


@app.put("/api/profiles/{profile_id}")
async def update_profile(profile_id: int, request: Request):
    if not _is_admin(request):
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    data["id"] = profile_id
    with get_conn() as conn:
        conn.execute("""
            UPDATE profiles SET
                code=:code, name=:name, category=:category,
                width_mm=:width_mm, price_mb=:price_mb, margin_hurt=:margin_hurt,
                img_url=:img_url, description=:description, active=:active
            WHERE id=:id
        """, data)
    return JSONResponse({"ok": True})


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: int, request: Request):
    if not _is_admin(request):
        return JSONResponse({"ok": False}, status_code=403)
    with get_conn() as conn:
        conn.execute("UPDATE profiles SET active=0 WHERE id=?", (profile_id,))
    return JSONResponse({"ok": True})


# ── API admin — ustawienia ────────────────────────────────────────────────────

@app.post("/api/settings")
async def update_settings(request: Request):
    if not _is_admin(request):
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    with get_conn() as conn:
        for key, value in data.items():
            if key == "admin_password_hash":
                continue
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
    return JSONResponse({"ok": True})


@app.post("/api/set-password")
async def change_password(request: Request, new_password: str = Form(...)):
    if not _is_admin(request):
        return JSONResponse({"ok": False}, status_code=403)
    set_password(new_password)
    return RedirectResponse("/admin", status_code=303)


# ── manifest PWA ──────────────────────────────────────────────────────────────

@app.get("/manifest.json")
async def manifest():
    return JSONResponse({
        "short_name": "Antyramy", "name": "Antyramy.eu Kalkulator",
        "icons": [{"src": "https://godek.eu/upload/elogo6.jpg", "sizes": "512x512", "type": "image/jpeg"}],
        "start_url": "/", "display": "standalone",
        "theme_color": "#0f172a", "background_color": "#ffffff",
    }, headers={"Content-Type": "application/manifest+json"})


# ── archiwum ──────────────────────────────────────────────────────────────────

@app.post("/admin/archive")
async def make_archive(request: Request, note: str = Form("")):
    if not _is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    from datetime import datetime
    zip_bytes = create_archive(note=note)
    filename = f"cennik_{datetime.now().strftime('%Y-%m-%d')}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── panel admina ──────────────────────────────────────────────────────────────

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": ""})


@app.post("/admin/login")
async def admin_login_post(request: Request, password: str = Form(...)):
    if not verify_password(password):
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "error": "Nieprawidłowe hasło"
        })
    token = make_session_token(password)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("kalk_admin", token, httponly=True, max_age=7200, samesite="Lax")
    return response


@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("kalk_admin")
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    if not _is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    return templates.TemplateResponse("admin/panel.html", {
        "request": request,
        "profiles": _profiles(),
        "settings": _settings(),
        "archives": list_archives(),
    })
