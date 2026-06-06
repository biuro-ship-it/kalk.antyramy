"""
Logika obliczania cen ramek.
Każdy element materiałowy ma własną marżę ustawianą globalnie.
Marża listwy pochodzi z profilu (margin_hurt).
"""
from typing import Optional

FORMATS_CONFIG: dict = {
    "10x15":  (10, 15,   "small",  "small",  4, 0),
    "13x18":  (13, 18,   "small",  "small",  4, 0),
    "15x21":  (15, 21,   "medium", "medium", 4, 0),
    "18x24":  (18, 24,   "medium", "medium", 4, 0),
    "20x30":  (20, 30,   "large",  "medium", 4, 0),
    "21x30":  (21, 29.7, "large",  "medium", 4, 0),
    "24x30":  (24, 30,   "large",  "large",  4, 0),
    "25x38":  (25, 38,   "large",  "large",  6, 1),
    "30x40":  (30, 40,   "large",  "large",  6, 1),
    "30x45":  (30, 45,   None,     "large",  6, 1),
    "40x50":  (40, 50,   None,     "large",  12, 2),
    "40x60":  (40, 60,   None,     "large",  12, 2),
    "50x70":  (50, 70,   None,     "large",  14, 2),
    "60x80":  (60, 80,   None,     "large",  14, 2),
    "70x100": (70, 100,  None,     "large",  14, 3),
}

LABOR_KEY = {"small": "labor_small", "medium": "labor_medium", "large": "labor_large"}


def _num(settings: dict, key: str, default: float) -> float:
    """Bezpieczna konwersja ustawienia na float — pusty/niepoprawny tekst → default."""
    value = settings.get(key, default)
    if value is None or value == "":
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _apply_margin(cost: float, margin_pct: float) -> float:
    """Przelicza koszt zakupu na cenę sprzedaży z marżą."""
    div = 1 - margin_pct / 100
    return cost / div if div > 0 else cost


def calculate_price(
    *,
    format_name: str,
    profile: dict,
    settings: dict,
    category: str,
    front_type: str,
    with_pp: bool,
    labor_override: Optional[float],
    mode: str = "wholesale",
) -> dict:
    if format_name not in FORMATS_CONFIG:
        return {}

    w, h, s_cat, p_cat, clip_count, hook_count = FORMATS_CONFIG[format_name]

    s_width      = float(profile.get("width_mm", 0) or 0)
    odpad        = 8  # stałe 8 cm odpadu na narożniki

    # długość listwy w metrach: 2*(wys+dł) + 8*szer_listwy_cm
    len_m   = (2 * (w + h) + odpad * s_width / 10) / 100
    area_m2 = (w * h) / 10000

    is_antyrama  = category == "antyrama"
    is_alu       = category == "alu"
    is_sama_rama = front_type == "sama_rama"
    is_pleksa    = front_type == "pleksa"

    # ── ceny zakupu ──────────────────────────────────────────────────
    front_key   = "plexsa_price_m2" if is_pleksa else "glass_price_m2"
    front_cost  = _num(settings, front_key, 0)
    back_cost   = _num(settings, "back_price_m2", 0)
    clip_cost   = _num(settings, "clip_price", 0)
    hook_cost   = _num(settings, "hook_price", 0)
    alu_kit_c   = _num(settings, "alu_kit_price", 0)
    pp_cost     = _num(settings, "pp_price_m2", 0)
    mb_cost     = float(profile.get("price_mb", 0) or 0)
    vat         = _num(settings, "vat", 23)

    # ── marże per element ────────────────────────────────────────────
    margin_front  = _num(settings, "margin_plexsa" if is_pleksa else "margin_glass", 30)
    margin_back   = _num(settings, "margin_back", 20)
    margin_pp     = _num(settings, "margin_pp", 30)
    margin_frame  = float(profile.get("margin_hurt", 40) or 40)   # marża listwy z profilu
    margin_alu    = _num(settings, "margin_alu_kit", 20)
    margin_clips  = _num(settings, "margin_clips", 20)

    # ── kalkulacja per element ze swoją marżą ────────────────────────
    net = 0.0

    if not is_sama_rama:
        net += _apply_margin(area_m2 * front_cost, margin_front)
        net += _apply_margin(area_m2 * back_cost,  margin_back)

    if is_antyrama:
        if not is_sama_rama:
            net += _apply_margin(clip_count * clip_cost + hook_count * hook_cost, margin_clips)
    elif is_alu:
        net += _apply_margin(len_m * mb_cost, margin_frame)
        net += _apply_margin(alu_kit_c, margin_alu)
    else:
        net += _apply_margin(len_m * mb_cost, margin_frame)

    if with_pp and not is_sama_rama:
        net += _apply_margin(area_m2 * pp_cost, margin_pp)

    # ── robocizna (bez marży — to koszt usługi) ──────────────────────
    base_labor_key = LABOR_KEY.get(p_cat) if p_cat else None
    base_labor = 0.0 if is_antyrama else _num(settings, base_labor_key or "", 0)
    labor = labor_override if labor_override is not None else base_labor
    net += labor

    gross = net * (1 + vat / 100)

    # koszt zakupu do info (bez marż)
    material_cost = 0.0
    if not is_sama_rama:
        material_cost += area_m2 * front_cost + area_m2 * back_cost
    if is_antyrama and not is_sama_rama:
        material_cost += clip_count * clip_cost + hook_count * hook_cost
    elif is_alu:
        material_cost += len_m * mb_cost + alu_kit_c
    elif not is_antyrama:
        material_cost += len_m * mb_cost
    if with_pp and not is_sama_rama:
        material_cost += area_m2 * pp_cost

    return {
        "format":   format_name,
        "net":      round(net, 2),
        "gross":    round(gross, 2),
        "material": round(material_cost, 2),
        "labor":    round(labor, 2),
        "profit":   round(net - material_cost - labor, 2),
        "margin":   round(margin_frame, 1),
        "vat":      vat,
    }


def calculate_all(
    *,
    profile: dict,
    settings: dict,
    category: str,
    front_type: str,
    with_pp: bool,
    margin_exceptions: dict,
    mode: str = "wholesale",
) -> list:
    results = []
    for fmt in FORMATS_CONFIG:
        key = f"{mode}__{fmt}"
        exc = margin_exceptions.get(key, {})
        results.append(calculate_price(
            format_name=fmt,
            profile=profile,
            settings=settings,
            category=category,
            front_type=front_type,
            with_pp=with_pp,
            labor_override=exc.get("labor"),
            mode=mode,
        ))
    return results
