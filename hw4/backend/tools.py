"""Tools the shop agent can call. All are read-only lookups against campus_customs.db.

- search_products          find products by keywords and filters
- get_product_description  description, category, garment type, colors
- get_product_price        price in USD
- check_stock              units on hand, per size or for one requested size
- get_customer_profile     who is chatting (name, email, customer since) - from AgentDeps
- get_current_page         the page the shopper is on, and what's in the Spotlight

The single-product tools accept a product id *or* the shopper's own wording. Matching is
case-insensitive and tolerant of partial names and small typos (see resolve_product).
Each call opens a read-only connection that is always closed (db.open_db), and records
the product ids it returned in ``deps.seen_product_ids``.
"""
import re
import sqlite3
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from pydantic_ai import RunContext

import catalogue
from db import open_db
from models import (
    CustomerProfile,
    DescriptionInfo,
    LookupMiss,
    PageInfo,
    PriceInfo,
    ProductMatch,
    ProductRef,
    ProductSummary,
    SizeStockStatus,
    StockReport,
    StockStatus,
)

LOW_STOCK = 5             # 1-4 units left counts as "low"
FUZZY_ACCEPT = 0.75       # best fuzzy score needed to accept a match on its own
FUZZY_MARGIN = 0.08       # ...and how far ahead of the runner-up it must be
FUZZY_SUGGEST = 0.65      # minimum score to offer a product as a suggestion

SIZE_ALIASES = {
    "xs": "XS", "x-small": "XS", "extra small": "XS", "extra-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "x-large": "XL", "extra large": "XL", "extra-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
}


@dataclass
class SearchRecord:
    """The latest search_products call in this turn, used to label the Spotlight
    ("12 of 27 hoodies") and build its "see all" link."""
    query: str
    category: str | None
    color: str | None
    max_price: float | None
    size_in_stock: str | None
    total: int
    ids: list[str]


@dataclass
class AgentDeps:
    """Per-request context for the agent, built by main.py for each chat message.

    customer: the logged-in shopper from the users table (None for guests).
    page:     the page the message was sent from, validated against the catalogue.
    """
    customer: CustomerProfile | None = None
    page: PageInfo | None = None
    conversation_summary: str | None = None   # older chat, condensed (memory.py)
    seen_product_ids: set[str] = field(default_factory=set)
    last_search: SearchRecord | None = None


# ---------- product matching ----------

def _normalize(text: str) -> str:
    """Lowercase, treat - _ / as spaces, drop punctuation and filler words, and map
    shopper words to catalogue words ("tee" -> "t shirt", "hoody" -> "hood")."""
    words = re.findall(r"[a-z0-9]+", re.sub(r"[-_/]", " ", text.lower()))
    mapped = (catalogue.SYNONYMS.get(w, w) for w in words if w not in catalogue.STOP_WORDS)
    return " ".join(re.sub(r"[-_/]", " ", w) for w in mapped)


def _fuzzy_score(query: str, name: str) -> float:
    """0-1 similarity: the better of whole-string similarity and per-word similarity."""
    whole = SequenceMatcher(None, query, name).ratio()
    q_words, n_words = query.split(), name.split()
    if not q_words or not n_words:
        return whole
    per_word = sum(max(SequenceMatcher(None, q, n).ratio() for n in n_words) for q in q_words) / len(q_words)
    return max(whole, per_word)


def _ref(row: sqlite3.Row) -> ProductRef:
    return ProductRef(id=row["product_id"], name=catalogue.display_name(row["name"]))


