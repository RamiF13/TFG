import pandas as pd
from pathlib import Path
# leer_reqmax
encabezado = 13

# filtrar_agente
agente = 'CTRELEUW'
nombres = {
    'MAXIMO REAL [MW]' : 'MAX_REAL_MW',
    'POTENCIA DECLARADA [MW]' : 'POTENCIA_DECLARADA_MW'
}

# Funciones

def leer_reqmax(ruta):
    """Carga del archivo REQ_MAX de CAMMESA"""
    df = pd.read_excel(ruta,header=encabezado)
    return df


def filtrar_agente(df):
    """Filtra por AGENTE NEMO = CTRELEUW"""
    df = df.rename(columns=nombres)
    mask = df['AGENTE NEMO'] == agente
    df = df.loc[mask,['MES','MAX_REAL_MW','POTENCIA_DECLARADA_MW']]
    return df


def union_filtro(rutas):
    """Carga y filtro de los archivos REQ_MAX de CAMMESA"""
    tablas = []
    for ruta in rutas:
        tabla = filtrar_agente(leer_reqmax(ruta))
        edicion, descarga = extraer_fechas(ruta)
        tabla["EDICION"] = edicion
        tabla["DESCARGA"] = descarga
        tablas.append(tabla)
    serie = pd.concat(tablas).sort_values(["MES","EDICION","DESCARGA"]).drop_duplicates(subset="MES", keep="last").reset_index(drop=True)
    return serie


def csv_tabla(serie,ruta):
    """Guarda la tabla a formato CSV"""
    serie.to_csv(ruta, index=False)


def extraer_fechas(ruta):
    """Devuelve la fecha de edición de la tabla y de descarga"""
    nombre_split = ruta.stem.split("_")
    if len(nombre_split) != 5:
        raise ValueError(f"Nombre inválido: {ruta.name}, se espera CAMMESA_MEM_ReqMax_aaaa-mm_aaaa-mm-dd \n siendo la primera la fecha de EDICIÓN y la segunda la fecha de DESCARGA")
    return nombre_split[3], nombre_split[4]
