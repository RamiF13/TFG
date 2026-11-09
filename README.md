# Prototipo de Pronóstico de la Demanda Máxima Estacional: Cooperativa Eléctrica de Trelew

Guía de instalación y uso del prototipo desarrollado como Trabajo Final de Grado de la Licenciatura en Ciencia de Datos (Universidad Siglo 21), modalidad Prototipado Tecnológico.

Autor: Ramiro Bernabé Ferreira Crettón.

## 1. Alcance del prototipo

El prototipo asiste la declaración de la Demanda Máxima Estacional de la Cooperativa Eléctrica de Consumo y Vivienda Ltda. de Trelew ante CAMMESA. Pronostica la demanda máxima de la estación con bandas de incertidumbre, la presenta junto al piso regulatorio y a las declaraciones históricas, proyecta el cargo por potencia y señala las estaciones en que podría justificarse solicitar el ajuste del piso.

El prototipo **no propone cuánto declarar**. Bajo la regla vigente (Res. SE 400/2025 y Res. SE 22/2026), declarar el piso regulatorio es la referencia de menor costo. La decisión del valor a declarar queda a cargo del Responsable de la declaración.

## 2. Requisitos

- Computadora con Windows 11.
- Python 3.12. 
  - Para verificar si ya está instalado, ejecutar `py -3.12 --version` en el Símbolo del sistema: si responde "Python 3.12" seguido del número de versión, no hace falta instalarlo. Si no, descargar el Python install manager desde https://www.python.org/downloads/ y, una vez instalado, ejecutar `pymanager install 3.12`.
- Git, disponible en https://git-scm.com/downloads.
- Conexión a internet para instalar las dependencias y para descargar la temperatura. El resto de las funciones operan sin conexión.

## 3. Instalación

Los comandos son ejecutados en una terminal. En Windows se recomienda utilizar "Símbolo del sistema", ya que PowerShell puede bloquear la activación del entorno virtual por su política de ejecución de scripts.

**3.1. Obtener el código.** Clonar el repositorio:

```
git clone https://github.com/RamiF13/TFG.git
cd TFG
```

**3.2. Crear el entorno virtual.** Dentro de la carpeta del proyecto:

```
py -3.12 -m venv .venv
```

El entorno virtual debe llamarse `.venv` y guardarse en la carpeta del proyecto, ya que el archivo de inicio lo busca en esa dirección.

**3.3. Activar el entorno e instalar las dependencias:**

```
.venv\Scripts\activate
pip install -r requirements.txt
```

La instalación puede demorar algunos minutos.

## 4. Registro de usuarios

El acceso al prototipo requiere usuario y contraseña. Por seguridad, el archivo de usuarios no se incluye en el repositorio, por lo que es necesario registrar al menos un usuario por rol. Con el entorno virtual activado:

```
python scripts\registrar_usuario.py
```

El script solicita el usuario, la contraseña (dos veces) y el rol:

- **OPERADOR**: Operador del prototipo. Accede a la carga y calidad de datos, la ejecución del pronóstico y los parámetros regulatorios.
- **RESPONSABLE**: Responsable de la declaración. Accede a la evaluación retrospectiva y a la consulta de la declaración.

La contraseña debe tener al menos 8 caracteres. Se recomienda ejecutar el script dos veces, una por rol. Para dar de baja un usuario, se elimina su entrada del archivo `data/usuarios/USUARIOS.json`.

## 5. Inicio del prototipo

Hacer doble clic en iniciar_prototipo.bat, en la carpeta del proyecto. Se abre una ventana del "Símbolo del sistema" y, a continuación, el prototipo en el navegador. Esa ventana debe permanecer abierta mientras se usa el prototipo. Para finalizar el prototipo, se cierra la ventana. Si el navegador no se abre automáticamente, ingresar a la dirección local que indica el "Símbolo del sistema". El prototipo se probó únicamente en Windows.

## 6. Uso por rol

| Rol | Pantalla | Función |
|---|---|---|
| Operador del prototipo | 1. Carga y calidad de datos | Incorpora los datos de CAMMESA y de temperatura y muestra el informe de calidad |
| Operador del prototipo | 2. Ejecución del pronóstico | Ejecuta el pronóstico de la estación y lo registra |
| Operador del prototipo | 3. Parámetros regulatorios | Actualiza los parámetros de la regla del cargo cuando cambia la normativa |
| Responsable de la declaración | 4. Evaluación retrospectiva | Compara los modelos en las estaciones pasadas y muestra el sobrecosto evitable |
| Responsable de la declaración | 5. Consulta de la declaración | Muestra el pronóstico, el piso, el cargo proyectado y el señalamiento |

El repositorio incluye los datos hasta septiembre de 2026, por lo que el prototipo puede usarse sin incorporar datos nuevos.

## 7. Actualización de los datos

En caso de que CAMMESA publique una edición nueva, el Operador del prototipo actualiza los datos con este procedimiento, en este orden:

1. **Descargar la base de CAMMESA.** En https://cammesaweb.cammesa.com/informe-sintesis-mensual/, descargar la base del mes (archivo `BASE_INFORME_MENSUAL_aaaa-mm`). Dentro del archivo comprimido descargado, el reporte se encuentra en `BASE_INFORME_MENSUAL_aaaa-mm > Bases_Demanda_INFORME_MENSUAL > Demanda - Req Máx.xlsx`.
2. **Cargar el archivo** en la pantalla 1, indicando la fecha en que se descargó. El prototipo valida el contenido del archivo y lo guarda con su propio nombre, por lo que no es necesario renombrarlo.
3. **Descargar temperatura** en la pantalla 1. Requiere conexión a internet.
4. **Actualizar serie de trabajo** en la pantalla 1. La actualización demora alrededor de un minuto y reconstruye la serie y la evaluación retrospectiva.

Después de actualizar los datos, se revisa el informe de calidad de la pantalla 1 y se ejecuta el pronóstico en la pantalla 2.

## 8. Estructura del repositorio

```
TFG/
├── iniciar_prototipo.bat     inicio con doble clic (Windows)
├── requirements.txt          dependencias
├── .streamlit/config.toml    configuración de la aplicación
├── app/                      aplicación Streamlit (inicio de sesión y pantallas)
├── src/                      módulos de carga, calidad, modelado, regulación, evaluación y usuarios
├── scripts/                  alta de usuarios
├── data/                     datos originales, procesados, parámetros y registro de ejecuciones
└── notebooks/                análisis paso a paso (01 a 17)
```

Las notebooks documentan el desarrollo y pueden abrirse con Visual Studio Code (extensión Jupyter), seleccionando el entorno `.venv` como intérprete.

## 9. Problemas frecuentes

- **El "Símbolo del sistema" muestra un error al iniciar.** El entorno virtual no existe, no se llama `.venv` o no tiene las dependencias instaladas. Repetir los pasos 3.2 y 3.3.
- **El inicio de sesión rechaza las credenciales.** Verificar el usuario y la contraseña. Si no hay usuarios registrados, ejecutar el script de la sección 4.
- **No se puede descargar la temperatura.** Verificar la conexión a internet. El resto del prototipo sigue funcionando con los últimos datos cargados.
