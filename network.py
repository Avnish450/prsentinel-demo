import re
import subprocess

def ping_host(host):
    # SECURITY FIX: stop command injection (CVE-DEMO-0003)
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
        raise ValueError("Invalid host")
    return subprocess.run(["ping", "-c", "1", host], capture_output=True)
