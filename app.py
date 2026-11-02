import os

BASE_DIR = "/var/app/files"

def read_user_file(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r") as f:
        return f.read()
