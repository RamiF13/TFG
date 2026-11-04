import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import statsmodels.formula.api as smf

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

#preparar_serie_hw - FECHA ATIPICA
FECHA_ATIPICA = pd.Timestamp("2020-04-01")

#pronosticar_hw
tendencia = None
estacional = "add"
periodos_estacionales = 12

#calcular_grados
umbral = 14

#pronosticar_cuantiles
formula = "MAX_REAL_MW ~ GRADOS_FRIO + GRADOS_CALOR"
cuantiles = np.arange(0.01, 1, 0.01).round(2)
niveles = [0.1, 0.5, 0.9]
paso = 0.01
max_iteraciones = 5000

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


def calcular_grados(tabla, umbral=umbral):
    """Agrega los grados de frío y de calor de cada mes respecto del umbral de temperatura"""
    tabla["GRADOS_FRIO"] = (umbral - tabla["TEMPERATURA_MEDIA_C"]).clip(lower=0)
    tabla["GRADOS_CALOR"] = (tabla["TEMPERATURA_MEDIA_C"] - umbral).clip(lower=0)
    return tabla


def filtrar_entrenamiento(serie, fecha_atipica=FECHA_ATIPICA):
    """Devuelve los meses aptos para entrenar, sin las posibles copias de la declaración ni el mes atípico"""
    meses_validos = ((~serie["POSIBLE_COPIA_DECLARACION"]) & (serie["MES"] != fecha_atipica))
    return serie[meses_validos]


def calcular_temperatura_media(serie):
    """Calcula la temperatura media de cada mes del calendario, promediando todos los años"""
    temp_media = serie.groupby(serie["MES"].dt.month)["TEMPERATURA_MEDIA_C"].mean()
    return temp_media


def armar_futuro(inicio, fin, temperatura):
    """Arma la tabla de los meses a pronosticar con la temperatura climatológica y sus grados de frío y calor"""
    fechas = pd.date_range(inicio, fin, freq="MS")
    futuro = pd.DataFrame({"MES" : fechas})
    futuro["TEMPERATURA_MEDIA_C"] = futuro["MES"].dt.month.map(temperatura)
    futuro = calcular_grados(futuro)
    return futuro


def pronosticar_cuantiles(entrenamiento, futuro, max_iter=max_iteraciones):
    """Ajusta la regresión cuantílica para cada cuantil, pronostica los meses futuros y ordena cada fila para evitar cruces"""
    escalera = {}
    modelo_cuantil = smf.quantreg(formula, entrenamiento)
    for cuantil in cuantiles:
        modelo_entrenado = modelo_cuantil.fit(q=cuantil, max_iter=max_iter)
        escalera[cuantil] = modelo_entrenado.predict(futuro)
    tabla_cuantiles = pd.DataFrame(escalera)
    ordenado = np.sort(tabla_cuantiles,axis=1)
    tabla_ordenada = pd.DataFrame(ordenado, columns=tabla_cuantiles.columns)
    return tabla_ordenada


def maximo_estacional(tabla_ordenada):
    """Calcula los cuantiles del máximo de la estación a partir de los cuantiles mensuales"""
    inicio = (tabla_ordenada.min()).min()
    fin = (tabla_ordenada.max()).max()
    valores = np.arange(inicio, fin + paso, paso)
    prob_maximo = np.ones(len(valores))
    for _, fila in tabla_ordenada.iterrows():
        f = np.interp(valores, fila.values, cuantiles, left=0, right=1)
        prob_maximo = prob_maximo * f
    cuantiles_maximo = np.interp(niveles, prob_maximo, valores)
    return cuantiles_maximo


def registrar_ejecucion(serie, entrenamiento, fecha_inicio, fecha_fin, cuantiles_maximo,ruta):
    """Agrega al registro una fila con la fecha, datos usados, configuración y el resultado de la ejecución"""
    fila = {
    "FECHA_EJECUCION" : pd.Timestamp.now().floor("s"),
    "DATOS_DESDE" : serie["MES"].min(),
    "DATOS_HASTA" : serie["MES"].max(),
    "MESES_ENTRENAMIENTO" : len(entrenamiento),
    "ESTACION_INICIO" : fecha_inicio,
    "ESTACION_FIN" : fecha_fin,
    "UMBRAL_C" : umbral,
    "CUANTILES" : ", ".join(str(n) for n in niveles),
    "MAXIMO_Q10" : cuantiles_maximo[0],
    "MAXIMO_Q50" : cuantiles_maximo[1],
    "MAXIMO_Q90" : cuantiles_maximo[2],
    }
    registro = pd.DataFrame([fila])
    registro.to_csv(ruta, mode="a", header=not ruta.exists(), index=False)
    return registro


