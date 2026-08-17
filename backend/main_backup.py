from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import sqlite3
from datetime import datetime

app = FastAPI(title="Winky AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3:1.7b"
DB_FILE = "winky.db"

SYSTEM_PROMPT = """
Kamu adalah Winky AI.

Nama kamu adalah Winky AI.
Bahasa utama kamu adalah Bahasa Indonesia.

Jawab langsung kepada pengguna.
Jangan menampilkan proses berpikir internal.
Jangan menampilkan "Thinking", "Let me think", analisis internal,
atau isi proses penalaran.

Kamu adalah asisten AI yang ramah, jelas, dan membantu.
Jika pengguna meminta kode, gunakan code block.
Jika tidak tahu, katakan dengan jujur.
"""

# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

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
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id)
            REFERENCES conversations(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# MODELS
# =========================

class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "name": "Winky AI",
        "status": "online"
    }


# =========================
# NEW CHAT
# =========================

@app.post("/api/conversations")
def create_conversation():

    conn = get_db()

    now = datetime.now().isoformat()

    cursor = conn.execute(
        """
        INSERT INTO conversations
        (title, created_at)
        VALUES (?, ?)
        """,
        ("Chat Baru", now)
    )

    conversation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "conversation_id": conversation_id,
        "title": "Chat Baru"
    }


# =========================
# CHAT
# =========================

@app.post("/api/chat")
def chat(data: ChatRequest):

    conn = get_db()

    # Jika belum ada conversation,
    # otomatis buat conversation baru.
    if data.conversation_id is None:

        now = datetime.now().isoformat()

        cursor = conn.execute(
            """
            INSERT INTO conversations
            (title, created_at)
            VALUES (?, ?)
            """,
            ("Chat Baru", now)
        )

        conversation_id = cursor.lastrowid

    else:

        conversation_id = data.conversation_id

    # Simpan pesan user
    conn.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            "user",
            data.message,
            datetime.now().isoformat()
        )
    )

    # Ambil riwayat percakapan
    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for row in rows:
        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    # Kirim ke Ollama
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "think": False,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "num_ctx": 2048,
                "num_predict": 300,
                "temperature": 0.7
            }
        },
        timeout=300
    )

    response.raise_for_status()

    result = response.json()

    reply = result["message"]["content"].strip()

    # Simpan jawaban AI
    conn.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            "assistant",
            reply,
            datetime.now().isoformat()
        )
    )

    # Kalau masih "Chat Baru",
    # gunakan pesan pertama sebagai judul.
    conversation = conn.execute(
        """
        SELECT title
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    ).fetchone()

    if conversation and conversation["title"] == "Chat Baru":

        title = data.message[:50]

        conn.execute(
            """
            UPDATE conversations
            SET title = ?
            WHERE id = ?
            """,
            (title, conversation_id)
        )

    conn.commit()
    conn.close()

    return {
        "conversation_id": conversation_id,
        "reply": reply
    }


# =========================
# RIWAYAT CHAT
# =========================

@app.get("/api/conversations")
def conversations():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, title, created_at
        FROM conversations
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# =========================
# AMBIL PESAN CHAT
# =========================

@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: int):

    conn = get_db()

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
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]
# =========================
# STREAMING CHAT
# =========================

@app.post("/api/chat/stream")
def chat_stream(data: ChatRequest):

    conn = get_db()

    # Buat conversation jika belum ada
    if data.conversation_id is None:

        now = datetime.now().isoformat()

        cursor = conn.execute(
            """
            INSERT INTO conversations
            (title, created_at)
            VALUES (?, ?)
            """,
            ("Chat Baru", now)
        )

        conversation_id = cursor.lastrowid

    else:
        conversation_id = data.conversation_id

    # Simpan pesan user
    conn.execute(
        """
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            "user",
            data.message,
            datetime.now().isoformat()
        )
    )

    # Ambil seluruh memory percakapan
    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for row in rows:
        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    conn.commit()
    conn.close()

    def generate():

        full_reply = ""

        try:

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
                    "think": False,
                    "stream": True,
                    "keep_alive": "5m",
                    "options": {
                        "num_ctx": 2048,
                        "num_predict": 300,
                        "temperature": 0.7
                    }
                },
                stream=True,
                timeout=300
            )

            response.raise_for_status()

            for line in response.iter_lines():

                if not line:
                    continue

                chunk = line.decode("utf-8")

                try:
                    data_chunk = __import__("json").loads(chunk)
                except Exception:
                    continue

                message = data_chunk.get("message", {})

                # Hanya ambil content.
                # Thinking sengaja tidak dikirim ke browser.
                content = message.get("content", "")

                if content:

                    full_reply += content

                    yield __import__("json").dumps({
                        "content": content
                    }) + "\n"

                if data_chunk.get("done"):
                    break

            # Simpan jawaban lengkap ke database
            conn2 = get_db()

            conn2.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    "assistant",
                    full_reply.strip(),
                    datetime.now().isoformat()
                )
            )

            # Judul otomatis
            conversation = conn2.execute(
                """
                SELECT title
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,)
            ).fetchone()

            if conversation and conversation["title"] == "Chat Baru":

                title = data.message[:50]

                conn2.execute(
                    """
                    UPDATE conversations
                    SET title = ?
                    WHERE id = ?
                    """,
                    (title, conversation_id)
                )

            conn2.commit()
            conn2.close()

            yield __import__("json").dumps({
                "done": True,
                "conversation_id": conversation_id
            }) + "\n"

        except Exception as error:

            yield __import__("json").dumps({
                "error": str(error)
            }) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )