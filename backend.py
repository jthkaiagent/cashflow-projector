"""
Startup Cash Flow Projector — Backend Server
==============================================
Flask + SQLite + JWT Auth — handles user accounts and project persistence.

Quick start:
  1. pip install flask flask-cors bcrypt pyjwt
  2. python backend.py
  3. Frontend at cashflow.html connects automatically

Deploy free on Render: https://render.com
"""

import sqlite3, os, json, uuid, re
from datetime import datetime, timedelta, timezone
from flask import Flask, g, request, jsonify
from flask_cors import CORS
import bcrypt
import jwt

app = Flask(__name__)
CORS(app)

# ── Config (change these in production) ──
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'change-this-to-a-random-secret-in-production')
app.config['DB_PATH'] = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'cashflow.db'))
app.config['JWT_EXPIRY_HOURS'] = 72

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DB_PATH'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None: db.close()

def init_db():
    db = sqlite3.connect(app.config['DB_PATH'])
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            name        TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            name        TEXT NOT NULL DEFAULT 'My Project',
            data        TEXT NOT NULL DEFAULT '{}',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
    """)
    db.commit()
    db.close()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def make_token(user_id, email):
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(hours=app.config['JWT_EXPIRY_HOURS']),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def require_auth():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, 'Missing or invalid token'
    token = auth[7:]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token expired'
    except jwt.InvalidTokenError:
        return None, 'Invalid token'

def validate_email(email):
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) is not None

# ── Routes: Auth ──────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now(timezone.utc).isoformat()})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    name = (data.get('name') or '').strip()

    if not validate_email(email):
        return jsonify({'error': 'Valid email required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    user_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.execute('INSERT INTO users (id, email, password, name) VALUES (?,?,?,?)',
               (user_id, email, pw_hash, name))
    db.commit()

    token = make_token(user_id, email)
    return jsonify({'token': token, 'user': {'id': user_id, 'email': email, 'name': name}}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = make_token(user['id'], user['email'])
    return jsonify({
        'token': token,
        'user': {'id': user['id'], 'email': user['email'], 'name': user['name']}
    })

@app.route('/api/auth/me', methods=['GET'])
def me():
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    db = get_db()
    user = db.execute('SELECT id, email, name, created_at FROM users WHERE id=?',
                      (payload['user_id'],)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': dict(user)})

# ── Routes: Projects ──────────────────────────────────────────────────────────

@app.route('/api/projects', methods=['GET'])
def list_projects():
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    db = get_db()
    rows = db.execute(
        'SELECT id, name, updated_at FROM projects WHERE user_id=? ORDER BY updated_at DESC',
        (payload['user_id'],)
    ).fetchall()
    return jsonify({'projects': [dict(r) for r in rows]})

@app.route('/api/projects', methods=['POST'])
def create_project():
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    data = request.get_json(silent=True) or {}
    project_id = str(uuid.uuid4())
    name = (data.get('name') or 'My Project').strip()
    project_data = data.get('data') or {}

    db = get_db()
    db.execute(
        'INSERT INTO projects (id, user_id, name, data) VALUES (?,?,?,?)',
        (project_id, payload['user_id'], name, json.dumps(project_data))
    )
    db.commit()
    return jsonify({'id': project_id, 'name': name}), 201

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    db = get_db()
    row = db.execute(
        'SELECT * FROM projects WHERE id=? AND user_id=?',
        (project_id, payload['user_id'])
    ).fetchone()
    if not row:
        return jsonify({'error': 'Project not found'}), 404
    result = dict(row)
    result['data'] = json.loads(result['data'])
    return jsonify(result)

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    data = request.get_json(silent=True) or {}
    db = get_db()
    existing = db.execute(
        'SELECT id FROM projects WHERE id=? AND user_id=?',
        (project_id, payload['user_id'])
    ).fetchone()
    if not existing:
        return jsonify({'error': 'Project not found'}), 404

    updates = []
    params = []
    if 'name' in data:
        updates.append('name=?')
        params.append(data['name'])
    if 'data' in data:
        updates.append('data=?')
        params.append(json.dumps(data['data']))
    updates.append("updated_at=datetime('now')")

    if updates:
        params.append(project_id)
        db.execute(f'UPDATE projects SET {", ".join(updates)} WHERE id=?', params)
        db.commit()
    return jsonify({'status': 'saved'})

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    payload, err = require_auth()
    if err:
        return jsonify({'error': err}), 401
    db = get_db()
    db.execute('DELETE FROM projects WHERE id=? AND user_id=?',
               (project_id, payload['user_id']))
    db.commit()
    return jsonify({'status': 'deleted'})

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Cash Flow Backend — http://localhost:{port}")
    print(f"   API: http://localhost:{port}/api/health")
    print(f"   Auth: POST /api/auth/signup, POST /api/auth/login")
    print(f"   Projects: GET/POST /api/projects, GET/PUT/DELETE /api/projects/<id>")
    app.run(host='0.0.0.0', port=port, debug=True)
