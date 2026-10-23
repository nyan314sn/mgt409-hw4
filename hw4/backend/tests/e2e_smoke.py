"""End-to-end check against the running app (Vite on :5173 proxying the API on :8000).

Logs in as the seeded test user, creates a brand-new account in the real database,
logs out, and logs back in. Each run makes a unique account with a random password,
which is never printed.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_smoke.py [base_url]
"""
import secrets
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok' if ok else 'FAIL'}] {label}{' - ' + detail if detail else ''}")
    if not ok:
        sys.exit(1)


def main() -> None:
    print(f"E2E auth smoke test against {BASE}")
    with httpx.Client(base_url=BASE, timeout=30) as c:
        res = c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
        check("seeded test user logs in", res.status_code == 200, res.json().get("email", ""))
        check("session cookie is HttpOnly", "httponly" in res.headers.get("set-cookie", "").lower())
        check("/me returns the user", c.get("/api/auth/me").json().get("first_name") == "Test")
        c.post("/api/auth/logout")
        check("logged out", c.get("/api/auth/me").status_code == 401)

        email = f"e2e.{int(time.time())}@campuscustoms.yale.edu"
        password = secrets.token_urlsafe(12)
        res = c.post("/api/auth/register", json={
            "first_name": "Handsome", "last_name": "Dan", "email": email, "password": password,
        })
        check("new account created", res.status_code == 201, email)
        c.post("/api/auth/logout")

        res = c.post("/api/auth/login", json={"email": email, "password": password})
        check("new account logs in", res.status_code == 200)
        c.post("/api/auth/logout")

        wrong = c.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
        unknown = c.post("/api/auth/login", json={"email": "nobody@yale.edu", "password": "wrong-password"})
        check("wrong password and unknown email give the same answer",
              wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json(),
              wrong.json().get("detail", ""))
    print("All end-to-end checks passed.")


if __name__ == "__main__":
    main()
