"""Problem 12: append-only audit trail of agent-loop activity."""
import json

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import audit
from agent import get_agent

SEED = {"email": "test@campuscustoms.yale.edu", "password": "password"}


class TwoTools:
    """Call 1: check_stock + get_customer_profile. Call 2: final reply."""

    def __init__(self):
        self.fail = None

    def __call__(self, messages, info: AgentInfo) -> ModelResponse:
        if self.fail:
            raise self.fail
        if any(isinstance(p, ToolReturnPart) for p in messages[-1].parts):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
                "message": "We have 2 left in L.", "product_ids": ["saybrook-college-crewneck"], "showcase_title": "Saybrook"})])
        return ModelResponse(parts=[
            ToolCallPart("check_stock", {"product": "saybrook crewneck", "size": "L"}),
            ToolCallPart("get_customer_profile", {}),
        ])


@pytest.fixture()
def model(monkeypatch):
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    m = TwoTools()
    with get_agent().override(model=FunctionModel(m)):
        yield m


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- the file itself ----------

def test_append_creates_valid_json_and_never_rewrites(temp_audit_trail):
    audit.append([{"n": 1}])
    first = temp_audit_trail.read_bytes()
    audit.append([{"n": 2}, {"n": 3}])
    second = temp_audit_trail.read_bytes()
    assert read(temp_audit_trail) == [{"n": 1}, {"n": 2}, {"n": 3}]
    # Everything before the closing "]" is untouched - only appended after.
    assert second.startswith(first[: first.rfind(b"]")])


def test_existing_entries_survive_a_new_server_run(temp_audit_trail):
    temp_audit_trail.write_text('[\n{"from": "an earlier run"}\n]\n', encoding="utf-8")
    audit.append([{"from": "this run"}])
    assert read(temp_audit_trail) == [{"from": "an earlier run"}, {"from": "this run"}]


def test_empty_array_and_damaged_file(temp_audit_trail):
    temp_audit_trail.write_text("[]", encoding="utf-8")
    audit.append([{"n": 1}])
    assert read(temp_audit_trail) == [{"n": 1}]
    temp_audit_trail.write_text('[{"n": 1}, {"n": 2', encoding="utf-8")  # damaged
    audit.append([{"n": 3}])
    assert temp_audit_trail.read_text(encoding="utf-8") == '[{"n": 1}, {"n": 2'  # left alone, not wiped


def test_short_truncates():
    assert len(audit.short("x" * 500)) == audit.SHORT
    assert audit.short({"a": 1}) == '{"a": 1}'


# ---------- what the agent loop writes ----------

def test_chat_run_writes_tool_steps_and_stop_reason(client, model, temp_audit_trail):
    client.post("/api/auth/login", json=SEED)
    assert client.post("/api/chat", json={"message": "saybrook in L?"}).status_code == 200
    entries = read(temp_audit_trail)
    run_ids = {e["run_id"] for e in entries}
    assert len(run_ids) == 1

    stock, profile, final = entries
    assert list(stock)[:3] == ["time", "run_id", "kind"]
    assert (stock["event"], stock["tool"], stock["step"], stock["user"], stock["kind"]) == ("tool_call", "check_stock", 1, "user:1", "chat")
    assert json.loads(stock["args"]) == {"product": "saybrook crewneck", "size": "L"}
    assert stock["result"] == "Saybrook College Crewneck · L: 2 (low_stock) · sold out: XXL · total 62"
    assert len(stock["result"]) <= audit.SHORT

    assert profile["tool"] == "get_customer_profile"
    assert profile["result"] == "customer profile (redacted)"
    assert "test@campuscustoms" not in temp_audit_trail.read_text(encoding="utf-8")

    assert final["event"] == "final" and final["tool"] == "final_result" and final["step"] == 2
    assert final["stop_reason"].startswith("final_answer")
    assert final["result"] == "We have 2 left in L."
    assert json.loads(final["args"])["product_ids"] == ["saybrook-college-crewneck"]
    assert final["tokens"][0] > 0 and final["cost_usd"] > 0


def test_failed_run_writes_error_stop_reason(client, model, temp_audit_trail):
    model.fail = RuntimeError("provider down")
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 503
    (entry,) = read(temp_audit_trail)
    assert (entry["event"], entry["stop_reason"], entry["user"]) == ("error", "error: RuntimeError", "guest")


def test_request_limit_is_a_stop_reason(client, monkeypatch, temp_audit_trail):
    """A model that keeps calling tools hits the loop limit; the trail says so."""
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")

    def loop_forever(messages, info):
        return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])

    with get_agent().override(model=FunctionModel(loop_forever)):
        assert client.post("/api/chat", json={"message": "hoodies"}).status_code == 503
    entries = read(temp_audit_trail)
    assert entries[-1]["event"] == "error" and entries[-1]["stop_reason"] == "request_limit"


def test_trail_accumulates_across_requests_and_clients(client, model, temp_audit_trail):
    from main import app
    client.post("/api/chat", json={"message": "one"})
    with TestClient(app) as other:
        other.post("/api/chat", json={"message": "two"})
    entries = read(temp_audit_trail)
    assert len({e["run_id"] for e in entries}) == 2 and len(entries) == 6
