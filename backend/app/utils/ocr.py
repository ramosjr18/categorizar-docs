import pdfplumber
import docx
import pandas as pd
import re
import json
import logging


def analizar_excel_contenido(df: pd.DataFrame) -> dict:
    """
    Analiza el contenido textual de un DataFrame para identificar ciertos patrones.
    """
    texto = df.to_string()
    texto_lower = texto.lower()

    return {
        "contiene_ips": bool(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", texto)),
        "contiene_hosts": "host" in texto_lower or "hostname" in texto_lower,
        "es_inventario": "inventario" in texto_lower or "patrimonial" in texto_lower
    }


def extraer_contenido(archivo, tipo: str) -> tuple[str, dict]:
    """
    Extrae el contenido textual y patrones de un archivo según su tipo.

    Args:
        archivo: stream o ruta del archivo.
        tipo (str): Tipo de archivo ('pdf', 'docx', 'xlsx', 'csv').

    Returns:
        Tuple: (contenido extraído, diccionario de patrones encontrados)

    Raises:
        RuntimeError: Si ocurre un error durante el procesamiento.
        ValueError: Si el tipo no es soportado o no se puede extraer contenido.
    """
    contenido = ""
    patrones = {}

    try:
        if tipo == "pdf":
            contenido = _procesar_pdf(archivo)

        elif tipo == "docx":
            contenido = _procesar_docx(archivo)

        elif tipo in {"xls", "xlsx"}:
            contenido, patrones = _procesar_excel(archivo)

        elif tipo == "csv":
            contenido, patrones = _procesar_csv(archivo)

        else:
            raise ValueError(f"Tipo de archivo '{tipo}' no soportado")

        return contenido, patrones

    except Exception as e:
        logging.exception(f"Error procesando archivo tipo {tipo}: {e}")
        raise RuntimeError(f"Error al procesar {tipo.upper()}: {str(e)}")


def _procesar_pdf(archivo) -> str:
    with pdfplumber.open(archivo) as pdf:
        if not pdf.pages:
            raise ValueError("El PDF no contiene páginas.")

        textos = []
        for i, pagina in enumerate(pdf.pages):
            try:
                texto = pagina.extract_text()
                if texto:
                    textos.append(texto)
                else:
                    logging.warning(f"Página {i + 1} del PDF no tiene texto extraíble.")
            except Exception as e:
                logging.warning(f"Error extrayendo texto de página {i + 1}: {e}")

        contenido = "\n".join(textos).strip()
        if not contenido:
            raise ValueError("No se pudo extraer texto del PDF.")
        return contenido


def _procesar_docx(archivo) -> str:
    doc = docx.Document(archivo)
    return "\n".join(p.text for p in doc.paragraphs)


def _procesar_excel(archivo) -> tuple[str, dict]:
    xls = pd.ExcelFile(archivo)
    hojas = {}
    patrones = {}

    for nombre_hoja in xls.sheet_names:
        df = xls.parse(nombre_hoja)
        hojas[nombre_hoja] = df.to_dict(orient='records')
        for k, v in analizar_excel_contenido(df).items():
            patrones[k] = patrones.get(k, False) or v

    contenido = json.dumps(hojas, ensure_ascii=False, default=str)
    return contenido, patrones


def _procesar_csv(archivo) -> tuple[str, dict]:
    df = pd.read_csv(archivo)
    contenido = df.to_json(orient='records', force_ascii=False, date_format='iso')
    patrones = analizar_excel_contenido(df)
    return contenido, patrones
