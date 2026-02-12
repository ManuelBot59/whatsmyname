import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. CONFIGURACIÓN DE PÁGINA (Título de Pestaña) ---
st.set_page_config(
    page_title="WhatsMyName Web | Herramienta SOCMINT | Manuel Travezaño",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS (Adaptados a tu Marca: Azul #1c3961 y Blanco/Gris) ---
st.markdown("""
<style>
    /* Ocultar elementos nativos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Fondo general más limpio */
    .stApp {
        background-color: #f4f7f6;
        color: #333;
    }

    /* Títulos Principales */
    h1 {
        background: linear-gradient(45deg, #1c3961, #0066a9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica', sans-serif;
        font-weight: 800;
        text-align: center;
        padding-top: 1rem;
    }
    
    /* Subtítulos */
    h3 {
        color: #1c3961;
        text-align: center;
        font-weight: 600;
        margin-bottom: 2rem;
    }

    /* Tarjetas de Resultados */
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #27ae60; /* Tu verde corporativo */
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    
    /* Enlaces en las tarjetas */
    .result-link {
        color: #1c3961 !important;
        text-decoration: none;
        font-weight: bold;
        font-size: 1.1em;
        display: block;
        margin-top: 5px;
    }
    .result-link:hover {
        color: #27ae60 !important;
        text-decoration: underline;
    }

    /* Badges de Categoría */
    .category-badge {
        background-color: #eef2f6;
        color: #1c3961;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: bold;
        float: right;
        text-transform: uppercase;
    }

    /* Botón Principal (Estilo ManuelBot) */
    .stButton > button {
        background-color: #1c3961;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #0066a9;
        color: white;
        border: none;
    }

    /* Footer de Créditos */
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

# --- LÓGICA DEL MOTOR (Requests puro para velocidad) ---
WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

@st.cache_data
def load_sites():
    try:
        response = requests.get(WMN_DATA_URL)
        data = response.json()
        return data['sites']
    except Exception as e:
        st.error(f"Error conectando con la base de datos: {e}")
        return []

def check_site(site, username):
    uri = site['uri_check'].format(account=username)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        # Timeout corto para velocidad máxima
        r = requests.get(uri, headers=headers, timeout=5)
        
        if r.status_code == site['e_code']:
            if site.get('e_string') and site['e_string'] not in r.text:
                return None
            return {
                "name": site['name'],
                "uri": uri,
                "category": site['cat']
            }
    except:
        return None
    return None

# --- 3. BARRA LATERAL (Simulando tu Menú Web) ---
with st.sidebar:
    # Tu Logo Oficial
    st.image("https://manuelbot59.com/images/FirmaManuelBot59.png", use_column_width=True)
    
    st.markdown("### 📌 Navegación")
    st.markdown("""
    - [🏠 Inicio](https://manuelbot59.com/)
    - [🎓 Cursos](https://manuelbot59.com/formacion/)
    - [🛒 Tienda](https://manuelbot59.com/tienda/)
    - [🕵️ OSINT](https://manuelbot59.com/osint/)
    """)
    
    st.markdown("---")
    st.markdown("### 📞 Contacto")
    st.markdown("📧 **Email:** ManuelBot@proton.me")
    st.markdown("✈️ **Telegram Soporte:** [ManuelBot59](https://t.me/ManuelBot59_Bot)")
    
    st.markdown("---")
    st.info("Esta herramienta realiza una enumeración de usuarios en +500 sitios web públicos utilizando técnicas SOCMINT.")

# --- 4. INTERFAZ PRINCIPAL ---

# Títulos
st.title("WhatsMyName Web")
st.markdown("### Herramienta SOCMINT | Manuel Travezaño")

# Carga de datos
sites = load_sites()
categories = sorted(list(set([s['cat'] for s in sites])))

# Panel de Búsqueda
with st.container():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        username = st.text_input("Usuario a investigar", placeholder="Ej: manuelbot59", label_visibility="collapsed")
    with col2:
        selected_category = st.selectbox("Categoría", ["Todas"] + categories, label_visibility="collapsed")
    with col3:
        start_btn = st.button("🔍 INVESTIGAR")

# Resultados
if start_btn:
    if not username:
        st.warning("⚠️ Por favor ingresa un nombre de usuario.")
    else:
        # Filtro
        target_sites = sites if selected_category == "Todas" else [s for s in sites if s['cat'] == selected_category]
        
        # Barra de progreso y status
        st.divider()
        st.markdown(f"**🔎 Analizando huella digital para:** `{username}` en {len(target_sites)} plataformas...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        found_count = 0
        processed = 0
        
        # Procesamiento Paralelo Rápido (30 hilos)
        with ThreadPoolExecutor(max_workers=30) as executor:
            future_to_site = {executor.submit(check_site, site, username): site for site in target_sites}
            
            for future in as_completed(future_to_site):
                result = future.result()
                processed += 1
                
                # Actualizar barra (cada 5 para no saturar UI)
                if processed % 5 == 0 or processed == len(target_sites):
                    progress_bar.progress(processed / len(target_sites))
                    status_text.caption(f"Progreso: {processed}/{len(target_sites)} sitios verificados")
                
                if result:
                    found_count += 1
                    with results_container:
                        st.markdown(f"""
                        <div class="result-card">
                            <span class="category-badge">{result['category']}</span>
                            <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Sitio detectado:</div>
                            <div style="font-size: 1.2em; font-weight: bold; color: #333;">{result['name']}</div>
                            <a href="{result['uri']}" target="_blank" class="result-link">
                                🔗 Ver Perfil Detectado
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

        progress_bar.progress(100)
        status_text.empty()
        
        if found_count > 0:
            st.success(f"✅ Análisis finalizado. Se encontraron {found_count} perfiles potenciales.")
        else:
            st.warning("❌ No se encontraron perfiles con este nombre de usuario.")

# --- 5. FOOTER / CRÉDITOS ---
st.markdown("""
<div class="footer-credits">
    This tool is powered by <a href="https://github.com/WebBreacher/WhatsMyName" target="_blank">WhatsMyName</a><br>
    Implementation and optimization by <a href="https://x.com/ManuelBot59" target="_blank"><strong>Manuel Travezaño</strong></a>
</div>
""", unsafe_allow_html=True)