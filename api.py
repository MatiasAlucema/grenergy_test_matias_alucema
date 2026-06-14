from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
import os

app = FastAPI(
    title="Grenergy Market API",
    description="API REST segura para consultar precios horarios de mercados europeos.",
    version="1.0"
)

# CORS para que Streamlit pueda consumir la API desde el mismo host
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── 1. SEGURIDAD ──────────────────────────────────────────────────────────────
API_KEY_NAME = "X-API-Key"

# El token se lee SIEMPRE desde variable de entorno. Nunca hardcodeado.
# Arrancar con: export GRENERGY_API_KEY="tu_token_secreto"
API_KEY_SECRET = os.getenv("GRENERGY_API_KEY")
if not API_KEY_SECRET:
    raise RuntimeError(
        "Variable de entorno GRENERGY_API_KEY no configurada. "
        "Ejecútala antes de arrancar: export GRENERGY_API_KEY=<token>"
    )

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verificar_token(api_key: str = Security(api_key_header)) -> str:
    """Valida que el header X-API-Key coincida con el token configurado."""
    if api_key != API_KEY_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: token inválido o no enviado."
        )
    return api_key

# ── 2. RUTA DEL CSV (relativa al script, no al directorio de trabajo) ─────────
DATA_FILE = Path(__file__).parent / "gold_precios_horarios_europa.csv"

def _cargar_datos() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Archivo de datos no encontrado: {DATA_FILE}"
        )
    df = pd.read_csv(DATA_FILE)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df

# ── 3. ENDPOINTS ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
def healthcheck():
    """Comprueba que la API está operativa."""
    return {"status": "ok", "data_file": str(DATA_FILE), "file_exists": DATA_FILE.exists()}


@app.get("/api/v1/precios", tags=["Precios"])
def obtener_precios(
    pais: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    limit: int = 1000,
    offset: int = 0,
    _: str = Security(verificar_token),
):
    """
    Retorna precios horarios en EUR/MWh.

    - **pais**: filtro opcional por país (España, Alemania, Polonia, Rumania).
    - **fecha_inicio**: fecha mínima ISO 8601 (ej. 2026-06-07).
    - **fecha_fin**: fecha máxima ISO 8601 (ej. 2026-06-12).
    - **limit**: máximo de registros devueltos (default 1000).
    - **offset**: desplazamiento para paginación.

    Requiere header: `X-API-Key: <token>`.
    """
    df = _cargar_datos()

    # Filtro por país
    if pais:
        df = df[df["pais"].str.lower() == pais.strip().lower()]

    # Filtro por rango de fechas
    if fecha_inicio:
        try:
            df = df[df["timestamp_utc"] >= pd.to_datetime(fecha_inicio, utc=True)]
        except ValueError:
            raise HTTPException(status_code=400, detail="fecha_inicio no tiene formato válido (YYYY-MM-DD).")

    if fecha_fin:
        try:
            df = df[df["timestamp_utc"] <= pd.to_datetime(fecha_fin, utc=True) + pd.Timedelta(days=1)]
        except ValueError:
            raise HTTPException(status_code=400, detail="fecha_fin no tiene formato válido (YYYY-MM-DD).")

    total = len(df)
    df = df.iloc[offset: offset + limit]

    # Serialización: timestamp a string ISO para JSON
    df["timestamp_utc"] = df["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return JSONResponse(content={
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": df.to_dict(orient="records"),
    })


@app.get("/api/v1/paises", tags=["Precios"])
def listar_paises(_: str = Security(verificar_token)):
    """Lista los países disponibles en el dataset."""
    df = _cargar_datos()
    return {"paises": sorted(df["pais"].unique().tolist())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)