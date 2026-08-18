Load test plan:

Do not run against production before the VPS is active and the service is healthy.

Suggested stages:
1 user -> 5 users -> 10 -> 25 -> 50

Measure:
- p50/p95 response start latency
- p95 total response time
- HTTP errors
- Ollama OOM/restarts
- CPU/RAM peak

Stop test if:
- RAM approaches exhaustion
- Ollama repeatedly restarts
- 5xx rate becomes significant
