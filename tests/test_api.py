import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PRSentinel Engine"

def test_repos_create_and_validation(client):
    # Invalid URL rejected
    bad_res = client.post("/api/repos", json={"url": "https://gitlab.com/user/project"})
    assert bad_res.status_code == 400

    ssh_res = client.post("/api/repos", json={"url": "ssh://git@github.com/user/project.git"})
    assert ssh_res.status_code == 400

    flag_res = client.post("/api/repos", json={"url": "--upload-pack=exploit"})
    assert flag_res.status_code == 400

    # Valid URL accepted
    good_res = client.post("/api/repos", json={"url": "https://github.com/pallets/flask"})
    assert good_res.status_code in (200, 201)
    data = good_res.json()
    assert data["owner"] == "pallets"
    assert data["name"] == "flask"
    assert "id" in data

def test_resolve_repo_input_endpoint(client):
    res_clone = client.post("/api/repos/resolve", json={"input": "git clone https://github.com/pallets/flask.git"})
    assert res_clone.status_code == 200
    data_clone = res_clone.json()
    assert data_clone["detected_type"] == "git_clone"
    assert data_clone["resolved_url"] == "https://github.com/pallets/flask"

    res_git = client.post("/api/repos/resolve", json={"input": "https://github.com/pallets/flask.git"})
    assert res_git.status_code == 200
    assert res_git.json()["detected_type"] == "git_url"

    res_web = client.post("/api/repos/resolve", json={"input": "https://github.com/pallets/flask"})
    assert res_web.status_code == 200
    assert res_web.json()["resolved_url"] == "https://github.com/pallets/flask"

def test_fixes_crud(client):
    # 1. List fixes (should have seeded demo fixes)
    res = client.get("/api/fixes")
    assert res.status_code == 200
    fixes = res.json()
    assert len(fixes) >= 1

    # 2. Create custom fix
    new_fix = {
        "id": "CVE-2024-TEST-01",
        "description": "Test fix rule",
        "file": "server.py",
        "severity": "HIGH",
        "fix_added_lines": ["if not auth.check(): raise PermissionError()"]
    }
    create_res = client.post("/api/fixes", json=new_fix)
    assert create_res.status_code == 201

    # 3. Toggle enabled
    put_res = client.put("/api/fixes/CVE-2024-TEST-01", json={"enabled": False})
    assert put_res.status_code == 200
    assert put_res.json()["enabled"] is False

    # 4. Clean up
    del_res = client.delete("/api/fixes/CVE-2024-TEST-01")
    assert del_res.status_code == 204

def test_rules_test_endpoint(client):
    diff_payload = {
        "diff": """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -6,2 +6,0 @@
-    if ".." in filename or filename.startswith("/"):
-        raise ValueError("Invalid file path")
""",
        "title": "minor cleanup"
    }
    res = client.post("/api/rules/test", json=diff_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["score"] >= 70
    assert data["level"] == "HIGH"
    assert len(data["evidence"]) >= 1

def test_policy_get_and_update(client):
    get_res = client.get("/api/policy")
    assert get_res.status_code == 200
    policy = get_res.json()
    assert "fail_on_level" in policy

    put_res = client.put("/api/policy", json={"fail_on_score": 80})
    assert put_res.status_code == 200
    assert put_res.json()["fail_on_score"] == 80

def test_stats_endpoint(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_repos" in stats
    assert "total_scans" in stats
    assert "high_findings" in stats
    assert "false_positive_rate" in stats
    assert isinstance(stats["activity_trend"], list)
