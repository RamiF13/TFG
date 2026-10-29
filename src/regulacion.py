import pandas as pd
import numpy as np

#calcular_piso
porcentaje_piso = 0.9
porcentaje_transitorio = 0.75
estacion_transitoria = "VERANO"
anio_transitorio = 2025

#calcular_hrp
horas_hrp_por_dia = 18

#calcular_cargo
kp = {
    1 : 1.1,
    2 : 1.1,
    3 : 0.9,
    4 : 0.9,
    5 : 0.9,
    6 : 1.1,
    7 : 1.1,
    8 : 1.1,
    9 : 0.9,
    10 : 0.9,
    11 : 0.9,
    12 : 1.1,
}
precio_ppad = 16
fpunta = 1



def calcular_piso(maximos):
    """Calcula el piso de cada estación en base a la anterior, si esta estaba completa"""
    maximo_anterior = maximos.groupby("ESTACION")["MAXIMO_MW"].shift(1)
    anterior_completa = maximos.groupby("ESTACION")["COMPLETA"].shift(1)
    maximos["MAXIMO_ANTERIOR_MW"] = maximo_anterior.where(anterior_completa == True)
    maximos["PORCENTAJE_PISO"] = porcentaje_piso
    transitorio = (maximos["ESTACION"] == estacion_transitoria) & (maximos["ANIO_ESTACION"] == anio_transitorio)
    maximos.loc[transitorio, "PORCENTAJE_PISO"] = porcentaje_transitorio
    maximos["PISO_MW"] = (maximos["MAXIMO_ANTERIOR_MW"] * maximos["PORCENTAJE_PISO"]).round(3)
    return maximos


def asignar_piso(serie, maximos):
    """Agrega a cada mes el piso de su estación"""
    columnas = maximos[["ESTACION", "ANIO_ESTACION", "PISO_MW"]]
    serie = serie.merge(columnas, on=["ESTACION", "ANIO_ESTACION"], how="left")
    return serie


def calcular_hrp(serie):
    """Calcula los días hábiles y las horas de remuneración de la potencia (HRP) de cada mes"""
    inicio_mes = serie["MES"].values.astype("datetime64[D]")
    fin_mes = (serie["MES"] + pd.offsets.MonthBegin(1)).values.astype("datetime64[D]")
    serie["DIAS_HABILES"] = np.busday_count(inicio_mes, fin_mes)
    serie["HRP"] = serie["DIAS_HABILES"] * horas_hrp_por_dia
    return serie


def calcular_cargo(serie, columna_declarada="POTENCIA_DECLARADA_MW"):
    """Calcula el cargo mensual por potencia según la Res. SE 400/2025, con el mayor entre la demanda registrada y el valor declarado"""
    serie["KP"] = serie["MES"].dt.month.map(kp)
    serie["REQ_POT_MW"] = np.maximum(serie["MAX_REAL_MW"], serie[columna_declarada])
    serie["CARGO_USD"] = (precio_ppad * serie["KP"] * serie["REQ_POT_MW"] * fpunta * serie["HRP"]).round(2)
    return serie

def cargo_estacion(serie):
    """Suma el cargo por potencia de los meses de cada estación"""
    cargo_estacional = serie.groupby(["ESTACION","ANIO_ESTACION"])["CARGO_USD"].sum()
    return cargo_estacional