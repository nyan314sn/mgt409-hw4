"""Problem 9: run log & cost, fair limits, longer memory, cart & checkout. No real AI calls."""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import limits
import memory
from agent import get_agent

SEED = {"email": "test@campuscustoms.yale.edu", "password": "password"}


class Scripted:
    """Call 1: check_stock. Call 2: final reply. Can be told to fail. Records instructions."""

    def __init__(self):
        self.fail = False
        self.instructions: list[str] = []
        self.history_lengths: list[int] = []

    def __call__(self, messages, info: AgentInfo) -> ModelResponse:
        if self.fail:
            raise RuntimeError("provider down")
        if not any(isinstance(p, ToolReturnPart) for p in messages[-1].parts):
            self.instructions.append(messages[-1].instructions)
            self.history_lengths.append(len(messages))
            return ModelResponse(parts=[ToolCallPart("check_stock", {"product": "saybrook crewneck", "size": "M"})])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "message": "We have it in M.", "product_ids": ["saybrook-college-crewneck"], "showcase_title": "Saybrook"})])


@pytest.fixture()
def model(monkeypatch):
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    s = Scripted()
    with get_agent().override(model=FunctionModel(s)):
        yield s


def q(db_file, sql, *args):
    con = sqlite3.connect(db_file)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def run(db_file, sql, *args):
    con = sqlite3.connect(db_file)
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def login(client, creds=SEED, ip=None):
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post("/api/auth/login", json=creds, headers=headers)


# ---------- 1. agent run log & cost ----------

def test_each_chat_is_logged_with_tools_tokens_and_cost(client, model, db_file):
    login(client)
    assert client.post("/api/chat", json={"message": "saybrook crewneck in M?"}).status_code == 200
    r = q(db_file, "SELECT * FROM agent_runs WHERE kind = 'chat' ORDER BY id DESC LIMIT 1")[0]
    assert (r["user_id"], r["status"], r["requests"], r["showcase_count"]) == (1, "ok", 2, 1)
    assert r["input_tokens"] > 0 and r["output_tokens"] > 0 and r["cost_usd"] > 0 and r["duration_ms"] >= 0
    calls = json.loads(r["tool_calls_json"])
    assert calls == [{"tool": "check_stock", "args": '{"product": "saybrook crewneck", "size": "M"}'}]


def test_failed_runs_are_logged_too(client, model, db_file):
    model.fail = True
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 503
    r = q(db_file, "SELECT * FROM agent_runs ORDER BY id DESC LIMIT 1")[0]
    assert (r["status"], r["error"], r["user_id"]) == ("error", "RuntimeError", None)


def test_usage_dashboard_is_admin_only(client, model, db_file):
    from main import app
    assert client.get("/api/admin/usage").status_code == 401
    login(client)
    client.post("/api/chat", json={"message": "saybrook crewneck in M?"})
    report = client.get("/api/admin/usage?days=7").json()
    assert report["totals"]["runs"] >= 1 and report["totals"]["costUsd"] > 0
    assert report["tools"][0] == {"tool": "check_stock", "calls": report["tools"][0]["calls"]}
    chat_run = next(r for r in report["recent"] if r["kind"] == "chat")
    assert chat_run["who"] == SEED["email"] and chat_run["toolCalls"][0]["tool"] == "check_stock"
    with TestClient(app) as other:
        other.post("/api/auth/register", json={"first_name": "Ann", "last_name": "B", "email": "ann@yale.edu", "password": "12345678ab"})
        assert other.get("/api/auth/me").json()["is_admin"] is False
        assert other.get("/api/admin/usage").status_code == 403


# ---------- 2. fair limits ----------

def test_logged_in_burst_limit(client, model, monkeypatch):
    monkeypatch.setattr(limits, "USER_BURST", (2, 600))
    login(client)
    assert [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(2)] == [200, 200]
    res = client.post("/api/chat", json={"message": "hi"})
    assert res.status_code == 429 and int(res.headers["retry-after"]) > 0
    assert "very quickly" in res.json()["detail"]


def test_logged_in_daily_limit_counts_logged_runs(client, model, db_file, monkeypatch):
    monkeypatch.setattr(limits, "USER_DAILY", 3)
    for _ in range(3):
        run(db_file, "INSERT INTO agent_runs (kind, user_id, model, status, duration_ms) VALUES ('chat', 1, 'm', 'ok', 1)")
    login(client)
    res = client.post("/api/chat", json={"message": "hi"})
    assert res.status_code == 429 and "today's chat limit" in res.json()["detail"]


