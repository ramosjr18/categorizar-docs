import os
import traceback
import pandas as pd
from datetime import date
from pathlib import Path

from flask import request, jsonify, send_from_directory, render_template, session, redirect, abort, current_app
from werkzeug.utils import secure_filename

from . import app, db
from .models import Documento, Usuario
from .utils.ocr import extraer_contenido
from .utils.categorize import categorizar
from .utils.file_comparator import hash_file
from .utils.es_graficable import es_graficable
from .auth_routes import login_required
from .utils_fs import ensure_dir

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

# Carpeta de uploads (asegurada)
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

@app.route("/upload", methods=["POST"])
@login_required
def subir_documento():
    try:
        archivo = request.files.get("archivo")
        if not archivo:
            return jsonify({"error": "No se recibió archivo"}), 400

        nombre = secure_filename(archivo.filename)
        tipo = nombre.split(".")[-1].lower()
        if tipo not in {"pdf", "docx", "xlsx", "csv"}:
            return jsonify({"error": f"Tipo de archivo '{tipo}' no soportado"}), 400

        hash_nuevo = hash_file(archivo.stream)
        grupo = nombre
        versiones = Documento.query.filter_by(grupo=grupo).order_by(Documento.version.desc()).all()

        for doc in versiones:
            if doc.hash_contenido == hash_nuevo:
                return jsonify({"error": f"Ya existe una versión con el mismo contenido (v{doc.version})"}), 400

        version = versiones[0].version + 1 if versiones else 1
        nombre_versionado = f"v{version}_{nombre}" if version > 1 else nombre
        ruta = str(UPLOAD_DIR / nombre_versionado)

        archivo.seek(0)
        archivo.save(ruta)

        try:
            with open(ruta, "rb") as f:
                texto_extraido, patrones = extraer_contenido(f, tipo)
        except Exception as ex:
            app.logger.error(f"Error extrayendo contenido de {nombre}: {ex}")
            return jsonify({"error": "Error extrayendo contenido"}), 400

        categoria = categorizar(nombre, texto_extraido or "", patrones or {})

        nuevo_doc = Documento(
            nombre=nombre,
            tipo=tipo,
            contenido=texto_extraido,
            categoria=categoria,
            fecha_subida=date.today().isoformat(),
            version=version,
            grupo=grupo,
            hash_contenido=hash_nuevo,
            # << clave para validar descargas >>
            usuario_id=session.get('user_id')
        )

        db.session.add(nuevo_doc)
        db.session.commit()

        return jsonify({
            "mensaje": f"Documento guardado como versión {version}",
            "categoria": categoria,
            "version": version
        })

    except Exception as e:
        traceback.print_exc()
        app.logger.error(f"Error interno en subir_documento: {e}")
        return jsonify({"error": "Error interno"}), 500


# --- DOCUMENTOS ---

@app.route("/documentos", methods=["GET"])
@login_required
def obtener_documentos():
    # Si prefieres listar solo los del usuario, descomenta:
    # documentos = Documento.query.filter_by(usuario_id=session.get('user_id')).all()
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
    if doc.usuario_id != session.get('user_id'):
        return jsonify({"error": "No autorizado"}), 403
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
    if doc.usuario_id != session.get('user_id'):
        return jsonify({"error": "No autorizado"}), 403
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"mensaje": "Documento eliminado"})


# (ELIMINADO) Endpoint vulnerable por nombre de archivo
# @app.route("/documentos/<nombre_archivo>")
# @login_required
# def servir_archivo(nombre_archivo):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], nombre_archivo, as_attachment=False)


@app.route('/documentos/<int:id>/descargar')
@login_required
def descargar_documento(id):
    doc = Documento.query.get_or_404(id)
    if doc.usuario_id != session.get('user_id'):
        return jsonify({"error": "No autorizado"}), 403
    return send_from_directory(UPLOAD_DIR, doc.nombre, as_attachment=True)


@app.route('/ver_docx')
@login_required
def ver_docx():
    nombre = request.args.get("nombre")
    return render_template("ver_docx.html", nombre=nombre)

# --- GRAFICAR DATOS ---

@app.route("/graficos")
@login_required
def graficar_datos():
    id_archivo = request.args.get("id")
    hojas = request.args.getlist("hojas")
    doc = Documento.query.get_or_404(id_archivo)
    if doc.usuario_id != session.get('user_id'):
        return jsonify({"error": "No autorizado"}), 403
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
    if doc.usuario_id != session.get('user_id'):
        return jsonify({"error": "No autorizado"}), 403
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

        if doc.usuario_id != session.get('user_id'):
            resultado[doc.nombre] = [{"error": "No autorizado"}]
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


@app.route("/validar_graficable", methods=["POST"])
@login_required
def validar_graficable():
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "No se recibió archivo"}), 400

    nombre_seguro = secure_filename(archivo.filename)
    if not (nombre_seguro.endswith(".xlsx") or nombre_seguro.endswith(".csv")):
        return jsonify({"graficable": False, "mensaje": "Formato no soportado"}), 400

    ruta_tmp = str(UPLOAD_DIR / f"tmp_{nombre_seguro}")

    try:
        archivo.save(ruta_tmp)
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
