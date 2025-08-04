import pandas as pd

def es_graficable(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            return evaluar_dataframe(df)

        elif file_path.endswith('.xlsx'):
            with pd.ExcelFile(file_path) as xls:   # <-- Aquí el cambio
                for hoja in xls.sheet_names:
                    df = xls.parse(hoja)
                    if evaluar_dataframe(df):
                        return True
            return False

        else:
            return False

    except Exception as e:
        print("Error leyendo archivo:", e)
        return False



def evaluar_dataframe(df):
    # Quitar columnas vacías
    df = df.dropna(axis=1, how='all')

    # Si no hay suficientes columnas o filas, no es graficable
    if df.shape[1] < 2 or df.shape[0] < 2:
        return False

    tipos = df.dtypes.astype(str)

    tiene_eje_x = any("object" in t or "datetime" in t for t in tipos)
    tiene_valores_numericos = any("float" in t or "int" in t for t in tipos)

    return tiene_eje_x and tiene_valores_numericos
