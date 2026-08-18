Monitoring checklist:

Backend:
- /api/health
- process uptime
- restart count
- response latency
- 4xx/5xx rate

Ollama:
- process uptime
- inference latency
- RAM usage
- concurrent generations

Server:
- CPU
- RAM
- disk
- network

Prototype target:
- Keep sustained concurrent chats low enough to avoid OOM.
- Increase concurrency only after load testing.
