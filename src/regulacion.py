import pandas as pd
import numpy as np
import json
from modelado import estacion_anterior

#parámetros regulatorios por defecto (mismas claves que PARAMETROS_REGULATORIOS.json)

parametros_defecto = {
    "precio_ppad" : 16,
    "porcentaje_piso" : 90,
    "porcentaje_transitorio" : 75,
    "estacion_transitoria" : "VERANO",
    "anio_transitorio" : 2025,
    "kp_pico" : 1.1,
    "kp_resto" : 0.9,
    "meses_kp_pico" : [12, 1, 2, 6, 7, 8],
    "fpunta" : 1,
        "hrp_dia_habil" : 16,
    "hrp_sabado" : 6,
    "hrp_domingo" : 4
}


def calcular_piso(maximos, parametros=parametros_defecto):
    """Calcula el piso de cada estación en base a la anterior, si esta estaba completa"""
    maximos = estacion_anterior(maximos, ["MAXIMO_MW", "COMPLETA"])
    maximos["MAXIMO_ANTERIOR_MW"] = maximos["MAXIMO_MW_ANTERIOR"].where(maximos["COMPLETA_ANTERIOR"] == True)
    maximos = maximos.drop(columns=["MAXIMO_MW_ANTERIOR", "COMPLETA_ANTERIOR"])
    maximos["PORCENTAJE_PISO"] = parametros["porcentaje_piso"] / 100
    transitorio = (maximos["ESTACION"] == parametros["estacion_transitoria"]) & (maximos["ANIO_ESTACION"] == parametros["anio_transitorio"])
    maximos.loc[transitorio, "PORCENTAJE_PISO"] = parametros["porcentaje_transitorio"] / 100
    maximos["PISO_MW"] = (maximos["MAXIMO_ANTERIOR_MW"] * maximos["PORCENTAJE_PISO"]).round(3)
    return maximos


def asignar_piso(serie, maximos):
    """Agrega a cada mes el piso de su estación"""
    columnas = maximos[["ESTACION", "ANIO_ESTACION", "PISO_MW"]]
    serie = serie.merge(columnas, on=["ESTACION", "ANIO_ESTACION"], how="left")
    return serie


def calcular_hrp(serie, parametros=parametros_defecto):
    """Calcula los días de cada tipo y las horas de remuneración de la potencia (HRP) de cada mes, según la tabla de CAMMESA"""
    inicio_mes = serie["MES"].values.astype("datetime64[D]")
    fin_mes = (serie["MES"] + pd.offsets.MonthBegin(1)).values.astype("datetime64[D]")
    serie["DIAS_HABILES"] = np.busday_count(inicio_mes, fin_mes, weekmask="1111100")
    serie["DIAS_SABADO"] = np.busday_count(inicio_mes, fin_mes, weekmask="0000010")
    serie["DIAS_DOMINGO"] = np.busday_count(inicio_mes, fin_mes, weekmask="0000001")
    serie["HRP"] = (serie["DIAS_HABILES"] * parametros["hrp_dia_habil"]
                    + serie["DIAS_SABADO"] * parametros["hrp_sabado"]
                    + serie["DIAS_DOMINGO"] * parametros["hrp_domingo"])
    return serie


def calcular_cargo(serie, columna_registrada="MAX_REAL_MW", columna_declarada="POTENCIA_DECLARADA_MW", parametros=parametros_defecto):
    """Calcula el cargo mensual por potencia según la Res. SE 400/2025, con el mayor entre la demanda registrada y el valor declarado"""
    es_pico = serie["MES"].dt.month.isin(parametros["meses_kp_pico"])
    serie["KP"] = np.where(es_pico, parametros["kp_pico"], parametros["kp_resto"])
    serie["REQ_POT_MW"] = np.maximum(serie[columna_registrada], serie[columna_declarada])
    serie["CARGO_USD"] = (parametros["precio_ppad"] * serie["KP"] * serie["REQ_POT_MW"] * parametros["fpunta"] * serie["HRP"]).round(2)
    return serie

def cargo_estacion(serie):
    """Suma el cargo por potencia de los meses de cada estación"""
    cargo_estacional = serie.groupby(["ESTACION","ANIO_ESTACION"])["CARGO_USD"].sum()
    return cargo_estacional


def cargar_parametros(ruta):
    """Lee el archivo de parámetros regulatorios, los valida y devuelve el valor de cada uno"""
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    parametros = {}
    for clave in datos:
        parametros[clave] = datos[clave]["valor"]
    validar_parametros(parametros)
    return parametros

def vigencia_parametros(ruta):
    """Devuelve la fecha de vigencia más reciente entre los parámetros regulatorios"""
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    fechas = [datos[clave]["vigencia_desde"] for clave in datos]
    return max(fechas)


def declaradas_estacionales(serie):
    """Calcula la potencia declarada máxima y promedio de cada estación"""
    tabla = serie.groupby(["ESTACION", "ANIO_ESTACION"]).agg(
        DECLARADA_MAX_MW=("POTENCIA_DECLARADA_MW", "max"),
        DECLARADA_MEDIA_MW=("POTENCIA_DECLARADA_MW", "mean"),
    )
    return tabla.reset_index()


