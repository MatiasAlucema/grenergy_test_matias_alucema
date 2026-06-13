import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# 1. Configuración inicial
st.set_page_config(page_title="Grenergy Energy Dashboard", layout="wide")

# Estilo personalizado para un look más corporativo
# 1. Configuración de estilo: Paleta Grenergy (Verde y Blanco)
st.markdown("""
    <style>
        /* Fondo general */
        .main { background-color: #FFFFFF; }
        
        /* Sidebar en verde corporativo */
        [data-testid="stSidebar"] {
            background-color: #00A36C; 
            color: white;
        }
        
        /* Títulos y texto en el sidebar */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label {
            color: white !important;
        }

        /* Estilo de las métricas */
        div.stMetric {
            background-color: #f0fdf4;
            border-left: 5px solid #00A36C;
            padding: 15px;
            border-radius: 5px;
        }
        
        /* Encabezados principales */
        h1, h2 { color: #00A36C !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🇪🇺 Dashboard de Precios de Energía")
st.markdown("Análisis comparativo de mercados eléctricos en Europa (€/MWh).")

# 2. Lógica de carga de datos (Resiliente)
@st.cache_data(ttl=3600) # Caché de 1 hora para no saturar
def load_data():
    try:
        # Intento de conexión a API
        res = requests.get("http://127.0.0.1:8000/api/v1/precios", timeout=3)
        if res.status_code == 200:
            return pd.DataFrame(res.json()), "API REST (Local)"
    except:
        pass
    
    # Fallback al CSV
    return pd.read_csv("gold_precios_horarios_europa.csv"), "Archivo CSV (Snapshot)"

df, origen = load_data()
df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])

# 3. Sidebar con filtros
st.sidebar.header("🎛️ Filtros de Análisis")
lista_paises = sorted(df['pais'].unique())
paises_sel = st.sidebar.multiselect("Seleccionar países:", lista_paises, default=lista_paises)

# Filtrado y ordenamiento cronológico
df_f = df[df['pais'].isin(paises_sel)].sort_values(['pais', 'timestamp_utc'])

# 4. Métricas superiores
col1, col2 = st.columns(2)
with col1:
    st.metric("Precio Promedio Seleccionado", f"{df_f['precio_mwh'].mean():.2f} €/MWh")
with col2:
    st.info(f"Fuente de datos: **{origen}**")

# 5. Gráfico principal
st.subheader("📈 Curva de Precios Horarios")
fig = px.line(
    df_f, x="timestamp_utc", y="precio_mwh", color="pais",
    template="plotly_white", markers=True
)
fig.update_layout(hovermode="x unified", legend_title_text="País")
fig.update_traces(connectgaps=True)
st.plotly_chart(fig, use_container_width=True)

# 6. Tabla detalle
with st.expander("Ver datos brutos"):
    st.dataframe(df_f.sort_values("timestamp_utc", ascending=False), use_container_width=True)