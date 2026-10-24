import pandas as pd

#rango
rangos_temperatura = {
"TEMPERATURA_MEDIA_C" : (0.0, 26.2),
"TEMPERATURA_MAX_C" : (-15.3, 45.2),
"TEMPERATURA_MIN_C": (-15.3, 45.2)
}

rangos_cammesa = {
    "MAX_REAL_MW" : (0.001, float("inf")),
    "POTENCIA_DECLARADA_MW" : (0.001, float("inf"))
}

def rango(tabla, rangos):
    """Marca los valores estan fuera del rango esperado"""
    fuera = pd.Series(False, index=tabla.index)
    for columna in rangos:
        minimo, maximo = rangos[columna]
        fuera = fuera | ~tabla[columna].between(minimo,maximo)
    return fuera


def mw_copia(tabla):
    """Detecta valores máximos similares a los declarados"""
    diferencia = (tabla["POTENCIA_DECLARADA_MW"] - tabla["MAX_REAL_MW"]).abs()
    return diferencia < 0.01 