
import streamlit as st
from servicios import verificar_ingreso, RUTA_USUARIOS

st.set_page_config(page_title="Soporte a la declaración de DME", layout="wide")

if "rol" not in st.session_state:
    st.session_state["rol"] = None


def pantalla_ingreso():
    st.markdown("<h1 style='text-align: center;'>Inicio de sesión</h1>", unsafe_allow_html=True)
    st.caption("Historia HU-08 - Operador del prototipo y Responsable de la declaración")
    _, centro, _ = st.columns([1, 1, 1])
    with centro.container(border=True):
        st.subheader("Soporte a la declaración de Demanda Máxima Estacional")
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
    consulta = st.Page("paginas/consulta_declaracion.py", title="5. Consulta de la declaración")
    navegacion = st.navigation({"Responsable de la declaración": [consulta]})

navegacion.run()