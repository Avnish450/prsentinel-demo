import re
import urllib.request
import json
from typing import Dict, Any, Optional

OSV_API_BASE = "https://api.osv.dev/v1/vulns"

def fetch_osv_vulnerability(vuln_id: str) -> Dict[str, Any]:
    """
    Fetch vulnerability record from OSV API (https://api.osv.dev/v1/vulns/{id}).
    Handles CVE-xxxx-xxxx and GHSA-xxxx-xxxx.
    """
    clean_id = vuln_id.strip()
    url = f"{OSV_API_BASE}/{clean_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PRSentinel/1.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Vulnerability ID '{clean_id}' not found in OSV database")
        raise RuntimeError(f"OSV API returned HTTP error {e.code}")
    except Exception as e:
        raise RuntimeError(f"Failed to query OSV API: {e}")

def extract_fix_from_osv(vuln_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fix candidate from OSV vulnerability data.
    """
    vuln_id = vuln_data.get("id", "UNKNOWN")
    summary = vuln_data.get("summary") or vuln_data.get("details", "")[:120] or "Security vulnerability fix"
    # Truncate summary if too long
    if len(summary) > 250:
        summary = summary[:247] + "..."

    # Determine package name
    package = "general"
    affected = vuln_data.get("affected", [])
    if affected and isinstance(affected, list):
        pkg_info = affected[0].get("package", {})
        package = pkg_info.get("name", "general")

    # Determine severity
    severity = "HIGH"
    db_spec = vuln_data.get("database_specific", {})
    if "severity" in db_spec:
        severity = str(db_spec["severity"]).upper()
    elif vuln_data.get("severity"):
        sevs = vuln_data["severity"]
        if isinstance(sevs, list) and sevs:
            score_type = sevs[0].get("type", "")
            severity = "HIGH" if "CVSS" in score_type else "MODERATE"

    # Find commit references
    commit_url = None
    references = vuln_data.get("references", [])
    for ref in references:
        r_url = ref.get("url", "")
        if "github.com" in r_url and "/commit/" in r_url:
            commit_url = r_url
            break

    fix_added_lines = []
    file_path = "app.py"

    # If GitHub commit URL exists, try fetching commit diff to extract added lines
    if commit_url:
        try:
            diff_url = commit_url.rstrip("/") + ".diff"
            req = urllib.request.Request(diff_url, headers={"User-Agent": "PRSentinel/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                diff_text = resp.read().decode("utf-8", errors="replace")
                # Parse added lines and file
                for line in diff_text.splitlines():
                    if line.startswith("+++ b/"):
                        file_path = line[6:].strip()
                    elif line.startswith("+") and not line.startswith("+++"):
                        content = line[1:].strip()
                        if content and not content.startswith("#") and len(content) > 10:
                            fix_added_lines.append(content)
                            if len(fix_added_lines) >= 8:
                                break
        except Exception:
            pass

    return {
        "id": vuln_id,
        "description": summary,
        "package": package,
        "file": file_path,
        "severity": severity,
        "source": "osv",
        "verified": True,
        "enabled": True,
        "fix_added_lines": fix_added_lines,
        "commit_url": commit_url
    }