def validar_parametros(parametros):
    """Revisa que los parámetros regulatorios tengan valores válidos y avisa si no se cumplen"""
    meses = parametros["meses_kp_pico"]
    errores = []
    for clave in ["precio_ppad", "kp_pico", "kp_resto", "fpunta"]:
        if parametros[clave] <= 0:
            errores.append(f"El parámetro {clave} tiene que ser mayor que 0 y vale {parametros[clave]}")
    for clave in ["porcentaje_piso", "porcentaje_transitorio"]:
        if not (0 <= parametros[clave] <= 100):
            errores.append(f"El parámetro {clave} tiene que estar entre 0 y 100, y vale {parametros[clave]}")
    if not (0 < parametros["hrp_dia_habil"] <= 24):
        errores.append(f"El parámetro hrp_dia_habil tiene que ser mayor que 0 y como máximo 24, y vale {parametros['hrp_dia_habil']}")
    for clave in ["hrp_sabado", "hrp_domingo"]:
        if not (0 <= parametros[clave] <= 24):
            errores.append(f"El parámetro {clave} tiene que estar entre 0 y 24, y vale {parametros[clave]}")
    for mes in meses:
        if not (1 <= mes <=12): 
            errores.append(f"El mes {mes} de meses_kp_pico no es válido, tiene que estar entre 1 y 12")
    if len(set(meses)) != len(meses):
        errores.append(f"meses_kp_pico tiene meses repetidos: {meses}")
    if parametros["estacion_transitoria"] not in ["VERANO", "INVIERNO"]:
        errores.append(f"estacion_transitoria tiene que ser VERANO o INVIERNO, y es {parametros['estacion_transitoria']}")
    if not (2000 <= parametros["anio_transitorio"] <= 2100):
        errores.append(f"El parámetro anio_transitorio tiene que ser un año de cuatro cifras entre 2000 y 2100, y vale {parametros['anio_transitorio']}")
    if errores:
        raise ValueError("\n".join(errores))


def guardar_parametros(ruta, editados):
    """Combina los campos editados con el archivo actual, valida los valores y guarda el archivo conservando la unidad de cada parámetro"""
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    for clave in editados:
        for campo in ["valor", "norma", "vigencia_desde"]:
            datos[clave][campo] = editados[clave][campo]
    sin_norma = [clave for clave in datos if not str(datos[clave]["norma"]).strip()]
    if sin_norma:
        raise ValueError(f"Estos parámetros no tienen norma: {', '.join(sin_norma)}")
    validar_parametros({clave: datos[clave]["valor"] for clave in datos})
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=4)


def cargo_escenarios(tabla, escenarios, columna_declarada="PISO_MW", parametros=parametros_defecto):
    """Calcula el cargo mensual de cada escenario, usando como demanda registrada la columna indicada para cada uno"""
    for nombre, columna in escenarios.items():
        calculado = calcular_cargo(tabla.copy(), columna_registrada=columna, columna_declarada=columna_declarada, parametros=parametros)
        tabla[nombre] = calculado["CARGO_USD"]
    return tabla


def sobrecosto_evitable(serie, maximos, fecha_inicio, fecha_fin, parametros=parametros_defecto):
    """Compara mes a mes el cargo con la potencia declarada contra el cargo declarando el piso, entre las fechas indicadas. Los máximos tienen que venir con el piso calculado"""
    tabla = serie[(serie["MES"] >= fecha_inicio) & (serie["MES"] <= fecha_fin)].copy()
    tabla = asignar_piso(tabla, maximos)
    tabla = calcular_hrp(tabla, parametros)
    tabla["CARGO_DECLARADO_USD"] = calcular_cargo(tabla.copy(), parametros=parametros)["CARGO_USD"]
    tabla["CARGO_PISO_USD"] = calcular_cargo(tabla.copy(), columna_declarada="PISO_MW", parametros=parametros)["CARGO_USD"]
    tabla["SOBRECOSTO_USD"] = tabla["CARGO_DECLARADO_USD"] - tabla["CARGO_PISO_USD"]
    return tabla


def sobrecosto_por_estacion(serie, maximos, fecha_inicio, fecha_fin, parametros=parametros_defecto):
    """Suma el sobrecosto de cada estación y cuenta cuántos meses con datos tiene"""
    meses = sobrecosto_evitable(serie, maximos, fecha_inicio, fecha_fin, parametros)
    return meses.groupby(["ESTACION", "ANIO_ESTACION"]).agg(
        SOBRECOSTO_USD=("SOBRECOSTO_USD", "sum"),
        MESES=("MES", "count"),
    ).reset_index()


def proyectar_cargo(futuro, maximos, estacion, anio, parametros=parametros_defecto):
    """Proyecta el cargo mensual de una estación con los cuantiles inferior, central y superior del pronóstico, declarando el piso"""
    maximos = maximos.copy()
    existe = ((maximos["ESTACION"] == estacion) & (maximos["ANIO_ESTACION"] == anio)).any()
    if not existe:
        proxima = pd.DataFrame({"ESTACION": [estacion], "ANIO_ESTACION": [anio], "COMPLETA": [False]})
        maximos = pd.concat([maximos, proxima], ignore_index=True)
    maximos = calcular_piso(maximos, parametros)
    futuro = futuro.copy()
    futuro["ESTACION"] = estacion
    futuro["ANIO_ESTACION"] = anio
    futuro = asignar_piso(futuro, maximos)
    futuro = calcular_hrp(futuro, parametros)
    escenarios = {"CARGO_Q10_USD": "Q10_MW", "CARGO_Q50_USD": "Q50_MW", "CARGO_Q90_USD": "Q90_MW"}
    futuro = cargo_escenarios(futuro, escenarios, parametros=parametros)
    return futuro


def senalar_ajuste(central, superior, piso):
    """Señala la estación si la banda superior del máximo estacional queda por debajo del piso e informa cuánto queda el piso por encima del pronóstico central y del superior"""
    return {
        "SENALADO": bool(superior < piso),
        "DIF_CENTRAL_MW": round(piso - central, 3),
        "DIF_SUPERIOR_MW": round(piso - superior, 3),
    }