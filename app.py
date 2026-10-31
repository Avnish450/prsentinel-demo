import os

BASE_DIR = "/var/app/files"

def read_user_file(filename):
    # SECURITY FIX: block path traversal (CVE-DEMO-0001)
    if ".." in filename or filename.startswith("/"):
        raise ValueError("Invalid file path")
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r") as f:
        return f.read()
