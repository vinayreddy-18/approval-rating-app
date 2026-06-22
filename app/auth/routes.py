from flask import Blueprint, render_template, request, jsonify

from ..database import get_db_connection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def landing():
    return render_template('landing.html')


@auth_bp.route('/dashboard')
def dashboard():
    user_email = request.args.get('email', '').strip()
    return render_template('dashboard.html', user_email=user_email)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    uid = data.get('uid')
    email = data.get('email')

    if not uid:
        return jsonify({'error': 'Firebase uid is required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT id FROM users WHERE firebase_uid = %s', (uid,))
    user_row = cur.fetchone()

    if user_row is None:
        cur.execute(
            'INSERT INTO users (firebase_uid, email) VALUES (%s, %s) RETURNING id',
            (uid, email)
        )
        user_id = cur.fetchone()['id']
        conn.commit()
    else:
        user_id = user_row['id']
        cur.execute(
            'UPDATE users SET email = %s WHERE id = %s',
            (email, user_id)
        )
        conn.commit()

    conn.close()
    return jsonify({'success': True, 'user_id': user_id})