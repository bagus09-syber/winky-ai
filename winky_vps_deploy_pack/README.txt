Winky VPS Deploy Pack

When the VPS is Active:
1. Clone/copy the deployment files into /opt/winky/deploy.
2. Ensure the GitHub repository is reachable.
3. Run: sudo bash /opt/winky/deploy/deploy.sh
4. Then verify the systemd services and API health.

The script installs FastAPI dependencies, Ollama, Qwen3 0.6B, builds the Vite frontend, and configures Nginx.