def test_guest_limit_per_network_address_survives_new_cookies(client, model, monkeypatch):
    monkeypatch.setattr(limits, "GUEST_IP_HOURLY", (2, 3600))
    for _ in range(2):
        client.cookies.clear()  # a guest clearing cookies to get a fresh guest session
        assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
    client.cookies.clear()
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 429


def test_forwarded_address_only_trusted_from_proxy(monkeypatch):
    from starlette.requests import Request

    def req(peer, xff):
        return Request({"type": "http", "client": (peer, 1), "headers": [(b"x-forwarded-for", xff.encode())]})
    assert limits.client_ip(req("127.0.0.1", "9.9.9.9")) == "9.9.9.9"
    assert limits.client_ip(req("127.0.0.1", "6.6.6.6, 9.9.9.9")) == "9.9.9.9"     # browser-written 6.6.6.6 ignored
    assert limits.client_ip(req("127.0.0.1", "9.9.9.9, 127.0.0.1")) == "9.9.9.9"   # our own proxy hop skipped
    assert limits.client_ip(req("203.0.113.5", "9.9.9.9")) == "203.0.113.5"      # header from an untrusted peer ignored


@pytest.fixture()
def trust_testclient(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXIES", {"testclient"})


def test_lockout_cannot_be_used_against_someone_else(client, trust_testclient):
    wrong = {**SEED, "password": "nope"}
    codes = [login(client, wrong, ip="198.51.100.7").status_code for _ in range(5)]
    assert codes == [401, 401, 401, 401, 429]                     # the attacker's address is locked out...
    assert login(client, SEED, ip="198.51.100.7").status_code == 429
    assert login(client, SEED, ip="192.0.2.44").status_code == 200   # ...but the real owner still gets in


def test_one_address_spraying_many_emails_is_blocked(client, trust_testclient):
    for i in range(20):
        login(client, {"email": f"user{i}@yale.edu", "password": "x"}, ip="198.51.100.9")
    res = login(client, {"email": "someone.else@yale.edu", "password": "x"}, ip="198.51.100.9")
    assert res.status_code == 429


def test_many_addresses_against_one_email_lock_it(client, trust_testclient):
    wrong = {**SEED, "password": "nope"}
    for i in range(30):
        login(client, wrong, ip=f"10.0.{i // 4}.{i % 4 + 1}")  # spread over many addresses
    assert login(client, SEED, ip="192.0.2.44").status_code == 429  # email-wide backstop


# ---------- 3. longer memory ----------

def test_old_messages_are_summarized_not_dropped(client, model, db_file, fake_summarizer):
    login(client)
    run(db_file, "DELETE FROM chat_messages WHERE user_id = 1")
    run(db_file, "DELETE FROM chat_summaries WHERE user_id = 1")  # start from no summary, whatever the data pack holds
    runs_before = q(db_file, "SELECT COALESCE(MAX(id), 0) FROM agent_runs")[0][0]
    con = sqlite3.connect(db_file)
    con.executemany("INSERT INTO chat_messages (user_id, role, content) VALUES (1, ?, ?)",
                    [("user" if i % 2 == 0 else "assistant", f"message {i}") for i in range(30)])
    con.commit()
    con.close()

    client.post("/api/chat", json={"message": "turn A"})  # 32 unsummarized -> background summary
    summary = q(db_file, "SELECT * FROM chat_summaries WHERE user_id = 1")[0]
    assert summary["summary"].startswith("- summary #1")
    kept = q(db_file, "SELECT COUNT(*) FROM chat_messages WHERE user_id = 1 AND id > ?", summary["through_message_id"])[0][0]
    assert kept == memory.KEEP_RECENT
    assert "message 0" in json.dumps([str(m) for m in fake_summarizer[0]])  # oldest messages went to the summarizer
    assert q(db_file, "SELECT COUNT(*) FROM agent_runs WHERE kind = 'summary' AND status = 'ok' AND id > ?", runs_before)[0][0] == 1

    client.post("/api/chat", json={"message": "turn B"})
    assert "## Earlier in this conversation" in model.instructions[-1]
    assert "summary #1" in model.instructions[-1]
    assert model.history_lengths[-1] == memory.KEEP_RECENT + 1  # the 20 kept messages (incl. turn A) + the new one
    assert len(client.get("/api/chat/history").json()["messages"]) == 34  # nothing deleted from the database


def test_guests_get_no_summary(client, model):
    client.post("/api/chat", json={"message": "hi"})
    assert "## Earlier in this conversation" not in model.instructions[-1]


# ---------- 4. cart & checkout ----------

def stock(db_file, pid, size):
    return q(db_file, "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", pid, size)[0][0]


def test_cart_quote_uses_live_prices_and_flags_problems(client):
    res = client.post("/api/cart/quote", json={"items": [
        {"productId": "saybrook-college-crewneck", "size": "M", "quantity": 2},
        {"productId": "saybrook-college-crewneck", "size": "M", "quantity": 1},   # merged
        {"productId": "saybrook-college-crewneck", "size": "XXL", "quantity": 1}, # sold out
        {"productId": "saybrook-college-crewneck", "size": "L", "quantity": 5},   # only 2 left
        {"productId": "nope", "size": "M", "quantity": 1},
    ]})
    body = res.json()
    lines = {(l["productId"], l["size"]): l for l in body["lines"]}
    assert lines[("saybrook-college-crewneck", "M")]["quantity"] == 3
    assert lines[("saybrook-college-crewneck", "M")]["lineTotal"] == 174.0
    assert lines[("saybrook-college-crewneck", "XXL")]["problem"] == "sold_out"
    assert lines[("saybrook-college-crewneck", "L")]["problem"] == "not_enough_stock"
    assert lines[("saybrook-college-crewneck", "L")]["available"] == 2
    assert lines[("nope", "M")]["problem"] == "unknown_product"
    assert body["ok"] is False


def test_checkout_requires_login(client):
    res = client.post("/api/orders", json={"items": [{"productId": "saybrook-college-crewneck", "size": "M", "quantity": 1}],
                                           "pickupName": "Test"})
    assert res.status_code == 401


def test_checkout_reserves_stock_and_records_order(client, db_file):
    login(client)
    before = stock(db_file, "saybrook-college-crewneck", "M")
    res = client.post("/api/orders", json={"pickupName": "Test User", "note": "Will pick up Friday", "items": [
        {"productId": "saybrook-college-crewneck", "size": "M", "quantity": 2},
        {"productId": "yale-mom-hoodie", "size": "S", "quantity": 1}]})
    assert res.status_code == 201
    order = res.json()
    assert order["orderNumber"].startswith("CC-") and order["status"] == "reserved"
    assert order["itemCount"] == 3 and order["subtotal"] == 58 * 2 + 68
    assert stock(db_file, "saybrook-college-crewneck", "M") == before - 2
    assert client.get("/api/orders").json()[0]["orderNumber"] == order["orderNumber"]
    assert client.get(f"/api/orders/{order['orderNumber']}").json()["items"][0]["image"].startswith("/data/products/")


def test_checkout_refuses_when_stock_ran_out(client, db_file):
    login(client)
    before = stock(db_file, "saybrook-college-crewneck", "M")
    res = client.post("/api/orders", json={"pickupName": "T", "items": [
        {"productId": "saybrook-college-crewneck", "size": "M", "quantity": 1},
        {"productId": "saybrook-college-crewneck", "size": "L", "quantity": 3}]})  # only 2 in L
    assert res.status_code == 409
    assert res.json()["detail"]["quote"]["ok"] is False
    assert stock(db_file, "saybrook-college-crewneck", "M") == before  # nothing reserved
    assert q(db_file, "SELECT COUNT(*) FROM orders")[0][0] == 0


def test_price_comes_from_database_not_browser(client, db_file):
    login(client)
    res = client.post("/api/orders", json={"pickupName": "T", "items": [
        {"productId": "saybrook-college-crewneck", "size": "M", "quantity": 1, "unitPrice": 0.01}]})
    assert res.json()["subtotal"] == 58.0


def test_orders_are_private(client, db_file):
    from main import app
    login(client)
    number = client.post("/api/orders", json={"pickupName": "T", "items": [
        {"productId": "yale-mom-hoodie", "size": "S", "quantity": 1}]}).json()["orderNumber"]
    with TestClient(app) as other:
        other.post("/api/auth/register", json={"first_name": "Ann", "last_name": "B", "email": "ann2@yale.edu", "password": "12345678ab"})
        assert other.get(f"/api/orders/{number}").status_code == 404
        assert other.get("/api/orders").json() == []
