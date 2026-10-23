"""Live check of Problem 8 with the real model (makes a few AI calls).

1. A guest on the Saybrook College Crewneck page asks "do you have this in pink?".
   The answer must be about that crewneck (it isn't made in pink) - and nothing is saved.
2. The seeded test user logs in, asks "what email is my account under?" and the same
   pink question on a product page, then logs out.
3. The test user logs back in from a new session: the saved history comes back, and a
   follow-up from the home page ("what about in XL?") is still about that product.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_context.py [base_url]
"""
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
SEED = {"email": "test@campuscustoms.yale.edu", "password": "password"}
PAGE = {"path": "/products/saybrook-college-crewneck"}
failures = 0


def ask(c: httpx.Client, message: str, page: dict | None, must: list[str]) -> str:
    global failures
    t = time.perf_counter()
    res = c.post("/api/chat", json={"message": message, "page": page})
    reply = res.json()["message"]["content"] if res.status_code == 200 else res.text
    missing = [m for m in must if m.lower() not in reply.lower()]
    failures += bool(missing) or res.status_code != 200
    where = f" [on {page['path']}]" if page else ""
    print(f"\n[{'ok' if not missing and res.status_code == 200 else 'FAIL'}] SHOPPER{where}: {message}  ({time.perf_counter() - t:.1f}s)")
    print(f"  ASSISTANT: {reply}")
    if missing:
        print(f"  missing: {missing}")
    return reply


def check(label: str, ok: bool) -> None:
    global failures
    failures += not ok
    print(f"[{'ok' if ok else 'FAIL'}] {label}")


def main() -> None:
    print("--- 1. Guest")
    with httpx.Client(base_url=BASE, timeout=120) as guest:
        ask(guest, "do you have this in pink?", PAGE, ["Saybrook College Crewneck"])
        history = guest.get("/api/chat/history").json()
        check("guest history kept for the visit but not saved", history["saved"] is False and len(history["messages"]) == 2)

    print("\n--- 2. Logged in")
    with httpx.Client(base_url=BASE, timeout=120) as first:
        first.post("/api/auth/login", json=SEED).raise_for_status()
        ask(first, "what email is my account under?", {"path": "/"}, ["test@campuscustoms.yale.edu"])
        ask(first, "do you have this in pink?", PAGE, ["Saybrook College Crewneck"])
        first.post("/api/auth/logout")

    print("\n--- 3. Coming back later")
    with httpx.Client(base_url=BASE, timeout=120) as later:
        later.post("/api/auth/login", json=SEED).raise_for_status()
        history = later.get("/api/chat/history").json()
        contents = [m["content"] for m in history["messages"]]
        check("saved history reloaded after logging back in",
              history["saved"] and "do you have this in pink?" in contents and "what email is my account under?" in contents)
        ask(later, "what about in XL - is that one in stock?", {"path": "/"}, ["Saybrook College Crewneck", "XL"])
        later.post("/api/auth/logout")

    print(f"\n{'All checks passed' if not failures else f'{failures} check(s) failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
