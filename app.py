import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Configuración de la página web
st.set_page_config(page_title="Grenergy - Dashboard Energético", layout="wide")

st.title("🇪🇺 Panel de Control: Precios de Mercados Eléctricos")
st.markdown("Visualización analítica de precios horarios de energía homogeneizados en **Euros (€/MWh)**.")
st.markdown("---")

# 1. DIRECCIÓN DE NUESTRA API REST LOCAL
API_URL = "http://127.0.0.1:8000/api/v1/precios"
API_KEY = "grenergy_2026_secure_token"  # El token que configuramos en api.py

headers = {"X-API-Key": API_KEY}

# 2. PETICIÓN SEGURA AL BACKEND
try:
    with st.spinner("Consultando datos reales mediante API REST securizada..."):
        respuesta = requests.get(API_URL, headers=headers)
        
    if respuesta.status_code == 200:
        datos = respuesta.json()
        df = pd.DataFrame(datos)
        
        # Formatear la fecha para que los gráficos la entiendan perfectamente
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
        
        # --- SECCIÓN DE FILTROS EN LA BARRA LATERAL ---
        st.sidebar.header("🎛️ Filtros de Análisis")
        
        # Selector de países dinámico
        lista_paises = sorted(df['pais'].unique().tolist())
        paises_seleccionados = st.sidebar.multiselect(
            "Selecciona países para comparar:",
            options=lista_paises,
            default=lista_paises
        )
        
        # Filtrar el dataframe con la selección del usuario
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
            # Mejorar el diseño visual de la gráfica
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
            
    else:
        st.error(f"❌ Error de Autenticación/Conexión con la API: Código {respuesta.status_code}")
        st.write(respuesta.json())

except requests.exceptions.ConnectionError:
    st.error("❌ Error de comunicación: No se pudo conectar con la API REST.")
    st.info("Asegúrate de que el script 'api.py' siga ejecutándose en la otra terminal en el puerto 8000.")