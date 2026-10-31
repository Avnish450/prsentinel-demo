import subprocess
from unittest.mock import patch
import pytest
from backend.services.git_service import safe_clone_repo, CloneTimeoutError, RepoTooLargeError

def test_clone_timeout_handling():
    def mock_run_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["git", "clone"], timeout=120)

    with patch("subprocess.run", side_effect=mock_run_timeout):
        with pytest.raises(CloneTimeoutError):
            with safe_clone_repo("https://github.com/example/repo"):
                pass

def test_repo_size_limit_handling():
    # Mock calculate_dir_size_bytes to exceed 250MB limit
    with patch("backend.services.git_service.calculate_dir_size_bytes", return_value=300 * 1024 * 1024):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with pytest.raises(RepoTooLargeError):
                with safe_clone_repo("https://github.com/example/repo"):
                    pass

