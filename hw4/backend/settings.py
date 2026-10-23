"""Backend settings. Reuses hw4/config.py so the .env lookup and OPENAI_MODEL default
live in one place, whether the app is started from backend/ or from hw4/."""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
HW_DIR = BACKEND_DIR.parent
if str(HW_DIR) not in sys.path:
    sys.path.append(str(HW_DIR))

import config  # noqa: E402  (loads the nearest .env)

OPENAI_MODEL = config.OPENAI_MODEL
PORTKEY_BASE_URL = config.PORTKEY_BASE_URL
# Summarizing old chat is a simple task; point this at a smaller model to save cost.
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", OPENAI_MODEL)

# Prices used to *estimate* cost per chat (USD per 1M tokens). The defaults are
# placeholders - set the real prices for your model in .env.
MODEL_INPUT_PRICE_PER_MTOK = float(os.getenv("MODEL_INPUT_PRICE_PER_MTOK", "1.25"))
MODEL_OUTPUT_PRICE_PER_MTOK = float(os.getenv("MODEL_OUTPUT_PRICE_PER_MTOK", "10.00"))

# Accounts allowed to see the usage dashboard (comma-separated emails).
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "test@campuscustoms.yale.edu").split(",") if e.strip()}

# Proxies whose X-Forwarded-For header we trust (the Vite dev server runs on this machine).
TRUSTED_PROXIES = {p.strip() for p in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if p.strip()}

DATA_DIR = HW_DIR / "data"
PRODUCT_IMAGES_DIR = DATA_DIR / "products"
PROMPT_FILE = BACKEND_DIR / "prompts" / "prompt.md"
