
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import requests
import sqlite3
import json
import re
import secrets
import hashlib
import ast
import operator as op
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
from urllib.parse import quote
import os


try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


# =========================================================
# APP
# =========================================================

app = FastAPI(title="Winky AI")


# =========================================================
# SECURITY / CORS
# =========================================================

DEFAULT_ORIGINS = [
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]

_extra_origins = [
    item.strip()
    for item in os.getenv("WINKY_ALLOWED_ORIGINS", "").split(",")
    if item.strip()
]

FRONTEND_ORIGINS = list(dict.fromkeys(
    DEFAULT_ORIGINS + _extra_origins
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"

    return response


# =========================================================
# CONFIG
# =========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

DEFAULT_MODEL = "qwen3:0.6b"

ALLOWED_MODELS = {
    "qwen3:0.6b",
    "qwen3:1.7b",
    "qwen3:4b",
    "winky-ai:latest",
}

DB_FILE = "winky.db"

MAX_FILE_SIZE = 2 * 1024 * 1024

MAX_MESSAGE_LENGTH = 12000
MAX_USERNAME_LENGTH = 50
MAX_MEMORY_KEY_LENGTH = 80
MAX_MEMORY_VALUE_LENGTH = 1000

RATE_LIMITS = {
    "login": (5, 60),
    "register": (5, 600),
    "chat": (30, 60),
    "upload": (10, 60),
    "search": (20, 60),
}

_rate_buckets = defaultdict(deque)


def client_ip(request):
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def check_rate_limit(key, subject):
    limit, window = RATE_LIMITS[key]
    now = datetime.now().timestamp()
    bucket = _rate_buckets[(key, subject)]

    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(429, "Terlalu banyak permintaan. Coba lagi sebentar.")

    bucket.append(now)

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".html",
    ".css",
    ".js",
    ".py",
    ".php",
    ".sql",
}

OLLAMA_OPTIONS = {
    "num_ctx": 1024,
    "num_predict": 180,
    "temperature": 0.4,
    "top_k": 20,
    "top_p": 0.8,
    "repeat_penalty": 1.1,
}


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Kamu adalah Winky AI.

Bahasa utama kamu Bahasa Indonesia.

Jawab langsung, natural, jelas, singkat, cepat, dan membantu.

Jangan menampilkan proses berpikir internal atau chain of thought.

Jika pengguna meminta kode, gunakan code block.

Gunakan memory dan knowledge pengguna jika relevan.

Jangan mengarang informasi pribadi.

Jika tidak tahu, katakan dengan jujur.

Gunakan sumber web jika tersedia.

Jika router memilih tool, gunakan hasil tool yang diberikan.
Jangan mengaku telah menjalankan sesuatu yang sebenarnya belum dijalankan.
"""


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table, column):
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(
        row["name"] == column
        for row in rows
    )


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            premium_expires_at TEXT,
            vip_expires_at TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            content TEXT NOT NULL,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    if not column_exists(conn, "conversations", "user_id"):
        conn.execute(
            "ALTER TABLE conversations ADD COLUMN user_id INTEGER"
        )

    if not column_exists(conn, "memories", "user_id"):
        conn.execute(
            "ALTER TABLE memories ADD COLUMN user_id INTEGER"
        )

    if not column_exists(conn, "users", "plan"):
        conn.execute(
            "ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'"
        )

    if not column_exists(conn, "users", "premium_expires_at"):
        conn.execute(
            "ALTER TABLE users ADD COLUMN premium_expires_at TEXT"
        )

    if not column_exists(conn, "users", "vip_expires_at"):
        conn.execute(
            "ALTER TABLE users ADD COLUMN vip_expires_at TEXT"
        )

    conn.commit()
    conn.close()


init_db()


# =========================================================
# REQUEST MODELS
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
    model: str | None = None
    file_id: int | None = None


class RenameConversationRequest(BaseModel):
    title: str


class MemoryRequest(BaseModel):
    key: str
    value: str


# =========================================================
# AUTH
# =========================================================

PASSWORD_ITERATIONS = 310_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password, stored_hash):
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)

            if algorithm != "pbkdf2_sha256":
                return False

            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )

            return secrets.compare_digest(
                actual,
                bytes.fromhex(digest_hex),
            )

        except Exception:
            return False

    legacy = hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()

    return secrets.compare_digest(
        legacy,
        stored_hash,
    )


def create_session(conn, user_id):
    token = secrets.token_urlsafe(32)

    conn.execute(
        """
        INSERT INTO sessions
        (token, user_id, created_at)
        VALUES (?, ?, ?)
        """,
        (
            token,
            user_id,
            datetime.now().isoformat()
        )
    )

    return token


def extract_token(auth):
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()

    return None


def require_user(conn, auth):
    token = extract_token(auth)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Silakan login terlebih dahulu."
        )

    user = conn.execute(
        """
        SELECT
            users.id,
            users.username,
            users.plan,
            users.premium_expires_at,
            users.vip_expires_at
        FROM users
        JOIN sessions
            ON sessions.user_id = users.id
        WHERE sessions.token = ?
        LIMIT 1
        """,
        (token,)
    ).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Silakan login terlebih dahulu."
        )

    return user



# =========================================================
# PLANS / PREMIUM / VIP
# =========================================================

PLAN_FEATURES = {
    "free": {
        "chat": True,
        "memory": True,
        "history": True,
        "file": True,
        "web": True,
        "voice": True,
        "robot_welcome": True,
        "advanced_voice": False,
        "deep_research": False,
        "advanced_rag": False,
        "offline_ai": True,
        "ai_tools": True,
        "premium_models": False,
        "vip_robot": False,
    },
    "premium": {
        "chat": True,
        "memory": True,
        "history": True,
        "file": True,
        "web": True,
        "voice": True,
        "robot_welcome": True,
        "advanced_voice": True,
        "deep_research": True,
        "advanced_rag": True,
        "offline_ai": True,
        "ai_tools": True,
        "premium_models": True,
        "vip_robot": False,
    },
    "vip": {
        "chat": True,
        "memory": True,
        "history": True,
        "file": True,
        "web": True,
        "voice": True,
        "robot_welcome": True,
        "advanced_voice": True,
        "deep_research": True,
        "advanced_rag": True,
        "offline_ai": True,
        "ai_tools": True,
        "premium_models": True,
        "vip_robot": True,
    },
}


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def effective_plan(user):
    raw = (user["plan"] if "plan" in user.keys() else "free") or "free"
    raw = raw.lower().strip()
    now = datetime.now()

    if raw == "vip":
        expires = _parse_iso(user["vip_expires_at"] if "vip_expires_at" in user.keys() else None)
        if expires is None or expires > now:
            return "vip"
        raw = "premium"

    if raw == "premium":
        expires = _parse_iso(user["premium_expires_at"] if "premium_expires_at" in user.keys() else None)
        if expires is not None and expires > now:
            return "premium"
        return "free"

    return "free"


def normalize_plan(plan):
    plan = (plan or "free").lower().strip()
    return plan if plan in PLAN_FEATURES else "free"


def get_plan_payload(user):
    plan = effective_plan(user)
    return {
        "plan": plan,
        "stored_plan": normalize_plan(user["plan"] if "plan" in user.keys() else "free"),
        "premium_expires_at": user["premium_expires_at"] if "premium_expires_at" in user.keys() else None,
        "vip_expires_at": user["vip_expires_at"] if "vip_expires_at" in user.keys() else None,
        "features": PLAN_FEATURES[plan],
    }


def require_feature(user, feature):
    plan = effective_plan(user)
    if not PLAN_FEATURES[plan].get(feature, False):
        raise HTTPException(
            status_code=403,
            detail=f"Fitur '{feature}' membutuhkan paket Premium/VIP."
        )
    return plan


@app.post("/api/auth/register")
def register(data: RegisterRequest, request: Request):
    check_rate_limit("register", client_ip(request))
    username = data.username.strip()
    password = data.password

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username minimal 3 karakter."
        )

    if len(username) > MAX_USERNAME_LENGTH:
        raise HTTPException(400, "Username terlalu panjang.")

    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password minimal 6 karakter."
        )

    conn = get_db()

    if conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone():
        conn.close()

        raise HTTPException(
            status_code=409,
            detail="Username sudah digunakan."
        )

    cur = conn.execute(
        """
        INSERT INTO users
        (username, password_hash, plan, created_at)
        VALUES (?, ?, 'free', ?)
        """,
        (
            username,
            hash_password(password),
            datetime.now().isoformat()
        )
    )

    user_id = cur.lastrowid
    token = create_session(
        conn,
        user_id
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "token": token,
        "user_id": user_id,
        "username": username
    }


@app.post("/api/auth/login")
def login(data: LoginRequest, request: Request):
    check_rate_limit("login", client_ip(request))
    conn = get_db()

    user = conn.execute(
        """
        SELECT id, username, password_hash
        FROM users
        WHERE username = ?
        LIMIT 1
        """,
        (data.username.strip(),)
    ).fetchone()

    if (
        not user
        or not verify_password(
            data.password,
            user["password_hash"],
        )
    ):
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Username atau password salah."
        )

    if not user["password_hash"].startswith("pbkdf2_sha256$"):
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(data.password), user["id"]),
        )

    token = create_session(
        conn,
        user["id"]
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "token": token,
        "user_id": user["id"],
        "username": user["username"]
    }


@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None)
):
    token = extract_token(authorization)

    if token:
        conn = get_db()

        conn.execute(
            """
            DELETE FROM sessions
            WHERE token = ?
            """,
            (token,)
        )

        conn.commit()
        conn.close()

    return {"success": True}


@app.get("/api/auth/me")
def me(
    authorization: str | None = Header(default=None)
):
    conn = get_db()

    user = require_user(
        conn,
        authorization
    )

    conn.close()

    payload = get_plan_payload(user)

    return {
        "id": user["id"],
        "username": user["username"],
        **payload
    }



@app.get("/api/account/plan")
def account_plan(
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(conn, authorization)
    payload = get_plan_payload(user)
    conn.close()
    return payload


# =========================================================
# CONVERSATIONS
# =========================================================

def create_conversation(conn, user_id):
    cur = conn.execute(
        """
        INSERT INTO conversations
        (title, created_at, user_id)
        VALUES (?, ?, ?)
        """,
        (
            "Chat Baru",
            datetime.now().isoformat(),
            user_id
        )
    )

    return cur.lastrowid


def check_conversation(conn, cid, uid):
    return conn.execute(
        """
        SELECT id, title
        FROM conversations
        WHERE id = ?
        AND user_id = ?
        LIMIT 1
        """,
        (cid, uid)
    ).fetchone()


def update_title(conn, cid, uid, message):
    row = check_conversation(
        conn,
        cid,
        uid
    )

    if not row:
        return

    if row["title"] != "Chat Baru":
        return

    title = (
        message
        .strip()
        .replace("\n", " ")
        [:50]
    )

    if title:
        conn.execute(
            """
            UPDATE conversations
            SET title = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                title,
                cid,
                uid
            )
        )


