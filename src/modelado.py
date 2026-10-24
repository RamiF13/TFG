import pandas as pd
from pathlib import Path

def union_serie_trabajo(cammesa, temperatura):
    """Une la tabla de CAMMESA con la variable exógena de temperatura de OpenMeteo"""
    serie = cammesa.merge(temperatura, on="MES", how="left")
    return serie