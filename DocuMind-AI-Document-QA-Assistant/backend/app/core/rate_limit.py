from collections import defaultdict, deque
from time import monotonic
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request, namespace: str, limit: int, window_seconds: int = 60) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{namespace}:{client}"
        now = monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded. Please try again shortly.")
        hits.append(now)


rate_limiter = InMemoryRateLimiter()
