"""Rate limits and client addresses.

- client_ip(): the shopper's network address. Behind the Vite dev proxy every request comes
  from 127.0.0.1, so X-Forwarded-For is used - but only when the request really came from a
  trusted proxy (otherwise anyone could fake the header).
- SlidingWindow: in-memory "N events per T seconds" counters for chat. They reset when the
  server restarts; the persistent daily limit for accounts is counted from agent_runs.
"""
import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from settings import TRUSTED_PROXIES

# Chat limits
USER_BURST = (20, 10 * 60)        # a logged-in shopper: 20 messages per 10 minutes...
USER_DAILY = 200                  # ...and 200 per rolling 24 hours (from agent_runs)
IP_BURST = (40, 10 * 60)          # one network address, all accounts and guests: 40 per 10 min
GUEST_IP_HOURLY = (60, 60 * 60)   # guests from one address (stops cookie-clearing): 60 per hour


def client_ip(request: Request) -> str:
    """Each proxy *appends* the address it received the request from, so the browser's real
    address is the rightmost entry that isn't one of our own proxies. Entries further left
    were written by the browser itself and can't be trusted."""
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or peer not in TRUSTED_PROXIES:
        return peer
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if hop not in TRUSTED_PROXIES:
            return hop[:64]
    return hops[0][:64] if hops else peer


class SlidingWindow:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def retry_after(self, key: str, limit: int, window: float, *, record: bool) -> int:
        """Seconds until another event is allowed (0 = allowed). Records the event if allowed
        and record=True."""
        now = time.time()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= window:
                events.popleft()
            if len(events) >= limit:
                return max(1, math.ceil(window - (now - events[0])))
            if record:
                events.append(now)
            return 0

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


chat_windows = SlidingWindow()


def too_many(seconds: int, what: str) -> HTTPException:
    minutes = max(1, math.ceil(seconds / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return HTTPException(status_code=429, headers={"Retry-After": str(seconds)},
                         detail=f"{what} Please try again in {minutes} {unit}.")
