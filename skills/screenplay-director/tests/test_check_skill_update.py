import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_skill_update.py"
SPEC = importlib.util.spec_from_file_location("check_skill_update", SCRIPT)
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
LOCAL = "a" * 40
REMOTE = "b" * 40


def make_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    skill = checkout / "skills" / "video-prompts"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n")
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "add", "skills"], check=True)
    subprocess.run([
        "git", "-C", str(checkout), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "Fixture",
    ], check=True)
    revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    return skill, revision


def test_matching_checkout_checks_remote_without_writing(tmp_path, monkeypatch):
    skill, revision = make_checkout(tmp_path)
    installed = tmp_path / "installed"
    installed.symlink_to(skill, target_is_directory=True)
    monkeypatch.setattr(check, "github_json", lambda route: {"sha": revision})
    assert check.check_update(installed) == {
        "status": "current", "local": revision, "upstream": revision, "source": "git",
    }


def test_copy_in_another_checkout_uses_its_recorded_ai_film_revision(tmp_path, monkeypatch):
    skill, unrelated_revision = make_checkout(tmp_path)
    assert unrelated_revision != LOCAL
    (skill / ".ai-film-skills-revision").write_text(LOCAL + "\n")
    monkeypatch.setattr(check, "github_json", lambda route: {"sha": LOCAL})
    assert check.check_update(skill) == {
        "status": "current", "local": LOCAL, "upstream": LOCAL, "source": "revision_file",
    }


def test_copied_skill_compares_recorded_revision(tmp_path, monkeypatch):
    (tmp_path / ".ai-film-skills-revision").write_text(LOCAL + "\n")
    routes = []

    def github(route):
        routes.append(route)
        return {"sha": REMOTE} if route == "commits/main" else {"status": "ahead"}

    monkeypatch.setattr(check, "github_json", github)
    assert check.check_update(tmp_path)["status"] == "update_available"
    assert routes == ["commits/main", f"compare/{LOCAL}...{REMOTE}?per_page=1"]


def test_missing_local_revision_still_checks_upstream(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "github_json", lambda route: {"sha": REMOTE})
    assert check.check_update(tmp_path) == {
        "status": "unverified", "local": None, "upstream": REMOTE, "source": None,
    }


def test_offline_check_is_unverified(tmp_path, monkeypatch):
    (tmp_path / ".ai-film-skills-revision").write_text(LOCAL + "\n")

    def unavailable(_route):
        raise OSError("offline")

    monkeypatch.setattr(check, "github_json", unavailable)
    assert check.check_update(tmp_path)["status"] == "unverified"


def test_diverged_remote_is_not_reported_as_an_update(tmp_path, monkeypatch):
    (tmp_path / ".ai-film-skills-revision").write_text(LOCAL + "\n")
    monkeypatch.setattr(check, "github_json", lambda route: (
        {"sha": REMOTE} if route == "commits/main" else {"status": "diverged"}
    ))
    assert check.check_update(tmp_path)["status"] == "diverged"
