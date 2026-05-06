import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
import re
import traceback
import hashlib
from typing import Optional
from threading import Lock

app = FastAPI()

# Konfiguracja ścieżek
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(BASE_DIR, "..", "static")
TEMPLATES_PATH = os.path.join(BASE_DIR, "..", "templates")

if os.path.exists(STATIC_PATH):
    app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

templates = Jinja2Templates(directory=TEMPLATES_PATH)

# BEZPIECZEŃSTWO: Ukrywamy szczegóły błędu przed użytkownikiem (wymóg z audytu)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Błąd serwera: {str(exc)}") # Logujemy tylko w konsoli (widoczne dla Ciebie na Vercel)
    return HTMLResponse(
        content="<div style='padding:20px; font-family:sans-serif; color:#b91c1c; background:#fef2f2; border-radius: 8px; text-align: center;'><h3>Wystąpił błąd systemu.</h3><p>Spróbuj ponownie lub skontaktuj się z obsługą.</p></div>",
        status_code=500
    )

# BEZPIECZEŃSTWO: Brak hasła "na sztywno" w kodzie
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "brak_hasla_ustaw_w_vercel") 
creds_path = os.path.join(BASE_DIR, 'credentials.json')

# Funkcja szyfrująca ciasteczko logowania
def get_auth_token():
    return hashlib.sha256((ADMIN_PASSWORD + "antyramy_secure_salt").encode()).hexdigest()

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
        if env_creds: 
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(env_creds), scope)
        else: 
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        
        client = gspread.authorize(creds)
        wb = client.open("Baza Ramek")
        data = wb.sheet1.get_all_values()
        if not data: return
        headers = [h.strip() for h in data[0]]
        rows = [dict(zip(headers, r)) for r in data[1:]]
        
        try: 
            ws_wyjatki = wb.worksheet("Wyjatki_Marze")
        except: 
            ws_wyjatki = wb.add_worksheet(title="Wyjatki_Marze", rows=100, cols=5)
            ws_wyjatki.append_row(["Tryb", "Produkt", "Format", "Marza", "Robocizna"])
        
        wyjatki_data = ws_wyjatki.get_all_values()
        temp_wyjatki = {f"{r[0]}_{r[1]}_{r[2]}": {"m": clean_val(r[3]), "l": clean_val(r[4]) if len(r) >= 5 else None} for r in wyjatki_data[1:] if len(r) >= 3}
        
        with data_lock:
            GLOBAL_SETTINGS = next((r for r in rows if r.get('nazwa', '').lower() == 'ustawienia'), {})
            CACHED_DATA = []
            for r in rows:
                name = r.get('nazwa', '').strip()
                if name != '' and name.lower() != 'ustawienia':
                    kat = r.get('kategoria', '').strip().lower()
                    if not kat: r['kategoria'] = 'brak'
                    CACHED_DATA.append(r)
            
            PROFILES_MAP = {p.get("nazwa"): p for p in CACHED_DATA if p.get("nazwa")}
            MARGIN_EXCEPTIONS = temp_wyjatki
            
    except Exception as e:
        LAST_ERROR = f"Błąd Google: Brak dostępu do arkusza lub błędne klucze."

@app.on_event("startup")
async def startup_event():
    fetch_data()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not CACHED_DATA: fetch_data()
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "mode": "wholesale", "profiles": [{"nazwa": item.get('nazwa'), "kat": item.get('kategoria', 'brak')} for item in CACHED_DATA if item.get('nazwa')], "error": LAST_ERROR})

@app.get("/manifest.json")
async def manifest():
    content = {
        "short_name": "Antyramy", "name": "Antyramy.eu Kalkulator",
        "icons": [{"src": "https://godek.eu/upload/elogo6.jpg", "sizes": "512x512", "type": "image/jpeg"}],
        "start_url": "/", "display": "standalone", "theme_color": "#0f172a", "background_color": "#ffffff"
    }
    return JSONResponse(content=content, headers={"Content-Type": "application/manifest+json"})

