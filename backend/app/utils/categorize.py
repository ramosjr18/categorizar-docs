import re
from typing import Optional, Dict

def categorizar(nombre_archivo: str, contenido: str, patrones: Optional[Dict[str, bool]] = None) -> str:
    """
    Categoriza un documento basándose en su nombre, contenido textual y patrones detectados.

    Args:
        nombre_archivo (str): Nombre del archivo.
        contenido (str): Texto extraído del documento.
        patrones (dict, opcional): Diccionario con patrones detectados, como IPs o términos técnicos.

    Returns:
        str: Categoría detectada o "General" si no se encuentra una coincidencia clara.
    """
    nombre_archivo = nombre_archivo.lower()
    contenido = contenido.lower()

    categorias = {
        "Inventario": ["inventario", "existencias", "almacén", "stock"],
        "Reporte": ["reporte", "informe", "estadísticas", "análisis", "summary"],
        "Finanzas": ["factura", "venta", "ingreso", "egreso", "balance"],
        "Legal": ["contrato", "firma", "jurídico", "legal", "cláusula", "politicas"],
        "Sistemas y Servidores": ["ip", "host", "hostname", "vlan", "switch", "firewall", "subred", "red", "interfaz"],
        "Politicas y Controles": ["controles", "control interno", "iso", "normativas", "compliance", "auditoría", "riesgos", "seguridad", "políticas", "procedimientos", "lineamientos"]
    }

    puntuaciones = {categoria: 0 for categoria in categorias}

    # Evaluar nombre del archivo
    for categoria, palabras in categorias.items():
        puntuaciones[categoria] += sum(1 for palabra in palabras if palabra in nombre_archivo)

    # Evaluar contenido textual
    for categoria, palabras in categorias.items():
        for palabra in palabras:
            coincidencias = re.findall(r'\b' + re.escape(palabra) + r'\b', contenido)
            puntuaciones[categoria] += len(coincidencias)

    # Ajuste por patrones estructurados
    if patrones:
        if patrones.get("contiene_ips") or patrones.get("contiene_hosts"):
            puntuaciones["Sistemas y Servidores"] += 3
        if patrones.get("es_inventario"):
            puntuaciones["Inventario"] += 2

    # Determinar categoría con mayor puntuación
    categoria_final = max(puntuaciones, key=puntuaciones.get)
    return categoria_final if puntuaciones[categoria_final] > 0 else "General"
