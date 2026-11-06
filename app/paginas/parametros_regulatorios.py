
from datetime import date
import pandas as pd
import streamlit as st
from servicios import leer_parametros_completos, guardar_parametros_editados
from regulacion import validar_parametros

ETIQUETAS = {
    "precio_ppad": "Precio de la potencia (PPAD)",
    "porcentaje_piso": "Porcentaje del piso",
    "porcentaje_transitorio": "Porcentaje del piso transitorio",
    "estacion_transitoria": "Estación del piso transitorio",
    "anio_transitorio": "Año del piso transitorio",
    "kp_pico": "KP de los meses pico",
    "kp_resto": "KP del resto de los meses",
    "meses_kp_pico": "Meses pico del KP",
    "fpunta": "Factor de punta (FPunta)",
    "horas_hrp_por_dia": "Horas fuera de valle por día",
}
CAMPOS = {"valor": "Valor", "norma": "Norma", "vigencia_desde": "Vigencia desde"}
MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
         7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
DECIMALES = ["precio_ppad", "kp_pico", "kp_resto", "fpunta"]
PORCENTAJES = ["porcentaje_piso", "porcentaje_transitorio"]
TRANSITORIOS = ["porcentaje_transitorio", "estacion_transitoria", "anio_transitorio"]

def formato_valor(clave, valor):
    """Devuelve el valor como texto para mostrarlo en las tablas"""
    if clave == "meses_kp_pico":
        return ", ".join(MESES[mes] for mes in valor)
    return str(valor)


def clave_control(clave, campo):
    """Arma el nombre del control con el número de versión del formulario, que cambia al descartar"""
    return f"{clave}_{campo}_{st.session_state['version_formulario']}"


def valor_con_unidad(clave, dato):
    """Devuelve el valor con su unidad para la tabla y los títulos de los desplegables"""
    texto = formato_valor(clave, dato["valor"])
    if dato["unidad"]:
        texto = f"{texto} {dato['unidad']}"
    return texto


def control_valor(clave, valor):
    """Muestra el control que corresponde a cada parámetro y devuelve lo que eligió el Operador"""
    if clave in DECIMALES:
        return round(st.number_input("Valor", value=float(valor), min_value=0.0, format="%.2f", key=clave_control(clave, "valor")), 4)
    if clave in PORCENTAJES:
        return round(st.number_input("Valor", value=float(valor), min_value=0.0, max_value=100.0, format="%.2f", key=clave_control(clave, "valor")), 4)
    if clave == "horas_hrp_por_dia":
        return st.number_input("Valor", value=int(valor), min_value=0, max_value=24, step=1, key=clave_control(clave, "valor"))
    if clave == "anio_transitorio":
        return st.number_input("Valor", value=int(valor), min_value=2000, max_value=2100, step=1, key=clave_control(clave, "valor"))
    if clave == "estacion_transitoria":
        opciones = ["VERANO", "INVIERNO"]
        return st.selectbox("Valor", opciones, index=opciones.index(valor), key=clave_control(clave, "valor"))
    if clave == "meses_kp_pico":
        return st.multiselect("Valor", list(MESES), default=valor, format_func=MESES.get, key=clave_control(clave, "valor"))


def calcular_cambios(originales, editados):
    """Arma la tabla de los campos que cambiaron, con el valor anterior y el nuevo"""
    cambios = []
    for clave in editados:
        for campo in CAMPOS:
            antes = originales[clave][campo]
            despues = editados[clave][campo]
            if clave == "meses_kp_pico" and campo == "valor":
                distinto = sorted(antes) != sorted(despues)
            else:
                distinto = antes != despues
            if distinto:
                if campo == "valor":
                    antes, despues = formato_valor(clave, antes), formato_valor(clave, despues)
                cambios.append({"Parámetro": ETIQUETAS[clave], "Campo": CAMPOS[campo], "Antes": str(antes), "Después": str(despues)})
    return pd.DataFrame(cambios)


@st.dialog("¿Está seguro?", width="large")
def confirmar(editados, cambios):
    st.write("Se van a guardar estos cambios en los parámetros regulatorios:")
    st.dataframe(cambios, hide_index=True, use_container_width=True)
    col_no, col_si = st.columns(2)
    if col_si.button("Sí, guardar", type="primary", use_container_width=True):
        try:
            guardar_parametros_editados(editados)
            st.session_state["parametros_guardados"] = True
        except ValueError as error:
            st.session_state["error_guardado"] = str(error)
        st.rerun()
    if col_no.button("No, volver", use_container_width=True):
        st.rerun()


