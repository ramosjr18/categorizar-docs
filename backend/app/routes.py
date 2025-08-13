import os
import traceback
import pandas as pd
from datetime import date
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher

from flask import request, jsonify, send_from_directory, render_template, session, redirect, abort, current_app, send_file
from werkzeug.utils import secure_filename

from . import app, db
from .models import Documento, Usuario
from .utils.ocr import extraer_contenido
from .utils.categorize import categorizar
from .utils.file_comparator import hash_file
from .utils.es_graficable import es_graficable
from .auth_routes import login_required
from .utils.utils_fs import ensure_dir
from .utils.utils_uploads import ensure_allowed_and_name, save_bytes

def ruta_fisica_de_documento(doc) -> Path:
    """
    Construye la ruta del archivo según el esquema nuevo.
    Si no existe (caso legacy), cae al esquema anterior.
    """
    base = Path(UPLOAD_DIR)

    # Esquema nuevo: <UPLOAD_DIR>/<grupo_dir>/v{version}/<nombre_original>
    grupo_dir = secure_filename(Path(doc.grupo).stem) or "doc"
    candidato = base / grupo_dir / f"v{doc.version}" / doc.nombre
    if candidato.exists():
        return candidato

    # Esquema legacy (por si tienes archivos con 'v{n}_' en el nombre directamente)
    legado = base / doc.nombre
    return legado


# --- PROTECCIÓN GLOBAL DE RUTAS ---
@app.before_request
def proteger_todas_rutas():
    rutas_publicas = [
        '/api/login',
        '/api/register',
        '/login.html',
        '/register.html',
        '/',
        '/favicon.ico',
    ]
    if any(request.path.startswith(r) for r in rutas_publicas):
        return
    if request.path.startswith('/static/') or request.path.startswith('/frontend/'):
        return
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401


UPLOAD_DIR = ensure_dir(Path(app.config.get('UPLOAD_FOLDER', 'uploads')))

# --- PÁGINAS PRINCIPALES ---
@app.route('/')
def home():
    return redirect('/index.html') if 'user_id' in session else send_from_directory('frontend', 'login.html')

@app.route('/index.html')
def index_page():
    return send_from_directory('frontend', 'index.html') if 'user_id' in session else redirect('/')

@app.route('/login.html')
def login_page():
    return redirect('/index.html') if 'user_id' in session else send_from_directory('frontend', 'login.html')

@app.route('/register.html')
def register_page():
    return redirect('/index.html') if 'user_id' in session else send_from_directory('frontend', 'register.html')

@app.route('/admin')
@login_required
def admin_panel():
    usuario = Usuario.query.get(session.get('user_id'))
    if not usuario or not usuario.is_admin:
        return "No autorizado", 403
    return render_template('admin.html')


# --- SUBIDA Y PROCESAMIENTO DE DOCUMENTOS ---
from flask import request, jsonify, session
from werkzeug.utils import secure_filename
from pathlib import Path
from io import BytesIO
from difflib import SequenceMatcher
from datetime import date

