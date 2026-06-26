"""
Synchronizacja cen z WooCommerce (b2b.antyramy.eu).
Obsługuje dwa typy produktów:
- variable: aktualizuje warianty przez /variations/batch
- simple:   aktualizuje cenę bezpośrednio przez PATCH /products/{id}
"""
import httpx
from .calc import calculate_price, FORMATS_CONFIG
from .database import get_conn

# Mapowanie atrybutu formatu z WooCommerce → klucz formatu w kalk
# WC używa polskich przecinków w liczbach dziesiętnych (21x29,7), kalk ma klucz "21x30"
WC_FORMAT_MAP: dict[str, str] = {
    "10x15":    "10x15",
    "13x18":    "13x18",
    "15x21":    "15x21",
    "18x24":    "18x24",
    "21x29,7":  "21x29.7",
    "24x30":    "24x30",
    "25x38":    "25x38",
    "29,7x42":  "29.7x42",
    "30x40":    "30x40",
    "30x45":    "30x45",
}

# Mapowanie wartości atrybutu materiału z WooCommerce → front_type w kalk
WC_MATERIAL_MAP: dict[str, str] = {
    "szkło":  "szklo",
    "plexa":  "pleksa",
    "pleksa": "pleksa",
    "szklo":  "szklo",
}


def _get_wc_links(profile_id: int) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT wc_product_id FROM wc_links WHERE profile_id=? ORDER BY wc_product_id",
            (profile_id,)
        ).fetchall()
    return [r["wc_product_id"] for r in rows]


def _get_margin_exceptions(profile_id: int) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mode, format, margin, labor FROM format_margins WHERE profile_id=? AND mode='wholesale'",
            (profile_id,)
        ).fetchall()
    return {f"wholesale__{r['format']}": {"margin": r["margin"], "labor": r["labor"]} for r in rows}


def _read_attrs(attrs: list, attr_fmt: str, attr_mat: str) -> tuple[str | None, str | None]:
    """Wyciąga wartości formatu i materiału z listy atrybutów WooCommerce."""
    fmt_val = mat_val = None
    for attr in attrs:
        name = attr.get("name", "").lower()
        if name == attr_fmt:
            options = attr.get("options") or attr.get("option")
            if isinstance(options, list):
                fmt_val = options[0].strip() if options else None
            elif isinstance(options, str):
                fmt_val = options.strip()
        elif name == attr_mat:
            options = attr.get("options") or attr.get("option")
            if isinstance(options, list):
                mat_val = options[0].strip() if options else None
            elif isinstance(options, str):
                mat_val = options.strip()
    return fmt_val, mat_val


