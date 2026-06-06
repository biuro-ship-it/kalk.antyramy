"""
Testy silnika wyceny (api/calc.py) — czysta logika, bez FastAPI i bazy.
"""
import pytest

from api.calc import FORMATS_CONFIG, _apply_margin, calculate_all, calculate_price

DEFAULT_SETTINGS = {
    "glass_price_m2": 28,
    "back_price_m2": 12,
    "labor_large": 6.5,
    "vat": 23,
    # marże per element pozostają domyślne (margin_glass=30, margin_back=20)
}


def _profile(**override):
    base = {"width_mm": 30, "price_mb": 10, "margin_hurt": 40}
    base.update(override)
    return base


def test_apply_margin_full_margin_has_no_zero_division():
    # marża 100% → dzielnik (1 - 1) = 0; zabezpieczenie: zwraca koszt bez dzielenia
    assert _apply_margin(100, 100) == 100
    # marża 30% → 70 / 0.70 = 100
    assert _apply_margin(70, 30) == pytest.approx(100)


def test_calculate_price_drewno_szklo_happy_path():
    # 30x40, drewno+szkło, marże per element (szkło 30%, plecy 20%, listwa 40%):
    #   szkło  = 0.12*28 / 0.70 = 4.80
    #   plecy  = 0.12*12 / 0.80 = 1.80
    #   listwa = 1.64*10 / 0.60 = 27.33
    #   praca  = 6.50 (bez marży)  → net = 40.43
    # koszt zakupu (material): 3.36 + 1.44 + 16.40 = 21.20
    result = calculate_price(
        format_name="30x40",
        profile=_profile(),
        settings=DEFAULT_SETTINGS,
        category="drewno",
        front_type="szklo",
        with_pp=False,
        labor_override=None,
    )
    assert result["format"] == "30x40"
    assert result["material"] == 21.2
    assert result["labor"] == 6.5
    assert result["net"] == 40.43
    assert result["gross"] == pytest.approx(result["net"] * 1.23, abs=0.05)
    assert result["margin"] == 40.0


def test_calculate_price_unknown_format_returns_empty():
    result = calculate_price(
        format_name="99x99",
        profile=_profile(),
        settings=DEFAULT_SETTINGS,
        category="drewno",
        front_type="szklo",
        with_pp=False,
        labor_override=None,
    )
    assert result == {}


def test_pleksa_uses_margin_plexsa_not_price():
    # Regresja: front pleksy MUSI używać klucza margin_plexsa, a NIE ceny plexsa_price_m2.
    # Przy margin_plexsa=30 i cenie 55 zł/m² front = 0.12*55/0.70 = 9.43 (nie 14.67 jak przy 55%).
    settings = {**DEFAULT_SETTINGS, "plexsa_price_m2": 55, "margin_plexsa": 30}
    common = dict(
        format_name="30x40",
        profile=_profile(),
        settings=settings,
        category="drewno",
        front_type="pleksa",
        with_pp=False,
        labor_override=None,
    )
    result = calculate_price(**common)
    # net = front 9.43 + plecy 1.80 + listwa 27.33 + praca 6.50 = 45.06
    assert result["net"] == pytest.approx(45.06, abs=0.02)

    # gdyby błędnie brało cenę (55) jako marżę, net byłby istotnie wyższy
    buggy = calculate_price(**{**common, "settings": {**settings, "margin_plexsa": 55}})
    assert result["net"] < buggy["net"]


def test_calculate_price_sama_rama_excludes_glass():
    common = dict(
        format_name="30x40",
        profile=_profile(),
        settings=DEFAULT_SETTINGS,
        category="drewno",
        with_pp=False,
        labor_override=None,
    )
    with_glass = calculate_price(front_type="szklo", **common)
    frame_only = calculate_price(front_type="sama_rama", **common)
    assert frame_only["material"] < with_glass["material"]


def test_calculate_all_covers_every_format():
    results = calculate_all(
        profile=_profile(),
        settings=DEFAULT_SETTINGS,
        category="drewno",
        front_type="szklo",
        with_pp=False,
        margin_exceptions={},
    )
    assert len(results) == len(FORMATS_CONFIG)
    assert all(r for r in results)  # żaden format nie zwrócił pustego wyniku
