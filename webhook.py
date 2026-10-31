import hashlib
import hmac

def handle_webhook(payload, signature, secret):
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    # SECURITY FIX: verify webhook signature (CVE-DEMO-0005)
    if not hmac.compare_digest(signature, expected):
        raise PermissionError("Bad signature")
    return payload
