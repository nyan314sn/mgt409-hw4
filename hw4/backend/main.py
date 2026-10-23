"""Campus Customs API (FastAPI). Run from the backend/ folder:

    uvicorn main:app --reload --port 8000

The Vite dev server proxies /api and /data to this app, so the browser sees one origin.
"""
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import auth
import catalogue
import limits
import memory
import orders
import usage
from agent import (
    HISTORY_TURNS,
    AgentUnavailable,
    customer_profile,
    hydrate_showcase,
    parse_stored_showcase,
    resolve_page,
    run_turn,
    store_page_context,
    store_showcase,
)
from db import get_db, init_schema
from guest_chat import GUEST_COOKIE, GUEST_TTL, MAX_GUEST_TURNS, guest_chats
from models import AssistantMessage, ChatHistory, ChatHistoryMessage, ChatReply, ChatRequest, Product
from settings import PRODUCT_IMAGES_DIR

log = logging.getLogger("campus_customs")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_schema()
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(orders.router)
# Only the product photos folder is public - never the data/ folder that holds the database.
app.mount("/data/products", StaticFiles(directory=PRODUCT_IMAGES_DIR), name="product-images")


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return field-level messages without echoing submitted values (e.g. passwords)."""
    fields = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err.get("loc") else "body"
        message = err.get("msg", "Invalid value.").removeprefix("Value error, ")
        fields.setdefault(field, message)
    return JSONResponse(status_code=422, content={"detail": "Please check the highlighted fields.", "fields": fields})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------- products ----------

@app.get("/api/products", response_model=list[Product])
def products(con: sqlite3.Connection = Depends(get_db)) -> list[Product]:
    return catalogue.list_products(con)


@app.get("/api/products/{product_id}", response_model=Product)
def product(product_id: str, con: sqlite3.Connection = Depends(get_db)) -> Product:
    found = catalogue.get_product(con, product_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return found


# ---------- chat ----------
# Logged-in shoppers: history is stored in chat_messages (one row per message, keyed by
# users.id). The model sees every not-yet-summarized message plus a summary of older ones
# (memory.py). Guests: history lives in memory (guest_chat.py) for this visit only.
# Either way the browser sends only the new message + page context; it never sends history,
# so it can't forge or drop earlier turns.

def _saved_messages(con: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    rows = con.execute(
        """SELECT role, content, products_json, page_context, created_at FROM chat_messages
           WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return rows[::-1]  # oldest first


def _check_chat_limits(con: sqlite3.Connection, user: sqlite3.Row | None, cc_guest: str | None, ip: str) -> None:
    """Fair-use limits so no single account, guest, or network address can run up AI costs."""
    if user:
        if usage.chats_last_24h(con, user["id"]) >= limits.USER_DAILY:
            raise limits.too_many(3600, "You've reached today's chat limit.")
        wait = limits.chat_windows.retry_after(f"user:{user['id']}", *limits.USER_BURST, record=False)
        if wait:
            raise limits.too_many(wait, "You're sending messages very quickly.")
    else:
        if guest_chats.turns_used(cc_guest) >= MAX_GUEST_TURNS:
            raise HTTPException(status_code=429, detail="You've reached the guest chat limit. Log in or create an account to keep chatting.")
        wait = limits.chat_windows.retry_after(f"guest-ip:{ip}", *limits.GUEST_IP_HOURLY, record=False)
        if wait:
            raise limits.too_many(wait, "Lots of guest chats are coming from your network. Log in to keep chatting, or")
    wait = limits.chat_windows.retry_after(f"ip:{ip}", *limits.IP_BURST, record=False)
    if wait:
        raise limits.too_many(wait, "Too many messages from your network.")


def _count_chat(user: sqlite3.Row | None, ip: str) -> None:
    if user:
        limits.chat_windows.retry_after(f"user:{user['id']}", *limits.USER_BURST, record=True)
    else:
        limits.chat_windows.retry_after(f"guest-ip:{ip}", *limits.GUEST_IP_HOURLY, record=True)
    limits.chat_windows.retry_after(f"ip:{ip}", *limits.IP_BURST, record=True)


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(
    user: sqlite3.Row | None = Depends(auth.optional_user),
    cc_guest: str | None = Cookie(default=None),
    con: sqlite3.Connection = Depends(get_db),
) -> ChatHistory:
    rows = _saved_messages(con, user["id"], 50) if user else guest_chats.history(cc_guest)
    return ChatHistory(saved=user is not None, messages=[
        ChatHistoryMessage(role=r["role"], content=r["content"], created_at=r["created_at"],
                           showcase=hydrate_showcase(con, parse_stored_showcase(r["products_json"])))
        for r in rows
    ])


@app.post("/api/chat", response_model=ChatReply)
async def chat(
    body: ChatRequest,
    request: Request,
    response: Response,
    background: BackgroundTasks,
    user: sqlite3.Row | None = Depends(auth.optional_user),
    cc_guest: str | None = Cookie(default=None),
    con: sqlite3.Connection = Depends(get_db),
) -> ChatReply:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message can't be empty.")
    ip = limits.client_ip(request)
    _check_chat_limits(con, user, cc_guest, ip)

    summary = None
    if user:
        summary, history = memory.load_memory(con, user["id"])
        customer = customer_profile(con, user)
    else:
        history = guest_chats.history(cc_guest)[-HISTORY_TURNS * 2:]
        customer = None
    page = resolve_page(con, body.page)

    _count_chat(user, ip)
    user_id = user["id"] if user else None
    try:
        content, showcase, stats = await run_turn(con, history, message, customer, page, summary)
    except AgentUnavailable as exc:
        if exc.stats:
            usage.record_run(con, exc.stats, user_id, ip)
            con.commit()  # keep the log row even though the request fails
        log.warning("Chat agent unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="The shop assistant is unavailable right now. Please try again in a moment.")
    usage.record_run(con, stats, user_id, ip)

    # Save both sides only after a successful reply, so a failed turn leaves no half-pair.
    user_row = {"role": "user", "content": message, "products_json": None, "page_context": store_page_context(page)}
    assistant_row = {"role": "assistant", "content": content, "products_json": store_showcase(showcase), "page_context": None}
    if user:
        con.executemany(
            "INSERT INTO chat_messages (user_id, role, content, products_json, page_context) VALUES (?, ?, ?, ?, ?)",
            [(user["id"], r["role"], r["content"], r["products_json"], r["page_context"]) for r in (user_row, assistant_row)],
        )
        con.commit()  # release the write lock before the background summary writes
        # Fold old messages into the summary after the reply is sent (no wait for the shopper).
        background.add_task(memory.update_summary, user["id"], ip)
    else:
        token = cc_guest or guest_chats.new_token()
        guest_chats.append_turn(token, user_row, assistant_row)
        response.set_cookie(GUEST_COOKIE, token, max_age=GUEST_TTL, httponly=True, samesite="lax",
                            secure=auth.COOKIE_SECURE, path="/")
    # The contract: chat text and product data travel as two separate objects.
    return ChatReply(message=AssistantMessage(content=content), showcase=showcase)


# ---------- admin: agent usage and cost ----------

@app.get("/api/admin/usage")
def admin_usage(
    days: int = Query(default=7, ge=1, le=90),
    _: sqlite3.Row = Depends(auth.require_admin),
    con: sqlite3.Connection = Depends(get_db),
) -> dict:
    return usage.usage_report(con, days)
