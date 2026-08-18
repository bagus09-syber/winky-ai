#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/winky"
REPO="https://github.com/bagus09-syber/winky-ai.git"
PYTHON="python3"
VENV="$APP_DIR/backend/venv"

echo "== Winky VPS deployment =="

apt-get update
apt-get install -y git curl python3 python3-venv python3-pip nginx build-essential nodejs npm

if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

systemctl enable --now ollama

if [ ! -d "$APP_DIR/.git" ]; then
    rm -rf "$APP_DIR"
    git clone "$REPO" "$APP_DIR"
else
    git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR/backend"
$PYTHON -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install fastapi "uvicorn[standard]" requests pydantic python-multipart duckduckgo-search

cd "$APP_DIR/frontend"
npm install
npm run build

ollama pull qwen3:0.6b

install -m 0644 "$APP_DIR/deploy/winky.service" /etc/systemd/system/winky.service
systemctl daemon-reload
systemctl enable --now winky

install -m 0644 "$APP_DIR/deploy/nginx-winky.conf" /etc/nginx/sites-available/winky
ln -sfn /etc/nginx/sites-available/winky /etc/nginx/sites-enabled/winky
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo
echo "Winky deployment finished."
echo "Check:"
echo "  systemctl status winky --no-pager"
echo "  systemctl status ollama --no-pager"
echo "  curl http://127.0.0.1:8001/api/health"
