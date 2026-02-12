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

# --- 2. ESTILOS CSS PROFESIONALES ---
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

    /* TARJETAS DE RESULTADOS */
    /* Estilo para el contenedor del expander y la tarjeta */
    .stExpander {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }
    
    /* Títulos dentro de las tarjetas */
    .card-title {
        color: #1c3961;
        font-weight: bold;
        font-size: 1rem;
    }
    .card-cat {
        color: #666;
        font-size: 0.8rem;
        background: #f0f2f5;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 5px;
    }

    /* Footer */
    .footer-credits {
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #ddd;
        font-size: 0.85em;
        color: #666;
        background-color: #f4f7f6;
        width: 100%;
    }
    .footer-credits a {
        color: #1c3961;
        font-weight: bold;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. BARRA LATERAL (SIDEBAR) ---
# Se coloca al principio para garantizar su carga
with st.sidebar:
    # Intento de cargar logo, si falla usa texto
    try:
        st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    except:
        st.header("ManuelBot59")
        
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🎓 Cursos](https://manuelbot59.com/formacion/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.markdown("### 📞 Contacto")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")
    st.markdown("---")
    st.caption("v2.1 Stable | Powered by WhatsMyName")

# --- 4. FUNCIONES Y LÓGICA ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
APP_URL = "https://whatsmyname.streamlit.app/" 

@st.cache_data
def load_sites():
    try:
        response = requests.get(WMN_DATA_URL)
        data = response.json()
        return data['sites']
    except Exception as e:
        st.error(f"Error cargando base de datos: {e}")
        return []

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(uri, headers=headers, timeout=6)
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            
            # Simulamos obtención de imagen/favicon
            domain = uri.split('/')[2]
            favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
            
            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat'],
                "image": favicon
            }
    except:
        return None
    return None

# --- FUNCION CRÍTICA: LIMPIAR TEXTO PARA PDF ---
def clean_text(text):
    """Elimina caracteres que rompen el PDF (emojis, caracteres raros)"""
    if not isinstance(text, str):
        return str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- CLASE PDF ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, clean_text('Reporte SOCMINT - WhatsMyName Web'), 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, clean_text('Herramienta: WhatsMyName Web | Autor: Manuel Travezaño'), 0, 1, 'C')
        self.set_text_color(0, 0, 255)
        self.cell(0, 5, APP_URL, 0, 1, 'C', link=APP_URL)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_reports(results, username):
    # CSV
    df = pd.DataFrame(results)
    csv = df.to_csv(index=False).encode('utf-8')
    
    # TXT
    txt_buffer = io.StringIO()
    txt_buffer.write(f"REPORTE DE INVESTIGACION - USUARIO: {username}\n")
    txt_buffer.write(f"Autor: Manuel Travezaño\n")
    txt_buffer.write(f"Herramienta: {APP_URL}\n")
    txt_buffer.write("="*50 + "\n\n")
    for item in results:
        txt_buffer.write(f"Sitio: {item['name']}\nURL: {item['uri']}\nCategoria: {item['category']}\n{'-'*30}\n")
    
    # PDF
    try:
        pdf = PDFReport()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        pdf.cell(0, 10, clean_text(f"Usuario Investigado: {username}"), ln=1)
        pdf.cell(0, 10, f"Total Hallazgos: {len(results)}", ln=1)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(50, 10, "Plataforma", 1)
        pdf.cell(40, 10, clean_text("Categoría"), 1)
        pdf.cell(100, 10, "Enlace", 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=9)
        for item in results:
            name = clean_text(item['name'][:25])
            cat = clean_text(item['category'][:20])
            uri = clean_text(item['uri'][:55])
            
            pdf.cell(50, 10, name, 1)
            pdf.cell(40, 10, cat, 1)
            pdf.cell(100, 10, uri, 1)
            pdf.ln()
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore') 
        # NOTA: 'ignore' aquí es el segundo filtro de seguridad si clean_text fallara
    except Exception as e:
        return csv, txt_buffer.getvalue(), None # Retorna None si falla PDF para no romper la app
    
    return csv, txt_buffer.getvalue(), pdf_bytes

# --- 5. INTERFAZ PRINCIPAL ---

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

# Estado
if "results" not in st.session_state:
    st.session_state.results = []

# Contenedor de Resultados (Fuera del 'if' para persistencia)
results_container = st.container()

# --- EJECUCIÓN ---
if run_btn and username:
    st.session_state.results = []
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    processed = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Actualizar barra cada 5 para rendimiento
            if processed % 5 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Analizando: {processed}/{len(target_sites)}")
            
            if res:
                st.session_state.results.append(res)
                # Forzar redibujado progresivo (Opcional, consume recursos pero es visual)
                # Si se siente lento, comentar las siguientes 3 líneas y dejar solo el render final
                
    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# --- RENDERIZADO (SE EJECUTA SIEMPRE QUE HAYA DATOS) ---
if st.session_state.results:
    with results_container:
        st.divider()
        st.markdown(f"### 🎯 Resultados: {len(st.session_state.results)}")
        
        # Grid de 4 columnas
        cols = st.columns(4)
        for i, item in enumerate(st.session_state.results):
            col = cols[i % 4]
            with col:
                # Usamos expaners nativos, son más estables que los modales
                label_text = f"✅ {item['name']}"
                with st.expander(label_text, expanded=False):
                    st.image(item['image'], width=64) # Icono pequeño
                    st.caption(f"Categoría: {item['category']}")
                    st.link_button("🔗 Ir al Perfil", item['uri'], use_container_width=True)

    # --- ZONA DE DESCARGA ---
    st.divider()
    st.subheader("📥 Exportar Reporte")
    
    csv_data, txt_data, pdf_data = generate_reports(st.session_state.results, username)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📄 Descargar CSV", csv_data, f"report_{username}.csv", "text/csv", use_container_width=True)
    with col2:
        st.download_button("📝 Descargar TXT", txt_data, f"report_{username}.txt", "text/plain", use_container_width=True)
    with col3:
        if pdf_data:
            st.download_button("📕 Descargar PDF", pdf_data, f"report_{username}.pdf", "application/pdf", use_container_width=True)
        else:
            st.error("Error generando PDF (Caracteres no soportados)")

# --- FOOTER SIEMPRE VISIBLE ---
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)