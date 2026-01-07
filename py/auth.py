import sqlite3
import os
import time
import hashlib
import secrets
from typing import Optional, List
from pathlib import Path

# Try to import bcrypt; if not available we'll fall back to PBKDF2
try:
    import bcrypt
    HAS_BCRYPT = True
except Exception:
    HAS_BCRYPT = False

DB_FILENAME = "users.db"


def get_db_path(user_data_dir: str):
    os.makedirs(user_data_dir, exist_ok=True)
    return os.path.join(user_data_dir, DB_FILENAME)


def init_user_db(user_data_dir: str):
    """Create users DB and sessions table if not exists."""
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        iterations INTEGER NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        consumed INTEGER NOT NULL DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 200000):
    """Return (hash, salt, iterations, algo) where algo is 'bcrypt' or 'pbkdf2'"""
    if HAS_BCRYPT:
        # bcrypt handles salt internally; return the encoded bcrypt hash
        bh = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return bh.decode('utf-8'), None, None, 'bcrypt'
    # fallback to PBKDF2
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd = password.encode('utf-8')
    dk = hashlib.pbkdf2_hmac('sha256', pwd, salt, iterations, dklen=32)
    return dk.hex(), salt.hex(), iterations, 'pbkdf2'


def create_user(user_data_dir: str, email: str, password: str, is_admin: bool = False) -> int:
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    password_hash, salt, iterations, algo = _hash_password(password)
    now = int(time.time())
    try:
        # store algorithm in password_hash column for bcrypt (string starting with $2)
        if algo == 'bcrypt':
            c.execute("INSERT INTO users (email, password_hash, salt, iterations, is_admin, created_at) VALUES (?,?,?,?,?,?)",
                      (email, password_hash, None, None, 1 if is_admin else 0, now))
        else:
            c.execute("INSERT INTO users (email, password_hash, salt, iterations, is_admin, created_at) VALUES (?,?,?,?,?,?)",
                      (email, password_hash, salt, iterations, 1 if is_admin else 0, now))
        conn.commit()
        user_id = c.lastrowid
    finally:
        conn.close()
    # create per-user data folders
    base = Path(user_data_dir) / "users" / str(user_id)
    for sub in ["chats", "history", "memory", "characters", "settings"]:
        os.makedirs(base / sub, exist_ok=True)
    return user_id


def get_user_by_email(user_data_dir: str, email: str):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash, salt, iterations, is_admin, created_at FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0],
        'email': row[1],
        'password_hash': row[2],
        'salt': row[3],
        'iterations': row[4],
        'is_admin': bool(row[5]),
        'created_at': row[6]
    }


def verify_password(user_record: dict, password: str) -> bool:
    expected = user_record.get('password_hash')
    # detect bcrypt hash
    try:
        if expected and expected.startswith('$2') and HAS_BCRYPT:
            return bcrypt.checkpw(password.encode('utf-8'), expected.encode('utf-8'))
    except Exception:
        pass
    # fallback to PBKDF2 verification
    salt_hex = user_record.get('salt')
    iterations = int(user_record.get('iterations') or 200000)
    if not salt_hex:
        return False
    salt = bytes.fromhex(salt_hex)
    dk, _, _ = _hash_password(password, salt=salt, iterations=iterations)
    return secrets.compare_digest(dk, expected)


def create_session(user_data_dir: str, user_id: int, max_age_days: int = 30) -> str:
    token = secrets.token_hex(32)
    expires_at = int(time.time()) + max_age_days * 24 * 3600
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)", (token, user_id, expires_at))
    conn.commit()
    conn.close()
    return token


def get_user_by_session(user_data_dir: str, token: str):
    if not token:
        return None
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    user_id, expires_at = row
    if int(time.time()) > expires_at:
        # expired
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    c.execute("SELECT id, email, is_admin, created_at FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    conn.close()
    if not u:
        return None
    return {'id': u[0], 'email': u[1], 'is_admin': bool(u[2]), 'created_at': u[3]}


def delete_session(user_data_dir: str, token: str):
    if not token:
        return
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def list_users(user_data_dir: str) -> List[dict]:
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, email, is_admin, created_at FROM users")
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'email': r[1], 'is_admin': bool(r[2]), 'created_at': r[3]} for r in rows]


def delete_user(user_data_dir: str, user_id: int):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_user_admin(user_data_dir: str, user_id: int, is_admin: bool):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
    conn.commit()
    conn.close()


def create_token(user_data_dir: str, user_id: int, token_type: str, ttl_seconds: int = 3600) -> str:
    tok = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ttl_seconds
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO tokens (token, user_id, type, expires_at, consumed) VALUES (?,?,?,?,0)", (tok, user_id, token_type, expires_at))
    conn.commit()
    conn.close()
    return tok


def get_token_record(user_data_dir: str, token: str):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT token, user_id, type, expires_at, consumed FROM tokens WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'token': row[0], 'user_id': row[1], 'type': row[2], 'expires_at': row[3], 'consumed': bool(row[4])}


def consume_token(user_data_dir: str, token: str):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE tokens SET consumed = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def set_password_by_userid(user_data_dir: str, user_id: int, new_password: str):
    password_hash, salt, iterations, algo = _hash_password(new_password)
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    if algo == 'bcrypt':
        c.execute("UPDATE users SET password_hash = ?, salt = NULL, iterations = NULL WHERE id = ?", (password_hash, user_id))
    else:
        c.execute("UPDATE users SET password_hash = ?, salt = ?, iterations = ? WHERE id = ?", (password_hash, salt, iterations, user_id))
    conn.commit()
    conn.close()


def set_user_verified(user_data_dir: str, user_id: int):
    db_path = get_db_path(user_data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()
    except Exception:
        # older schema may not have is_verified; ignore
        pass
    conn.close()


def ensure_root_admin(user_data_dir: str):
    """Ensure there is a root admin user. If environment variable ROOT_ADMIN_PASSWORD
    is set it will be used; otherwise a default password 'root' is created. This function
    will NOT overwrite an existing root user.
    """
    root_email = os.environ.get('ROOT_ADMIN_EMAIL', 'root')
    root_password = os.environ.get('ROOT_ADMIN_PASSWORD', 'root')
    init_user_db(user_data_dir)
    user = get_user_by_email(user_data_dir, root_email)
    if user:
        return user['id']
    return create_user(user_data_dir, root_email, root_password, is_admin=True)
