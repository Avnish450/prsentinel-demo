import os
import re
import json
import subprocess
import urllib.request
from typing import List, Dict, Any, Optional, Tuple
import prsentinel
from backend.services.crypto_service import sanitize_text

SECURITY_COMMIT_REGEX = re.compile(
    r"(CVE-\d{4}-\d+|GHSA-[a-z0-9-]+|security|vulnerab|XSS|CSRF|injection|sanitiz|traversal|overflow|auth\s*bypass)",
    re.IGNORECASE
)

CVE_EXTRACTOR = re.compile(r"(CVE-\d{4}-\d+|GHSA-[a-z0-9-]+)", re.IGNORECASE)

def gh_api_call(url: str, token: Optional[str] = None, accept: str = "application/vnd.github+json"):
    """GitHub API request with rate-limit and auth error handling."""
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "PRSentinel/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            if "json" in accept:
                return json.loads(content)
            return content
    except urllib.error.HTTPError as e:
        if e.code == 403:
            msg = "GitHub API rate limit exceeded. Please provide a GitHub Personal Access Token."
            raise RuntimeError(msg)
        elif e.code == 404:
            raise RuntimeError("Repository or Pull Request not found on GitHub")
        elif e.code == 401:
            raise RuntimeError("Invalid GitHub authentication token")
        raise RuntimeError(f"GitHub API returned HTTP {e.code}: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"GitHub request failed: {e}")

def run_patch_scan(
    patch_text: str,
    title: str = "Uploaded Patch",
    fixes: List[Dict[str, Any]] = None,
    policy: Dict[str, Any] = None,
    logger = None
) -> Dict[str, Any]:
    """Scan a raw diff/patch without cloning."""
    if logger:
        logger("Analyzing patch content...")
    context = {"title": title}
    result = prsentinel.analyze_diff(patch_text, context=context, fixes=fixes, policy=policy)
    if logger:
        logger(f"Patch scan complete. Score: {result['score']}/100 ({result['level']}).")
    return result

def run_single_pr_scan(
    pr_url: str,
    token: Optional[str] = None,
    fixes: List[Dict[str, Any]] = None,
    policy: Dict[str, Any] = None,
    logger = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Scan a single pull request URL."""
    # Pattern: https://github.com/owner/repo/pull/123
    m = re.match(r"^https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)", pr_url.strip())
    if not m:
        raise ValueError("Invalid PR URL. Format must be https://github.com/owner/repo/pull/<number>")

    owner, repo, pr_num = m.group(1), m.group(2), m.group(3)
    if logger:
        logger(f"Fetching metadata and diff for {owner}/{repo} PR #{pr_num}...")

    # Fetch PR details
    pr_meta_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
    meta = gh_api_call(pr_meta_url, token=token)

    # Fetch PR diff
    diff_text = gh_api_call(pr_meta_url, token=token, accept="application/vnd.github.v3.diff")

    title = meta.get("title", "")
    author = meta.get("user", {}).get("login", "")
    author_assoc = meta.get("author_association", "")
    first_time = author_assoc in ("FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE")

    age_days = None
    if author and token:
        try:
            u_info = gh_api_call(f"https://api.github.com/users/{author}", token=token)
            if "created_at" in u_info:
                from datetime import datetime, timezone
                created = datetime.fromisoformat(u_info["created_at"].replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created).days
        except Exception:
            pass

    context = {
        "title": title,
        "author": author,
        "age_days": age_days,
        "first_time": first_time
    }

    if logger:
        logger(f"Running multi-signal analysis on PR #{pr_num}: '{title}'...")

    result = prsentinel.analyze_diff(diff_text, context=context, fixes=fixes, policy=policy)
    return result, {
        "pr_num": pr_num,
        "owner": owner,
        "repo": repo,
        "title": title,
        "url": pr_url,
        "author": author
    }

def run_open_prs_scan(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    fixes: List[Dict[str, Any]] = None,
    policy: Dict[str, Any] = None,
    logger = None
) -> List[Dict[str, Any]]:
    """Fetch and scan all open pull requests for a repository."""
    if logger:
        logger(f"Querying open pull requests for {owner}/{repo}...")

    prs_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=30"
    open_prs = gh_api_call(prs_url, token=token)

    if not isinstance(open_prs, list):
        if logger:
            logger("No open pull requests found.")
        return []

    if logger:
        logger(f"Found {len(open_prs)} open pull request(s). Starting scans...")

    findings = []
    for idx, pr in enumerate(open_prs, start=1):
        pr_num = str(pr.get("number"))
        pr_url = pr.get("html_url", f"https://github.com/{owner}/{repo}/pull/{pr_num}")
        pr_title = pr.get("title", "")
        author = pr.get("user", {}).get("login", "")

        if logger:
            logger(f"[{idx}/{len(open_prs)}] Scanning PR #{pr_num}: '{pr_title}'...")

        try:
            diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
            diff_text = gh_api_call(diff_url, token=token, accept="application/vnd.github.v3.diff")

            context = {
                "title": pr_title,
                "author": author,
                "first_time": pr.get("author_association") in ("FIRST_TIME_CONTRIBUTOR", "NONE")
            }
            res = prsentinel.analyze_diff(diff_text, context=context, fixes=fixes, policy=policy)
            if res["score"] >= 40:
                findings.append({
                    "scan_result": res,
                    "target_ref": f"PR #{pr_num}",
                    "target_url": pr_url,
                    "title": f"PR #{pr_num}: {pr_title}",
                    "file_path": res["evidence"][0]["file"] if res["evidence"] else "multiple files"
                })
        except Exception as e:
            if logger:
                logger(f"Warning: Failed to scan PR #{pr_num}: {e}")

    return findings

def run_history_audit(
    repo_dir: str,
    max_commits: int = 500,
    fixes: List[Dict[str, Any]] = None,
    logger = None
) -> List[Dict[str, Any]]:
    """
    History Audit: walks up to N merged commits (default 500, max 2000).
    For each deleted line, uses git blame on parent commit to find introducing commit.
    If introducing commit message matches security patterns, records a finding!
    Also cross-references against registered fixes.
    """
    max_commits = min(max(max_commits, 10), 2000)
    if logger:
        logger(f"Starting git history audit (inspecting up to {max_commits} commits)...")

    # Get commits list: SHA \x00 Subject
    cmd = ["git", "log", f"--max-count={max_commits}", "--format=%H%x00%s", "HEAD"]
    res = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
    if res.returncode != 0:
        if logger:
            logger(f"Git log failed: {res.stderr}")
        return []

    lines = [l for l in res.stdout.splitlines() if l.strip()]
    commits = []
    for line in lines:
        parts = line.split("\x00")
        if len(parts) >= 2:
            commits.append((parts[0].strip(), parts[1].strip()))

    if logger:
        logger(f"Auditing {len(commits)} commits for security fix regressions...")

    findings = []
    seen_reversals = set()

    for idx, (commit_sha, subject) in enumerate(commits):
        if idx % 50 == 0 and logger and idx > 0:
            logger(f"Audited {idx}/{len(commits)} commits...")

        # Diff this commit against its parent
        diff_cmd = ["git", "diff-tree", "-p", "-U0", "-r", f"{commit_sha}^", commit_sha]
        diff_res = subprocess.run(diff_cmd, cwd=repo_dir, capture_output=True, text=True)
        if diff_res.returncode != 0:
            continue  # Initial commit has no parent

        diff_text = diff_res.stdout
        if not diff_text or "-" not in diff_text:
            continue

        # 1. First check against registered fixes using analyze_diff
        if fixes:
            direct_check = prsentinel.analyze_diff(
                diff_text,
                context={"title": subject},
                fixes=fixes
            )
            if direct_check["score"] >= 70:
                evidence_file = direct_check["evidence"][0]["file"] if direct_check["evidence"] else "unknown"
                key = (commit_sha, evidence_file)
                if key not in seen_reversals:
                    seen_reversals.add(key)
                    findings.append({
                        "mode": "history_audit",
                        "score": direct_check["score"],
                        "level": direct_check["level"],
                        "title": f"Commit {commit_sha[:8]}: {subject}",
                        "target_ref": commit_sha[:8],
                        "target_url": None,
                        "file_path": evidence_file,
                        "fix_id": direct_check["evidence"][0].get("fix_id") if direct_check["evidence"] else None,
                        "fix_commit_sha": None,
                        "reasons": direct_check["reasons"],
                        "breakdown": direct_check["breakdown"],
                        "evidence": direct_check["evidence"],
                        "summary": direct_check["summary"]
                    })
                    continue

        # 2. Autonomous git blame analysis for deleted lines
        current_file = None
        for diff_line in diff_text.splitlines():
            if diff_line.startswith("diff --git"):
                m = re.search(r" a/(.+) b/(.+)$", diff_line)
                current_file = m.group(1) if m else None
            elif diff_line.startswith("@@") and current_file:
                # @@ -start,count +start,count @@
                m = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff_line)
                if not m:
                    continue
                parent_start = int(m.group(1))
                parent_count = int(m.group(2)) if m.group(2) is not None else 1
                if parent_count <= 0:
                    continue

                # Run git blame on parent commit for this deleted line range
                blame_cmd = [
                    "git", "blame",
                    "-L", f"{parent_start},+{parent_count}",
                    "--porcelain",
                    f"{commit_sha}^",
                    "--",
                    current_file
                ]
                blame_res = subprocess.run(blame_cmd, cwd=repo_dir, capture_output=True, text=True)
                if blame_res.returncode != 0:
                    continue

                intro_shas = set()
                blame_lines = blame_res.stdout.splitlines()
                for b_line in blame_lines:
                    tokens = b_line.split()
                    if tokens and len(tokens[0]) == 40 and re.match(r"^[0-9a-f]{40}$", tokens[0]):
                        sha = tokens[0]
                        if sha != "0000000000000000000000000000000000000000" and sha != commit_sha:
                            intro_shas.add(sha)

                for intro_sha in intro_shas:
                    # Check commit message of the introducing commit
                    msg_res = subprocess.run(
                        ["git", "log", "-1", "--format=%B", intro_sha],
                        cwd=repo_dir, capture_output=True, text=True
                    )
                    intro_msg = msg_res.stdout.strip()
                    if SECURITY_COMMIT_REGEX.search(intro_msg):
                        key = (commit_sha, current_file, intro_sha)
                        if key in seen_reversals:
                            continue
                        seen_reversals.add(key)

                        intro_subject = intro_msg.splitlines()[0] if intro_msg else intro_sha[:8]
                        cve_match = CVE_EXTRACTOR.search(intro_msg)
                        cve_id = cve_match.group(1) if cve_match else "SECURITY-FIX"

                        findings.append({
                            "mode": "history_audit",
                            "score": 90,
                            "level": "HIGH",
                            "title": f"Commit {commit_sha[:8]} deleted security fix from {intro_sha[:8]}",
                            "target_ref": commit_sha[:8],
                            "target_url": None,
                            "file_path": current_file,
                            "fix_id": cve_id,
                            "fix_commit_sha": intro_sha,
                            "reasons": [
                                f"Commit {commit_sha[:8]} ('{subject}') removed code introduced in security fix {intro_sha[:8]}",
                                f"Original security commit: '{intro_subject}'"
                            ],
                            "breakdown": [
                                {
                                    "signal": "git_blame_security_reversal",
                                    "points": 90,
                                    "reason": f"Removed lines introduced by security commit {intro_sha[:8]} ('{intro_subject}')"
                                }
                            ],
                            "evidence": [
                                {
                                    "file": current_file,
                                    "fix_id": cve_id,
                                    "fix_commit_sha": intro_sha,
                                    "fix_commit_subject": intro_subject,
                                    "reverting_commit_sha": commit_sha,
                                    "reverting_commit_subject": subject,
                                    "similarity": 1.0,
                                    "description": f"Reversal of {cve_id}: {intro_subject}"
                                }
                            ],
                            "summary": f"HIGH RISK: Commit {commit_sha[:8]} ('{subject}') removes security logic originally introduced to resolve {cve_id} in {intro_sha[:8]} ('{intro_subject}')."
                        })

    if logger:
        logger(f"History audit finished. Found {len(findings)} regression(s).")

    return findings

def run_branch_compare(
    repo_dir: str,
    base_branch: str,
    head_branch: str,
    fixes: List[Dict[str, Any]] = None,
    policy: Dict[str, Any] = None,
    logger = None
) -> Dict[str, Any]:
    """Scan diff between two branches in the cloned repository."""
    if logger:
        logger(f"Comparing branches: {base_branch}...{head_branch}...")

    cmd = ["git", "diff", f"{base_branch}...{head_branch}"]
    res = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Git diff failed between {base_branch} and {head_branch}: {res.stderr}")

    diff_text = res.stdout
    context = {"title": f"Branch compare: {base_branch}..{head_branch}"}
    return prsentinel.analyze_diff(diff_text, context=context, fixes=fixes, policy=policy)

