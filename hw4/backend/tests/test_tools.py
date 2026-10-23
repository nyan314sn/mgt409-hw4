"""Lookup tools: product matching, price, description, stock by size, and connection hygiene."""
import sqlite3
from types import SimpleNamespace

import pytest
from pydantic_ai.models.function import FunctionModel

import db
import tools
from agent import get_agent
from models import DescriptionInfo, LookupMiss, PriceInfo, StockReport
from tools import AgentDeps, check_stock, get_product_description, get_product_price, resolve_product


@pytest.fixture()
def ctx(db_file):
    return SimpleNamespace(deps=AgentDeps())


def resolve(text):
    with db.open_db(read_only=True) as con:
        return resolve_product(con, text)


# ---------- matching: case, partial, typos ----------

@pytest.mark.parametrize("text, match_type, product_id", [
    ("saybrook-college-crewneck", "exact_id", "saybrook-college-crewneck"),
    ("SAYBROOK-COLLEGE-CREWNECK", "exact_id", "saybrook-college-crewneck"),
    ("saybrook college crewneck", "exact_id", "saybrook-college-crewneck"),  # name slugs to the id
    ("yale MOM hoodie", "exact_name", "yale-mom-hoodie"),
    ("hopper crewneck", "partial", "grace-hopper-college-crewneck"),
    ("the Saybrook CREWNECK", "partial", "saybrook-college-crewneck"),
    ("yale mom hoody", "partial", "yale-mom-hoodie"),
    ("saybrook tee", "partial", "saybrook-logo-t-shirt"),
    ("saybrok colege crewnek", "fuzzy", "saybrook-college-crewneck"),
    ("grace hoper tee", "fuzzy", "grace-hopper-logo-t-shirt"),
])
def test_resolve_product_matches(db_file, text, match_type, product_id):
    result = resolve(text)
    assert not isinstance(result, LookupMiss), result
    ref, match = result
    assert (match.match_type, ref.id) == (match_type, product_id)
    assert (match.note is not None) == (match_type == "fuzzy")


def test_ambiguous_names_ask_instead_of_guessing(db_file):
    result = resolve("saybrook")
    assert isinstance(result, LookupMiss) and result.reason == "ambiguous"
    assert {s.id for s in result.suggestions} == {
        "saybrook-college-crewneck", "saybrook-logo-t-shirt", "saybrook-sweater-fleece-jacket"}


@pytest.mark.parametrize("text", ["coffee mug", "pink baseball cap", "", "   "])
def test_unknown_products_are_not_found(db_file, text):
    result = resolve(text)
    assert isinstance(result, LookupMiss) and result.reason == "not_found" and result.suggestions == []


def test_sql_wildcards_in_input_are_harmless(db_file):
    assert isinstance(resolve("%"), LookupMiss)
    assert isinstance(resolve("_ _ _"), LookupMiss)
    assert isinstance(resolve("'; DROP TABLE catalogue; --"), LookupMiss)
    with db.open_db(read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0] == 102


# ---------- price / description / stock come from the database ----------

def test_price_matches_database(ctx, db_file):
    result = get_product_price(ctx, "saybrok crewnek")
    assert isinstance(result, PriceInfo)
    with db.open_db(read_only=True) as con:
        expected = con.execute("SELECT price FROM catalogue WHERE product_id = 'saybrook-college-crewneck'").fetchone()[0]
    assert result.price == expected == 58.0 and result.currency == "USD"
    assert "saybrook-college-crewneck" in ctx.deps.seen_product_ids


def test_price_follows_database_changes(ctx, db_file):
    con = sqlite3.connect(db_file)
    con.execute("UPDATE catalogue SET price = 61.5 WHERE product_id = 'basic-hoodie-big-yale'")
    con.commit()
    con.close()
    assert get_product_price(ctx, "Basic Hoodie Big Yale").price == 61.5


