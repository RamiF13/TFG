
import pandas as pd
from modelado import pronostico_anterior_mensual
from regulacion import asignar_piso, calcular_hrp, cargo_escenarios, parametros_defecto


MODELOS = {
    "RC": "Regresión cuantílica",
    "ANT": "Repetición del pico de la estación anterior",
    "HW": "Holt-Winters",
}


def errores_maximo(retrospectivo):
    """Calcula el error del máximo estacional de cada modelo, real menos pronóstico, en las estaciones donde pronostican los tres"""
    comunes = retrospectivo[retrospectivo["PRONOSTICO_ANT"].notna()].copy()
    comunes["ERROR_RC_MW"] = comunes["MAXIMO_MW"] - comunes["Q50_MW"]
    comunes["ERROR_HW_MW"] = comunes["MAXIMO_MW"] - comunes["HW_MW"]
    comunes["ERROR_ANT_MW"] = comunes["MAXIMO_MW"] - comunes["PRONOSTICO_ANT"]
    return comunes


def cargos_retrospectivos(retrospectivo_mensual, serie, maximos, parametros=parametros_defecto):
    """Calcula por estación el cargo de referencia con la demanda registrada y el proyectado por cada modelo, declarando el piso, y el error de cada modelo. Los máximos tienen que venir con el piso calculado"""
    mensual = retrospectivo_mensual.merge(serie[["MES", "MAX_REAL_MW"]], on="MES", how="left")
    mensual = pronostico_anterior_mensual(serie, mensual)
    mensual = asignar_piso(mensual, maximos)
    mensual = calcular_hrp(mensual, parametros)
    escenarios = {"CARGO_REFERENCIA_USD": "MAX_REAL_MW", "CARGO_RC_USD": "PRED_RC_MW", "CARGO_HW_USD": "PRED_HW_MW", "CARGO_ANT_USD": "PRED_ANT_MW"}
    mensual = cargo_escenarios(mensual, escenarios, parametros=parametros)
    cargos = mensual.groupby(["ESTACION", "ANIO_ESTACION"])[list(escenarios)].sum(min_count=6).reset_index()
    for modelo in MODELOS:
        cargos[f"ERROR_{modelo}_USD"] = cargos["CARGO_REFERENCIA_USD"] - cargos[f"CARGO_{modelo}_USD"]
    return cargos


def resumen_metricas(errores, cargos):
    """Arma la tabla de métricas por modelo: error absoluto medio y sesgo del máximo estacional en MW, y error absoluto medio del cargo en dólares"""
    filas = []
    for clave, nombre in MODELOS.items():
        filas.append({
            "MODELO": nombre,
            "MAE_MW": errores[f"ERROR_{clave}_MW"].abs().mean(),
            "SESGO_MW": errores[f"ERROR_{clave}_MW"].mean(),
            "MAE_CARGO_USD": cargos[f"ERROR_{clave}_USD"].abs().mean(),
        })
    return pd.DataFrame(filas)


def unir_estaciones(retrospectivo, maximos, declaradas):
    """Agrega a cada estación evaluada su piso y su potencia declarada máxima, ordenadas de la más antigua a la más reciente"""
    claves = ["ESTACION", "ANIO_ESTACION"]
    estaciones = asignar_piso(retrospectivo, maximos)
    estaciones = estaciones.merge(declaradas[claves + ["DECLARADA_MAX_MW"]], on=claves, how="left")
    return estaciones.sort_values(["ANIO_ESTACION", "ESTACION"]).reset_index(drop=True)