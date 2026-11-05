import streamlit as st
import altair as alt
import pandas as pd
from servicios import calcular_evaluacion, resumen_metricas, cobertura_banda, etiqueta_estacion, formato_usd, formato_miles

st.title("Evaluación retrospectiva", anchor=False)
st.caption("Historia HU-05 - Responsable de la declaración")

estaciones, errores, cargos, sobrecosto = calcular_evaluacion()

col_seleccion, col_info = st.columns(2, vertical_alignment="bottom")
opcion = col_seleccion.selectbox("Estaciones evaluadas", ["Todas", "Inviernos", "Veranos"])
col_info.info("Cada estación se pronosticó usando solo los datos anteriores a su inicio.")

filtros = {"Inviernos": "INVIERNO", "Veranos": "VERANO"}
if opcion in filtros:
    tipo = filtros[opcion]
    estaciones = estaciones[estaciones["ESTACION"] == tipo]
    errores = errores[errores["ESTACION"] == tipo]
    cargos = cargos[cargos["ESTACION"] == tipo]

# Gráfico
largo = estaciones.melt(id_vars=["ETIQUETA"], value_vars=["MAXIMO_MW", "DECLARADA_MAX_MW"], var_name="SERIE", value_name="MW")
largo["SERIE"] = largo["SERIE"].replace({"MAXIMO_MW": "Demanda máxima registrada", "DECLARADA_MAX_MW": "Potencia declarada"})
eje_x = alt.X("ETIQUETA:N", scale=alt.Scale(domain=list(estaciones["ETIQUETA"])), title=None, axis=alt.Axis(labelAngle=0))
color_series = alt.Color(
    "SERIE:N", title=None, legend=alt.Legend(orient="bottom", labelLimit=0),
    scale=alt.Scale(domain=["Demanda máxima registrada", "Potencia declarada"], range=["#1f77b4", "#2ca02c"]),
)
tooltip_estacion = [
    alt.Tooltip("ETIQUETA:N", title="Estación"),
    alt.Tooltip("MAXIMO_MW:Q", title="Demanda registrada (MW)", format=".2f"),
    alt.Tooltip("Q10_MW:Q", title="Banda inferior (MW)", format=".2f"),
    alt.Tooltip("Q50_MW:Q", title="Pronóstico central (MW)", format=".2f"),
    alt.Tooltip("Q90_MW:Q", title="Banda superior (MW)", format=".2f"),
    alt.Tooltip("PISO_MW:Q", title="Piso (MW)", format=".2f"),
]
lineas = alt.Chart(largo).mark_line(point=alt.OverlayMarkDef(size=80, filled=True)).encode(
    x=eje_x,
    y=alt.Y("MW:Q", title="MW", scale=alt.Scale(zero=False)),
    color=color_series,
    tooltip=[alt.Tooltip("SERIE:N", title="Serie"), alt.Tooltip("ETIQUETA:N", title="Estación"), alt.Tooltip("MW:Q", title="Valor (MW)", format=".2f")],
)
banda = alt.Chart(estaciones).mark_rule(strokeWidth=3, color="#ff7f0e").encode(x=eje_x, y=alt.Y("Q10_MW:Q", title="MW"), y2="Q90_MW:Q", tooltip=tooltip_estacion)
central = alt.Chart(estaciones).mark_point(filled=True, size=80, color="#ff7f0e", shape="diamond").encode(x=eje_x, y=alt.Y("Q50_MW:Q", title="MW"), tooltip=tooltip_estacion)
marca_piso = alt.Chart(estaciones).mark_tick(thickness=3, size=30, color="#d62728").encode(x=eje_x, y=alt.Y("PISO_MW:Q", title="MW"), tooltip=tooltip_estacion)
grafico = alt.layer(lineas, banda, central, marca_piso).properties(
    height=350,
    title="Estaciones pasadas: pronóstico con bandas, demanda registrada, declaración y piso",
)
st.altair_chart(grafico)
st.caption("Rombo naranja: pronóstico central; barra naranja: banda inferior a superior; marca roja: piso de cada estación. La potencia declarada es la máxima de cada estación.")

# Métricas
st.subheader("Métricas por modelo", anchor=False)
metricas = resumen_metricas(errores, cargos)
cobertura = cobertura_banda(estaciones["MAXIMO_MW"], estaciones["Q10_MW"], estaciones["Q90_MW"])
tabla = pd.DataFrame({
    "Modelo": metricas["MODELO"],
    "Error absoluto medio (MW)": [f"{v:.2f}".replace(".", ",") for v in metricas["MAE_MW"]],
    "Sesgo (MW)": [f"{v:+.2f}".replace(".", ",") for v in metricas["SESGO_MW"]],
    "Cobertura de la banda": [f"{cobertura:.0%}", "-", "-"],
    "Error absoluto medio del cargo (U$S)": [formato_miles(v) for v in metricas["MAE_CARGO_USD"]],
})
st.dataframe(tabla, hide_index=True)
st.caption(
    f"Error y sesgo en MW sobre {len(errores)} estaciones, en las que pronostican los tres modelos; cobertura y error del cargo sobre {len(estaciones)} estaciones. "
    "Sesgo positivo: pronóstico de menos. Cobertura nominal de la banda: 80 %. Con pocas estaciones, las diferencias entre modelos son indicativas."
)

# Sobrecosto
col_sobrecosto, col_nota = st.columns(2)
detalle = " - ".join(
    f"{etiqueta_estacion(fila['ESTACION'], fila['ANIO_ESTACION'])} ({fila['MESES']} meses): U$S {formato_miles(fila['SOBRECOSTO_USD'])}"
    for _, fila in sobrecosto.iterrows()
)
with col_sobrecosto.container(border=True):
    st.metric("Sobrecosto desde noviembre de 2025", formato_usd(sobrecosto["SOBRECOSTO_USD"].sum()))
    st.caption(f"Declarar el piso frente a lo declarado. {detalle}. No depende del filtro de estaciones.")
    col_nota.info(
    "El error del cargo de cada estación se calcula con las reglas actuales (Res. SE 400/2025 y 22/2026), aunque antes de noviembre de 2025 regían otras: "
    "para esas estaciones es una diferencia contrafactual bajo el régimen actual, no un costo efectivamente pagado. "
    "El sobrecosto se informa solo desde que rige la regla actual."
)