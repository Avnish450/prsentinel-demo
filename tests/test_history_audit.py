import os
import subprocess
import tempfile
import pytest
from backend.services.scanner_service import run_history_audit

def test_history_audit_planted_reversal():
    """
    Simulates a real Git repository with:
    1. Initial commit with basic code
    2. Commit 'Fix CVE-2024-9999: add security validation' adding check
    3. Commit 'minor cleanup and styling' that deletes the check
    Verifies history_audit discovers the reversal via git blame on the parent commit.
    """
    with tempfile.TemporaryDirectory(prefix="test_repo_") as temp_dir:
        env = {
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "author@example.com",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin")
        }

        # 1. git init
        subprocess.run(["git", "init", "-b", "main"], cwd=temp_dir, env=env, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, env=env, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, env=env, check=True)

        # Commit 1: vulnerable code
        file_path = os.path.join(temp_dir, "auth_handler.py")
        with open(file_path, "w") as f:
            f.write("def login(user, password):\n    return db.verify(user, password)\n")
        subprocess.run(["git", "add", "auth_handler.py"], cwd=temp_dir, env=env, check=True)
        subprocess.run(["git", "commit", "-m", "Initial auth implementation"], cwd=temp_dir, env=env, check=True)

        # Commit 2: security fix
        with open(file_path, "w") as f:
            f.write(
                "def login(user, password):\n"
                "    if not re.match(r'^[a-zA-Z0-9]+$', user):\n"
                "        raise ValueError('Invalid user format')\n"
                "    return db.verify(user, password)\n"
            )
        subprocess.run(["git", "add", "auth_handler.py"], cwd=temp_dir, env=env, check=True)
        subprocess.run(["git", "commit", "-m", "Fix CVE-2024-9999: sanitize and validate username against injection"], cwd=temp_dir, env=env, check=True)
        fix_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True).stdout.strip()

        # Commit 3: reverting commit masked as minor cleanup
        with open(file_path, "w") as f:
            f.write("def login(user, password):\n    return db.verify(user, password)\n")
        subprocess.run(["git", "add", "auth_handler.py"], cwd=temp_dir, env=env, check=True)
        subprocess.run(["git", "commit", "-m", "minor cleanup of redundant code"], cwd=temp_dir, env=env, check=True)
        revert_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True).stdout.strip()

        # Run history audit
        findings = run_history_audit(temp_dir, max_commits=10)

        assert len(findings) >= 1
        found = findings[0]
        assert found["level"] == "HIGH"
        assert found["target_ref"] == revert_sha[:8]
        assert found["fix_commit_sha"] == fix_sha
        assert "CVE-2024-9999" in found["fix_id"]
        assert "CVE-2024-9999" in found["summary"]

