import os
import hashlib
from collections import defaultdict


def hash_file(file_stream):
    hasher = hashlib.sha256()
    while chunk := file_stream.read(8192):
        hasher.update(chunk)
    file_stream.seek(0)  # Reiniciar el stream para que pueda usarse después
    return hasher.hexdigest()


def comparar_archivos_en_directorio(directorio):
    nombres = defaultdict(list)
    hashes = defaultdict(list)

    for root, _, files in os.walk(directorio):
        for file in files:
            path = os.path.join(root, file)
            nombres[file].append(path)
            file_hash = hash_file(path)
            hashes[file_hash].append(path)

    duplicados_nombre = {k: v for k, v in nombres.items() if len(v) > 1}
    duplicados_contenido = {k: v for k, v in hashes.items() if len(v) > 1}

    return duplicados_nombre, duplicados_contenido
