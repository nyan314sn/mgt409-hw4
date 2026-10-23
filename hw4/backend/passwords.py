"""Password hashing: PBKDF2-HMAC-SHA256, stored as ``pbkdf2_sha256$<salt>$<hex hash>``.

Matches the seed data exactly: the salt is the stored text (UTF-8 encoded),
120,000 iterations, 32-byte digest written as lowercase hex. Signup and login
both go through this module so their settings can never drift apart.
"""
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 16  # -> 32 hex characters of salt per user


def _derive(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return digest.hex()


def hash_password(password: str) -> str:
    """Hash a new password with a fresh random salt (used at signup)."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_derive(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Re-hash ``password`` with the salt from ``stored`` and compare in constant time."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_derive(password, salt), expected)


# Checked when the email is unknown, so a miss costs the same time as a wrong password
# and response timing doesn't reveal which emails have accounts.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
