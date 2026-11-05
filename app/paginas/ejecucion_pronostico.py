import streamlit as st
import altair as alt
import pandas as pd
from servicios import ejecutar_pronostico, estacion_a_declarar, nombre_estacion, leer_serie, formato_mw, formato_mes, cobertura_retrospectiva

st.title("Ejecución del pronóstico", anchor=False)
st.caption("Historia HU-03 - Operador del prototipo")

estacion, anio = estacion_a_declarar()
serie = leer_serie()

col_seleccion, col_datos, col_boton = st.columns([2, 2, 1], vertical_alignment="bottom")
col_seleccion.selectbox("Estación a pronosticar", [nombre_estacion(estacion, anio)])
col_datos.caption(f"Datos disponibles: {formato_mes(serie['MES'].min())} a {formato_mes(serie['MES'].max())}")
realizar = col_boton.button("Realizar pronóstico", type="primary")

if realizar:
    try:
        st.session_state["pronostico"] = ejecutar_pronostico(estacion, anio)
    except PermissionError:
        st.error("No se pudo registrar la ejecución porque el archivo de registro está abierto en otro programa. Cerrar el archivo y volver a realizar el pronóstico.")
        st.stop()

if "pronostico" not in st.session_state:
    st.info("Realizar el pronóstico para ver los resultados.")
    st.stop()

futuro, cuantiles_maximo, modelos, registro = st.session_state["pronostico"]

historia = serie[["MES", "MAX_REAL_MW"]].tail(24)
eje_x = alt.X("MES:T", title=None, axis=alt.Axis(format="%m/%Y"))
tooltip_pronostico = [
    alt.Tooltip("MES:T", title="Mes", format="%m/%Y"),
    alt.Tooltip("Q10_MW:Q", title="Banda inferior (MW)", format=".2f"),
    alt.Tooltip("Q50_MW:Q", title="Pronóstico central (MW)", format=".2f"),
    alt.Tooltip("Q90_MW:Q", title="Banda superior (MW)", format=".2f"),
]
historica = alt.Chart(historia).mark_line(color="#1f77b4", point=alt.OverlayMarkDef(size=60, filled=True, color="#1f77b4")).encode(
    x=eje_x,
    y=alt.Y("MAX_REAL_MW:Q", title="MW", scale=alt.Scale(zero=False)),
    tooltip=[alt.Tooltip("MES:T", title="Mes", format="%m/%Y"), alt.Tooltip("MAX_REAL_MW:Q", title="Demanda máxima registrada (MW)", format=".2f")],
)
banda = alt.Chart(futuro).mark_area(opacity=0.25, color="#ff7f0e").encode(x=eje_x, y=alt.Y("Q10_MW:Q", title="MW"), y2="Q90_MW:Q", tooltip=tooltip_pronostico)
central = alt.Chart(futuro).mark_line(color="#ff7f0e", strokeDash=[6, 4], point=alt.OverlayMarkDef(size=60, filled=True, color="#ff7f0e")).encode(
    x=eje_x, y=alt.Y("Q50_MW:Q", title="MW"), tooltip=tooltip_pronostico,
)
inicio = alt.Chart(pd.DataFrame({"MES": [futuro["MES"].min()]})).mark_rule(color="gray", strokeDash=[3, 3]).encode(x=eje_x)
grafico = alt.layer(historica, banda, central, inicio).properties(
    height=350,
    title="Demanda máxima mensual: histórica y pronosticada con bandas de incertidumbre",
)
st.altair_chart(grafico)
st.caption("Línea azul: demanda máxima registrada. Línea naranja punteada: pronóstico central de cada mes. Área naranja: banda inferior a superior. Línea gris: inicio del pronóstico.")

col1, col2, col3 = st.columns(3)
with col1.container(border=True):
    st.metric("Máximo estacional pronosticado", formato_mw(cuantiles_maximo[1]))
    st.caption("Valor central")
with col2.container(border=True):
    st.metric("Banda inferior", formato_mw(cuantiles_maximo[0]))
    st.caption("Cuantil inferior")
with col3.container(border=True):
    st.metric("Banda superior", formato_mw(cuantiles_maximo[2]))
    st.caption("Cuantil superior")

st.subheader("Pronóstico del máximo estacional según modelo", anchor=False)
st.dataframe(
    modelos,
    hide_index=True,
    column_config={"Máximo estacional pronosticado (MW)": st.column_config.NumberColumn(format="%.1f")},
)

fila = registro.iloc[0]
st.caption(
    f"Ejecución registrada: {fila['FECHA_EJECUCION']:%d/%m/%Y %H:%M} - "
    f"datos de {formato_mes(fila['DATOS_DESDE'])} a {formato_mes(fila['DATOS_HASTA'])} - "
    f"cuantiles {fila['CUANTILES']} - cobertura nominal de la banda: 80 %, "
    f"observada en la evaluación retrospectiva: {cobertura_retrospectiva():.0%}"
)
