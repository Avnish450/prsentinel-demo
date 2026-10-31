#!/usr/bin/env python3
"""PRSentinel: flags pull requests that undo a past security fix."""
import argparse
import html
import json
import keyword
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher

MARKER = "<!-- prsentinel -->"
DEFAULT_SENSITIVE_PATTERNS = [
    r"raise", r"valid", r"sanit", r"auth", r"escape", r"verify",
    r"permission", r"token", r"password", r"(?:^|[^.])\.\.(?:[^.]|$)", r"startswith",
    r"isinstance", r"assert", r"secure", r"check", r"allowlist", r"whitelist"
]
SENSITIVE = re.compile(f"({'|'.join(DEFAULT_SENSITIVE_PATTERNS)})", re.I)
CLEANUP_TITLE = re.compile(r"(clean|tidy|refactor|minor|typo|simplif|small|chore)", re.I)
TOKEN = re.compile(r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|([A-Za-z_][A-Za-z0-9_]*)|(\s+)""")


def is_trivial_line(normalized_line: str) -> bool:
    """Ignore trivial normalized lines: length < 12 or fewer than 3 alphabetic tokens."""
    if not normalized_line or len(normalized_line) < 12:
        return True
    alpha_tokens = re.findall(r"[A-Za-z]+", normalized_line)
    if len(alpha_tokens) < 3:
        return True
    return False


def normalize(line: str) -> str:
    """Make code comparable: drop comments/whitespace, mask identifiers to ID while keeping literals and operators."""
    s = line.strip()
    if not s or s.startswith("#"):
        return ""
    # Strip trailing comments while keeping string literals intact
    s = re.sub(r"\s+#[^'\"]*$", "", s)

    def repl(m):
        # Keep string literals (lowercased)
        if m.group(1):
            return m.group(1).lower()
        # Mask identifiers to ID unless it is a Python keyword
        if m.group(2):
            w = m.group(2)
            return w if keyword.iskeyword(w) else "ID"
        # Preserve single space between tokens
        if m.group(3):
            return " "
        return ""

    res = TOKEN.sub(repl, s)
    return re.sub(r"\s+", " ", res).strip()


def parse_full_diff(text: str):
    """
    Parse unified diff into removed lines, added lines, renamed files, and deleted files.
    Handles 'rename from/to', 'deleted file mode', and standard chunks.
    """
    removed = {}
    added = {}
    renames = {}
    deleted_files = set()

    current_file_a = None
    current_file_b = None
    in_hunk = False

    for line in text.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
            m = re.search(r" a/(.+) b/(.+)$", line)
            if m:
                current_file_a = m.group(1)
                current_file_b = m.group(2)
                if current_file_a != current_file_b:
                    renames[current_file_a] = current_file_b
            else:
                current_file_a = current_file_b = None
        elif line.startswith("rename from "):
            current_file_a = line.split("rename from ", 1)[1].strip()
        elif line.startswith("rename to "):
            current_file_b = line.split("rename to ", 1)[1].strip()
            if current_file_a:
                renames[current_file_a] = current_file_b
        elif line.startswith("deleted file mode"):
            if current_file_a:
                deleted_files.add(current_file_a)
        elif line.startswith("--- "):
            if line.startswith("--- a/"):
                current_file_a = line[6:].strip()
            elif line.startswith("--- /dev/null"):
                current_file_a = None
        elif line.startswith("+++ "):
            if line.startswith("+++ b/"):
                current_file_b = line[6:].strip()
            elif line.startswith("+++ /dev/null"):
                current_file_b = None
                if current_file_a:
                    deleted_files.add(current_file_a)
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk:
            if line.startswith("-") and not line.startswith("---"):
                f = current_file_a or current_file_b or "unknown"
                removed.setdefault(f, []).append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                f = current_file_b or current_file_a or "unknown"
                added.setdefault(f, []).append(line[1:])

    return {
        "removed": removed,
        "added": added,
        "renames": renames,
        "deleted_files": list(deleted_files)
    }


def parse_diff(text: str):
    """Return {filename: [removed lines]} from a unified diff."""
    return parse_full_diff(text)["removed"]


def detect_moved_lines(removed_lines, added_lines_pool, similarity_threshold=0.85):
    """
    Detect if removed lines were merely moved/refactored elsewhere in the diff.
    Returns (is_moved, moved_matches).
    """
    if not removed_lines or not added_lines_pool:
        return False, []

    moved_matches = []
    norm_added = [normalize(l) for l in added_lines_pool]
    norm_added = [a for a in norm_added if not is_trivial_line(a)]

    if not norm_added:
        return False, []

    for r_line in removed_lines:
        r_norm = normalize(r_line)
        if is_trivial_line(r_norm):
            continue
        best_ratio = 0.0
        best_add = None
        for a_norm in norm_added:
            ratio = SequenceMatcher(None, r_norm, a_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_add = a_norm
        if best_ratio >= similarity_threshold:
            moved_matches.append((r_line, best_add, best_ratio))

    is_moved = len(moved_matches) > 0 and (len(moved_matches) >= len(removed_lines) * 0.5 or len(moved_matches) >= 2)
    return is_moved, moved_matches


def reverse_match_detailed(removed_by_file, fix, renames=None):
    """
    Detailed reverse match:
    - Filters trivial lines (< 12 chars or < 3 tokens)
    - Requires 2+ matching lines OR 1 line with similarity >= 0.9
    - Returns match details dict
    """
    renames = renames or {}
    target_base = os.path.basename(fix["file"])

    # Collect removed lines for this file or its renamed equivalent
    cands_raw = []
    for fname, lines in removed_by_file.items():
        base = os.path.basename(fname)
        new_name = renames.get(fname, fname)
        new_base = os.path.basename(new_name)
        if base == target_base or new_base == target_base or fname == fix["file"]:
            cands_raw.extend(lines)

    if not cands_raw:
        return {"similarity": 0.0, "line_matches": [], "valid": False, "max_sim": 0.0}

    # Filter out trivial lines
    cands_norm = [(l, normalize(l)) for l in cands_raw]
    cands_norm = [item for item in cands_norm if not is_trivial_line(item[1])]

    fix_lines_raw = fix.get("fix_added_lines", [])
    fix_norm = [(l, normalize(l)) for l in fix_lines_raw]
    fix_norm = [item for item in fix_norm if not is_trivial_line(item[1])]

    if not cands_norm or not fix_norm:
        return {"similarity": 0.0, "line_matches": [], "valid": False, "max_sim": 0.0}

    line_matches = []
    best_ratios = []

    for f_raw, f_n in fix_norm:
        best_sim = 0.0
        best_cand_raw = ""
        for c_raw, c_n in cands_norm:
            sim = SequenceMatcher(None, f_n, c_n).ratio()
            if sim > best_sim:
                best_sim = sim
                best_cand_raw = c_raw
        best_ratios.append(best_sim)
        if best_sim >= 0.70:
            line_matches.append({
                "fix_line": f_raw,
                "removed_line": best_cand_raw,
                "similarity": round(best_sim, 3)
            })

    max_sim = max(best_ratios) if best_ratios else 0.0
    matching_lines_count = len([r for r in best_ratios if r >= 0.75])
    # Engine requirement: require 2+ matching lines or one line with similarity >= 0.9
    valid = (matching_lines_count >= 2) or (max_sim >= 0.9)

    avg_sim = (sum(best_ratios) / len(best_ratios)) if best_ratios else 0.0

    return {
        "similarity": round(avg_sim, 3),
        "max_sim": round(max_sim, 3),
        "line_matches": line_matches,
        "matching_lines_count": matching_lines_count,
        "valid": valid,
        "fix_lines": [f[0] for f in fix_norm],
        "cands": [c[0] for c in cands_norm]
    }


def reverse_match(removed, fix):
    """How much of a known fix is being removed? Returns 0.0 - 1.0 (backward compatible)."""
    res = reverse_match_detailed(removed, fix)
    if not res["valid"]:
        return 0.0
    return res["similarity"]


def analyze_diff(diff_text: str, context: dict = None, fixes: list = None, policy: dict = None) -> dict:
    """
    Main analytical engine entrypoint:
    Returns {
        score, level, breakdown[{signal,points,reason}],
        evidence[], reasons[], advice, moved_lines_detected, summary
    }
    """
    context = context or {}
    fixes = fixes if fixes is not None else []
    policy = policy or {}

    parsed = parse_full_diff(diff_text)
    removed = parsed["removed"]
    added = parsed["added"]
    renames = parsed["renames"]

    # Gather all removed and added lines
    all_removed = [l for ls in removed.values() for l in ls]
    all_added = [l for ls in added.values() for l in ls]

    # Evaluate fixes
    best_fix = None
    best_match_info = None
    best_pct = 0.0
    evidence = []

    for fix in fixes:
        if not fix.get("enabled", True):
            continue
        match_info = reverse_match_detailed(removed, fix, renames)
        if match_info["valid"] and match_info["similarity"] > 0:
            evidence.append({
                "fix_id": fix.get("id"),
                "description": fix.get("description", ""),
                "file": fix.get("file", ""),
                "severity": fix.get("severity", "HIGH"),
                "similarity": match_info["similarity"],
                "max_similarity": match_info["max_sim"],
                "matching_lines_count": match_info["matching_lines_count"],
                "fix_lines": match_info.get("fix_lines", []),
                "removed_lines": [m["removed_line"] for m in match_info.get("line_matches", [])],
                "line_matches": match_info.get("line_matches", [])
            })
            if match_info["similarity"] > best_pct:
                best_pct = match_info["similarity"]
                best_fix = fix
                best_match_info = match_info

    # Check for moved lines (refactor detection)
    matched_removed_lines = []
    if best_match_info and best_match_info.get("line_matches"):
        matched_removed_lines = [m["removed_line"] for m in best_match_info["line_matches"]]
    moved_detected, moved_matches = detect_moved_lines(matched_removed_lines or all_removed, all_added)

    # Sensitive keywords check
    sensitive_patterns = policy.get("sensitive_keywords") or DEFAULT_SENSITIVE_PATTERNS
    sensitive_rx = re.compile(f"({'|'.join(sensitive_patterns)})", re.I)
    removes_check = any(sensitive_rx.search(l) for l in all_removed)

    # Signals toggles
    toggles = policy.get("signal_toggles", {})
    enable_fix_reversal = toggles.get("fix_reversal", True)
    enable_sensitive = toggles.get("sensitive_keywords", True)
    enable_title = toggles.get("cleanup_title", True)
    enable_age = toggles.get("account_age", True)
    enable_first_time = toggles.get("first_time", True)

    points = 0
    breakdown = []
    reasons = []

    # 1. Known Fix Reversal Signal
    if enable_fix_reversal and best_fix and best_pct >= 0.4:
        # Scale points: baseline 60 * similarity
        fix_points = round(60 * best_pct)
        # Treat similarity >= 0.9 as HIGH on its own
        if best_match_info and best_match_info.get("max_sim", 0) >= 0.9:
            fix_points = max(fix_points, 75)
        points += fix_points
        breakdown.append({
            "signal": "fix_reversal",
            "points": fix_points,
            "reason": f"Removes code matching security fix {best_fix.get('id')} ({round(best_pct * 100)}% similarity)"
        })
        reasons.append("This change removes a safety check")
        reasons.append(f"That check was added to fix a known security bug ({best_fix.get('id')}: {best_fix.get('description', '')})")
        reasons.append(f"{round(best_pct * 100)}% match with the original fix, in reverse")

    # 2. Sensitive Keyword Removal Signal
    if enable_sensitive and removes_check:
        k_points = 10
        points += k_points
        breakdown.append({
            "signal": "sensitive_check_removed",
            "points": k_points,
            "reason": "Removed lines contain validation, auth, or sanitization keywords"
        })
        if not reasons:
            reasons.append("Removed lines look like validation or safety checks")

    # 3. Cleanup PR Title Signal
    title = context.get("title", "")
    if enable_title and title and CLEANUP_TITLE.search(title) and (removes_check or best_pct >= 0.4):
        t_points = 5
        points += t_points
        breakdown.append({
            "signal": "cleanup_title_mismatch",
            "points": t_points,
            "reason": f"Title '{title}' sounds harmless but commit deletes security logic"
        })
        reasons.append(f'Described as "{title}" but it removes a safety check')

    # 4. PR Author Account Age Signal
    age_days = context.get("age_days")
    if enable_age and age_days is not None and age_days < 30:
        a_points = 15
        points += a_points
        breakdown.append({
            "signal": "young_account",
            "points": a_points,
            "reason": f"Submitted by account created only {age_days} days ago"
        })
        reasons.append(f"Sent by a {age_days}-day-old account")

    # 5. First-time Contributor Signal
    first_time = context.get("first_time", False)
    if enable_first_time and first_time:
        f_points = 10
        points += f_points
        breakdown.append({
            "signal": "first_time_author",
            "points": f_points,
            "reason": "First contribution to this repository"
        })
        reasons.append("First contribution to this repository")

    # 6. Moved lines reduction (Refactor protection)
    if moved_detected:
        reduction = 45
        points = max(0, points - reduction)
        breakdown.append({
            "signal": "moved_lines_reduction",
            "points": -reduction,
            "reason": "Safety check was re-added elsewhere in PR (code refactor/relocation)"
        })
        reasons.append("Safety check lines were re-added elsewhere in this pull request (refactoring detected)")

    # Treat similarity >= 0.9 as HIGH on its own unless lines were moved
    if best_match_info and best_match_info.get("max_sim", 0) >= 0.9 and not moved_detected:
        if points < 75:
            delta = 75 - points
            points = 75
            breakdown.append({
                "signal": "high_fidelity_reversal",
                "points": delta,
                "reason": "Near-identical reversal (similarity >= 90%) elevates risk to HIGH"
            })

    points = min(max(points, 0), 100)

    # Determine risk level
    if points >= 70:
        level = "HIGH"
    elif points >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not reasons:
        reasons.append("No fix reversal detected")

    advice = {
        "HIGH": "Do not merge yet. Review first.",
        "MEDIUM": "Review carefully before merging.",
        "LOW": "No action needed."
    }[level]

    # Generate plain-English summary
    if level == "HIGH":
        if best_fix:
            summary = f"HIGH RISK: This PR reverts critical security logic from {best_fix.get('id')} ({best_fix.get('description', '')}). Immediate manual review required."
        else:
            summary = "HIGH RISK: PR removes multiple sensitive security validations. Do not merge without verification."
    elif level == "MEDIUM":
        summary = "MEDIUM RISK: Changes touch sensitive validation logic or resemble a partial fix modification. Proceed with caution."
    else:
        if moved_detected:
            summary = "LOW RISK: Removed checks were detected as relocated or refactored within the PR. No security regressions identified."
        else:
            summary = "LOW RISK: No security fix reversals or suspicious patterns detected."

    return {
        "score": points,
        "level": level,
        "breakdown": breakdown,
        "evidence": evidence,
        "reasons": reasons,
        "advice": advice,
        "moved_lines_detected": moved_detected,
        "summary": summary
    }


def analyse(diff_text, fixes, title, age_days, first_time):
    """Legacy backward-compatible adapter returning (points, level_str, reasons, advice)."""
    context = {"title": title, "age_days": age_days, "first_time": first_time}
    res = analyze_diff(diff_text, context=context, fixes=fixes)
    level_str = f"{res['level']} RISK"
    return res["score"], level_str, res["reasons"], res["advice"]


def format_report(points, level, reasons, advice):
    """Format markdown report with PRSentinel sticky header."""
    level_display = level if "RISK" in level else f"{level} RISK"
    lines = [MARKER, f"## PRSentinel: {points} / 100 {level_display}", ""]
    lines += [f"- {html.escape(r)}" for r in reasons]
    lines += ["", f"**Advice: {html.escape(advice)}**"]
    return "\n".join(lines)


# ---------- GitHub helpers (used inside the Action) ----------
def gh(method, url, token, data=None, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data else None)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "prsentinel")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode()


def account_age_days(login, token):
    try:
        info = json.loads(gh("GET", f"https://api.github.com/users/{login}", token))
        created = datetime.fromisoformat(info["created_at"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created).days
    except Exception:
        return None


def post_comment(repo, pr, token, body):
    base = f"https://api.github.com/repos/{repo}/issues"
    try:
        existing = json.loads(gh("GET", f"{base}/{pr}/comments?per_page=100", token))
        for c in existing:
            if MARKER in c.get("body", ""):
                gh("PATCH", f"{base}/comments/{c['id']}", token, {"body": body})
                return
        gh("POST", f"{base}/{pr}/comments", token, {"body": body})
    except Exception as e:
        print(f"Warning: Failed to post sticky GitHub comment: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="PRSentinel: detect PRs that revert security fixes.")
    ap.add_argument("--diff", help="Path to diff file, or '-' for stdin")
    ap.add_argument("--title", default="", help="Pull request title")
    ap.add_argument("--age-days", type=int, help="PR author account age in days")
    ap.add_argument("--first-time", action="store_true", help="PR author is first-time contributor")
    ap.add_argument("--fixes", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixes.json"),
                    help="Path to fixes.json file")
    a = ap.parse_args()

    fixes = []
    if os.path.exists(a.fixes):
        with open(a.fixes, "r") as f:
            fixes = json.load(f)

    if a.diff:  # local / fallback mode
        diff = sys.stdin.read() if a.diff == "-" else open(a.diff).read()
        result = analyse(diff, fixes, a.title, a.age_days, a.first_time)
        print(format_report(*result).replace(MARKER + "\n", ""))
        return

    # Action mode via environment variables
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("REPO")
    pr = os.environ.get("PR_NUMBER")

    if not token or not repo or not pr:
        print("Usage: prsentinel.py --diff <diff-file> OR set GITHUB_TOKEN, REPO, PR_NUMBER env vars.", file=sys.stderr)
        sys.exit(1)

    diff = gh("GET", f"https://api.github.com/repos/{repo}/pulls/{pr}", token,
              accept="application/vnd.github.v3.diff")
    age = account_age_days(os.environ.get("PR_AUTHOR", ""), token)
    first = os.environ.get("AUTHOR_ASSOC", "") in ("FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE")
    result = analyse(diff, fixes, os.environ.get("PR_TITLE", ""), age, first)
    report = format_report(*result)
    print(report)
    post_comment(repo, pr, token, report)


if __name__ == "__main__":
    main()
