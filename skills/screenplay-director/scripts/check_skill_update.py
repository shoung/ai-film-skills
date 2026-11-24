#!/usr/bin/env python3
"""Compare the installed ai-film-skills revision with upstream without updating it."""

import argparse
from http.client import HTTPException
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen


UPSTREAM_API = "https://api.github.com/repos/shoung/ai-film-skills/"
REVISION_FILE = ".ai-film-skills-revision"
SHA = re.compile(r"[0-9a-f]{40}")


def git(directory, *arguments):
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True, text=True, timeout=3,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def installed_revision(skill_dir):
    skill_dir = skill_dir.resolve()
    try:
        revision = (skill_dir / REVISION_FILE).read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        revision = ""
    if SHA.fullmatch(revision):
        return revision, "revision_file", None

    top = git(skill_dir, "rev-parse", "--show-toplevel")
    if top is not None and top.returncode == 0:
        root = Path(top.stdout.strip()).resolve()
        skill_path = skill_dir.relative_to(root) if skill_dir.is_relative_to(root) else Path()
        if len(skill_path.parts) == 2 and skill_path.parts[0] == "skills":
            tracked = git(root, "ls-files", "--error-unmatch", str(skill_path / "SKILL.md"))
            head = git(root, "rev-parse", "HEAD")
            if tracked is not None and tracked.returncode == 0 and head is not None and head.returncode == 0:
                revision = head.stdout.strip()
                if SHA.fullmatch(revision):
                    return revision, "git", root

    return None, None, None


def github_json(route):
    request = Request(UPSTREAM_API + route, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-film-skills-update-check",
    })
    with urlopen(request, timeout=5) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("GitHub returned an unexpected response")
    return payload


def compare_revisions(local, upstream, checkout):
    if local == upstream:
        return "current"
    if checkout is not None:
        for base, tip, result in (
            (local, upstream, "update_available"),
            (upstream, local, "local_ahead"),
        ):
            comparison = git(checkout, "merge-base", "--is-ancestor", base, tip)
            if comparison is not None and comparison.returncode == 0:
                return result
    relation = github_json(f"compare/{local}...{upstream}?per_page=1").get("status")
    if not isinstance(relation, str):
        return "unverified"
    return {
        "ahead": "update_available", "behind": "local_ahead", "diverged": "diverged",
    }.get(relation, "unverified")


def check_update(skill_dir):
    local, source, checkout = installed_revision(skill_dir)
    result = {"status": "unverified", "local": local, "upstream": None, "source": source}
    try:
        upstream = github_json("commits/main").get("sha")
        if isinstance(upstream, str) and SHA.fullmatch(upstream):
            result["upstream"] = upstream
            if local is not None:
                result["status"] = compare_revisions(local, upstream, checkout)
    except (OSError, ValueError, HTTPException):
        pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(check_update(args.skill_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
