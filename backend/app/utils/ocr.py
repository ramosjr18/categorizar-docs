import pdfplumber
import docx
import pandas as pd
import re
import json
import logging

def analizar_excel_contenido(df):
    texto = df.to_string()

    return {
        "contiene_ips": bool(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", texto)),
        "contiene_hosts": "host" in texto.lower() or "hostname" in texto.lower(),
        "es_inventario": "inventario" in texto.lower() or "patrimonial" in texto.lower()
    }

def extraer_contenido(archivo, tipo):
    contenido = ""
    patrones = {}

    if tipo == "pdf":
        try:
            with pdfplumber.open(archivo) as pdf:
                total_paginas = len(pdf.pages)
                if total_paginas == 0:
                    raise ValueError("El PDF no contiene páginas.")

                textos = []
                for i, pagina in enumerate(pdf.pages):
                    try:
                        texto_pagina = pagina.extract_text()
                        if texto_pagina:
                            textos.append(texto_pagina)
                        else:
                            logging.warning(f"Página {i+1} del PDF no tiene texto extraíble.")
                    except Exception as e:
                        logging.warning(f"Error extrayendo texto de página {i+1}: {str(e)}")

                contenido = "\n".join(textos)

                if not contenido.strip():
                    raise ValueError("No se pudo extraer texto del PDF.")
        except Exception as e:
            raise RuntimeError(f"Error al procesar PDF: {str(e)}")


    elif tipo == "docx":
        try:
            documento = docx.Document(archivo)
            contenido = "\n".join(p.text for p in documento.paragraphs)
        except Exception as e:
            raise RuntimeError(f"Error al procesar DOCX: {str(e)}")

    elif tipo in ["xls", "xlsx"]:
        try:
            xls = pd.ExcelFile(archivo)
            hojas = {}
            patrones = {}

            for nombre_hoja in xls.sheet_names:
                df = xls.parse(nombre_hoja)
                hojas[nombre_hoja] = df.to_dict(orient='records')

                patrones_hoja = analizar_excel_contenido(df)
                for clave, valor in patrones_hoja.items():
                    patrones[clave] = patrones.get(clave, False) or valor

            contenido = json.dumps(hojas, ensure_ascii=False, default=str)
        except Exception as e:
            raise RuntimeError(f"Error al procesar Excel: {str(e)}")

    elif tipo == "csv":
        try:
            df = pd.read_csv(archivo)
            contenido = df.to_json(orient='records', force_ascii=False, date_format='iso')
            patrones = analizar_excel_contenido(df)
        except Exception as e:
            raise RuntimeError(f"Error al procesar CSV: {str(e)}")

    else:
        raise ValueError(f"Tipo de archivo '{tipo}' no soportado")

    return contenido, patrones