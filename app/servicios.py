
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

RUTA_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.append(str(RUTA_PROYECTO / "src"))

from modelado import asignar_estaciones, calcular_maximos_estacionales, pronosticar_estacion, proxima_estacion
from regulacion import cargar_parametros, proyectar_cargo, vigencia_parametros, declaradas_estacionales, senalar_ajuste
from usuarios import verificar_ingreso

RUTA_SERIE = RUTA_PROYECTO / "data" / "processed" / "SERIE_TRABAJO_CTRELEUW.csv"
RUTA_PARAMETROS = RUTA_PROYECTO / "data" / "parametros" / "PARAMETROS_REGULATORIOS.json"
RUTA_USUARIOS = RUTA_PROYECTO / "data" / "usuarios" / "USUARIOS.json"

@st.cache_data
def leer_serie():
    """Lee la serie de trabajo y le asigna la estación de cada mes"""
    serie = pd.read_csv(RUTA_SERIE, parse_dates=["MES"])
    serie = asignar_estaciones(serie)
    return serie


@st.cache_data
def calcular_consulta(estacion, anio):
    """Guarda en caché el pronóstico de la estación y la proyección del cargo para no recalcularlos en cada interacción"""
    serie = leer_serie()
    parametros = cargar_parametros(RUTA_PARAMETROS)
    futuro, _, cuantiles_maximo, _ = pronosticar_estacion(serie, estacion, anio)
    maximos = calcular_maximos_estacionales(serie)
    futuro = proyectar_cargo(futuro, maximos, estacion, anio, parametros)
    piso = futuro["PISO_MW"].iloc[0]
    senal = senalar_ajuste(cuantiles_maximo[1], cuantiles_maximo[2], piso)
    return futuro, cuantiles_maximo, maximos, senal


def formato_mw(valor):
    """Devuelve el valor en MW como texto, con un decimal y coma decimal"""
    return f"{valor:.1f} MW".replace(".", ",")


def formato_usd(valor):
    """Devuelve el importe en dólares como texto, sin decimales y con punto de miles"""
    return f"U\\$S {valor:,.0f}".replace(",", ".")


def formato_millones(valor):
    """Devuelve el importe en millones de dólares como texto, con dos decimales y coma decimal"""
    return f"{valor / 1_000_000:.2f}".replace(".", ",")


def estacion_a_declarar():
    """Devuelve la estación siguiente a la última con datos"""
    estacion, anio = proxima_estacion(leer_serie())
    return estacion, int(anio)


def nombre_estacion(estacion, anio):
    """Devuelve el nombre de la estación para mostrar, con sus meses"""
    if estacion == "VERANO":
        return f"Verano {anio}-{str(anio + 1)[-2:]} (nov {anio} a abr {anio + 1})"
    return f"Invierno {anio} (may a oct {anio})"


def fechas_actualizacion():
    """Devuelve la fecha de la última carga de datos y la de vigencia de los parámetros, en formato dd/mm/aaaa"""
    ultima_carga = pd.Timestamp(leer_serie()["DESCARGA"].max()).strftime("%d/%m/%Y")
    vigencia = pd.Timestamp(vigencia_parametros(RUTA_PARAMETROS)).strftime("%d/%m/%Y")
    return ultima_carga, vigencia


def etiqueta_estacion(estacion, anio):
    """Devuelve el nombre corto de la estación para los ejes de los gráficos"""
    if estacion == "VERANO":
        return f"Ver. {str(anio)[-2:]}-{str(anio + 1)[-2:]}"
    return f"Inv. {str(anio)[-2:]}"


@st.cache_data
def historial_estacion(estacion):
    """Arma la demanda máxima registrada y la potencia declarada de las estaciones completas del mismo tipo"""
    serie = leer_serie()
    maximos = calcular_maximos_estacionales(serie)
    declaradas = declaradas_estacionales(serie)
    historial = maximos.merge(declaradas, on=["ESTACION", "ANIO_ESTACION"])
    historial = historial[(historial["ESTACION"] == estacion) & historial["COMPLETA"]].copy()
    historial["ETIQUETA"] = [etiqueta_estacion(e, a) for e, a in zip(historial["ESTACION"], historial["ANIO_ESTACION"])]
    return historial[["ANIO_ESTACION", "ETIQUETA", "MAXIMO_MW", "DECLARADA_MAX_MW", "DECLARADA_MEDIA_MW"]]