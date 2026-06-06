"""
Testy integracyjne tras HTTP (api/index.py) przez FastAPI TestClient.
Baza jest tymczasowa (patrz conftest.py) i pusta — bez profili.
"""
from fastapi.testclient import TestClient

from api.auth import set_password
from api.index import app

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
