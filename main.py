import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE ESTADO (MEMORIA) ---
if "results" not in st.session_state:
    st.session_state.results = []

# --- 3. ESTILOS CSS REFINADOS ---
st.markdown("""
<style>
    /* Ocultar elementos nativos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #f4f7f6;
    }

    /* TÍTULO PRINCIPAL */
    h1 {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        text-align: center;
        padding-top: 1rem;
    }

    /* TARJETAS DE RESULTADOS (SOLO LAS QUE TIENEN DATOS) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
        height: 100%; /* Altura uniforme */
    }

    /* ESTILO BOTONES */
    div.stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }

    /* FOOTER */
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
            
            # Recuperar favicon para imagen
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

# --- 5. LIMPIEZA DE TEXTO PARA PDF (CRÍTICO) ---
def clean_text(text):
    """Elimina caracteres no soportados por FPDF (latin-1)"""
    if not isinstance(text, str):
        return str(text)
    # Codifica a ASCII ignorando errores y decodifica de nuevo
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- 6. GENERADOR DE REPORTES (PDF, CSV, TXT) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, clean_text('Reporte SOCMINT - WhatsMyName Web'), 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, clean_text('Autor: Manuel Travezano | Herramienta: WhatsMyName Web'), 0, 1, 'C')
        
        # Enlace clickeable en el PDF
        self.set_text_color(0, 0, 255)
        self.cell(0, 5, clean_text(APP_URL), 0, 1, 'C', link=APP_URL)
        
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_files(results, username):
    # 1. CSV
    df = pd.DataFrame(results)
    csv = df.to_csv(index=False).encode('utf-8')
    
    # 2. TXT
    txt = io.StringIO()
    txt.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt.write(f"Herramienta: {APP_URL}\n")
    txt.write("="*60 + "\n\n")
    for item in results:
        txt.write(f"Plataforma: {item['name']}\nCategoria: {item['category']}\nEnlace: {item['uri']}\n{'-'*30}\n")
    
    # 3. PDF (Blindado contra errores)
    pdf_bytes = None
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        pdf.cell(0, 10, clean_text(f"Usuario Investigado: {username}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(5)
        
        # Encabezados Tabla
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(50, 8, clean_text("Plataforma"), 1, 0, 'L', 1)
        pdf.cell(40, 8, clean_text("Categoría"), 1, 0, 'L', 1)
        pdf.cell(100, 8, clean_text("Enlace"), 1, 1, 'L', 1)
        
        # Filas
        pdf.set_font("Arial", size=8)
        for item in results:
            name = clean_text(item['name'][:25])
            cat = clean_text(item['category'][:20])
            uri = clean_text(item['uri'][:60])
            
            pdf.cell(50, 8, name, 1)
            pdf.cell(40, 8, cat, 1)
            # Celda con enlace
            pdf.set_text_color(0, 0, 255)
            pdf.cell(100, 8, uri, 1, 1, link=item['uri'])
            pdf.set_text_color(0, 0, 0)
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e:
        print(f"Error generando PDF: {e}") # Log interno para depuración
        
    return csv, txt.getvalue(), pdf_bytes

# --- 7. MODAL DE DETALLES ---
@st.dialog("Detalles del Perfil")
def show_details_modal(item):
    st.markdown(f"### {item['name']}")
    st.caption(f"Categoría: {item['category']}")
    st.markdown("---")
    
    # Imagen centrada 60%
    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        st.image(item['image'], caption="Vista Previa", use_column_width=True)
    
    st.markdown("---")
    # Botón de enlace (Verde)
    st.link_button("🔗 Ir al Sitio Oficial", item['uri'], type="primary", use_container_width=True)


# --- 8. BARRA LATERAL (Siempre visible) ---
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

# --- 9. INTERFAZ PRINCIPAL ---
st.markdown("<h1 style='text-align: center;'>WhatsMyName Web</h1>", unsafe_allow_html=True)
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

# Contenedor de Resultados (Placeholder)
results_container = st.container()

# Lógica de Ejecución
if run_btn and username:
    st.session_state.results = []
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    processed = 0
    
    # Creamos la cuadrícula vacía que iremos llenando
    with results_container:
        st.markdown("### ⏳ Analizando...")
        grid_placeholder = st.empty()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Barra de progreso suave
            if processed % 5 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Verificando: {processed}/{len(target_sites)}")
            
            if res:
                st.session_state.results.append(res)
                # Redibujar cuadrícula
                with grid_placeholder.container():
                    cols = st.columns(4)
                    for i, item in enumerate(st.session_state.results):
                        with cols[i % 4]:
                            with st.container(border=True):
                                st.markdown(f"**{item['name']}**")
                                st.caption(item['category'])
                                
                                # Botón Modal (Clave única usando índice)
                                if st.button("👁️ Ver", key=f"v_{i}_{item['name']}"):
                                    show_details_modal(item)
                                
                                # Enlace directo
                                st.markdown(f"<a href='{item['uri']}' target='_blank' style='text-decoration:none; color:#1c3961; font-weight:bold; font-size:0.9em;'>🔗 Enlace Directo</a>", unsafe_allow_html=True)

    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# Renderizado Persistente (Si hay resultados y no estamos buscando)
elif st.session_state.results:
    with results_container:
        st.divider()
        st.markdown(f"### 🎯 Resultados: {len(st.session_state.results)}")
        
        cols = st.columns(4)
        for i, item in enumerate(st.session_state.results):
            with cols[i % 4]:
                with st.container(border=True):
                    st.markdown(f"**{item['name']}**")
                    st.caption(item['category'])
                    
                    if st.button("👁️ Ver", key=f"p_v_{i}_{item['name']}"):
                        show_details_modal(item)
                    
                    st.markdown(f"<a href='{item['uri']}' target='_blank' style='text-decoration:none; color:#1c3961; font-weight:bold; font-size:0.9em;'>🔗 Enlace Directo</a>", unsafe_allow_html=True)

# --- 10. ZONA DE DESCARGA ---
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
            st.warning("⚠️ PDF no disponible (caracteres no soportados detectados)")

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)