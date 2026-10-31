import re
import sqlite3

def get_user(conn, username):
    # SECURITY FIX: stop SQL injection (CVE-DEMO-0002)
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        raise ValueError("Invalid username")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchone()
