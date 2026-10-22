import pandas as pd
import requests
import json

# obtener_era5
url_base = "https://archive-api.open-meteo.com/v1/archive"

# calculos
calcs = {"temperature_2m_mean" : "mean",
        "temperature_2m_max" : "max",
        "temperature_2m_min" : "min"}

nombres_columnas = {"time" : "MES",
                    "temperature_2m_mean" : "TEMPERATURA_MEDIA_C",
                    "temperature_2m_max" : "TEMPERATURA_MAX_C",
                    "temperature_2m_min" : "TEMPERATURA_MIN_C"
                    }

# Funciones

def obtener_era5(inicio,fin):
    """Consulta a la API Open-Meteo (ERA5) y devuelve la respuesta en JSON"""
    diccionario = {
    "latitude" : -43.20894,
    "longitude" : -65.28209,
    "start_date" : inicio,
    "end_date" : fin,
    "timezone" : "America/Argentina/Buenos_Aires",
    "daily" : ['temperature_2m_mean','temperature_2m_max','temperature_2m_min'],
    "models" : "era5"
    }
    consulta = requests.get(url_base,params=diccionario)
    consulta.raise_for_status()
    return consulta.json()

def guardar_consulta(datos,ruta):
    """Guarda la consulta a Open-Meteo en la ruta asignada"""
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo)


def calculos_mensuales(datos):
    """Calcula MAX, MIN y media mensual de los datos"""
    df = pd.DataFrame(datos['daily'])
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index("time").resample("MS").agg(calcs)
    df = df.reset_index()
    df = df.rename(columns=nombres_columnas)
    return df