from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, Usuario
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Usuario ya existe'}), 400

    nuevo_usuario = Usuario(email=data['email'])
    nuevo_usuario.set_password(data['password'])
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({'message': 'Usuario registrado correctamente'}), 201


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

    usuario = Usuario.query.filter_by(email=data['email']).first()
    if usuario and usuario.check_password(data['password']):
        session.permanent = True  # respeta PERMANENT_SESSION_LIFETIME
        session['user_id'] = usuario.id
        return jsonify({'message': 'Login exitoso'})

    return jsonify({'error': 'Credenciales inválidas'}), 401


@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    return jsonify({'message': 'Logout exitoso'})
