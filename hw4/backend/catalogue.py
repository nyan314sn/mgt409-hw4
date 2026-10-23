"""Read-only catalogue queries, shared by the products API and the agent's tools."""
import json
import re
import sqlite3
from difflib import get_close_matches

from models import Product, SizeStock

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
COMMON_WORD_SHARE = 0.6  # a search word found in more than 60% of products is too common to filter on
CATEGORIES = ["Hoodies", "Crewnecks", "Quarter-zips", "Tees", "Jackets"]

# Words that would match everything (or nothing useful) in a keyword search.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "for", "in", "of", "on", "with", "to", "do", "you", "have",
    "any", "some", "show", "me", "i", "want", "need", "looking", "something", "is", "are", "it",
}
# Shopper words -> words used in the catalogue.
SYNONYMS = {
    "hoodie": "hood", "hoody": "hood", "tee": "t-shirt", "tshirt": "t-shirt", "shirt": "shirt",
    "sweatshirt": "sweatshirt", "crew": "crewneck", "quarterzip": "quarter-zip", "zip": "zip",
    "grey": "gray", "pink": "pink", "mother": "mom", "father": "dad",
}


def display_name(name: str) -> str:
    """Tidy names generated from URL slugs: "Benjamin Franklin 1 4 Zip" -> "... 1/4 Zip"."""
    return re.sub(r"\b1 4 Zip\b", "1/4 Zip", name)


def category_for(garment_type: str) -> str:
    """Collapse the 22 free-text garment types into the shop's five categories."""
    g = garment_type.lower()
    if "jacket" in g:
        return "Jackets"
    if "quarter-zip" in g:
        return "Quarter-zips"
    if "hood" in g:
        return "Hoodies"
    if "t-shirt" in g or "performance shirt" in g:
        return "Tees"
    return "Crewnecks"


def _stock(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    stock: dict[str, dict[str, int]] = {}
    for row in con.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(row["product_id"], {})[row["size"]] = row["quantity"]
    return stock


def _product(row: sqlite3.Row, stock: dict[str, int]) -> Product:
    return Product(
        id=row["product_id"],
        name=display_name(row["name"]),
        garment_type=row["garment_type"],
        category=category_for(row["garment_type"]),
        description=row["description"],
        colors=json.loads(row["colors"]),
        tags=json.loads(row["search_tags"]),
        # Images are served from /data/products (see main.py), matching image_file_path.
        image=f"/data/{row['image_file_path']}",
        price=row["price"],
        sizes=[SizeStock(size=s, quantity=stock.get(s, 0)) for s in SIZE_ORDER],
    )


def list_products(con: sqlite3.Connection) -> list[Product]:
    stock = _stock(con)
    rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [_product(r, stock.get(r["product_id"], {})) for r in rows]


def get_product(con: sqlite3.Connection, product_id: str) -> Product | None:
    row = con.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return None
    sizes = {r["size"]: r["quantity"] for r in
             con.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,))}
    return _product(row, sizes)


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-/]*", query.lower())
    terms = []
    for w in words:
        if w in STOP_WORDS:
            continue
        w = SYNONYMS.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = SYNONYMS.get(w[:-1], w[:-1])  # hoodies -> hood, tees -> t-shirt
        terms.append(w)
    return terms


def _haystack(p: Product) -> str:
    return " ".join([p.id.replace("-", " "), p.name, p.garment_type, p.category,
                     p.description, " ".join(p.colors), " ".join(p.tags)]).lower()


def search(
    con: sqlite3.Connection,
    query: str = "",
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    limit: int | None = 8,
) -> list[Product]:
    """Keyword search plus filters, case-insensitive. Products matching more query words
    rank higher; small typos ("hoddie", "saybrok") still match. limit=None returns all."""
    products = list_products(con)
    terms = _terms(query)
    if len(terms) > 1:
        # Words in almost every product ("yale") don't narrow anything; with other words
        # present, drop them so "yale dad" means "dad", not "everything".
        hays = [_haystack(p) for p in products]
        specific = [t for t in terms if sum(t in h for h in hays) <= COMMON_WORD_SHARE * len(hays)]
        terms = specific or terms
    scored = []
    for p in products:
        if category and p.category.lower() != category.lower():
            continue
        if color and not any(color.lower() in c.lower() for c in p.colors):
            continue
        if max_price is not None and p.price > max_price:
            continue
        if size and not any(s.size == size.upper() and s.quantity > 0 for s in p.sizes):
            continue
        hay = _haystack(p)
        hay_words = set(re.findall(r"[a-z0-9]+", hay))
        # Exact substring counts 1; a close spelling of a catalogue word (typo) counts 0.8.
        score = sum(1.0 if t in hay else 0.8 if len(t) >= 4 and get_close_matches(t, hay_words, n=1, cutoff=0.8) else 0.0
                    for t in terms)
        if terms and score == 0:
            continue
        scored.append((score, p))
    scored.sort(key=lambda sp: (-sp[0], sp[1].name))
    return [p for _, p in scored[:limit]] if limit is not None else [p for _, p in scored]
