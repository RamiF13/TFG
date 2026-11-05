
import sys
from getpass import getpass
from pathlib import Path

RUTA_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.append(str(RUTA_PROYECTO / "src"))

from usuarios import registrar_usuario, ROLES

RUTA_USUARIOS = RUTA_PROYECTO / "data" / "usuarios" / "USUARIOS.json"

usuario = input("Usuario: ").strip()
contrasena = getpass("Contraseña: ")
repetida = getpass("Repetir contraseña: ")
rol = input(f"Rol {ROLES}: ").strip().upper()

if contrasena != repetida:
    print("Las contraseñas no coinciden. El usuario no se registró.")
else:
    try:
        registrar_usuario(RUTA_USUARIOS, usuario, contrasena, rol)
        print(f"Usuario {usuario} registrado con el rol {rol}.")
    except ValueError as error:
        print(f"No se registró el usuario:\n{error}")