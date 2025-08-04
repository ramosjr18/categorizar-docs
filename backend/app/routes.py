import os
import traceback
import pandas as pd
from datetime import date
from flask import request, jsonify, send_from_directory, render_template, session, redirect
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from . import app, db
from .models import Documento, Usuario
from .utils.ocr import extraer_contenido
from .utils.categorize import categorizar
from .utils.file_comparator import hash_file
from .utils.es_graficable import es_graficable


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
    # Permitir acceso a rutas públicas y a archivos estáticos (ejemplo: frontend/*)
    if any(request.path.startswith(ruta) for ruta in rutas_publicas):
        return  # acceso permitido sin login

    # Permitir acceso a archivos estáticos (css, js, img, etc.)
    if request.path.startswith('/static/') or request.path.startswith('/frontend/'):
        return

    # Si no está logueado, negar acceso
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado, inicie sesión'}), 401


# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Faltan datos"}), 400
    
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Usuario ya existe"}), 400

    nuevo_usuario = Usuario(email=data['email'])
    nuevo_usuario.password_hash = generate_password_hash(data['password'])
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({"message": "Usuario registrado correctamente"}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Faltan datos"}), 400

    user = Usuario.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return jsonify({"message": "Login exitoso"})
    return jsonify({"error": "Credenciales inválidas"}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logout exitoso"})


# --- PÁGINAS PRINCIPALES ---

@app.route('/')
def home():
    if 'user_id' in session:
        # Si está logueado, redirige al index
        return redirect('/index.html')
    else:
        # Si no está logueado, mostrar login
        return send_from_directory('frontend', 'login.html')


@app.route('/index.html')
def index_page():
    if 'user_id' not in session:
        return redirect('/')
    return send_from_directory('frontend', 'index.html')


@app.route('/login.html')
def login_page():
    if 'user_id' in session:
        return redirect('/index.html')
    return send_from_directory('frontend', 'login.html')


@app.route('/register.html')
def register_page():
    if 'user_id' in session:
        return redirect('/index.html')
    return send_from_directory('frontend', 'register.html')


# --- RUTAS EXISTENTES PROTEGIDAS ---

@app.route("/upload", methods=["POST"])
def subir_documento():
    try:
        archivo = request.files.get("archivo")
        if not archivo:
            return jsonify({"error": "No se recibió archivo"}), 400

        nombre = secure_filename(archivo.filename)
        tipo = nombre.split(".")[-1].lower()
        tipos_permitidos = {"pdf", "docx", "xlsx", "csv"}
        if tipo not in tipos_permitidos:
            return jsonify({"error": f"Tipo de archivo '{tipo}' no soportado"}), 400

        hash_nuevo = hash_file(archivo.stream)

        grupo = nombre
        versiones = Documento.query.filter_by(grupo=grupo).order_by(Documento.version.desc()).all()

        for doc in versiones:
            if doc.hash_contenido == hash_nuevo:
                return jsonify({"error": f"Ya existe una versión con el mismo contenido (v{doc.version})"}), 400

        version = versiones[0].version + 1 if versiones else 1
        nombre_versionado = f"v{version}_{nombre}" if version > 1 else nombre
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_versionado)

        archivo.seek(0)
        archivo.save(ruta)

        try:
            with open(ruta, "rb") as f:
                texto_extraido, patrones = extraer_contenido(f, tipo)
        except Exception as ex:
            app.logger.error(f"Error extrayendo contenido de {nombre}: {ex}")
            return jsonify({"error": f"Error extrayendo contenido: {str(ex)}"}), 400

        if not texto_extraido:
            texto_extraido = ""
            patrones = {}

        categoria = categorizar(nombre, texto_extraido, patrones)

        doc = Documento(
            nombre=nombre,
            tipo=tipo,
            contenido=texto_extraido,
            categoria=categoria,
            fecha_subida=date.today().isoformat(),
            version=version,
            grupo=grupo,
            hash_contenido=hash_nuevo
        )

        db.session.add(doc)
        db.session.commit()

        return jsonify({
            "mensaje": f"Documento guardado como versión {version}",
            "categoria": categoria,
            "version": version
        })

    except Exception as e:
        traceback.print_exc()
        app.logger.error(f"Error interno en subir_documento: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@app.route("/documentos", methods=["GET"])
def obtener_documentos():
    documentos = Documento.query.all()
    resultado = [
        {
            "id": doc.id,
            "nombre": doc.nombre,
            "tipo": doc.tipo,
            "categoria": doc.categoria,
            "fecha": doc.fecha_subida
        }
        for doc in documentos
    ]
    return jsonify(resultado)


@app.route("/documentos/<int:id>", methods=["GET"])
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
def eliminar_documento(id):
    doc = Documento.query.get_or_404(id)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"mensaje": "Documento eliminado"})


@app.route('/documentos/<nombre_archivo>')
def servir_archivo(nombre_archivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nombre_archivo, as_attachment=False)


