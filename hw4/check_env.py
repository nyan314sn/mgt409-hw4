"""Verify the HW4 environment: interpreter, .env loading, package imports, and the data pack.

Run with: C:\\Users\\Pi\\miniconda3\\python.exe check_env.py
"""
import importlib
import sys
from pathlib import Path

import config

REQUIRED = {
    "python-dotenv": "dotenv",
    "openai": "openai",
    "pydantic": "pydantic",
    "pydantic-ai-slim": "pydantic_ai",
    "httpx": "httpx",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pytest": "pytest",
}


def main() -> int:
    ok = True
    print(f"Python: {sys.executable} ({sys.version.split()[0]})")
    print(f".env:   {config.ENV_FILE or 'NOT FOUND'}")
    # Report presence only -- never the value.
    print(f"PORTKEY_API_KEY: {'set' if config.PORTKEY_API_KEY else 'MISSING'}")
    print(f"OPENAI_MODEL:    {config.OPENAI_MODEL}")
    ok &= bool(config.PORTKEY_API_KEY)

    for package, module in REQUIRED.items():
        try:
            mod = importlib.import_module(module)
            print(f"  [ok]   {package} {getattr(mod, '__version__', '')}")
        except ImportError as exc:
            ok = False
            print(f"  [FAIL] {package}: {exc}")

    # Local-only data pack (not in git): hw4/data/campus_customs.db + hw4/data/products/
    data = Path(__file__).resolve().parent / "data"
    db_ok = (data / "campus_customs.db").is_file()
    photos = len(list((data / "products").glob("*.jpg"))) if (data / "products").is_dir() else 0
    print(f"Data pack: campus_customs.db {'found' if db_ok else 'MISSING'}, {photos} product photos")
    ok &= db_ok and photos > 0

    print("Environment OK" if ok else "Environment has problems")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
