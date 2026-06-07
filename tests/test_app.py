"""
Testy integracyjne tras HTTP (api/index.py) przez FastAPI TestClient.
Baza jest tymczasowa (patrz conftest.py) i pusta — bez profili.
"""
from fastapi.testclient import TestClient

from api.auth import set_password
from api.database import get_conn
from api.index import BASE_DIR, app

client = TestClient(app)


def test_home_returns_200_not_500():
    # Regresja: wcześniej 500 ("no such table: profiles"), bo init_db był
    # w @app.on_event("startup"), którego a2wsgi (ASGI->WSGI) nie uruchamia.
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_manifest_is_served_with_correct_type():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")


def test_calculate_antyrama_renders_without_profile():
    response = client.post(
        "/calculate",
        data={"category": "antyrama", "front_type": "szklo", "mode": "wholesale"},
    )
    assert response.status_code == 200


def test_calculate_without_profile_redirects_home():
    response = client.post(
        "/calculate", data={"category": "drewno"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_admin_panel_requires_auth():
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert "/admin/login" in response.headers["location"]


def test_api_profiles_forbidden_without_admin():
    response = client.post("/api/profiles", json={})
    assert response.status_code == 403


def test_admin_login_flow():
    fresh = TestClient(app)  # własny klient, żeby cookie nie wyciekło do innych testów

    bad = fresh.post("/admin/login", data={"password": "zle"}, follow_redirects=False)
    assert bad.status_code == 200
    assert "Nieprawidłowe hasło" in bad.text

    set_password("tajne123")
    ok = fresh.post("/admin/login", data={"password": "tajne123"}, follow_redirects=False)
    assert ok.status_code == 303
    assert "kalk_admin" in ok.headers.get("set-cookie", "")


def _admin_client() -> TestClient:
    c = TestClient(app)
    set_password("tajne123")
    c.post("/admin/login", data={"password": "tajne123"})
    return c


def test_save_margins_single_update_persists():
    # Frontend wysyła marże pojedynczo (omija WAF) — backend musi przyjąć
    # żądanie z jednym wpisem i bez metadanych profilu na górze.
    c = _admin_client()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO profiles (code,name,category,width_mm,price_mb,margin_hurt) "
            "VALUES ('SM','SM','drewno',30,10,40)"
        )
        pid = conn.execute("SELECT id FROM profiles WHERE code='SM'").fetchone()["id"]

    res = c.post("/api/save-margins", json={
        "updates": [{"mode": "wholesale", "profile_id": pid, "format": "30x40", "margin": 55, "labor": 3}]
    })
    assert res.status_code == 200
    assert res.json()["ok"] is True

    with get_conn() as conn:
        row = conn.execute(
            "SELECT margin, labor FROM format_margins WHERE profile_id=? AND format='30x40'", (pid,)
        ).fetchone()
    assert row["margin"] == 55
    assert row["labor"] == 3


def test_save_margins_forbidden_without_admin():
    res = TestClient(app).post("/api/save-margins", json={"updates": []})
    assert res.status_code == 403


def test_upload_image_rejects_over_1mb():
    c = _admin_client()
    big = b"x" * (1024 * 1024 + 1)  # 1 MB + 1 bajt
    res = c.post("/api/upload-image", files={"file": ("duzy.png", big, "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "1 MB" in body["error"]


def test_upload_image_accepts_small_png():
    c = _admin_client()
    small = b"x" * 1024  # 1 KB
    res = c.post("/api/upload-image", files={"file": ("maly.png", small, "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["url"].startswith("/static/images/")

    # sprzątanie: usuń realnie zapisany plik
    saved = BASE_DIR / body["url"].lstrip("/")
    if saved.exists():
        saved.unlink()
