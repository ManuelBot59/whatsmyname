import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# Importamos la librería de extracción
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

# --- 2. GESTIÓN DE ESTADO (CRÍTICO: SIEMPRE AL INICIO) ---
# Inicializamos las variables ANTES de cualquier lógica
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

    /* ESTILO DE TARJETA TIPO "HIPPIE OSINT" */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
        transition: transform 0.2s, box-shadow 0.2s;
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

# --- 4. FUNCIONES AUXILIARES Y EXTRACTOR ---
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

def get_profile_details(url):
    """ Usa socid-extractor para obtener datos reales """
    if not socid_extract:
        return {}, None

    try:
        data = socid_extract(url)
        if not data:
            return {}, None
            
        details = {k: v for k, v in data.items() if v and k != 'image'}
        image = data.get('image')
        return details, image
    except:
        return {}, None

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # 1. Validación rápida
        r = requests.get(uri, headers=headers, timeout=5)
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            
            # 2. Extracción profunda
            extracted_details, extracted_image = get_profile_details(uri)
            
            # Fallback de imagen
            if not extracted_image:
                domain = uri.split('/')[2]
                extracted_image = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat'],
                "image": extracted_image,
                "details": extracted_details
            }
    except:
        return None
    return None

# --- 5. GENERACIÓN DE REPORTES (BLINDADO) ---
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
            txt.write(f"  > Datos: {item['details']}\n")
    
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

# --- 6. INTERFAZ PRINCIPAL ---
# BARRA LATERAL (Siempre primero)
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

# Buscador
c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    username = st.text_input("Usuario", placeholder="Ej: manuelbot59", label_visibility="collapsed")
with c2:
    cat_filter = st.selectbox("Cat", ["Todas"] + categories, label_visibility="collapsed")
with c3:
    run_btn = st.button("🔍 INVESTIGAR", use_container_width=True, type="primary")

# Contenedor Progresivo
results_placeholder = st.container()

# Lógica de Ejecución
if run_btn and username:
    st.session_state.results = []
    st.session_state.search_active = True # Marcamos que estamos buscando
    
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    processed = 0
    
    with results_placeholder:
        st.markdown("### ⏳ Analizando y Extrayendo Datos...")
        grid_dynamic = st.empty()
    
    # Hilos reducidos para estabilidad con socid-extractor
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
                
                # Renderizado Progresivo
                with grid_dynamic.container():
                    cols = st.columns(2)
                    for i, item in enumerate(st.session_state.results):
                        with cols[i % 2]:
                            with st.container(border=True):
                                c1, c2, c3 = st.columns([1, 4, 2])
                                with c1:
                                    st.image(item['image'], width=45)
                                with c2:
                                    st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                                with c3:
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

# RENDERIZADO PERSISTENTE (SOLUCIÓN AL ERROR DE PANTALLA EN BLANCO)
# Se ejecuta si hay resultados en memoria Y NO se está buscando activamente en este momento
elif "results" in st.session_state and st.session_state.results and not run_btn:
    with results_placeholder:
        st.divider()
        st.markdown(f"### 🎯 Resultados: {len(st.session_state.results)}")
        cols = st.columns(2)
        for i, item in enumerate(st.session_state.results):
            with cols[i % 2]:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 4, 2])
                    with c1:
                        st.image(item['image'], width=45)
                    with c2:
                        st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                    with c3:
                        st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                    
                    if item.get('details'):
                        with st.expander("👁️ Ver Detalles Extraídos"):
                            d1, d2 = st.columns([1, 2])
                            with d1:
                                st.image(item['image'], use_column_width=True, caption="Perfil")
                            with d2:
                                for k, v in item['details'].items():
                                    st.markdown(f"**{k}:** {v}")
                    else:
                        st.caption("Solo detección de cuenta.")

# --- 7. ZONA DE DESCARGA ---
if "results" in st.session_state and st.session_state.results:
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

# Footer (Siempre al final, fuera de condicionales)
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a> & <a href="https://github.com/soxoj/socid-extractor" target="_blank">socid-extractor</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)