@app.route("/upload", methods=["POST"])
@login_required
def subir_documento():
    """
    Cambios:
    - Se guarda SIEMPRE con el nombre ORIGINAL del archivo.
    - La versión se maneja con subcarpetas: <UPLOAD_DIR>/<grupo_sanitizado>/v{version}/<nombre_original>
    - Si difiere ≥1% y el nombre coincide (mismo grupo), pide decisión (409) o aplica estrategia replace/new_version.
    - El campo Documento.nombre guarda el NOMBRE ORIGINAL (no la ruta).
    """
    try:
        archivos = request.files.getlist("archivo")
        if not archivos:
            return jsonify({"error": "No se recibieron archivos"}), 400

        estrategia = (request.form.get("estrategia") or request.args.get("estrategia") or "").strip().lower()
        resultados = []
        UMBRAL_IGUAL = 0.99  # ≥99% = igual

        def _sim_texto(a: str, b: str) -> float:
            a = (a or "").strip(); b = (b or "").strip()
            if not a and not b:
                return 1.0
            return SequenceMatcher(None, a, b).ratio()

        def _grupo_dir(nombre_visible: str) -> str:
            # Carpeta base para el grupo (usa el "nombre original" como hoy, sin extensión)
            stem = Path(nombre_visible).stem
            safe = secure_filename(stem) or "doc"
            return safe

        def _ruta_destino(grupo_visible: str, version: int, nombre_original: str) -> Path:
            # <UPLOAD_DIR>/<grupo>/v{version}/<nombre_original>
            base = Path(UPLOAD_DIR)
            carpeta = base / _grupo_dir(grupo_visible) / f"v{version}"
            carpeta.mkdir(parents=True, exist_ok=True)
            return carpeta / nombre_original

        for file_storage in archivos:
            # --- 1) Validación / preparación ---
            nombre_archivo_final, data = ensure_allowed_and_name(file_storage)
            hash_nuevo = hash_file(BytesIO(data))

            nombre_original = secure_filename(file_storage.filename)
            tipo_subida = Path(nombre_archivo_final).suffix.lower().lstrip(".")

            # Regla actual de agrupación por nombre visible (tú ya la usas)
            grupo = nombre_original

            # Extraer texto (antes de escribir a disco)
            try:
                texto_nuevo, patrones_nuevo = extraer_contenido(BytesIO(data), tipo_subida)
            except Exception as ex:
                app.logger.error(f"Error extrayendo contenido de {nombre_original}: {ex}")
                resultados.append({"nombre": nombre_original, "error": "Error extrayendo contenido"})
                continue

            # --- 2) Buscar versiones previas del mismo grupo ---
            versiones = (Documento.query
                         .filter_by(grupo=grupo)
                         .order_by(Documento.version.desc())
                         .all())

            # Duplicado exacto por hash
            duplicado = next((doc for doc in versiones if doc.hash_contenido == hash_nuevo), None)
            if duplicado:
                resultados.append({
                    "nombre": nombre_original,
                    "error": f"Ya existe una versión con el mismo contenido (v{duplicado.version})"
                })
                continue

            if versiones:
                actual = versiones[0]  # última versión
                sim = _sim_texto(texto_nuevo, actual.contenido or "")

                if sim >= UMBRAL_IGUAL:
                    resultados.append({
                        "nombre": nombre_original,
                        "error": f"Documento ya registrado (v{actual.version}), similitud {sim:.2%}"
                    })
                    continue

                # Cambia ≥1%: pedir decisión si no vino estrategia
                if estrategia not in ("replace", "new_version"):
                    resultados.append({
                        "nombre": nombre_original,
                        "requires_decision": True,
                        "opciones": ["replace", "new_version"],
                        "mensaje": (f"Cambio detectado de {100*(1-sim):.2f}% respecto a v{actual.version}. "
                                    "¿Reemplazar esa versión o crear una nueva?"),
                        "version_actual": actual.version
                    })
                    continue

                if estrategia == "replace":
                    # Guardar en el MISMO path de la versión actual, con el nombre ORIGINAL (actual.nombre)
                    destino = _ruta_destino(actual.grupo, actual.version, actual.nombre)
                    destino.write_bytes(data)

                    categoria = categorizar(nombre_original, texto_nuevo or "", patrones_nuevo or {})
                    # Mantener nombre original en DB:
                    actual.contenido = texto_nuevo
                    actual.categoria = categoria
                    actual.hash_contenido = hash_nuevo
                    actual.fecha_subida = date.today().isoformat()
                    actual.tipo = Path(actual.nombre).suffix.lower().lstrip(".") or tipo_subida
                    db.session.commit()

                    resultados.append({
                        "mensaje": f"Documento reemplazado (v{actual.version})",
                        "categoria": categoria,
                        "version": actual.version,
                        "nombre_visible": nombre_original,
                        "id": actual.id
                    })
                    continue

                # estrategia == "new_version" → crear nueva subcarpeta v{n+1}, conservar nombre original
                version = actual.version + 1
                destino = _ruta_destino(grupo, version, nombre_original)
                destino.write_bytes(data)

                categoria = categorizar(nombre_original, texto_nuevo or "", patrones_nuevo or {})

                nuevo_doc = Documento(
                    nombre=nombre_original,               # ← Guarda SOLO el nombre original
                    tipo=Path(nombre_original).suffix.lower().lstrip("."),
                    contenido=texto_nuevo,
                    categoria=categoria,
                    fecha_subida=date.today().isoformat(),
                    version=version,
                    grupo=grupo,
                    hash_contenido=hash_nuevo,
                    usuario_id=session.get('user_id')
                )
                db.session.add(nuevo_doc)
                db.session.commit()

                resultados.append({
                    "mensaje": f"Documento guardado como versión {version}",
                    "categoria": categoria,
                    "version": version,
                    "nombre_visible": nombre_original,
                    "id": nuevo_doc.id
                })
            else:
                # Primera versión (v1), conservar nombre original
                version = 1
                destino = _ruta_destino(grupo, version, nombre_original)
                destino.write_bytes(data)

                categoria = categorizar(nombre_original, texto_nuevo or "", patrones_nuevo or {})

                nuevo_doc = Documento(
                    nombre=nombre_original,               # ← Guarda SOLO el nombre original
                    tipo=Path(nombre_original).suffix.lower().lstrip("."),
                    contenido=texto_nuevo,
                    categoria=categoria,
                    fecha_subida=date.today().isoformat(),
                    version=version,
                    grupo=grupo,
                    hash_contenido=hash_nuevo,
                    usuario_id=session.get('user_id')
                )
                db.session.add(nuevo_doc)
                db.session.commit()

                resultados.append({
                    "mensaje": f"Documento guardado como versión {version}",
                    "categoria": categoria,
                    "version": version,
                    "nombre_visible": nombre_original,
                    "id": nuevo_doc.id
                })

        if any(r.get("requires_decision") for r in resultados):
            return jsonify(resultados), 409

        return jsonify(resultados)

    except Exception as e:
        import traceback
        traceback.print_exc()
        app.logger.error(f"Error interno en subir_documento: {e}")
        return jsonify({"error": "Error interno"}), 500


