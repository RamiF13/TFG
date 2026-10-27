import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

#asignar_estaciones
estaciones = {
    1 : "VERANO",
    2 : "VERANO",
    3 : "VERANO", 
    4 : "VERANO", 
    5 : "INVIERNO",
    6 : "INVIERNO",
    7 : "INVIERNO",
    8 : "INVIERNO",
    9 : "INVIERNO",
    10 : "INVIERNO",
    11 : "VERANO", 
    12 : "VERANO"
}

#calcular_maximos_estacionales
meses_estacion = 6

#preparar_serie_hw
FECHA_ATIPICA = pd.Timestamp("2020-04-01")

#pronosticar_hw
tendencia = None
estacional = "add"
periodos_estacionales = 12

def union_serie_trabajo(cammesa, temperatura):
    """Une la tabla de CAMMESA con la variable exógena de temperatura de OpenMeteo"""
    serie = cammesa.merge(temperatura, on="MES", how="left")
    return serie
 

def asignar_estaciones(serie):
    """Asigna a cada mes su estación y el año en que empieza"""
    serie["ESTACION"] = serie["MES"].dt.month.map(estaciones)
    enero_abril = serie["MES"].dt.month <= 4
    serie["ANIO_ESTACION"] = serie["MES"].dt.year - enero_abril
    return serie


def calcular_maximos_estacionales(serie):
    """Calcula el máximo de cada estación, marca si es completa, y si su pico tiene una posible copia y si es utilizable"""
    tabla = serie.groupby(["ANIO_ESTACION", "ESTACION"]).agg(MAXIMO_MW=("MAX_REAL_MW","max"), MESES=("MAX_REAL_MW","count"))
    tabla["COMPLETA"] = tabla["MESES"] == meses_estacion
    filas_pico = serie.groupby(["ANIO_ESTACION", "ESTACION"])["MAX_REAL_MW"].idxmax()
    tabla["PICO_CON_COPIA"] = serie.loc[filas_pico, "POSIBLE_COPIA_DECLARACION"].values
    tabla["UTILIZABLE"] = ~tabla["PICO_CON_COPIA"] & tabla["COMPLETA"]
    tabla = tabla.reset_index()
    tabla = tabla.sort_values(["ESTACION", "ANIO_ESTACION"])
    return tabla


def pronostico_ingenuo(maximos):
    """Pronostica cada estación con el máximo de la misma estación del año anterior, si era utilizable y calcula su error"""
    maximos["PRONOSTICO_ANT"] = maximos.groupby("ESTACION")["MAXIMO_MW"].shift(1)
    ant_utilizable = maximos.groupby("ESTACION")["UTILIZABLE"].shift(1)
    maximos["PRONOSTICO_ANT"] = maximos["PRONOSTICO_ANT"].where(ant_utilizable == True)
    maximos["EVALUABLE"] = maximos["UTILIZABLE"] & maximos["PRONOSTICO_ANT"].notna()
    maximos["ERROR_MW"] = maximos["MAXIMO_MW"] - maximos["PRONOSTICO_ANT"]
    return maximos

def preparar_serie_hw(serie, fecha_atipica=FECHA_ATIPICA):
    """Arma la serie mensual para Holt-Winters, reemplazando el mes atípico por el promedio del mismo mes en los demás años"""
    serie_mensual = serie.set_index("MES")["MAX_REAL_MW"].asfreq("MS")
    fecha_tipica_mask = (serie_mensual.index.month == fecha_atipica.month) & (serie_mensual.index.year != fecha_atipica.year)
    fechas_normales = serie_mensual[fecha_tipica_mask]
    promedio_mes = fechas_normales.mean()
    serie_hw = serie_mensual.copy()
    serie_hw.loc[fecha_atipica] = promedio_mes
    return serie_hw

def pronosticar_hw(serie_hw,meses_pronostico):
    """Entrena Holt-Winters a la serie mensual y pronostica los meses pedidos"""
    modelo_hw = ExponentialSmoothing(serie_hw, trend=tendencia, seasonal=estacional, seasonal_periods=periodos_estacionales)
    fit_hw = modelo_hw.fit()
    pronostico = fit_hw.forecast(meses_pronostico)
    return pronostico
