# -*- coding: utf-8 -*-
"""Password hashing - stdlib pbkdf2_hmac, salted, constant-time compare."""

import hashlib
import hmac
import os

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), _ITERATIONS).hex()
    return f"pbkdf2${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$", 3)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                        bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False
