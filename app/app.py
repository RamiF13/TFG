
import streamlit as st

st.set_page_config(page_title="Soporte a la declaración de DME", layout="wide")

consulta = st.Page("paginas/consulta_declaracion.py", title="5. Consulta de la declaración")
navegacion = st.navigation({"Responsable de la declaración": [consulta]})
navegacion.run()