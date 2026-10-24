import pandas as pd
from calidad import mw_copia

# leer_reqmax
encabezado = 13

# filtrar_agente
agente = 'CTRELEUW'
nombres = {
    'MAXIMO REAL [MW]' : 'MAX_REAL_MW',
    'POTENCIA DECLARADA [MW]' : 'POTENCIA_DECLARADA_MW'
}

# detectar_revisados
tolerancia = 0.0005

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


def csv_tabla(tabla,ruta):
    """Guarda la tabla a formato CSV"""
    tabla.to_csv(ruta, index=False)


def extraer_fechas(ruta):
    """Devuelve la fecha de edición de la tabla y de descarga"""
    nombre_split = ruta.stem.split("_")
    if len(nombre_split) != 5:
        raise ValueError(f"Nombre inválido: {ruta.name}, se espera CAMMESA_MEM_ReqMax_aaaa-mm_aaaa-mm-dd \n siendo la primera la fecha de EDICIÓN y la segunda la fecha de DESCARGA")
    return nombre_split[3], nombre_split[4]

def meses_faltantes(tabla):
    """Devuelve que meses faltan en la serie"""
    inicio = tabla["MES"].min()
    fin = tabla["MES"].max()
    completa = pd.date_range(inicio, fin, freq="MS")
    return completa.difference(tabla["MES"])


def apilar_ediciones(rutas):
    """Apila ediciones de CAMMESA"""
    tablas = []
    for ruta in rutas:
        tabla = filtrar_agente(leer_reqmax(ruta))
        edicion, descarga = extraer_fechas(ruta)
        tabla["EDICION"] = edicion
        tabla["DESCARGA"] = descarga
        tablas.append(tabla)
    return pd.concat(tablas)


def detectar_revisados(ediciones):
    """Devuelve TRUE para cada mes que el valor cambió"""
    maximo = ediciones.groupby("MES")["MAX_REAL_MW"].max()
    minimo = ediciones.groupby("MES")["MAX_REAL_MW"].min()
    variacion = maximo - minimo
    return variacion > tolerancia

def deduplicar(ediciones):
    """Deduplica valores entre ediciones"""
    return ediciones.sort_values(["MES","EDICION","DESCARGA"]).drop_duplicates(subset="MES", keep="last").reset_index(drop=True)


def union_filtro(rutas):
    """Carga, une, deduplica, filtra, marca como revisados y detecta los meses con el máximo real copiado de la potencia declarada, los datos de los archivos REQ_MAX de CAMMESA"""
    ediciones = apilar_ediciones(rutas)
    revisados = detectar_revisados(ediciones)
    serie = deduplicar(ediciones)
    serie["REVISADO"] = serie["MES"].map(revisados)
    serie["COPIA_DECLARADA"] = mw_copia(serie)
    return serie
