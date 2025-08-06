import os
import hashlib
from collections import defaultdict
from typing import Tuple, Dict, List


def hash_file(file_obj) -> str:
    """
    Calcula el hash SHA-256 de un archivo dado como objeto file-like.

    Args:
        file_obj: archivo abierto en modo binario, con método read().

    Returns:
        str: Hash hexadecimal del contenido del archivo.
    """

    file_obj.seek(0)
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(8192), b""):
        hasher.update(chunk)
    file_obj.seek(0) 
    return hasher.hexdigest()


def comparar_archivos_en_directorio(directorio: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Compara archivos en un directorio para detectar duplicados por nombre y por contenido.

    Args:
        directorio (str): Ruta del directorio a analizar.

    Returns:
        Tuple:
            - dict con archivos duplicados por nombre.
            - dict con archivos duplicados por hash de contenido.
    """
    archivos_por_nombre = defaultdict(list)
    archivos_por_hash = defaultdict(list)

    for root, _, files in os.walk(directorio):
        for file in files:
            ruta_completa = os.path.join(root, file)
            archivos_por_nombre[file].append(ruta_completa)

            try:
                file_hash = hash_file(ruta_completa)
                archivos_por_hash[file_hash].append(ruta_completa)
            except Exception as e:
                print(f"Error al procesar '{ruta_completa}': {e}")

    duplicados_nombre = {nombre: rutas for nombre, rutas in archivos_por_nombre.items() if len(rutas) > 1}
    duplicados_contenido = {hash_: rutas for hash_, rutas in archivos_por_hash.items() if len(rutas) > 1}

    return duplicados_nombre, duplicados_contenido
