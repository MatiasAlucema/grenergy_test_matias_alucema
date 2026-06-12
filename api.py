from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
import pandas as pd
import os

app = FastAPI(
    title="Grenergy Market API",
    description="API REST segura para consultar precios horarios de mercados europeos.",
    version="1.0"
)

# 1. CONFIGURACIÓN DE SEGURIDAD (Exigido en la prueba)
API_KEY_NAME = "X-API-Key"
API_KEY_SECRET = "grenergy_2026_secure_token"  # Este es el token que validará la API
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verificar_token(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY_SECRET:
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado: El token de seguridad es inválido o no fue enviado."
        )
    return api_key

# 2. RUTA DEL ARCHIVO EXPORTADO
DATA_FILE = "gold_precios_horarios_europa.csv"

# 3. ENDPOINT PARA CONSULTAR PRECIOS
@app.get("/api/v1/precios", tags=["Precios"])
def obtener_precios(pais: str = None, token: str = Depends(verificar_token)):
    """
    Retorna los precios horarios de energía homogeneizados en EUR.
    Filtro opcional por país mediante query params (?pais=España).
    Requiere incluir 'X-API-Key' en las cabeceras (Headers) de la solicitud.
    """
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=500, detail="Error interno: Archivo de datos no encontrado en el servidor local.")
    
    # Leer el archivo local
    df = pd.read_csv(DATA_FILE)
    
    # Filtrar por país si se solicita
    if pais:
        df = df[df['pais'].str.lower() == pais.lower()]
    
    # Convertir a formato JSON estándar para la respuesta de la API
    resultado = df.to_dict(orient="records")
    return JSONResponse(content=resultado)

if __name__ == "__main__":
    import uvicorn
    # Arranca el servidor local en el puerto 8000
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)