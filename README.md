# Ecosistema de Datos: Precios de Mercados Energéticos Europeos
### Prueba Técnica - Data & AI Engineer | Grenergy Digital Team

Este repositorio contiene la solución completa para la prueba técnica de Grenergy. El proyecto implementa una solución de datos **End-to-End**: partiendo de la ingesta automatizada y normalización de APIs heterogéneas en la nube (**Microsoft Fabric**), hasta su exposición segura mediante una **API REST** y un **Dashboard Analítico** interactivo en local.

---

## 🏗️ Arquitectura de la Solución

El flujo completo de datos se compone de dos fases desacopladas bajo principios de ingeniería de software robustos:

1. **Fase 1 (Nube - Microsoft Fabric):** Arquitectura Medallón (Bronze ➔ Silver ➔ Gold) implementada en PySpark. Centraliza datos de España (ENTSO-E), Rumanía (ENTSO-E), Alemania (SMARD) y Polonia (PSE), resolviendo retos de paginación, formatos (XML/JSON), diferencias cambiarias (PLN ➔ EUR) y desajustes de granularidad temporal (15 min vs 1 hora).
2. **Fase 2 (Local - Arquitectura Backend/Frontend):**
   * **Backend:** API REST securizada construida con **FastAPI** que sirve los datos procesados en la capa Gold exigiendo autenticación perimetral.
   * **Frontend:** Interfaz web interactiva construida con **Streamlit** y **Plotly** para la comparación multi-país de curvas de precios Day-Ahead.

---

## 📁 Estructura del Proyecto

```text
grenergy_test/
├── api.py                            # Backend: API REST Securizada (FastAPI)
├── app.py                            # Frontend: Interfaz Web Interactiva (Streamlit)
├── gold_precios_horarios_europa.csv   # Base de Datos Local (Snapshot de la Capa Gold de Fabric)
├── README.md                         # Documentación técnica del ecosistema
└── notebooks/                        # Exportación de lógica ETL de Microsoft Fabric
    ├── 01_Capa_Bronze.ipynb          # Ingesta cruda e idempotente desde APIs externas
    ├── 02_Capa_Silver.ipynb          # Limpieza, tipado duro y conversión UTC
    └── 03_Capa_Gold.ipynb            # Agregación horaria y normalización monetaria (EUR)
🚀 Instalación y Ejecución (Fase 2 en Local)
Siga estos pasos para replicar el entorno de ejecución local en su máquina. Se requiere Python 3.9 o superior.

1. Clonar el repositorio y acceder a la ruta
Bash
git clone [https://github.com/TU_USUARIO/grenergy_test.git](https://github.com/TU_USUARIO/grenergy_test.git)
cd grenergy_test
2. Instalar las dependencias del sistema
Bash
pip install fastapi uvicorn pandas streamlit requests plotly watchfiles
3. Levantar el Backend (API REST)
Ejecute el servidor de la API. Este se iniciará por defecto en el puerto 8000:

Bash
python api.py
💡 Nota: Puede acceder a la documentación interactiva y auto-generada de la API (Swagger UI) entrando a: http://127.0.0.1:8000/docs desde su navegador.

4. Levantar el Frontend (Interfaz Web)
Abra una nueva terminal, sitúese en la misma carpeta y ejecute el panel visual:

Bash
streamlit run app.py
🚀 El Dashboard analítico se abrirá automáticamente en su navegador web en la dirección http://localhost:8501.

🧠 Decisiones de Diseño y Justificación Técnica
1. Arquitectura Medallón sobre Delta Lake (Fase 1)
Se optó por implementar una arquitectura en tres niveles sobre el Lakehouse de Fabric para garantizar la trazabilidad del dato:

Bronze: Almacenamiento inmutable de los payloads nativos (JSON/XML). Desacopla las restricciones de rate-limiting de las APIs del procesamiento posterior.

Silver: Limpieza de datos, tipado estricto y eliminación exhaustiva de duplicados mediante dropDuplicates basado en la clave única temporal. Esto dota al pipeline de idempotencia, permitiendo reejecuciones del mismo día sin duplicar registros.

Gold: Tabla consolidada de negocio lista para consumo analítico de alta velocidad.

2. Gestión de Desafíos Específicos de las APIs
Tratamiento de XML Complejos (ENTSO-E): En lugar de usar parseadores DOM tradicionales que saturan la memoria al procesar respuestas masivas, se implementó un procesador iterativo basado en ElementTree para extraer los nodos TimeSeries de forma eficiente.

Normalización de Granularidad (Polonia PT15M vs PT60M): La API de Polonia (PSE) opera en bloques de 15 minutos. En la capa Gold, se normalizó la frecuencia a nivel horario mediante un truncado de fecha (date_trunc("hour")) y una agregación por promedio (avg), logrando la perfecta simetría y comparabilidad con los datos de Alemania, España y Rumanía.

Unificación Monetaria (PLN ➔ EUR): Atendiendo al requerimiento del negocio, se parametrizó un factor de conversión dinámico en la capa Gold para transformar los precios de Polonia (PLN/MWh) a Euros (€/MWh), permitiendo realizar análisis cruzados precisos en un solo dashboard.

Estandarización Temporal (UTC): Se convirtieron todos los registros de tiempos locales a UTC en la capa Silver, blindando al sistema contra errores analíticos derivados de los cambios estacionales de hora (invierno/verano) de cada país.

3. Escalabilidad del Pipeline
El diseño del motor ETL en Fabric rechaza el hardcodeo de variables. Toda la infraestructura se alimenta de diccionarios de configuración y parámetros de entrada. Incorporar un nuevo mercado europeo requiere únicamente mapear sus credenciales y endpoints en el bloque de configuración, permitiendo escalar el pipeline sin modificar el núcleo del código fuente.

4. Estrategia de Seguridad en la API REST (Fase 2)
Para securizar el endpoint se seleccionó un mecanismo de Autenticación por API Key en la cabecera HTTP (X-API-Key).

Justificación: Al tratarse de una arquitectura orientada al intercambio directo de servicios (M2M / Backend-to-Frontend), este esquema proporciona una barrera perimetral criptográfica robusta sin la latencia ni complejidad de almacenamiento de estados (sesiones o tokens OAuth2 complejos), adaptándose idealmente a microservicios analíticos eficientes.