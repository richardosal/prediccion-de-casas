import streamlit as st
import pandas as pd
import joblib

# ==========================
# Cargar modelo entrenado
# ==========================
modelo = joblib.load("modelo.pkl")

# ==========================
# Configuración de la página
# ==========================
st.set_page_config(
    page_title="Predicción de Precio de Viviendas",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Predicción del Precio Medio de Viviendas")
st.markdown(
    "Modifica las características de la vivienda y obtén una predicción del precio."
)

# ==========================
# Formulario de entrada
# ==========================

col1, col2 = st.columns(2)

with col1:
    longitud = st.number_input(
        "Longitud",
        min_value=-125.0,
        max_value=-114.0,
        value=-122.23,
        step=0.01
    )

    latitud = st.number_input(
        "Latitud",
        min_value=32.0,
        max_value=42.0,
        value=37.88,
        step=0.01
    )

    edad_media_vivienda = st.slider(
        "Edad media de la vivienda",
        min_value=1,
        max_value=60,
        value=29
    )

    total_habitaciones = st.number_input(
        "Total de habitaciones",
        min_value=1,
        value=3000
    )

    total_banos = st.number_input(
        "Total de baños",
        min_value=1,
        value=500
    )

with col2:
    poblacion = st.number_input(
        "Población",
        min_value=1,
        value=1000
    )

    hogares = st.number_input(
        "Número de hogares",
        min_value=1,
        value=400
    )

    ingreso_medio = st.number_input(
        "Ingreso medio",
        min_value=0.0,
        value=5.0,
        step=0.1
    )

    proximidad_oceanica = st.selectbox(
        "Proximidad oceánica",
        [
            "<1H OCEAN",
            "INLAND",
            "NEAR OCEAN",
            "NEAR BAY",
            "ISLAND"
        ]
    )

# ==========================
# Codificación variable categórica
# ==========================

ocean_mapping = {
    "<1H OCEAN": 0,
    "INLAND": 1,
    "NEAR OCEAN": 2,
    "NEAR BAY": 3,
    "ISLAND": 4
}

proximidad_oceanica_cod = ocean_mapping[proximidad_oceanica]

# ==========================
# Crear DataFrame
# ==========================

datos = pd.DataFrame({
    "longitud": [longitud],
    "latitud": [latitud],
    "edad media vivienda": [edad_media_vivienda],
    "total de habitaciones": [total_habitaciones],
    "total baños": [total_banos],
    "poblacion": [poblacion],
    "hogares": [hogares],
    "ingreso medio": [ingreso_medio],
    "proximidad oceánica": [proximidad_oceanica_cod]
})

# ==========================
# Predicción
# ==========================

if st.button("🔮 Predecir precio"):
    prediccion = modelo.predict(datos)[0]

    st.success(
        f"Precio medio estimado: ${prediccion:,.2f}"
    )

    st.subheader("Valores utilizados")
    st.dataframe(datos)
