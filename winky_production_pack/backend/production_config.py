import os

APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8001"))

DB_FILE = os.getenv("DB_FILE", "winky.db")

FRONTEND_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5175,http://127.0.0.1:5175",
    ).split(",")
    if x.strip()
]

REDIS_URL = os.getenv("REDIS_URL", "")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "")

RATE_LIMIT_LOGIN_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "5")
)

RATE_LIMIT_CHAT_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "30")
)

RATE_LIMIT_UPLOAD_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10")
)

MAX_CONCURRENT_CHATS = int(
    os.getenv("MAX_CONCURRENT_CHATS", "4")
)

REQUEST_TIMEOUT_SECONDS = int(
    os.getenv("REQUEST_TIMEOUT_SECONDS", "300")
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
