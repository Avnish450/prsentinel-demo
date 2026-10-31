import inspect
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from backend.services.git_service import safe_clone_repo
from backend.services.crypto_service import sanitize_text

def test_clone_arguments_passed_as_list_after_separator():
    """Verify git clone arguments are strictly a list and URL is passed after '--' separator."""
    captured_cmds = []

    def mock_run(cmd, **kwargs):
        captured_cmds.append((cmd, kwargs))
        # Ensure shell=True was never used
        assert kwargs.get("shell") is not True, "subprocess.run must NEVER use shell=True"
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = ""
        mock_res.stderr = ""
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        try:
            with safe_clone_repo("https://github.com/example/repo") as repo_dir:
                pass
        except Exception:
            pass

    assert len(captured_cmds) >= 1
    clone_cmd, kwargs = captured_cmds[0]
    assert isinstance(clone_cmd, list), "git clone must be invoked with an argument list"
    assert clone_cmd[0] == "git"
    assert "core.hooksPath=/dev/null" in clone_cmd[2]
    assert "--filter=blob:none" in clone_cmd
    assert "--no-submodules" in clone_cmd
    assert "--" in clone_cmd

    # URL must strictly appear AFTER "--"
    dash_index = clone_cmd.index("--")
    url_index = clone_cmd.index("https://github.com/example/repo.git")
    assert url_index > dash_index, "Repository URL must be positioned after '--'"

def test_tokens_never_appear_in_sanitized_logs():
    token = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    log_text = f"Failed to connect using token {token} or https://x-access-token:{token}@github.com/foo/bar.git"
    sanitized = sanitize_text(log_text)
    assert token not in sanitized
    assert "ghp_" not in sanitized
    assert "https://***@github.com" in sanitized