def test_description_fields(ctx):
    result = get_product_description(ctx, "benjamin franklin 1/4 zip")
    assert isinstance(result, DescriptionInfo)
    assert result.product.id == "benjamin-franklin-1-4-zip"
    assert result.category == "Quarter-zips" and "quarter-zip" in result.description.lower()
    assert result.colors == ["heather gray", "blue", "red", "white"]


def test_stock_all_sizes(ctx):
    result = check_stock(ctx, "saybrook college crewneck")
    assert isinstance(result, StockReport)
    assert [(s.size, s.quantity, s.status) for s in result.sizes] == [
        ("XS", 15, "in_stock"), ("S", 15, "in_stock"), ("M", 15, "in_stock"),
        ("L", 2, "low_stock"), ("XL", 15, "in_stock"), ("XXL", 0, "sold_out")]
    assert result.sold_out_sizes == ["XXL"] and result.total_in_stock == 62
    assert result.requested_size is None


@pytest.mark.parametrize("size, normalized, status, quantity", [
    ("XXL", "XXL", "sold_out", 0),
    ("2xl", "XXL", "sold_out", 0),
    ("large", "L", "low_stock", 2),
    ("Medium", "M", "in_stock", 15),
])
def test_stock_for_requested_size(ctx, size, normalized, status, quantity):
    result = check_stock(ctx, "saybrook-college-crewneck", size=size)
    assert (result.requested_size, result.requested_size_status, result.requested_size_quantity) == (
        normalized, status, quantity)


def test_stock_for_a_size_the_shop_does_not_carry(ctx):
    result = check_stock(ctx, "saybrook-college-crewneck", size="3XL")
    assert result.requested_size_status == "size_not_offered"


def test_tools_return_miss_for_unknown_product(ctx):
    for tool in (get_product_price, get_product_description, check_stock):
        assert isinstance(tool(ctx, "flux capacitor"), LookupMiss)
    assert ctx.deps.seen_product_ids == set()


# ---------- connection hygiene ----------

class TrackedConnection(sqlite3.Connection):
    live: set[int] = set()
    opened = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        TrackedConnection.opened += 1
        TrackedConnection.live.add(id(self))

    def close(self):
        TrackedConnection.live.discard(id(self))
        super().close()


@pytest.fixture()
def tracked(monkeypatch):
    TrackedConnection.live.clear()
    TrackedConnection.opened = 0
    monkeypatch.setattr(db, "CONNECTION_CLASS", TrackedConnection)
    return TrackedConnection


def test_no_connection_leaks(tracked, client, ctx, monkeypatch):
    # Direct tool calls, including misses and errors.
    get_product_price(ctx, "saybrook crewneck")
    get_product_description(ctx, "nope nope")
    check_stock(ctx, "yale mom hoodie", size="M")
    tools.search_products(ctx, "hockey")
    with pytest.raises(RuntimeError):
        with db.open_db() as con:
            con.execute("SELECT 1")
            raise RuntimeError("boom")

    # API requests, including a failing one and a full chat turn with tool calls.
    client.get("/api/products")
    client.get("/api/products/nope")
    client.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "wrong"})
    client.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})

    def scripted(messages, info):
        from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
        if any(isinstance(p, ToolReturnPart) for p in messages[-1].parts):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"message": "ok", "product_ids": []})])
        return ModelResponse(parts=[ToolCallPart("check_stock", {"product": "saybrook crewneck", "size": "XXL"})])

    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    with get_agent().override(model=FunctionModel(scripted)):
        assert client.post("/api/chat", json={"message": "XXL?"}).status_code == 200

    assert tracked.opened > 10
    assert tracked.live == set(), f"{len(tracked.live)} connection(s) left open"


def test_common_words_do_not_widen_search(db_file):
    import catalogue
    with db.open_db(read_only=True) as con:
        dad = catalogue.search(con, "Yale Dad", limit=None)
        just_yale = catalogue.search(con, "yale", limit=None)
    assert dad and all("dad" in p.name.lower() for p in dad)
    assert len(just_yale) > 50  # a lone common word still searches normally
