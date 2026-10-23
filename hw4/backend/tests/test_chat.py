"""Chat route, history handling, products API, and catalogue search.

The real model is replaced with a scripted FunctionModel, so these tests make no AI calls.
"""
import json
import sqlite3

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import catalogue
from agent import get_agent

SEED_LOGIN = {"email": "test@campuscustoms.yale.edu", "password": "password"}


class ScriptedModel:
    """Call 1: search_products(**search). Call 2: the final AgentReply. Records what it saw."""

    def __init__(self):
        self.search = {"query": "hoodie"}
        self.product_ids = ["basic-hoodie-big-yale"]
        self.title = "Hoodies"
        self.message = "Here are our hoodies! The **Basic Hoodie Big Yale** is a classic."
        self.fail = False
        self.seen: list[list] = []

    def __call__(self, messages, info: AgentInfo) -> ModelResponse:
        if self.fail:
            raise RuntimeError("provider down")
        self.seen.append(messages)
        if self.search is None or any(isinstance(p, ToolReturnPart) for p in messages[-1].parts):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
                "message": self.message, "product_ids": self.product_ids, "showcase_title": self.title,
            })])
        return ModelResponse(parts=[ToolCallPart("search_products", self.search)])


@pytest.fixture()
def scripted(monkeypatch):
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    model = ScriptedModel()
    with get_agent().override(model=FunctionModel(model)):
        yield model


@pytest.fixture()
def logged_in(client):
    assert client.post("/api/auth/login", json=SEED_LOGIN).status_code == 200
    return client


def rows(db_file, sql, *args):
    con = sqlite3.connect(db_file)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def user_texts(messages) -> list[str]:
    return [p.content for m in messages if isinstance(m, ModelRequest)
            for p in m.parts if isinstance(p, UserPromptPart)]


# ---------- chat ----------

def test_history_without_any_chat_is_empty(client):
    assert client.get("/api/chat/history").json() == {"saved": False, "messages": []}


def test_message_and_products_are_separate(logged_in, scripted, db_file):
    scripted.product_ids = ["basic-hoodie-big-yale", "not-a-real-product", "basic-hoodie-big-yale",
                            "champion-reverse-weave-hoodie-1"]
    before = len(rows(db_file, "SELECT id FROM chat_messages WHERE user_id = 1"))

    res = logged_in.post("/api/chat", json={"message": "What hoodies do you have?"})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"message", "showcase"}
    assert body["message"] == {"role": "assistant", "content": scripted.message}

    showcase = body["showcase"]
    assert showcase["title"] == "Hoodies"
    # Invented ids dropped, duplicates removed, order kept; full live Product objects.
    assert [p["id"] for p in showcase["products"]] == ["basic-hoodie-big-yale", "champion-reverse-weave-hoodie-1"]
    first = showcase["products"][0]
    assert first == logged_in.get("/api/products/basic-hoodie-big-yale").json()
    assert {"image", "name", "price", "description", "sizes", "garmentType"} <= first.keys()

    from db import open_db
    with open_db(read_only=True) as con:
        expected_total = len(catalogue.search(con, "hoodie", limit=None))
    assert showcase["totalMatches"] == expected_total > 2
    assert showcase["browseUrl"] == "/products?q=hoodie"

    saved = rows(db_file, "SELECT role, content, products_json FROM chat_messages WHERE user_id = 1 ORDER BY id")
    assert len(saved) == before + 2
    assert (saved[-2]["role"], saved[-2]["content"]) == ("user", "What hoodies do you have?")
    stored = json.loads(saved[-1]["products_json"])
    assert stored["title"] == "Hoodies" and stored["items"][0] == {"id": "basic-hoodie-big-yale", "name": "Basic Hoodie Big Yale"}
    assert "price" not in json.dumps(stored)  # ids only; prices are looked up live


def test_small_talk_has_no_showcase(logged_in, scripted, db_file):
    scripted.search, scripted.product_ids, scripted.title = None, [], None
    scripted.message = "Boola Boola! How can I help?"
    body = logged_in.post("/api/chat", json={"message": "hi!"}).json()
    assert body == {"message": {"role": "assistant", "content": "Boola Boola! How can I help?"}, "showcase": None}
    assert rows(db_file, "SELECT products_json FROM chat_messages ORDER BY id DESC LIMIT 1")[0][0] is None


def test_browse_url_carries_search_filters(logged_in, scripted):
    scripted.search = {"query": "", "category": "Hoodies", "max_price": 70, "size_in_stock": "XL"}
    from db import open_db
    with open_db(read_only=True) as con:
        matches = catalogue.search(con, "", "Hoodies", None, 70, "XL", limit=None)
    scripted.product_ids = [matches[0].id]
    showcase = logged_in.post("/api/chat", json={"message": "hoodies under 60 in XL"}).json()["showcase"]
    assert showcase["browseUrl"] == "/products?category=Hoodies&size=XL&max=70"
    assert showcase["totalMatches"] == len(matches)


def test_color_search_has_total_but_no_link(logged_in, scripted):
    scripted.search = {"query": "hoodie", "color": "red"}
    scripted.product_ids = []
    body = logged_in.post("/api/chat", json={"message": "red hoodies?"}).json()
    assert body["showcase"] is None  # nothing picked -> no showcase at all


def test_default_title_when_agent_omits_one(logged_in, scripted):
    scripted.title = None
    assert logged_in.post("/api/chat", json={"message": "hoodies"}).json()["showcase"]["title"] == "Picked for you"


