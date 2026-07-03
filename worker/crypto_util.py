"""AES-256-GCM helpers matching the Next.js app's src/lib/crypto.ts.

Format: base64(iv[12] || ciphertext || authTag[16]). Python's AESGCM already
appends the tag to the ciphertext on encrypt, which is why this lines up with
the Node side (which concatenates iv + ciphertext + cipher.getAuthTag()).
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    b64_key = os.environ["CREDENTIALS_ENCRYPTION_KEY"]
    key = base64.b64decode(b64_key)
    if len(key) != 32:
        raise ValueError("CREDENTIALS_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def encrypt_secret(plaintext: str) -> str:
    key = _get_key()
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext_and_tag).decode("ascii")


def decrypt_secret(encoded: str) -> str:
    key = _get_key()
    raw = base64.b64decode(encoded)
    iv, ciphertext_and_tag = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext_and_tag, None)
    return plaintext.decode("utf-8")
