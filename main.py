import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from bs4 import BeautifulSoup
import dns.resolver
from email_validator import validate_email, EmailNotValidError
import urllib.parse
from datetime import datetime
import time

# Importamos socid-extractor
try:
    from socid_extractor import extract as socid_extract
except ImportError:
    socid_extract = None

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="ManuelBot59 | Suite OSINT",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE ESTADO ---
if "results" not in st.session_state:
    st.session_state.results = []
if "search_active" not in st.session_state:
    st.session_state.search_active = False

# --- 3. ESTILOS CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #f4f7f6; color: #333;}

    h1 {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        text-align: center;
        padding-top: 1rem;
    }

    /* Tarjetas de Resultados */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        border-left: 5px solid #27ae60;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        border-color: #00c6fb;
    }

    .site-title { font-size: 1.1rem; font-weight: 700; color: #1c3961; }
    .site-cat { font-size: 0.8rem; color: #64748b; background-color: #f1f5f9; padding: 2px 8px; border-radius: 12px; }

    /* Footer */
    .footer-credits {
        text-align: center; margin-top: 50px; padding: 20px;
        border-top: 1px solid #ddd; font-size: 0.85em; color: #666;
    }
    .footer-credits a {color: #1c3961; font-weight: bold; text-decoration: none;}
</style>
""", unsafe_allow_html=True)

# --- 4. MOTORES DE EXTRACCIÓN ---
def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def extract_telegram(username):
    try:
        r = requests.get(f"https://t.me/{username}", headers=get_headers(), timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        image = soup.find("meta", property="og:image")
        title = soup.find("meta", property="og:title")
        desc = soup.find("meta", property="og:description")
        
        details = {}
        img_url = None
        if title:
            name_raw = title.get("content", "").replace("Telegram: Contact @", "")
            details["Nombre Visible"] = name_raw.split(" - ")[0]
        if desc: details["Biografía"] = desc.get("content", "")
        if image: img_url = image.get("content")
        return details, img_url
    except:
        return {}, None

# --- EXTRACTOR GITLAB (MANTENIDO JSON) ---
def extract_gitlab(username):
    try:
        r = requests.get(f"https://gitlab.com/api/v4/users?username={username}", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data_list = r.json()
            if data_list and len(data_list) > 0:
                user = data_list[0]
                details = {
                    "ID": user.get("id"),
                    "Username": user.get("username"),
                    "Nombre": user.get("name"),
                    "Estado": user.get("state"),
                    "Email Público": user.get("public_email", "Oculto"),
                    "Web URL": user.get("web_url")
                }
                return {k: v for k, v in details.items() if v}, user.get("avatar_url")
    except:
        pass
    return {}, None

# --- EXTRACTOR GITHUB (RESTAURADO PARA API) ---
def extract_github(username):
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Mapeo exacto de los campos solicitados
            details = {
                "ID": data.get("id"),
                "Node ID": data.get("node_id"),
                "Tipo": data.get("type"),
                "Nombre": data.get("name"),
                "Empresa": data.get("company"),
                "Blog": data.get("blog"),
                "Ubicación": data.get("location"),
                "Email": data.get("email"),
                "Bio": data.get("bio"),
                "Twitter": data.get("twitter_username"),
                "Repos Públicos": data.get("public_repos"),
                "Seguidores": data.get("followers"),
                "Siguiendo": data.get("following"),
                "Creado": data.get("created_at"),
                "Actualizado": data.get("updated_at")
            }
            return {k: v for k, v in details.items() if v}, data.get("avatar_url")
    except:
        pass
    return {}, None

def extract_gravatar(username):
    try:
        r = requests.get(f"https://en.gravatar.com/{username}.json", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()['entry'][0]
            return {"Nombre": data.get("displayName"), "Ubicación": data.get("currentLocation")}, data.get("thumbnailUrl")
    except:
        pass
    return {}, None

def extract_generic_meta(url):
    try:
        r = requests.get(url, headers=get_headers(), timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        details = {}
        image = None
        if soup.title: details["Título"] = soup.title.string.strip()[:50]
        img = soup.find("meta", property="og:image")
        if img: image = img.get("content")
        return details, image
    except:
        return {}, None

# --- LÓGICA DE DETECCIÓN ---
def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    
    # 1. Validación de existencia
    try:
        r = requests.get(uri, headers=get_headers(), timeout=6)
        if r.status_code != site['e_code']: return None
        if site.get('e_string') and site['e_string'] not in r.text: return None
    except:
        return None

    details = {}
    image_url = None
    site_name = site['name'].lower()
    
    # Enrutamiento (AQUÍ ESTABA EL ERROR DE GITHUB FALTANTE)
    if "telegram" in site_name: 
        details, image_url = extract_telegram(username)
    elif "gitlab" in site_name: 
        details, image_url = extract_gitlab(username)
    elif "github" in site_name:  # <--- RESTAURADO
        details, image_url = extract_github(username)
    elif "gravatar" in site_name: 
        details, image_url = extract_gravatar(username)
    else:
        # Genérico + Socid
        details, image_url = extract_generic_meta(uri)
        if not details and socid_extract:
            try:
                data = socid_extract(uri)
                if data:
                    details = {k: v for k, v in data.items() if v and k != 'image'}
                    image_url = data.get('image')
            except: pass

    # Fallback de imagen
    if not image_url:
        try:
            domain = uri.split('/')[2]
            image_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
        except: 
            image_url = "https://via.placeholder.com/128?text=Found"

    return {
        "name": site['name'],
        "uri": uri,
        "category": site['cat'],
        "image": image_url,
        "details": details
    }

# --- 5. MÓDULO DE CORREO ---
def analyze_email(email):
    results = {}
    try:
        v = validate_email(email)
        email = v["email"]
        results['valid_format'] = True
    except EmailNotValidError as e: return {'valid_format': False, 'error': str(e)}

    domain = email.split('@')[1]
    username_part = email.split('@')[0]
    results['domain'], results['username_part'] = domain, username_part

    try:
        mx = dns.resolver.resolve(domain, 'MX')
        results['has_mail_server'] = True
    except: results['has_mail_server'] = False

    import hashlib
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    try:
        r = requests.get(f"https://en.gravatar.com/{email_hash}.json", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()['entry'][0]
            results['gravatar'] = {'found': True, 'profile': data.get('profileUrl'), 'image': data.get('thumbnailUrl'), 'name': data.get('displayName'), 'location': data.get('currentLocation')}
        else: results['gravatar'] = {'found': False}
    except: results['gravatar'] = {'found': False}

    try:
        r = requests.get(f"https://www.duolingo.com/2017-06-30/users?email={email}", headers=get_headers(), timeout=5)
        if r.status_code == 200 and r.json()['users']:
            user = r.json()['users'][0]
            results['duolingo'] = {"image": user.get("picture") + "/xxlarge" if user.get("picture") else None, "username": user.get("username"), "learning": [c['title'] for c in user.get("courses", [])]}
    except: pass

    return results

# --- 6. GENERADORES DE ARCHIVOS ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
APP_URL = "https://whatsmyname.streamlit.app/"

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

# Clase PDF personalizada
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, clean_text('Reporte SOCMINT - WhatsMyName Web'), 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, clean_text('Herramienta: WhatsMyName Web | Autor: Manuel Travezaño'), 0, 1, 'C')
        self.set_text_color(0, 0, 255)
        self.cell(0, 5, APP_URL, 0, 1, 'C', link=APP_URL)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_files(results, target):
    # Timestamp con Zona Horaria Local
    now = datetime.now().astimezone() 
    timestamp_display = now.strftime("%d/%m/%Y %H:%M:%S (GMT%z)")
    timestamp_filename = now.strftime("%Y%m%d_%H%M%S")

    # 1. CSV
    df = pd.DataFrame(results)
    df['fecha_extraccion'] = timestamp_display
    csv = df.drop(columns=['details', 'image'], errors='ignore').to_csv(index=False).encode('utf-8')
    
    # 2. TXT
    txt = io.StringIO()
    txt.write(f"REPORTE DE INVESTIGACION - USUARIO: {target}\n")
    txt.write(f"Fecha de Extraccion: {timestamp_display}\n")
    txt.write(f"Herramienta: {APP_URL}\n")
    txt.write("="*60 + "\n\n")
    for item in results:
        txt.write(f"Plataforma: {item['name']}\n")
        txt.write(f"URL: {item['uri']}\n")
        if item.get('details'):
            for k, v in item['details'].items():
                txt.write(f"  - {k}: {v}\n")
        txt.write("-" * 20 + "\n")
    
    # 3. PDF
    pdf_bytes = None
    try:
        pdf = PDFReport() 
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        pdf.cell(0, 10, clean_text(f"Objetivo: {target}"), ln=1)
        pdf.cell(0, 10, clean_text(f"Fecha: {timestamp_display}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(10)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(50, 8, clean_text("Plataforma"), 1, 0, 'L', 1)
        pdf.cell(40, 8, clean_text("Categoría"), 1, 0, 'L', 1)
        pdf.cell(100, 8, clean_text("Enlace"), 1, 1, 'L', 1)
        
        pdf.set_font("Arial", size=9)
        for item in results:
            name = clean_text(item['name'][:25])
            cat = clean_text(item['category'][:20])
            
            pdf.cell(50, 8, name, 1)
            pdf.cell(40, 8, cat, 1)
            
            pdf.set_text_color(0, 0, 255)
            pdf.cell(100, 8, clean_text("Enlace al perfil"), 1, 0, link=item['uri'])
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e:
        print(f"Error PDF: {e}")
        pdf_bytes = None
        
    return csv, txt.getvalue(), pdf_bytes, timestamp_filename

# --- 7. INTERFAZ ---
@st.cache_data
def load_sites():
    try: return requests.get(WMN_DATA_URL).json()['sites']
    except: return []

with st.sidebar:
    try: st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    except: st.header("ManuelBot59")
    st.markdown("### 📌 Navegación")
    st.markdown("""
    - [🏠 Inicio](https://manuelbot59.com/)
    - [🕵️ OSINT](https://manuelbot59.com/osint/)
    """)
    st.markdown("---")
    st.markdown("### 📞 Soporte")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")

st.markdown("<h1 class='main-title'>ManuelBot59 Suite OSINT</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["👤 Búsqueda de Usuario", "📧 Análisis de Correo"])

# TAB 1: USUARIOS
with tab1:
    st.markdown("### 🔎 Rastreador de Huella Digital")
    progress_placeholder = st.empty()
    
    sites = load_sites()
    categories = sorted(list(set([s['cat'] for s in sites])))
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: username = st.text_input("Usuario", placeholder="Ej: manuelbot59", key="u_in")
    with c2: cat_filter = st.selectbox("Categoría", ["Todas"] + categories, key="c_in")
    with c3: run_user = st.button("INVESTIGAR", type="primary", key="b_u")

    user_res_container = st.container()

    if run_user and username:
        st.session_state.results = []
        target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
        
        with progress_placeholder.container():
            prog_bar = st.progress(0)
            status_text = st.empty()
        
        processed = 0
        with user_res_container:
            grid_dynamic = st.empty()
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(check_site, s, username): s for s in target_sites}
            for future in as_completed(futures):
                res = future.result()
                processed += 1
                if processed % 5 == 0 or processed == len(target_sites):
                    prog_bar.progress(processed / len(target_sites))
                    status_text.caption(f"Verificando: {processed}/{len(target_sites)}")
                
                if res:
                    st.session_state.results.append(res)
                    with grid_dynamic.container():
                        cols = st.columns(2)
                        for i, item in enumerate(st.session_state.results):
                            with cols[i % 2]:
                                with st.container(border=True):
                                    cc1, cc2 = st.columns([1, 4])
                                    with cc1: st.image(item['image'], width=40)
                                    with cc2:
                                        st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                                        st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                                        st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                                        
                                        # ELIMINADO EL TEXTO URL DUPLICADO
                                        # Solo se muestra el botón y si hay detalles, el expander.
                                    
                                    if item.get('details'):
                                        with st.expander("👁️ Ver Detalles Extraídos"):
                                            dc1, dc2 = st.columns([1, 2])
                                            with dc1:
                                                st.image(item['image'], use_column_width=True, caption="Perfil")
                                            with dc2:
                                                for k, v in item['details'].items():
                                                    st.markdown(f"**{k}:** {v}")
        
        prog_bar.progress(100)
    
    if st.session_state.results:
        st.divider()
        st.subheader("📥 Exportar Reporte")
        csv, txt, pdf, ts_filename = generate_files(st.session_state.results, username)
        
        d1, d2, d3 = st.columns(3)
        with d1: 
            st.download_button("📄 Descargar CSV", csv, f"{username}_{ts_filename}.csv", "text/csv", use_container_width=True)
        with d2: 
            st.download_button("📝 Descargar TXT", txt, f"{username}_{ts_filename}.txt", "text/plain", use_container_width=True)
        with d3:
            if pdf: 
                st.download_button("📕 Descargar PDF", pdf, f"{username}_{ts_filename}.pdf", "application/pdf", use_container_width=True)
            else: 
                st.warning("PDF no disponible")

# TAB 2: CORREOS
with tab2:
    st.markdown("### 📧 Inteligencia de Correo")
    email_in = st.text_input("Correo electrónico", placeholder="ejemplo@gmail.com")
    run_email = st.button("ANALIZAR CORREO", type="primary")
    
    if run_email and email_in:
        with st.spinner("Analizando..."):
            data = analyze_email(email_in)
        
        if not data['valid_format']: st.error("Formato inválido")
        else:
            c_t, c_s = st.columns(2)
            with c_t:
                st.info(f"Dominio: {data['domain'].upper()}")
                if data['has_mail_server']: st.success("✅ Servidor MX Activo")
            with c_s:
                if data['gravatar']['found']:
                    st.success("✅ Gravatar Detectado")
                    g = data['gravatar']
                    st.image(g['image'], width=80)
                    st.write(f"**Nombre:** {g['name']}")
                
                if data.get('duolingo'):
                    st.success("✅ Duolingo Detectado")
                    d = data['duolingo']
                    if d['image']: st.image(d['image'], width=80)
                    st.write(f"**User:** {d['username']}")

            st.divider()
            st.markdown("### 👣 Huellas Digitales")
            encoded_email = urllib.parse.quote(email_in)
            
            links = [
                ("Duolingo", f"https://www.duolingo.com/2017-06-30/users?email={email_in}"),
                ("Spotify", f"https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email_in}"),
                ("Twitter", f"https://api.twitter.com/i/users/email_available.json?email={email_in}"),
                ("HaveIBeenPwned", f"https://haveibeenpwned.com/account/{email_in}"),
                ("Intelx", f"https://intelx.io/?s={encoded_email}"),
                ("GitHub Commits", f"https://github.com/search?q=committer-email:{email_in}&type=commits")
            ]
            
            lc = st.columns(4)
            for i, (name, url) in enumerate(links):
                with lc[i % 4]: st.link_button(f"🔎 {name}", url, use_container_width=True)

# Footer Actualizado
st.markdown("""
<div class="footer-credits">
    OSINT Suite developed by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a><br>
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a>, 
    <a href="https://github.com/soxoj/socid-extractor" target="_blank">socid-extractor</a> & 
    <a href="https://www.dnspython.org/" target="_blank">DNSPython</a>
</div>
""", unsafe_allow_html=True)