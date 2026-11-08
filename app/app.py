
import streamlit as st
from servicios import verificar_ingreso, RUTA_USUARIOS

st.set_page_config(page_title="Soporte a la declaración de DME", layout="wide")

if "rol" not in st.session_state:
    st.session_state["rol"] = None


def pantalla_ingreso():
    st.markdown("<div style='text-align: center; font-size: 2.75rem; font-weight: 700;'>Inicio de sesión</div>", unsafe_allow_html=True)
    st.caption("Historia HU-08 - Operador del prototipo y Responsable de la declaración")
    _, centro, _ = st.columns([1, 1, 1])
    with centro.container(border=True):
        st.subheader("Soporte a la declaración de Demanda Máxima Estacional", anchor=False)
        st.caption("Agente CTRELEUW")
        with st.form("ingreso"):
            usuario = st.text_input("Usuario")
            contrasena = st.text_input("Contraseña", type="password")
            ingresar = st.form_submit_button("Ingresar", type="primary")
        if ingresar:
            rol = verificar_ingreso(RUTA_USUARIOS, usuario, contrasena)
            if rol is None:
                st.error("Error: usuario o contraseña incorrectos.")
            else:
                st.session_state["rol"] = rol
                st.session_state["usuario"] = usuario.strip().lower()
                st.rerun()

if st.session_state["rol"] is None:
    navegacion = st.navigation([st.Page(pantalla_ingreso, title="Inicio de sesión")])
else:
    with st.sidebar:
        st.markdown("**Soporte a la declaración de Demanda Máxima Estacional**")
        st.caption(f"Agente CTRELEUW - Usuario: {st.session_state['usuario']}")
        if st.button("Cerrar sesión"):
            st.session_state["rol"] = None
            st.rerun()
    if st.session_state["rol"] == "OPERADOR":
        paginas = {"Operador del prototipo": [
            st.Page("paginas/carga_calidad.py", title="1. Carga y calidad de datos"),
            st.Page("paginas/ejecucion_pronostico.py", title="2. Ejecución del pronóstico"),
            st.Page("paginas/parametros_regulatorios.py", title="3. Parámetros regulatorios"),
        ]}
    elif st.session_state["rol"] == "RESPONSABLE":
        paginas = {"Responsable de la declaración": [
            st.Page("paginas/evaluacion_retrospectiva.py", title="4. Evaluación retrospectiva"),
            st.Page("paginas/consulta_declaracion.py", title="5. Consulta de la declaración"),
        ]}
    else:
        st.error("El rol del usuario no es válido.")
        st.stop()
    navegacion = st.navigation(paginas)


navegacion.run()