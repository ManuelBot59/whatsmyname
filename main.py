import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE ESTADO (SOLUCIÓN AL REFRESH) ---
# Inicializamos las variables para que persistan entre clics
if "results" not in st.session_state:
    st.session_state.results = []
if "search_done" not in st.session_state:
    st.session_state.search_done = False

# --- 3. ESTILOS CSS CORREGIDOS (SOLUCIÓN CUADROS VACÍOS) ---
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

    /* ESTILO DE LA TARJETA (Uniformidad) */
    /* Usamos una clase personalizada para evitar bordes en columnas vacías */
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div > div[data-testid="stVerticalBlock"] {
        /* Ajuste fino para uniformidad vertical si es necesario */
    }

    /* Botones dentro de las tarjetas */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid #1c3961;
        color: #1c3961;
        background-color: white;
        transition: all 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #1c3961;
        color: white;
        border-color: #1c3961;
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

# --- 4. LÓGICA DE BÚSQUEDA ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
APP_URL = "https://whatsmyname.streamlit.app/" 

@st.cache_data
def load_sites():
    try:
        response = requests.get(WMN_DATA_URL)
        data = response.json()
        return data['sites']
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(uri, headers=headers, timeout=6) # Timeout un poco más alto
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            
            # Simulamos obtención de imagen/favicon
            domain = uri.split('/')[2]
            favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
            
            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat'],
                "image": favicon
            }
    except:
        return None
    return None

# --- 5. CLASE PDF PERSONALIZADA (SOLUCIÓN PIE DE PÁGINA) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte SOCMINT - WhatsMyName Web', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        # Texto
        self.cell(0, 5, f'Herramienta: WhatsMyName Web | Autor: Manuel Travezano', 0, 1, 'C')
        # Enlace activo
        self.set_text_color(0, 0, 255) # Azul
        self.cell(0, 5, APP_URL, 0, 1, 'C', link=APP_URL)
        self.set_text_color(0, 0, 0) # Negro
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_reports(results, username):
    # CSV
    df = pd.DataFrame(results)
    csv = df.to_csv(index=False).encode('utf-8')
    
    # TXT
    txt_buffer = io.StringIO()
    txt_buffer.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt_buffer.write(f"Autor: Manuel Travezano\n")
    txt_buffer.write(f"Herramienta: {APP_URL}\n")
    txt_buffer.write("="*50 + "\n\n")
    for item in results:
        txt_buffer.write(f"Sitio: {item['name']}\nURL: {item['uri']}\nCategoria: {item['category']}\n{'-'*30}\n")
    
    # PDF
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Usuario Investigado: {username}", ln=1)
    pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(50, 10, "Plataforma", 1)
    pdf.cell(40, 10, "Categoria", 1)
    pdf.cell(100, 10, "Enlace", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    for item in results:
        name = item['name'][:25]
        cat = item['category'][:20]
        uri = item['uri'][:55]
        pdf.cell(50, 10, name, 1)
        pdf.cell(40, 10, cat, 1)
        pdf.cell(100, 10, uri, 1)
        pdf.ln()
        
    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    
    return csv, txt_buffer.getvalue(), pdf_bytes

# --- 6. VENTANA EMERGENTE (MODAL CORREGIDO) ---
@st.dialog("Detalles Extraídos")
def show_details(item):
    # Cabecera
    st.markdown(f"### {item['name']}")
    st.caption(f"Categoría: {item['category']}")
    st.markdown("---")
    
    # Imagen al 60% centrada
    c1, c2, c3 = st.columns([1, 2, 1]) # Columnas ajustadas para centrar
    with c2:
        st.image(item['image'], caption="Evidencia Visual", use_column_width=True)
    
    st.markdown("---")
    
    # Botón de enlace en la parte superior derecha (Simulado con columnas)
    st.success("✅ Presencia Confirmada")
    st.link_button("🔗 Ir al Perfil Oficial", item['uri'], type="primary", use_container_width=True)


# --- 7. INTERFAZ PRINCIPAL ---

with st.sidebar:
    st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🎓 Cursos](https://manuelbot59.com/formacion/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.markdown("### 📞 Contacto")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")
    st.markdown("---")

st.title("WhatsMyName Web")
st.markdown("### Herramienta SOCMINT | Manuel Travezaño")

sites = load_sites()
categories = sorted(list(set([s['cat'] for s in sites])))

c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    username = st.text_input("Usuario", placeholder="Ej: manuelbot59", label_visibility="collapsed")
with c2:
    cat_filter = st.selectbox("Cat", ["Todas"] + categories, label_visibility="collapsed")
with c3:
    run_btn = st.button("🔍 INVESTIGAR", use_container_width=True, type="primary")

# --- 8. EJECUCIÓN DE BÚSQUEDA ---
if run_btn and username:
    st.session_state.results = []
    st.session_state.search_done = False
    
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    # Placeholder para mostrar progreso numérico
    progress_placeholder = st.container()
    
    processed = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            if processed % 5 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Analizando: {processed}/{len(target_sites)}")
            
            if res:
                st.session_state.results.append(res)
                # Mostrar hallazgo rápido en texto mientras carga el resto
                with progress_placeholder:
                    st.toast(f"Encontrado: {res['name']}", icon="✅")

    prog_bar.progress(100)
    st.session_state.search_done = True
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# --- 9. RENDERIZADO DE RESULTADOS (PERSISTENTE) ---
# Esta sección está fuera del 'if run_btn' para que no desaparezca al interactuar
if st.session_state.results:
    st.divider()
    st.markdown("### 🎯 Resultados Encontrados")
    
    results = st.session_state.results
    cols_per_row = 4
    
    # Bucle corregido para evitar duplicados de keys
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(results):
                item = results[i + j]
                with cols[j]:
                    # Usamos st.container con borde nativo para estética uniforme
                    with st.container(border=True):
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"{item['category']}")
                        
                        # SOLUCIÓN ERROR DUPLICATE KEY:
                        # Usamos el índice (i+j) para garantizar que la key sea única siempre
                        unique_key = f"btn_{i+j}_{item['name']}"
                        
                        if st.button("👁️ Ver Detalles", key=unique_key):
                            show_details(item)

# --- 10. ZONA DE DESCARGA ---
if st.session_state.search_done and st.session_state.results:
    st.divider()
    st.subheader("📥 Exportar Reporte")
    
    csv_data, txt_data, pdf_data = generate_reports(st.session_state.results, username)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📄 Descargar CSV", csv_data, f"report_{username}.csv", "text/csv", use_container_width=True)
    with col2:
        st.download_button("📝 Descargar TXT", txt_data, f"report_{username}.txt", "text/plain", use_container_width=True)
    with col3:
        st.download_button("📕 Descargar PDF", pdf_data, f"report_{username}.pdf", "application/pdf", use_container_width=True)

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)