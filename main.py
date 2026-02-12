import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import tempfile

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS ---
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

    /* Estilo de Tarjetas (Botones del Grid) */
    div[data-testid="stColumn"] > div > div > div > div.stButton > button {
        background-color: white;
        color: #1c3961;
        border: 1px solid #ddd;
        border-radius: 10px;
        height: 120px;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    
    div[data-testid="stColumn"] > div > div > div > div.stButton > button:hover {
        border-color: #00c6fb;
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        background-color: #f0f9ff;
    }

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
LOGO_URL = "https://manuelbot59.com/images/FirmaManuelBot59.png" # Logo para el PDF

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

# --- 4. CLASE PDF PERSONALIZADA ---
class PDFReport(FPDF):
    def header(self):
        # Intentamos descargar el logo temporalmente para ponerlo en el PDF
        try:
            logo_path = "logo_temp.png"
            response = requests.get(LOGO_URL)
            if response.status_code == 200:
                with open(logo_path, 'wb') as f:
                    f.write(response.content)
                self.image(logo_path, 10, 8, 50)
        except:
            pass
            
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Reporte de Investigacion OSINT', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Generado por manuelbot59.com', 0, 0, 'C')

# --- 5. VENTANA EMERGENTE (MODAL) ---
@st.dialog("Detalles Extraídos")
def show_details(item):
    col_info, col_link = st.columns([2, 1.5])
    
    with col_info:
        st.caption("PLATAFORMA")
        st.subheader(item['name'])
        st.caption(f"Categoría: {item['category']}")
        
    with col_link:
        st.write("") # Espacio
        # Usamos st.link_button nativo para asegurar que funcione el estilo y el enlace
        st.link_button("🔗 Ver perfil Detectado", item['uri'], type="primary", use_container_width=True)

    st.markdown("---")
    
    # Imagen centrada al 60%
    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        # Mostramos la imagen
        st.image(item['image'], caption="Evidencia Visual", width=200)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.success("✅ Hallazgo positivo.")

# --- 6. INTERFAZ PRINCIPAL ---

with st.sidebar:
    st.image(LOGO_URL, use_column_width=True)
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🎓 Cursos](https://manuelbot59.com/formacion/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.markdown("### 📞 Contacto")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    # Cambio solicitado: "Telegram Soporte"
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

if "results_list" not in st.session_state:
    st.session_state.results_list = []

if run_btn and username:
    st.session_state.results_list = []
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status = st.empty()
    grid_container = st.container()
    
    processed = 0
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            if processed % 10 == 0:
                prog_bar.progress(processed / len(target_sites))
                status.text(f"Analizando: {processed}/{len(target_sites)}")
            
            if res:
                st.session_state.results_list.append(res)
    
    prog_bar.empty()
    status.success(f"Análisis finalizado. {len(st.session_state.results_list)} cuentas encontradas.")

# --- 7. RENDERIZADO Y EXPORTACIÓN ---
if st.session_state.results_list:
    st.markdown("### 🎯 Resultados Encontrados")
    
    # Grid Layout
    cols_per_row = 4
    results = st.session_state.results_list
    
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(results):
                item = results[i + j]
                with cols[j]:
                    # Botón que abre el modal
                    if st.button(f"✅ {item['name']}\n\n({item['category']})", key=f"btn_{item['uri']}"):
                        show_details(item)

    # --- ZONA DE EXPORTACIÓN ---
    st.divider()
    st.subheader("📥 Descargar Reporte")
    
    col_pdf, col_csv, col_txt = st.columns(3)
    
    # Preparar datos
    df = pd.DataFrame(st.session_state.results_list)
    
    # 1. Exportar CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    csv_data += b"\n\nGenerado por: https://manuelbot59.com"
    
    with col_csv:
        st.download_button(
            label="📄 Descargar CSV",
            data=csv_data,
            file_name=f"reporte_{username}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 2. Exportar TXT
    txt_buffer = io.StringIO()
    txt_buffer.write(f"REPORTE DE INVESTIGACION OSINT - USUARIO: {username}\n")
    txt_buffer.write("="*50 + "\n\n")
    for item in st.session_state.results_list:
        txt_buffer.write(f"Sitio: {item['name']}\nURL: {item['uri']}\nCategoria: {item['category']}\n{'-'*30}\n")
    txt_buffer.write(f"\nGenerado por: https://manuelbot59.com\n")
    
    with col_txt:
        st.download_button(
            label="📝 Descargar TXT",
            data=txt_buffer.getvalue(),
            file_name=f"reporte_{username}.txt",
            mime="text/plain",
            use_container_width=True
        )

    # 3. Exportar PDF (Con Logo)
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.cell(200, 10, txt=f"Objetivo: {username}", ln=1, align='L')
        pdf.cell(200, 10, txt=f"Total Encontrados: {len(results)}", ln=1, align='L')
        pdf.ln(10)
        
        # Tabla simple en PDF
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(50, 10, "Sitio", 1)
        pdf.cell(40, 10, "Categoria", 1)
        pdf.cell(100, 10, "Enlace", 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=9)
        for item in results:
            pdf.cell(50, 10, item['name'][:25], 1)
            pdf.cell(40, 10, item['category'], 1)
            pdf.cell(100, 10, item['uri'][:60], 1) # Recortar si es muy largo
            pdf.ln()
            
        # Firma Final
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Reporte generado por WhatsMyName Web - manuelbot59.com", 0, 1, 'C')
        
        # Guardar en buffer
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
        
        with col_pdf:
            st.download_button(
                label="📕 Descargar PDF",
                data=pdf_bytes,
                file_name=f"reporte_{username}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    except Exception as e:
        with col_pdf:
            st.error(f"Error PDF: {e}")

# Footer final
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)