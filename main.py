import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE ESTADO (Para que no se borre al dar clic) ---
if "results" not in st.session_state:
    st.session_state.results = []
if "search_active" not in st.session_state:
    st.session_state.search_active = False

# --- 3. ESTILOS CSS (Diseño Uniforme y Profesional) ---
st.markdown("""
<style>
    /* Ocultar marcas de agua de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Fondo */
    .stApp {
        background-color: #f4f7f6;
    }

    /* Título Principal */
    .main-title {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        text-align: center;
        padding-top: 1rem;
        margin-bottom: 0px;
    }

    /* Estilo de la Tarjeta de Resultado (Estilo GitHub/GitLab de la imagen) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        border-left: 5px solid #27ae60; /* Borde verde a la izquierda */
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    /* Texto dentro de las tarjetas */
    .card-header-text {
        font-weight: bold;
        font-size: 1.2rem;
        color: #1c3961;
    }
    
    .card-subtext {
        font-size: 0.85rem;
        color: #666;
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

# --- 4. FUNCIONES AUXILIARES ---
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

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(uri, headers=headers, timeout=5)
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            
            # Intentamos obtener favicon
            domain = uri.split('/')[2]
            favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
            
            # Estructura de datos simulando "Detalles Extraídos"
            # En un caso real, aquí iría el scraping. Aquí simulamos datos básicos.
            details = {
                "Plataforma": site['name'],
                "Categoría": site['cat'],
                "Enlace": uri
            }
            
            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat'],
                "image": favicon,
                "details": details
            }
    except:
        return None
    return None

# --- 5. GENERADOR DE PDF BLINDADO (Sin errores Unicode) ---
def clean_text(text):
    """Elimina caracteres que rompen el PDF"""
    if not isinstance(text, str): return str(text)
    # Reemplaza caracteres no latinos con '?' para evitar el crash
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
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_pdf(results, username):
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        pdf.cell(0, 10, clean_text(f"Objetivo: {username}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(5)
        
        # Encabezados de tabla
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(60, 10, clean_text("Plataforma"), 1, 0, 'L', 1)
        pdf.cell(40, 10, clean_text("Categoría"), 1, 0, 'L', 1)
        pdf.cell(90, 10, clean_text("Enlace"), 1, 1, 'L', 1)
        
        # Filas
        pdf.set_font("Arial", size=9)
        for item in results:
            name = clean_text(item['name'][:30])
            cat = clean_text(item['category'][:20])
            uri = clean_text(item['uri'][:50])
            
            pdf.cell(60, 10, name, 1)
            pdf.cell(40, 10, cat, 1)
            pdf.cell(90, 10, uri, 1, 0, 'L', link=item['uri']) # Enlace clickeable
            pdf.ln()
            
        return pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e:
        return None

# --- 6. RENDERIZADOR DE TARJETAS (Visualización) ---
def render_results_grid(results_list):
    """Renderiza la lista de resultados en 2 columnas (Estilo Rectangular Ancho)"""
    # Usamos 2 columnas para que las tarjetas sean anchas como en la imagen de referencia
    cols = st.columns(2)
    
    for i, item in enumerate(results_list):
        with cols[i % 2]:
            with st.container(border=True):
                # Fila Superior: Icono + Nombre + Botón
                c1, c2, c3 = st.columns([1, 4, 2])
                with c1:
                    st.image(item['image'], width=40)
                with c2:
                    st.markdown(f"<div class='card-header-text'>{item['name']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='card-subtext'>{item['category']}</div>", unsafe_allow_html=True)
                with c3:
                    st.link_button("🔗 Visitar", item['uri'], use_container_width=True)
                
                # Fila Inferior: Detalles (Expander en lugar de Modal para estabilidad)
                with st.expander("👁️ Ver Detalles Extraídos"):
                    # Aquí simulamos la vista detallada de la imagen que enviaste
                    d1, d2 = st.columns([1, 2])
                    with d1:
                        st.image(item['image'], use_column_width=True, caption="Evidencia")
                    with d2:
                        st.caption("INFORMACIÓN TÉCNICA")
                        st.code(f"Site: {item['name']}\nCat: {item['category']}\nURL: {item['uri']}", language="yaml")

# --- 7. BARRA LATERAL (Siempre visible) ---
with st.sidebar:
    st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🎓 Cursos](https://manuelbot59.com/formacion/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.markdown("### 📞 Soporte")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")
    st.markdown("---")

# --- 8. CUERPO PRINCIPAL ---
st.markdown("<h1 class='main-title'>WhatsMyName Web</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Herramienta SOCMINT | Manuel Travezaño</p>", unsafe_allow_html=True)

sites = load_sites()
categories = sorted(list(set([s['cat'] for s in sites])))

# Buscador
c_search_1, c_search_2, c_search_3 = st.columns([3, 1, 1])
with c_search_1:
    username = st.text_input("Usuario", placeholder="Ej: manuelbot59", label_visibility="collapsed")
with c_search_2:
    cat_filter = st.selectbox("Cat", ["Todas"] + categories, label_visibility="collapsed")
with c_search_3:
    run_btn = st.button("🔍 INVESTIGAR", use_container_width=True, type="primary")

# Contenedor de Resultados (Placeholder para carga progresiva)
results_placeholder = st.container()

# Lógica de Ejecución
if run_btn and username:
    st.session_state.results = [] # Limpiar
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    processed = 0
    
    # Grid dinámico
    with results_placeholder:
        st.markdown("### ⏳ Analizando en tiempo real...")
        # Creamos un contenedor vacío que iremos llenando
        dynamic_grid = st.empty()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Actualizar barra
            if processed % 10 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Analizando: {processed}/{len(target_sites)} sitios")
            
            if res:
                st.session_state.results.append(res)
                # ¡TRUCO! Redibujamos la cuadrícula entera cada vez que hay un hallazgo.
                # Esto logra el efecto progresivo y ordenado.
                with dynamic_grid.container():
                    render_results_grid(st.session_state.results)

    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# Renderizado Persistente (Si no estamos buscando pero hay datos)
elif st.session_state.results:
    with results_placeholder:
        st.markdown(f"### 🎯 Resultados: {len(st.session_state.results)}")
        render_results_grid(st.session_state.results)

# --- 9. ZONA DE DESCARGA ---
if st.session_state.results:
    st.divider()
    st.subheader("📥 Exportar Reporte")
    
    # Generar datos
    df = pd.DataFrame(st.session_state.results)
    # Limpiamos columna 'details' para el CSV/TXT
    df_clean = df.drop(columns=['details', 'image'], errors='ignore')
    
    csv_data = df_clean.to_csv(index=False).encode('utf-8')
    pdf_bytes = generate_pdf(st.session_state.results, username)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 Descargar CSV", csv_data, f"report_{username}.csv", "text/csv", use_container_width=True)
    with col2:
        if pdf_bytes:
            st.download_button("📕 Descargar PDF", pdf_bytes, f"report_{username}.pdf", "application/pdf", use_container_width=True)
        else:
            st.error("Error generando PDF (Caracteres no soportados en el nombre de usuario o resultados)")

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)