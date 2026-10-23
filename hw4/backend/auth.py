"""Create-account / log-in / log-out endpoints with cookie sessions and lockout.

Security choices:
- Passwords: PBKDF2-HMAC-SHA256 with a per-user salt (see passwords.py).
- Login failures always return the same "Invalid email or password." message.
- Repeated failures lock that email *from that network address*, plus wider per-address
  and per-email limits (see LOCK_RULES). Unknown emails are tracked and locked the same
  way, so the lockout doesn't reveal who has an account.
- Sessions: a random token in an HttpOnly cookie; only its SHA-256 is stored.
- password_hash never leaves this module, and requests are never echoed back.
"""
import hashlib
import math
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from db import get_db
from guest_chat import GUEST_COOKIE
from limits import client_ip
from settings import ADMIN_EMAILS
from passwords import DUMMY_HASH, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "cc_session"
SESSION_TTL = 7 * 24 * 3600
MAX_FAILED_ATTEMPTS = 5
FAILURE_WINDOW = 15 * 60
LOCKOUT_SECONDS = 15 * 60
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

INVALID_LOGIN = "Invalid email or password."
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ---------- request / response models ----------

def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address.")
    return value


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str
    # Upper bound keeps PBKDF2 cost per request predictable.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    is_admin: bool = False


def _user_out(row: sqlite3.Row) -> UserOut:
    first, last = row["first_name"], row["last_name"]
    if not first:  # older rows may only have `name`
        first, _, last = row["name"].partition(" ")
    return UserOut(id=row["id"], first_name=first, last_name=last or "", email=row["email"],
                   is_admin=row["email"].lower() in ADMIN_EMAILS)


# ---------- sessions ----------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(con: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    now = time.time()
    con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    con.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), user_id, now, now + SESSION_TTL),
    )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_TTL, httponly=True,
        samesite="lax", secure=COOKIE_SECURE, path="/",
    )
    response.delete_cookie(GUEST_COOKIE, path="/")  # the guest conversation ends at login


def current_user(
    cc_session: str | None = Cookie(default=None),
    con: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    """Dependency for routes that need a logged-in user."""
    if cc_session:
        row = con.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ?""",
            (_token_hash(cc_session), time.time()),
        ).fetchone()
        if row:
            return row
    raise HTTPException(status_code=401, detail="Not logged in.")


def require_admin(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    """Dependency for the usage dashboard: only accounts listed in ADMIN_EMAILS."""
    if user["email"].lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admins only.")
    return user


def optional_user(
    cc_session: str | None = Cookie(default=None),
    con: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row | None:
    """Dependency for routes open to guests: the logged-in user, or None."""
    try:
        return current_user(cc_session, con)
    except HTTPException:
        return None


# ---------- lockout ----------
# Failed logins are counted at three levels (table login_locks). The tight per-email lock is
# scoped to the attacker's network address, so nobody can lock a shopper out of their own
# account from somewhere else just by typing their email with wrong passwords.

LOCK_RULES = {
    # scope: (failures allowed, within seconds, lock for seconds)
    "email_ip": (MAX_FAILED_ATTEMPTS, FAILURE_WINDOW, LOCKOUT_SECONDS),  # one email from one address
    "ip": (20, 15 * 60, 15 * 60),                                        # one address trying many emails
    "email": (30, 60 * 60, 30 * 60),                                     # one email from many addresses
}


def _lock_keys(email: str, ip: str) -> dict[str, str]:
    return {"email_ip": f"{email}|{ip}", "ip": ip, "email": email}


def _locked_for(con: sqlite3.Connection, email: str, ip: str, now: float) -> int:
    """Seconds remaining on the longest active lock that applies (0 if none)."""
    remaining = 0
    for scope, key in _lock_keys(email, ip).items():
        row = con.execute("SELECT locked_until FROM login_locks WHERE scope = ? AND key = ?", (scope, key)).fetchone()
        if row and row["locked_until"] and row["locked_until"] > now:
            remaining = max(remaining, math.ceil(row["locked_until"] - now))
    return remaining


def _record_failure(con: sqlite3.Connection, email: str, ip: str, now: float) -> None:
    for scope, key in _lock_keys(email, ip).items():
        limit, window, lock_for = LOCK_RULES[scope]
        row = con.execute("SELECT * FROM login_locks WHERE scope = ? AND key = ?", (scope, key)).fetchone()
        if row is None or now - row["first_failed_at"] > window:
            count, first = 1, now
        else:
            count, first = row["failed_count"] + 1, row["first_failed_at"]
        locked_until = now + lock_for if count >= limit else None
        if locked_until:
            count, first = 0, now  # start fresh once the lock expires
        con.execute(
            """INSERT INTO login_locks (scope, key, failed_count, first_failed_at, locked_until)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(scope, key) DO UPDATE SET failed_count = excluded.failed_count,
                   first_failed_at = excluded.first_failed_at,
                   locked_until = COALESCE(excluded.locked_until, login_locks.locked_until)""",
            (scope, key, count, first, locked_until),
        )


def _clear_failures(con: sqlite3.Connection, email: str, ip: str) -> None:
    """A successful login clears this email+address counter (not the email-wide or address-wide ones)."""
    con.execute("DELETE FROM login_locks WHERE scope = 'email_ip' AND key = ?", (_lock_keys(email, ip)["email_ip"],))


def _locked_error(seconds: int) -> HTTPException:
    minutes = max(1, math.ceil(seconds / 60))
    return HTTPException(
        status_code=429,
        detail=f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
        headers={"Retry-After": str(seconds)},
    )


# ---------- endpoints ----------

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, response: Response, con: sqlite3.Connection = Depends(get_db)) -> UserOut:
    if con.execute("SELECT 1 FROM users WHERE lower(email) = ?", (body.email,)).fetchone():
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try logging in.")
    cur = con.execute(
        """INSERT INTO users (name, email, password_hash, first_name, last_name)
           VALUES (?, ?, ?, ?, ?)""",
        (f"{body.first_name} {body.last_name}", body.email, hash_password(body.password),
         body.first_name, body.last_name),
    )
    _start_session(con, response, cur.lastrowid)
    row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _user_out(row)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, response: Response,
          con: sqlite3.Connection = Depends(get_db)) -> UserOut:
    email = body.email.strip().lower()
    ip = client_ip(request)
    now = time.time()

    remaining = _locked_for(con, email, ip, now)
    if remaining:
        raise _locked_error(remaining)

    row = con.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    # Always run one PBKDF2 check so unknown emails take as long as wrong passwords.
    ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH) and row is not None

    if not ok:
        _record_failure(con, email, ip, now)
        con.commit()  # keep the failure even though we raise
        remaining = _locked_for(con, email, ip, now)
        if remaining:
            raise _locked_error(remaining)
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    _clear_failures(con, email, ip)
    _start_session(con, response, row["id"])
    return _user_out(row)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    cc_session: str | None = Cookie(default=None),
    con: sqlite3.Connection = Depends(get_db),
) -> Response:
    if cc_session:
        con.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(GUEST_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: sqlite3.Row = Depends(current_user)) -> UserOut:
    return _user_out(user)