@app.post("/api/conversations")
def new_conversation(
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    cid = create_conversation(
        conn,
        user["id"]
    )

    conn.commit()
    conn.close()

    return {
        "conversation_id": cid,
        "title": "Chat Baru"
    }


@app.get("/api/conversations")
def list_conversations(
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    rows = conn.execute(
        """
        SELECT id, title, created_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    if not check_conversation(
        conn,
        conversation_id,
        user["id"]
    ):
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Percakapan tidak ditemukan."
        )

    rows = conn.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    data: RenameConversationRequest,
    authorization: str | None = Header(default=None)
):
    title = data.title.strip()[:100]

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Judul chat kosong."
        )

    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    if not check_conversation(
        conn,
        conversation_id,
        user["id"]
    ):
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Percakapan tidak ditemukan."
        )

    conn.execute(
        """
        UPDATE conversations
        SET title = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            title,
            conversation_id,
            user["id"]
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "title": title
    }


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    if not check_conversation(
        conn,
        conversation_id,
        user["id"]
    ):
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Percakapan tidak ditemukan."
        )

    conn.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    conn.execute(
        """
        DELETE FROM conversations
        WHERE id = ?
        AND user_id = ?
        """,
        (
            conversation_id,
            user["id"]
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


# =========================================================
# MEMORY
# =========================================================

def save_memory(
    conn,
    uid,
    key,
    value
):
    key = key.strip().lower()
    value = value.strip()

    if len(key) > MAX_MEMORY_KEY_LENGTH:
        key = key[:MAX_MEMORY_KEY_LENGTH]

    if len(value) > MAX_MEMORY_VALUE_LENGTH:
        value = value[:MAX_MEMORY_VALUE_LENGTH]

    if not key or not value:
        return

    row = conn.execute(
        """
        SELECT id
        FROM memories
        WHERE user_id = ?
        AND key = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (uid, key)
    ).fetchone()

    now = datetime.now().isoformat()

    if row:
        conn.execute(
            """
            UPDATE memories
            SET value = ?, created_at = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                value,
                now,
                row["id"],
                uid
            )
        )
    else:
        conn.execute(
            """
            INSERT INTO memories
            (user_id, key, value, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                uid,
                key,
                value,
                now
            )
        )


def auto_memory(
    conn,
    uid,
    text
):
    patterns = [
        (
            r"\bnama saya\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "nama"
        ),
        (
            r"\bnamaku\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "nama"
        ),
        (
            r"\bnama aku\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "nama"
        ),
        (
            r"\bsaya suka\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?]|$)",
            "suka"
        ),
        (
            r"\baku suka\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?]|$)",
            "suka"
        ),
        (
            r"\bsaya tidak suka\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?]|$)",
            "tidak_suka"
        ),
        (
            r"\bsaya tinggal di\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "tempat_tinggal"
        ),
        (
            r"\baku tinggal di\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "tempat_tinggal"
        ),
        (
            r"\bsaya sekolah di\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "sekolah"
        ),
        (
            r"\baku sekolah di\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "sekolah"
        ),
        (
            r"\b(?:umur saya|usia saya|umurku|usiaku)\s+(\d+)\s*tahun\b",
            "umur"
        ),
        (
            r"\b(?:saya|aku) umur\s+(\d+)\b",
            "umur"
        ),
        (
            r"\b(?:hobi saya|hobi aku|saya hobi|aku hobi)\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "hobi"
        ),
        (
            r"\b(?:saya sedang membuat|aku sedang membuat|saya membuat|aku membuat)\s+(.+?)(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
            "proyek"
        ),
    ]

    for pattern, key in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            if value:
                save_memory(
                    conn,
                    uid,
                    key,
                    value
                )

    vehicle = re.search(
        r"\b(?:saya punya|aku punya|saya memiliki|aku memiliki)\s+"
        r"(motor|mobil|kendaraan)\s+(.+?)"
        r"(?=\s+dan\s+(?:saya|aku)\b|[.!?,]|$)",
        text,
        re.IGNORECASE
    )

    if vehicle:
        save_memory(
            conn,
            uid,
            "kendaraan",
            f"{vehicle.group(1).strip()} {vehicle.group(2).strip()}"
        )


def memory_messages(conn, uid):
    rows = conn.execute(
        """
        SELECT key, value
        FROM memories
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (uid,)
    ).fetchall()

    if not rows:
        return []

    text = "\n".join(
        f"- {row['key']}: {row['value']}"
        for row in rows
    )

    return [
        {
            "role": "system",
            "content": (
                "Informasi memory pengguna:\n\n"
                + text
                + "\n\nGunakan hanya jika relevan."
            )
        }
    ]


def memory_answer(conn, uid, text):
    t = text.lower().strip()

    checks = [
        (
            [
                "siapa nama saya",
                "nama saya siapa",
                "ingat nama saya"
            ],
            "nama",
            lambda v: f"Nama kamu adalah {v}.",
            "Saya belum menyimpan nama kamu."
        ),
        (
            [
                "berapa umur saya",
                "umur saya berapa",
                "berapa usia saya",
                "usia saya berapa"
            ],
            "umur",
            lambda v: f"Umur kamu {v} tahun.",
            "Saya belum menyimpan umur kamu."
        ),
        (
            [
                "saya sekolah di mana",
                "di mana saya sekolah",
                "sekolah saya"
            ],
            "sekolah",
            lambda v: f"Kamu sekolah di {v}.",
            "Saya belum menyimpan sekolah kamu."
        ),
        (
            [
                "saya tinggal di mana",
                "di mana saya tinggal",
                "tempat tinggal saya"
            ],
            "tempat_tinggal",
            lambda v: f"Kamu tinggal di {v}.",
            "Saya belum menyimpan tempat tinggal kamu."
        ),
    ]

    for phrases, key, formatter, fallback in checks:
        if any(
            phrase in t
            for phrase in phrases
        ):
            row = conn.execute(
                """
                SELECT value
                FROM memories
                WHERE user_id = ?
                AND key = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (uid, key)
            ).fetchone()

            return (
                formatter(row["value"])
                if row
                else fallback
            )

    if any(
        phrase in t
        for phrase in [
            "apa yang saya ingat",
            "apa yang kamu ingat tentang saya",
            "memory saya",
            "memori saya"
        ]
    ):
        rows = conn.execute(
            """
            SELECT key, value
            FROM memories
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (uid,)
        ).fetchall()

        if not rows:
            return (
                "Belum ada informasi yang "
                "tersimpan tentang kamu."
            )

        return (
            "Ini yang saya ingat tentang kamu:\n\n"
            + "\n".join(
                f"- {row['key']}: {row['value']}"
                for row in rows
            )
        )

    return None


@app.get("/api/memories")
def list_memory(
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    rows = conn.execute(
        """
        SELECT id, key, value, created_at
        FROM memories
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/memories")
def create_memory(
    data: MemoryRequest,
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    save_memory(
        conn,
        user["id"],
        data.key,
        data.value
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


@app.delete("/api/memories/{memory_id}")
def delete_memory(
    memory_id: int,
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    cur = conn.execute(
        """
        DELETE FROM memories
        WHERE id = ?
        AND user_id = ?
        """,
        (
            memory_id,
            user["id"]
        )
    )

    if cur.rowcount == 0:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Memory tidak ditemukan."
        )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


# =========================================================
# FILES
# =========================================================

def file_context(conn, uid, fid):
    row = conn.execute(
        """
        SELECT id, filename, content
        FROM files
        WHERE id = ?
        AND user_id = ?
        LIMIT 1
        """,
        (
            fid,
            uid
        )
    ).fetchone()

    if not row:
        return None

    return (
        f"FILE: {row['filename']}\n\n"
        f"{row['content']}"
    )


@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    request: Request = None,
):
    rate_subject = extract_token(authorization) or (client_ip(request) if request else "unknown")
    check_rate_limit("upload", rate_subject)
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    filename = Path(file.filename or "file").name

    ext = (
        "."
        + filename.rsplit(".", 1)[1].lower()
        if "." in filename
        else ""
    )

    if ext not in ALLOWED_EXTENSIONS:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="Format file tidak didukung."
        )

    raw = await file.read()

    if len(raw) > MAX_FILE_SIZE:
        conn.close()

        raise HTTPException(
            status_code=413,
            detail="Ukuran file maksimal 2 MB."
        )

    content = raw.decode(
        "utf-8",
        errors="replace"
    )

    cur = conn.execute(
        """
        INSERT INTO files
        (user_id, filename, extension, content, size, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            filename,
            ext,
            content,
            len(raw),
            datetime.now().isoformat()
        )
    )

    file_id = cur.lastrowid

    conn.commit()
    conn.close()

    return {
        "success": True,
        "file_id": file_id,
        "filename": filename,
        "size": len(raw)
    }


@app.get("/api/files")
def list_files(
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    rows = conn.execute(
        """
        SELECT id, filename, extension, size, created_at
        FROM files
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.delete("/api/files/{file_id}")
def delete_file(
    file_id: int,
    authorization: str | None = Header(default=None)
):
    conn = get_db()
    user = require_user(
        conn,
        authorization
    )

    cur = conn.execute(
        """
        DELETE FROM files
        WHERE id = ?
        AND user_id = ?
        """,
        (
            file_id,
            user["id"]
        )
    )

    if cur.rowcount == 0:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="File tidak ditemukan."
        )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


# =========================================================
# LOCAL RAG / CHUNKING
# =========================================================

def chunk_text(text, chunk_size=1800, overlap=250):
    text = text or ""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(length, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(start + 1, end - overlap)

    return chunks


def knowledge_context(conn, uid, query):
    words = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9_]+", query)
        if len(word) >= 3
    }

    if not words:
        return None

    rows = conn.execute(
        """
        SELECT id, filename, content
        FROM files
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (uid,)
    ).fetchall()

    ranked = []

    for row in rows:
        filename = row["filename"]
        for chunk_index, chunk in enumerate(
            chunk_text(row["content"])
        ):
            chunk_lower = chunk.lower()
            score = (
                sum(1 for word in words if word in chunk_lower)
                + 2 * sum(
                    1
                    for word in words
                    if word in filename.lower()
                )
            )
            if score:
                ranked.append(
                    (
                        score,
                        filename,
                        chunk_index,
                        chunk,
                    )
                )

    ranked.sort(
        key=lambda item: (
            item[0],
            -item[2],
        ),
        reverse=True,
    )

    if not ranked:
        return None

    parts = []
    seen = set()

    for score, filename, chunk_index, chunk in ranked[:6]:
        key = (filename, chunk_index)
        if key in seen:
            continue
        seen.add(key)
        parts.append(
            f"FILE: {filename}\n"
            f"CHUNK: {chunk_index + 1}\n"
            f"RELEVANCE: {score}\n\n"
            f"{chunk}"
        )

    return "\n\n====================\n\n".join(parts)


# =========================================================
# WEB
# =========================================================

def needs_web_search(text):
    t = text.lower()

    keys = [
        "cari di web",
        "cari di internet",
        "search web",
        "web search",
        "berita terbaru",
        "berita hari ini",
        "berita terkini",
        "terbaru",
        "terkini",
        "hari ini",
        "sekarang",
        "harga terbaru",
        "update terbaru",
        "latest",
        "current",
        "news",
    ]

    if any(
        key in t
        for key in keys
    ):
        return True

    patterns = [
        r"\bberapa harga\b",
        r"\bberapa biaya\b",
        r"\bjadwal .* kapan\b",
        r"\bkapan .* rilis\b",
        r"\bversi terbaru\b",
    ]

    return any(
        re.search(
            pattern,
            t
        )
        for pattern in patterns
    )


def perform_web_search(query):
    if DDGS is None:
        return []

    try:
        with DDGS() as ddgs:
            data = ddgs.text(
                query,
                max_results=5
            )

            return [
                {
                    "title": item.get(
                        "title",
                        ""
                    ),
                    "url": item.get(
                        "href",
                        ""
                    ),
                    "snippet": item.get(
                        "body",
                        ""
                    ),
                }
                for item in data
            ]

    except Exception as error:
        print(
            "WEB SEARCH ERROR:",
            error
        )

        return []


@app.get("/api/search")
def search(q: str, request: Request):
    check_rate_limit("search", client_ip(request))
    q = q.strip()

    if not q:
        raise HTTPException(
            status_code=400,
            detail="Query kosong."
        )

    return {
        "query": q,
        "results": perform_web_search(q)
    }


# =========================================================
# HEALTH / MODELS
# =========================================================

def internet_available():
    try:
        requests.get(
            "https://www.google.com",
            timeout=3
        )
        return True
    except Exception:
        return False


def offline_mode():
    return not internet_available()


@app.get("/")
def home():
    return {
        "name": "Winky AI",
        "status": "online",
        "model": DEFAULT_MODEL
    }


@app.get("/api/health")
def health():
    ollama = False

    try:
        ollama = requests.get(
            OLLAMA_TAGS_URL,
            timeout=5
        ).ok
    except Exception:
        pass

    return {
        "backend": True,
        "ollama": ollama,
        "model": DEFAULT_MODEL
    }


@app.get("/api/models")
def models():
    try:
        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        names = [
            item.get("name")
            for item in data.get(
                "models",
                []
            )
            if item.get("name") in ALLOWED_MODELS
        ]

        return {
            "models": names
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# =========================================================
# AI ROUTER
# =========================================================

def choose_model(
    message,
    requested_model=None
):
    if requested_model in ALLOWED_MODELS:
        return requested_model

    text = message.lower()

    coding_keywords = [
        "buat kode",
        "buatkan kode",
        "coding",
        "program",
        "python",
        "javascript",
        "typescript",
        "php",
        "html",
        "css",
        "sql",
        "laravel",
        "fastapi",
        "api",
        "debug",
        "syntax",
        "perbaiki kode",
        "function",
        "class",
    ]

    strong_keywords = [
        "analisis",
        "analisa",
        "bandingkan",
        "jelaskan secara mendalam",
        "secara detail",
        "strategi",
        "arsitektur",
        "optimasi",
        "penelitian",
        "deep research",
        "buat rencana",
        "buat roadmap",
        "kelebihan dan kekurangan",
    ]

    if any(
        keyword in text
        for keyword in coding_keywords
    ):
        if "qwen3:4b" in ALLOWED_MODELS:
            return "qwen3:4b"

        if "qwen3:1.7b" in ALLOWED_MODELS:
            return "qwen3:1.7b"

    if any(
        keyword in text
        for keyword in strong_keywords
    ) or len(message) > 700:
        if "qwen3:1.7b" in ALLOWED_MODELS:
            return "qwen3:1.7b"

    return DEFAULT_MODEL


def detect_tools(message):
    text = message.lower().strip()
    tools = []

    if "deep research" in text or "riset mendalam" in text:
        tools.append("deep_research")
    elif needs_web_search(text):
        tools.append("web")

    if any(
        keyword in text
        for keyword in [
            "hitung", "berapa hasil", "kalkulator",
            "persentase", "persen", "jumlahkan",
            "kurangkan", "kalikan", "bagi"
        ]
    ):
        tools.append("calculator")

    if any(
        keyword in text
        for keyword in [
            "file saya", "dokumen saya", "file ini",
            "dokumen ini", "isi file", "analisis file",
            "cek file", "baca file", "dokumen"
        ]
    ):
        tools.append("file")

    if any(
        keyword in text
        for keyword in [
            "kode", "coding", "program", "python",
            "javascript", "php", "laravel"
        ]
    ):
        tools.append("coding")

    return list(dict.fromkeys(tools))


def get_tool_status(
    tools,
    online=True
):
    result = {}

    for tool in tools:
        if tool == "web":
            result["web"] = (
                "ready"
                if online
                else "offline"
            )

        elif tool == "deep_research":
            result[tool] = "ready" if online else "offline"
        elif tool in {
            "calculator",
            "file",
            "coding",
        }:
            result[tool] = "ready"

    return result


# =========================================================
# SAFE CALCULATOR
# =========================================================

_ALLOWED_BIN = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARY = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def safe_calculate(expression):
    if len(expression) > 100:
        raise ValueError(
            "Ekspresi terlalu panjang."
        )

    tree = ast.parse(
        expression,
        mode="eval"
    )

    def evaluate(node):
        if isinstance(
            node,
            ast.Expression
        ):
            return evaluate(node.body)

        if (
            isinstance(node, ast.Constant)
            and isinstance(
                node.value,
                (int, float)
            )
        ):
            return node.value

        if isinstance(
            node,
            ast.BinOp
        ):
            function = _ALLOWED_BIN.get(
                type(node.op)
            )

            if not function:
                raise ValueError(
                    "Operator tidak didukung."
                )

            left = evaluate(node.left)
            right = evaluate(node.right)

            if (
                isinstance(node.op, ast.Pow)
                and abs(right) > 100
            ):
                raise ValueError(
                    "Pangkat terlalu besar."
                )

            return function(
                left,
                right
            )

        if isinstance(
            node,
            ast.UnaryOp
        ):
            function = _ALLOWED_UNARY.get(
                type(node.op)
            )

            if not function:
                raise ValueError(
                    "Operator tidak didukung."
                )

            return function(
                evaluate(node.operand)
            )

        raise ValueError(
            "Ekspresi tidak didukung."
        )

    return evaluate(tree)


def extract_math(text):
    cleaned = re.sub(
        r"[^0-9+\-*/().%^ ]",
        " ",
        text.lower()
    )

    cleaned = cleaned.replace(
        "^",
        "**"
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    ).strip()

    if (
        not re.search(r"\d", cleaned)
        or not re.search(
            r"[+\-*/]",
            cleaned
        )
    ):
        return None

    return cleaned


# =========================================================
# DEEP RESEARCH
# =========================================================

def deep_research(query, max_queries=3, max_results_per_query=4):
    if DDGS is None:
        return []

    queries = [query.strip()]
    base = query.strip()

    for suffix in [" official", " latest", " analysis"]:
        if len(queries) >= max_queries:
            break
        queries.append(base + suffix)

    merged = []
    seen_urls = set()

    try:
        with DDGS() as ddgs:
            for q in queries:
                data = ddgs.text(
                    q,
                    max_results=max_results_per_query
                )
                for item in data:
                    url = item.get("href", "")
                    title = item.get("title", "")
                    snippet = item.get("body", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    merged.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "query": q,
                    })
    except Exception as error:
        print("DEEP RESEARCH ERROR:", error)

    return merged[:10]


# =========================================================
# CHAT STREAM
# =========================================================

@app.post("/api/chat/stream")
def chat_stream(
    data: ChatRequest,
    authorization: str | None = Header(default=None),
    request: Request = None,
):
    conn_for_rate = extract_token(authorization) or (client_ip(request) if request else "unknown")
    check_rate_limit("chat", conn_for_rate)
    message = data.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Pesan kosong."
        )

    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(400, "Pesan terlalu panjang.")

    conn = get_db()

    user = require_user(
        conn,
        authorization
    )

    uid = user["id"]
    plan = effective_plan(user)

    selected_model = choose_model(
        message,
        data.model
    )

    if selected_model in {"qwen3:4b", "winky-ai:latest"} and plan == "free":
        selected_model = "qwen3:1.7b" if "qwen3:1.7b" in ALLOWED_MODELS else DEFAULT_MODEL

    selected_tools = detect_tools(
        message
    )

    online = internet_available()

    tool_status = get_tool_status(
        selected_tools,
        online
    )

    if data.conversation_id is None:
        cid = create_conversation(
            conn,
            uid
        )
    else:
        cid = data.conversation_id

        if not check_conversation(
            conn,
            cid,
            uid
        ):
            conn.close()

            raise HTTPException(
                status_code=404,
                detail="Percakapan tidak ditemukan."
            )

    # Save user
    conn.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            cid,
            "user",
            message,
            datetime.now().isoformat()
        )
    )

    # Auto memory
    auto_memory(
        conn,
        uid,
        message
    )

    # Direct memory answer
    direct = memory_answer(
        conn,
        uid,
        message
    )

    if direct:
        conn.execute(
            """
            INSERT INTO messages
            (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                cid,
                "assistant",
                direct,
                datetime.now().isoformat()
            )
        )

        update_title(
            conn,
            cid,
            uid,
            message
        )

        conn.commit()
        conn.close()

        def memory_stream():
            yield (
                json.dumps(
                    {
                        "content": direct
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

            yield (
                json.dumps(
                    {
                        "done": True,
                        "conversation_id": cid,
                        "model": selected_model,
                        "router": True,
                        "tools": [],
                        "online": online,
                        "tool_status": {}
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

        return StreamingResponse(
            memory_stream(),
            media_type="application/x-ndjson"
        )

    # History
    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        LIMIT 30
        """,
        (cid,)
    ).fetchall()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Memory
    messages.extend(
        memory_messages(
            conn,
            uid
        )
    )

    # Selected file
    if data.file_id is not None:
        ctx = file_context(
            conn,
            uid,
            data.file_id
        )

        if ctx:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Konteks file:\n\n"
                        + ctx[:50000]
                    )
                }
            )

    # Automatic knowledge
    kctx = knowledge_context(
        conn,
        uid,
        message
    )

    if kctx:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Knowledge file relevan:\n\n"
                    + kctx
                )
            }
        )

    # History
    messages.extend(
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    )

    conn.commit()
    conn.close()

    def generate():
        full = ""

        try:
            # Router event
            yield (
                json.dumps(
                    {
                        "router": True,
                        "model": selected_model,
                        "tools": selected_tools,
                        "tool_status": tool_status,
                        "online": online
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

            # Calculator
            if "calculator" in selected_tools:
                expression = extract_math(
                    message
                )

                if expression:
                    try:
                        result = safe_calculate(
                            expression
                        )

                        calculator_text = (
                            f"Hasil kalkulator: "
                            f"{expression} = {result}"
                        )

                        messages.append(
                            {
                                "role": "system",
                                "content": calculator_text
                            }
                        )

                        yield (
                            json.dumps(
                                {
                                    "tool": "calculator",
                                    "content":
                                        calculator_text
                                        + "\n\n"
                                },
                                ensure_ascii=False
                            )
                            + "\n"
                        )

                    except Exception as error:
                        print(
                            "CALCULATOR ERROR:",
                            error
                        )

            # Deep research
            if "deep_research" in selected_tools and online:
                yield (
                    json.dumps(
                        {
                            "tool": "deep_research",
                            "content": "🔬 Menjalankan riset mendalam...\n\n"
                        },
                        ensure_ascii=False
                    )
                    + "\n"
                )

                research_results = deep_research(message)

                if research_results:
                    research_context = "\n\n".join(
                        (
                            f"SOURCE {index}: {item['title']}\n"
                            f"URL: {item['url']}\n"
                            f"SUMMARY: {item['snippet']}"
                        )
                        for index, item in enumerate(research_results, 1)
                    )

                    messages.append({
                        "role": "system",
                        "content": (
                            "Gunakan hasil deep research berikut. "
                            "Gabungkan informasi yang konsisten dan sebutkan sumber yang relevan.\n\n"
                            + research_context
                        )
                    })

                    yield (
                        json.dumps(
                            {"sources": research_results},
                            ensure_ascii=False
                        )
                        + "\n"
                    )

            elif "deep_research" in selected_tools and not online:
                yield (
                    json.dumps(
                        {
                            "tool": "offline",
                            "content": "📴 Deep Research membutuhkan internet. Menggunakan knowledge lokal...\n\n"
                        },
                        ensure_ascii=False
                    )
                    + "\n"
                )

            # Web
            if (
                "web" in selected_tools
                and online
            ):
                yield (
                    json.dumps(
                        {
                            "tool": "web",
                            "content":
                                "🔎 Mencari informasi terbaru...\n\n"
                        },
                        ensure_ascii=False
                    )
                    + "\n"
                )

                results = perform_web_search(
                    message
                )

                if results:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "Hasil web:\n\n"
                                + "\n\n".join(
                                    (
                                        f"Judul: {item['title']}\n"
                                        f"URL: {item['url']}\n"
                                        f"Ringkasan: {item['snippet']}"
                                    )
                                    for item in results
                                )
                            )
                        }
                    )

                    yield (
                        json.dumps(
                            {
                                "sources": results
                            },
                            ensure_ascii=False
                        )
                        + "\n"
                    )

            elif (
                "web" in selected_tools
                and not online
            ):
                yield (
                    json.dumps(
                        {
                            "tool": "offline",
                            "content":
                                "📴 Internet offline. Menggunakan Winky lokal...\n\n"
                        },
                        ensure_ascii=False
                    )
                    + "\n"
                )

                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Internet offline. "
                            "Gunakan hanya sumber lokal."
                        )
                    }
                )

            # Tool instructions
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Router Winky:\n"
                        f"Model = {selected_model}\n"
                        f"Tools = "
                        f"{', '.join(selected_tools) or 'none'}\n"
                        f"Internet = "
                        f"{'online' if online else 'offline'}\n\n"
                        "Tool status:\n"
                        + json.dumps(
                            tool_status,
                            ensure_ascii=False
                        )
                    )
                }
            )

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Tool Winky:\n"
                        "- web: informasi terbaru dari internet.\n"
                        "- deep_research: riset multi-query dengan beberapa sumber web.\n"
                        "- calculator: perhitungan matematika aman.\n"
                        "- file: membaca file pengguna.\n"
                        "- coding: membuat, menjelaskan, dan memperbaiki kode.\n"
                        "Jangan mengaku mengeksekusi kode "
                        "jika kode memang tidak dijalankan."
                    )
                }
            )

            # Ollama
            print(
                "OLLAMA MODEL:",
                selected_model
            )

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": selected_model,
                    "messages": messages,
                    "think": False,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": OLLAMA_OPTIONS
                },
                stream=True,
                timeout=300
            )

            response.raise_for_status()

            # Stream
            for line in response.iter_lines():

                if not line:
                    continue

                try:
                    chunk = json.loads(
                        line.decode(
                            "utf-8"
                        )
                    )
                except Exception:
                    continue

                content = (
                    chunk
                    .get("message", {})
                    .get("content", "")
                )

                if content:
                    full += content

                    yield (
                        json.dumps(
                            {
                                "content": content
                            },
                            ensure_ascii=False
                        )
                        + "\n"
                    )

                if chunk.get("done"):
                    break

            if not full.strip():
                full = (
                    "Maaf, Winky tidak "
                    "mendapatkan jawaban dari model."
                )

            # Save assistant
            conn2 = get_db()

            conn2.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    cid,
                    "assistant",
                    full.strip(),
                    datetime.now().isoformat()
                )
            )

            update_title(
                conn2,
                cid,
                uid,
                message
            )

            conn2.commit()
            conn2.close()

            yield (
                json.dumps(
                    {
                        "done": True,
                        "conversation_id": cid,
                        "model": selected_model,
                        "plan": plan,
                        "tools": selected_tools,
                        "online": online
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

        except requests.RequestException as error:
            print(
                "OLLAMA ERROR:",
                error
            )

            yield (
                json.dumps(
                    {
                        "error":
                            "Ollama tidak dapat dihubungi. "
                            "Pastikan Ollama sedang berjalan."
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

        except Exception as error:
            print(
                "CHAT ERROR:",
                error
            )

            yield (
                json.dumps(
                    {
                        "error": str(error)
                    },
                    ensure_ascii=False
                )
                + "\n"
            )

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
