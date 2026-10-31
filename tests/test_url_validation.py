import pytest
from backend.services.git_service import validate_github_url, InvalidRepoURLError

def test_valid_github_urls():
    url1, owner1, repo1 = validate_github_url("https://github.com/torvalds/linux")
    assert url1 == "https://github.com/torvalds/linux"
    assert owner1 == "torvalds"
    assert repo1 == "linux"

    url2, owner2, repo2 = validate_github_url("https://github.com/org.sub-team/my-repo.git")
    assert url2 == "https://github.com/org.sub-team/my-repo"
    assert owner2 == "org.sub-team"
    assert repo2 == "my-repo"

def test_normalize_git_clone_and_git_url_formats():
    from backend.services.git_service import normalize_repo_input

    # 1. Git clone command format
    res1 = normalize_repo_input("git clone https://github.com/pallets/flask.git")
    assert res1 == "https://github.com/pallets/flask.git"
    norm1, owner1, repo1 = validate_github_url(res1)
    assert norm1 == "https://github.com/pallets/flask"

    # 2. Git URL format
    res2 = normalize_repo_input("https://github.com/psf/requests.git")
    assert res2 == "https://github.com/psf/requests.git"
    norm2, owner2, repo2 = validate_github_url(res2)
    assert norm2 == "https://github.com/psf/requests"

    # 3. Quoted git clone command
    res3 = normalize_repo_input("git clone 'https://github.com/tiangolo/fastapi.git'")
    norm3, owner3, repo3 = validate_github_url(res3)
    assert norm3 == "https://github.com/tiangolo/fastapi"

    # 4. Trailing slash and tree subpath
    res4 = normalize_repo_input("https://github.com/torvalds/linux/tree/master")
    norm4, owner4, repo4 = validate_github_url(res4)
    assert norm4 == "https://github.com/torvalds/linux"

def test_reject_non_github_hosts():
    with pytest.raises(InvalidRepoURLError):
        validate_github_url("https://gitlab.com/user/repo")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("https://bitbucket.org/user/repo")

def test_reject_file_and_ssh_protocols():
    with pytest.raises(InvalidRepoURLError):
        validate_github_url("file:///etc/passwd")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("ssh://git@github.com/user/repo.git")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("git://github.com/user/repo.git")

def test_reject_option_flags_and_injections():
    with pytest.raises(InvalidRepoURLError):
        validate_github_url("--upload-pack=whoami")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("-o ProxyCommand=calc")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("https://github.com/--flag/evil")

    with pytest.raises(InvalidRepoURLError):
        validate_github_url("https://github.com/user/../evil")