@app.route('/ver_docx')
def ver_docx():
    nombre = request.args.get("nombre")
    return render_template("ver_docx.html", nombre=nombre)


@app.route("/graficos")
def graficar_datos():
    id_archivo = request.args.get("id")
    hojas = request.args.getlist("hojas")

    doc = Documento.query.get_or_404(id_archivo)
    ruta = os.path.join(app.config['UPLOAD_FOLDER'], doc.nombre)
    extension = doc.tipo.lower()

    datos_para_graficar = {}

    try:
        if extension == "xlsx":
            todas_las_hojas = pd.read_excel(ruta, sheet_name=None)
            for hoja in hojas:
                if hoja in todas_las_hojas:
                    df = todas_las_hojas[hoja]
                    datos_para_graficar[hoja] = df.to_dict(orient="records")
        elif extension == "csv":
            df = pd.read_csv(ruta)
            for columna in hojas:
                if columna in df.columns:
                    datos_para_graficar[columna] = df[[columna]].to_dict(orient="records")
        else:
            return jsonify({"error": "Tipo de archivo no compatible"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al procesar el archivo: {str(e)}"}), 500
    return render_template("graficos.html", datos=datos_para_graficar)


@app.route("/api/hojas/<int:id_archivo>")
def obtener_hojas_o_columnas(id_archivo):
    doc = Documento.query.get_or_404(id_archivo)
    nombre_archivo = doc.nombre
    extension = doc.tipo.lower()
    ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)

    try:
        if extension == "xlsx":
            hojas = pd.read_excel(ruta, sheet_name=None)
            return jsonify(list(hojas.keys()))
        elif extension == "csv":
            df = pd.read_csv(ruta)
            return jsonify(list(df.columns))
        else:
            return jsonify({"error": "Tipo de archivo no compatible para graficar"}), 400
    except Exception as e:
        return jsonify({"error": f"No se pudo procesar el archivo: {str(e)}"}), 500


@app.route("/api/graficos-multiples", methods=["POST"])
def graficos_multiples():
    datos = request.get_json()

    if not isinstance(datos, list):
        return jsonify({"error": "Se esperaba una lista de archivos con hojas"}), 400

    resultado = {}

    for entrada in datos:
        id_archivo = entrada.get("id")
        hojas = entrada.get("hojas", [])

        if not id_archivo or not hojas:
            continue

        doc = Documento.query.get(id_archivo)
        if not doc:
            continue

        nombre_archivo = doc.nombre
        extension = doc.tipo.lower()
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)

        try:
            if extension == "xlsx":
                hojas_dict = pd.read_excel(ruta, sheet_name=hojas)
            elif extension == "csv":
                df = pd.read_csv(ruta)
                hojas_dict = {col: df[[col]] for col in hojas if col in df.columns}
            else:
                continue

            for nombre_hoja, df in hojas_dict.items():
                if df.shape[1] < 1:
                    continue

                if df.shape[1] >= 2:
                    etiquetas = df.iloc[:, 0].astype(str).tolist()
                    valores = df.iloc[:, 1].fillna(0).astype(float).tolist()
                    registros = [
                        {df.columns[0]: etiqueta, df.columns[1]: valor}
                        for etiqueta, valor in zip(etiquetas, valores)
                    ]
                else:
                    etiquetas = df.index.astype(str).tolist()
                    valores = df.iloc[:, 0].fillna(0).astype(float).tolist()
                    registros = [
                        {"Índice": etiqueta, df.columns[0]: valor}
                        for etiqueta, valor in zip(etiquetas, valores)
                    ]

                clave = f"{nombre_archivo} - {nombre_hoja}"
                resultado[clave] = registros

        except Exception as e:
            resultado[nombre_archivo] = [{"error": f"No se pudo procesar: {str(e)}"}]

    return jsonify(resultado)


@app.route("/validar_graficable", methods=["POST"])
def validar_graficable():
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "No se recibió archivo"}), 400

    nombre = archivo.filename
    if not (nombre.endswith(".xlsx") or nombre.endswith(".csv")):
        return jsonify({"graficable": False, "mensaje": "Solo se aceptan archivos .xlsx o .csv"}), 400

    nombre_seguro = secure_filename(nombre)
    ruta_temporal = os.path.join(app.config['UPLOAD_FOLDER'], f"tmp_{nombre_seguro}")

    try:
        archivo.save(ruta_temporal)

        # Si es necesario, en es_graficable abre los archivos con 'with' para liberar manejadores

        es_valido = es_graficable(ruta_temporal)

    except Exception as e:
        app.logger.error(f"Error en validar_graficable: {e}")
        return jsonify({"error": "Error interno en la validación"}), 500

    finally:
        # Intentar cerrar cualquier recurso si es necesario antes de eliminar
        try:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
        except Exception as e:
            app.logger.warning(f"No se pudo eliminar archivo temporal: {e}")

    return jsonify({"graficable": es_valido})



@app.route('/documentos/<int:id>/descargar')
def descargar_documento(id):
    doc = Documento.query.get_or_404(id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], doc.nombre, as_attachment=True)
