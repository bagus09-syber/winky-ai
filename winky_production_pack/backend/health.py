from datetime import datetime


def readiness_payload(
    backend=True,
    ollama=False,
    database=True,
):
    return {
        "status": "ready" if backend and database else "degraded",
        "backend": backend,
        "ollama": ollama,
        "database": database,
        "time": datetime.now().isoformat(),
    }
