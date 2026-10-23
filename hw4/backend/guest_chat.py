"""Short-lived chat memory for guests (not logged in).

Guests can chat, but their conversation is not saved to the database. It is kept in this
process's memory, keyed by a random ``cc_guest`` cookie, so the agent still has context
across turns and a page refresh. It disappears after GUEST_TTL of inactivity, at login or
logout, or when the server restarts.

Entries use the same keys as chat_messages rows (role, content, products_json,
page_context, created_at), so the agent's history code treats both the same way.
"""
import secrets
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone

GUEST_COOKIE = "cc_guest"
GUEST_TTL = 2 * 3600            # seconds of inactivity before a guest chat is forgotten
MAX_GUEST_SESSIONS = 500        # oldest guest chats are dropped beyond this
MAX_GUEST_MESSAGES = 40         # rows kept per guest (20 turns)
MAX_GUEST_TURNS = 30            # user messages a guest can send before being asked to log in


class GuestChats:
    def __init__(self) -> None:
        self._chats: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def new_token() -> str:
        return secrets.token_urlsafe(24)

    def _prune(self, now: float) -> None:
        while self._chats:
            token, chat = next(iter(self._chats.items()))
            if now - chat["seen"] > GUEST_TTL or len(self._chats) > MAX_GUEST_SESSIONS:
                del self._chats[token]
            else:
                break

    def history(self, token: str | None) -> list[dict]:
        if not token:
            return []
        with self._lock:
            now = time.time()
            self._prune(now)
            chat = self._chats.get(token)
            return list(chat["rows"]) if chat else []

    def turns_used(self, token: str | None) -> int:
        if not token:
            return 0
        with self._lock:
            chat = self._chats.get(token)
            return chat["turns"] if chat else 0

    def append_turn(self, token: str, user_row: dict, assistant_row: dict) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            now = time.time()
            chat = self._chats.pop(token, None) or {"rows": [], "turns": 0}
            chat["rows"].extend([{**user_row, "created_at": stamp}, {**assistant_row, "created_at": stamp}])
            chat["rows"] = chat["rows"][-MAX_GUEST_MESSAGES:]
            chat["turns"] += 1
            chat["seen"] = now
            self._chats[token] = chat  # most recently used goes last
            self._prune(now)

    def clear(self) -> None:
        with self._lock:
            self._chats.clear()


guest_chats = GuestChats()