def test_history_is_sent_to_the_model_on_the_next_turn(logged_in, scripted):
    logged_in.post("/api/chat", json={"message": "What hoodies do you have?"})
    logged_in.post("/api/chat", json={"message": "Is this one in pink?"})

    second_turn = scripted.seen[-2]  # first model call of turn 2
    texts = user_texts(second_turn)
    assert "What hoodies do you have?" in texts and texts[-1] == "Is this one in pink?"
    shown = [p.content for m in second_turn if isinstance(m, ModelResponse)
             for p in m.parts if isinstance(p, TextPart)]
    assert any('[Shown on the page as product cards under "Hoodies": Basic Hoodie Big Yale (id: basic-hoodie-big-yale)]' in t
               for t in shown)


def test_reloaded_showcase_uses_live_data(logged_in, scripted, db_file):
    logged_in.post("/api/chat", json={"message": "What hoodies do you have?"})
    con = sqlite3.connect(db_file)
    con.execute("UPDATE catalogue SET price = 70 WHERE product_id = 'basic-hoodie-big-yale'")
    con.commit()
    con.close()
    last = logged_in.get("/api/chat/history").json()["messages"][-1]
    assert last["role"] == "assistant" and last["showcase"]["products"][0]["price"] == 70.0


def test_history_window_is_capped(logged_in, scripted, db_file):
    con = sqlite3.connect(db_file)
    con.executemany("INSERT INTO chat_messages (user_id, role, content) VALUES (1, ?, ?)",
                    [("user" if i % 2 == 0 else "assistant", f"old {i}") for i in range(60)])
    con.commit()
    con.close()
    logged_in.post("/api/chat", json={"message": "latest"})
    first_call = scripted.seen[0]
    import memory
    assert len(first_call) == memory.MAX_UNSUMMARIZED + 1  # capped history + the new request


def test_product_page_reaches_the_agent(logged_in, scripted):
    logged_in.post("/api/chat", json={"message": "Is this warm?", "page": {"path": "/products/benjamin-franklin-1-4-zip"}})
    request = scripted.seen[0][-1]
    assert user_texts(scripted.seen[0])[-1] == (
        "Is this warm?\n\n[Sent from the product page for Benjamin Franklin 1/4 Zip (id: benjamin-franklin-1-4-zip). "
        "\"This\"/\"it\" means this product unless the shopper names a different one.]")
    assert "product page for **Benjamin Franklin 1/4 Zip** (id: benjamin-franklin-1-4-zip)" in request.instructions


def test_agent_failure_returns_503_and_saves_nothing(logged_in, scripted, db_file):
    scripted.fail = True
    before = rows(db_file, "SELECT COUNT(*) FROM chat_messages")[0][0]
    res = logged_in.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 503 and "unavailable" in res.json()["detail"]
    assert rows(db_file, "SELECT COUNT(*) FROM chat_messages")[0][0] == before


def test_history_endpoint_reads_seed_format(logged_in, db_file):
    """The seed rows store products_json as a list of full product dicts; still readable."""
    seed_style = json.dumps([{"product_id": "basic-hoodie-big-yale", "name": "Basic Hoodie Big Yale",
                              "price": 68.0, "image_url": "/x.jpg"}])
    con = sqlite3.connect(db_file)
    con.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (1, 'user', 'old question')")
    con.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (1, 'assistant', 'old answer', ?)",
                (seed_style,))
    con.commit()
    con.close()
    question, answer = logged_in.get("/api/chat/history").json()["messages"][-2:]
    assert (question["role"], question["content"], question["showcase"]) == ("user", "old question", None)
    assert answer["showcase"]["title"] == "Picked for you"
    assert answer["showcase"]["products"][0]["id"] == "basic-hoodie-big-yale"
    assert "sizes" in answer["showcase"]["products"][0]


def test_message_validation(logged_in, scripted):
    assert logged_in.post("/api/chat", json={"message": ""}).status_code == 422
    assert logged_in.post("/api/chat", json={"message": "x" * 1001}).status_code == 422


# ---------- products API ----------

def test_products_api_uses_camel_case(client):
    products = client.get("/api/products").json()
    assert len(products) == 102
    first = products[0]
    assert {"id", "garmentType", "category", "image", "sizes"} <= first.keys()
    assert client.get("/api/products/nope").status_code == 404


def test_images_are_public_but_database_is_not(client):
    assert client.get("/data/products/basic-hoodie-big-yale.jpg").status_code == 200
    assert client.get("/data/campus_customs.db").status_code == 404
    assert client.get("/data/products/../campus_customs.db").status_code == 404


# ---------- catalogue search (used by the agent's tools) ----------

def test_search_ranks_and_filters(db_file):
    from db import open_db
    with open_db(read_only=True) as con:
        saybrook = catalogue.search(con, "Saybrook")
        hoodies = catalogue.search(con, "hoodies", limit=50)
        navy_xl_cheap = catalogue.search(con, "", color="navy", size="XL", max_price=40, limit=50)
        nothing = catalogue.search(con, "coffee mug")
    assert saybrook and all("saybrook" in p.id for p in saybrook)
    assert hoodies[0].category == "Hoodies"
    assert all(p.price <= 40 and any("navy" in c for c in p.colors) for p in navy_xl_cheap)
    assert all(any(s.size == "XL" and s.quantity > 0 for s in p.sizes) for p in navy_xl_cheap)
    assert nothing == []
