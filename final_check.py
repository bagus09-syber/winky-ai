import ast
import json
import subprocess
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

MAIN_PY = BACKEND / "main.py"
MAIN_JS = FRONTEND / "src" / "main.js"

API = "http://127.0.0.1:8001"
WEB = "http://localhost:5175"


def ok(label):
    print(f"[OK] {label}")


def fail(label, detail=""):
    print(f"[FAIL] {label}")
    if detail:
        print(f"      {detail}")


print("=" * 60)
print("WINKY AI — FINAL CHECK")
print("=" * 60)


# ---------------------------------------------------------
# 1. FILES
# ---------------------------------------------------------

if MAIN_PY.exists():
    ok("backend/main.py ditemukan")
else:
    fail("backend/main.py tidak ditemukan")

if MAIN_JS.exists():
    ok("frontend/src/main.js ditemukan")
else:
    fail("frontend/src/main.js tidak ditemukan")


# ---------------------------------------------------------
# 2. PYTHON SYNTAX
# ---------------------------------------------------------

if MAIN_PY.exists():
    try:
        source = MAIN_PY.read_text(encoding="utf-8")
        ast.parse(source, filename=str(MAIN_PY))
        ok("Python syntax valid")
    except Exception as e:
        fail("Python syntax error", str(e))


# ---------------------------------------------------------
# 3. NODE SYNTAX
# ---------------------------------------------------------

if MAIN_JS.exists():
    try:
        result = subprocess.run(
            ["node", "--check", str(MAIN_JS)],
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
        )

        if result.returncode == 0:
            ok("JavaScript syntax valid")
        else:
            fail(
                "JavaScript syntax error",
                result.stderr.strip() or result.stdout.strip(),
            )

    except FileNotFoundError:
        fail(
            "Node.js tidak ditemukan",
            "Pastikan Node.js sudah terpasang.",
        )
    except Exception as e:
        fail("Node check gagal", str(e))


# ---------------------------------------------------------
# 4. BACKEND HEALTH
# ---------------------------------------------------------

try:
    response = requests.get(
        f"{API}/api/health",
        timeout=5,
    )

    if response.ok:
        data = response.json()

        ok("Backend API dapat diakses")

        if data.get("ollama"):
            ok("Ollama online")
        else:
            fail(
                "Ollama offline",
                "Pastikan Ollama sedang berjalan.",
            )
    else:
        fail(
            "Backend health gagal",
            f"HTTP {response.status_code}",
        )

except Exception as e:
    fail(
        "Backend tidak dapat diakses",
        str(e),
    )


# ---------------------------------------------------------
# 5. FRONTEND
# ---------------------------------------------------------

try:
    response = requests.get(
        WEB,
        timeout=5,
    )

    if response.ok:
        ok("Frontend Vite dapat diakses")
    else:
        fail(
            "Frontend HTTP error",
            f"HTTP {response.status_code}",
        )

except Exception as e:
    fail(
        "Frontend tidak dapat diakses",
        str(e),
    )


# ---------------------------------------------------------
# 6. EXPECTED BACKEND FEATURES
# ---------------------------------------------------------

if MAIN_PY.exists():
    text = MAIN_PY.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    checks = {
        "Login": '/api/auth/login',
        "Register": '/api/auth/register',
        "Chat streaming": '/api/chat/stream',
        "Conversations": '/api/conversations',
        "Memory": '/api/memories',
        "Files": '/api/files',
        "Search": '/api/search',
        "Models": '/api/models',
        "Health": '/api/health',
        "Account plan": '/api/account/plan',
        "Premium/VIP": 'PLAN_FEATURES',
        "AI router": 'choose_model',
        "Calculator": 'safe_calculate',
        "Web tool": 'perform_web_search',
        "Offline detection": 'internet_available',
    }

    for name, needle in checks.items():

        if needle in text:
            ok(f"Feature code: {name}")
        else:
            fail(f"Feature code: {name}")


# ---------------------------------------------------------
# 7. EXPECTED FRONTEND FEATURES
# ---------------------------------------------------------

if MAIN_JS.exists():
    text = MAIN_JS.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    checks = {
        "Chat": 'sendMessage',
        "Voice STT": 'SpeechRecognition',
        "TTS": 'speechSynthesis',
        "Memory": '/api/memories',
        "Files": '/api/files',
        "Web": 'webSearchEnabled',
        "Router": 'showAIStatus',
        "Sources": 'showSources',
        "Plan": 'loadAccountPlan',
        "Robot": 'setRobotState',
    }

    for name, needle in checks.items():

        if needle in text:
            ok(f"Frontend: {name}")
        else:
            fail(f"Frontend: {name}")


print()
print("=" * 60)
print("FINAL CHECK SELESAI")
print("=" * 60)
print()
print("Interpretasi:")
print("- [OK] = komponen ditemukan/berjalan.")
print("- [FAIL] = perlu diperbaiki.")
print("- Tes fitur interaktif tetap perlu dilakukan di browser.")