def resolve_product(con: sqlite3.Connection, text: str) -> tuple[ProductRef, ProductMatch] | LookupMiss:
    """Match a product id or the shopper's wording to exactly one product.

    1. exact id, case-insensitive ("Basic-Hoodie-Big-Yale")
    2. exact name, case-insensitive ("basic hoodie big yale")
    3. partial: every word appears in the name or id, via SQL LIKE (case-insensitive)
       ("hopper crewneck" -> Grace Hopper College Crewneck)
    4. fuzzy: closest name by similarity, for typos ("saybrok colege crewnek")
    Ambiguous or unknown wording returns a LookupMiss with suggestions, never a guess.
    """
    query = text.strip()[:200]
    norm = _normalize(query)
    if not norm:
        return LookupMiss(query=query, reason="not_found", message="No product name was given.")

    def found(row: sqlite3.Row, match_type, note=None):
        return _ref(row), ProductMatch(query=query, match_type=match_type, note=note)

    slug = norm.replace(" ", "-")
    row = con.execute(
        "SELECT product_id, name FROM catalogue WHERE product_id = ? COLLATE NOCASE OR product_id = ? COLLATE NOCASE",
        (query, slug),
    ).fetchone()
    if row:
        return found(row, "exact_id")

    row = con.execute("SELECT product_id, name FROM catalogue WHERE name = ? COLLATE NOCASE", (query,)).fetchone()
    if row:
        return found(row, "exact_name")

    words = norm.split()
    where = " AND ".join("(name LIKE ? OR product_id LIKE ?)" for _ in words)
    params = [p for w in words for p in (f"%{w}%", f"%{w}%")]
    rows = con.execute(f"SELECT product_id, name FROM catalogue WHERE {where} ORDER BY name", params).fetchall()
    if len(rows) == 1:
        return found(rows[0], "partial")
    if len(rows) > 1:
        exact_phrase = [r for r in rows if norm in _normalize(r["name"])]
        if len(exact_phrase) == 1:
            return found(exact_phrase[0], "partial")
        return LookupMiss(
            query=query, reason="ambiguous",
            message=f"'{query}' matches {len(rows)} products. Ask the shopper which one they mean.",
            suggestions=[_ref(r) for r in rows[:6]],
        )

    scored = sorted(
        ((max(_fuzzy_score(norm, _normalize(r["name"])), _fuzzy_score(norm, _normalize(r["product_id"]))), r)
         for r in con.execute("SELECT product_id, name FROM catalogue")),
        key=lambda sr: sr[0], reverse=True,
    )
    best_score, best = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score >= FUZZY_ACCEPT and best_score - runner_up >= FUZZY_MARGIN:
        return found(best, "fuzzy", note=f"'{query}' matched '{catalogue.display_name(best['name'])}' (closest name). Confirm with the shopper.")

    suggestions = [_ref(r) for s, r in scored[:3] if s >= FUZZY_SUGGEST]
    return LookupMiss(
        query=query,
        reason="ambiguous" if suggestions else "not_found",
        message=(f"No product clearly matches '{query}'. Closest options are listed."
                 if suggestions else f"No product matches '{query}'. Try search_products."),
        suggestions=suggestions,
    )


def normalize_size(size: str) -> str | None:
    """'medium' -> 'M', 'xl' -> 'XL'. None if it isn't one of the shop's sizes."""
    key = size.strip().lower()
    return SIZE_ALIASES.get(key) or (key.upper() if key.upper() in catalogue.SIZE_ORDER else None)


def _status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity < LOW_STOCK else "in_stock"


# ---------- tools ----------

def search_products(
    ctx: RunContext[AgentDeps],
    query: str = "",
    category: Literal["Hoodies", "Crewnecks", "Quarter-zips", "Tees", "Jackets"] | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size_in_stock: Literal["XS", "S", "M", "L", "XL", "XXL"] | None = None,
    limit: int = 12,
) -> list[ProductSummary]:
    """Find products. Use this to browse or recommend (by college, sport, school, family
    member, style, color, budget, or size in stock). Tolerates small typos.

    Args:
        query: Keywords such as "Saybrook", "hockey", "Yale Mom", "vintage bulldog".
            Empty lists everything that matches the filters.
        category: Limit to one category.
        color: Only products that include this color (e.g. "navy", "gray", "red").
        max_price: Only products at or under this price in USD.
        size_in_stock: Only products with this size in stock.
        limit: Maximum results (1-20). 12 fills the on-page showcase.
    """
    with open_db(read_only=True) as con:
        matches = catalogue.search(con, query, category, color, max_price, size_in_stock, limit=None)
    results = matches[:max(1, min(limit, 20))]
    ctx.deps.seen_product_ids.update(p.id for p in results)
    ctx.deps.last_search = SearchRecord(query=query, category=category, color=color, max_price=max_price,
                                        size_in_stock=size_in_stock, total=len(matches),
                                        ids=[p.id for p in matches])
    return [
        ProductSummary(id=p.id, name=p.name, category=p.category, price=p.price, colors=p.colors,
                       sizes_in_stock=[s.size for s in p.sizes if s.quantity > 0], description=p.description)
        for p in results
    ]