@app.post("/refresh")
async def refresh():
    fetch_data()
    return RedirectResponse(url="/", status_code=303)

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(request: Request, profile_name: Optional[str] = Form(None), mode: str = Form("wholesale"), password: Optional[str] = Form(None), main_category: str = Form("drewno"), front_type: str = Form("szklo"), with_pp: Optional[str] = Form(None)):
    if not CACHED_DATA: fetch_data()
    
    # Obsługa autoryzacji admina - sprawdzamy hasło z formularza LUB z wcześniej zadanego ciastka
    auth_cookie = request.cookies.get("admin_auth")
    is_admin = (password == ADMIN_PASSWORD) or (auth_cookie == get_auth_token())
    
    is_antyrama = (main_category == "antyrama")
    is_alu = (main_category == "alu")
    is_plastik = (main_category == "plastik")
    is_pleksa = (front_type == "pleksa")
    is_sama_rama = (front_type == "sama_rama")
    
    profile = {"nazwa": "ANTYRAMA", "szerokosc_listwy": "0", "cena_zakupu_mb": "0"} if is_antyrama else PROFILES_MAP.get(profile_name)
    if not profile: return RedirectResponse(url="/", status_code=303)
    
    przekroj_img = profile.get('link_zdjecie', '') if not is_antyrama else ''
    description = profile.get('Opis_Dodatkowy', '') if not is_antyrama else ''
    
    def get_smart_val(key):
        val_str = profile.get(key, "").strip() if not is_antyrama else ""
        return clean_val(GLOBAL_SETTINGS.get(key, 0)) if val_str in ["", "0", "zmienna"] else clean_val(val_str)
    
    s_width, s_price = clean_val(profile.get('szerokosc_listwy', 0)), clean_val(profile.get('cena_zakupu_mb', 0))
    
    if is_sama_rama:
        front_p = back_p = clip_p = hook_p = alu_kit_p = 0
    else:
        front_p = clean_val(GLOBAL_SETTINGS.get('cena_pleksy_m2', 0)) if is_pleksa else get_smart_val('cena_szkla_m2')
        back_p = get_smart_val('cena_tylow_m2')
        clip_p = clean_val(GLOBAL_SETTINGS.get('cena_spinki', 0))
        hook_p = clean_val(GLOBAL_SETTINGS.get('cena_zaczep', 0))
        alu_kit_p = clean_val(GLOBAL_SETTINGS.get('montaz_alu', 0))

    pp_p = clean_val(GLOBAL_SETTINGS.get('cena_pp_m2', 0))
    vat = get_smart_val('vat') or 23
    
    if is_antyrama: 
        m_key = 'marza_pleksa_hurt' if is_pleksa else 'marza_anty_hurt'
    elif is_alu: 
        m_key = 'marza_alu_hurt'
    elif is_plastik:
        m_key = 'marza_TS'
    else: 
        m_key = 'marza_hurt'
    
    base_margin = clean_val(profile.get(m_key, 0)) or clean_val(GLOBAL_SETTINGS.get(m_key, 0))
    
    if is_sama_rama:
        label = f"SAMA RAMA: {profile['nazwa']}"
    else:
        label = f"ANTYRAMA {front_type.upper()}" if is_antyrama else (f"ALU: {profile['nazwa']}" if is_alu else f"RAMA {main_category.upper()}: {profile['nazwa']}")
    
    results = []
    for name, config in FORMATS_CONFIG.items():
        w, h, s_cat, p_cat, s_count, z_count = config
        len_m, area_m2 = (2*(w+h) + FRAME_MARGIN*s_width)/100, (w*h)/10000
        c_surowiec = (area_m2 * front_p) + (area_m2 * back_p)
        
        if is_antyrama: 
            if not is_sama_rama: c_surowiec += (s_count * clip_p) + (z_count * hook_p)
            else: c_surowiec = 0
        elif is_alu: 
            c_surowiec += (len_m * s_price) + alu_kit_p
        else: 
            c_surowiec += (len_m * s_price)
            if not is_sama_rama:
                c_surowiec += (get_smart_val(f'cena_podporka_{s_cat}') if s_cat else 0)
        
        if with_pp and not is_sama_rama: c_surowiec += (area_m2 * pp_p)
        
        base_labor = 0 if is_antyrama else (get_smart_val(f'koszt_prod_{p_cat}') if p_cat else 0)
        saved_data = MARGIN_EXCEPTIONS.get(f"{mode}_{label}_{name}", {})
        active_margin = saved_data.get("m", base_margin)
        active_labor = saved_data.get("l", base_labor) if saved_data.get("l") is not None else base_labor
        
        total_cost = c_surowiec + active_labor
        div = (1 - (active_margin / 100))
        net = total_cost / div if div != 0 else total_cost
        
        results.append({"size": name, "net": f"{net:.2f}", "gross": f"{(net * (1 + vat/100)):.2f}", "surowiec": f"{c_surowiec:.2f}", "labor": f"{active_labor:.2f}", "profit": f"{(net - total_cost):.2f}", "active_margin": f"{active_margin:.1f}"})
        
    # Tworzymy odpowiedź
    response = templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, "results": results, "profile": label, "profile_raw_name": profile.get("nazwa"), 
        "mode": mode, "is_admin": is_admin, "profiles": [{"nazwa": item.get('nazwa'), "kat": item.get('kategoria', 'brak')} for item in CACHED_DATA if item.get('nazwa')], 
        "main_category": main_category, "front_type": front_type, "with_pp": with_pp, 
        "selected_profile": profile_name, "vat": vat, 
        # BEZPIECZEŃSTWO: Nie wstrzykujemy już "admin_password" do HTML!
        "przekroj_img": przekroj_img, "description": description
    })
    
    # BEZPIECZEŃSTWO: Ustawiamy bezpieczne ciasteczko logowania na 1 godzinę (3600 sekund)
    if is_admin:
        response.set_cookie(key="admin_auth", value=get_auth_token(), httponly=True, max_age=3600, samesite="Lax")
    
    return response

