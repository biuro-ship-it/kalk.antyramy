import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import math
import json
import re
import traceback
from typing import Optional
from threading import Lock

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_details = traceback.format_exc()
    return HTMLResponse(
        content=f"<div style='padding:20px; font-family:monospace; color:#b91c1c; background:#fef2f2;'><pre>{error_details}</pre></div>",
        status_code=500
    )

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "qwerty11") 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
creds_path = os.path.join(BASE_DIR, 'credentials.json')
templates_path = os.path.join(BASE_DIR, "..", "templates")
templates = Jinja2Templates(directory=templates_path)

data_lock = Lock()
CACHED_DATA = []
PROFILES_MAP = {}
GLOBAL_SETTINGS = {}
MARGIN_EXCEPTIONS = {}
LAST_ERROR = None
FRAME_MARGIN = 8

FORMATS_CONFIG = {
    "10x15": (10, 15, "mala", "mala", 4, 0), "13x18": (13, 18, "mala", "mala", 4, 0),
    "15x21": (15, 21, "srednia", "srednia", 4, 0), "18x24": (18, 24, "srednia", "srednia", 4, 0),
    "20x30": (20, 30, "duza", "srednia", 4, 0), "21x29.7": (21, 29.7, "duza", "srednia", 4, 0),
    "24x30": (24, 30, "duza", "duza", 4, 0), "25x38": (25, 38, "duza", "duza", 6, 1),
    "30x40": (30, 40, "duza", "duza", 6, 1), "30x45": (30, 45, None, "duza", 6, 1),
    "40x50": (40, 50, None, "duza", 12, 2), "40x60": (40, 60, None, "duza", 12, 2),
    "50x70": (50, 70, None, "duza", 14, 2), "60x80": (60, 80, None, "duza", 14, 2),
    "70x100": (70, 100, None, "duza", 14, 3),
}

def clean_val(val):
    if val is None or val == "": return 0.0
    s = str(val).replace(',', '.').strip()
    match = re.findall(r"\d+\.?\d*", s)
    try: return float(match[0]) if match else 0.0
    except: return 0.0

def fetch_data():
    global CACHED_DATA, GLOBAL_SETTINGS, PROFILES_MAP, MARGIN_EXCEPTIONS, LAST_ERROR
    try:
        LAST_ERROR = None
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        env_creds = os.environ.get("GOOGLE_CREDENTIALS")
        if env_creds: creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(env_creds), scope)
        else: creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        
        client = gspread.authorize(creds)
        wb = client.open("Baza Ramek")
        
        # BAZA GŁÓWNA
        data = wb.sheet1.get_all_values()
        headers = [h.strip() for h in data[0]]
        rows = [dict(zip(headers, r)) for r in data[1:]]
        
        # NOWOŚĆ: BAZA WYJĄTKÓW (Zapisane marże)
        try:
            ws_wyjatki = wb.worksheet("Wyjatki_Marze")
        except gspread.exceptions.WorksheetNotFound:
            ws_wyjatki = wb.add_worksheet(title="Wyjatki_Marze", rows=100, cols=4)
            ws_wyjatki.append_row(["Tryb", "Produkt", "Format", "Marza"])
            
        wyjatki_data = ws_wyjatki.get_all_values()
        temp_wyjatki = {}
        if wyjatki_data and len(wyjatki_data) > 1:
            for r in wyjatki_data[1:]:
                if len(r) >= 4:
                    temp_wyjatki[f"{r[0]}_{r[1]}_{r[2]}"] = clean_val(r[3])

        with data_lock:
            GLOBAL_SETTINGS = next((r for r in rows if r.get('nazwa', '').lower() == 'ustawienia'), {})
            CACHED_DATA = [r for r in rows if r.get('nazwa', '') != '' and r.get('nazwa', '').lower() != 'ustawienia']
            PROFILES_MAP = {p.get("nazwa"): p for p in CACHED_DATA if p.get("nazwa")}
            MARGIN_EXCEPTIONS = temp_wyjatki
    except Exception as e:
        LAST_ERROR = f"Błąd Google: {str(e)}"

def get_profiles_list():
    return [{"nazwa": item.get('nazwa'), "img": item.get('link_zdjecie', '')} for item in CACHED_DATA if item.get('nazwa')]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not CACHED_DATA: fetch_data()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, "profiles": get_profiles_list(), "is_loaded": (len(CACHED_DATA) > 0), "error": LAST_ERROR
    })

