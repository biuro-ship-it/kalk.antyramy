import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import math
import json

app = FastAPI()

# --- ZABEZPIECZENIE ---
ADMIN_PASSWORD = "qwerty11" 

# --- KONFIGURACJA ŚCIEŻEK ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
creds_path = os.path.join(BASE_DIR, 'credentials.json')
templates_path = os.path.join(BASE_DIR, "..", "templates")
templates = Jinja2Templates(directory=templates_path)

CACHED_DATA = []
GLOBAL_SETTINGS = {}
LAST_ERROR = None

# Konfiguracja formatów: (szer, wys, kat_podporki, kat_produkcji, s_spinki, z_zaczepy)
FORMATS_CONFIG = {
    "10x15": (10, 15, "mala", "mala", 4, 0),
    "13x18": (13, 18, "mala", "mala", 4, 0),
    "15x21": (15, 21, "srednia", "srednia", 4, 0),
    "18x24": (18, 24, "srednia", "srednia", 4, 0),
    "20x30": (20, 30, "duza", "srednia", 4, 0),
    "21x29.7": (21, 29.7, "duza", "srednia", 4, 0),
    "24x30": (24, 30, "duza", "duza", 4, 0),
    "25x38": (25, 38, "duza", "duza", 6, 1),
    "30x40": (30, 40, "duza", "duza", 6, 1),
    "30x45": (30, 45, None, "duza", 6, 1),
    "40x50": (40, 50, None, "duza", 12, 2),
    "40x60": (40, 60, None, "duza", 12, 2),
    "50x70": (50, 70, None, "duza", 14, 2),
    "60x80": (60, 80, None, "duza", 14, 2),
    "70x100": (70, 100, None, "duza", 14, 3),
}

def clean_val(val):
    if val is None or val == "": return 0.0
    s = str(val).replace(',', '.').strip()
    s = "".join(c for c in s if c.isdigit() or c == '.')
    try: return float(s) if s else 0.0
    except: return 0.0

def fetch_data():
    global CACHED_DATA, GLOBAL_SETTINGS, LAST_ERROR
    try:
        LAST_ERROR = None
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Pobieranie klucza z bezpiecznego sejfu Vercel lub z pliku lokalnego
        google_creds_env = os.environ.get("GOOGLE_CREDENTIALS")
        if google_creds_env:
            creds_dict = json.loads(google_creds_env)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif os.path.exists(creds_path):
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        else:
            LAST_ERROR = "Błąd: Brak bezpiecznego klucza Google (Vercel Environment Variables)."
            return
        
        client = gspread.authorize(creds)
        sheet = client.open("Baza Ramek").sheet1
        data = sheet.get_all_values()
        if not data: return
        headers = [h.strip() for h in data[0]]
        rows = [dict(zip(headers, r)) for r in data[1:]]
        GLOBAL_SETTINGS = next((r for r in rows if r.get('nazwa', '').lower() == 'ustawienia'), {})
        CACHED_DATA = [r for r in rows if r.get('nazwa', '') != '' and r.get('nazwa', '').lower() != 'ustawienia']
    except Exception as e:
        LAST_ERROR = f"Błąd Google: {str(e)}"

def get_profiles_list():
    # Zwraca listę obiektów {nazwa, img} zamiast samych nazw dla podglądu JS
    return [{"nazwa": item.get('nazwa'), "img": item.get('link_zdjecie', '')} for item in CACHED_DATA if item.get('nazwa')]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not CACHED_DATA: fetch_data()
    return templates.TemplateResponse("index.html", {
        "request": request, "profiles": get_profiles_list(), "is_loaded": (len(CACHED_DATA) > 0)
    })

