
import json
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

RUTA_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.append(str(RUTA_PROYECTO / "src"))

from modelado import asignar_estaciones, calcular_maximos_estacionales, pronosticar_estacion, proxima_estacion, pronosticar_hw_estacion, fechas_estacion, registrar_ejecucion, cobertura_banda, union_serie_trabajo
from regulacion import cargar_parametros, proyectar_cargo, vigencia_parametros, declaradas_estacionales, senalar_ajuste, calcular_piso, sobrecosto_por_estacion, guardar_parametros
from usuarios import verificar_ingreso
from evaluacion import errores_maximo, cargos_retrospectivos, unir_estaciones, resumen_metricas, MODELOS
from carga_cammesa import union_filtro, meses_faltantes, csv_tabla
from carga_openmeteo import calculos_mensuales
from calidad import rango, rangos_temperatura, rangos_cammesa

RUTA_SERIE = RUTA_PROYECTO / "data" / "processed" / "SERIE_TRABAJO_CTRELEUW.csv"
RUTA_PARAMETROS = RUTA_PROYECTO / "data" / "parametros" / "PARAMETROS_REGULATORIOS.json"
RUTA_USUARIOS = RUTA_PROYECTO / "data" / "usuarios" / "USUARIOS.json"
RUTA_REGISTRO = RUTA_PROYECTO / "data" / "registros" / "EJECUCIONES_PRONOSTICO.csv"
RUTA_RETROSPECTIVO = RUTA_PROYECTO / "data" / "processed" / "RETROSPECTIVO_CTRELEUW.csv"
RUTA_RETROSPECTIVO_MENSUAL = RUTA_PROYECTO / "data" / "processed" / "RETROSPECTIVO_MENSUAL_CTRELEUW.csv"
RUTA_RAW_CAMMESA = RUTA_PROYECTO / "data" / "raw" / "cammesa"
RUTA_RAW_OPENMETEO = RUTA_PROYECTO / "data" / "raw" / "openmeteo"
RUTA_CAMMESA = RUTA_PROYECTO / "data" / "processed" / "CAMMESA_CTRELEUW_ReqMax.csv"
RUTA_TEMPERATURA = RUTA_PROYECTO / "data" / "processed" / "OPENMETEO_TRELEW_TempMensual.csv"
INICIO_REGIMEN = pd.Timestamp("2025-11-01")

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

@st.cache_data
def leer_serie():
    """Lee la serie de trabajo y le asigna la estación de cada mes"""
    serie = pd.read_csv(RUTA_SERIE, parse_dates=["MES"])
    serie = asignar_estaciones(serie)
    return serie

def actualizar_serie_trabajo():
    """Regenera los CSV de CAMMESA, de temperatura y la serie de trabajo a partir de los archivos crudos, y borra la caché de la app"""
    rutas_cammesa = sorted(RUTA_RAW_CAMMESA.glob("CAMMESA_MEM_ReqMax_*.xlsx"))
    cammesa = union_filtro(rutas_cammesa)
    csv_tabla(cammesa, RUTA_CAMMESA)
    ruta_temperatura = sorted(RUTA_RAW_OPENMETEO.glob("OPENMETEO_ERA5_temp_*.json"))[-1]
    with open(ruta_temperatura, encoding="utf-8") as archivo:
        temperatura = calculos_mensuales(json.load(archivo))
    csv_tabla(temperatura, RUTA_TEMPERATURA)
    cammesa = pd.read_csv(RUTA_CAMMESA, parse_dates=["MES"])
    temperatura = pd.read_csv(RUTA_TEMPERATURA, parse_dates=["MES"])
    serie = union_serie_trabajo(cammesa, temperatura)
    csv_tabla(serie, RUTA_SERIE)
    st.cache_data.clear()
    return serie


def informe_calidad(serie):
    """Resume los controles de calidad de la serie: meses faltantes, revisados entre ediciones, posible copia de la declaración y valores fuera de rango"""
    estaciones = calcular_maximos_estacionales(asignar_estaciones(serie.copy()))
    return {
        "faltantes": meses_faltantes(serie),
        "revisados": serie.loc[serie["REVISADO"], "MES"],
        "posible_copia": serie.loc[serie["POSIBLE_COPIA_DECLARACION"], "MES"],
        "fuera_rango_demanda": serie.loc[rango(serie, rangos_cammesa), "MES"],
        "fuera_rango_temperatura": serie.loc[rango(serie, rangos_temperatura), "MES"],
        "estaciones_incompletas": estaciones.loc[~estaciones["COMPLETA"], ["ESTACION", "ANIO_ESTACION", "MESES"]]
    }


