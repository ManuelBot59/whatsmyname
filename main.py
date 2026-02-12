import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from bs4 import BeautifulSoup
import dns.resolver
import re
from email_validator import validate_email, EmailNotValidError
import urllib.parse

# Importamos socid-extractor como respaldo
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
    
    /* Botones de Enlace Email */
    .email-link-btn {
        text-decoration: none; color: #333; display: block;
        padding: 8px; border-radius: 5px; background: white;
        border: 1px solid #ddd; margin-bottom: 5px; font-size: 0.9rem;
        transition: all 0.2s;
    }
    .email-link-btn:hover {
        background: #f0f9ff; border-color: #00c6fb; color: #00c6fb;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. MOTORES DE USUARIO ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
APP_URL = "https://whatsmyname.streamlit.app/"

@st.cache_data
def load_sites():
    try:
        response = requests.get(WMN_DATA_URL)
        data = response.json()
        return data['sites']
    except:
        return []

def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# ... (Extractores anteriores mantenidos simplificados para el ejemplo) ...
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

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        r = requests.get(uri, headers=get_headers(), timeout=6)
        if r.status_code != site['e_code']: return None
        if site.get('e_string') and site['e_string'] not in r.text: return None
        
        details, image = extract_generic_meta(uri)
        if not image:
            domain = uri.split('/')[2]
            image = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

        return {"name": site['name'], "uri": uri, "category": site['cat'], "image": image, "details": details}
    except:
        return None

# --- 5. MOTORES DE CORREO AVANZADOS ---

def check_duolingo_json(email):
    """Extrae datos reales del JSON de Duolingo"""
    try:
        url = f"https://www.duolingo.com/2017-06-30/users?email={email}"
        r = requests.get(url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "users" in data and len(data["users"]) > 0:
                user = data["users"][0]
                return {
                    "found": True,
                    "platform": "Duolingo",
                    "username": user.get("username"),
                    "name": user.get("name"),
                    "bio": user.get("bio"),
                    "location": user.get("location"),
                    "learning": [course['title'] for course in user.get("courses", [])],
                    "image": user.get("picture") + "/xxlarge" if user.get("picture") else None
                }
    except:
        pass
    return None

def analyze_email(email):
    results = {}
    
    # 1. Validación Formato
    try:
        v = validate_email(email)
        email = v["email"]
        results['valid_format'] = True
    except EmailNotValidError as e:
        return {'valid_format': False, 'error': str(e)}

    domain = email.split('@')[1]
    username_part = email.split('@')[0]
    results['domain'] = domain
    results['username_part'] = username_part

    # 2. DNS
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        results['mx_records'] = [str(x.exchange) for x in mx_records]
        results['has_mail_server'] = True
    except:
        results['has_mail_server'] = False
        results['mx_records'] = []

    # 3. Gravatar
    import hashlib
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    gravatar_url = f"https://en.gravatar.com/{email_hash}.json"
    
    try:
        r = requests.get(gravatar_url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()['entry'][0]
            results['gravatar'] = {
                'found': True, 'profile': data.get('profileUrl'),
                'image': data.get('thumbnailUrl'), 'name': data.get('displayName'),
                'location': data.get('currentLocation')
            }
        else:
            results['gravatar'] = {'found': False}
    except:
        results['gravatar'] = {'found': False}

    # 4. Duolingo (JSON Extraction)
    results['duolingo'] = check_duolingo_json(email)

    return results

# --- 6. GENERADORES ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_files(results, target):
    df = pd.DataFrame(results)
    csv = df.drop(columns=['details', 'image'], errors='ignore').to_csv(index=False).encode('utf-8')
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, clean_text(f"Reporte: {target}"), ln=1)
        pdf.ln(5)
        for item in results:
            pdf.cell(0, 10, clean_text(f"{item['name']} - {item['uri']}"), ln=1)
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except:
        pdf_bytes = None
    return csv, pdf_bytes

# --- 7. INTERFAZ ---
with st.sidebar:
    try:
        st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    except:
        st.header("ManuelBot59")
    st.markdown("### 📌 Navegación")
    st.markdown("""
    - [🏠 Inicio](https://manuelbot59.com/)
    - [🎓 Cursos](https://manuelbot59.com/formacion/)
    - [🛒 Tienda](https://manuelbot59.com/tienda/)
    - [🕵️ OSINT](https://manuelbot59.com/osint/)
    """)
    st.markdown("---")
    st.markdown("### 📞 Soporte")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")

st.markdown("<h1 class='main-title'>ManuelBot59 Suite OSINT</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["👤 Búsqueda de Usuario", "📧 Análisis de Correo"])

# --- TAB 1: USUARIOS ---
with tab1:
    st.markdown("### 🔎 Rastreador de Huella Digital")
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
        prog_bar = st.progress(0)
        status_text = st.empty()
        
        with user_res_container:
            grid = st.empty()
        
        processed = 0
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(check_site, s, username): s for s in target_sites}
            for future in as_completed(futures):
                res = future.result()
                processed += 1
                if processed % 10 == 0:
                    prog_bar.progress(processed / len(target_sites))
                    status_text.caption(f"Verificando: {processed}/{len(target_sites)}")
                
                if res:
                    st.session_state.results.append(res)
                    with grid.container():
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
                                    if item.get('details'):
                                        with st.expander("Detalles"):
                                            st.write(item['details'])
        prog_bar.progress(100)

# --- TAB 2: CORREOS (NUEVO + HUELLAS DIGITALES) ---
with tab2:
    st.markdown("### 📧 Inteligencia de Correo")
    email_in = st.text_input("Correo electrónico", placeholder="ejemplo@gmail.com")
    run_email = st.button("ANALIZAR CORREO", type="primary")
    
    if run_email and email_in:
        with st.spinner("Analizando..."):
            data = analyze_email(email_in)
        
        if not data['valid_format']:
            st.error("Formato de correo inválido")
        else:
            # Resultados Técnicos
            c_tech, c_soc = st.columns(2)
            with c_tech:
                st.info(f"**Dominio:** {data['domain'].upper()}")
                if data['has_mail_server']:
                    st.success("✅ Servidor de Correo Activo (MX)")
                else:
                    st.error("❌ Dominio sin servidor de correo")
            
            # Resultados Sociales (Gravatar & Duolingo)
            with c_soc:
                # Gravatar
                if data['gravatar']['found']:
                    st.success("✅ Gravatar Detectado")
                    col_g1, col_g2 = st.columns([1, 3])
                    with col_g1: st.image(data['gravatar']['image'], width=80)
                    with col_g2:
                        st.write(f"**Nombre:** {data['gravatar']['name']}")
                        st.write(f"**Loc:** {data['gravatar']['location']}")
                
                # Duolingo (Extraído de JSON)
                if data.get('duolingo'):
                    duo = data['duolingo']
                    st.success("✅ Cuenta Duolingo Detectada")
                    col_d1, col_d2 = st.columns([1, 3])
                    with col_d1: 
                        if duo['image']: st.image(duo['image'], width=80)
                    with col_d2:
                        st.write(f"**Usuario:** {duo['username']}")
                        st.write(f"**Idiomas:** {', '.join(duo['learning'])}")
            
            st.divider()
            st.markdown("### 👣 Huellas Digitales (Enlaces de Verificación)")
            st.info("Haz clic en estos enlaces para verificar manualmente la existencia de la cuenta (Algunos pueden requerir login).")
            
            # LISTA DE ENLACES SOLICITADA
            encoded_email = urllib.parse.quote(email_in)
            username_part = email_in.split('@')[0]
            
            links_map = [
                ("Duolingo (JSON)", f"https://www.duolingo.com/2017-06-30/users?email={email_in}"),
                ("Chess.com", f"https://www.chess.com/callback/email/available?email={email_in}"),
                ("Spotify (Google Cache)", f"https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email_in}"),
                ("Strava", f"https://www.strava.com/athletes/email_unique?email={email_in}"),
                ("Twitter API", f"https://api.twitter.com/i/users/email_available.json?email={email_in}"),
                ("Netshoes", f"https://www.netshoes.com.br/auth/account/exists/{email_in}"),
                ("XVideos", f"https://www.xvideos.com/account/checkemail?email={email_in}"),
                ("PicsArt API", f"https://api.picsart.com/users/email/existence?email_encoded=0&emails={email_in}"),
                ("Google CSE", f"https://cse.google.com/cse?cx=d69e08526637c468d#gsc.tab=0&gsc.q={email_in}"),
                ("ViewDNS Reverse", f"https://viewdns.info/reversewhois/?q={email_in}"),
                ("MySpace", f"https://myspace.com/search/people?q={email_in}"),
                ("Whoisology", f"https://whoisology.com/email/{email_in}/1"),
                ("ProtonMail API", f"https://api.protonmail.ch/pks/lookup?op=get&search={email_in}"),
                ("Hunter.io", f"https://hunter.io/email-verifier/{email_in}"),
                ("Intelx", f"https://intelx.io/?s={encoded_email}"),
                ("GitHub Commits", f"https://github.com/search?q=committer-email:{email_in}+author-email:{email_in}&type=commits"),
                ("Gmail OSINT", f"https://gmail-osint.activetk.jp/{username_part}"),
                ("2IP (Breach Check)", f"https://2ip.ru/?area=ajaxHaveIBeenPwned&query={email_in}"),
                ("Pastebin Dump", f"https://psbdmp.ws/api/search/email/{email_in}")
            ]
            
            # Renderizado de enlaces en 4 columnas
            cols_links = st.columns(4)
            for i, (name, url) in enumerate(links_map):
                with cols_links[i % 4]:
                    st.link_button(f"🔎 {name}", url, use_container_width=True)

# Footer
st.markdown("""
<div class="footer-credits">
    Suite OSINT desarrollada por <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a><br>
    Powered by WhatsMyName & DNSPython
</div>
""", unsafe_allow_html=True)