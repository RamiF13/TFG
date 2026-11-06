from datetime import date

import streamlit as st

from servicios import (leer_serie, actualizar_serie_trabajo, informe_calidad, guardar_archivo_cammesa,
                       descargar_temperatura, archivos_disponibles, formato_mes, nombre_estacion, latitud, longitud)

CONTROLES = {
    "faltantes": ("Meses faltantes", "Meses sin dato entre el primero y el último de la serie."),
    "revisados": ("Revisados entre ediciones", "Meses cuyo valor cambió de una edición de CAMMESA a otra. Se usa el de la edición más nueva."),
    "posible_copia": ("Posible copia de la declaración", "Meses donde el máximo real está a menos de 0,01 MW de la potencia declarada."),
    "fuera_rango_demanda": ("Demanda fuera de rango", "Meses con máximo real o potencia declarada menor o igual a 0."),
    "fuera_rango_temperatura": ("Temperatura fuera de rango", "Meses con temperatura vacía o fuera de los récords del SMN para Trelew Aero, con un margen de 3 °C."),
}


def abrir(seccion):
    """Recuerda qué sección usó el Operador por última vez, para que siga abierta al recargar la página"""
    st.session_state["seccion_abierta"] = seccion


def avisar(seccion, texto):
    """Guarda el mensaje de éxito de la sección y recarga la página para mostrar los datos actualizados"""
    st.session_state["mensaje_carga"] = (seccion, texto)
    st.rerun()


def abrir_seccion(seccion, titulo):
    """Crea el desplegable de la sección, abierto si fue la última usada, y muestra su mensaje pendiente"""
    desplegable = st.expander(titulo, expanded=st.session_state.get("seccion_abierta") == seccion)
    aviso = desplegable.empty()
    mensaje = st.session_state.get("mensaje_carga")
    if mensaje and mensaje[0] == seccion:
        aviso.success(mensaje[1])
        del st.session_state["mensaje_carga"]
    return desplegable


st.title("Carga y calidad de datos", anchor=False)
st.caption("Historias HU-01 y HU-02 - Operador del prototipo")

# Archivos originales
st.subheader("Archivos originales", anchor=False)
cammesa, temperatura = archivos_disponibles()
with st.expander(f"CAMMESA, base Req Máx ({len(cammesa)} archivos)"):
    st.dataframe(cammesa, hide_index=True, use_container_width=True)
with st.expander(f"Open-Meteo, reanálisis ERA5 ({len(temperatura)} archivos)"):
    st.dataframe(temperatura, hide_index=True, use_container_width=True)
    st.caption(f"Temperatura consultada en las coordenadas de la estación Trelew Aero del SMN (latitud {latitud}, longitud {longitud}). Open-Meteo devuelve la celda ERA5 más cercana a ese punto.")

# Acciones
st.subheader("Acciones", anchor=False)

with abrir_seccion("cammesa", "Cargar una edición de CAMMESA"):
    with st.form("cargar_cammesa"):
        archivo = st.file_uploader("Archivo Req Máx descargado de CAMMESA", type="xlsx")
        descarga = st.date_input("Fecha en que se descargó de CAMMESA", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        cargar = st.form_submit_button("Guardar archivo", type="primary", on_click=abrir, args=("cammesa",))
    if cargar:
        if archivo is None:
            st.error("Seleccione un archivo antes de guardar.")
        else:
            try:
                nombre = guardar_archivo_cammesa(archivo, descarga)
            except ValueError as error:
                st.error(str(error))
            else:
                avisar("cammesa", f"Se guardó {nombre}. Actualice la serie de trabajo para incorporarlo.")

with abrir_seccion("temperatura", "Descargar la temperatura"):
    st.write("Descarga de Open-Meteo la temperatura diaria desde el 01/01/2019 hasta el último día del mes anterior.")
    if st.button("Descargar temperatura", on_click=abrir, args=("temperatura",)):
        try:
            with st.spinner("Consultando Open-Meteo..."):
                nombre = descargar_temperatura()
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("No se pudo consultar Open-Meteo. Revise la conexión a internet e intente nuevamente.")
        else:
            avisar("temperatura", f"Se guardó {nombre}. Actualice la serie de trabajo para incorporarlo.")

with abrir_seccion("serie", "Actualizar la serie de trabajo"):
    st.write("Vuelve a armar la serie con todos los archivos originales. Los archivos originales no se modifican.")
    if st.button("Actualizar serie de trabajo", type="primary", on_click=abrir, args=("serie",)):
        try:
            with st.spinner("Actualizando la serie..."):
                actualizar_serie_trabajo()
        except ValueError as error:
            st.error(str(error))
        else:
            avisar("serie", "La serie de trabajo se actualizó. Las demás pantallas ya utilizan los datos nuevos.")

# Informe de calidad
st.subheader("Informe de calidad", anchor=False)
serie = leer_serie()
st.write(f"Serie de trabajo: de {formato_mes(serie['MES'].min())} a {formato_mes(serie['MES'].max())}, {len(serie)} meses.")
informe = informe_calidad(serie)
incompletas = informe["estaciones_incompletas"]

conteos = [(CONTROLES[clave][0], len(informe[clave])) for clave in CONTROLES]
conteos.append(("Estaciones incompletas", len(incompletas)))
columnas = st.columns(3)
for posicion, (titulo, cantidad) in enumerate(sorted(conteos, key=lambda par: par[1], reverse=True)):
    columnas[posicion % 3].metric(titulo, cantidad)

for clave, (titulo, explicacion) in CONTROLES.items():
    meses = informe[clave]
    if len(meses) > 0:
        with st.expander(f"{titulo} ({len(meses)})"):
            st.write(explicacion)
            st.write(", ".join(formato_mes(mes) for mes in meses))

if len(incompletas) > 0:
    with st.expander(f"Estaciones incompletas ({len(incompletas)})"):
        st.write("Estaciones con menos de 6 meses de datos. No se usan para evaluar los modelos.")
        st.write(", ".join(f"{nombre_estacion(fila.ESTACION, fila.ANIO_ESTACION)} ({fila.MESES} meses)" for fila in incompletas.itertuples()))

st.caption("Los valores marcados no son borrados, quedan en la serie para que el Operador los revise.")