def leer_parametros():
    """Lee los parámetros regulatorios del JSON"""
    return cargar_parametros(RUTA_PARAMETROS)


def leer_parametros_completos():
    """Lee el archivo de parámetros con el valor, la unidad, la norma y la vigencia de cada uno, para mostrarlos en la pantalla"""
    with open(RUTA_PARAMETROS, encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_parametros_editados(editados):
    """Guarda los parámetros editados en la pantalla. Si algún valor no es válido, da ValueError y no escribe el archivo"""
    guardar_parametros(RUTA_PARAMETROS, editados)


@st.cache_data
def calcular_consulta(estacion, anio, parametros):
    """Guarda en caché el pronóstico de la estación y la proyección del cargo para no recalcularlos en cada interacción"""
    serie = leer_serie()
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
    historial["ETIQUETA"] = [etiqueta_estacion(estacion, anio) for anio in historial["ANIO_ESTACION"]]
    return historial[["ANIO_ESTACION", "ETIQUETA", "MAXIMO_MW", "DECLARADA_MAX_MW", "DECLARADA_MEDIA_MW"]]


@st.cache_data
def calcular_pronostico(estacion, anio):
    """Guarda en caché el pronóstico de la estación con la regresión cuantílica, Holt-Winters y la repetición del pico anterior"""
    serie = leer_serie()
    futuro, _, cuantiles_maximo, entrenamiento = pronosticar_estacion(serie, estacion, anio)
    pronostico_hw = pronosticar_hw_estacion(serie, estacion, anio)
    maximos = calcular_maximos_estacionales(serie)
    anterior = maximos[(maximos["ESTACION"] == estacion) & (maximos["ANIO_ESTACION"] == anio - 1)]
    modelos = pd.DataFrame({
        "Modelo": ["Regresión cuantílica (valor central)", "Repetición del pico de la estación anterior", "Holt-Winters"],
        "Máximo estacional pronosticado (MW)": [cuantiles_maximo[1], anterior["MAXIMO_MW"].iloc[0], pronostico_hw.max()],
    })
    return futuro, cuantiles_maximo, modelos, entrenamiento


def ejecutar_pronostico(estacion, anio):
    """Ejecuta el pronóstico de la estación y agrega la ejecución al registro"""
    futuro, cuantiles_maximo, modelos, entrenamiento = calcular_pronostico(estacion, anio)
    inicio, fin = fechas_estacion(estacion, anio)
    registro = registrar_ejecucion(leer_serie(), entrenamiento, inicio, fin, cuantiles_maximo, RUTA_REGISTRO)
    return futuro, cuantiles_maximo, modelos, registro


def formato_mes(fecha):
    """Devuelve el mes como texto abreviado junto con su año en castellano"""
    return f"{MESES[fecha.month - 1]} {fecha.year}"


@st.cache_data
def cobertura_retrospectiva():
    """Devuelve la cobertura observada de la banda del máximo estacional en el pronóstico retrospectivo"""
    retrospectivo = pd.read_csv(RUTA_RETROSPECTIVO)
    return cobertura_banda(retrospectivo["MAXIMO_MW"], retrospectivo["Q10_MW"], retrospectivo["Q90_MW"])


@st.cache_data
def calcular_evaluacion(parametros):
    """Calcula y guarda en caché todo lo que muestra la pantalla de evaluación retrospectiva"""
    serie = leer_serie()
    maximos = calcular_piso(calcular_maximos_estacionales(serie), parametros)
    retrospectivo = pd.read_csv(RUTA_RETROSPECTIVO)
    mensual = pd.read_csv(RUTA_RETROSPECTIVO_MENSUAL, parse_dates=["MES"])

    estaciones = unir_estaciones(retrospectivo, maximos, declaradas_estacionales(serie))
    estaciones["ETIQUETA"] = [etiqueta_estacion(estacion, anio) for estacion, anio in zip(estaciones["ESTACION"], estaciones["ANIO_ESTACION"])]
    errores = errores_maximo(retrospectivo)
    cargos = cargos_retrospectivos(mensual, serie, maximos, parametros)
    sobrecosto = sobrecosto_por_estacion(serie, maximos, INICIO_REGIMEN, serie["MES"].max(), parametros)
    return estaciones, errores, cargos, sobrecosto


def formato_miles(valor):
    """Devuelve el número sin decimales y con punto de miles"""
    return f"{valor:,.0f}".replace(",", ".")