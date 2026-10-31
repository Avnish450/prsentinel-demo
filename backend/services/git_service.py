import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple
from backend.config import MAX_CLONE_TIMEOUT_SEC, MAX_REPO_SIZE_MB
from backend.services.crypto_service import sanitize_text

GITHUB_URL_REGEX = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?$")

def normalize_repo_input(raw_input: str) -> str:
    """
    Cleans raw user input which may be:
    - A website URL: https://github.com/owner/repo or https://github.com/owner/repo/
    - A Git URL: https://github.com/owner/repo.git
    - A Git clone command: git clone https://github.com/owner/repo.git
    - An SSH URL: git@github.com:owner/repo.git -> converted to https
    """
    if not raw_input or not isinstance(raw_input, str):
        return ""

    s = raw_input.strip()

    # Strip 'git clone' prefix if user copied the full command
    if s.lower().startswith("git clone "):
        s = s[10:].strip()

    # Strip quotes if copied with quotes
    s = s.strip("\"'")

    # Strip trailing slashes
    s = s.rstrip("/")

    # Strip /tree/main, /blob/main etc. if user copied from deep link
    s = re.sub(r"/(tree|blob)/[\w.-]+.*$", "", s)

    # Convert git@github.com:owner/repo.git to https://github.com/owner/repo
    m_ssh = re.match(r"^git@github\.com:([\w.-]+)/([\w.-]+?)(?:\.git)?$", s)
    if m_ssh:
        return f"https://github.com/{m_ssh.group(1)}/{m_ssh.group(2)}"

    return s

def resolve_website_github_repo(website_url: str) -> Optional[str]:
    """
    Given a project website or documentation URL, inspects the HTML for GitHub repo links.
    """
    if not website_url or not isinstance(website_url, str):
        return None
    url = website_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (PRSentinel Website Resolver)"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read(500000).decode("utf-8", errors="ignore")
            matches = re.findall(r"https?://github\.com/([\w.-]+)/([\w.-]+)", content)
            ignored_owners = {
                "features", "pricing", "about", "explore", "topics",
                "site", "security", "contact", "join", "enterprise", "login", "signup"
            }
            for owner, repo in matches:
                if owner.lower() not in ignored_owners:
                    clean_repo = re.sub(r"[#?\"'/].*$", "", repo)
                    if clean_repo.endswith(".git"):
                        clean_repo = clean_repo[:-4]
                    if clean_repo and not clean_repo.startswith("-"):
                        return f"https://github.com/{owner}/{clean_repo}"
    except Exception:
        pass
    return None

class GitServiceError(Exception):
    """Base error for Git operations."""
    pass

class InvalidRepoURLError(GitServiceError):
    """Raised when repo URL is invalid or unsafe."""
    pass

class CloneTimeoutError(GitServiceError):
    """Raised when git clone times out."""
    pass

class RepoTooLargeError(GitServiceError):
    """Raised when cloned repo exceeds max allowed size."""
    pass

def validate_github_url(url: str) -> Tuple[str, str, str]:
    r"""
    Validate that url strictly matches ^https://github\.com/[\w.-]+/[\w.-]+(\.git)?$
    Rejects file://, ssh://, git://, option-like strings, and non-GitHub hosts.
    Returns (normalized_url, owner, repo_name).
    """
    if not url or not isinstance(url, str):
        raise InvalidRepoURLError("Repository URL cannot be empty")

    url = url.strip()

    # Reject option-like strings or flags
    if url.startswith("-"):
        raise InvalidRepoURLError("Invalid repository URL: option flags not permitted")

    # Reject non-https protocols explicitly
    if any(url.lower().startswith(p) for p in ("file://", "ssh://", "git://", "ftp://", "http://")):
        raise InvalidRepoURLError("Only HTTPS GitHub URLs are supported (https://github.com/...)")

    m = GITHUB_URL_REGEX.match(url)
    if not m:
        raise InvalidRepoURLError("URL must match https://github.com/owner/repository")

    owner, repo_name = m.group(1), m.group(2)
    # Ensure neither starts with a dash or contains path traversal
    if owner.startswith("-") or repo_name.startswith("-") or ".." in owner or ".." in repo_name:
        raise InvalidRepoURLError("Invalid repository name or owner in GitHub URL")

    normalized_url = f"https://github.com/{owner}/{repo_name}"
    return normalized_url, owner, repo_name

def calculate_dir_size_bytes(dir_path: str) -> int:
    """Calculate the total size in bytes of a directory."""
    total = 0
    try:
        for entry in os.scandir(dir_path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += calculate_dir_size_bytes(entry.path)
    except Exception:
        pass
    return total

@contextmanager
def safe_clone_repo(url: str, token: Optional[str] = None, logger=None):
    """
    Context manager that safely clones a GitHub repository into an isolated temp dir.
    Guarantees:
    - URL validated before execution
    - Subprocess argument list (never shell=True)
    - URL passed after '--'
    - GIT_TERMINAL_PROMPT=0
    - core.hooksPath=/dev/null
    - --filter=blob:none, --no-submodules
    - timeout enforcement
    - max repo size enforcement
    - token is stripped from git remote and logs
    - temp directory completely deleted on exit
    """
    normalized_url, owner, repo_name = validate_github_url(url)

    temp_dir = tempfile.mkdtemp(prefix="prsentinel_repo_")
    try:
        if logger:
            logger(f"Starting secure clone for {owner}/{repo_name}...")

        # Construct safe clone URL
        if token:
            clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"
        else:
            clone_url = f"https://github.com/{owner}/{repo_name}.git"

        # Safe environment
        env = {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "echo",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"),
            "HOME": temp_dir
        }

        # Safe argument list passed after --
        clone_cmd = [
            "git",
            "-c", "core.hooksPath=/dev/null",
            "clone",
            "--filter=blob:none",
            "--no-submodules",
            "--depth=500",
            "--",
            clone_url,
            temp_dir
        ]

        try:
            res = subprocess.run(
                clone_cmd,
                env=env,
                timeout=MAX_CLONE_TIMEOUT_SEC,
                capture_output=True,
                text=True
            )
        except subprocess.TimeoutExpired:
            raise CloneTimeoutError(f"Clone timed out after {MAX_CLONE_TIMEOUT_SEC}s")

        if res.returncode != 0:
            err = sanitize_text(res.stderr or res.stdout)
            if "Authentication failed" in err or "could not read Username" in err:
                raise GitServiceError("Repository not found or private repository requires an access token")
            raise GitServiceError(f"Git clone failed: {err}")

        # Immediately strip any credentials from the cloned repo remote URL
        clean_remote_url = f"https://github.com/{owner}/{repo_name}.git"
        subprocess.run(
            ["git", "remote", "set-url", "origin", clean_remote_url],
            cwd=temp_dir,
            env=env,
            capture_output=True
        )

        # Check repository size limit
        size_bytes = calculate_dir_size_bytes(temp_dir)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > MAX_REPO_SIZE_MB:
            raise RepoTooLargeError(
                f"Repository size ({size_mb:.1f} MB) exceeds maximum allowed limit of {MAX_REPO_SIZE_MB} MB"
            )

        if logger:
            logger(f"Clone completed successfully ({size_mb:.1f} MB, hooks disabled).")

        yield temp_dir

    finally:
        # Guarantee temp dir deletion
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