def get_product_description(ctx: RunContext[AgentDeps], product: str) -> DescriptionInfo | LookupMiss:
    """Get a product's description, category, garment type, and colors from the database.
    Use for "what does it look like / what is it made like / what colors" questions.

    Args:
        product: Product id (from search_products) or the shopper's wording for it.
    """
    with open_db(read_only=True) as con:
        resolved = resolve_product(con, product)
        if isinstance(resolved, LookupMiss):
            return resolved
        ref, match = resolved
        p = catalogue.get_product(con, ref.id)
    ctx.deps.seen_product_ids.add(ref.id)
    return DescriptionInfo(product=ref, match=match, category=p.category, garment_type=p.garment_type,
                           description=p.description, colors=p.colors)


def get_product_price(ctx: RunContext[AgentDeps], product: str) -> PriceInfo | LookupMiss:
    """Get a product's current price (USD) from the database. Call this every time a price
    is asked about or quoted - never reuse a price from memory or an earlier turn.

    Args:
        product: Product id (from search_products) or the shopper's wording for it.
    """
    with open_db(read_only=True) as con:
        resolved = resolve_product(con, product)
        if isinstance(resolved, LookupMiss):
            return resolved
        ref, match = resolved
        price = con.execute("SELECT price FROM catalogue WHERE product_id = ?", (ref.id,)).fetchone()["price"]
    ctx.deps.seen_product_ids.add(ref.id)
    return PriceInfo(product=ref, match=match, price=price)


def check_stock(ctx: RunContext[AgentDeps], product: str, size: str | None = None) -> StockReport | LookupMiss:
    """Get live stock from the inventory table: units on hand for every size, and the status
    of one size if the shopper asked about it. Call this for any availability question.

    Args:
        product: Product id (from search_products) or the shopper's wording for it.
        size: Size the shopper asked about, e.g. "M", "medium", "XL", "2XL". Omit for all sizes.
    """
    with open_db(read_only=True) as con:
        resolved = resolve_product(con, product)
        if isinstance(resolved, LookupMiss):
            return resolved
        ref, match = resolved
        quantities = {r["size"]: r["quantity"] for r in
                      con.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (ref.id,))}
    ctx.deps.seen_product_ids.add(ref.id)

    sizes = [SizeStockStatus(size=s, quantity=quantities.get(s, 0), status=_status(quantities.get(s, 0)))
             for s in catalogue.SIZE_ORDER]
    report = StockReport(
        product=ref, match=match, sizes=sizes,
        available_sizes=[s.size for s in sizes if s.quantity > 0],
        sold_out_sizes=[s.size for s in sizes if s.quantity == 0],
        total_in_stock=sum(s.quantity for s in sizes),
    )
    if size:
        wanted = normalize_size(size)
        if wanted is None:
            report.requested_size, report.requested_size_status = size.strip(), "size_not_offered"
        else:
            entry = next(s for s in sizes if s.size == wanted)
            report.requested_size = wanted
            report.requested_size_status = entry.status
            report.requested_size_quantity = entry.quantity
    return report


def get_customer_profile(ctx: RunContext[AgentDeps]) -> CustomerProfile | str:
    """Who you're chatting with: first and last name, email, customer-since date, and how
    many messages are in their saved chat history. Only ever about the current shopper.
    Use it to personalize, or when they ask what email or name is on their account.
    """
    if ctx.deps.customer is None:
        return "The shopper is a guest (not logged in). No name or email is known; don't ask for them."
    return ctx.deps.customer


def get_current_page(ctx: RunContext[AgentDeps]) -> PageInfo | str:
    """The page the shopper is looking at right now: page type, the product if it's a
    product page, Products-page filters, and the cards shown in the Spotlight (in order).
    Use it to resolve "this", "it", "the second one", etc.
    """
    if ctx.deps.page is None:
        return "No page information was sent with this message."
    if ctx.deps.page.product:
        ctx.deps.seen_product_ids.add(ctx.deps.page.product.id)
    ctx.deps.seen_product_ids.update(p.id for p in ctx.deps.page.spotlight)
    return ctx.deps.page


TOOLS = [search_products, get_product_description, get_product_price, check_stock,
         get_customer_profile, get_current_page]
