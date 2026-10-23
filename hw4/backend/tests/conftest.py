"""Shared fixtures. Tests import backend modules the same way uvicorn does (flat, from backend/)."""
import shutil
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# A frozen copy of the original seed database, so tests don't depend on (or change) live data.
# It isn't in git (no databases are); on first run it's copied from the data pack
# (data/campus_customs.db), which is the original seed when freshly placed.
SEED_DB = Path(__file__).resolve().parent / "fixtures" / "seed.db"


def _ensure_seed() -> None:
    if SEED_DB.exists():
        return
    import sqlite3

    from db import DEFAULT_DB
    if not DEFAULT_DB.exists():
        pytest.exit(f"Data pack missing: put campus_customs.db in {DEFAULT_DB.parent} (see README).", returncode=2)
    SEED_DB.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"{DEFAULT_DB.resolve().as_uri()}?mode=ro", uri=True)
    dst = sqlite3.connect(SEED_DB)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


_ensure_seed()


@pytest.fixture(autouse=True)
def fresh_guest_chats(monkeypatch):
    """Guest chats live in process memory; start every test with none."""
    from guest_chat import guest_chats
    monkeypatch.setenv("PYDANTIC_AI_NO_BANNER", "1")
    guest_chats.clear()
    yield
    guest_chats.clear()


@pytest.fixture(autouse=True)
def fake_summarizer(monkeypatch):
    """Never call a real model for history summaries in tests."""
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    import memory
    calls: list[list] = []

    def summarize(messages, info):
        calls.append(messages)
        return ModelResponse(parts=[TextPart(f"- summary #{len(calls)}: shopper wants a Saybrook crewneck in M")])

    agent = Agent(FunctionModel(summarize), output_type=str, instructions=memory.SUMMARIZER_PROMPT)
    monkeypatch.setattr(memory, "get_summarizer", lambda: agent)
    return calls


@pytest.fixture(autouse=True)
def temp_audit_trail(tmp_path, monkeypatch):
    """Tests write their audit entries to a temp file, never to output/audit_trail.json."""
    path = tmp_path / "audit_trail.json"
    monkeypatch.setenv("AUDIT_TRAIL_PATH", str(path))
    return path


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    import limits
    limits.chat_windows.clear()
    yield
    limits.chat_windows.clear()


@pytest.fixture()
def db_file(tmp_path, monkeypatch):
    """A fresh copy of the original seed database per test; the real one is never touched."""
    path = tmp_path / "campus_customs.db"
    shutil.copy(SEED_DB, path)
    monkeypatch.setenv("CC_DB_PATH", str(path))
    return path


@pytest.fixture()
def client(db_file):
    from fastapi.testclient import TestClient

    from main import app
    with TestClient(app) as c:
        yield c