@app.post("/refresh")
async def refresh():
    fetch_data()
    return RedirectResponse(url="/", status_code=303)

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request, profile_name: Optional[str] = Form(None), mode: str = Form("retail"), 
    password: Optional[str] = Form(None), product_type: str = Form("normal"),
    with_pp: Optional[str] = Form(None), use_pleksa: Optional[str] = Form(None)
):
    if not CACHED_DATA: fetch_data()
    is_admin = (password == ADMIN_PASSWORD)
    
    is_szklo_anty = (product_type == "antyrama")
    is_pleksa_anty = (product_type == "pleksa")
    is_alu = (product_type == "alu")
    
    if not profile_name and not (is_szklo_anty or is_pleksa_anty):
        return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "error": "Wybierz kod profilu.", "profiles": get_profiles_list()})

    profile = {"nazwa": "ANTYRAMA", "szerokosc_listwy": "0", "cena_zakupu_mb": "0", "link_zdjecie": ""} if (is_szklo_anty or is_pleksa_anty) else PROFILES_MAP.get(profile_name)
    if not profile: return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "error": "Brak profilu.", "profiles": get_profiles_list()})

    def get_smart_val(key):
        val_str = profile.get(key, "").strip() if (not is_szklo_anty and not is_pleksa_anty) else ""
        return clean_val(GLOBAL_SETTINGS.get(key, 0)) if val_str in ["", "0", "zmienna"] else clean_val(val_str)

    s_width = clean_val(profile.get('szerokosc_listwy', 0))
    s_price = clean_val(profile.get('cena_zakupu_mb', 0))
    img_url = profile.get('link_zdjecie', '') 
    
    if is_pleksa_anty or use_pleksa: front_p, front_label = clean_val(GLOBAL_SETTINGS.get('cena_pleksy_m2', 0)), "PLEKSA"
    else: front_p, front_label = get_smart_val('cena_szkla_m2'), "SZKŁO"

    back_p, clip_p, hook_p = get_smart_val('cena_tylow_m2'), clean_val(GLOBAL_SETTINGS.get('cena_spinki', 0)), clean_val(GLOBAL_SETTINGS.get('cena_zaczep', 0))
    pp_p, alu_kit_p, vat = clean_val(GLOBAL_SETTINGS.get('cena_pp_m2', 0)), clean_val(GLOBAL_SETTINGS.get('montaz_alu', 0)), get_smart_val('vat') or 23

    if is_szklo_anty: m_key = 'marza_anty_hurt' if mode == "wholesale" else 'marza_anty_detal'
    elif is_pleksa_anty: m_key = 'marza_pleksa_hurt' if mode == "wholesale" else 'marza_pleksa_detal'
    elif is_alu: m_key = 'marza_alu_hurt' if mode == "wholesale" else 'marza_alu_detal'
    else: m_key = 'marza_hurt' if mode == "wholesale" else 'marza'
        
    base_margin = clean_val(GLOBAL_SETTINGS.get(m_key, 0)) or clean_val(profile.get(m_key, 0)) or get_smart_val('marza_hurt' if mode == "wholesale" else 'marza')

    results = []
    for name, config in FORMATS_CONFIG.items():
        w, h, s_cat, p_cat, s_count, z_count = config
        len_m, area_m2 = (2*(w+h) + FRAME_MARGIN*s_width)/100, (w*h)/10000
        c_surowiec = (area_m2 * front_p) + (area_m2 * back_p)
        
        if is_szklo_anty or is_pleksa_anty: c_surowiec += (s_count * clip_p) + (z_count * hook_p); label = f"ANTYRAMA {front_label}"
        elif is_alu: c_surowiec += (len_m * s_price) + alu_kit_p; label = f"ALU: {profile['nazwa']} ({front_label})"
        else: c_surowiec += (len_m * s_price) + (get_smart_val(f'cena_podporka_{s_cat}') if s_cat else 0); label = f"RAMA DREWNO: {profile['nazwa']} ({front_label})"
            
        if with_pp: c_surowiec += (area_m2 * pp_p)
        c_robocizna = 0 if (is_szklo_anty or is_pleksa_anty) else (get_smart_val(f'koszt_prod_{p_cat}') if p_cat else 0)
        total_cost = c_surowiec + c_robocizna
        
        # POBIERANIE MARŻY INDYWIDUALNEJ (Z GOOGLE SHEETS)
        exception_key = f"{mode}_{label}_{name}"
        active_margin = MARGIN_EXCEPTIONS.get(exception_key)
        if active_margin is None: active_margin = base_margin
            
        if active_margin >= 100: active_margin = 99.9
        
        divisor = (1 - (active_margin / 100))
        net, gross = total_cost / divisor, (total_cost / divisor) * (1 + (vat / 100))
        
        results.append({
            "size": name, "net": f"{net:.2f}", "gross": f"{gross:.2f}",
            "surowiec": f"{c_surowiec:.2f}", "total_cost": f"{total_cost:.2f}",
            "profit": f"{(net - total_cost):.2f}", "active_margin": f"{active_margin:.1f}"
        })

    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, "results": results, "profile": label, "margin": base_margin, "mode": mode,
        "is_admin": is_admin, "profiles": get_profiles_list(), "product_type": product_type, 
        "with_pp": with_pp, "use_pleksa": use_pleksa, "selected_profile": profile_name, "img_url": img_url,
        "vat": vat, "admin_password": password if is_admin else None
    })

@app.post("/save_margins")
async def save_margins(request: Request):
    try:
        data = await request.json()
        if data.get("password") != ADMIN_PASSWORD:
            return JSONResponse({"success": False, "error": "Brak autoryzacji"})

        env_creds = os.environ.get("GOOGLE_CREDENTIALS")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(env_creds), scope) if env_creds else ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        
        wb = gspread.authorize(creds).open("Baza Ramek")
        try: ws = wb.worksheet("Wyjatki_Marze")
        except: ws = wb.add_worksheet("Wyjatki_Marze", 100, 4)

        all_data = ws.get_all_values()
        if not all_data: all_data = [["Tryb", "Produkt", "Format", "Marza"]]

        existing = {f"{r[0]}_{r[1]}_{r[2]}": r for r in all_data[1:] if len(r) >= 4}
        for u in data.get("updates", []):
            existing[f"{u['mode']}_{u['profile']}_{u['size']}"] = [u['mode'], u['profile'], u['size'], str(u['margin'])]

        new_data = [all_data[0]] + list(existing.values())
        ws.clear()
        try: ws.update('A1', new_data)
        except: ws.update(values=new_data, range_name='A1')

        fetch_data() # Zaktualizuj pamięć serwera Vercel
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})