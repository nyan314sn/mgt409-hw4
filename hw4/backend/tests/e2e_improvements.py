"""Live check of the Problem 9 improvements against the running app (makes a couple of AI calls).

Note: step 4 really reserves 1 Saybrook Logo T Shirt (size S) for the seeded test user, so
that item's stock goes down by one - exactly what a shopper's reservation does.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_improvements.py [base_url]
"""
import sqlite3
import sys
import time
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
DB = Path(__file__).resolve().parents[2] / "data" / "campus_customs.db"
SEED = {"email": "test@campuscustoms.yale.edu", "password": "password"}
failures = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"[{'ok' if ok else 'FAIL'}] {label}{' - ' + detail if detail else ''}")


def db(sql: str, *args):
    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=120) as c:
        print("--- Fair limits: lockout can't be used against the real owner")
        attacker = {"X-Forwarded-For": "198.51.100.7"}
        codes = [c.post("/api/auth/login", json={**SEED, "password": "wrong"}, headers=attacker).status_code for _ in range(5)]
        check("5 wrong passwords lock the attacker's address", codes == [401, 401, 401, 401, 429], str(codes))
        res = c.post("/api/auth/login", json=SEED, headers={"X-Forwarded-For": "192.0.2.44"})
        check("the owner can still log in from their own address", res.status_code == 200)

        print("\n--- Run log & cost")
        t = time.perf_counter()
        res = c.post("/api/chat", json={"message": "Is the Saybrook College Crewneck in stock in medium?",
                                        "page": {"path": "/products"}})
        check("chat replied", res.status_code == 200, f"{time.perf_counter() - t:.1f}s: {res.json()['message']['content'][:90]}…")
        usage = c.get("/api/admin/usage?days=1").json()
        run = next(r for r in usage["recent"] if r["kind"] == "chat")
        check("the run is logged with its tool calls, tokens and cost",
              bool(run["toolCalls"]) and run["inputTokens"] > 0 and run["costUsd"] > 0,
              f"tools={[x['tool'] for x in run['toolCalls']]} tokens={run['inputTokens']}/{run['outputTokens']} cost=${run['costUsd']:.4f}")

        print("\n--- Longer memory")
        for _ in range(60):  # the summary runs in the background after the reply
            row = db("SELECT summary, through_message_id FROM chat_summaries WHERE user_id = 1")
            if row:
                break
            time.sleep(1)
        check("older messages were summarized for the test user", bool(row),
              (row[0][0][:140].replace("\n", " ") + "…") if row else "no summary yet")
        if row:
            kept = db("SELECT COUNT(*) FROM chat_messages WHERE user_id = 1 AND id > ?", row[0][1])[0][0]
            total = db("SELECT COUNT(*) FROM chat_messages WHERE user_id = 1")[0][0]
            check("recent messages stay word-for-word; nothing deleted", 20 <= kept < total, f"{kept} recent of {total} saved")

        print("\n--- Cart & checkout")
        item = {"productId": "saybrook-logo-t-shirt", "size": "S", "quantity": 1}
        before = next(s["quantity"] for s in c.get("/api/products/saybrook-logo-t-shirt").json()["sizes"] if s["size"] == "S")
        quote = c.post("/api/cart/quote", json={"items": [item, {**item, "size": "L"}]}).json()
        check("cart quote flags a sold-out size", quote["ok"] is False and any(l["problem"] == "sold_out" for l in quote["lines"]))
        order = c.post("/api/orders", json={"items": [item], "pickupName": "Test User", "note": "e2e check"})
        check("reservation placed", order.status_code == 201, order.json().get("orderNumber", order.text))
        after = next(s["quantity"] for s in c.get("/api/products/saybrook-logo-t-shirt").json()["sizes"] if s["size"] == "S")
        check("stock went down by one", after == before - 1, f"{before} -> {after}")
        check("order shows under My orders", c.get("/api/orders").json()[0]["orderNumber"] == order.json()["orderNumber"])
        c.post("/api/auth/logout")

    print(f"\n{'All checks passed' if not failures else f'{failures} check(s) failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
