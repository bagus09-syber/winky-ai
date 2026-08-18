import asyncio

# Prototype guardrail for a small VPS.
chat_semaphore = asyncio.Semaphore(4)
