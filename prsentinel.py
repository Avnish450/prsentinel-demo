#!/usr/bin/env python3
"""PRSentinel: flags pull requests that undo a past security fix."""
import argparse, json, keyword, os, re, sys, urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher

MARKER = "<!-- prsentinel -->"
SENSITIVE = re.compile(r"(raise|valid|sanit|auth|escape|verify|permission|token|password|\.\.|startswith|isinstance|assert)", re.I)
CLEANUP_TITLE = re.compile(r"(clean|tidy|refactor|minor|typo|simplif|small)", re.I)
TOKEN = re.compile(r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|([A-Za-z_][A-Za-z0-9_]*)|(\s+)""")


def parse_diff(text):
    """Return {filename: [removed lines]} from a unified diff."""
    removed, current, in_hunk = {}, None, False
    for line in text.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
            m = re.search(r" b/(.+)$", line)
            current = m.group(1) if m else None
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("-") and current:
            removed.setdefault(current, []).append(line[1:])
    return removed


def normalize(line):
    """Make code comparable: drop comments/whitespace, rename identifiers to ID."""
    s = line.strip()
    if s.startswith("#"):
        return ""
    s = re.sub(r"\s+#[^'\"]*$", "", s)

    def repl(m):
        if m.group(1):
            return m.group(1).lower()
        if m.group(2):
            w = m.group(2)
            return w if keyword.iskeyword(w) else "ID"
        return ""

    return TOKEN.sub(repl, s)


def reverse_match(removed, fix):
    """How much of a known fix is being removed? Returns 0.0 - 1.0."""
    target = os.path.basename(fix["file"])
    cands = []
    for fname, lines in removed.items():
        if os.path.basename(fname) == target:
            cands += [normalize(l) for l in lines]
    cands = [c for c in cands if len(c) >= 6]
    fix_lines = [normalize(l) for l in fix["fix_added_lines"]]
    fix_lines = [f for f in fix_lines if len(f) >= 6]
    if not cands or not fix_lines:
        return 0.0
    best = [max(SequenceMatcher(None, f, c).ratio() for c in cands) for f in fix_lines]
    return sum(best) / len(best)


def analyse(diff_text, fixes, title, age_days, first_time):
    removed = parse_diff(diff_text)
    best_fix, best_pct = None, 0.0
    for fix in fixes:
        pct = reverse_match(removed, fix)
        if pct > best_pct:
            best_fix, best_pct = fix, pct
    all_removed = [l for ls in removed.values() for l in ls]
    removes_check = any(SENSITIVE.search(l) for l in all_removed)

    points, reasons = 0, []
    if best_fix and best_pct >= 0.5:
        points += round(60 * best_pct)
        reasons.append("This change removes a safety check")
        reasons.append(f"That check was added to fix a known security bug "
                       f"({best_fix['id']}: {best_fix['description']})")
        reasons.append(f"{round(best_pct * 100)}% match with the original fix, in reverse")
    if removes_check:
        points += 10
        if not reasons:
            reasons.append("Removed lines look like validation or safety checks")
    if title and CLEANUP_TITLE.search(title) and (removes_check or best_pct >= 0.5):
        points += 5
        reasons.append(f'Described as "{title}" but it removes a safety check')
    if age_days is not None and age_days < 30:
        points += 15
        reasons.append(f"Sent by a {age_days}-day-old account")
    if first_time:
        points += 10
        reasons.append("First contribution to this repository")

    points = min(points, 100)
    level = "HIGH RISK" if points >= 70 else "MEDIUM RISK" if points >= 40 else "LOW RISK"
    if not reasons:
        reasons.append("No fix reversal detected")
    advice = {"HIGH RISK": "Do not merge yet. Review first.",
              "MEDIUM RISK": "Review carefully before merging.",
              "LOW RISK": "No action needed."}[level]
    return points, level, reasons, advice


def format_report(points, level, reasons, advice):
    lines = [MARKER, f"## PRSentinel: {points} / 100 {level}", ""]
    lines += [f"- {r}" for r in reasons]
    lines += ["", f"**Advice: {advice}**"]
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
    existing = json.loads(gh("GET", f"{base}/{pr}/comments?per_page=100", token))
    for c in existing:
        if MARKER in c.get("body", ""):
            gh("PATCH", f"{base}/comments/{c['id']}", token, {"body": body})
            return
    gh("POST", f"{base}/{pr}/comments", token, {"body": body})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff")
    ap.add_argument("--title", default="")
    ap.add_argument("--age-days", type=int)
    ap.add_argument("--first-time", action="store_true")
    ap.add_argument("--fixes", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixes.json"))
    a = ap.parse_args()
    fixes = json.load(open(a.fixes))

    if a.diff:  # local / fallback mode
        diff = sys.stdin.read() if a.diff == "-" else open(a.diff).read()
        result = analyse(diff, fixes, a.title, a.age_days, a.first_time)
        print(format_report(*result).replace(MARKER + "\n", ""))
        return

    token, repo, pr = os.environ["GITHUB_TOKEN"], os.environ["REPO"], os.environ["PR_NUMBER"]
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
