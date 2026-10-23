"""Auth tests. Each test runs against a fresh temp copy of the seed database.

Run from backend/: C:\\Users\\Pi\\miniconda3\\python.exe -m pytest tests -q
"""
import hashlib
import sqlite3
import time

import auth
from passwords import ITERATIONS, hash_password, verify_password

SEED_EMAIL = "test@campuscustoms.yale.edu"
SEED_PASSWORD = "password"
NEW_USER = {
    "first_name": "Handsome",
    "last_name": "Dan",
    "email": "Handsome.Dan@Yale.edu",
    "password": "bulldog-bark-1889",
}


def rows(db_file, sql, *args):
    con = sqlite3.connect(db_file)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


# ---------- hashing ----------

def test_seed_hash_verifies_with_same_settings(db_file):
    stored = rows(db_file, "SELECT password_hash FROM users WHERE email = ?", SEED_EMAIL)[0][0]
    assert ITERATIONS == 120_000
    assert verify_password(SEED_PASSWORD, stored)
    assert not verify_password("Password", stored)


def test_new_hashes_use_unique_salts():
    a, b = hash_password("same-password"), hash_password("same-password")
    assert a != b and a.startswith("pbkdf2_sha256$")
    assert verify_password("same-password", a) and verify_password("same-password", b)


# ---------- login / register ----------

def test_seeded_user_can_log_in(client):
    res = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert res.status_code == 200
    assert res.json() == {"id": 1, "first_name": "Test", "last_name": "User", "email": SEED_EMAIL, "is_admin": True}
    assert "password" not in res.text
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["email"] == SEED_EMAIL


def test_new_account_is_stored_securely_and_can_log_in(client, db_file):
    res = client.post("/api/auth/register", json=NEW_USER)
    assert res.status_code == 201
    assert client.get("/api/auth/me").json()["first_name"] == "Handsome"  # logged in after signup

    row = rows(db_file, "SELECT * FROM users WHERE email = ?", "handsome.dan@yale.edu")[0]
    assert (row["name"], row["first_name"], row["last_name"]) == ("Handsome Dan", "Handsome", "Dan")
    assert NEW_USER["password"] not in row["password_hash"]
    algorithm, salt, digest = row["password_hash"].split("$")
    assert algorithm == "pbkdf2_sha256" and len(salt) == 32 and len(digest) == 64

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    res = client.post("/api/auth/login", json={"email": "HANDSOME.dan@yale.edu ", "password": NEW_USER["password"]})
    assert res.status_code == 200


def test_duplicate_email_rejected(client):
    assert client.post("/api/auth/register", json=NEW_USER).status_code == 201
    dup = {**NEW_USER, "email": "handsome.dan@YALE.EDU"}
    assert client.post("/api/auth/register", json=dup).status_code == 409


def test_validation_errors_do_not_echo_password(client):
    res = client.post("/api/auth/register", json={**NEW_USER, "password": "short7!"})
    assert res.status_code == 422
    assert "password" in res.json()["fields"]
    assert "short7!" not in res.text
    res = client.post("/api/auth/register", json={**NEW_USER, "email": "not-an-email"})
    assert res.json()["fields"]["email"] == "Enter a valid email address."


def test_wrong_password_and_unknown_email_look_identical(client):
    wrong = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": "nope"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@yale.edu", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Invalid email or password."}


def test_session_token_is_hashed_at_rest(client, db_file):
    res = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    token = res.cookies.get(auth.SESSION_COOKIE)
    stored = [r["token_hash"] for r in rows(db_file, "SELECT token_hash FROM sessions")]
    assert token and token not in stored
    assert hashlib.sha256(token.encode()).hexdigest() in stored


# ---------- lockout ----------

def _fail(client, email, times):
    return [client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code
            for _ in range(times)]


def test_lockout_after_repeated_failures(client, db_file):
    codes = _fail(client, SEED_EMAIL, auth.MAX_FAILED_ATTEMPTS)
    assert codes == [401] * (auth.MAX_FAILED_ATTEMPTS - 1) + [429]

    # Even the correct password is refused while locked.
    res = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert res.status_code == 429 and "Try again in" in res.json()["detail"]
    assert int(res.headers["retry-after"]) > 0

    # Once the lock expires, the right password works and the counter resets.
    con = sqlite3.connect(db_file)
    con.execute("UPDATE login_locks SET locked_until = ?", (time.time() - 1,))
    con.commit()
    con.close()
    res = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    assert res.status_code == 200
    assert rows(db_file, "SELECT * FROM login_locks WHERE scope = 'email_ip' AND key LIKE ?", SEED_EMAIL + "|%") == []


def test_unknown_emails_lock_the_same_way(client):
    """Lockout must not reveal which emails have accounts."""
    real = _fail(client, SEED_EMAIL, auth.MAX_FAILED_ATTEMPTS)
    fake = _fail(client, "ghost@yale.edu", auth.MAX_FAILED_ATTEMPTS)
    assert real == fake


def test_lockout_is_per_email(client):
    _fail(client, SEED_EMAIL, auth.MAX_FAILED_ATTEMPTS)
    client.post("/api/auth/register", json=NEW_USER)
    client.post("/api/auth/logout")
    res = client.post("/api/auth/login", json={"email": NEW_USER["email"], "password": NEW_USER["password"]})
    assert res.status_code == 200
