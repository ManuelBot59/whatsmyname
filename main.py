import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from bs4 import BeautifulSoup

# Importamos socid-extractor como respaldo
try:
    from socid_extractor import extract as socid_extract
except ImportError:
    socid_extract = None

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
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

    .stApp {
        background-color: #f4f7f6;
        color: #333;
    }

    h1 {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        text-align: center;
        padding-top: 1rem;
    }

    /* TARJETA HIPPIE STYLE MEJORADA */
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

    .site-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1c3961;
        margin-bottom: 2px;
    }
    .site-cat {
        font-size: 0.8rem;
        color: #64748b;
        background-color: #f1f5f9;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-block;
        margin-bottom: 10px;
    }

    /* Footer */
    .footer-credits {
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #ddd;
        font-size: 0.85em;
        color: #666;
    }
    .footer-credits a {
        color: #1c3961;
        font-weight: bold;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. MOTORES DE EXTRACCIÓN PERSONALIZADOS ---

def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# A. Extractor de Telegram (Metadata Scraping)
def extract_telegram(username):
    url = f"https://t.me/{username}"
    try:
        r = requests.get(url, headers=get_headers(), timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Buscar metadatos OpenGraph
        image = soup.find("meta", property="og:image")
        title = soup.find("meta", property="og:title")
        desc = soup.find("meta", property="og:description")
        
        details = {}
        img_url = None
        
        if title:
            # Telegram suele poner "Nombre - @username" o "Nombre"
            name_raw = title.get("content", "").replace("Telegram: Contact @", "")
            details["Nombre Visible"] = name_raw.split(" - ")[0] if " - " in name_raw else name_raw
            
        if desc:
            details["Biografía"] = desc.get("content", "")
            
        if image:
            img_url = image.get("content")
            
        return details, img_url
    except:
        return {}, None

# B. Extractor de GitHub (API)
def extract_github(username):
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            details = {
                "Nombre": data.get("name"),
                "Bio": data.get("bio"),
                "Ubicación": data.get("location"),
                "Empresa": data.get("company"),
                "Twitter": data.get("twitter_username"),
                "Repos Públicos": data.get("public_repos"),
                "Seguidores": data.get("followers")
            }
            # Limpiamos valores None
            return {k: v for k, v in details.items() if v}, data.get("avatar_url")
    except:
        pass
    return {}, None

# C. Extractor de Gravatar (JSON)
def extract_gravatar(username):
    try:
        # Gravatar suele funcionar con hash de email, pero a veces el usuario es directo
        r = requests.get(f"https://en.gravatar.com/{username}.json", headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()['entry'][0]
            details = {
                "Nombre": data.get("displayName"),
                "Ubicación": data.get("currentLocation"),
                "Sobre mí": data.get("aboutMe")
            }
            img = data.get("thumbnailUrl")
            return {k: v for k, v in details.items() if v}, img
    except:
        pass
    return {}, None

# D. Extractor Genérico (Meta Tags)
def extract_generic_meta(url):
    try:
        r = requests.get(url, headers=get_headers(), timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        details = {}
        image = None
        
        # Título de la página
        if soup.title:
            details["Título Página"] = soup.title.string.strip()
            
        # Meta Descripción
        desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if desc:
            details["Descripción"] = desc.get("content", "")[:200] + "..." # Limitamos largo
            
        # Imagen
        img = soup.find("meta", property="og:image")
        if img:
            image = img.get("content")
            
        return details, image
    except:
        return {}, None

# --- 5. LOGICA CENTRAL DE "SMART EXTRACT" ---
def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    
    # 1. Verificar Existencia (Fase Rápida)
    try:
        r = requests.get(uri, headers=get_headers(), timeout=6)
        # Validación básica de código de estado
        if r.status_code != site['e_code']:
            return None
        # Validación de texto falso positivo
        if site.get('e_string') and site['e_string'] not in r.text:
            return None
    except:
        return None

    # 2. Extracción de Inteligencia (Fase Profunda)
    # Seleccionamos el extractor según el sitio
    details = {}
    image_url = None
    
    site_name = site['name'].lower()
    
    if "telegram" in site_name:
        details, image_url = extract_telegram(username)
    elif "github" in site_name:
        details, image_url = extract_github(username)
    elif "gravatar" in site_name:
        details, image_url = extract_gravatar(username)
    else:
        # Intento genérico con BeautifulSoup primero (más rápido)
        details, image_url = extract_generic_meta(uri)
        
        # Si falla y tenemos socid, intentamos socid (más lento pero potente)
        if not details and not image_url and socid_extract:
            try:
                data = socid_extract(uri)
                if data:
                    details = {k: v for k, v in data.items() if v and k != 'image'}
                    image_url = data.get('image')
            except:
                pass

    # Fallback de imagen (Favicon) si no encontramos nada
    if not image_url:
        try:
            domain = uri.split('/')[2]
            image_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
        except:
            image_url = "https://via.placeholder.com/128?text=404"

    return {
        "name": site['name'],
        "uri": uri,
        "category": site['cat'],
        "image": image_url,
        "details": details
    }

# --- 6. UTILIDADES AUXILIARES ---
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

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, clean_text('Reporte SOCMINT - WhatsMyName Web'), 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, clean_text('Autor: Manuel Travezaño | Herramienta: WhatsMyName Web'), 0, 1, 'C')
        self.set_text_color(0, 0, 255)
        self.cell(0, 5, APP_URL, 0, 1, 'C', link=APP_URL)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, f'Pag {self.page_no()}', 0, 0, 'C')

def generate_files(results, username):
    # CSV
    df = pd.DataFrame(results)
    df_simple = df.drop(columns=['details', 'image'], errors='ignore')
    csv = df_simple.to_csv(index=False).encode('utf-8')
    
    # TXT
    txt = io.StringIO()
    txt.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt.write(f"Herramienta: {APP_URL}\n")
    txt.write("="*60 + "\n\n")
    for item in results:
        txt.write(f"Plataforma: {item['name']}\nURL: {item['uri']}\n")
        if item.get('details'):
            for k, v in item['details'].items():
                txt.write(f"  - {k}: {v}\n")
        txt.write("-" * 20 + "\n")
    
    # PDF
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, clean_text(f"Objetivo: {username}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(5)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(60, 8, clean_text("Plataforma"), 1, 0, 'L', 1)
        pdf.cell(40, 8, clean_text("Categoría"), 1, 0, 'L', 1)
        pdf.cell(90, 8, clean_text("Enlace"), 1, 1, 'L', 1)
        
        pdf.set_font("Arial", size=9)
        for item in results:
            name = clean_text(item['name'][:30])
            cat = clean_text(item['category'][:20])
            pdf.cell(60, 8, name, 1)
            pdf.cell(40, 8, cat, 1)
            pdf.set_text_color(0, 0, 255)
            pdf.cell(90, 8, clean_text("Enlace aqui"), 1, 1, 'C', link=item['uri'])
            pdf.set_text_color(0, 0, 0)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except:
        pdf_bytes = None
    
    return csv, txt.getvalue(), pdf_bytes

# --- 7. INTERFAZ PRINCIPAL ---
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
    st.markdown("---")

st.markdown("<h1 class='main-title'>WhatsMyName Web</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Herramienta SOCMINT | Manuel Travezaño</p>", unsafe_allow_html=True)

sites = load_sites()
categories = sorted(list(set([s['cat'] for s in sites])))

c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    username = st.text_input("Usuario", placeholder="Ej: manuelbot59", label_visibility="collapsed")
with c2:
    cat_filter = st.selectbox("Cat", ["Todas"] + categories, label_visibility="collapsed")
with c3:
    run_btn = st.button("🔍 INVESTIGAR", use_container_width=True, type="primary")

results_placeholder = st.container()

if run_btn and username:
    st.session_state.results = []
    st.session_state.search_active = True
    
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    prog_bar = st.progress(0)
    status_text = st.empty()
    processed = 0
    
    with results_placeholder:
        st.markdown("### ⏳ Analizando y Extrayendo Datos...")
        grid_dynamic = st.empty()
    
    # Reducimos hilos a 10 para dar tiempo a los scrapers de trabajar
    with ThreadPoolExecutor(max_workers=10) as executor:
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
                                c_a, c_b, c_c = st.columns([1, 4, 2])
                                with c_a:
                                    st.image(item['image'], width=45)
                                with c_b:
                                    st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                                with c_c:
                                    st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                                
                                if item.get('details'):
                                    with st.expander("👁️ Ver Detalles Extraídos", expanded=False):
                                        d1, d2 = st.columns([1, 2])
                                        with d1:
                                            st.image(item['image'], use_column_width=True, caption="Perfil")
                                        with d2:
                                            for k, v in item['details'].items():
                                                st.markdown(f"**{k}:** {v}")
                                else:
                                    st.caption("Solo detección de cuenta.")

    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

elif st.session_state.results:
    with results_placeholder:
        st.divider()
        st.markdown(f"### 🎯 Resultados: {len(st.session_state.results)}")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.results):
            with cols[i % 2]:
                with st.container(border=True):
                    c_a, c_b, c_c = st.columns([1, 4, 2])
                    with c_a:
                        st.image(item['image'], width=45)
                    with c_b:
                        st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                    with c_c:
                        st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                    
                    if item.get('details'):
                        with st.expander("👁️ Ver Detalles Extraídos"):
                            d1, d2 = st.columns([1, 2])
                            with d1:
                                st.image(item['image'], use_column_width=True, caption="Perfil")
                            with d2:
                                for k, v in item['details'].items():
                                    st.markdown(f"**{k}:** {v}")

if st.session_state.results:
    st.divider()
    st.subheader("📥 Exportar Reporte")
    csv_data, txt_data, pdf_data = generate_files(st.session_state.results, username)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 Descargar CSV", csv_data, f"report_{username}.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button("📝 Descargar TXT", txt_data, f"report_{username}.txt", "text/plain", use_container_width=True)
    with c3:
        if pdf_data:
            st.download_button("📕 Descargar PDF", pdf_data, f"report_{username}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("⚠️ Error generando PDF")

st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a> & <a href="https://github.com/soxoj/socid-extractor" target="_blank">socid-extractor</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)