from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, Usuario
from functools import wraps
from email_validator import validate_email, EmailNotValidError

auth_bp = Blueprint('auth', __name__)

# ---------------------------
# Decoradores
# ---------------------------

def login_required(f):
    """Protege rutas que requieren sesión activa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def json_required(*fields):
    """Valida que el request tenga JSON con campos requeridos."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON requerido'}), 400
            for field in fields:
                if field not in data:
                    return jsonify({'error': f'Campo "{field}" es requerido'}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ---------------------------
# Rutas de autenticación
# ---------------------------

@auth_bp.route('/api/register', methods=['POST'])
@json_required('email', 'password')
def register():
    """
    Registra el primer usuario como admin.
    Después de eso, bloquea el registro público.
    """
    data = request.get_json()

    # Validar email
    try:
        valid = validate_email(data['email'])
        email = valid.email
    except EmailNotValidError as e:
        return jsonify({'error': str(e)}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'Usuario ya existe'}), 400

    # Verificar si ya existe al menos un usuario en el sistema
    ya_hay_usuarios = Usuario.query.first() is not None
    if ya_hay_usuarios:
        return jsonify({'error': 'Registro deshabilitado. Solo el admin puede crear usuarios.'}), 403

    nuevo_usuario = Usuario(email=email, is_admin=True)  # El primer usuario es admin
    nuevo_usuario.set_password(data['password'])

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error al registrar usuario'}), 500

    return jsonify({'message': 'Administrador creado correctamente'}), 201


@auth_bp.route('/api/yo', methods=['GET'])
@login_required
def yo():
    user = Usuario.query.get(session.get('user_id'))
    return jsonify({
        'email': user.email,
        'is_admin': getattr(user, 'is_admin', False)
    }), 200


@auth_bp.route('/api/admin/crear_usuario', methods=['POST'])
@json_required('email', 'password')
@login_required
def crear_usuario():
    """
    Solo el admin puede crear nuevos usuarios.
    """
    admin_id = session.get('user_id')
    admin = Usuario.query.get(admin_id)

    if not admin or not admin.is_admin:
        return jsonify({'error': 'Solo el administrador puede crear usuarios'}), 403

    data = request.get_json()
    try:
        valid = validate_email(data['email'])
        email = valid.email
    except EmailNotValidError as e:
        return jsonify({'error': str(e)}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({'error': 'Este email ya está registrado'}), 400

    nuevo_usuario = Usuario(email=email)
    nuevo_usuario.set_password(data['password'])

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error al crear usuario'}), 500

    return jsonify({'message': 'Usuario creado correctamente'}), 201


@auth_bp.route('/api/login', methods=['POST'])
@json_required('email', 'password')
def login():
    """
    Inicia sesión con email y contraseña. Guarda la sesión del usuario.
    """
    data = request.get_json()

    usuario = Usuario.query.filter_by(email=data['email']).first()
    if usuario and usuario.check_password(data['password']):
        session.clear()
        session.permanent = True
        session['user_id'] = usuario.id
        return jsonify({'message': 'Login exitoso'}), 200

    return jsonify({'error': 'Credenciales inválidas'}), 401


@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """
    Cierra sesión del usuario autenticado.
    """
    session.clear()
    return jsonify({'message': 'Logout exitoso'}), 200
