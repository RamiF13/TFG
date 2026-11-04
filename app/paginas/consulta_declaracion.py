
import streamlit as st
import altair as alt
import pandas as pd
from servicios import calcular_consulta, formato_mw, formato_usd, estacion_a_declarar, nombre_estacion, fechas_actualizacion, historial_estacion, formato_millones, etiqueta_estacion


st.title("Consulta de la declaración")
st.caption("Historias HU-06 y HU-07 - Responsable de la declaración")


estacion, anio = estacion_a_declarar()
ultima_carga, vigencia = fechas_actualizacion()


col_seleccion, col_info = st.columns(2, vertical_alignment="center")
col_seleccion.selectbox("Estación a declarar", [nombre_estacion(estacion, anio)])
col_info.caption(f"Última carga de datos: {ultima_carga} - Parámetros vigentes desde {vigencia}")


with st.spinner("Calculando el pronóstico..."):
    futuro, cuantiles_maximo, maximos = calcular_consulta(estacion, anio)


piso = futuro["PISO_MW"].iloc[0]
anterior = maximos[(maximos["ESTACION"] == estacion) & (maximos["ANIO_ESTACION"] == anio - 1)]
maximo_anterior = anterior["MAXIMO_MW"].iloc[0]
porcentaje = round(piso / maximo_anterior * 100)
cargo = futuro[["CARGO_Q10_USD", "CARGO_Q50_USD", "CARGO_Q90_USD"]].sum()


col1, col2, col3, col4 = st.columns(4)
with col1.container(border=True):
    st.metric("Piso regulatorio", formato_mw(piso))
    st.caption(f"{porcentaje} % de {formato_mw(maximo_anterior)}")
with col2.container(border=True):
    st.metric("Pronóstico (central)", formato_mw(cuantiles_maximo[1]))
    st.caption("Máximo de la estación")
with col3.container(border=True):
    st.metric("Banda de incertidumbre", f"{formato_mw(cuantiles_maximo[0])} a {formato_mw(cuantiles_maximo[2])}")
    st.caption("Inferior a superior")
with col4.container(border=True):
    st.metric("Cargo proyectado", f"U\\$S {formato_millones(cargo['CARGO_Q10_USD'])} a {formato_millones(cargo['CARGO_Q90_USD'])} M")
    st.caption(f"Central: {formato_usd(cargo['CARGO_Q50_USD'])}. Al declarar el piso")


historial = historial_estacion(estacion)
largo = historial.melt(
    id_vars=["ETIQUETA", "DECLARADA_MEDIA_MW"],
    value_vars=["MAXIMO_MW", "DECLARADA_MAX_MW"],
    var_name="SERIE",
    value_name="MW",
)
largo["SERIE"] = largo["SERIE"].replace({"MAXIMO_MW": "Demanda máxima registrada", "DECLARADA_MAX_MW": "Potencia declarada"})
etiqueta_pronostico = etiqueta_estacion(estacion, anio)
pronostico = pd.DataFrame({
    "ETIQUETA": [etiqueta_pronostico],
    "Q10": [cuantiles_maximo[0]],
    "Q50": [cuantiles_maximo[1]],
    "Q90": [cuantiles_maximo[2]],
    "PISO": [piso],
})
orden = list(historial["ETIQUETA"]) + [etiqueta_pronostico]
eje_x = alt.X("ETIQUETA:N", scale=alt.Scale(domain=orden), title=None, axis=alt.Axis(labelAngle=0))
eje_y = alt.Y("MW:Q", scale=alt.Scale(zero=False), title="MW")
tooltip_pronostico = [
    alt.Tooltip("ETIQUETA:N", title="Estación"),
    alt.Tooltip("Q10:Q", title="Banda inferior", format=".2f"),
    alt.Tooltip("Q50:Q", title="Pronóstico central", format=".2f"),
    alt.Tooltip("Q90:Q", title="Banda superior", format=".2f"),
    alt.Tooltip("PISO:Q", title="Piso", format=".2f"),
]
color_series = alt.Color(
    "SERIE:N", title=None, legend=alt.Legend(orient="bottom", labelLimit=0),
    scale=alt.Scale(domain=["Demanda máxima registrada", "Potencia declarada"], range=["#1f77b4", "#2ca02c"]),
)
base = alt.Chart(largo).encode(x=eje_x, y=eje_y, color=color_series)
lineas = base.mark_line()

tooltip_comun = [
    alt.Tooltip("SERIE:N", title="Serie"),
    alt.Tooltip("ETIQUETA:N", title="Estación"),
    alt.Tooltip("MW:Q", title="Valor (MW)", format=".2f"),
]
puntos_registrada = base.mark_point(size=90, filled=True).transform_filter(
    alt.datum.SERIE == "Demanda máxima registrada"
).encode(tooltip=tooltip_comun)
puntos_declarada = base.mark_point(size=90, filled=True).transform_filter(
    alt.datum.SERIE == "Potencia declarada"
).encode(tooltip=tooltip_comun + [alt.Tooltip("DECLARADA_MEDIA_MW:Q", title="Declarada promedio (MW)", format=".2f")])

banda = alt.Chart(pronostico).mark_rule(strokeWidth=3, color="#ff7f0e").encode(x=eje_x, y=alt.Y("Q10:Q"), y2="Q90:Q", tooltip=tooltip_pronostico)
central = alt.Chart(pronostico).mark_point(filled=True, size=90, color="#ff7f0e").encode(x=eje_x, y="Q50:Q", tooltip=tooltip_pronostico)
marca_piso = alt.Chart(pronostico).mark_tick(thickness=3, size=40, color="#d62728").encode(x=eje_x, y="PISO:Q", tooltip=tooltip_pronostico)
grafico = alt.layer(lineas, puntos_registrada, puntos_declarada, banda, central, marca_piso).properties(
    height=350,
    title="Estaciones del mismo tipo: demanda máxima registrada, declaración, piso y pronóstico",
)
st.altair_chart(grafico)
st.caption("En la estación a declarar: punto naranja, pronóstico central; barra naranja, banda inferior a superior; marca roja, piso regulatorio. La potencia declarada es la máxima de cada estación.")

anterior_historial = historial[historial["ANIO_ESTACION"] == anio - 1]
tabla_anterior = pd.DataFrame({
    "Misma estación del año anterior": [nombre_estacion(estacion, anio - 1)],
    "Demanda máxima registrada": [formato_mw(anterior_historial["MAXIMO_MW"].iloc[0])],
    "Potencia declarada": [formato_mw(anterior_historial["DECLARADA_MAX_MW"].iloc[0])],
})
st.dataframe(tabla_anterior, hide_index=True)