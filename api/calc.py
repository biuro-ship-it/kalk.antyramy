"""
Logika obliczania cen ramek.
Odizolowana od FastAPI — łatwa do testowania.
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


def calculate_price(
    *,
    format_name: str,
    profile: dict,
    settings: dict,
    category: str,
    front_type: str,
    with_pp: bool,
    margin_override: Optional[float],
    labor_override: Optional[float],
    mode: str = "wholesale",
) -> dict:
    if format_name not in FORMATS_CONFIG:
        return {}

    w, h, s_cat, p_cat, clip_count, hook_count = FORMATS_CONFIG[format_name]

    s_width      = float(profile.get("width_mm", 0))
    frame_margin = float(settings.get("frame_margin_mm", 8))

    len_m   = (2 * (w + h) + frame_margin * s_width / 10) / 100
    area_m2 = (w * h) / 10000

    is_antyrama  = category == "antyrama"
    is_alu       = category == "alu"
    is_sama_rama = front_type == "sama_rama"
    is_pleksa    = front_type == "pleksa"

    glass_p = float(settings.get("plexsa_price_m2" if is_pleksa else "glass_price_m2", 0))
    back_p  = float(settings.get("back_price_m2", 0))
    clip_p  = float(settings.get("clip_price", 0))
    hook_p  = float(settings.get("hook_price", 0))
    alu_kit = float(settings.get("alu_kit_price", 0))
    pp_p    = float(settings.get("pp_price_m2", 0))
    vat     = float(settings.get("vat", 23))
    mb_p    = float(profile.get("price_mb", 0))

    if is_sama_rama:
        material = 0.0
    else:
        material = area_m2 * glass_p + area_m2 * back_p

    if is_antyrama:
        if not is_sama_rama:
            material += clip_count * clip_p + hook_count * hook_p
    elif is_alu:
        material += len_m * mb_p + alu_kit
    else:
        material += len_m * mb_p
        if not is_sama_rama and s_cat:
            material += float(settings.get(f"support_{s_cat}", 0))

    if with_pp and not is_sama_rama:
        material += area_m2 * pp_p

    base_labor_key = LABOR_KEY.get(p_cat) if p_cat else None
    base_labor = 0.0 if is_antyrama else float(settings.get(base_labor_key or "", 0))
    base_margin = float(profile.get("margin_hurt", 40))

    margin = margin_override if margin_override is not None else base_margin
    labor  = labor_override  if labor_override  is not None else base_labor

    total_cost = material + labor
    div   = 1 - margin / 100
    net   = total_cost / div if div > 0 else total_cost
    gross = net * (1 + vat / 100)

    return {
        "format":   format_name,
        "net":      round(net, 2),
        "gross":    round(gross, 2),
        "material": round(material, 2),
        "labor":    round(labor, 2),
        "profit":   round(net - total_cost, 2),
        "margin":   round(margin, 1),
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
            margin_override=exc.get("margin"),
            labor_override=exc.get("labor"),
            mode=mode,
        ))
    return results
