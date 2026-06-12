import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# Configuración de la página web
st.set_page_config(page_title="Grenergy - Dashboard Energético", layout="wide")

st.title("🇪🇺 Panel de Control: Precios de Mercados Eléctricos")
st.markdown("Visualización analítica de precios horarios de energía homogeneizados en **Euros (€/MWh)**.")
st.markdown("---")

# 1. DIRECCIÓN DE NUESTRA API REST LOCAL
API_URL = "http://127.0.0.1:8000/api/v1/precios"
API_KEY = "grenergy_2026_secure_token"
headers = {"X-API-Key": API_KEY}

df = None
modo_conexion = ""

# 2. INTENTO DE PETICIÓN SEGURA AL BACKEND (Con un timeout de 3 segundos)
try:
    with st.spinner("Consultando datos reales mediante API REST securizada..."):
        # Añadimos un timeout para que no se quede colgado en la nube buscando la API local
        respuesta = requests.get(API_URL, headers=headers, timeout=3)
        
    if respuesta.status_code == 200:
        datos = respuesta.json()
        df = pd.DataFrame(datos)
        modo_conexion = "api"
    else:
        raise requests.exceptions.ConnectionError

except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
    # 3. MECANISMO DE RESPALDO (FALLBACK) PARA STREAMLIT CLOUD
    # Si la API no está accesible, lee el CSV del repositorio directamente
    DATA_FILE = "gold_precios_horarios_europa.csv"
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        modo_conexion = "csv"
    else:
        st.error("❌ Error crítico: No se pudo conectar a la API REST ni se encontró el archivo CSV de respaldo.")
        st.stop()

# --- RENDERIZADO DE LA INTERFAZ (SI HAY DATOS) ---
if df is not None and not df.empty:
    
    # Mostrar banner informativo según el tipo de conexión
    if modo_conexion == "api":
        st.success("🔌 Conectado exitosamente a la API REST local (Entorno de Desarrollo).")
    else:
        st.info("ℹ️ **Modo Demostración Activo:** La API REST local no es accesible desde la nube. Cargando el snapshot de la Capa Gold directamente desde el repositorio de GitHub.")

    # Formatear la fecha para los gráficos
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    
    # --- SECCIÓN DE FILTROS EN LA BARRA LATERAL ---
    st.sidebar.header("🎛️ Filtros de Análisis")
    
    lista_paises = sorted(df['pais'].unique().tolist())
    paises_seleccionados = st.sidebar.multiselect(
        "Selecciona países para comparar:",
        options=lista_paises,
        default=lista_paises
    )
    
    df_filtrado = df[df['pais'].isin(paises_seleccionados)]
    
    # --- RECUADROS DE MÉTRICAS CLAVE ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Muestras Horarias", value=len(df_filtrado))
    with col2:
        precio_medio = df_filtrado['precio_mwh'].mean() if not df_filtrado.empty else 0
        st.metric(label="Precio Promedio General", value=f"{precio_medio:.2f} €/MWh")
    with col3:
        st.metric(label="Mercados Activos", value=len(paises_seleccionados))
        
    st.markdown("---")
    
    # --- GRÁFICA INTERACTIVA DE LÍNEAS (Plotly) ---
    st.subheader("📈 Curva de Precios Day-Ahead (Frecuencia Horaria)")
    
    if not df_filtrado.empty:
        fig = px.line(
            df_filtrado,
            x="timestamp_utc",
            y="precio_mwh",
            color="pais",
            labels={"timestamp_utc": "Fecha y Hora (UTC)", "precio_mwh": "Precio (€/MWh)", "pais": "País"},
            template="plotly_white",
            height=500
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- TABLA DE DATOS DETALLADA ---
        st.subheader("📋 Histórico Homogeneizado de Precios")
        st.dataframe(
            df_filtrado.sort_values(by="timestamp_utc", ascending=False), 
            use_container_width=True
        )
    else:
        st.warning("Por favor, selecciona al menos un país en la barra lateral para desplegar los análisis.")