# --- DOCUMENTOS ---
@app.route("/documentos", methods=["GET"])
@login_required
def obtener_documentos():
    documentos = Documento.query.all()
    return jsonify([{
        "id": doc.id,
        "nombre": doc.nombre,
        "tipo": doc.tipo,
        "categoria": doc.categoria,
        "fecha": doc.fecha_subida
    } for doc in documentos])


@app.route("/documentos/<int:id>", methods=["GET"])
@login_required
def obtener_documento(id):
    doc = Documento.query.get_or_404(id)
    return jsonify({
        "id": doc.id,
        "nombre": doc.nombre,
        "tipo": doc.tipo,
        "categoria": doc.categoria,
        "contenido": doc.contenido,
        "fecha": doc.fecha_subida
    })


@app.route("/documentos/<int:id>", methods=["DELETE"])
@login_required
def eliminar_documento(id):
    doc = Documento.query.get_or_404(id)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"mensaje": "Documento eliminado"})


@app.route("/documentos/<int:doc_id>/descargar")
@login_required
def descargar(doc_id):
    doc = Documento.query.get_or_404(doc_id)
    path = ruta_fisica_de_documento(doc)
    if not path.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404
    return send_file(str(path), as_attachment=True, download_name=doc.nombre)


@app.route("/documentos/<nombre_archivo>")
@login_required
def servir_archivo(nombre_archivo):
    # Asegura que el nombre de archivo sea seguro
    nombre_archivo = secure_filename(nombre_archivo)
    return send_from_directory(UPLOAD_DIR, nombre_archivo, as_attachment=False)


@app.route("/ver_docx")
@login_required
def ver_docx():
    nombre = request.args.get("nombre")  # opcional si también pasas id
    doc = Documento.query.filter_by(nombre=nombre).order_by(Documento.version.desc()).first_or_404()
    path = ruta_fisica_de_documento(doc)
    # ... abrir/convertir docx desde 'path'