def particion_temporal(validos, fecha_corte):
    """Divide los meses válidos en entrenamiento y prueba"""
    entrenamiento = validos[validos["MES"] <= fecha_corte]
    prueba = validos[validos["MES"] > fecha_corte]
    prueba = prueba.reset_index(drop=True)
    return entrenamiento, prueba


def metricas_bandas(prueba):
    """Calcula la cobertura de la banda 0.1 a 0.9, la proporción por debajo y por encima, y el error y sesgo de la mediana"""
    real = prueba["MAX_REAL_MW"]
    por_debajo = (real < prueba["PRED_10"]).mean()
    por_encima = (real > prueba["PRED_90"]).mean()
    cobertura = ((real >= prueba["PRED_10"]) & (real <= prueba["PRED_90"])).mean()
    mae = (real - prueba["PRED_50"]).abs().mean()
    sesgo = (real - prueba["PRED_50"]).mean()
    return {
        "COBERTURA" : cobertura,
        "POR_DEBAJO" : por_debajo,
        "POR_ENCIMA" : por_encima,
        "MAE" : mae,
        "SESGO" : sesgo
    }


def fechas_estacion(estacion, anio):
    """Devuelve el primer mes y el último mes de una estación"""
    if estacion == "INVIERNO":
        inicio = pd.Timestamp(year=anio, month=5 , day=1)
        fin = pd.Timestamp(year=anio, month=10, day=1)
    else:
        inicio = pd.Timestamp(year=anio, month=11 , day=1)
        fin = pd.Timestamp(year=anio + 1, month=4 , day=1)
    return inicio, fin

def pronostico_retrospectivo(serie, estaciones_evaluadas):
    """Pronostica cada estación evaluada usando solo los datos anteriores a su inicio, con la regresión cuantílica y Holt-Winters"""
    resultados = []
    mensuales = []
    estaciones_evaluadas = estaciones_evaluadas.reset_index(drop=True)
    for _, fila in estaciones_evaluadas.iterrows():
        inicio, fin = fechas_estacion(fila["ESTACION"], fila["ANIO_ESTACION"])
        pasado = serie[serie["MES"] < inicio].copy()
        pasado = calcular_grados(pasado)
        entrenamiento = filtrar_entrenamiento(pasado)
        temp_media = calcular_temperatura_media(pasado)
        futuro = armar_futuro(inicio, fin, temp_media)
        tabla_ordenada = pronosticar_cuantiles(entrenamiento, futuro)
        cuantiles_maximo = maximo_estacional(tabla_ordenada)
        #holt-winters
        serie_hw = preparar_serie_hw(pasado)
        pronostico_hw = pronosticar_hw(serie_hw, 6)
        pico_hw = pronostico_hw.max()
        resultados.append({
            "Q10_MW" : cuantiles_maximo[0],
            "Q50_MW" : cuantiles_maximo[1],
            "Q90_MW" : cuantiles_maximo[2],
            "HW_MW" : pico_hw,
        })
        mensual = pd.DataFrame({
            "ESTACION" : fila["ESTACION"],
            "ANIO_ESTACION" : fila["ANIO_ESTACION"],
            "MES" : futuro["MES"],
            "PRED_RC_MW" : tabla_ordenada[0.5].values,
            "PRED_HW_MW" : pronostico_hw.values
        })
        mensuales.append(mensual)
    resultados = pd.DataFrame(resultados)
    retrospectivo = pd.concat([estaciones_evaluadas, resultados], axis=1)
    mensuales = pd.concat(mensuales, ignore_index=True)
    return retrospectivo, mensuales


def pronostico_anterior_mensual(serie, tabla):
    """Agrega a la tabla como pronóstico la demanda máxima real del mismo mes del año anterior"""
    anteriores = serie[["MES", "MAX_REAL_MW"]].copy()
    anteriores["MES"] = anteriores["MES"] + pd.DateOffset(years=1)
    anteriores = anteriores.rename(columns={"MAX_REAL_MW": "PRED_ANT_MW"})
    tabla = tabla.merge(anteriores, on="MES", how="left")
    return tabla