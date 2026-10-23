"""Live check of the chat -> page contract with the real model (makes a few AI calls).

For "what hoodies do you have?" the reply must carry the chat text and the product data as
two separate parts, the products must be real catalogue items with image/name/price/info,
and each one must open its product page.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_showcase.py [base_url]
"""
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
QUESTIONS = ["What hoodies do you have?", "Show me gifts for a Yale dad under $60", "hi! who are you?"]


def main() -> None:
    failures = 0
    with httpx.Client(base_url=BASE, timeout=120) as c:
        c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"}).raise_for_status()
        catalogue = {p["id"]: p for p in c.get("/api/products").json()}
        for q in QUESTIONS:
            t = time.perf_counter()
            res = c.post("/api/chat", json={"message": q})
            body = res.json()
            print(f"\nSHOPPER: {q}  ({time.perf_counter() - t:.1f}s)")
            print(f"  keys: {sorted(body)}")
            print(f"  message: {body['message']['content']}")
            show = body["showcase"]
            if show is None:
                print("  showcase: none (page unchanged)")
                continue
            print(f"  showcase: '{show['title']}' - {len(show['products'])} cards"
                  f" (totalMatches={show['totalMatches']}, browseUrl={show['browseUrl']})")
            for p in show["products"]:
                ok = (p["id"] in catalogue and p["price"] == catalogue[p["id"]]["price"]
                      and p["image"] and p["description"]
                      and c.get(p["image"]).status_code == 200
                      and c.get(f"/products/{p['id']}").status_code == 200       # detail route renders
                      and c.get(f"/api/products/{p['id']}").status_code == 200)  # detail data loads
                failures += not ok
                print(f"    [{'ok' if ok else 'FAIL'}] {p['name']} - ${p['price']:.0f}")
        c.post("/api/auth/logout")
    print(f"\n{'All cards valid' if not failures else f'{failures} card(s) failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
