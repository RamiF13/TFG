
import json
import hashlib
import hmac
import secrets
from pathlib import Path


ITERACIONES = 600_000
ROLES = ["OPERADOR", "RESPONSABLE"]
LARGO_MINIMO = 8


def generar_hash(contrasena, sal):
    """Genera el hash de la contraseña con la sal indicada, usando PBKDF2 con SHA-256"""
    clave = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), ITERACIONES)
    return clave.hex()


def cargar_usuarios(ruta):
    """Lee el archivo de usuarios, o devuelve un diccionario vacío si todavía no existe"""
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def registrar_usuario(ruta, usuario, contrasena, rol):
    """Registra un usuario nuevo con su rol, guardando la sal y el hash de la contraseña, nunca la contraseña"""
    usuario = usuario.strip().lower()
    usuarios = cargar_usuarios(ruta)
    errores = []
    if not usuario.strip():
        errores.append("El usuario no puede estar vacío")
    if usuario in usuarios:
        errores.append(f"El usuario {usuario} ya existe")
    if len(contrasena) < LARGO_MINIMO:
        errores.append(f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres")
    if rol not in ROLES:
        errores.append(f"El rol debe ser uno de {ROLES}")
    if errores:
        raise ValueError("\n".join(errores))
    sal = secrets.token_hex(16)
    usuarios[usuario] = {"rol": rol, "sal": sal, "hash": generar_hash(contrasena, sal)}
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(usuarios, archivo, indent=4, ensure_ascii=False)


def verificar_ingreso(ruta, usuario, contrasena):
    """Verifica el usuario y la contraseña, y devuelve el rol si son correctos o None si no lo son"""
    usuario = usuario.strip().lower()
    usuarios = cargar_usuarios(ruta)
    if usuario not in usuarios:
        return None
    datos = usuarios[usuario]
    if hmac.compare_digest(generar_hash(contrasena, datos["sal"]), datos["hash"]):
        return datos["rol"]
    return None