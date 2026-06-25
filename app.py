import streamlit as st
import pandas as pd
import requests
import time
import io

# ============================================================
# CONFIGURACIÓN DATAROBOT DESDE STREAMLIT SECRETS
# ============================================================

DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
DATAROBOT_HOST = st.secrets["DATAROBOT_HOST"]


# ============================================================
# CONFIGURACIÓN GENERAL DE STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Predicción de Arriendos",
    page_icon="🏠",
    layout="wide"
)


# ============================================================
# ESTILOS VISUALES
# ============================================================

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #312e81 100%);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .title-card {
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899);
        padding: 2rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        box-shadow: 0px 8px 30px rgba(0,0,0,0.35);
        margin-bottom: 2rem;
    }

    .title-card h1 {
        font-size: 3rem;
        margin-bottom: 0.3rem;
    }

    .title-card p {
        font-size: 1.15rem;
        opacity: 0.95;
    }

    .info-box {
        background: rgba(255, 255, 255, 0.10);
        border-radius: 18px;
        padding: 1.2rem;
        color: white;
        border-left: 5px solid #38bdf8;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.08);
        padding: 1.3rem;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.15);
        color: white;
        text-align: center;
        box-shadow: 0px 6px 20px rgba(0,0,0,0.25);
        min-height: 150px;
    }

    .metric-card h3 {
        font-size: 2rem;
        margin-bottom: 0.2rem;
    }

    .metric-card h4 {
        font-size: 1.5rem;
        margin-bottom: 0.1rem;
    }

    .prediction-card {
        background: linear-gradient(135deg, #22c55e, #14b8a6);
        padding: 2rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        box-shadow: 0px 10px 35px rgba(0,0,0,0.35);
        margin-top: 1.5rem;
    }

    .prediction-card h1 {
        font-size: 3rem;
        margin-top: 0.5rem;
    }

    .error-card {
        background: linear-gradient(135deg, #ef4444, #f97316);
        padding: 1.5rem;
        border-radius: 18px;
        color: white;
        margin-top: 1rem;
    }

    div.stButton > button {
        width: 100%;
        height: 3.5rem;
        border-radius: 15px;
        font-size: 1.15rem;
        font-weight: bold;
        background: linear-gradient(135deg, #6366f1, #ec4899);
        color: white;
        border: none;
        box-shadow: 0px 6px 20px rgba(0,0,0,0.25);
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5, #db2777);
        color: white;
        transform: scale(1.01);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def formato_cop(valor):
    """
    Convierte un valor numérico a formato de pesos colombianos.
    Ejemplo: 1850000 -> $1.850.000 COP
    """
    try:
        valor = float(valor)
        return f"${valor:,.0f}".replace(",", ".") + " COP"
    except:
        return str(valor)


def detectar_columna_prediccion(resultado, columnas_entrada):
    """
    Detecta automáticamente la columna donde DataRobot devuelve la predicción.
    Evita tomar columnas como prediction_status.
    """

    columnas = list(resultado.columns)

    posibles = [
        col for col in columnas
        if "prediction" in col.lower()
        and "status" not in col.lower()
        and col not in columnas_entrada
    ]

    if posibles:
        return posibles[0]

    posibles = [
        col for col in columnas
        if "predicted" in col.lower()
        and col not in columnas_entrada
    ]

    if posibles:
        return posibles[0]

    posibles = [
        col for col in columnas
        if col not in columnas_entrada
        and "status" not in col.lower()
    ]

    for col in posibles:
        try:
            pd.to_numeric(resultado[col])
            return col
        except:
            pass

    return None


# ============================================================
# FUNCIÓN PARA CONECTAR CON DATAROBOT
# ============================================================

def hacer_prediccion_batch(df_input):
    """
    Envía los datos a DataRobot usando Batch Predictions API.
    Retorna un DataFrame con la predicción.
    """

    batch_url = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"

    headers_json = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "Content-Type": "application/json; encoding=utf-8"
    }

    payload = {
        "deploymentId": DATAROBOT_DEPLOYMENT_ID,
        "passthroughColumnsSet": "all",
        "includePredictionStatus": True
    }

    response = requests.post(
        batch_url,
        headers=headers_json,
        json=payload
    )

    if response.status_code >= 400:
        raise Exception(f"Error creando el job en DataRobot: {response.text}")

    job = response.json()

    upload_url = job["links"]["csvUpload"]
    job_url = job["links"]["self"]

    csv_buffer = io.StringIO()
    df_input.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    upload_headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "Content-Type": "text/csv; encoding=utf-8"
    }

    upload_response = requests.put(
        upload_url,
        headers=upload_headers,
        data=csv_bytes
    )

    if upload_response.status_code >= 400:
        raise Exception(f"Error subiendo los datos a DataRobot: {upload_response.text}")

    progress_bar = st.progress(0)
    status_text = st.empty()

    status = ""

    while status not in ["COMPLETED", "FAILED", "ABORTED"]:
        job_response = requests.get(
            job_url,
            headers={"Authorization": f"Token {DATAROBOT_API_KEY}"}
        )

        if job_response.status_code >= 400:
            raise Exception(f"Error consultando el estado del job: {job_response.text}")

        job_data = job_response.json()
        status = job_data.get("status", "")

        porcentaje = job_data.get("percentageCompleted", 0)

        try:
            porcentaje = int(float(porcentaje))
        except:
            porcentaje = 0

        progress_bar.progress(min(porcentaje, 100))
        status_text.info(f"⏳ Estado del modelo: {status} - {porcentaje}%")

        if status in ["COMPLETED", "FAILED", "ABORTED"]:
            break

        time.sleep(2)

    if status != "COMPLETED":
        raise Exception(f"El proceso terminó con estado: {status}")

    download_url = job_data["links"]["download"]

    download_response = requests.get(
        download_url,
        headers={"Authorization": f"Token {DATAROBOT_API_KEY}"}
    )

    if download_response.status_code >= 400:
        raise Exception(f"Error descargando los resultados: {download_response.text}")

    result_df = pd.read_csv(io.StringIO(download_response.text))

    progress_bar.progress(100)
    status_text.success("✅ Predicción completada correctamente")

    return result_df


# ============================================================
# ENCABEZADO
# ============================================================

st.markdown("""
<div class="title-card">
    <h1>🏠 Predicción Inteligente de Arriendos</h1>
    <p>Frontend interactivo conectado con un modelo desplegado en DataRobot</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Panel de control")

    st.write("Configura las variables del inmueble y ejecuta la predicción.")

    modo_demo = st.toggle("🧪 Activar modo demo", value=False)

    st.divider()

    st.subheader("📌 Variables de entrada")
    st.write("📐 metros_cuadrados")
    st.write("🛏️ habitaciones")
    st.write("🚿 banos")
    st.write("🏙️ estrato")

    st.divider()

    st.subheader("🎯 Variable objetivo")
    st.write("💰 precio_arriendo_cop")

    st.caption("El precio de arriendo no se ingresa porque es el valor que el modelo debe predecir.")


# ============================================================
# FORMULARIO DE VARIABLES
# ============================================================

st.markdown("""
<div class="info-box">
    <h3>🏡 Datos del inmueble</h3>
    <p>Ingresa las características del inmueble. El modelo estimará el precio de arriendo.</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    metros_cuadrados = st.slider(
        "📐 Metros cuadrados",
        min_value=10,
        max_value=500,
        value=70,
        step=1
    )

    habitaciones = st.number_input(
        "🛏️ Habitaciones",
        min_value=0,
        max_value=20,
        value=2,
        step=1
    )

with col2:
    banos = st.number_input(
        "🚿 Baños",
        min_value=0,
        max_value=10,
        value=1,
        step=1
    )

    estrato = st.select_slider(
        "🏙️ Estrato",
        options=[1, 2, 3, 4, 5, 6],
        value=3
    )

    st.write("")
    calcular = st.button("🚀 Predecir precio de arriendo")


# ============================================================
# RESUMEN VISUAL
# ============================================================

st.subheader("📊 Resumen de entrada")

resumen_col1, resumen_col2, resumen_col3, resumen_col4 = st.columns(4)

with resumen_col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>📐</h3>
        <h4>{metros_cuadrados}</h4>
        <p>Metros cuadrados</p>
    </div>
    """, unsafe_allow_html=True)

with resumen_col2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>🛏️</h3>
        <h4>{habitaciones}</h4>
        <p>Habitaciones</p>
    </div>
    """, unsafe_allow_html=True)

with resumen_col3:
    st.markdown(f"""
    <div class="metric-card">
        <h3>🚿</h3>
        <h4>{banos}</h4>
        <p>Baños</p>
    </div>
    """, unsafe_allow_html=True)

with resumen_col4:
    st.markdown(f"""
    <div class="metric-card">
        <h3>🏙️</h3>
        <h4>{estrato}</h4>
        <p>Estrato</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# DATAFRAME QUE SE ENVÍA AL MODELO
# ============================================================

input_data = pd.DataFrame([{
    "metros_cuadrados": metros_cuadrados,
    "habitaciones": habitaciones,
    "banos": banos,
    "estrato": estrato
}])

columnas_entrada = list(input_data.columns)

st.subheader("🧾 Datos enviados al modelo")
st.dataframe(input_data, use_container_width=True)


# ============================================================
# EJECUCIÓN DE LA PREDICCIÓN
# ============================================================

if calcular:

    if modo_demo:
        prediccion_demo = (
            metros_cuadrados * 18000
            + habitaciones * 120000
            + banos * 100000
            + estrato * 180000
        )

        st.markdown(f"""
        <div class="prediction-card">
            <h2>🧪 Precio estimado en modo demo</h2>
            <h1>{formato_cop(prediccion_demo)}</h1>
            <p>Este valor es simulado. No viene de DataRobot.</p>
        </div>
        """, unsafe_allow_html=True)

    else:
        try:
            with st.spinner("🤖 Enviando datos a DataRobot..."):
                resultado = hacer_prediccion_batch(input_data)

            st.success("✅ Respuesta recibida desde DataRobot")

            st.subheader("📌 Resultado completo")
            st.dataframe(resultado, use_container_width=True)

            columna_resultado = detectar_columna_prediccion(resultado, columnas_entrada)

            if columna_resultado:
                valor_predicho = resultado[columna_resultado].iloc[0]
                valor_formateado = formato_cop(valor_predicho)

                st.markdown(f"""
                <div class="prediction-card">
                    <h2>🎯 Precio de arriendo estimado</h2>
                    <h1>{valor_formateado}</h1>
                    <p>Resultado generado por el deployment de DataRobot</p>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.warning(
                    "La predicción llegó, pero no se detectó automáticamente la columna del resultado. "
                    "Revisa la tabla completa que aparece arriba."
                )

        except Exception as e:
            st.markdown(f"""
            <div class="error-card">
                <h3>❌ Error al conectar con DataRobot</h3>
                <p>{str(e)}</p>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.markdown("---")
st.caption("App desarrollada con Streamlit + DataRobot")
import jobLib