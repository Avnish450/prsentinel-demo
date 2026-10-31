import json
import pytest
import prsentinel
from backend.services.audit_service import sanitize_repo_text

@pytest.fixture
def fixes():
    return [
        {
            "id": "CVE-2021-0001",
            "description": "Path traversal fix in app.py",
            "file": "app.py",
            "fix_added_lines": [
                "if \"..\" in filename or filename.startswith(\"/\"):",
                "raise ValueError(\"Invalid file path\")"
            ]
        }
    ]

def test_trivial_lines_ignored():
    assert prsentinel.is_trivial_line(prsentinel.normalize("x = 1")) is True
    assert prsentinel.is_trivial_line(prsentinel.normalize("return None")) is True
    assert prsentinel.is_trivial_line(prsentinel.normalize("pass")) is True
    # Non-trivial security check
    assert prsentinel.is_trivial_line(prsentinel.normalize("if not current_user.is_admin:")) is False
    assert prsentinel.is_trivial_line(prsentinel.normalize("if \"..\" in filename or filename.startswith(\"/\"):")) is False

def test_normalize_preserves_literals_and_operators():
    line = 'if ".." in path or path.startswith("/"): # security check'
    norm = prsentinel.normalize(line)
    # Literals kept lowercased, identifier 'path' masked to 'ID', operators '.' and '(' kept
    assert '".."' in norm
    assert '"/"' in norm
    assert "ID" in norm
    assert "security check" not in norm  # comments stripped

def test_similarity_threshold_and_line_count_requirement(fixes):
    # Only 1 weak line match (< 0.9) should NOT trigger HIGH or count as valid match
    weak_diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,0 @@
-    if ".." in something:
"""
    res = prsentinel.analyze_diff(weak_diff, fixes=fixes)
    assert res["level"] != "HIGH"

def test_similarity_ge_09_treated_as_high_on_its_own(fixes):
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,0 @@
-    if ".." in filename or filename.startswith("/"):
-        raise ValueError("Invalid file path")
"""
    res = prsentinel.analyze_diff(diff, fixes=fixes)
    assert res["score"] >= 75
    assert res["level"] == "HIGH"

def test_moved_line_refactor_is_not_high(fixes):
    # Removed from app.py, re-added in utils.py
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -6,3 +6,3 @@
-    if ".." in filename or filename.startswith("/"):
-        raise ValueError("Invalid file path")
+    validate_safe_path(filename)
diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -1,0 +1,3 @@
+def validate_safe_path(filename):
+    if ".." in filename or filename.startswith("/"):
+        raise ValueError("Invalid file path")
"""
    res = prsentinel.analyze_diff(diff, fixes=fixes, context={"title": "Refactor path validator to utils"})
    assert res["moved_lines_detected"] is True
    assert res["level"] != "HIGH", "Moved lines refactor must NOT be classified as HIGH risk"
    assert any("moved_lines_reduction" in b["signal"] for b in res["breakdown"])

def test_renamed_file_reversal_caught(fixes):
    diff = """diff --git a/app.py b/app_v2.py
similarity index 90%
rename from app.py
rename to app_v2.py
--- a/app.py
+++ b/app_v2.py
@@ -6,3 +6,0 @@
-    if ".." in filename or filename.startswith("/"):
-        raise ValueError("Invalid file path")
"""
    res = prsentinel.analyze_diff(diff, fixes=fixes)
    assert res["level"] == "HIGH"

def test_reformatted_whitespace_reversal_caught(fixes):
    # Same code, different formatting
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -6,3 +6,0 @@
-    if ".." in file_var or file_var.startswith("/"):
-            raise ValueError("Invalid file path")
"""
    res = prsentinel.analyze_diff(diff, fixes=fixes)
    assert res["level"] == "HIGH"

def test_harmless_commits_not_flagged(fixes):
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,3 @@
-# Old header
-print("starting application...")
+# Updated header
+print("starting app server v2...")
"""
    res = prsentinel.analyze_diff(diff, fixes=fixes)
    assert res["score"] == 0
    assert res["level"] == "LOW"

def test_xss_payloads_in_commit_messages_rendered_as_text():
    xss_msg = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    sanitized = sanitize_repo_text(xss_msg)
    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized
    assert "<img" not in sanitized
    assert "&lt;img" in sanitized

