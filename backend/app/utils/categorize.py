import re

def categorizar(nombre_archivo, contenido, patrones=None):
    nombre_archivo = nombre_archivo.lower()
    contenido = contenido.lower()

    categorias = {
        "Inventario": ["inventario", "existencias", "almacén", "stock"],
        "Reporte": ["reporte", "informe", "estadísticas", "análisis", "summary"],
        "Finanzas": ["factura", "venta", "ingreso", "egreso", "balance"],
        "Legal": ["contrato", "firma", "jurídico", "legal", "cláusula", "politicas"],
        "Sistemas y Servidores": ["ip", "host", "hostname", "vlan", "switch", "firewall", "subred", "red", "interfaz"],
        "Politicas y Controles": ["controles","control interno","iso","normativas","compliance","auditoría","riesgos","seguridad","políticas","procedimientos","lineamientos"]
    }

    puntuaciones = {categoria: 0 for categoria in categorias}

    for categoria, palabras in categorias.items():
        for palabra in palabras:
            if palabra in nombre_archivo:
                puntuaciones[categoria] += 1

    for categoria, palabras in categorias.items():
        for palabra in palabras:
            puntuaciones[categoria] += len(re.findall(r'\b' + re.escape(palabra) + r'\b', contenido))

    if patrones:
        if patrones.get("contiene_ips") or patrones.get("contiene_hosts") or patrones.get("es_inventario"):
            puntuaciones["Sistemas y Servidores"] += 3

    categoria_final = max(puntuaciones, key=puntuaciones.get)
    return categoria_final if puntuaciones[categoria_final] > 0 else "General"