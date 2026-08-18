"""
Storage abstraction notes.

Current default:
- SQLite via existing main.py

Production migration targets:
- PostgreSQL for users/sessions/messages/files metadata
- Object storage for large uploads
- Redis for rate limits/cache/session acceleration
- Vector DB for scalable RAG

Do not switch automatically in prototype mode.
"""


STORAGE_MODES = {
    "sqlite": "Current prototype/default",
    "postgresql": "Production database target",
    "redis": "Cache/rate-limit/session support",
    "vector": "Scalable vector retrieval target",
}
