import base64
import hashlib
import re
from cryptography.fernet import Fernet
from backend.config import ENCRYPTION_SECRET

# Derive or prepare a valid 32-byte url-safe base64 key
def _get_fernet_key(secret: str) -> bytes:
    try:
        # Check if already a valid 32-byte base64 key
        raw = base64.urlsafe_b64decode(secret.encode())
        if len(raw) == 32:
            return secret.encode()
    except Exception:
        pass
    # Derive 32 bytes with SHA256
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)

_FERNET = Fernet(_get_fernet_key(ENCRYPTION_SECRET))

def encrypt_token(plain_text: str) -> str:
    """Encrypt a GitHub PAT or token at rest."""
    if not plain_text:
        return ""
    return _FERNET.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_token(cipher_text: str) -> str:
    """Decrypt a stored token."""
    if not cipher_text:
        return ""
    try:
        return _FERNET.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""

TOKEN_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{30,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}", re.IGNORECASE),
    re.compile(r"gho_[A-Za-z0-9_]{30,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
]

def sanitize_text(text: str) -> str:
    """Sanitize strings to ensure tokens, secrets, or basic auth never appear in logs or errors."""
    if not text:
        return ""
    res = str(text)
    # Redact credentials in URLs first
    res = re.sub(r"https://[^@\s]+@github\.com", "https://***@github.com", res, flags=re.IGNORECASE)
    # Redact raw tokens and bearer credentials
    for pat in TOKEN_PATTERNS:
        res = pat.sub("[REDACTED_TOKEN]", res)
    return res
