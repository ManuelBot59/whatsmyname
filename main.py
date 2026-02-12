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

# --- 2. GESTIÓN DEL ESTADO (MEMORIA) ---
# Esto evita que se borre todo al dar clic en un botón
if "results" not in st.session_state:
    st.session_state.results = []
if "is_searching" not in st.session_state:
    st.session_state.is_searching = False

# --- 3. ESTILOS CSS CORREGIDOS ---
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

    /* ESTILO DE LA TARJETA (Uniformidad) */
    /* Aplicamos el estilo a un contenedor personalizado, no a la columna entera */
    .custom-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        border-left: 5px solid #27ae60;
        height: 250px; /* Altura fija para que todos sean iguales */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        border-color: #00c6fb;
    }

    .card-title {
        font-weight: bold;
        font-size: 1.1rem;
        color: #1c3961;
        margin-bottom: 5px;
    }
    
    .card-cat {
        font-size: 0.8rem;
        background: #f0f2f5;
        padding: 2px 8px;
        border-radius: 4px;
        color: #666;
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

# --- 5. CLASE PDF (PIE DE PÁGINA PERSONALIZADO) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte SOCMINT - WhatsMyName Web', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-25) # Un poco más arriba
        self.set_font('Arial', 'I', 8)
        # Nombre y Herramienta
        self.cell(0, 5, f'Herramienta: WhatsMyName Web | Autor: Manuel Travezano', 0, 1, 'C')
        # Enlace clickeable (aunque visualmente es texto en FPDF básico, ponemos la URL)
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

# --- 6. MODAL ---
@st.dialog("Detalles Extraídos")
def show_details(item):
    st.caption("PLATAFORMA")
    st.subheader(item['name'])
    st.caption(f"Categoría: {item['category']}")
    st.markdown("---")
    
    # Imagen al 60%
    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        st.image(item['image'], caption="Evidencia", use_column_width=True)
    
    st.markdown("---")
    # Botón dentro del modal
    st.link_button("🔗 Ir al Perfil", item['uri'], type="primary", use_container_width=True)


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

# --- 8. LÓGICA DE EJECUCIÓN ---

if run_btn and username:
    # Reiniciar resultados al buscar de nuevo
    st.session_state.results = []
    
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    # Contenedor para mostrar resultados progresivamente
    results_container = st.container()
    
    processed = 0
    found_temp = 0
    
    # Hilos
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(check_site, s, username): s for s in target_sites}
        
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Actualizar barra cada cierto tiempo
            if processed % 5 == 0 or processed == len(target_sites):
                prog_bar.progress(processed / len(target_sites))
                status_text.caption(f"Analizando: {processed}/{len(target_sites)}")
            
            if res:
                # Agregar al estado y a la lista temporal
                st.session_state.results.append(res)
                
                # --- RENDERIZADO PROGRESIVO EN TIEMPO REAL ---
                # Calculamos si necesitamos una nueva fila o usar la existente
                # Truco: Renderizamos TODO el grid de nuevo en el container cada vez que hay un hallazgo
                # Esto asegura que el layout (4 columnas) siempre esté perfecto
                with results_container:
                    # Limpiamos el contenedor anterior visualmente (Streamlit lo hace auto al re-escribir)
                    # Grid Logic:
                    results = st.session_state.results
                    cols_per_row = 4
                    for i in range(0, len(results), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j in range(cols_per_row):
                            if i + j < len(results):
                                item = results[i + j]
                                with cols[j]:
                                    # Usamos un container con estilo CSS personalizado para la tarjeta
                                    with st.container(border=True):
                                        st.markdown(f"**{item['name']}**")
                                        st.caption(f"{item['category']}")
                                        if st.button("👁️ Ver Detalles", key=f"btn_{item['uri']}"):
                                            show_details(item)
    
    prog_bar.progress(100)
    if len(st.session_state.results) > 0:
        status_text.success(f"✅ Finalizado. {len(st.session_state.results)} perfiles encontrados.")
    else:
        status_text.warning("❌ No se encontraron resultados.")

# --- 9. RENDERIZADO PERSISTENTE (Para que no desaparezca al clicar botones) ---
# Esta parte se ejecuta si NO estamos buscando, pero hay resultados en memoria
elif st.session_state.results:
    st.markdown("### 🎯 Resultados (Persistentes)")
    
    results = st.session_state.results
    cols_per_row = 4
    
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(results):
                item = results[i + j]
                with cols[j]:
                    with st.container(border=True): # Borde nativo de Streamlit que se ve limpio
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"{item['category']}")
                        # El botón DEBE tener una key única basada en la URL para no duplicarse
                        if st.button("👁️ Ver Detalles", key=f"persistent_{item['uri']}"):
                            show_details(item)

# --- 10. ZONA DE DESCARGA ---
if st.session_state.results:
    st.divider()
    st.subheader("📥 Exportar Reporte")
    
    csv_data, txt_data, pdf_data = generate_reports(st.session_state.results, username)
    
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