"""Live chat check against the running app with the real model (makes a few AI calls).

Logs in as the seeded test user and has a three-turn conversation that only works if the
agent remembers earlier turns. The test user's chat history in the real database grows by
these turns, just as it would for a real shopper.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_chat.py [base_url]
"""
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"

TURNS = [
    ("Do you have anything for Saybrook College?", None),
    ("Which of those is the cheapest, and is it in stock in medium?", None),
    ("Is this one warm enough for a football game in November?", "saybrook-sweater-fleece-jacket"),
]


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=120) as c:
        res = c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
        res.raise_for_status()
        for message, product_id in TURNS:
            started = time.perf_counter()
            res = c.post("/api/chat", json={"message": message, "productId": product_id})
            print(f"\nSHOPPER: {message}" + (f"   [on page: {product_id}]" if product_id else ""))
            if res.status_code != 200:
                print(f"  ERROR {res.status_code}: {res.text}")
                sys.exit(1)
            body = res.json()
            print(f"ASSISTANT ({time.perf_counter() - started:.1f}s): {body['content']}")
            for p in body["products"]:
                print(f"  [card] {p['name']} - ${p['price']:.2f}")
        c.post("/api/auth/logout")


if __name__ == "__main__":
    main()
