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
if "email_results" not in st.session_state:
    st.session_state.email_results = {}

# --- 3. ESTILOS CSS PROFESIONALES ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #f4f7f6; color: #333;}

    /* Títulos */
    h1 {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        text-align: center;
        padding-top: 1rem;
    }

    /* Tarjetas */
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

    /* Footer */
    .footer-credits {
        text-align: center; margin-top: 50px; padding: 20px;
        border-top: 1px solid #ddd; font-size: 0.85em; color: #666;
    }
    .footer-credits a {color: #1c3961; font-weight: bold; text-decoration: none;}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: white;
        border-radius: 5px 5px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1c3961; color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES DE USUARIO (WHATS MY NAME) ---
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

# ... (Aquí van tus extractores anteriores: Telegram, GitHub, etc. Mantenlos igual) ...
# Para ahorrar espacio en la respuesta, asumo que usas las mismas funciones extract_telegram, extract_github, etc.
# Si necesitas que las repita, avísame. Usaré una versión simplificada aquí.

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
        
        # Extracción básica para el ejemplo
        details, image = extract_generic_meta(uri)
        
        if not image:
            domain = uri.split('/')[2]
            image = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

        return {
            "name": site['name'], "uri": uri, "category": site['cat'],
            "image": image, "details": details
        }
    except:
        return None

# --- 5. NUEVO MÓDULO DE CORREO ---
def analyze_email(email):
    results = {}
    
    # 1. Validación de Formato
    try:
        v = validate_email(email)
        email = v["email"]
        results['valid_format'] = True
        results['normalized'] = email
    except EmailNotValidError as e:
        return {'valid_format': False, 'error': str(e)}

    domain = email.split('@')[1]
    username_part = email.split('@')[0]
    results['domain'] = domain
    results['username_part'] = username_part

    # 2. Validación DNS (MX Records)
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        results['mx_records'] = [str(x.exchange) for x in mx_records]
        results['has_mail_server'] = True
    except:
        results['has_mail_server'] = False
        results['mx_records'] = []

    # 3. Gravatar Check
    gravatar_url = f"https://en.gravatar.com/{username_part}.json" # A veces funciona por usuario
    # Nota: Gravatar real usa MD5 del email, implementémoslo correctamente
    import hashlib
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    gravatar_hash_url = f"https://en.gravatar.com/{email_hash}.json"
    
    try:
        r = requests.get(gravatar_hash_url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()['entry'][0]
            results['gravatar'] = {
                'found': True,
                'profile': data.get('profileUrl'),
                'image': data.get('thumbnailUrl'),
                'name': data.get('displayName'),
                'location': data.get('currentLocation')
            }
        else:
            results['gravatar'] = {'found': False}
    except:
        results['gravatar'] = {'found': False}

    return results

# --- 6. GENERADORES DE ARCHIVOS ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_files(results, target):
    # CSV
    df = pd.DataFrame(results)
    csv = df.drop(columns=['details', 'image'], errors='ignore').to_csv(index=False).encode('utf-8')
    
    # PDF
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, clean_text(f"Reporte OSINT: {target}"), ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", size=9)
        for item in results:
            pdf.cell(0, 10, clean_text(f"{item['name']} - {item['uri']}"), ln=1)
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except:
        pdf_bytes = None
        
    return csv, pdf_bytes

# --- 7. INTERFAZ PRINCIPAL ---

# Sidebar
with st.sidebar:
    try:
        st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    except:
        st.header("ManuelBot59")
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.markdown("### 📞 Soporte")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")

# Header
st.markdown("<h1 class='main-title'>ManuelBot59 Suite OSINT</h1>", unsafe_allow_html=True)

# SISTEMA DE PESTAÑAS
tab1, tab2 = st.tabs(["👤 Búsqueda de Usuario", "📧 Análisis de Correo"])

# --- PESTAÑA 1: USUARIOS (Tu código anterior optimizado) ---
with tab1:
    st.markdown("### 🔎 Rastreador de Huella Digital")
    
    sites = load_sites()
    categories = sorted(list(set([s['cat'] for s in sites])))
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        username = st.text_input("Usuario", placeholder="Ej: manuelbot59", key="user_input")
    with c2:
        cat_filter = st.selectbox("Categoría", ["Todas"] + categories, key="cat_input")
    with c3:
        run_user_btn = st.button("INVESTIGAR", type="primary", key="btn_user")

    user_container = st.container()

    if run_user_btn and username:
        st.session_state.results = []
        target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
        
        prog_bar = st.progress(0)
        status_text = st.empty()
        processed = 0
        
        with user_container:
            grid_dynamic = st.empty()
        
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
                    with grid_dynamic.container():
                        cols = st.columns(2)
                        for i, item in enumerate(st.session_state.results):
                            with cols[i % 2]:
                                with st.container(border=True):
                                    cc1, cc2 = st.columns([1, 4])
                                    with cc1: st.image(item['image'], width=40)
                                    with cc2:
                                        st.markdown(f"**{item['name']}**")
                                        st.caption(item['category'])
                                        st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                                    
                                    if item.get('details'):
                                        with st.expander("Detalles"):
                                            st.write(item['details'])

        prog_bar.progress(100)
        if st.session_state.results:
            st.success(f"Encontrados: {len(st.session_state.results)}")
            csv, pdf = generate_files(st.session_state.results, username)
            st.download_button("Descargar CSV", csv, f"{username}.csv")

# --- PESTAÑA 2: CORREOS (NUEVO MÓDULO) ---
with tab2:
    st.markdown("### 📧 Inteligencia de Correo Electrónico")
    st.info("Este módulo realiza un análisis técnico y busca perfiles públicos asociados al correo (Gravatar). No realiza intrusión ni usa bases de datos filtradas.")
    
    email_input = st.text_input("Ingresa el correo electrónico", placeholder="ejemplo@gmail.com")
    run_email_btn = st.button("ANALIZAR CORREO", type="primary")
    
    if run_email_btn and email_input:
        with st.spinner("Realizando análisis técnico..."):
            data = analyze_email(email_input)
            st.session_state.email_results = data
            
        if not data['valid_format']:
            st.error(f"Formato inválido: {data.get('error')}")
        else:
            # 1. Resultados Técnicos
            c_tech, c_social = st.columns(2)
            
            with c_tech:
                st.markdown("#### 🛠️ Análisis Técnico")
                st.success("✅ Formato Válido")
                
                if data['has_mail_server']:
                    st.success(f"✅ Servidor de Correo Activo (MX)")
                    with st.expander("Ver Registros MX"):
                        for mx in data['mx_records']:
                            st.code(mx)
                else:
                    st.error("❌ No tiene servidor de correo (Dominio inactivo o falso)")
                
                st.markdown(f"**Proveedor:** {data['domain'].upper()}")
                st.markdown(f"**Posible Usuario:** `{data['username_part']}`")

            # 2. Resultados Sociales (Gravatar)
            with c_social:
                st.markdown("#### 👤 Identidad Pública")
                if data['gravatar']['found']:
                    st.success("✅ Perfil Gravatar Detectado")
                    col_grav_img, col_grav_info = st.columns([1, 2])
                    with col_grav_img:
                        st.image(data['gravatar']['image'], width=100)
                    with col_grav_info:
                        st.markdown(f"**Nombre:** {data['gravatar']['name']}")
                        st.markdown(f"**Ubicación:** {data['gravatar']['location']}")
                        st.link_button("Ver Perfil Gravatar", data['gravatar']['profile'])
                else:
                    st.warning("⚠️ No se encontró perfil público en Gravatar.")

            st.divider()
            
            # 3. CORRELACIÓN (MAGIA)
            st.subheader("🔄 Correlación de Usuario")
            st.markdown(f"¿Quieres buscar presencias del usuario **{data['username_part']}** en otras redes?")
            
            # Botón que simula ir a la pestaña 1
            if st.button(f"🔎 Buscar '{data['username_part']}' en 700+ sitios"):
                # Aquí podrías guardar el usuario en session_state y pedir al usuario cambiar de tab
                st.info(f"Ve a la pestaña 'Búsqueda de Usuario' e ingresa: {data['username_part']}")

# Footer
st.markdown("""
<div class="footer-credits">
    Suite OSINT desarrollada por <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a><br>
    Powered by WhatsMyName & DNSPython
</div>
""", unsafe_allow_html=True)