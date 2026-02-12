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

# --- 2. ESTILOS CSS PROFESIONALES (Tarjetas Uniformes) ---
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

    /* ESTILO DE TARJETAS (Uniformidad) */
    div[data-testid="stColumn"] {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        transition: transform 0.2s;
        min-height: 220px; /* Altura fija mínima para uniformidad */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    div[data-testid="stColumn"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        border-color: #00c6fb;
    }

    /* Ajuste de botones dentro de columnas */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
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

# --- 3. LÓGICA DE BÚSQUEDA ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
APP_URL = "https://whatsmyname.streamlit.app/" # Tu enlace para los reportes

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
        r = requests.get(uri, headers=headers, timeout=5)
        
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

# --- 4. VENTANA EMERGENTE (MODAL) ---
@st.dialog("Detalles Extraídos")
def show_details(item):
    # Cabecera
    st.markdown(f"### {item['name']}")
    st.caption(f"Categoría: {item['category']}")
    st.markdown("---")
    
    # Imagen al 60%
    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        st.image(item['image'], caption="Evidencia Visual", use_column_width=True)
    
    st.markdown("---")
    
    # Botón de enlace (Parte superior derecha visualmente ajustada en el flujo)
    st.link_button("🔗 Ir al Perfil", item['uri'], type="primary", use_container_width=True)

# --- 5. REPORTES (PDF, CSV, TXT) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte SOCMINT - WhatsMyName Web', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        # PIE DE PÁGINA CON ENLACE
        self.cell(0, 10, f'Generado en: {APP_URL} | Pagina {self.page_no()}', 0, 0, 'C')

def generate_reports(results, username):
    # 1. CSV
    df = pd.DataFrame(results)
    csv = df.to_csv(index=False).encode('utf-8')
    
    # 2. TXT
    txt_buffer = io.StringIO()
    txt_buffer.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt_buffer.write(f"Herramienta: WhatsMyName Web\nEnlace: {APP_URL}\n")
    txt_buffer.write("="*50 + "\n\n")
    for item in results:
        txt_buffer.write(f"Sitio: {item['name']}\nURL: {item['uri']}\nCategoria: {item['category']}\n{'-'*30}\n")
    
    # 3. PDF
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

# --- 6. INTERFAZ PRINCIPAL ---

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

# Estado de la sesión para resultados
if "results_list" not in st.session_state:
    st.session_state.results_list = []

if run_btn and username:
    st.session_state.results_list = [] # Limpiar
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    # Barra de progreso
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    # --- ÁREA DE RESULTADOS (GRID PROGRESIVO) ---
    st.markdown("### 🎯 Resultados en Tiempo Real")
    
    # Contenedor principal para ir añadiendo filas
    results_container = st.container()
    
    # Variables de control para el grid
    current_row_cols = [] 
    
    processed = 0
    found_count = 0
    
    # Ejecutor
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        # Iteramos conforme se completan las tareas
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Actualizar barra (cada 5 para rendimiento)
            if processed % 5 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Analizando: {processed}/{len(target_sites)}")
            
            if res:
                found_count += 1
                st.session_state.results_list.append(res)
                
                # --- LÓGICA DE GRID PROGRESIVO ---
                # Si no tenemos columnas activas o ya llenamos las 4, creamos nuevas
                if not current_row_cols or len(current_row_cols) >= 4:
                    with results_container:
                        current_row_cols = st.columns(4)
                
                # Seleccionamos la columna libre actual
                # (found_count - 1) % 4 nos da el índice 0, 1, 2, 3
                col_idx = (found_count - 1) % 4
                col = current_row_cols[col_idx]
                
                # Renderizamos la tarjeta en esa columna
                with col:
                    st.markdown(f"**✅ {res['name']}**")
                    st.caption(f"Cat: {res['category']}")
                    
                    # Botón 1: Ver Detalles (Modal)
                    if st.button("👁️ Ver Detalles", key=f"det_{res['uri']}"):
                        show_details(res)
                    
                    # Botón 2: Enlace Directo (Estilo nativo)
                    st.link_button("🔗 Ir al Sitio", res['uri'])

    prog_bar.empty()
    if found_count > 0:
        status_text.success(f"✅ Finalizado. {found_count} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# --- ZONA DE DESCARGA (Solo si hay resultados) ---
if st.session_state.results_list:
    st.divider()
    st.subheader("📥 Exportar Reporte")
    
    csv_data, txt_data, pdf_data = generate_reports(st.session_state.results_list, username)
    
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        st.download_button("📄 Descargar CSV", csv_data, f"report_{username}.csv", "text/csv", use_container_width=True)
    with dc2:
        st.download_button("📝 Descargar TXT", txt_data, f"report_{username}.txt", "text/plain", use_container_width=True)
    with dc3:
        st.download_button("📕 Descargar PDF", pdf_data, f"report_{username}.pdf", "application/pdf", use_container_width=True)

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)