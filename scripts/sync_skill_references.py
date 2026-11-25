"""Synchronize local copies of shared references for one-folder installs."""

import argparse
from pathlib import Path


SKILLS = Path(__file__).resolve().parents[1] / "skills"
WRITING_SKILLS = (
    "dialogue-expert",
    "film-quality-control",
    "h3-prompt-writing",
    "screenplay-director",
    "screenplay-doctor",
    "screenplay-framework",
    "screenplay-writing",
    "storyboard-grid",
    "video-prompts",
    "visual-asset-prompts",
)
REFERENCES = (
    ("video-prompts", "concise-format.md", ("h3-prompt-writing",)),
    ("video-prompts", "performance-control.md", ("h3-prompt-writing",)),
    ("video-prompts", "storyboard-table-format.md", ("h3-prompt-writing", "screenplay-director")),
    ("video-prompts", "storyboard-table-template.md", ("h3-prompt-writing", "screenplay-director")),
    ("antigravity-writer", "writer-fallback.md", WRITING_SKILLS),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report missing or stale copies")
    args = parser.parse_args()
    stale = []
    for owner, filename, targets in REFERENCES:
        content = (SKILLS / owner / "references" / filename).read_bytes()
        for skill in targets:
            target = SKILLS / skill / "references" / filename
            if target.is_file() and target.read_bytes() == content:
                continue
            if args.check:
                stale.append(target.relative_to(SKILLS.parent))
                continue
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(content)
    for path in stale:
        print(f"Missing or stale shared reference: {path}")
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
