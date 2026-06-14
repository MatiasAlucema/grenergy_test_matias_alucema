import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ── Configuración inicial ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Grenergy Energy Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Fondo principal oscuro */
    .main { background-color: #0f1a15; }
    section[data-testid="stMain"] { background-color: #0f1a15; }

    /* Sidebar verde corporativo */
    [data-testid="stSidebar"] { background-color: #00A36C; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: white !important; }

    /* Títulos principales */
    h1, h2, h3 { color: #00A36C !important; }

    /* Texto general en blanco */
    p, span, div { color: #e0e0e0; }

    /* Métricas KPI */
    div[data-testid="stMetric"] {
        background-color: #1e3a2f;
        border-left: 5px solid #00A36C;
        padding: 16px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #a8d5b5 !important;
        font-size: 0.85rem;
    }
    div[data-testid="stMetricValue"] > div {
        color: #ffffff !important;
        font-size: 1.5rem;
        font-weight: 700;
    }

    /* Separador */
    hr { border-color: #1e3a2f; }

    /* Expander */
    details { background-color: #1a2e23; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🇪🇺 Dashboard de Precios de Energía")
st.markdown("Análisis comparativo de mercados eléctricos en Europa (€/MWh).")

# ── Constantes ────────────────────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"
API_KEY  = os.getenv("GRENERGY_API_KEY", "")
HEADERS  = {"X-API-Key": API_KEY}
CSV_FALLBACK = os.path.join(os.path.dirname(__file__), "gold_precios_horarios_europa.csv")
PAISES_COLOR = {
    "Alemania": "#00A36C",
    "España":   "#2ecc71",
    "Polonia":  "#76d7c4",
    "Rumania":  "#004d33",
}

# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data() -> tuple[pd.DataFrame, str]:
    try:
        res = requests.get(
            f"{API_BASE}/api/v1/precios",
            headers=HEADERS,
            params={"limit": 10000},
            timeout=5,
        )
        if res.status_code == 200:
            return pd.DataFrame(res.json()["data"]), "API REST (Local)"
        else:
            st.sidebar.warning(f"API respondió {res.status_code}. Usando CSV.")
    except Exception as e:
        st.sidebar.warning(f"API no disponible. Usando CSV.")

    if not os.path.exists(CSV_FALLBACK):
        st.error("No se encontró el CSV de datos.")
        st.stop()

    return pd.read_csv(CSV_FALLBACK), "Archivo CSV (Snapshot)"


df_raw, origen = load_data()
df_raw["timestamp_utc"] = pd.to_datetime(df_raw["timestamp_utc"], utc=True)

# ── Sidebar: filtros ──────────────────────────────────────────────────────────
st.sidebar.header("🎛️ Filtros de Análisis")

todos_paises = sorted(df_raw["pais"].unique())
paises_sel = st.sidebar.multiselect("Países:", todos_paises, default=todos_paises)

fecha_min = df_raw["timestamp_utc"].min().date()
fecha_max = df_raw["timestamp_utc"].max().date()

st.sidebar.markdown("**Rango de fechas:**")
fecha_inicio = st.sidebar.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
fecha_fin    = st.sidebar.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

if fecha_inicio > fecha_fin:
    st.sidebar.error("La fecha de inicio debe ser anterior a la fecha fin.")
    st.stop()

granularidad = st.sidebar.radio(
    "Granularidad:",
    ["Horaria (original)", "Diaria (agregada)"],
    index=0,
    help="PT15M (Polonia/España/Rumanía) y PT60M (Alemania) se normalizan a 1h en la capa Gold.",
)

st.sidebar.markdown("---")
st.sidebar.info(f"📦 Fuente: **{origen}**")

# ── Filtrado ──────────────────────────────────────────────────────────────────
mask = (
    df_raw["pais"].isin(paises_sel) &
    (df_raw["timestamp_utc"].dt.date >= fecha_inicio) &
    (df_raw["timestamp_utc"].dt.date <= fecha_fin)
)
df_f = df_raw[mask].copy().sort_values(["pais", "timestamp_utc"])

if df_f.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

if granularidad == "Diaria (agregada)":
    df_f["fecha"] = df_f["timestamp_utc"].dt.date
    df_f = (
        df_f.groupby(["fecha", "pais"], as_index=False)["precio_mwh"]
        .mean()
        .rename(columns={"fecha": "timestamp_utc"})
    )
    df_f["timestamp_utc"] = pd.to_datetime(df_f["timestamp_utc"])
    df_f["precio_mwh"] = df_f["precio_mwh"].round(2)

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Precio Promedio", f"{df_f['precio_mwh'].mean():.2f} €/MWh")
col2.metric("Precio Máximo",   f"{df_f['precio_mwh'].max():.2f} €/MWh")
col3.metric("Precio Mínimo",   f"{df_f['precio_mwh'].min():.2f} €/MWh")
col4.metric("Registros",       f"{len(df_f):,}")

st.markdown("---")

# ── Gráfico de curva de precios ───────────────────────────────────────────────
st.subheader("📈 Curva de Precios")
color_map = {p: PAISES_COLOR.get(p, "#999") for p in paises_sel}

fig_line = px.line(
    df_f,
    x="timestamp_utc",
    y="precio_mwh",
    color="pais",
    template="plotly_dark",
    color_discrete_map=color_map,
    labels={"timestamp_utc": "Fecha/Hora (UTC)", "precio_mwh": "€/MWh", "pais": "País"},
)
fig_line.update_layout(
    hovermode="x unified",
    legend_title_text="País",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0f1a15",
)
fig_line.update_traces(connectgaps=True)
st.plotly_chart(fig_line, use_container_width=True)

# ── Box plot comparativo ──────────────────────────────────────────────────────
st.subheader("📊 Distribución Comparativa por País")
fig_box = px.box(
    df_f,
    x="pais",
    y="precio_mwh",
    color="pais",
    template="plotly_dark",
    color_discrete_map=color_map,
    labels={"pais": "País", "precio_mwh": "€/MWh"},
)
fig_box.update_layout(
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0f1a15",
)
st.plotly_chart(fig_box, use_container_width=True)

# ── Tabla de datos brutos ─────────────────────────────────────────────────────
with st.expander("🔍 Ver datos brutos"):
    st.dataframe(
        df_f.sort_values("timestamp_utc", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )
    csv_export = df_f.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar CSV filtrado",
        data=csv_export,
        file_name=f"grenergy_precios_{fecha_inicio}_{fecha_fin}.csv",
        mime="text/csv",
    )