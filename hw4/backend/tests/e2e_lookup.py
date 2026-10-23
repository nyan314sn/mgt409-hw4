"""Live check of the lookup tools with the real model (makes a few AI calls).

Each question is checked against campus_customs.db: the reply must contain the real
price / quantity, and a sold-out size must be called out as sold out.

Run from hw4: C:\\Users\\Pi\\miniconda3\\python.exe backend/tests/e2e_lookup.py [base_url]
"""
import sqlite3
import sys
import time
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
DB = Path(__file__).resolve().parents[2] / "data" / "campus_customs.db"


def db_value(sql: str, *args):
    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    try:
        return con.execute(sql, args).fetchone()[0]
    finally:
        con.close()


def stock(pid: str, size: str) -> int:
    return db_value("SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", pid, size)


def price(pid: str) -> float:
    return db_value("SELECT price FROM catalogue WHERE product_id = ?", pid)


CHECKS = [
    # (question, strings that must appear in the reply (case-insensitive))
    ("How much is the saybrok colege crewnek?",
     [f"${price('saybrook-college-crewneck'):.0f}"]),
    ("Do you have the Saybrook College Crewneck in XXL?",
     ["sold out"]),
    ("How many are left in large?",
     [str(stock("saybrook-college-crewneck", "L"))]),
    ("What does the yale mom hoody look like, and what does it cost?",
     [f"${price('yale-mom-hoodie'):.0f}"]),
    ("How many Benjamin Franklin 1/4 zips do you have in medium?",
     [str(stock("benjamin-franklin-1-4-zip", "M"))]),
]


def main() -> None:
    failures = 0
    with httpx.Client(base_url=BASE, timeout=120) as c:
        c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"}).raise_for_status()
        for question, must_have in CHECKS:
            started = time.perf_counter()
            res = c.post("/api/chat", json={"message": question})
            reply = res.json().get("content", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
            missing = [m for m in must_have if m.lower() not in reply.lower()]
            ok = res.status_code == 200 and not missing
            failures += not ok
            print(f"\n[{'ok' if ok else 'FAIL'}] SHOPPER: {question}  ({time.perf_counter() - started:.1f}s)")
            print(f"ASSISTANT: {reply}")
            if missing:
                print(f"  missing expected: {missing}")
        c.post("/api/auth/logout")
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
