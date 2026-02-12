import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS (Grid y Modal) ---
st.markdown("""
<style>
    /* Ocultar elementos nativos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Fondo general */
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

    /* ESTILO DE TARJETAS (Pequeños cuadrados) */
    div[data-testid="stColumn"] > div > div > div > div.stButton > button {
        background-color: white;
        color: #1c3961;
        border: 1px solid #ddd;
        border-radius: 10px;
        height: 120px; /* Altura fija para que sean cuadrados */
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

    /* Texto dentro de los botones/tarjetas */
    div[data-testid="stColumn"] > div > div > div > div.stButton > button p {
        font-size: 16px;
        font-weight: bold;
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
            
            # Intentamos obtener favicon para la imagen (ya que no hacemos scraping profundo por velocidad)
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
    # Cabecera del modal con botón a la derecha
    col_info, col_link = st.columns([2, 1.5])
    
    with col_info:
        st.caption("PLATAFORMA")
        st.subheader(item['name'])
        st.caption(f"Categoría: {item['category']}")
        
    with col_link:
        # Botón para ir al sitio (Verde y llamativo)
        st.markdown(f"""
            <a href="{item['uri']}" target="_blank" style="
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                display: block;
                text-align: center;
                margin-top: 10px;
            ">Visitar Perfil ➜</a>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Imagen centrada al 60%
    c1, c2, c3 = st.columns([1, 3, 1]) # Columnas para centrar (1 espacio, 3 contenido, 1 espacio)
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.image(item['image'], caption="Evidencia Visual", width=200) # Width 200px es aprox 60% en modal
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.success("✅ El usuario ha sido detectado con éxito en esta plataforma.")

# --- 5. INTERFAZ PRINCIPAL ---

# Sidebar
with st.sidebar:
    st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    st.markdown("### 📌 Navegación")
    st.markdown("- [🏠 Inicio](https://manuelbot59.com/)")
    st.markdown("- [🎓 Cursos](https://manuelbot59.com/formacion/)")
    st.markdown("- [🕵️ OSINT](https://manuelbot59.com/osint/)")
    st.markdown("---")
    st.info("Herramienta optimizada para velocidad y concurrencia.")

# Main
st.title("WhatsMyName Web")
st.markdown("### Herramienta SOCMINT | Manuel Travezaño")

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

# Contenedor de resultados
if "results_list" not in st.session_state:
    st.session_state.results_list = []

if run_btn and username:
    st.session_state.results_list = [] # Limpiar anterior
    target_sites = sites if cat_filter == "Todas" else [s for s in sites if s['cat'] == cat_filter]
    
    prog_bar = st.progress(0)
    status = st.empty()
    
    # Grid Container
    grid_container = st.container()
    
    processed = 0
    
    # Ejecución rápida
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

# --- RENDERIZADO DE RESULTADOS (GRID) ---
if st.session_state.results_list:
    st.markdown("### 🎯 Resultados Encontrados")
    
    # Lógica de Grid (4 columnas por fila)
    cols_per_row = 4
    results = st.session_state.results_list
    
    # Iterar sobre los resultados en pasos de 4
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        # Llenar cada columna de la fila actual
        for j in range(cols_per_row):
            if i + j < len(results):
                item = results[i + j]
                with cols[j]:
                    # IMPORTANTE: El botón usa el nombre del sitio como etiqueta.
                    # Al hacer click, se llama a show_details(item)
                    if st.button(f"✅ {item['name']}\n\n({item['category']})", key=f"btn_{item['uri']}"):
                        show_details(item)

# Footer
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)