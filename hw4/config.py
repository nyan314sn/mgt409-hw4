"""Shared configuration: finds and loads the nearest .env, exposes model settings.

Secrets are read from the environment only and never printed.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

HW_DIR = Path(__file__).resolve().parent


def find_env_file(start: Path = HW_DIR) -> Path | None:
    """Return the nearest .env in `start` or any parent directory."""
    for folder in (start, *start.parents):
        candidate = folder / ".env"
        if candidate.is_file():
            return candidate
    return None


ENV_FILE = find_env_file()
if ENV_FILE:
    load_dotenv(ENV_FILE, override=False)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
