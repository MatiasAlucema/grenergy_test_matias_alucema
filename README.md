# Grenergy — Prueba Técnica: Data & AI Engineer

Pipeline ETL de precios Day Ahead de cuatro mercados eléctricos europeos, expuesto mediante una API REST segura y un dashboard web interactivo.

---

## Índice

1. [Arquitectura general](#arquitectura-general)
2. [Fase 1 — ETL en Microsoft Fabric](#fase-1--etl-en-microsoft-fabric)
3. [Fase 2 — API REST + Interfaz Web](#fase-2--api-rest--interfaz-web)
4. [Requisitos e instalación](#requisitos-e-instalación)
5. [Ejecución paso a paso](#ejecución-paso-a-paso)
6. [Decisiones técnicas relevantes](#decisiones-técnicas-relevantes)

---

## Arquitectura general

```
APIs externas
  ├── ENTSO-E (España, Rumanía) → XML / PT15M / EUR
  ├── SMARD   (Alemania)        → JSON / PT60M / EUR
  └── PSE     (Polonia)         → JSON / PT15M / PLN ⚠️ conversión a EUR

Microsoft Fabric (Lakehouse: Grenergy_Lakehouse)
  ├── 🟫 Capa Bronze  → tablas crudas inmutables por país
  ├── ⬜ Capa Silver  → esquema común, deduplicación, tipado estricto
  └── 🟨 Capa Gold    → normalización monetaria, reducción de granularidad,
                        KPIs diarios, exportación CSV

Fase 2 (local)
  ├── api.py  → FastAPI  (puerto 8000) — autenticación por API Key
  └── app.py  → Streamlit (puerto 8501) — dashboard interactivo
```

---

## Fase 1 — ETL en Microsoft Fabric

### Notebooks

| Notebook | Responsabilidad |
|---|---|
| `01_Capa_Bronze.ipynb` | Descarga perimetral de cada API sin transformación |
| `02_Capa_Silver.ipynb` | Parseo XML/JSON, esquema común, deduplicación |
| `03_Capa_Gold.ipynb`   | Conversión PLN→EUR, reducción granularidad, KPIs diarios |

### Ejecución en Fabric

1. Accede a Microsoft Fabric con las credenciales facilitadas.
2. Selecciona la capacidad **Trial** cuando el sistema lo solicite.
3. Abre el Lakehouse `Grenergy_Lakehouse`.
4. Ejecuta los notebooks en orden: Bronze → Silver → Gold.
5. El CSV de salida (`gold_precios_horarios_europa.csv`) queda en `Files/gold_precios_horarios_export/`.

### Ventana de carga incremental

El pipeline descarga los **últimos 6 días** en cada ejecución. Este margen cubre los retrasos habituales de publicación de las APIs (ENTSO-E publica D-1, SMARD puede retrasarse hasta 2 días).

---

## Fase 2 — API REST + Interfaz Web

### Estructura de archivos

```
fase2/
├── api.py                            # Backend FastAPI
├── app.py                            # Frontend Streamlit
├── gold_precios_horarios_europa.csv  # Dataset exportado desde Fabric
└── requirements.txt
```

### Endpoints disponibles

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Healthcheck — no requiere autenticación |
| GET | `/api/v1/precios` | Precios horarios con filtros opcionales |
| GET | `/api/v1/paises` | Lista de países disponibles |
| GET | `/docs` | Documentación interactiva (Swagger UI) |

#### Parámetros de `/api/v1/precios`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `pais` | string | Filtro por país (España, Alemania, Polonia, Rumania) |
| `fecha_inicio` | string | Fecha mínima en formato `YYYY-MM-DD` |
| `fecha_fin` | string | Fecha máxima en formato `YYYY-MM-DD` |
| `limit` | int | Máximo de registros (default: 1000) |
| `offset` | int | Desplazamiento para paginación (default: 0) |

---

## Requisitos e instalación

### Python 3.10+

```bash
pip install fastapi uvicorn pandas streamlit plotly requests python-multipart
```

O con el fichero de dependencias:

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
fastapi==0.111.0
uvicorn==0.29.0
pandas==2.2.2
streamlit==1.35.0
plotly==5.22.0
requests==2.32.2
python-multipart==0.0.9
```

---

## Ejecución paso a paso

### 1. Configurar el token de seguridad

El token **nunca debe hardcodearse** en el código. Se configura mediante variable de entorno:

```bash
# Linux / macOS
export GRENERGY_API_KEY="tu_token_secreto"

# Windows (PowerShell)
$env:GRENERGY_API_KEY = "tu_token_secreto"
```

> ⚠️ La API no arrancará si esta variable no está definida.

### 2. Colocar el CSV de datos

Copia el archivo exportado desde Fabric al directorio de trabajo:

```bash
cp /ruta/a/gold_precios_horarios_europa.csv ./fase2/
```

### 3. Arrancar la API

```bash
cd fase2
python api.py
# Servidor disponible en http://127.0.0.1:8000
# Documentación Swagger en http://127.0.0.1:8000/docs
```

### 4. Arrancar el dashboard

En otra terminal (con la misma variable de entorno configurada):

```bash
cd fase2
streamlit run app.py
# Dashboard disponible en http://localhost:8501
```

### 5. Interfaz web

El dashboard está desplegado en Streamlit Cloud y accesible públicamente:

🔗 [https://grenergytestmatiasalucema-clyatzqwntytkwgb4on6mh.streamlit.app/](https://grenergytestmatiasalucema-clyatzqwntytkwgb4on6mh.streamlit.app/)

Para ejecutarlo localmente, sigue los pasos anteriores y accede en `http://localhost:8501`.

### 6. Probar la API manualmente

```bash
# Con curl
curl -H "X-API-Key: tu_token_secreto" \
     "http://127.0.0.1:8000/api/v1/precios?pais=España&fecha_inicio=2026-06-07&fecha_fin=2026-06-10"

# Healthcheck (sin autenticación)
curl http://127.0.0.1:8000/health
```

---

## Decisiones técnicas relevantes

### Diseño del pipeline (arquitectura Medallion)

Se adoptó la arquitectura Medallion (Bronze / Silver / Gold) porque separa claramente las responsabilidades: Bronze garantiza la trazabilidad del dato crudo, Silver estandariza y limpia, Gold produce las tablas analíticas listas para consumo. Esto facilita el reprocesamiento parcial sin afectar a otras capas.

### Gestión de diferencias entre APIs

Cada fuente presenta retos distintos:

- **ENTSO-E (España / Rumanía):** respuesta XML con namespace fijo. Se parsea con `xml.etree.ElementTree`. Los timestamps vienen en UTC nativo (`...Z`), lo que simplifica la homogeneización.
- **SMARD (Alemania):** API en dos pasos (índice → bloque semanal). Los timestamps llegan en milisegundos Unix, por lo que se dividen entre 1000 antes de la conversión.
- **PSE (Polonia):** API REST pública con filtro por fecha. Devuelve 96 registros diarios en PLN/MWh a resolución PT15M.

### Conversión PLN → EUR

Se aplica un factor fijo de `0.23 PLN/EUR` parametrizado como constante en la capa Gold. Esta decisión es consciente y justificada: la prueba no requiere integrar una API de tipo de cambio en tiempo real, y un factor hardcodeado pero externalizado como constante es suficiente para un entorno de datos energéticos donde el precio ya incorpora la variabilidad del mercado. En producción, esta constante podría sustituirse por una llamada diaria a la API del BCE.

### Reducción de granularidad de Polonia

Los datos de Polonia llegan a PT15M. Para unificarlos con el resto de países en la capa Gold (todos a PT60M), se aplica `date_trunc("hour")` + `avg()` sobre los 4 registros de cada hora. Se eligió la media aritmética porque es la métrica estándar para precios horarios en mercados energéticos.

### Mecanismo de seguridad de la API (API Key en header)

Se eligió **API Key via header HTTP** (`X-API-Key`) por las siguientes razones:

- Es el mecanismo más sencillo de implementar y auditar para una API interna o de uso controlado.
- Evita exponer el token en logs de servidor (a diferencia de query params).
- Es compatible con cualquier cliente HTTP sin librerías adicionales.
- Para un contexto de producción real se recomendaría OAuth 2.0 / JWT, pero para esta prueba añadiría complejidad innecesaria sin beneficio real dado que no hay gestión de usuarios ni sesiones.

El token se lee **exclusivamente desde la variable de entorno `GRENERGY_API_KEY`**. La API no arranca si la variable no está definida, lo que evita accidentalmente desplegar sin seguridad.

### Escalabilidad del pipeline

La configuración de cada país se centraliza en el diccionario `CONFIG_PAISES` en la capa Bronze. Añadir un nuevo país (por ejemplo, Francia vía ENTSO-E) requiere únicamente:

1. Añadir una entrada al diccionario con su EIC code.
2. Invocar la función `descargar_entsoe` con la nueva clave.
3. Llamar a `transformar_xml_entsoe` en Silver.
4. Incluirlo en el `unionByName` de Gold.

No es necesario modificar la lógica de ninguna capa.

### Resiliencia del frontend

El dashboard Streamlit implementa un patrón **API-first con fallback a CSV**: intenta conectarse a la API local y, si falla (API no levantada, token incorrecto, timeout), carga el CSV directamente. Esto garantiza que el dashboard sea operativo incluso sin el servidor backend, lo cual es especialmente útil en demostraciones o entornos sin red.