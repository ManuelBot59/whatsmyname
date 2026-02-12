import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. BARRA LATERAL (SIDEBAR) - CARGA PRIMERO ---
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
    st.caption("v3.0 Pro | Powered by WhatsMyName")

# --- 3. ESTILOS CSS (DISEÑO RECTANGULAR "HIPPIE STYLE") ---
st.markdown("""
<style>
    /* Ocultar elementos nativos */
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

    /* Títulos y textos */
    .site-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1c3961;
        margin-bottom: 0px;
    }
    .site-cat {
        font-size: 0.8rem;
        color: #64748b;
        background-color: #f1f5f9;
        padding: 2px 8px;
        border-radius: 12px;
        display: inline-block;
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

# --- 4. LÓGICA DE BÚSQUEDA Y EXTRACCIÓN ---
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

# --- BONUS: Función para extraer datos reales de GitHub (Para que se vea como en la foto) ---
def get_github_details(username):
    try:
        api_url = f"https://api.github.com/users/{username}"
        r = requests.get(api_url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                "Bio": data.get("bio", "Sin bio"),
                "Ubicación": data.get("location", "Desconocida"),
                "Seguidores": data.get("followers", 0),
                "Repos Públicos": data.get("public_repos", 0),
                "Avatar": data.get("avatar_url")
            }
    except:
        pass
    return None

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(uri, headers=headers, timeout=5)
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            
            # Datos básicos
            details = {}
            image_url = None
            
            # --- Lógica de Extracción Especial (Ejemplo para GitHub) ---
            if site['name'] == "GitHub":
                gh_data = get_github_details(username)
                if gh_data:
                    details = gh_data
                    image_url = gh_data.get("Avatar")
            
            # Fallback para imagen (Favicon de Google)
            if not image_url:
                domain = uri.split('/')[2]
                image_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat'],
                "image": image_url,
                "details": details # Diccionario con info extra
            }
    except:
        return None
    return None

# --- 5. LIMPIEZA DE TEXTO (Evita Error PDF) ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 6. CLASE PDF MEJORADA (Enlaces Limpios) ---
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
    # Limpiar columnas complejas para el CSV
    df_simple = df.drop(columns=['details'], errors='ignore')
    csv = df_simple.to_csv(index=False).encode('utf-8')
    
    # TXT
    txt = io.StringIO()
    txt.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt.write(f"Herramienta: {APP_URL}\n")
    txt.write("="*60 + "\n\n")
    for item in results:
        txt.write(f"Plataforma: {item['name']}\nURL: {item['uri']}\n")
    
    # PDF
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        pdf.cell(0, 10, clean_text(f"Objetivo: {username}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(5)
        
        # Encabezados
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(60, 8, clean_text("Plataforma"), 1, 0, 'L', 1)
        pdf.cell(40, 8, clean_text("Categoría"), 1, 0, 'L', 1)
        pdf.cell(90, 8, clean_text("Enlace"), 1, 1, 'L', 1)
        
        # Filas
        pdf.set_font("Arial", size=9)
        for item in results:
            name = clean_text(item['name'][:30])
            cat = clean_text(item['category'][:20])
            
            pdf.cell(60, 8, name, 1)
            pdf.cell(40, 8, cat, 1)
            
            # ENLACE LIMPIO: Texto "Enlace aquí" con hipervínculo real
            pdf.set_text_color(0, 0, 255)
            # cell(w, h, txt, border, ln, align, fill, link)
            pdf.cell(90, 8, clean_text("Enlace aqui"), 1, 1, 'C', link=item['uri'])
            pdf.set_text_color(0, 0, 0)
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e:
        print(f"Error PDF: {e}")
        pdf_bytes = None
        
    return csv, txt.getvalue(), pdf_bytes

# --- 7. INTERFAZ PRINCIPAL ---
st.markdown("<h1 class='main-title'>WhatsMyName Web</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Herramienta SOCMINT | Manuel Travezaño</p>", unsafe_allow_html=True)

sites = load_sites()
categories = sorted(list(set([s['cat'] for s in sites])))

# Estado
if "results" not in st.session_state:
    st.session_state.results = []

# Buscador
c_search_1, c_search_2, c_search_3 = st.columns([3, 1, 1])
with c_search_1:
    username = st.text_input("Usuario", placeholder="Ej: manuelbot59", label_visibility="collapsed")
with c_search_2:
    cat_filter = st.selectbox("Cat", ["Todas"] + categories, label_visibility="collapsed")
with c_search_3:
    run_btn = st.button("🔍 INVESTIGAR", use_container_width=True, type="primary")

# Contenedor de Resultados
results_placeholder = st.container()

# Lógica de Ejecución
if run_btn and username:
    st.session_state.results = [] # Limpiar
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    processed = 0
    
    # Placeholder del Grid para actualización en tiempo real
    with results_placeholder:
        st.markdown("### ⏳ Analizando en tiempo real...")
        grid_dynamic = st.empty()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            if processed % 10 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Verificando: {processed}/{len(target_sites)}")
            
            if res:
                st.session_state.results.append(res)
                
                # --- RENDERIZADO PROGRESIVO ---
                # Redibujamos la cuadrícula cada vez que hay un hallazgo
                with grid_dynamic.container():
                    # Usamos 2 columnas para el estilo rectangular ancho
                    cols = st.columns(2)
                    for i, item in enumerate(st.session_state.results):
                        with cols[i % 2]:
                            with st.container(border=True):
                                # Layout: Icono | Info | Botón Visitar
                                c1, c2, c3 = st.columns([1, 4, 2])
                                with c1:
                                    st.image(item['image'], width=45)
                                with c2:
                                    st.markdown(f"<div class='site-title'>{item['name']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<span class='site-cat'>{item['category']}</span>", unsafe_allow_html=True)
                                with c3:
                                    st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                                
                                # Sección "Ver Detalles" (Expander)
                                # Solo si hay detalles extra (como el scraper de GitHub) o siempre para la foto
                                with st.expander("👁️ Ver Detalles Extraídos"):
                                    d1, d2 = st.columns([1, 2])
                                    with d1:
                                        # Imagen más grande
                                        st.image(item['image'], use_column_width=True, caption="Evidencia")
                                    with d2:
                                        # Si hay detalles técnicos (Scraping), los mostramos
                                        if item['details']:
                                            for k, v in item['details'].items():
                                                if k != "Avatar": # No repetir avatar
                                                    st.markdown(f"**{k}:** {v}")
                                        else:
                                            st.info("Solo detección de existencia disponible.")
                                            st.text(f"URL: {item['uri']}")

    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# Renderizado Persistente (Si hay datos y no se está buscando)
elif st.session_state.results:
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
                    
                    with st.expander("👁️ Ver Detalles Extraídos"):
                        d1, d2 = st.columns([1, 2])
                        with d1:
                            st.image(item['image'], use_column_width=True, caption="Evidencia")
                        with d2:
                            if item['details']:
                                for k, v in item['details'].items():
                                    if k != "Avatar":
                                        st.markdown(f"**{k}:** {v}")
                            else:
                                st.caption(f"URL Detectada: {item['uri']}")

# --- 9. ZONA DE DESCARGA ---
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
            st.warning("⚠️ Error generando PDF (Caracteres extraños)")

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)