# --- GRAFICAR DATOS ---
@app.route("/graficos")
@login_required
def graficar_datos():
    id_archivo = request.args.get("id")
    hojas = request.args.getlist("hojas")
    doc = Documento.query.get_or_404(id_archivo)
    ruta = str(UPLOAD_DIR / doc.nombre)

    datos_para_graficar = {}

    try:
        if doc.tipo == "xlsx":
            hojas_dict = pd.read_excel(ruta, sheet_name=None)
            for hoja in hojas:
                if hoja in hojas_dict:
                    datos_para_graficar[hoja] = hojas_dict[hoja].to_dict(orient="records")
        elif doc.tipo == "csv":
            df = pd.read_csv(ruta)
            for col in hojas:
                if col in df.columns:
                    datos_para_graficar[col] = df[[col]].to_dict(orient="records")
        else:
            return jsonify({"error": "Tipo de archivo no compatible"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al procesar archivo: {str(e)}"}), 500

    return render_template("graficos.html", datos=datos_para_graficar)


@app.route("/api/hojas/<int:id_archivo>")
@login_required
def obtener_hojas_o_columnas(id_archivo):
    doc = Documento.query.get_or_404(id_archivo)
    ruta = str(UPLOAD_DIR / doc.nombre)

    try:
        if doc.tipo == "xlsx":
            return jsonify(list(pd.read_excel(ruta, sheet_name=None).keys()))
        elif doc.tipo == "csv":
            return jsonify(list(pd.read_csv(ruta).columns))
        else:
            return jsonify({"error": "No compatible para graficar"}), 400
    except Exception as e:
        return jsonify({"error": f"Error procesando archivo: {str(e)}"}), 500


@app.route("/api/graficos-multiples", methods=["POST"])
@login_required
def graficos_multiples():
    datos = request.get_json()
    if not isinstance(datos, list):
        return jsonify({"error": "Formato inválido"}), 400

    resultado = {}

    for entrada in datos:
        id_archivo = entrada.get("id")
        hojas = entrada.get("hojas", [])
        if not id_archivo or not hojas:
            continue

        doc = Documento.query.get(id_archivo)
        if not doc:
            continue

        ruta = str(UPLOAD_DIR / doc.nombre)

        try:
            if doc.tipo == "xlsx":
                hojas_dict = pd.read_excel(ruta, sheet_name=hojas)
            elif doc.tipo == "csv":
                df = pd.read_csv(ruta)
                hojas_dict = {col: df[[col]] for col in hojas if col in df.columns}
            else:
                continue

            for hoja, df in hojas_dict.items():
                if df.empty:
                    continue
                etiquetas = df.iloc[:, 0].astype(str).tolist()
                valores = df.iloc[:, 1].fillna(0).astype(float).tolist() if df.shape[1] > 1 else df.iloc[:, 0].tolist()
                clave = f"{doc.nombre} - {hoja}"
                resultado[clave] = [
                    {df.columns[0]: e, df.columns[1] if df.shape[1] > 1 else df.columns[0]: v}
                    for e, v in zip(etiquetas, valores)
                ]
        except Exception as e:
            resultado[doc.nombre] = [{"error": f"Error: {str(e)}"}]

    return jsonify(resultado)


@app.route("/validar_graficable", methods=["POST"])  # (No usada si no haces validación previa)
@login_required
def validar_graficable():
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "No se recibió archivo"}), 400

    nombre_tmp, data = ensure_allowed_and_name(archivo, allowed_exts={".xlsx", ".csv"})
    ruta_tmp = str(UPLOAD_DIR / f"tmp_{nombre_tmp}")

    try:
        Path(ruta_tmp).write_bytes(data)
        es_valido = es_graficable(ruta_tmp)
    except Exception as e:
        app.logger.error(f"Error validando graficable: {e}")
        return jsonify({"error": "Error interno"}), 500
    finally:
        try:
            os.remove(ruta_tmp)
        except Exception as e:
            app.logger.warning(f"No se pudo eliminar temporal: {e}")

    return jsonify({"graficable": es_valido})


@app.route('/api/check-session')
def check_session():
    if 'user_id' in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False}), 401
