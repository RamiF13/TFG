import pandas as pd

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
        tablas.append(filtrar_agente(leer_reqmax(ruta)))
    serie = pd.concat(tablas).sort_values("MES").reset_index(drop=True)
    return serie


def csv_tabla(serie,ruta):
    """Guarda la tabla a formato CSV"""
    serie.to_csv(ruta, index=False)