@app.post("/save_margins")
async def save_margins(request: Request):
    try:
        # BEZPIECZEŃSTWO: Weryfikacja tożsamości odbywa się teraz przez zaszyfrowane ciasteczko
        auth_cookie = request.cookies.get("admin_auth")
        if auth_cookie != get_auth_token():
            return JSONResponse({"success": False, "error": "Brak autoryzacji. Zaloguj się ponownie wpisując hasło i klikając Oblicz."})
            
        data = await request.json()
        
        env_creds = os.environ.get("GOOGLE_CREDENTIALS")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(env_creds), scope) if env_creds else ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        wb = client.open("Baza Ramek")
        ws = wb.worksheet("Wyjatki_Marze")
        all_data = ws.get_all_values()
        header = ["Tryb", "Produkt", "Format", "Marza", "Robocizna"]
        existing = {f"{r[0]}_{r[1]}_{r[2]}": r for r in all_data[1:] if len(r) >= 3} if all_data else {}
        for u in data.get("updates", []): 
            existing[f"{u['mode']}_{u['profile']}_{u['size']}"] = [u['mode'], u['profile'], u['size'], str(u['margin']), str(u['labor'])]
        ws.clear(); ws.update(values=[header] + list(existing.values()), range_name='A1')
        if data.get("profile_raw_name"):
            main_ws = wb.sheet1
            main_rows = main_ws.get_all_values()
            headers = [h.strip() for h in main_rows[0]]
            try:
                img_col = headers.index("link_zdjecie") + 1
                desc_col = headers.index("Opis_Dodatkowy") + 1
                for i, row in enumerate(main_rows[1:], start=2):
                    if row[0] == data["profile_raw_name"]:
                        main_ws.update_cell(i, img_col, data.get("new_img", ""))
                        main_ws.update_cell(i, desc_col, data.get("new_desc", ""))
                        break
            except: pass
        fetch_data()
        return JSONResponse({"success": True})
    except Exception as e: return JSONResponse({"success": False, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)