def descartar_edicion():
    """Cambia la versión del formulario para que los controles vuelvan a los valores del archivo"""
    st.session_state["version_formulario"] += 1


@st.dialog("¿Descartar los cambios?", width="large")
def confirmar_descarte(cambios):
    st.write("Se van a perder estos cambios sin guardar:")
    st.dataframe(cambios, hide_index=True, use_container_width=True)
    col_no, col_si = st.columns(2)
    if col_si.button("Sí, descartar", type="primary", use_container_width=True):
        descartar_edicion()
        st.rerun()
    if col_no.button("No, volver", use_container_width=True):
        st.rerun()
st.title("Parámetros regulatorios", anchor=False)
st.caption("Historia HU-04 - Operador del prototipo")

if st.session_state.pop("parametros_guardados", False):
    st.success("Los parámetros se guardaron. Los próximos cálculos ya usan los valores nuevos.")
if "error_guardado" in st.session_state:
    st.error(st.session_state.pop("error_guardado"))

originales = leer_parametros_completos()

st.subheader("Parámetros vigentes", anchor=False)
vigentes = pd.DataFrame([
    {"Parámetro": ETIQUETAS[clave], "Valor": valor_con_unidad(clave, dato),
     "Norma": dato["norma"], "Vigencia desde": dato["vigencia_desde"]}
    for clave, dato in originales.items()
])
st.dataframe(vigentes, hide_index=True, use_container_width=True)

st.subheader("Editar parámetros", anchor=False)
st.write("Un cambio de unidad o de moneda en la norma requiere modificar el código.")
st.write("El piso transitorio (75% en el verano 2025, Res. SE 22/2026, art. 6) ya venció y se conserva para recalcular esa estación.")
st.session_state.setdefault("version_formulario", 0)
with st.form("editar_parametros"):
    st.write("Abrí los parámetros que quieras cambiar. Los que no abras quedan como están.")
    editados = {}
    for clave, dato in originales.items():
        if clave in TRANSITORIOS:
            continue
        titulo = f"{ETIQUETAS[clave]}: {valor_con_unidad(clave, dato)}".replace("$", "\\$")
        with st.expander(titulo):
            col_valor, col_norma, col_vigencia = st.columns([1, 2, 1])
            with col_valor:
                valor = control_valor(clave, dato["valor"])
            with col_norma:
                norma = st.text_area("Norma", value=dato["norma"], height=68, key=clave_control(clave, "norma"))
            with col_vigencia:
                vigencia = st.date_input("Vigencia desde", value=date.fromisoformat(dato["vigencia_desde"]), format="DD/MM/YYYY", key=clave_control(clave, "vigencia"))
        editados[clave] = {"valor": valor, "norma": " ".join(norma.split()), "vigencia_desde": vigencia.isoformat()}
    col_guardar, col_descartar = st.columns(2)
    enviado = col_guardar.form_submit_button("Guardar cambios", type="primary", use_container_width=True)
    descartado = col_descartar.form_submit_button("Descartar cambios", use_container_width=True)
if descartado:
    cambios = calcular_cambios(originales, editados)
    if cambios.empty:
        st.info("No hay cambios para descartar.")
    else:
        confirmar_descarte(cambios)
if enviado:
    valores = {clave: dato["valor"] for clave, dato in originales.items()}
    valores.update({clave: editados[clave]["valor"] for clave in editados})
    try:
        validar_parametros(valores)
        errores = []
    except ValueError as error:
        errores = str(error).split("\n")
    errores += [f"La norma de {ETIQUETAS[clave]} no puede quedar vacía" for clave in editados if not editados[clave]["norma"]]
    if errores:
        lista = "\n".join(f"- {linea}" for linea in errores)
        st.error(f"Existen errores en los parámetros. No se realizaron los cambios.\n\n{lista}")
    else:
        cambios = calcular_cambios(originales, editados)
        if cambios.empty:
            st.info("No hay cambios por guardar.")
        else:
            confirmar(editados, cambios)