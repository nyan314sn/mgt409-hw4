"""Cart pricing and checkout: reserve items for in-store pickup at 57 Broadway.

No payment is taken online - shoppers pay when they pick up - so the site never handles card
details. Prices always come from the database (never from the browser), and stock is taken
off atomically when an order is placed, so two shoppers can't reserve the last item twice.
"""
import secrets
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

import auth
import catalogue
from db import get_db
from models import CartIn, CartLineQuote, CartQuote, CheckoutIn, OrderItemOut, OrderOut

router = APIRouter(prefix="/api", tags=["cart"])


def _merge(items) -> dict[tuple[str, str], int]:
    """Same product+size listed twice -> one line."""
    merged: dict[tuple[str, str], int] = {}
    for line in items:
        merged[(line.product_id, line.size)] = merged.get((line.product_id, line.size), 0) + line.quantity
    return merged


def quote_cart(con: sqlite3.Connection, items) -> CartQuote:
    lines = []
    for (pid, size), qty in _merge(items).items():
        product = catalogue.get_product(con, pid)
        if product is None:
            lines.append(CartLineQuote(product_id=pid, size=size, quantity=qty, available=0, problem="unknown_product"))
            continue
        available = next((s.quantity for s in product.sizes if s.size == size), 0)
        problem = "sold_out" if available == 0 else "not_enough_stock" if available < qty else None
        lines.append(CartLineQuote(
            product_id=pid, size=size, quantity=qty, name=product.name, image=product.image,
            unit_price=product.price, line_total=round(product.price * qty, 2), available=available, problem=problem,
        ))
    priced = [l for l in lines if l.line_total is not None]
    return CartQuote(
        lines=lines,
        item_count=sum(l.quantity for l in priced),
        subtotal=round(sum(l.line_total for l in priced), 2),
        ok=bool(lines) and all(l.problem is None for l in lines),
    )


@router.post("/cart/quote", response_model=CartQuote)
def cart_quote(body: CartIn, con: sqlite3.Connection = Depends(get_db)) -> CartQuote:
    """Live prices and stock for a cart (open to guests - the cart itself lives in the browser)."""
    return quote_cart(con, body.items)


def _order_out(con: sqlite3.Connection, order: sqlite3.Row) -> OrderOut:
    items = []
    for r in con.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY product_name, size", (order["id"],)):
        product = catalogue.get_product(con, r["product_id"])
        items.append(OrderItemOut(product_id=r["product_id"], name=r["product_name"], size=r["size"],
                                  quantity=r["quantity"], unit_price=r["unit_price"],
                                  image=product.image if product else ""))
    return OrderOut(order_number=order["order_number"], status=order["status"], pickup_name=order["pickup_name"],
                    note=order["note"], item_count=order["item_count"], subtotal=order["subtotal"],
                    created_at=order["created_at"], items=items)


@router.post("/orders", response_model=OrderOut, status_code=201)
def place_order(
    body: CheckoutIn,
    user: sqlite3.Row = Depends(auth.current_user),
    con: sqlite3.Connection = Depends(get_db),
) -> OrderOut:
    quote = quote_cart(con, body.items)
    if not quote.lines:
        raise HTTPException(status_code=422, detail="Your cart is empty.")
    if not quote.ok:
        raise HTTPException(status_code=409, detail={
            "message": "Some items changed while you were shopping. Please review your cart.",
            "quote": quote.model_dump(by_alias=True)})

    # Take stock off line by line; the WHERE makes each update all-or-nothing, and any
    # shortfall (someone else just bought it) rolls back the whole order.
    for line in quote.lines:
        cur = con.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND size = ? AND quantity >= ?",
            (line.quantity, line.product_id, line.size, line.quantity))
        if cur.rowcount != 1:
            con.rollback()
            raise HTTPException(status_code=409, detail={
                "message": "Someone just bought the last of an item in your cart. Please review your cart.",
                "quote": quote_cart(con, body.items).model_dump(by_alias=True)})

    number = f"CC-{datetime.now(timezone.utc):%y%m%d}-{secrets.token_hex(3).upper()}"
    cur = con.execute(
        """INSERT INTO orders (order_number, user_id, pickup_name, note, item_count, subtotal)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (number, user["id"], body.pickup_name.strip(), (body.note or "").strip() or None, quote.item_count, quote.subtotal))
    con.executemany(
        "INSERT INTO order_items (order_id, product_id, product_name, size, quantity, unit_price) VALUES (?, ?, ?, ?, ?, ?)",
        [(cur.lastrowid, l.product_id, l.name, l.size, l.quantity, l.unit_price) for l in quote.lines])
    return _order_out(con, con.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone())


@router.get("/orders", response_model=list[OrderOut])
def my_orders(user: sqlite3.Row = Depends(auth.current_user), con: sqlite3.Connection = Depends(get_db)) -> list[OrderOut]:
    rows = con.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user["id"],)).fetchall()
    return [_order_out(con, r) for r in rows]


@router.get("/orders/{order_number}", response_model=OrderOut)
def my_order(order_number: str, user: sqlite3.Row = Depends(auth.current_user),
             con: sqlite3.Connection = Depends(get_db)) -> OrderOut:
    row = con.execute("SELECT * FROM orders WHERE order_number = ? AND user_id = ?", (order_number, user["id"])).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return _order_out(con, row)