async def sync_profile(profile_id: int, profile: dict, settings: dict) -> dict:
    """
    Wysyła ceny do wszystkich powiązanych produktów WooCommerce.
    Zwraca {"ok": bool, "results": [...], "error": str?}
    """
    wc_url    = settings.get("wc_url", "").rstrip("/")
    wc_key    = settings.get("wc_key", "")
    wc_secret = settings.get("wc_secret", "")
    attr_fmt  = settings.get("wc_attr_format", "format").lower()
    attr_mat  = settings.get("wc_attr_material", "materiał").lower()
    price_key = "net" if settings.get("wc_price_type") == "net" else "gross"

    if not wc_url or not wc_key or not wc_secret:
        return {"ok": False, "error": "Uzupełnij dane WooCommerce API w ustawieniach"}

    wc_ids = _get_wc_links(profile_id)
    if not wc_ids:
        return {"ok": False, "error": "Profil nie ma przypisanych produktów WooCommerce"}

    margin_exc = _get_margin_exceptions(profile_id)
    category   = profile.get("category", "drewno")
    results    = []

    async with httpx.AsyncClient(timeout=30, auth=(wc_key, wc_secret)) as client:
        for wc_id in wc_ids:
            # ── pobierz produkt ───────────────────────────────────────────
            try:
                prod_resp = await client.get(f"{wc_url}/wp-json/wc/v3/products/{wc_id}")
            except Exception as e:
                results.append({"wc_id": wc_id, "ok": False, "error": str(e)})
                continue

            if prod_resp.status_code != 200:
                results.append({"wc_id": wc_id, "ok": False, "error": f"HTTP {prod_resp.status_code}"})
                continue

            product    = prod_resp.json()
            prod_type  = product.get("type", "simple")

            # ── VARIABLE: aktualizuj warianty ─────────────────────────────
            if prod_type == "variable":
                try:
                    var_resp = await client.get(
                        f"{wc_url}/wp-json/wc/v3/products/{wc_id}/variations",
                        params={"per_page": 100},
                    )
                except Exception as e:
                    results.append({"wc_id": wc_id, "ok": False, "error": str(e)})
                    continue

                if var_resp.status_code != 200:
                    results.append({"wc_id": wc_id, "ok": False, "error": f"Variations HTTP {var_resp.status_code}"})
                    continue

                updates = []
                skipped = []
                for var in var_resp.json():
                    fmt_val, mat_val = _read_attrs(var.get("attributes", []), attr_fmt, attr_mat)

                    kalk_fmt = WC_FORMAT_MAP.get(fmt_val)
                    if not kalk_fmt:
                        skipped.append(fmt_val)
                        continue

                    front_type = WC_MATERIAL_MAP.get(mat_val, "szklo") if mat_val else "szklo"
                    exc        = margin_exc.get(f"wholesale__{kalk_fmt}", {})
                    price_data = calculate_price(
                        format_name=kalk_fmt, profile=profile, settings=settings,
                        category=category, front_type=front_type, with_pp=False,
                        labor_override=exc.get("labor"), margin_override=exc.get("margin"),
                        mode="wholesale",
                    )
                    if price_data:
                        updates.append({
                            "id": var["id"],
                            "regular_price": str(round(price_data[price_key], 2)),
                        })

                if not updates:
                    results.append({"wc_id": wc_id, "ok": False,
                                     "error": f"Brak pasujących wariantów (pominięte: {skipped})"})
                    continue

                try:
                    batch = await client.post(
                        f"{wc_url}/wp-json/wc/v3/products/{wc_id}/variations/batch",
                        json={"update": updates},
                    )
                    if batch.status_code == 200:
                        results.append({"wc_id": wc_id, "ok": True, "updated": len(updates), "skipped": skipped, "type": "variable"})
                    else:
                        results.append({"wc_id": wc_id, "ok": False, "error": f"Batch HTTP {batch.status_code}"})
                except Exception as e:
                    results.append({"wc_id": wc_id, "ok": False, "error": str(e)})

            # ── SIMPLE: pobierz atrybuty z produktu, zaktualizuj cenę ─────
            else:
                fmt_val, mat_val = _read_attrs(product.get("attributes", []), attr_fmt, attr_mat)

                kalk_fmt = WC_FORMAT_MAP.get(fmt_val)
                if not kalk_fmt:
                    results.append({"wc_id": wc_id, "ok": False,
                                     "error": f"Nieznany format: '{fmt_val}'"})
                    continue

                front_type = WC_MATERIAL_MAP.get(mat_val, "szklo") if mat_val else "szklo"
                exc        = margin_exc.get(f"wholesale__{kalk_fmt}", {})
                price_data = calculate_price(
                    format_name=kalk_fmt, profile=profile, settings=settings,
                    category=category, front_type=front_type, with_pp=False,
                    labor_override=exc.get("labor"), margin_override=exc.get("margin"),
                    mode="wholesale",
                )
                if not price_data:
                    results.append({"wc_id": wc_id, "ok": False, "error": "Błąd kalkulacji"})
                    continue

                new_price = str(round(price_data[price_key], 2))
                try:
                    patch = await client.put(
                        f"{wc_url}/wp-json/wc/v3/products/{wc_id}",
                        json={"regular_price": new_price},
                    )
                    if patch.status_code == 200:
                        results.append({"wc_id": wc_id, "ok": True, "updated": 1,
                                         "format": kalk_fmt, "price": new_price, "type": "simple"})
                    else:
                        results.append({"wc_id": wc_id, "ok": False, "error": f"PATCH HTTP {patch.status_code}"})
                except Exception as e:
                    results.append({"wc_id": wc_id, "ok": False, "error": str(e)})

    all_ok = bool(results) and all(r["ok"] for r in results)
    return {"ok": all_ok, "results": results}
