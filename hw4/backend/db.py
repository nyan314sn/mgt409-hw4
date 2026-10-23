"""SQLite access. The backend is the only code that opens the database."""
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from settings import DATA_DIR

DEFAULT_DB = DATA_DIR / "campus_customs.db"

# Tables the auth flow adds next to the seed tables (catalogue, inventory, users, chat_messages).
AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT PRIMARY KEY,
    failed_count INTEGER NOT NULL DEFAULT 0,
    first_failed_at REAL NOT NULL,
    locked_until REAL
);

-- Problem 9: failed-login counters by scope (email+ip, ip, email). Replaces login_attempts.
CREATE TABLE IF NOT EXISTS login_locks (
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    failed_count INTEGER NOT NULL DEFAULT 0,
    first_failed_at REAL NOT NULL,
    locked_until REAL,
    PRIMARY KEY (scope, key)
);

-- Problem 9: one row per agent run (chat turn or history summary): tools, tokens, cost.
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    kind TEXT NOT NULL,
    user_id INTEGER,
    client_ip TEXT,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    duration_ms INTEGER NOT NULL,
    requests INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL,
    tool_calls_json TEXT,
    showcase_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user ON agent_runs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created ON agent_runs(created_at);

-- Problem 9: rolling summary of each shopper's older chat (messages up to through_message_id).
CREATE TABLE IF NOT EXISTS chat_summaries (
    user_id INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    through_message_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Problem 9: orders reserved for in-store pickup.
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'reserved',
    pickup_name TEXT NOT NULL,
    note TEXT,
    item_count INTEGER NOT NULL,
    subtotal REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, id);

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    size TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    PRIMARY KEY (order_id, product_id, size),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
);
"""


def db_path() -> Path:
    return Path(os.getenv("CC_DB_PATH", DEFAULT_DB))


# Connection class used for every connection; tests swap in a subclass that tracks closes.
CONNECTION_CLASS: type[sqlite3.Connection] = sqlite3.Connection


def connect(read_only: bool = False) -> sqlite3.Connection:
    """Open a connection. Callers must close it - prefer open_db() or get_db().

    Note: ``with sqlite3.connect(...) as con`` only commits/rolls back; it does NOT close.
    """
    if read_only:
        target, uri = f"{db_path().resolve().as_uri()}?mode=ro", True
    else:
        target, uri = str(db_path()), False
    # FastAPI may open a connection in a worker thread and use it from the async route;
    # each connection still serves only one request at a time.
    con = sqlite3.connect(target, uri=uri, timeout=10, check_same_thread=False, factory=CONNECTION_CLASS)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def open_db(read_only: bool = False) -> Iterator[sqlite3.Connection]:
    """Connection that is always closed: committed on success, rolled back on error."""
    con = connect(read_only)
    try:
        yield con
        if not read_only:
            con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_schema() -> None:
    with open_db() as con:
        con.executescript(AUTH_SCHEMA)
        # chat_messages (seed table): remember which page each message was sent from, and
        # index the per-user, in-order lookup that loading history does on every chat turn.
        columns = {r["name"] for r in con.execute("PRAGMA table_info(chat_messages)")}
        if "page_context" not in columns:
            con.execute("ALTER TABLE chat_messages ADD COLUMN page_context TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, id)")


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, closed when the request ends."""
    with open_db() as con:
        yield con
