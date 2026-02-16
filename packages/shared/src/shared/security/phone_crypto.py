from __future__ import annotations

import base64
import hashlib
import hmac
import os


def _keystream(secret: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hashlib.sha256(secret + nonce + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def encrypt_phone(value: str | None, key: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    plaintext = value.encode("utf-8")
    nonce = os.urandom(16)
    secret = hashlib.sha256(key.encode("utf-8")).digest()
    stream = _keystream(secret, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    digest = hmac.new(secret, plaintext, hashlib.sha256).hexdigest()
    return token, digest