@app.post("/refresh")
async def refresh():
    fetch_data()
    return RedirectResponse(url="/", status_code=303)

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request, 
    profile_name: str = Form(None), 
    mode: str = Form("retail"), 
    password: str = Form(None),
    product_type: str = Form("normal"),
    with_pp: str = Form(None),
    use_pleksa: str = Form(None)
):
    if not CACHED_DATA: fetch_data()
    is_admin = (password == ADMIN_PASSWORD)
    
    is_szklo_anty = (product_type == "antyrama")
    is_pleksa_anty = (product_type == "pleksa")
    is_alu = (product_type == "alu")
    is_normal = (product_type == "normal")
    
    if is_szklo_anty or is_pleksa_anty:
        profile = {"nazwa": "ANTYRAMA", "szerokosc_listwy": "0", "cena_zakupu_mb": "0", "link_zdjecie": ""}
    else:
        profile = next((item for item in CACHED_DATA if item.get("nazwa") == profile_name), None)

    if not profile:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Wybierz kod profilu.", "profiles": get_profiles_list()})

    def get_smart_val(key):
        val_str = profile.get(key, "").strip() if (not is_szklo_anty and not is_pleksa_anty) else ""
        if val_str == "" or val_str == "0" or val_str == "zmienna":
            return clean_val(GLOBAL_SETTINGS.get(key, 0))
        return clean_val(val_str)

    s_width = clean_val(profile.get('szerokosc_listwy', 0))
    s_price = clean_val(profile.get('cena_zakupu_mb', 0))
    img_url = profile.get('link_zdjecie', '') # POBIERAMY URL ZDJĘCIA
    
    if is_pleksa_anty or use_pleksa:
        front_p = clean_val(GLOBAL_SETTINGS.get('cena_pleksy_m2', 0))
        front_label = "PLEKSA"
    else:
        front_p = get_smart_val('cena_szkla_m2')
        front_label = "SZKŁO"

    back_p = get_smart_val('cena_tylow_m2')
    clip_p = clean_val(GLOBAL_SETTINGS.get('cena_spinki', 0))
    hook_p = clean_val(GLOBAL_SETTINGS.get('cena_zaczep', 0))
    pp_p = clean_val(GLOBAL_SETTINGS.get('cena_pp_m2', 0))
    alu_kit_p = clean_val(GLOBAL_SETTINGS.get('montaz_alu', 0))
    vat = get_smart_val('vat') or 23

    # MARŻA
    if is_szklo_anty: m_key = 'marza_anty_hurt' if mode == "wholesale" else 'marza_anty_detal'
    elif is_pleksa_anty: m_key = 'marza_pleksa_hurt' if mode == "wholesale" else 'marza_pleksa_detal'
    elif is_alu: m_key = 'marza_alu_hurt' if mode == "wholesale" else 'marza_alu_detal'
    else: m_key = 'marza_hurt' if mode == "wholesale" else 'marza'
        
    margin = clean_val(GLOBAL_SETTINGS.get(m_key, 0))
    if margin == 0: margin = clean_val(profile.get(m_key, 0))
    if margin == 0: margin = get_smart_val('marza_hurt' if mode == "wholesale" else 'marza')

    results = []
    for name, config in FORMATS_CONFIG.items():
        w, h, s_cat, p_cat, s_count, z_count = config
        len_m = (2 * (w + h) + 8 * s_width) / 100
        area_m2 = (w * h) / 10000
        c_surowiec = (area_m2 * front_p) + (area_m2 * back_p)
        
        if is_szklo_anty or is_pleksa_anty:
            c_surowiec += (s_count * clip_p) + (z_count * hook_p)
            label = f"ANTYRAMA {front_label}"
        elif is_alu:
            c_surowiec += (len_m * s_price) + alu_kit_p
            label = f"ALU: {profile['nazwa']} ({front_label})"
        else:
            c_surowiec += (len_m * s_price)
            if s_cat: c_surowiec += get_smart_val(f'cena_podporka_{s_cat}')
            label = f"RAMA DREWNO: {profile['nazwa']} ({front_label})"
            
        if with_pp: c_surowiec += (area_m2 * pp_p)
        c_robocizna = get_smart_val(f'koszt_prod_{p_cat}') if p_cat else 0
        divisor = (1 - (margin / 100))
        net = c_surowiec / (divisor if divisor > 0 else 0.01)
        gross = net * (1 + (vat / 100))
        
        res_row = {"size": name, "net": f"{net:.2f}", "gross": f"{gross:.2f}"}
        if is_admin:
            res_row.update({"surowiec": f"{c_surowiec:.2f}", "mr": f"{net:.2f}", "rb": f"{(c_surowiec+c_robocizna):.2f}", "zmr": f"{(net-c_surowiec):.2f}"})
        results.append(res_row)

    return templates.TemplateResponse("index.html", {
        "request": request, "results": results, "profile": label, "margin": margin, "mode": mode,
        "is_admin": is_admin, "profiles": get_profiles_list(), "product_type": product_type, 
        "with_pp": with_pp, "use_pleksa": use_pleksa, "selected_profile": profile_name, "img_url": img_url
    })